#!/usr/bin/env python3
"""Integration test: a future field change must close old state and emit history."""
from pathlib import Path
import json
import shutil
import subprocess
import tempfile
from datetime import date, timedelta

ROOT=Path(__file__).resolve().parents[2]

with tempfile.TemporaryDirectory(prefix="agentengraph-test-") as td:
    dst=Path(td)/"repo"
    shutil.copytree(ROOT,dst,ignore=shutil.ignore_patterns(".git","node_modules"))

    build=dst/".github/scripts/build-agentengraph.py"
    validate=dst/".github/scripts/validate-agentengraph.py"

    # Establish baseline from current source.
    subprocess.run(["python",str(build)],cwd=dst,check=True,capture_output=True,text=True)
    subprocess.run(["python",str(validate)],cwd=dst,check=True,capture_output=True,text=True)

    before=json.loads((dst/"_agentengraph/assertions.json").read_text(encoding="utf-8"))
    before_events=json.loads((dst/"_agentengraph/events.json").read_text(encoding="utf-8"))

    data_path=dst/"data/agents.json"
    data=json.loads(data_path.read_text(encoding="utf-8"))
    baseline_date=date.fromisoformat(data["updated"])
    test_date=(baseline_date+timedelta(days=1)).isoformat()
    data["updated"]=test_date
    target=data["agents"][0]
    old_summary=target["summary"]
    target["summary"]=old_summary+" [HISTORY-TEST]"
    target["last_verified"]=test_date
    data_path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    subprocess.run(["python",str(build)],cwd=dst,check=True,capture_output=True,text=True)
    subprocess.run(["python",str(validate)],cwd=dst,check=True,capture_output=True,text=True)

    after=json.loads((dst/"_agentengraph/assertions.json").read_text(encoding="utf-8"))
    after_events=json.loads((dst/"_agentengraph/events.json").read_text(encoding="utf-8"))

    aid=target["profile_id"]
    old=[a for a in after["assertions"] if a["agent_id"]==aid and a["path"]=="description.summary" and a["value"]==old_summary]
    new=[a for a in after["assertions"] if a["agent_id"]==aid and a["path"]=="description.summary" and a["value"]==target["summary"]]
    changes=[e for e in after_events["events"] if e["agent_id"]==aid and e.get("event_type")=="field_change" and e.get("path")=="description.summary" and e.get("date")==test_date]

    assert old and old[-1]["valid_to"]==test_date, old
    assert new and new[-1]["valid_from"]==test_date and new[-1]["valid_to"] is None, new
    assert changes, "No field_change event generated"
    assert len(after["assertions"]) > len(before["assertions"])
    assert len(after_events["events"]) > len(before_events["events"])

print("AGENTENGRAPH_HISTORY_TEST_OK")
