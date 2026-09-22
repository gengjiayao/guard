"""Verify evidence integrity without equating integrity with performance success."""
import hashlib
import json
from pathlib import Path
import tarfile

ROOT=Path(__file__).resolve().parents[1]

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def main():
    a=json.loads((ROOT/'analysis.json').read_text())
    assert not a['failures'] and a['attempts']==a['completed']==61
    assert all(r['metrics']['completion_fraction']==1 and r['metrics']['drops']==0 for r in a['runs'])
    index={(r['study'],r['arm']):r for r in a['runs']}
    pairs=[]
    for study,left,right in [
        ('allreduce_dp2','dp2_joint32','dp2_joint32_trace'),
        ('fb40','diagnose_startup_peer','diagnose_peer_trace'),
        ('fb40','regression_startup_peer','fixed_trace_peer_trace'),
        ('fb40','regression_joint8','fixed_trace_joint8_fb_trace')]:
        x,y=index[study,left],index[study,right]
        assert x['fct_sha256']==y['fct_sha256'],(study,left,right,'FCT')
        assert x['metrics']==y['metrics'],(study,left,right,'metrics')
        pairs.append(dict(study=study,arms=[left,right],fct_sha256=x['fct_sha256'],all_metrics_identical=True))
    trace=json.loads((ROOT/'trace_analysis.json').read_text())
    assert len(trace)==1 and trace[0]['complete_events']==1280 and trace[0]['cap_truncations']==0
    startup=json.loads((ROOT/'startup_diagnosis.json').read_text())
    assert len(startup)==4 and all(t['completed']==6615 and t['cap_omissions']==0 for t in startup)
    for p in ROOT.glob('*-manifest.json'):
        m=json.loads(p.read_text());snap=ROOT/'harness_snapshots'/p.name.replace('-manifest.json','')
        for name,digest in m['harness_hashes'].items():
            assert sha(snap/Path(name).relative_to('scripts'))==digest,(p,name)
        rec=json.loads((ROOT/'runs'/m['tasks'][0]['key']/'result.json').read_text())
        repo=Path(rec['output_dir']).parents[2]
        for name,digest in m['hashes'].items():assert sha(repo/name)==digest,(p,name)
        for name,digest in m['topology_hashes'].items():assert sha(repo/'config'/(name+'.txt'))==digest
    archives=json.loads((ROOT/'raw_index.json').read_text());assert len(archives)==61
    for name,e in archives.items():
        p=ROOT/name;assert sha(p)==e['sha256']
        with tarfile.open(p) as t:
            rec=json.load(t.extractfile('record/result.json'))
            assert rec==json.loads((ROOT/'runs'/e['key']/'result.json').read_text())
            for member in t.getmembers():
                if member.name.startswith('raw/') and member.isfile():
                    h=hashlib.sha256()
                    stream=t.extractfile(member)
                    for b in iter(lambda:stream.read(1048576),b''):h.update(b)
                    assert h.hexdigest()==sha(Path(rec['output_dir'])/Path(member.name).name)
    report=dict(status='development evidence verified; performance goal remains active',attempts=61,completed=61,
        identity_pairs=pairs,complete_DP2_trace_events=1280,complete_Analytics_traces=4,
        archived_attempts=len(archives),harness_snapshots='all original hashes verified',
        source_build_topology_hashes='verified',independent_confirmation=False,
        source_commits={p.name:json.loads(p.read_text())['source_commit'] for p in ROOT.glob('*-manifest.json')})
    (ROOT/'validation_checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: 61 complete runs; four identical trace pairs; five complete traces; all archives and frozen provenance')

if __name__=='__main__':main()
