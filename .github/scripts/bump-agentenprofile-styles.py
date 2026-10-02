#!/usr/bin/env python3
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
changed=[]
for path in sorted((ROOT/"agenten").glob("*/index.html")):
    text=path.read_text(encoding="utf-8")
    new=re.sub(r'/assets/styles\.css\?v=[0-9.]+','/assets/styles.css?v=8.7.3',text)
    if new!=text:
        path.write_text(new,encoding="utf-8")
        changed.append(str(path.relative_to(ROOT)))
print(f"Updated {len(changed)} AgentenProfile")
for p in changed[:10]:
    print("-",p)
