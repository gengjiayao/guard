"""Close this development batch without claiming the broader goal is achieved."""
import hashlib
import json
from pathlib import Path
import tarfile
from concurrent.futures import ThreadPoolExecutor

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''): h.update(block)
    return h.hexdigest()


def main():
    data=json.loads((ROOT/'analysis.json').read_text())
    records={p.parent.name:json.loads(p.read_text()) for p in (ROOT/'runs').glob('*/result.json')}
    failed='allreduce_dp2_prefix8-s301-slots_prefix_slots8'
    retry='allreduce_dp2_prefix8-s301-slots_retry_slots8'
    assert [r['key'] for r in data['failures']]==[failed]
    assert records[retry]['status']=='completed'
    assert records[failed]['extra']==records[retry]['extra']
    assert records[failed]['flow_sha256']==records[retry]['flow_sha256']
    old=json.loads((ROOT/'slots_prefix-manifest.json').read_text())
    new=json.loads((ROOT/'slots_retry-manifest.json').read_text())
    assert old['hashes']==new['hashes'], 'retry must use the identical simulator binary and libraries'
    rows={r['key']:r for r in data['runs']}
    gate_runs=[]
    for key,r in records.items():
        if r['status']!='completed' or r['extra'].get('guard_post_grant_window_bdps',1)<=1:
            continue
        stats=next(Path(r['output_dir']).glob('*_out_guard_stats.txt')).read_text().splitlines()
        parts=next(line.split() for line in stats if 'first_grant_gated' in line)
        gated=int(parts[parts.index('first_grant_gated')+1])
        released=int(parts[parts.index('first_grant_released')+1])
        assert gated==released==rows[key]['stats']['registrations'], (key,gated,released)
        gate_runs.append(key)
    index=json.loads((ROOT/'raw_index.json').read_text())
    assert set(index)=={f'raw/{k}.tar.gz' for k in records}
    def check(item):
        path,meta=item
        assert sha(ROOT/path)==meta['sha256'],path
        record=records[meta['key']]
        with tarfile.open(ROOT/path,'r:gz') as tar:
            assert json.load(tar.extractfile('record/result.json'))==record
            if record['status']=='completed':
                row=rows[meta['key']]
                for field,suffix in [('fct_sha256','_out_fct.txt'),('stats_sha256','_out_guard_stats.txt'),
                                     ('queue_sha256','_out_queue_stats.txt')]:
                    member=next(x for x in tar.getnames() if x.startswith('raw/') and x.endswith(suffix))
                    assert hashlib.sha256(tar.extractfile(member).read()).hexdigest()==row[field]
    with ThreadPoolExecutor(max_workers=3) as pool: list(pool.map(check,index.items()))
    result=dict(status='development evidence verified; goal still active', attempts=data['attempts'],
        complete_original_trace_runs=data['complete_original_trace_runs'],
        diagnostic_prefix_runs=data['diagnostic_prefix_runs'],
        preserved_failed_attempt=failed, successful_retry=retry,
        retry_simulator_hashes='identical; only driver initialization and its test changed',
        post_grant_gate_checks=gate_runs, verified_archives=len(index),
        completion_identity='all inputs completed; same input identities within every study',
        performance_decision='No universal dominance. No fresh independent confirmation or paper promotion.')
    (ROOT/'validation_checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS development evidence',data['attempts'],'attempts;',len(index),'raw archives; goal remains active')


if __name__=='__main__':main()
