"""Finish derived artifacts only after every frozen simulation returns."""
import json,subprocess,sys,time
from pathlib import Path
from campaign import ROOT
m=json.loads((ROOT/'manifest.json').read_text())
while True:
 records=[ROOT/'runs'/t['key']/'result.json' for t in m['tasks']]
 if all(p.exists() for p in records):break
 time.sleep(15)
assert all(json.loads(p.read_text())['status']=='completed' for p in records)
for cmd in [[sys.executable,'scripts/analyze.py'],[sys.executable,'scripts/make_results.py'],[sys.executable,'scripts/plot.py','--final'],[sys.executable,'scripts/archive_raw.py'],['bash','paper/build.sh'],['bash','paper/build.sh','supplement'],[sys.executable,'scripts/final_gate.py']]:
 print('RUN',cmd,flush=True);subprocess.run(cmd,cwd=ROOT,check=True)
print('READY_FOR_FINAL_REVIEW',flush=True)
