"""Validate every full attempt, frozen binary, exact observation pair, and raw archive."""
import csv,hashlib,json,re,subprocess,tarfile
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def main():
    a=json.loads((ROOT/'analysis.json').read_text());idx={(r['study'],r['arm']):r for r in a['runs']}
    manifests=list(ROOT.glob('*-manifest.json'))
    assert a['attempts']==sum(len(json.loads(p.read_text())['tasks']) for p in manifests)
    assert a['attempts']==70 and a['completed']==70 and not a['failures']
    assert all(r['seed']==301 for r in a['runs'])
    stable=[idx['allreduce_dp2','homa_order_homa_stable_'+s] for s in ['a','b','small','large']]
    stable.append(idx['allreduce_dp2','batch_dp2_homa'])
    stable.append(idx['allreduce_dp2','budget_dp2_homa'])
    assert len({r['fct_sha256'] for r in stable})==1
    assert all(r['metrics']==stable[0]['metrics'] for r in stable)
    legacy=[idx['allreduce_dp2','homa_order_homa_legacy_'+s] for s in ['a','b','small','large']]
    assert len({r['fct_sha256'] for r in legacy})==3
    # Optional GUARD code off/on controls are independent of source-layout changes.
    old=json.loads((ROOT.parent/'guard_timeout_20260921/analysis.json').read_text())
    oi={(r['study'],r['arm']):r for r in old['runs']}
    cross=[]
    for parent in ['shared','joint32']:
        new=idx['allreduce_dp2','batch_dp2_'+parent+'_cursor'];prev=oi['allreduce_dp2','cursor_'+parent+'_cursor']
        assert new['fct_sha256']==prev['fct_sha256'] and new['metrics']==prev['metrics']
        cross.append(dict(current=new['key'],previous=prev['key'],all_metrics_identical=True))
    for parent in ['shared','joint32','shared_l10']:
        new=idx['allreduce_dp2','budget_dp2_'+parent+'_cursor'];prev=idx['allreduce_dp2','batch_dp2_'+parent+'_cursor']
        assert new['fct_sha256']==prev['fct_sha256'] and new['metrics']==prev['metrics']
        cross.append(dict(current=new['key'],previous=prev['key'],all_metrics_identical=True))
    diag=[]
    for variant,tracearm in [('cursor','batch_trace_shared_l10_cursor_trace'),('batch','batch_dp2_shared_l10_batch_trace'),('budget','budget_dp2_shared_l10_budget_trace')]:
        phase='budget_dp2' if variant=='budget' else 'batch_dp2'
        x=idx['allreduce_dp2',phase+'_shared_l10_'+variant];y=idx['allreduce_dp2',tracearm]
        assert x['fct_sha256']==y['fct_sha256'] and x['metrics']==y['metrics']
        rec=json.loads((ROOT/'runs'/y['key']/'result.json').read_text())
        path=next(Path(y['output_dir']).glob('*controller.csv'))
        lines=path.read_text().splitlines();footer=[v for v in lines if v.startswith('#')]
        attempted,written,truncated=map(int,re.findall(r'\d+',footer[0]));sampled=int(re.search(r'sampled_out=(\d+)',footer[1]).group(1))
        assert attempted==written+sampled and truncated==0
        rows=list(csv.DictReader(v for v in lines if not v.startswith('#')));assert len(rows)==written
        completed=[v for v in rows if v['event_type']=='complete'];counts=Counter(int(v['flow_id']) for v in completed)
        assert set(counts)==set(range(1280)) and all(n==1 for n in counts.values())
        inp=np.loadtxt(rec['flow'],skiprows=1);fct=np.loadtxt(y['fct_file'],dtype=np.int64)
        for v in completed:
            fid=int(v['flow_id']);f=inp[fid]
            match=fct[(fct[:,0]==f[0])&(fct[:,1]==f[1])&(fct[:,4]==f[3])&(abs(fct[:,5]-round(f[4]*1e9))<=2)]
            assert len(match)==1 and int(v['time_ns'])==int(match[0,5]+match[0,6])
        timeouts=[v for v in rows if v['event_type']=='timeout_probe'];assert len(timeouts)==y['metrics']['timeout_recoveries']
        classified=[]
        for v in timeouts:
            outstanding=int(v['snd_nxt'])-int(v['snd_una']);assert outstanding>=0
            assert (v['binding']=='empty_flight')==(outstanding==0)
            classified.append(dict(flow_id=int(v['flow_id']),outstanding_bytes=outstanding,
                next_avail_delta_ns=int(v['next_avail_ns'])-int(v['time_ns']),rate_bps=int(v['final_rate_bps']),row=v))
        protocol=defaultdict(lambda:dict(packets=0,serialized_bytes=0));hosts=set()
        for v in csv.DictReader(Path(str(path)+'.wire.csv').open()):
            node=int(v['node_id']);proto=int(v['l3_protocol']);assert 0<=node<16;hosts.add(node)
            for k in ['packets','serialized_bytes']:protocol[proto][k]+=int(v[k])
        assert hosts==set(range(16)) and protocol[17]['packets']>=32000000
        assert protocol[249]['packets']==y['metrics']['grants']
        diag.append(dict(variant=variant,trace_key=y['key'],trace_neutral=True,trace_rows=written,cap_omissions=truncated,
            completed_events=len(completed),timeouts=classified,protocol=dict(protocol)))
    (ROOT/'diagnostic_analysis.json').write_text(json.dumps(diag,indent=2)+'\n')
    wt=subprocess.check_output(['git','-C','/home/gengjiayao/ict/guard','worktree','list','--porcelain'],text=True)
    repos={}
    for block in wt.strip().split('\n\n'):
        fields=dict(l.split(' ',1) for l in block.splitlines() if ' ' in l)
        if 'HEAD' in fields:repos[fields['HEAD']]=Path(fields['worktree'])
    for p in manifests:
        m=json.loads(p.read_text());repo=repos[m['source_commit']];snapshot=ROOT/'harness_snapshots'/p.name.replace('-manifest.json','')
        assert not subprocess.check_output(['git','diff','HEAD','--name-only'],cwd=repo,text=True).strip()
        for name,digest in m['harness_hashes'].items():assert sha(snapshot/Path(name).relative_to('scripts'))==digest
        for name,digest in m['hashes'].items():assert sha(repo/name)==digest
        for name,digest in m['topology_hashes'].items():assert sha(repo/'config'/(name+'.txt'))==digest
        for task in m['tasks']:assert sha(Path(task['flow']))==task['flow_sha256']
    archives=json.loads((ROOT/'raw_index.json').read_text());assert len(archives)==a['attempts']
    for name,e in archives.items():
        p=ROOT/name;assert sha(p)==e['sha256']
        with tarfile.open(p) as t:
            rec=json.load(t.extractfile('record/result.json'))
            assert rec==json.loads((ROOT/'runs'/e['key']/'result.json').read_text())
            for member in t.getmembers():
                if member.name.startswith('raw/') and member.isfile():
                    h=hashlib.sha256();stream=t.extractfile(member)
                    for b in iter(lambda:stream.read(1048576),b''):h.update(b)
                    assert h.hexdigest()==sha(Path(rec['output_dir'])/Path(member.name).name)
    checks=dict(status='evidence verified; universal performance objective remains active',attempts=a['attempts'],completed=a['completed'],
        homa_stable_fct_sha256=stable[0]['fct_sha256'],homa_stable_identical_runs=len(stable),homa_legacy_variants=3,
        exact_cross_build_guard_pairs=cross,trace_pairs=3,runs_with_drops=sum(r['metrics']['drops']>0 for r in a['runs']),source_build_input_harness_archive_hashes='verified',independent_confirmation=False,
        source_commits={p.name:json.loads(p.read_text())['source_commit'] for p in manifests})
    (ROOT/'validation_checks.json').write_text(json.dumps(checks,indent=2)+'\n')
    print('PASS: all70 original runs, six exact Homa matches, three trace pairs and all frozen raw evidence verified')
if __name__=='__main__':main()
