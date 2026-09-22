"""Check reproducibility and archive integrity; never mark performance goal achieved."""
import hashlib,json,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()
def main():
 a=json.loads((ROOT/'analysis.json').read_text());assert not a['failures'];assert a['completed']==a['attempts']
 pairs=[]
 for left,right in [('dp2_shared','dp2_shared_trace'),('dp2_recovery8','dp2_recovery8_trace'),('peer_dp2_startup_wide','peer_dp2_startup_peer')]:
  rows=[next(r for r in a['runs'] if r['arm']==name and r['study']=='allreduce_dp2') for name in [left,right]]
  assert rows[0]['fct_sha256']==rows[1]['fct_sha256'], (left,right,'FCT')
  assert rows[0]['metrics']==rows[1]['metrics'], (left,right,'metrics')
  pairs.append(dict(arms=[left,right],fct_sha256=rows[0]['fct_sha256'],all_metrics_identical=True))
 trace=json.loads((ROOT/'trace_analysis.json').read_text());assert len(trace)==2
 for t in trace:assert t['complete_events']==1280 and t['cap_truncations']==0
 for p in ROOT.glob('*-manifest.json'):
  m=json.loads(p.read_text());snap=ROOT/'harness_snapshots'/p.name.replace('-manifest.json','')
  for name,digest in m['harness_hashes'].items():assert sha(snap/Path(name).relative_to('scripts'))==digest
 archives=json.loads((ROOT/'raw_index.json').read_text());assert len(archives)==a['attempts']
 for name,e in archives.items():
  p=ROOT/name;assert sha(p)==e['sha256']
  with tarfile.open(p) as t:
   r=json.load(t.extractfile('record/result.json'));assert r==json.loads((ROOT/'runs'/e['key']/'result.json').read_text())
   for member in t.getmembers():
    if member.name.startswith('raw/') and member.isfile():
     assert hashlib.sha256(t.extractfile(member).read()).hexdigest()==sha(Path(r['output_dir'])/Path(member.name).name)
 report=dict(status='all recorded development evidence verified; full goal remains active',attempts=a['attempts'],complete=a['completed'],
  identity_pairs=pairs,complete_traces=2,complete_events_per_trace=1280,archived_attempts=len(archives),
  harness_round_snapshots='all original hashes verified',independent_confirmation=False,
  source_commits={p.name:json.loads(p.read_text())['source_commit'] for p in ROOT.glob('*-manifest.json')})
 (ROOT/'validation_checks.json').write_text(json.dumps(report,indent=2)+'\n')
 print('PASS:',a['attempts'],'complete runs; three exact pairs; two full traces; all archives and harness snapshots; goal active')
if __name__=='__main__':main()
