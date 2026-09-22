"""Evidence integrity and instrumentation neutrality, not a dominance gate."""
import hashlib,json,tarfile,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 a=json.loads((ROOT/'analysis.json').read_text());assert not a['failures'];assert a['completed']==a['attempts']
 traces=json.loads((ROOT/'trace_analysis.json').read_text())
 for r in traces:
  assert r['complete_events']==1280
  attempted,written,omitted=map(int,re.findall(r'\d+',r['footer'][0]))
  sampled=int(re.search(r'sampled_out=(\d+)',r['footer'][1]).group(1))
  assert attempted-written==omitted==sampled, 'row-budget truncation'
 pairs=[]
 for left,right in [('share128_window1','shared_trace'),('startup','startup_trace')]:
  rows=[next(v for v in a['runs'] if v['arm']=='stable_'+arm) for arm in [left,right]]
  assert rows[0]['fct_sha256']==rows[1]['fct_sha256'], 'instrumentation changes FCT'
  assert rows[0]['metrics']==rows[1]['metrics'], 'instrumentation changes summarized metrics'
  pairs.append(dict(profiles=[left,right],fct_sha256=rows[0]['fct_sha256'],identical_all_metrics=True))
 archives=json.loads((ROOT/'raw_index.json').read_text())
 assert len(archives)==a['attempts']
 for name,entry in archives.items():
  p=ROOT/name;assert sha(p)==entry['sha256']
  with tarfile.open(p) as f:
   rec=json.load(f.extractfile('record/result.json'))
   assert rec==json.loads((ROOT/'runs'/entry['key']/'result.json').read_text())
   for m in f.getmembers():
    if m.name.startswith('raw/') and m.isfile():
     digest=hashlib.sha256(f.extractfile(m).read()).hexdigest()
     assert digest==sha(Path(rec['output_dir'])/Path(m.name).name)
 report=dict(status='all recorded evidence and stable-build trace-neutrality verified; goal remains active',
  attempts=a['attempts'],source_commits={p.name:json.loads(p.read_text())['source_commit'] for p in ROOT.glob('*-manifest.json')},
  trace_sets=len(traces),complete_events_per_trace=1280,no_row_cap_omissions=True,
  trace_neutral_pairs=pairs,verified_archives=len(archives),independent_confirmation=False)
 (ROOT/'validation_checks.json').write_text(json.dumps(report,indent=2)+'\n')
 print('PASS:',a['attempts'],'complete attempts;',len(traces),'complete trace sets; two exact trace/no-trace pairs; goal active')
if __name__=='__main__':main()
