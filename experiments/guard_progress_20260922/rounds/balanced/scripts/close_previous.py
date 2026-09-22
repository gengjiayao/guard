"""Close the prior candidate's previously missing 75 cells, without mixing cohorts."""
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1].parent/'guard_optimization_20260921'


def main():
    manifest=json.loads((ROOT/'holdout/confirmation-manifest.json').read_text())
    records={p.parent.name:json.loads(p.read_text()) for p in (ROOT/'holdout/runs').glob('*/result.json')}
    assert set(records)=={t['key'] for t in manifest['tasks']},(len(records),len(manifest['tasks']))
    assert all(r['status']=='completed' for r in records.values())
    for command in [('confirm.py','analyze'),('report.py',),('archive.py',),('final_gate.py',)]:
        subprocess.run([sys.executable,str(ROOT/'scripts'/command[0]),*command[1:]],check=True)
    data=json.loads((ROOT/'confirmation-evidence.json').read_text())
    lines=['# 补齐此前缺少的 75 次复测', '',
           '本次按用户“有问题的都测试”的要求，补跑之前明确标为未执行的 75 次大负载外部基线与 OFLM 消融。原有冻结配置、源代码、二进制和种子 401–405 均保持一致。', '',
           f'该候选的冻结矩阵现已完成全部 {len(records)} 次仿真，全部通过身份及流完成检查。此处对应上一轮候选，不是采用新接收端策略的 501–505 验证。原 `REPORT.zh.md` 保留首次 379 次验证的历史记录。', '',
           '新增比较（平均五种子配对百分比；负值表示更低）：','']
    for s in ['ali30','ali50','allreduce_dp2']:
        for b in ['hpcc','homa','dcqcn','timely']:
            row=next(x for x in data['comparisons'] if x['study']==s and x['baseline']==b and x['metric']=='fct_mean_us')
            lo,hi=row['ci95']
            lines.append(f'- {s} 对 {b.upper() if b!="homa" else "Homa"}：平均 FCT {row["percent_change"]:+.2f}%，95% 区间 [{lo:+.2f}%, {hi:+.2f}%]。')
    lines+=['','OFLM 消融：','']
    for b in ['no_selective','no_release','no_oflm']:
        parts=[]
        for metric in ['fct_mean_us','grants','mean_flow_goodput_gbps']:
            x=next(x for x in data['comparisons'] if x['study']=='ali50' and x['baseline']==b and x['metric']==metric)
            parts.append(f'{metric} {x["percent_change"]:+.2f}%')
        lines.append('- '+b+'：'+'；'.join(parts)+'。')
    lines+=['','`analysis.json`、`confirmation-evidence.json`、三张摘要图、原始归档索引和验证门均已更新到完整矩阵。全部失败开发尝试仍保留。这个候选的存储、DP2、公平性回退仍阻止其作为统一默认配置采用。', '',
            '更新后的候选与独立证据见相邻目录 `guard_balanced_20260921`。']
    (ROOT/'FOLLOWUP.zh.md').write_text('\n'.join(lines)+'\n')
    print('Closed prior cohort:',len(records),'complete runs')


if __name__=='__main__':
    main()
