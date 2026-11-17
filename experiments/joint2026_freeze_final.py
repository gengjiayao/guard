from pathlib import Path
import hashlib,json,subprocess,sys,datetime
w=Path('/home/gengjiayao/ict/guard-joint-20261117');ref=Path('/home/gengjiayao/ict/guard-fixed-reference-20261117');main=Path('/home/gengjiayao/ict/guard')
candidate='predict64_no_progress'
def read(p):return json.loads(p.read_text())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def fingerprint(repo):return {str(p.relative_to(repo)):sha(p) for p in [repo/'build/scratch/network-load-balance',*sorted((repo/'build').glob('*.so'))]}
assert not subprocess.check_output(['git','status','--porcelain'],cwd=w,text=True).strip()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ref,text=True).strip()=='6c438d7c7223d698bc2bea3333e8eac271fe002c'
for repo in [w,ref]:
 for p in (repo/'experiments/results').glob('joint_*/pid.txt'):
  proc=Path('/proc')/p.read_text().strip()/'cmdline'
  assert not proc.exists() or b'runner.py' not in proc.read_bytes() and b'joint2026_parallel' not in proc.read_bytes(),str(p)+' still running'
dev=read(w/'experiments/results/joint_precise_int_development/comparison.json');assert dev['complete']
rows=[r for r in dev['summary'] if r['arm']==candidate];assert len(rows)==6
assert all(r['n']==3 and r['p95_mean_reduction']>10 and r['p99_mean_reduction']>10 for r in rows)
for name in ['joint_probe16a','joint_probe16b','joint_probe17a','joint_probe17b']:
 plan=read(w/'experiments/results'/name/'plan.json');assert plan['runtime']==fingerprint(w)
 audit=read(w/'experiments/results'/name/'int-integrity-audit.json');assert len(audit)==len(plan['inputs'])*len(plan['variants'])
 assert all(r['guard_scheduled_acks_without_int']==0 for r in audit)
original=read(main/'experiments/results/generalize_frozen_runtime/manifest.json')['runtime'];assert fingerprint(ref)==original
cal=read(ref/'experiments/results/joint_reference_calibration/results.json');assert len(cal)==6
old={(r['case'],r['seed']):r for r in read(main/'experiments/results/generalize_frozen_baseline/results.json') if r['arm']=='homa'}
calibration=[]
for r in cal:
 b=old[(r['case'],r['seed'])];assert r['status']=='completed' and r['input_sha256']==b['input_sha256'] and r['completed']==b['completed']
 calibration.append({'case':r['case'],'original':b['tails']['all'],'restored':r['tails']['all']})
for n in [2,3]:
 extra=read(ref/f'experiments/results/joint_reference_calibration_repeat{n}/results.json');assert len(extra)==1
 r=extra[0];b=old[(r['case'],r['seed'])];assert r['status']=='completed' and r['input_sha256']==b['input_sha256']
 calibration.append({'case':r['case'],'repeat':n,'original':b['tails']['all'],'restored':r['tails']['all']})
