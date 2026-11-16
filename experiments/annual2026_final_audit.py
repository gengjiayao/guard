#!/usr/bin/env python3
"""Recompute final report values from all frozen runs, without censoring."""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,csv,hashlib,json,math,statistics,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experiments.annual2026_collectives import summarize,sha,dump
from experiments.summarize_workload import parse_fct
from experiments.summarize_campaign import percentile

def interval(xs):
    n=len(xs);t={5:2.7764451051977987,10:2.2621571628540993}[n]
    mean=statistics.fmean(xs);margin=t*statistics.stdev(xs)/math.sqrt(n)
    return {'n_seeds':n,'mean':mean,'ci95_low':mean-margin,'ci95_high':mean+margin}

def primary(case):
    return 'makespan_us' if case=='concurrent' else 'mean_cct_us' if case.startswith(('alltoall','ring')) else 'p99_fct_us'

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--campaign-base',type=Path);p.add_argument('--freeze',type=Path);p.add_argument('--raw-root',type=Path);a=p.parse_args()
    repo=Path(__file__).resolve().parents[1]
    freeze=json.loads((a.freeze or repo/'experiments/annual2026_tail_final_freeze.json').read_text())
    cases={};records=[];run_rows=[];all_runs=[];plans={};activity=[]
    names=['primary','sensitivity','regression']
    for name in names:
        root=(a.campaign_base or repo/'experiments/results')/('annual2026_tail_final_'+name)
        plan=json.loads((root/'plan.json').read_text());runs=json.loads((root/'results.json').read_text());plans[name]=plan
        assert plan['source_diff_sha256']==hashlib.sha256(b'').hexdigest()
        assert plan['runtime']==freeze['runtime']
        variants=plan.get('variants',plan.get('arms'));assert variants==freeze['variants']
        expected={(x['case'],x['seed'],arm) for x in plan['inputs'] for arm in variants}
        assert len(runs)==len(expected) and {(r['case'],r['seed'],r['arm']) for r in runs}==expected
        for r in runs:
            assert r['status']=='completed' and r['exit_code']==0
            assert r['git']==plan['git'];out=Path(r['output_dir'])
            if a.raw_root:out=a.raw_root/out.name
            for fname,digest in r['output_hashes'].items():assert sha(out/fname)==digest,(r['key'],fname)
            trace=json.loads((root/'inputs'/f'{r["case"]}-{r["seed"]}.json').read_text())
            # Validate flow identities, complete counts, and DAG edges again.
            # JSON persisted integer priority keys as strings; normalize only
            # serialization, preserving every value and equality assertion.
            recomputed=json.loads(json.dumps(summarize(out,trace)))
            for k in ['metrics','operations','stats','pfc','completed','analyzed','integrity']:
                assert recomputed[k]==r[k],(r['key'],k)
            rows=parse_fct(out/f'{out.name}_out_fct.txt')
            warmup=trace['duration']*plan['warmup_fraction'] if name!='regression' else .005 if r['case']=='mixed' else 0
            selected=[x for x in rows if x['start_ns']>=2e9+warmup*1e9]
            if r['case']=='mixed':selected=[x for x in rows if x['start_ns']>2005000000]
            groups={'all':selected}
            if name!='regression' or r['case']=='mixed':
                for label,lo,hi in [('le8KiB',0,8192),('8to64KiB',8192,65536),('64KiBto1MiB',65536,1048576),('gt1MiB',1048576,math.inf)]:
                    groups[label]=[x for x in selected if lo<x['size']<=hi]
            for group,rs in groups.items():
                if not rs:continue
                for q in [95,99]:
                    metric=f'p{q}_fct_us';val=percentile([x['fct_us'] for x in rs],q)
                    if name!='regression':assert val==r['tails'][group][metric]
                    records.append({'campaign':name,'case':r['case'],'seed':r['seed'],'arm':r['arm'],'group':group,'metric':metric,'sample_count':len(rs),'value_us':val})
            for metric in ['mean_cct_us','makespan_us']:
                if metric in r['metrics'] and (metric=='mean_cct_us' or r['case']=='concurrent'):
                    records.append({'campaign':name,'case':r['case'],'seed':r['seed'],'arm':r['arm'],'group':'all','metric':metric,'sample_count':len(r['operations']),'value_us':r['metrics'][metric]})
            cases[r['case']]=plan['seeds']
            run_rows.append({'campaign':name,'case':r['case'],'seed':r['seed'],'arm':r['arm'],'completed':r['completed'],'analyzed':len(selected),'output_dir':r['output_dir'],'input_sha256':r['input_sha256'],'fct_sha256':r['output_hashes'][out.name+'_out_fct.txt']})
        all_runs.extend(runs)
    summaries=[];effects=[];arms=['guard','hpcc','dcqcn','homa']
    for case,group,metric in sorted({(r['case'],r['group'],r['metric']) for r in records}):
        by={(r['seed'],r['arm']):r for r in records if (r['case'],r['group'],r['metric'])==(case,group,metric)}
        for arm in arms:
            rows=[by[s,arm] for s in cases[case]]
            summaries.append({'case':case,'group':group,'metric':metric,'arm':arm,'n_min':min(r['sample_count'] for r in rows),'n_max':max(r['sample_count'] for r in rows),**interval([r['value_us'] for r in rows])})
        for baseline in arms[1:]:
            reductions=[100*(1-by[s,'guard']['value_us']/by[s,baseline]['value_us']) for s in cases[case]]
            effects.append({'case':case,'group':group,'metric':metric,'baseline':baseline,'seeds':cases[case],'reductions_percent':reductions,**interval(reductions)})
    health=[]
    stat_keys=['switch_drops_total','timeout_recoveries','irn_retransmit_packets','homa_retransmit_packets','recovery_nacks_generated','proactive_releases','registrations','reactive_binding_rate_changes','grant_event_rate_changes']
    for case in sorted(cases):
        for arm in arms:
            rs=[r for r in all_runs if (r['case'],r['arm'])==(case,arm)]
            health.append({'case':case,'arm':arm,'runs':len(rs),'completed':sum(r['completed'] for r in rs),**{k:sum(r['stats'][k] for r in rs) for k in stat_keys},'pfc_pause_events':sum(r['pfc']['pfc_pause_events'] for r in rs)})
    result={'freeze':freeze,'plans':plans,'runs':len(all_runs),'completed_records':sum(r['completed'] for r in all_runs),'summary':summaries,'effects':effects,'health':health,'audited_files':sum(len(r['output_hashes']) for r in all_runs),'policy':'All planned runs, seeds and flow sizes retained. Tail metrics use start-time warmup and full completion. Percentiles computed per seed; paired percent reductions summarized across seeds. CI is t interval across seed statistics, not a confidence interval for the population percentile.'}
    a.out.mkdir(parents=True,exist_ok=True);dump(a.out/'report-analysis.json',result)
    for name,rows in [('per-seed',records),('summary',summaries),('effects',effects),('health',health),('run-manifest',run_rows)]:
        with (a.out/(name+'.csv')).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    for e in effects:
        if e['group']=='all' and e['baseline']=='homa' and e['metric']==primary(e['case']):
            print(e['case'],e['metric'],*[round(e[k],3) for k in ['mean','ci95_low','ci95_high']])
    print('AUDIT',result['runs'],result['completed_records'],result['audited_files'])

if __name__=='__main__':main()
