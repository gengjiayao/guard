#!/usr/bin/env python3
"""Retrospective tail-latency analysis; preserve the original frozen results."""
from pathlib import Path
from collections import Counter
import argparse,csv,hashlib,json,math,statistics

CASES=['incast2','incast7','mixed','fabric']
ARMS=['guard','hpcc','dcqcn','homa']
BINS=[('le8KiB',0,8192),('8to64KiB',8192,65536),('64KiBto1MiB',65536,1048576),('gt1MiB',1048576,math.inf)]

def percentile(xs,q):
    xs=sorted(xs);assert xs and 0<=q<=100
    pos=(len(xs)-1)*q/100;lo=math.floor(pos);hi=math.ceil(pos)
    return xs[lo]+(xs[hi]-xs[lo])*(pos-lo)

def interval(xs):
    assert len(xs)==5
    mean=statistics.fmean(xs);delta=2.7764451051977987*statistics.stdev(xs)/math.sqrt(5)
    return {'mean':mean,'ci95_low':mean-delta,'ci95_high':mean+delta,'n_seeds':5}

def parse(path):
    rows=[]
    for line in path.read_text().splitlines():
        src,dst,sp,dp,size,start,duration,ideal=map(int,line.split())
        assert size>0 and duration>0 and ideal>0
        rows.append({'src':src,'dst':dst,'size':size,'start_ns':start,'fct_us':duration/1000,'ideal_us':ideal/1000})
    return rows

def load_run(r,raw_root):
    out=raw_root/Path(r['output_dir']).name if raw_root else Path(r['output_dir'])
    path=out/(out.name+'_out_fct.txt')
    assert hashlib.sha256(path.read_bytes()).hexdigest()==r['output_hashes'][path.name]
    f=parse(path);assert len(f)==r['completed']
    inp=out/(out.name+'_input_flow.txt');lines=inp.read_text().splitlines()
    assert hashlib.sha256(inp.read_bytes()).hexdigest()==r['input_sha256']
    assert int(lines[0])==len(f)
    expected=Counter()
    for line in lines[1:]:
        src,dst,pg,size,start=line.split();expected[int(src),int(dst),int(size),round(float(start)*1e9)]+=1
    for x in f:
        key=next(((*[x[k] for k in ['src','dst','size']],x['start_ns']+d) for d in [-2,-1,0,1,2]
                  if expected[(*[x[k] for k in ['src','dst','size']],x['start_ns']+d)]>0),None)
        assert key is not None;expected[key]-=1
    assert not any(expected.values())
    f=[x for x in f if r['case']!='mixed' or x['start_ns']>2005000000]
    assert len(f)==r['analyzed']
    assert abs(percentile([x['fct_us'] for x in f],99)-r['metrics']['p99_fct_us'])<1e-8
    assert abs(statistics.fmean(x['fct_us'] for x in f)-r['metrics']['mean_fct_us'])<1e-8
    return f

