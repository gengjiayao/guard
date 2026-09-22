"""Resume only this campaign's paused schedulers after delegated cells finish."""
import os,signal,time,json
from pathlib import Path
from campaign import ROOT
checks={3577920:[f'ali50-s303-{a}' for a in ['no_oflm','no_selective','no_release']],3572514:[f'ali50-s304-{a}' for a in ['no_selective','no_release']],3571810:['ali50-s305-no_release']}
m=json.loads((ROOT/'manifest.json').read_text())
checks[3567472]=[t['key'] for t in m['tasks'] if t['study'] in ['ali30','ali50'] and t['seed'] in [303,304,305]]
while checks:
 for pid,keys in list(checks.items()):
  if not all((ROOT/'runs'/k/'result.json').exists() for k in keys):continue
  cmd=Path(f'/proc/{pid}/cmdline').read_bytes()
  if b'campaign.py' not in cmd:raise RuntimeError('PID no longer belongs to campaign')
  os.kill(pid,signal.SIGCONT);print('RESUMED',pid,time.strftime('%H:%M:%S'),flush=True);del checks[pid]
 if checks:time.sleep(15)
