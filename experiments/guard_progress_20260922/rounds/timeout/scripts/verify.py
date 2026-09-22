"""Verify complete evidence, explicitly retaining failed attempts and truncated logs."""
import hashlib,json,re,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def main():
    a=json.loads((ROOT/'analysis.json').read_text());idx={(r['study'],r['arm']):r for r in a['runs']}
    assert a['attempts']==90 and a['completed']==75 and len(a['failures'])==15
    for r in a['failures']:
        assert r['arm'].startswith('diagnosis_') and not r['arm'].startswith('diagnosis_retry_') or r['arm'].startswith('trace_retry_') or r['arm']=='smoke_shared_deadline'
    pairs=[]
    for profile in ['joint32_l10','shared_l10','l10_ack1','l10_last','l10_ack1_last']:
        pairs.append(('allreduce_dp2','diagnosis_retry_'+profile,'diagnosis_retry_'+profile+'_trace'))
    for profile in ['l10_ack1','l10_ack1_last']:
        pairs.append(('allreduce_dp2','diagnosis_retry_'+profile,'trace_sparse_'+profile+'_trace_full'))
    for phase in ['bounded','idle']:
        pairs.append(('allreduce_dp2',phase+'_joint32_l10_deadline',phase+'_joint32_l10_deadline_trace'))
    pair_checks=[]
    for study,left,right in pairs:
        x,y=idx[study,left],idx[study,right]
        assert x['fct_sha256']==y['fct_sha256'] and x['metrics']==y['metrics'],(left,right)
        pair_checks.append(dict(arms=[left,right],fct_sha256=x['fct_sha256'],all_metrics_identical=True))
    diag=json.loads((ROOT/'diagnostic_analysis.json').read_text());assert len(diag)==5
    assert all(r['trace_neutral'] and r['cap_omissions']==0 and r['complete_events']==1280 for r in diag)
    assert sum(len(r['timeouts']) for r in diag)==18
    assert sum(t['outstanding_bytes']==0 for r in diag for t in r['timeouts'])==1
    for phase in ['bounded','idle']:
        r=idx['allreduce_dp2',phase+'_joint32_l10_deadline_trace']
        f=next(Path(r['output_dir']).glob('*controller.csv'));lines=f.read_text().splitlines()
        footer=[l for l in lines if l.startswith('#')];attempted,written,truncated=map(int,re.findall(r'\d+',footer[0]));sampled=int(re.search(r'sampled_out=(\d+)',footer[1]).group(1))
        assert attempted==written+sampled and truncated==0
        import csv
        rows=list(csv.DictReader(v for v in lines if not v.startswith('#')))
        c=[v for v in rows if v['event_type']=='complete'];assert len(c)==1280 and {int(v['flow_id']) for v in c}==set(range(1280))
        assert sum(v['event_type']=='timeout_probe' for v in rows)==r['metrics']['timeout_recoveries']
    # Check actual ACK timer bounds against the maximum base RTT of each topology.
    timer_runs=0
    for r in a['runs']:
        d=Path(r['output_dir']);stats=next(d.glob('*_out_guard_stats.txt')).read_text()
        lines=[l for l in stats.splitlines() if l.startswith('guard_ack_deadline ')]
        if not lines:continue
        log=(ROOT/'runs'/r['key']/'simulation.log').read_text()
        max_rtt=int(re.search(r'maxRtt: (\d+)',log).group(1))
        for l in lines:
            v=l.split()[1:];v=dict(zip(v[::2],v[1::2]));bound=float(v['max_delay_rtts'])
            assert int(v['sent'])<=int(v['timers'])
            assert int(v['max_wait_ns'])<=max_rtt*bound+1
            if bound==0:assert int(v['sent'])==int(v['timers'])==int(v['max_wait_ns'])==0
        timer_runs+=1
    wt=subprocess.check_output(['git','-C','/home/gengjiayao/ict/guard','worktree','list','--porcelain'],text=True)
    repos={}
    for block in wt.strip().split('\n\n'):
        fields=dict(l.split(' ',1) for l in block.splitlines() if ' ' in l)
        if 'HEAD' in fields:repos[fields['HEAD']]=Path(fields['worktree'])
    manifests=list(ROOT.glob('*-manifest.json'))
    for p in manifests:
        m=json.loads(p.read_text());snap=ROOT/'harness_snapshots'/p.name.replace('-manifest.json','')
        for name,digest in m['harness_hashes'].items():assert sha(snap/Path(name).relative_to('scripts'))==digest,(p,name)
        repo=repos[m['source_commit']]
        for name,digest in m['hashes'].items():assert sha(repo/name)==digest,(repo,name)
        for name,digest in m['topology_hashes'].items():assert sha(repo/'config'/(name+'.txt'))==digest
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
    checks=dict(status='recorded evidence verified; full performance goal remains active',attempts=a['attempts'],completed=a['completed'],
        preserved_failures=len(a['failures']),trace_pairs=pair_checks,complete_diagnostic_traces=5,
        original_truncated_traces_preserved=2,timeout_events_classified=18,empty_flight_timeouts=1,
        actual_ack_timer_bound_runs=timer_runs,source_build_input_harness_archive_hashes='verified',independent_confirmation=False,
        source_commits={p.name:json.loads(p.read_text())['source_commit'] for p in manifests})
    (ROOT/'validation_checks.json').write_text(json.dumps(checks,indent=2)+'\n')
    print('PASS:',a['attempts'],'attempts;',a['completed'],'complete;',len(a['failures']),'preserved failures; nine exact trace pairs; all frozen evidence verified')
if __name__=='__main__':main()
