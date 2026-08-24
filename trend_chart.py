#!/usr/bin/env python3
"""生成新方案命中趋势图: 旧V6 vs rot8 vs rot8+温号3 (210-233 累计命中线 + 每期明细表)"""
import json
from backtest_new import draws, build_union, start, end

REDS  = {1,2,7,8,12,13,18,19,23,24,29,30,34,35,40,45,46}
BLUES = {3,4,9,10,14,15,20,25,26,31,36,37,41,42,47,48}
def wave(n): return 'red' if n in REDS else ('blue' if n in BLUES else 'green')
WAVE_C = {'red':'#dc2626','blue':'#2563eb','green':'#059669'}

rows=[]
for k,d in enumerate(draws):
    if not (start<=int(d['i'])<=end): continue
    u20,w3=build_union(k,True,warm_n=1); u20o,_=build_union(k,False)
    rows.append({'i':d['i'][-3:],'s':d['s'],
                 'old':int(d['s'] in u20o),'rot':int(d['s'] in u20),'warm':int(d['s'] in w3)})

n=len(rows)
c_old=c_rot=c_new=0
lines={'old':[],'rot':[],'new':[]}
for r in rows:
    c_old+=r['old']; c_rot+=r['rot']; c_new+=max(r['rot'],r['warm'])
    lines['old'].append(c_old); lines['rot'].append(c_rot); lines['new'].append(c_new)

# ---- SVG 折线图 ----
W,H,L,B,T=820,250,34,26,12
pw,ph=W-L-B,H-T-B
x=lambda i: L+pw*(i/(n-1))
def y(v): return T+ph-(v/n)*ph
pts={k:' '.join(f"{x(i):.1f},{y(v):.1f}" for i,v in enumerate(vals)) for k,vals in lines.items()}
grid=''
for gv in range(0,25,5):
    gy=y(gv)
    grid+=f'<line x1="{L}" y1="{gy:.1f}" x2="{W-B}" y2="{gy:.1f}" stroke="#1e293b" stroke-width="1"/><text x="{L-6}" y="{gy+4:.1f}" fill="#64748b" font-size="10" text-anchor="end">{gv}</text>'
xlab=''.join(f'<text x="{x(i):.1f}" y="{H-8}" fill="#64748b" font-size="9" text-anchor="middle">{r["i"]}</text>' for i,r in enumerate(rows))
legend=('''<div class="legend"><span class="lg old">─ 旧V6 (20码)</span><span class="lg rot">─ rot8 (20码)</span><span class="lg new">─ rot8+温号1 (21码)</span></div>''')

# ---- 明细表 ----
tr=''
for i,r in enumerate(rows):
    hit=r['rot'] or r['warm']
    cls='hit' if hit else 'miss'
    tr+=f'''<tr class="{cls}">
<td>{r['i']}期</td>
<td><span class="ball" style="background:{WAVE_C[wave(r['s'])]}">{r['s']:02d}</span></td>
<td>{'✅' if r['old'] else '❌'}</td>
<td>{'✅' if r['rot'] else '❌'}</td>
<td>{'✅' if r['warm'] else '❌'}</td>
<td>{'🎯 命中' if hit else '✖ 未中'}</td></tr>'''

html=f'''<!doctype html><html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>纯模型命中趋势 210-233</title><style>
*{{margin:0;padding:0;box-sizing:border-box}}body{{background:#0b1220;color:#e2e8f0;font-family:-apple-system,"PingFang SC",sans-serif;padding:16px}}
h1{{text-align:center;color:#fbbf24;font-size:1.15rem;margin-bottom:4px}}.sub{{text-align:center;color:#94a3b8;font-size:.75rem;margin-bottom:14px}}
.card{{background:#111a2e;border:1px solid #233;border-radius:12px;padding:14px;margin:0 auto 12px;max-width:880px}}
.card h3{{color:#94a3b8;font-size:.85rem;margin-bottom:8px}}
.legend{{display:flex;gap:16px;justify-content:center;font-size:.75rem;margin-bottom:6px}}
.lg.old{{color:#94a3b8}}.lg.rot{{color:#38bdf8}}.lg.new{{color:#fbbf24}}
svg{{width:100%;height:auto;display:block}}
.stats{{display:flex;gap:10px;flex-wrap:wrap;justify-content:center;margin-bottom:10px}}
.stat{{background:#0f1830;border:1px solid #2d3a52;border-radius:10px;padding:8px 14px;text-align:center;min-width:130px}}
.stat b{{display:block;font-size:1.05rem}}
.stat span{{font-size:.65rem;color:#94a3b8}}
.stat.old b{{color:#94a3b8}}.stat.rot b{{color:#38bdf8}}.stat.new b{{color:#fbbf24}}
table{{border-collapse:collapse;width:100%;font-size:.72rem}}
th,td{{border:1px solid #2d3a52;padding:5px 6px;text-align:center}}
th{{color:#94a3b8;background:#0f1830;font-size:.68rem}}
tr.hit{{background:#132a22}}tr.miss{{background:#2a1418}}
.ball{{display:inline-flex;width:24px;height:24px;border-radius:50%;color:#fff;font-weight:700;align-items:center;justify-content:center;font-size:.62rem;box-shadow:0 1px 4px rgba(0,0,0,.5)}}
.note{{color:#64748b;font-size:.68rem;margin-top:8px;text-align:center}}
</style></head><body>
<h1>📈 新方案命中趋势 (210~233期回测)</h1>
<div class="sub">rot8选位轮转 + 温号1 · 完全复刻 buildUnion 逻辑 · 数据源 macau_mark6_data.csv</div>
<div class="card">
<div class="stats">
<div class="stat old"><b>{c_old}/{n} · {c_old/n*100:.1f}%</b><span>旧V6 20码<br>期望+17.2/期</span></div>
<div class="stat rot"><b>{c_rot}/{n} · {c_rot/n*100:.1f}%</b><span>rot8 20码<br>期望+19.2/期</span></div>
<div class="stat new"><b>{c_new}/{n} · {c_new/n*100:.1f}%</b><span>rot8+温号1 21码<br>期望+20.1/期</span></div>
</div>
{legend}
<svg viewBox="0 0 {W} {H}">
{grid}
<polyline points="{pts['old']}" fill="none" stroke="#94a3b8" stroke-width="2" stroke-dasharray="4 3"/>
<polyline points="{pts['rot']}" fill="none" stroke="#38bdf8" stroke-width="2"/>
<polyline points="{pts['new']}" fill="none" stroke="#fbbf24" stroke-width="2.5"/>
<circle cx="{x(n-1):.1f}" cy="{y(c_new):.1f}" r="3.5" fill="#fbbf24"/>
{xlab}
</svg>
</div>
<div class="card"><h3>📋 每期明细</h3>
<div style="overflow-x:auto"><table>
<tr><th>期号</th><th>特码</th><th>旧V6</th><th>rot8</th><th>温号1</th><th>结果</th></tr>{tr}
</table></div>
<div class="note">232期 42牛: 旧V6漏 → rot8救回(轮转覆盖) · 223期 23: rot8漏 → 温号1救回 · 233期 07鼠: 模型全盲 → 内幕补位层单独解决(模型/内幕分离)</div>
</div>
</body></html>'''
out='/Users/xiejinyu/macau-mark6/local-trend.html'
open(out,'w').write(html)
print("已生成",out)
