#!/usr/bin/env python3
"""生成 本地参考页 (本地-only, 绝不上线): 大漏+高频观察池 + 纯模型21码对照 + 命中跟踪表
大漏+高频 = 漏≥80期 ∩ 频≥30次 (236期11号型: 漏116×频32)
2026年度命中12.3% vs 基线~10% (+2.3pp, 近100期+5.2pp z≈1.7临界)
2024-2025为深负 → 仅观察, 不进主策略
每期开奖后运行本脚本 → 跟踪表自动更新到最新期 (数据至X期)
"""
import sys
sys.path.insert(0, '/Users/xiejinyu')
import macau_model_4d as m4
from backtest_new import build_union

draws = m4.load()
k = len(draws)  # 已开奖期数 (数据至最后一期)
ISSUE = int(draws[-1]['i'][-3:]) + 1  # 下一期
tlt = k
LAST_ISSUE = int(draws[-1]['i'][-3:])

# ── 当前期池 (下一期预测参考) ──
sc = {}; sl = {}
for i, d in enumerate(draws[:k]):
    s = d['s']; sc[s] = sc.get(s, 0) + 1; sl[s] = i
leak = {n: tlt - 1 - sl.get(n, tlt) for n in range(1, 50)}
pool = [n for n in range(1, 50) if leak[n] >= 80 and sc.get(n, 0) >= 30]
pool.sort(key=lambda n: (-leak[n], -sc.get(n, 0)))

u20, w1 = build_union(k, rot=True, warm_n=1)
model = u20 + w1

REDS  = {1,2,7,8,12,13,18,19,23,24,29,30,34,35,40,45,46}
BLUES = {3,4,9,10,14,15,20,25,26,31,36,37,41,42,47,48}
def wave(n): return 'red' if n in REDS else ('blue' if n in BLUES else 'green')
WAVE_C = {'red':'#dc2626','blue':'#2563eb','green':'#059669'}

def ball(n, size=34):
    c = WAVE_C[wave(n)]
    return (f'<span style="display:inline-block;width:{size}px;height:{size}px;line-height:{size}px;'
            f'border-radius:50%;background:{c};color:#fff;font-weight:700;font-size:{size*0.40}px;'
            f'text-align:center;box-shadow:0 2px 6px rgba(0,0,0,.4)">{n:02d}</span>')

pool_html = ''.join(ball(n) for n in pool) or '<span class="none">本期无(漏≥80∩频≥30)</span>'
model_html = ''.join(ball(n) for n in model)
in_both = [n for n in pool if n in model]

# ── 命中跟踪表: 自210期起, 每期观察池+特码+命中 ──
def pool_at(t):
    tt = draws[:t]; tl = len(tt)
    sc2 = {}; sl2 = {}
    for i, d in enumerate(tt):
        s = d['s']; sc2[s] = sc2.get(s, 0) + 1; sl2[s] = i
    lk = {n: tl - 1 - sl2.get(n, tl) for n in range(1, 50)}
    return [n for n in range(1, 50) if lk[n] >= 80 and sc2.get(n, 0) >= 30], lk, sc2

START = 210
tr_rows = []
for iss in range(START, LAST_ISSUE + 1):
    idx = {int(d['i'][-3:]): i for i, d in enumerate(draws)}[iss]
    pp, lk, sc2 = pool_at(idx)
    s = draws[idx]['s']
    hit = s in pp
    tr_rows.append((iss, s, pp, hit))

n_all = len(tr_rows)
ok_all = sum(1 for r in tr_rows if r[3])
w50 = tr_rows[-50:]; w25 = tr_rows[-25:]
ok50 = sum(1 for r in w50 if r[3]); ok25 = sum(1 for r in w25 if r[3])
# 2026年段 (用最新年份期号映射, 避免跨年后3位重号)
idxmap = {int(d['i'][-3:]): i for i, d in enumerate(draws)}
y26 = [r for r in tr_rows if draws[idxmap[r[0]]]['i'][:4] == '2026']
ok26 = sum(1 for r in y26 if r[3])

# 表格行 (倒序, 最新在前, 最多显示40行)
show = tr_rows[::-1][:40]
tbl = ''
for iss, s, pp, hit in show:
    pp_s = ' '.join(f'{x:02d}' for x in pp) if pp else '-'
    tbl += (f'<tr class="{"hit" if hit else "miss"}"><td>{iss}期</td>'
            f'<td><span class="ball" style="background:{WAVE_C[wave(s)]}">{s:02d}</span></td>'
            f'<td>{pp_s}</td><td>{"🎯" if hit else "✗"}</td></tr>')

# 近12次命中明细
hits = [r for r in tr_rows if r[3]][::-1][:12]
hit_tbl = ''
for iss, s, pp, hit in hits:
    hit_tbl += (f'<tr><td>{iss}期</td><td><span class="ball" style="background:{WAVE_C[wave(s)]}">{s:02d}</span></td>'
                f'<td>{" ".join("%02d"%x for x in pp)}</td><td>🎯 池命中</td></tr>')

def rate_span(rates):
    return ' / '.join(f'{x[0]}/{x[1]}={x[2]*100:.0f}%' for x in rates)

