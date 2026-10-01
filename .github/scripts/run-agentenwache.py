#!/usr/bin/env python3
"""AgentenWache v1: monitor AgentenGraph primary sources without auto-publishing facts."""
from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urljoin
from urllib.request import Request, build_opener
import difflib
import json
import re
import socket
import ssl
import time

ROOT = Path(__file__).resolve().parents[2]
GRAPH_SOURCES = ROOT / "_agentengraph" / "sources.json"
OUT = ROOT / "_agentenwache"
STATE_FILE = OUT / "source-states.json"
OVERRIDES_FILE = OUT / "monitoring-overrides.json"
QUEUE_FILE = OUT / "review-queue.json"
EVENT_FILE = OUT / "events.json"
SUMMARY_FILE = OUT / "last-run.json"

VERSION = "1.0"
USER_AGENT = "AgentenIndex-Wache/1.0 (+https://agentenindex.de/methodik/)"
MAX_BYTES = 5_000_000
TIMEOUT = 18
HOST_WORKERS = 8
HOST_DELAY = 0.35

TEXT_TYPES = ("text/", "application/json", "application/xml", "application/xhtml+xml")
SKIP_TAGS = {"script","style","noscript","svg","template","form","nav","header","footer","aside"}
BLOCK_TAGS = {"p","div","section","article","main","li","h1","h2","h3","h4","h5","h6","td","th","br","hr","dt","dd"}

def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")

