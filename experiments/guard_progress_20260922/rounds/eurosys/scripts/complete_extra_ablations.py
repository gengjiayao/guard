import json
from concurrent.futures import ThreadPoolExecutor
from campaign import ROOT,run_one
m=json.loads((ROOT/'manifest.json').read_text())
keys={'ali50-s304-no_selective','ali50-s304-no_release','ali50-s305-no_release'}
with ThreadPoolExecutor(max_workers=3) as pool:
 list(pool.map(run_one,[t for t in m['tasks'] if t['key'] in keys]))