def csv_write(path,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=keys,lineterminator='\n');writer.writeheader();writer.writerows(rows)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('campaign',type=Path);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--original-regression',type=Path);ap.add_argument('--raw-root',type=Path);a=ap.parse_args()
    results=json.loads((a.campaign/'results.json').read_text());plan=json.loads((a.campaign/'plan.json').read_text())
    assert len(results)==200 and plan['seeds']==list(range(1601,1606))
    rows=[];audited=0;identities={}
    for r in results:
        if r['case'] not in CASES:continue
        assert r['status']=='completed';f=load_run(r,a.raw_root);audited+=len(f)
        key=r['case'],r['seed'];ident=Counter((x['src'],x['dst'],x['size'],x['start_ns']) for x in f)
        if key in identities:assert ident==identities[key]
        identities[key]=ident
        groups=[('all',f)]
        if r['case']=='mixed':groups += [(name,[x for x in f if lo<x['size']<=hi]) for name,lo,hi in BINS]
        for group,g in groups:
            assert g
            for q in [95,99]:
                rows.append({'case':r['case'],'group':group,'arm':r['arm'],'seed':r['seed'],'metric':f'p{q}_fct_us',
                             'sample_count':len(g),'value_us':percentile([x['fct_us'] for x in g],q),
                             'expected_tail_count':len(g)*(1-q/100)})
    summaries=[];effects=[]
    for case,group in dict.fromkeys((r['case'],r['group']) for r in rows):
        for metric in ['p95_fct_us','p99_fct_us']:
            for arm in ARMS:
                rs=[r for r in rows if (r['case'],r['group'],r['metric'],r['arm'])==(case,group,metric,arm)]
                summaries.append({'case':case,'group':group,'arm':arm,'metric':metric,
                                  'n_min':min(r['sample_count'] for r in rs),'n_max':max(r['sample_count'] for r in rs),
                                  **interval([r['value_us'] for r in rs])})
            for base in ARMS[1:]:
                vals=[]
                for seed in plan['seeds']:
                    def value(arm):return next(r['value_us'] for r in rows if (r['case'],r['group'],r['metric'],r['arm'],r['seed'])==(case,group,metric,arm,seed))
                    vals.append(100*(1-value('guard')/value(base)))
                effects.append({'case':case,'group':group,'metric':metric,'baseline':base,'seed_reductions_percent':vals,**interval(vals)})
    regression=[]
    if a.original_regression:
        for old in json.loads((a.original_regression/'results.json').read_text()):
            f=load_run(old,a.raw_root)
            for q in [95,99]:
                metric=f'p{q}_fct_us';new=next(r['value_us'] for r in rows if (r['case'],r['group'],r['metric'],r['arm'],r['seed'])==(old['case'],'all',metric,'guard',old['seed']))
                before=percentile([x['fct_us'] for x in f],q)
                regression.append({'case':old['case'],'seed':old['seed'],'metric':metric,'original_us':before,'optimized_us':new,'reduction_percent':100*(1-new/before)})
    activity=[]
    for case in plan['cases']:
        group=[r for r in results if r['case']==case and r['arm']=='guard']
        activity.append({'case':case,**{key:sum(r['stats'][key] for r in group) for key in
            ['hpcc_feedback_updates','hpcc_rate_updates_applied','reactive_binding_rate_changes','grant_event_rate_changes','registrations']}})
    source_guard=next(r for r in results if r['arm']=='guard')
    out=a.raw_root/Path(source_guard['output_dir']).name if a.raw_root else Path(source_guard['output_dir'])
    config=out/'config.txt';assert hashlib.sha256(config.read_bytes()).hexdigest()==source_guard['output_hashes']['config.txt']
    config_values={line.split()[0]:line.split()[1] for line in config.read_text().splitlines() if len(line.split())==2}
    relevant={key:config_values[key] for key in ['GUARD_ONE_RTT_BYPASS','GUARD_TAIL_BYPASS','GUARD_TAIL_BYPASS_BDPS','GUARD_TAIL_CONGESTION_GATE']}
    report={'source_campaign':str(a.campaign),'source_plan_sha256':hashlib.sha256((a.campaign/'plan.json').read_bytes()).hexdigest(),
            'source_git':plan['git'],'analysis_kind':'Retrospective metric revision requested after the original mean-FCT study; no new simulation or retuning.',
            'quantile_method':'Linear interpolation at (n-1)*q; compute each seed quantile before summarizing five seeds. Never pool seeds.',
            'uncertainty':'Intervals are 95% t intervals across five seed statistics, not confidence bounds for the population quantile. Directed cases have only 16, 56 or 64 flows per seed; P99 is near a sample maximum.',
            'retained_flows':audited,'audited_runs':80,'rows':rows,'summary':summaries,'effects':effects,'original_regression':regression,
            'guard_activity':activity,'guard_bypass_config':relevant,
            'incast7_payload_serialization_lower_bound_us':7*2*1024**2*8/100e9*1e6}
    a.output.mkdir(parents=True,exist_ok=True);(a.output/'tail-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
    for name,data in [('tail-per-seed',rows),('tail-summary',summaries),('tail-effects',effects),('original-tail-regression',regression),('guard-activity',activity)]:csv_write(a.output/(name+'.csv'),data)
    for case in CASES:
        for metric in ['p95_fct_us','p99_fct_us']:
            group=[x for x in summaries if (x['case'],x['group'],x['metric'])==(case,'all',metric)]
            h=next(x for x in effects if (x['case'],x['group'],x['metric'],x['baseline'])==(case,'all',metric,'homa'))
            print(case,metric,' '.join('%s=%.3f'%(x['arm'],x['mean']) for x in group),'vs Homa %.3f%% [%.3f, %.3f]'%(h['mean'],h['ci95_low'],h['ci95_high']))
    for c in ['incast2','incast7']:
        r=[r['reduction_percent'] for r in regression if r['case']==c and r['metric']=='p99_fct_us']
        print('original P99 comparison',c,interval(r))
    print('AUDIT',audited,'selected flow records from 80 existing runs')

if __name__=='__main__':main()
