import json,hashlib,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def main():
 a=json.loads((ROOT/'analysis.json').read_text());assert a['attempts']==a['completed']==65 and not a['failures']
 manifests={p.stem.removesuffix('-manifest'):json.loads(p.read_text()) for p in ROOT.glob('*-manifest.json')}
 assert sum(len(m['tasks']) for m in manifests.values())==65
 commits={}
 for phase,m in manifests.items():
  repo=Path('/home/gengjiayao/ict/'+('guard-utiltrace' if phase=='activity' else 'guard-utilfeedback' if phase.startswith('feedback') else 'guard-utilwidth'))
  assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==m['source_commit']
  assert not subprocess.check_output(['git','diff','HEAD','--name-only'],cwd=repo,text=True).strip()
  commits[phase]=m['source_commit']
  for name,digest in m['hashes'].items():assert sha(repo/name)==digest,name
  for name,digest in m['harness_hashes'].items():assert sha(ROOT/'harness_snapshots'/phase/Path(name).relative_to('scripts'))==digest,name
  for name,digest in m['topology_hashes'].items():assert sha(repo/'config'/(name+'.txt'))==digest,name
  for t in m['tasks']:
   assert sha(t['flow'])==t['flow_sha256']
   r=json.loads((ROOT/'runs'/t['key']/'result.json').read_text());assert r['status']=='completed'
   assert sha(r['config'])==r['config_sha256']
 index=json.loads((ROOT/'raw_index.json').read_text());assert len(index)==65
 for name,v in index.items():
  path=ROOT/name;assert sha(path)==v['sha256']
  record=json.loads((ROOT/'runs'/v['key']/'result.json').read_text());out=Path(record['output_dir'])
  with tarfile.open(path) as tar:
   for entry in tar:
    base=out if entry.name.startswith('raw/') else ROOT/'runs'/v['key']
    raw=tar.extractfile(entry).read();assert hashlib.sha256(raw).hexdigest()==sha(base/Path(entry.name).name)
 for file in ['grant_diagnosis.json','adaptive_grant_diagnosis.json']:
  for r in json.loads((ROOT/file).read_text()).values():assert r['trace_neutral'] and not r['cap_omissions'] and not r['unmatched_received'] and not r['unmatched_sent']
 for file in ['activity_analysis.json','adaptive_activity_analysis.json']:
  for r in json.loads((ROOT/file).read_text()).values():assert r['data_conservation'] and not r['controller_cap_omissions']
 d=json.loads((ROOT/'width_comparison.json').read_text())
 for r in d['pairs'].values():assert r['k1_cross_build_exact_fct'] and r['k1_cross_build_exact_all_metrics']
 for r in json.loads((ROOT/'width_trace_validation.json').read_text()).values():assert r['all_transitions_verified'] and r['trace_neutral_counts']
 for r in json.loads((ROOT/'feedback_validation.json').read_text()).values():assert r['trace_neutral'] and r['all_gate_checks_verified']
 assert all(not r['metrics']['drops'] and not r['metrics']['timeout_recoveries'] for r in a['runs'])
 result=dict(completed=65,failed_simulations=0,failed_initial_builds=1,source_commits=commits,source_build_input_harness_config_archive_hashes='verified',paired_complete_fct_and_metrics='exact for all observation pairs; unchanged K1 exact across sources',goal_status='active',independent_confirmation=False)
 (ROOT/'validation_checks.json').write_text(json.dumps(result,indent=2)+'\n');print('Verified all 65 complete runs, pairs, actual feedback gates, all archive/source hashes')
if __name__=='__main__':main()