html = f'''<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{ISSUE}期 本地参考 · 大漏+高频观察池</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0b1220;color:#e2e8f0;font-family:-apple-system,"PingFang SC",sans-serif;padding:16px}}
h1{{font-size:1.15rem;text-align:center;color:#fbbf24;margin-bottom:4px}}
.sub{{text-align:center;font-size:.72rem;color:#94a3b8;margin-bottom:14px}}
.card{{background:#111a2e;border:1px solid #233;border-radius:12px;padding:14px;margin:0 auto 12px;max-width:880px}}
.card h3{{color:#94a3b8;font-size:.85rem;margin-bottom:10px}}
.pool-card{{border-color:#60a5fa;background:#0e1a33}}
.pool-card h3{{color:#60a5fa}}
.note{{font-size:.68rem;color:#64748b;margin-top:8px;line-height:1.5}}
.none{{color:#94a3b8}}
table{{border-collapse:collapse;width:100%;font-size:.68rem}}
th,td{{border:1px dashed #2d3a52;padding:3px 5px;text-align:center}}
th{{color:#94a3b8;background:#0d1526}}
tr.hit td{{background:#132a22}}
tr.miss td{{color:#4a5a72}}
.balls{{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}}
.stat{{display:inline-block;background:#0d1526;border:1px solid #233;border-radius:8px;padding:6px 12px;margin:4px 8px 0 0;font-size:.72rem}}
.stat b{{color:#fbbf24;font-size:1rem}}
.warn{{color:#f87171;font-weight:700}}
.updated{{color:#fbbf24;font-weight:700}}
</style>
</head>
<body>
<h1>❄️ {ISSUE}期 本地参考页 · 大漏+高频观察池</h1>
<div class="sub">仅本地观察 · 不进主策略 · 不上线 · 数据至{LAST_ISSUE}期 · <span class="updated">跟踪表自210期起, 每期开奖后运行本脚本自动更新</span></div>

<div class="card pool-card"><h3>🆕 大漏+高频观察池 (漏≥80 ∩ 频≥30) · {len(pool)}码</h3>
<div class="balls">{pool_html}</div>
<div class="note">池内: {", ".join(f"{n:02d}(漏{leak[n]}·频{sc.get(n,0)})" for n in pool) if pool else "无"}</div>
</div>

<div class="card"><h3>🔵 纯模型21码对照 (rot8并集20 + 温号1) · 与观察池重合 {len(in_both)}码</h3>
<div class="balls">{model_html}</div>
<div class="note">重合: {", ".join("%02d"%n for n in in_both) if in_both else "无"} · 池外模型码说明观察池与主策略正交</div></div>

<div class="card"><h3>📈 观察池累计命中 (自{START}期 · {n_all}期)</h3>
<div class="stat"><b>{ok_all}/{n_all} · {ok_all/n_all*100:.0f}%</b><span>累计<br>基线约10%</span></div>
<div class="stat"><b>{ok50}/{len(w50)} · {ok50/len(w50)*100:.0f}%</b><span>近50期<br>基线约10%</span></div>
<div class="stat"><b>{ok25}/{len(w25)} · {ok25/len(w25)*100:.0f}%</b><span>近25期<br>基线约10%</span></div>
<div class="stat"><b>{ok26}/{len(y26)} · {ok26/len(y26)*100:.0f}%</b><span>2026年<br>基线约10%</span></div>
<div class="note">观察池平均4-5码 → 随机基线约8-10% · 判定: 20期连续命中≥5次(基线~4次)再考虑纳入模型</div></div>

<div class="card"><h3>🎯 近12次池命中明细</h3>
<div style="overflow-x:auto"><table>
<tr><th>期号</th><th>特码</th><th>当期池</th><th>结果</th></tr>{hit_tbl or '<tr><td colspan=4>暂无</td></tr>'}
</table></div>
<div class="note">倒序 · 2026年度12.3% vs 基线~10% (近100期+5.2pp z≈1.7临界) · 2024-2025为深负 → 数据积累效应, 非独立新信号</div></div>

<div class="card"><h3>📋 命中跟踪表 (自{START}期 · 最新{len(show)}期)</h3>
<div style="overflow-x:auto"><table>
<tr><th>期号</th><th>特码</th><th>当期观察池</th><th>命中</th></tr>{tbl}
</table></div>
<div class="note">灰=未命中 · 每期开奖后运行 <b>python3 gen_cold_pool_page.py</b> 自动追加最新一期</div></div>

<div class="card"><h3>⚠️ 使用规则</h3>
<div class="note">1. <span class="warn">不进主策略</span>: 并集21码+内幕补位仍是唯一主策略<br>
2. 观察池仅在页面参考: 若与主策略/内幕高票重叠, 可作信心增强, 不单独下注<br>
3. 跟踪20-50期: 若命中率持续 &gt;15% 再考虑纳入模型层</div></div>
</body>
</html>'''
out = f'/Users/xiejinyu/macau-mark6/local-{ISSUE}-cold-pool.html'
open(out, 'w').write(html)
print('已生成', out)
print(f'数据至{LAST_ISSUE}期 · {ISSUE}期池({len(pool)}码): {" ".join("%02d"%n for n in pool) if pool else "无"}')
print(f'累计 {ok_all}/{n_all}={ok_all/n_all*100:.0f}% · 近50 {ok50}/{len(w50)}={ok50/len(w50)*100:.0f}% · 近25 {ok25}/{len(w25)}={ok25/len(w25)*100:.0f}% · 2026 {ok26}/{len(y26)}={ok26/len(y26)*100:.0f}%')