def load(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def dump(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def stable_id(prefix: str, *parts: str, length=18) -> str:
    raw = "|".join(str(p) for p in parts).encode("utf-8")
    return prefix + sha256(raw).hexdigest()[:length].upper()

class VisibleTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.main_depth = 0
        self.seen_main = False
        self.all_parts = []
        self.main_parts = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in SKIP_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag in {"main","article"}:
            self.main_depth += 1
            self.seen_main = True
        if tag in BLOCK_TAGS:
            self._append(" ")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in SKIP_TAGS:
            if self.skip_depth:
                self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        if tag in BLOCK_TAGS:
            self._append(" ")
        if tag in {"main","article"} and self.main_depth:
            self.main_depth -= 1

    def handle_data(self, data):
        if not self.skip_depth:
            self._append(data)

    def _append(self, value):
        self.all_parts.append(value)
        if self.main_depth:
            self.main_parts.append(value)

    def text(self):
        parts = self.main_parts if self.seen_main and len("".join(self.main_parts)) > 250 else self.all_parts
        return " ".join(parts)

def normalize_text(raw: bytes, content_type: str) -> str:
    charset = "utf-8"
    m = re.search(r"charset=([A-Za-z0-9._-]+)", content_type or "", re.I)
    if m:
        charset = m.group(1)
    try:
        text = raw.decode(charset, errors="replace")
    except LookupError:
        text = raw.decode("utf-8", errors="replace")

    if "html" in (content_type or "").lower() or "<html" in text[:1500].lower():
        parser = VisibleTextParser()
        try:
            parser.feed(text)
            text = parser.text()
        except Exception:
            text = re.sub(r"<[^>]+>", " ", text)

    text = text.replace("\u00a0", " ")
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def tokens(text: str) -> list[str]:
    return re.findall(r"[\w€$£¥%+./:-]+", text.lower(), flags=re.UNICODE)

def simhash64(words: list[str]) -> str:
    if not words:
        return "0"*16
    # 3-token shingles reduce sensitivity to navigation/order noise while retaining small text edits.
    shingles = [" ".join(words[i:i+3]) for i in range(max(1, len(words)-2))]
    if len(words) < 3:
        shingles = words
    vec = [0]*64
    for sh in shingles:
        h = int.from_bytes(sha256(sh.encode("utf-8")).digest()[:8], "big")
        for i in range(64):
            vec[i] += 1 if (h >> i) & 1 else -1
    out = 0
    for i,v in enumerate(vec):
        if v >= 0:
            out |= 1 << i
    return f"{out:016x}"

def hamming_hex(a: str | None, b: str | None) -> int | None:
    if not a or not b:
        return None
    try:
        return (int(a,16) ^ int(b,16)).bit_count()
    except Exception:
        return None

def is_textual(content_type: str) -> bool:
    ct = (content_type or "").lower()
    return not ct or any(x in ct for x in TEXT_TYPES) or "html" in ct

def robots_url(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}/robots.txt"

def registrableish(host: str) -> str:
    host=(host or "").lower().split(":")[0].strip(".")
    parts=[p for p in host.split(".") if p]
    if len(parts) <= 2:
        return host
    two=".".join(parts[-2:])
    common_second_level={"co.uk","org.uk","ac.uk","com.au","net.au","co.jp","co.nz","com.br"}
    return ".".join(parts[-3:]) if two in common_second_level and len(parts)>=3 else two

def robots_rule_matches(target: str, rule: str) -> bool:
    """Match Google-style robots patterns with * wildcards and optional trailing $."""
    if not rule:
        return False
    anchored = rule.endswith("$")
    body = rule[:-1] if anchored else rule
    pattern = "^" + re.escape(body).replace(r"\\*", ".*")
    if anchored:
        pattern += "$"
    return re.search(pattern, target) is not None

def robots_rule_specificity(rule: str) -> int:
    """Approximate robots specificity by non-wildcard rule length."""
    return len(rule.rstrip("$").replace("*",""))

def robots_allows(url: str, cache: dict[str, list[tuple[str, str]]]) -> bool:
    host = urlparse(url).netloc.lower()
    # Cache parsed rules per host, never a path-specific allow/deny decision.
    # A robots.txt file can allow one path and disallow another on the same host.
    if host not in cache:
        # Conservative but resilient: only explicit AgentenIndex-Wache/User-agent:* Disallow matches block.
        # If robots cannot be fetched, do not invent a prohibition.
        try:
            req = Request(robots_url(url), headers={"User-Agent": USER_AGENT, "Accept":"text/plain"})
            with build_opener().open(req, timeout=8) as resp:
                raw = resp.read(300_000).decode("utf-8", errors="replace")
            groups = []
            current_agents = []
            current_rules = []
            for line in raw.splitlines():
                line = line.split("#",1)[0].strip()
                if not line or ":" not in line:
                    continue
                k,v = [x.strip() for x in line.split(":",1)]
                kl=k.lower()
                if kl=="user-agent":
                    if current_rules:
                        groups.append((current_agents,current_rules))
                        current_agents=[]; current_rules=[]
                    current_agents.append(v.lower())
                elif kl in {"allow","disallow"} and current_agents:
                    current_rules.append((kl,v))
            if current_agents or current_rules:
                groups.append((current_agents,current_rules))
            ua="agentenindex-wache"
            applicable=[]
            for agents,rules in groups:
                if any(a=="*" or a in ua for a in agents):
                    applicable.extend(rules)
            cache[host]=applicable
        except Exception:
            cache[host]=[]

    parsed = urlparse(url)
    target = parsed.path or "/"
    if parsed.query:
        target += "?" + parsed.query
    matched=None
    for kind,rule in cache[host]:
        if not rule or not robots_rule_matches(target, rule):
            continue
        candidate=(robots_rule_specificity(rule),kind)
        if matched is None or candidate[0] > matched[0] or (candidate[0]==matched[0] and kind=="allow"):
            matched=candidate
    return not (matched and matched[1]=="disallow")

def fetch_source(source: dict, previous: dict | None, robots_cache: dict[str, list[tuple[str, str]]]) -> dict:
    url=source["url"]
    checked=now_iso()
    if not robots_allows(url, robots_cache):
        return {
            "source_id":source["source_id"],"checked_at":checked,"url":url,
            "result":"robots_disallowed","ok":False,"error":"robots.txt disallows monitoring path"
        }

    headers={
        "User-Agent":USER_AGENT,
        "Accept":"text/html,application/xhtml+xml,application/json,text/plain,application/xml;q=0.9,*/*;q=0.2",
        "Accept-Language":"de,en;q=0.7",
        "Cache-Control":"no-cache",
    }
    if previous and previous.get("etag"):
        headers["If-None-Match"]=previous["etag"]
    if previous and previous.get("last_modified"):
        headers["If-Modified-Since"]=previous["last_modified"]

    req=Request(url,headers=headers,method="GET")
    try:
        with build_opener().open(req, timeout=TIMEOUT) as resp:
            status=getattr(resp,"status",200)
            final_url=resp.geturl()
            ct=resp.headers.get("Content-Type","")
            etag=resp.headers.get("ETag")
            lm=resp.headers.get("Last-Modified")
            if status==304 and previous:
                result=dict(previous)
                result.update({"checked_at":checked,"result":"not_modified","ok":True})
                return result
            raw=resp.read(MAX_BYTES+1)
            truncated=len(raw)>MAX_BYTES
            raw=raw[:MAX_BYTES]
            record={
                "source_id":source["source_id"],"checked_at":checked,"url":url,
                "result":"fetched","ok":200 <= status < 400,"status_code":status,
                "final_url":final_url,"content_type":ct,"etag":etag,"last_modified":lm,
                "bytes_read":len(raw),"truncated":truncated,
            }
            if is_textual(ct):
                text=normalize_text(raw,ct)
                words=tokens(text)
                record.update({
                    "text_hash":sha256(text.encode("utf-8")).hexdigest(),
                    "simhash64":simhash64(words),
                    "token_count":len(words),
                    "text_length":len(text),
                    "text_sample":text[:1200],
                })
            else:
                record.update({
                    "binary_hash":sha256(raw).hexdigest(),
                    "token_count":0,"text_length":0,"text_sample":"",
                })
            return record
    except HTTPError as e:
        if e.code==304 and previous:
            result=dict(previous)
            result.update({"checked_at":checked,"result":"not_modified","ok":True})
            return result
        return {
            "source_id":source["source_id"],"checked_at":checked,"url":url,
            "result":"http_error","ok":False,"status_code":e.code,
            "final_url":getattr(e,"url",url),"error":str(e),
        }
    except (URLError, socket.timeout, TimeoutError, ssl.SSLError) as e:
        return {
            "source_id":source["source_id"],"checked_at":checked,"url":url,
            "result":"network_error","ok":False,"error":str(e),
        }
    except Exception as e:
        return {
            "source_id":source["source_id"],"checked_at":checked,"url":url,
            "result":"error","ok":False,"error":f"{type(e).__name__}: {e}",
        }

def classify(previous: dict | None, current: dict) -> tuple[str | None, str | None, dict]:
    if previous is None:
        return "baseline", None, {}
    metrics={}
    old_status=previous.get("status_code")
    new_status=current.get("status_code")
    if old_status != new_status and new_status is not None:
        metrics["old_status"]=old_status; metrics["new_status"]=new_status
        sev="high" if new_status >= 400 or new_status in {404,410} else "medium"
        return "status_change",sev,metrics

    old_final=previous.get("final_url") or previous.get("url")
    new_final=current.get("final_url") or current.get("url")
    if old_final and new_final and old_final != new_final:
        metrics["old_final_url"]=old_final; metrics["new_final_url"]=new_final
        old_host=urlparse(old_final).netloc.lower()
        new_host=urlparse(new_final).netloc.lower()
        sev="high" if registrableish(old_host) != registrableish(new_host) else "medium"
        return "redirect_change",sev,metrics

    if previous.get("ok") and not current.get("ok"):
        metrics["previous_result"]=previous.get("result")
        metrics["current_result"]=current.get("result")
        return "availability_change","high",metrics
    if not previous.get("ok") and current.get("ok"):
        metrics["previous_result"]=previous.get("result")
        metrics["current_result"]=current.get("result")
        return "availability_restored","low",metrics

    old_hash=previous.get("text_hash") or previous.get("binary_hash")
    new_hash=current.get("text_hash") or current.get("binary_hash")
    if old_hash and new_hash and old_hash != new_hash:
        dist=hamming_hex(previous.get("simhash64"),current.get("simhash64"))
        old_tokens=previous.get("token_count") or 0
        new_tokens=current.get("token_count") or 0
        delta=(new_tokens-old_tokens)/max(old_tokens,1)
        metrics.update({
            "old_hash":old_hash,"new_hash":new_hash,
            "simhash_distance":dist,
            "old_token_count":old_tokens,"new_token_count":new_tokens,
            "token_delta_pct":round(delta*100,2),
        })
        ad=abs(delta)
        if dist is not None and (dist >= 18 or ad >= .35):
            sev="high"
        elif dist is not None and (dist >= 8 or ad >= .12):
            sev="medium"
        else:
            sev="low"
        return "content_change",sev,metrics
    return None,None,metrics

def main():
    started=now_iso()
    graph=load(GRAPH_SOURCES,{"sources":[]})
    sources=[s for s in graph.get("sources",[]) if s.get("active")]
    OUT.mkdir(parents=True,exist_ok=True)
    state_doc=load(STATE_FILE,{"watch_version":VERSION,"states":[]})
    override_doc=load(OVERRIDES_FILE,{"version":1,"overrides":[]})
    queue_doc=load(QUEUE_FILE,{"watch_version":VERSION,"items":[]})
    events_doc=load(EVENT_FILE,{"watch_version":VERSION,"events":[]})

    prior={s["source_id"]:s for s in state_doc.get("states",[])}
    overrides={o["url"]:o for o in override_doc.get("overrides",[]) if o.get("url")}
    queue={i["review_id"]:i for i in queue_doc.get("items",[])}
    events={e["event_id"]:e for e in events_doc.get("events",[])}

    by_host=defaultdict(list)
    results=[]
    manual_source_ids=set()
    for source in sources:
        override=overrides.get(source["url"])
        if override and override.get("mode")=="manual_only":
            sid=source["source_id"]
            manual_source_ids.add(sid)
            results.append((source,{
                "source_id":sid,
                "checked_at":now_iso(),
                "url":source["url"],
                "result":"manual_only",
                "ok":False,
                "monitoring_mode":"manual_only",
                "manual_reason":override.get("reason"),
                "manual_verified_at":override.get("verified_at"),
            }))
            continue
        by_host[urlparse(source["url"]).netloc.lower()].append(source)

    robots_cache={}
    def process_host(items):
        out=[]
        for idx,source in enumerate(items):
            if idx:
                time.sleep(HOST_DELAY)
            out.append((source,fetch_source(source,prior.get(source["source_id"]),robots_cache)))
        return out

    with ThreadPoolExecutor(max_workers=HOST_WORKERS) as ex:
        futures=[ex.submit(process_host,items) for _,items in sorted(by_host.items())]
        for future in as_completed(futures):
            results.extend(future.result())

    new_states={}
    counts=defaultdict(int)
    changes=[]
    for source,current in results:
        sid=source["source_id"]
        previous=prior.get(sid)
        if current.get("result")=="manual_only":
            change_type,severity,metrics=None,None,{}
        else:
            change_type,severity,metrics=classify(previous,current)
        counts[current.get("result","unknown")]+=1
        if change_type=="baseline":
            counts["baseline"]+=1
        elif change_type:
            counts["changes"]+=1
            counts[f"severity_{severity}"]+=1
            detected=current["checked_at"]
            fingerprint=current.get("text_hash") or current.get("binary_hash") or current.get("result","")
            rid=stable_id("REV-",sid,change_type)
            eid=stable_id("WAT-",sid,change_type,fingerprint,detected)
            event={
                "event_id":eid,
                "detected_at":detected,
                "source_id":sid,
                "agent_ids":source.get("agent_ids",[]),
                "source_title":source.get("title"),
                "url":source.get("url"),
                "change_type":change_type,
                "severity":severity,
                "metrics":metrics,
                "previous_checked_at":previous.get("checked_at") if previous else None,
                "status":"needs_review",
                "policy":"Never auto-publish as product fact.",
            }
            events[eid]=event
            existing=queue.get(rid)
            if existing and existing.get("status")=="open":
                existing["last_detected"]=detected
                existing["occurrences"]=int(existing.get("occurrences",1))+1
                existing["severity"]=severity
                existing["latest_metrics"]=metrics
                existing["current"]={
                    "status_code":current.get("status_code"),
                    "final_url":current.get("final_url"),
                    "text_hash":current.get("text_hash"),
                    "simhash64":current.get("simhash64"),
                    "token_count":current.get("token_count"),
                    "text_sample":current.get("text_sample"),
                    "result":current.get("result"),
                    "error":current.get("error"),
                }
            else:
                queue[rid]={
                    "review_id":rid,
                    "status":"open",
                    "first_detected":detected,
                    "last_detected":detected,
                    "occurrences":1,
                    "severity":severity,
                    "change_type":change_type,
                    "source_id":sid,
                    "source_title":source.get("title"),
                    "url":source.get("url"),
                    "agent_ids":source.get("agent_ids",[]),
                    "previous": {
                        "status_code":previous.get("status_code") if previous else None,
                        "final_url":previous.get("final_url") if previous else None,
                        "text_hash":previous.get("text_hash") if previous else None,
                        "simhash64":previous.get("simhash64") if previous else None,
                        "token_count":previous.get("token_count") if previous else None,
                        "text_sample":previous.get("text_sample") if previous else None,
                    },
                    "current": {
                        "status_code":current.get("status_code"),
                        "final_url":current.get("final_url"),
                        "text_hash":current.get("text_hash"),
                        "simhash64":current.get("simhash64"),
                        "token_count":current.get("token_count"),
                        "text_sample":current.get("text_sample"),
                        "result":current.get("result"),
                        "error":current.get("error"),
                    },
                    "latest_metrics":metrics,
                    "editorial_action":"Open the official source, assess the change, then update data/agents.json only if a supported product fact changed.",
                }
            changes.append({"source_id":sid,"type":change_type,"severity":severity,"agents":source.get("agent_ids",[])})

        # Manual-only sources are intentionally excluded from automated fetches and are not failures.
        if current.get("result")=="manual_only":
            current["consecutive_failures"]=0
            current["source_title"]=source.get("title")
            current["agent_ids"]=source.get("agent_ids",[])
            new_states[sid]=current
        # Preserve last successful fingerprint across transient failures, while recording the latest check.
        elif not current.get("ok") and previous and previous.get("ok"):
            merged=dict(previous)
            merged["checked_at"]=current.get("checked_at")
            merged["last_check_result"]=current.get("result")
            merged["last_check_error"]=current.get("error")
            merged["last_check_status_code"]=current.get("status_code")
            merged["consecutive_failures"]=int(previous.get("consecutive_failures",0))+1
            # Availability failures are still queueable, but the good fingerprint stays as comparison baseline.
            new_states[sid]=merged
        else:
            current["consecutive_failures"]=0 if current.get("ok") else int((previous or {}).get("consecutive_failures",0))+1
            current["source_title"]=source.get("title")
            current["agent_ids"]=source.get("agent_ids",[])
            new_states[sid]=current

    # Ensure currently broken canonical sources (404/410) appear in the review queue,
    # even when they were already broken at the very first baseline run.
    source_by_id={s["source_id"]:s for s in sources}
    for sid,state in new_states.items():
        status_code=state.get("status_code") or state.get("last_check_status_code")
        if sid not in source_by_id or status_code not in {404,410}:
            continue
        source=source_by_id[sid]
        rid=stable_id("REV-",sid,"source_unavailable")
        if rid not in queue or queue[rid].get("status")!="open":
            detected=state.get("checked_at") or finished if 'finished' in locals() else now_iso()
            queue[rid]={
                "review_id":rid,
                "status":"open",
                "first_detected":detected,
                "last_detected":detected,
                "occurrences":1,
                "severity":"medium",
                "change_type":"source_unavailable",
                "source_id":sid,
                "source_title":source.get("title"),
                "url":source.get("url"),
                "agent_ids":source.get("agent_ids",[]),
                "previous":None,
                "current":{
                    "status_code":status_code,
                    "final_url":state.get("final_url"),
                    "result":state.get("result") or state.get("last_check_result"),
                    "error":state.get("error") or state.get("last_check_error"),
                },
                "latest_metrics":{"status_code":status_code,"baseline_health":True},
                "editorial_action":"Check whether the official source moved or was retired. Replace the source in data/agents.json only with a current authoritative source; do not infer any product change from the broken URL alone.",
            }
            eid=stable_id("WAT-",sid,"source_unavailable",str(status_code))
            events.setdefault(eid,{
                "event_id":eid,
                "detected_at":detected,
                "source_id":sid,
                "agent_ids":source.get("agent_ids",[]),
                "source_title":source.get("title"),
                "url":source.get("url"),
                "change_type":"source_unavailable",
                "severity":"medium",
                "metrics":{"status_code":status_code,"baseline_health":True},
                "previous_checked_at":None,
                "status":"needs_review",
                "policy":"Never auto-publish as product fact.",
            })

    # Retain inactive historical states but mark them.
    active_ids={s["source_id"] for s in sources}
    for sid,old in prior.items():
        if sid not in active_ids:
            inactive=dict(old)
            inactive["active"]=False
            new_states[sid]=inactive
    for sid,state in new_states.items():
        if sid in active_ids:
            state["active"]=True

    # Technical availability reviews are no longer actionable once a source is inactive
    # or explicitly classified as manual_only. Keep the history, but acknowledge the queue item.
    technical_change_types={"status_change","availability_change","availability_restored","source_unavailable"}
    acknowledged_at=now_iso()
    for item in queue.values():
        if item.get("status")!="open" or item.get("change_type") not in technical_change_types:
            continue
        sid=item.get("source_id")
        state=new_states.get(sid) or {}
        current_healthy=(
            state.get("ok") is True
            and state.get("last_check_result") not in {"http_error","network_error","error","robots_disallowed"}
        )
        recovered_technical_status=(
            item.get("change_type") in {"status_change","availability_restored"}
            and current_healthy
        )
        if sid in manual_source_ids or sid not in active_ids or recovered_technical_status:
            item["status"]="acknowledged"
            item["acknowledged_at"]=acknowledged_at
            if sid in manual_source_ids:
                item["resolution"]="Source is explicitly manual_only; automated availability review is not actionable."
            elif sid not in active_ids:
                item["resolution"]="Source is inactive; automated availability review is no longer actionable."
            else:
                item["resolution"]="Source is healthy again; technical recovery acknowledged without asserting a product change."

    open_items=[i for i in queue.values() if i.get("status")=="open"]
    open_items.sort(key=lambda x:({"high":0,"medium":1,"low":2}.get(x.get("severity"),3),x.get("first_detected","")))

    finished=now_iso()
    summary={
        "name":"AgentenWache",
        "version":VERSION,
        "started_at":started,
        "finished_at":finished,
        "source_registry":"_agentengraph/sources.json",
        "active_sources":len(sources),
        "hosts":len(by_host),
        "counts":dict(sorted(counts.items())),
        "open_review_items":len(open_items),
        "changes_this_run":changes,
        "principle":"Monitoring detects source changes only. No detected change becomes an AgentenIndex product fact without editorial verification.",
    }

    dump(STATE_FILE,{"watch_version":VERSION,"updated_at":finished,"states":sorted(new_states.values(),key=lambda x:x["source_id"])})
    dump(QUEUE_FILE,{"watch_version":VERSION,"updated_at":finished,"open_count":len(open_items),"items":sorted(queue.values(),key=lambda x:x["review_id"])})
    dump(EVENT_FILE,{"watch_version":VERSION,"updated_at":finished,"events":sorted(events.values(),key=lambda x:(x.get("detected_at",""),x["event_id"]))})
    dump(SUMMARY_FILE,summary)
    print(json.dumps({"status":"AGENTENWACHE_RUN_COMPLETE",**summary},ensure_ascii=False))

if __name__=="__main__":
    main()
