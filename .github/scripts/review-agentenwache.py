#!/usr/bin/env python3
"""Update one AgentenWache review item after human/editorial inspection."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import json
import sys

ROOT=Path(__file__).resolve().parents[2]
QUEUE=ROOT/"_agentenwache"/"review-queue.json"
SYSTEM_SCHEMA_PATH=ROOT/"data"/"agent-system-schema.json"
SYSTEM_SCHEMA=json.loads(SYSTEM_SCHEMA_PATH.read_text(encoding="utf-8")) if SYSTEM_SCHEMA_PATH.exists() else {"watch_change_categories":[]}
SYSTEM_SIGNALS=sorted(set(SYSTEM_SCHEMA.get("watch_change_categories") or []))

VALID={"reviewed_no_product_change","applied_to_agents","dismissed_noise","acknowledged"}

def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")

parser=argparse.ArgumentParser()
parser.add_argument("--id",required=True,dest="review_id")
parser.add_argument("--status",required=True,choices=sorted(VALID))
parser.add_argument("--note",required=True)
parser.add_argument("--system-signal",choices=SYSTEM_SIGNALS,default=None,help="Optional, human-reviewed system change category.")
args=parser.parse_args()

if not QUEUE.exists():
    raise SystemExit("AgentenWache queue does not exist")

doc=json.loads(QUEUE.read_text(encoding="utf-8"))
found=None
for item in doc.get("items",[]):
    if item.get("review_id")==args.review_id:
        found=item
        break
if not found:
    raise SystemExit(f"Unknown review id: {args.review_id}")

found["status"]=args.status
found["reviewed_at"]=now_iso()
found["review_note"]=args.note
if args.system_signal:
    found["system_signal"]=args.system_signal
doc["updated_at"]=now_iso()
doc["open_count"]=sum(1 for i in doc.get("items",[]) if i.get("status")=="open")
QUEUE.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

print(json.dumps({
    "status":"AGENTENWACHE_REVIEW_UPDATED",
    "review_id":args.review_id,
    "review_status":args.status,
    "system_signal":args.system_signal,
    "open_count":doc["open_count"],
},ensure_ascii=False))