chosen=read(w/'experiments/results/joint_probe16b/variants.json')[candidate]
protocol={'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'guard_controller_git':subprocess.check_output(['git','rev-parse','HEAD'],cwd=w,text=True).strip(),'baselines_source_git':'6c438d7c7223d698bc2bea3333e8eac271fe002c','guard_runtime':fingerprint(w),'baselines_runtime':original,'variants':{'guard':chosen},'loads':[50,70,80],'workloads':['WebSearch','AliStorage2019'],'duration_seconds':{'WebSearch':.06,'AliStorage2019':.02},'warmup_fraction':.25,'validation_inputs':list(range(91001,91011)),'runs':360,'baseline_variants':{'hpcc':{'cc':'hpcc'},'dcqcn':{'cc':'dcqcn'},'homa':{'cc':'homa'},'homa_repeat2':{'cc':'homa'},'homa_repeat3':{'cc':'homa'}},'cdf_hashes':{c:sha(w/'traffic_gen'/f'{c}.txt') for c in ['WebSearch','AliStorage2019']},'primary':'BOTH per-run overall P95 and overall P99 FCT, all message sizes; mean paired percentage reduction against the original fixed Homa; all twelve workload/load/metric means must exceed 10%.','secondary':'All HPCC/DCQCN comparisons and confidence intervals retained. Two additional Homa executions per input provide fastest-of-three sensitivity checks for BOTH P95 and P99. No size-bin substitution, rerun selection, or pooling repetitions.','policy':'Source, runtime, one common configuration and analysis frozen before generation or inspection of the ten reserved final inputs. All failures, all input flows and all cases retained. Tuning after final validation requires new independent inputs.','development_evidence':['joint_probe16a','joint_probe16b','joint_probe17a','joint_probe17b'],'selected_development_means':rows,'selection_reason':'Common profile with both metrics above 10% in every development case; precise ACK-aligned INT and periodic demand reallocation without redundant per-BDP grant refresh.','baseline_calibration':calibration,'baseline_calibration_note':'Identical source, 63 runtime hashes and inputs reproduce most original tails; WebSearch high-load Homa has process-to-process differences. The original StallCheck traverses a pointer-keyed unordered_map, a suspected source of recovery-order variability. Do not alter the baseline or substitute reruns. Primary Homa is the first prespecified Homa run; two extra runs per final input are all retained for a conservative fastest-of-three sensitivity check.','cdf_source':{'WebSearch':'https://github.com/alibaba-edu/High-Precision-Congestion-Control/blob/master/traffic_gen/WebSearch_distribution.txt','AliStorage2019':'https://github.com/alibaba-edu/High-Precision-Congestion-Control/blob/master/traffic_gen/AliStorage2019.txt'},'analysis_sha256':sha(w/'experiments/joint2026_final_audit.py'),'native_correctness_tests':['guard_predicted_int','guard_ack_aligned_int','guard_compact_short','guard_dynamic_priority']}
# Inputs must not exist anywhere in this round before this freeze.
for repo in [w,ref]:
 for p in (repo/'experiments/results').glob('joint_*/plan.json'):
  assert not set(read(p)['seeds']) & set(protocol['validation_inputs']),str(p)
roots=[(w,'joint_final_guard','guard',8),(ref,'joint_final_baselines','baselines',16)]
for repo,name,_,_ in roots:assert not (repo/'experiments/results'/name).exists()
p=w/'experiments/joint2026_final_protocol.json';assert not p.exists();p.write_text(json.dumps(protocol,indent=2)+'\n')
subprocess.run(['git','add','experiments/joint2026_final_protocol.json'],cwd=w,check=True)
subprocess.run(['git','commit','-m','experiments: freeze joint P95/P99 profile before independent validation'],cwd=w,check=True)
source=(w/'experiments/joint2026_parallel.py').read_text()
assert source.count('REPO=Path(__file__).resolve().parents[1]')==1
assert source.count('assert 1<=a.jobs<=8')==1
for repo,name,label,jobs in roots:
 root=repo/'experiments/results'/name;root.mkdir(parents=True)
 runner=root/'frozen_runner.py'
 runner.write_text(source.replace('REPO=Path(__file__).resolve().parents[1]',f'REPO=Path({str(repo)!r})').replace('assert 1<=a.jobs<=8','assert 1<=a.jobs<=16'))
 (root/'protocol.json').write_text(p.read_text())
 variants=protocol['variants'] if label=='guard' else protocol['baseline_variants']
 (root/'variants.json').write_text(json.dumps(variants,indent=2)+'\n')
 args=[sys.executable,str(runner),'--root',str(root),'--variants',str(root/'variants.json'),'--arms',','.join(variants),'--seeds',','.join(map(str,protocol['validation_inputs'])),'--loads','50,70,80','--cdfs','WebSearch,AliStorage2019','--web-duration','.06','--ali-duration','.02','--jobs',str(jobs)]
 subprocess.run(args+['--prepare-only'],cwd=repo,check=True)
 with (root/'campaign.log').open('w') as log:proc=subprocess.Popen(args,cwd=repo,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 (root/'pid.txt').write_text(str(proc.pid)+'\n');print(label,root,proc.pid,60*len(variants),'planned runs',flush=True)
