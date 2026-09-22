"""Publication gate: frozen cells, trace identities, macros and raw provenance."""
import hashlib,json,re
from pathlib import Path
from campaign import ROOT,REPO,sha,save
m=json.loads((ROOT/'manifest.json').read_text());a=json.loads((ROOT/'analysis.json').read_text())
expected={t['key'] for t in m['tasks']};actual={r['key'] for r in a['runs']}
assert expected==actual,sorted(expected-actual)
assert not a['failures'],a['failures']
assert sha(REPO/'build/scratch/network-load-balance')==m['binary_sha256'],'Binary changed'
assert sha(REPO/'run.py')==m['run_py_sha256'],'Driver changed'
assert all(r['valid'] and r['metrics']['completion_fraction']==1 for r in a['runs'])
for r in a['runs']:
 assert sha(r['fct_file'])==r['fct_sha256'],r['key']
 s=json.loads((ROOT/'runs'/r['key']/'result.json').read_text())
 assert s['status']=='completed' and s['completed']==s['flow_count'],r['key']
 assert sha(s['config'])==s['config_sha256'],r['key']
tex=(ROOT/'paper/results.tex').read_text();assert 'pending' not in tex
macros=set(re.findall(r'\\newcommand\{\\([A-Za-z]+)',tex))
c=json.loads((ROOT/'claim_evidence.json').read_text());known=set(c['absolute'])|set(c['paired_effects'])|{k+'CI' for k in c['paired_effects']}|{'MeanReductionRangeHpcc','MeanReductionRangeDcqcn','MeanReductionRangeTimely'}
assert macros<=known,macros-known
for p in (ROOT/'paper/sections').glob('*.tex'):
 assert not re.search(r'\\begin\{(?:table\*?|tabular)\}',p.read_text()),p
raw=json.loads((ROOT/'raw_index.json').read_text());assert set(raw)==expected
for key,v in raw.items():assert sha(ROOT/v['path'])==v['sha256'],key
report={'status':'PASS','runs':len(expected),'completed_flows_across_runs':sum(t['flow_count'] for t in m['tasks']),'seeds':m['seeds'],'reported_macros':len(macros),'raw_archives':len(raw),'all_input_completions_retained':True,'source_revision':m['git_sha'],'binary_sha256':m['binary_sha256'],'paper_pdf_sha256':sha(ROOT/'paper/main.pdf'),'supplement_pdf_sha256':sha(ROOT/'paper/supplement.pdf')}
save(ROOT/'audit/final-integrity.json',report);print(json.dumps(report,indent=2))
