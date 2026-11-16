#!/usr/bin/env python3
"""Summarize all frozen runs, with seed-paired effects and raw-data audits."""
from pathlib import Path
import argparse,csv,hashlib,json,math,statistics

def primary(case):
    return 'makespan_us' if case=='concurrent' else 'mean_cct_us' if case.startswith(('alltoall','ring')) else 'mean_fct_us'

def interval(values):
    n=len(values);mean=statistics.fmean(values)
    t={5:2.7764451051977987}.get(n)
    assert t is not None,'Declare the seed count before analysis'
    margin=t*statistics.stdev(values)/math.sqrt(n)
    return {'mean':mean,'ci95_low':mean-margin,'ci95_high':mean+margin,'n':n}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('root',type=Path);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--raw-root',type=Path)
    a=ap.parse_args();plan=json.loads((a.root/'plan.json').read_text());runs=json.loads((a.root/'results.json').read_text())
    cases=plan['cases'];arms=list(plan['arms']);seeds=plan['seeds']
    assert len(runs)==len(cases)*len(arms)*len(seeds)
    assert len({r['key'] for r in runs})==len(runs)
    seen={};total=0;stats={};records=[];summaries=[];effects=[]
    for r in runs:
        assert r['status']=='completed' and r['exit_code']==0
        assert r['binary_sha256']==plan['binary_sha256'] and r['git']==plan['git']
        assert r['integrity']=='all flow identities and dependency edges checked'
        output_dir=a.raw_root/Path(r['output_dir']).name if a.raw_root else Path(r['output_dir'])
        for name,digest in r['output_hashes'].items():
            assert hashlib.sha256((output_dir/name).read_bytes()).hexdigest()==digest,(r['key'],name)
        ident=(r['case'],r['seed']);hashes=(r['input_sha256'],r['dependency_sha256'])
        if ident in seen:assert seen[ident]==hashes
        seen[ident]=hashes;total+=r['completed']
        metrics=r['metrics'];metric=primary(r['case'])
        records.append({'case':r['case'],'seed':r['seed'],'algorithm':r['arm'],'primary_metric':metric,'primary_us':metrics[metric],**metrics})
        for k in ['switch_drops_total','timeout_recoveries','irn_retransmit_packets','homa_retransmit_packets','recovery_nacks_generated']:
            assert k in r['stats'],(r['key'],k)
            stats[k]=stats.get(k,0)+r['stats'][k]
    for c in cases:
        for arm in arms:
            group=[r for r in runs if r['case']==c and r['arm']==arm];assert sorted(r['seed'] for r in group)==sorted(seeds)
            for m in group[0]['metrics']:
                summaries.append({'case':c,'arm':arm,'metric':m,**interval([r['metrics'][m] for r in group])})
        for arm in arms:
            if arm=='guard':continue
            for m in ['mean_fct_us','p99_fct_us','queue_bytes_max',primary(c)]:
                if any(e['case']==c and e['baseline']==arm and e['metric']==m for e in effects):continue
                values=[]
                for seed in seeds:
                    g=next(r for r in runs if (r['case'],r['seed'],r['arm'])==(c,seed,'guard'))
                    b=next(r for r in runs if (r['case'],r['seed'],r['arm'])==(c,seed,arm))
                    if b['metrics'][m]==0:break
                    values.append(100*(1-g['metrics'][m]/b['metrics'][m]))
                if len(values)==len(seeds):effects.append({'case':c,'baseline':arm,'metric':m,'seed_effects_percent':values,**interval(values)})
    guard_stats={k:sum(r['stats'].get(k,0) for r in runs if r['arm']=='guard') for k in ['grants_sent','grant_bytes_sent','proactive_releases','hpcc_rate_updates_applied','hpcc_actual_rate_changes','reactive_binding_rate_changes','grant_event_rate_changes']}
    output={'plan':plan,'runs':len(runs),'completed_flow_records':total,'integrity':stats,'guard_activity':guard_stats,'summary':summaries,'effects':effects}
    a.output.mkdir(parents=True,exist_ok=True);(a.output/'analysis.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    for name,rows in [('per_run_metrics',records),('summary',summaries),('paired_effects',effects)]:
        fields=list(dict.fromkeys(k for r in rows for k in r))
        with (a.output/(name+'.csv')).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    for c in cases:
        m=primary(c);line=[]
        for arm in arms:
            s=next(x for x in summaries if (x['case'],x['arm'],x['metric'])==(c,arm,m));line.append('%s=%.3f'%(arm,s['mean']))
        print(c,m,' '.join(line))
    print('AUDIT',len(runs),total,stats,guard_stats)

if __name__=='__main__':main()
