#!/usr/bin/env python3
"""Audit paired tail metrics without dropping seeds, failures, or slow flows."""
import argparse,csv,json,math,statistics,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experiments.annual2026_tail_loads import tail_metrics
from experiments.annual2026_collectives import sha,dump

def interval(xs):
    m=statistics.fmean(xs)
    if len(xs)==5:
        e=2.7764451051977987*statistics.stdev(xs)/math.sqrt(5)
        return {'mean':m,'ci95_low':m-e,'ci95_high':m+e}
    return {'mean':m,'ci95_low':None,'ci95_high':None}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('campaign',type=Path);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    plan=json.loads((a.campaign/'plan.json').read_text());rs=json.loads((a.campaign/'results.json').read_text())
    expected={(t['case'],t['seed'],arm) for t in plan['inputs'] for arm in plan['variants']}
    assert {(r['case'],r['seed'],r['arm']) for r in rs}==expected
    assert len(rs)==len(expected) and all(r['status']=='completed' for r in rs)
    rows=[];identities={};digests={}
    for r in rs:
        out=Path(r['output_dir']);p=out/f'{out.name}_out_fct.txt';assert sha(p)==r['output_hashes'][p.name]
        t=next(t for t in plan['inputs'] if (t['case'],t['seed'])==(r['case'],r['seed']))
        assert r['input_sha256']==t['flow_sha256'] and r['completed']==t['flow_count']
        fresh=tail_metrics(out,t['duration']*plan['warmup_fraction']);assert fresh==r['tails']
        import hashlib
        digests[r['key']]=hashlib.sha256('\n'.join(sorted(p.read_text().splitlines())).encode()).hexdigest()
        for group,v in fresh.items():
            for q in [95,99]:rows.append({'case':r['case'],'seed':r['seed'],'arm':r['arm'],'group':group,'metric':f'p{q}_fct_us','n':v['n'],'value':v[f'p{q}_fct_us']})
    summaries=[];effects=[]
    for case,group,metric in sorted({(r['case'],r['group'],r['metric']) for r in rows}):
        for arm in plan['variants']:
            part=[r for r in rows if (r['case'],r['group'],r['metric'],r['arm'])==(case,group,metric,arm)]
            summaries.append({'case':case,'group':group,'metric':metric,'arm':arm,'n_min':min(r['n'] for r in part),'n_max':max(r['n'] for r in part),**interval([r['value'] for r in part])})
            for baseline in ['homa','guard']:
                if arm==baseline or baseline not in plan['variants']:continue
                diffs=[]
                for r in part:
                    b=next(x for x in rows if (x['case'],x['group'],x['metric'],x['arm'],x['seed'])==(case,group,metric,baseline,r['seed']))
                    diffs.append(100*(1-r['value']/b['value']))
                effects.append({'case':case,'group':group,'metric':metric,'arm':arm,'baseline':baseline,'reductions_percent':diffs,**interval(diffs)})
    a.output.mkdir(parents=True,exist_ok=True);dump(a.output/'analysis.json',{'campaign':str(a.campaign),'plan':plan,'runs':len(rs),'flow_completions':sum(r['completed'] for r in rs),'summary':summaries,'effects':effects,'fct_sorted_sha256':digests})
    for name,data in [('per-seed',rows),('summary',summaries),('effects',effects)]:
        with (a.output/f'{name}.csv').open('w') as f:
            w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    for e in effects:
        if e['group']=='all' and e['metric']=='p99_fct_us' and e['baseline']=='homa':
            print(e['case'],e['arm'],'P99 reduction vs Homa',round(e['mean'],3),e['ci95_low'],e['ci95_high'])
if __name__=='__main__':main()
