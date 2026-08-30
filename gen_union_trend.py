#!/usr/bin/env python3
"""并集 rot8+温号1 命中趋势表 (自210期累积) — 样式同线上网站趋势表
每期21位码格: 灰色=未命中 · 彩色球=命中(波色) · 末列=特码 · 汇总行 + 下期预测行
"""
import sys
sys.path.insert(0, '/Users/xiejinyu')
import macau_model_4d as m4
from backtest_new import build_union

REDS  = {1,2,7,8,12,13,18,19,23,24,29,30,34,35,40,45,46}
BLUES = {3,4,9,10,14,15,20,25,26,31,36,37,41,42,47,48}
def wave(n): return 'red' if n in REDS else ('blue' if n in BLUES else 'green')
WAVE_C = {'red':'#dc2626','blue':'#2563eb','green':'#059669'}

draws = m4.load()
idx = {int(d['i'][-3:]): k for k, d in enumerate(draws)}

START, END = 210, 236  # 当期号体系连续段 (数据至236期)
rows = []  # (期号, 特码, 21码列表, 是否命中)
for iss in range(START, END + 1):
    if iss not in idx:
        continue
    k = idx[iss]
    u20, w1 = build_union(k, rot=True, warm_n=1)
    model = u20 + w1
    s = draws[k]['s']
    rows.append((iss, s, model, s in model))

n = len(rows)
ok = sum(1 for r in rows if r[3])
# 汇总: 每位命中次数
pos_hits = [0] * 21
for iss, s, model, hit in rows:
    for p, num in enumerate(model):
        if num == s: pos_hits[p] += 1

def ball(num, size=24):
    c = WAVE_C[wave(num)]
    return (f'<span style="display:inline-block;width:{size}px;height:{size}px;line-height:{size}px;'
            f'border-radius:50%;background:{c};color:#fff;font-weight:700;font-size:{size*0.42}px;'
            f'text-align:center;box-shadow:0 2px 6px rgba(0,0,0,.4)">{num}</span>')

trs = ''
for iss, s, model, hit in rows:
    cells = [f'<td class="iss">{iss}</td>']
    for p, num in enumerate(model):
        if num == s:
            cells.append(f'<td class="hit">{ball(num)}</td>')
        else:
            cells.append(f'<td class="miss">{num}</td>')
    cells.append(f'<td>{ball(s, 30)}</td>')
    trs += '<tr>' + ''.join(cells) + '</tr>'

# 汇总行: 每位累计命中
sum_cells = ['<td class="iss">累计</td>']
for p in range(21):
    v = pos_hits[p]
    hot = ' hot' if v >= 5 else ''
    sum_cells.append(f'<td class="sum{hot}">{v}</td>')
sum_cells.append(f'<td class="sum hot">{ok}/{n}</td>')
sum_tr = '<tr class="sum">' + ''.join(sum_cells) + '</tr>'

# 预测行: 下一期 (数据至最新开奖, k=len(draws))
k = len(draws)
ISSUE = int(draws[-1]['i'][-3:]) + 1
u20, w1 = build_union(k, rot=True, warm_n=1)
pred = u20 + w1
pred_cells = ['<td class="iss">%d期</td>' % ISSUE]
for num in pred:
    pred_cells.append(f'<td class="pred">{num}</td>')
pred_cells.append('<td class="pred">?</td>')
pred_tr = '<tr class="pred">' + ''.join(pred_cells) + '</tr>'

# 状态信号行已按纠错红线移除 (2026-08-24): 近5期池命中的"高/中/低"状态是码数混淆+2026后验, 已证伪
# 策略 = 恒定池21码(rot8+温号1) + 内幕补位 = 22码, 均注, 无切换
rec = rows[-5:]
span = f"{rec[0][0]}-{rec[-1][0]}期"
state_html = (f'<div class="state">📡 近5期({span})池命中 {sum(1 for r in rec if r[3])}/5 · '
              f'<b>策略: 恒定池21码(rot8+温号1)+内幕补位=22码, 均注, 不切换</b>'
              f'（状态信号已证伪: 码数混淆+2026后验, 勿按状态加注）</div>')

html = f'''<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>并集 rot8+温号1 命中趋势表</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0b1220;color:#e2e8f0;font-family:-apple-system,"PingFang SC",sans-serif;padding:16px}}
h1{{font-size:1.15rem;text-align:center;margin-bottom:4px;color:#fbbf24}}
.sub{{text-align:center;font-size:.72rem;color:#94a3b8;margin-bottom:14px}}
table{{border-collapse:collapse;width:100%;max-width:1200px;margin:0 auto;font-size:.6rem}}
th,td{{border:1px dashed #2d3a52;padding:2px 3px;text-align:center}}
th{{color:#94a3b8;font-weight:600;background:#111a2e}}
td.iss{{color:#94a3b8;font-weight:600}}
td.miss{{color:#4a5a72;font-size:.55rem}}
td.hit{{background:#132a22}}
tr.sum td{{font-weight:700;color:#94a3b8;border-top:2px solid #334155}}
tr.sum td.hot{{color:#fbbf24}}
tr.pred td{{background:#1a2332}}
tr.pred td:first-child{{color:#fbbf24;font-weight:700}}
tr.pred td.pred{{color:#e2e8f0;font-weight:700}}
.legend{{text-align:center;font-size:.65rem;color:#64748b;margin-top:12px}}
.rate{{text-align:center;font-size:.85rem;margin-top:8px}}
.rate b{{color:#34d399}}
.state{{text-align:center;font-size:.75rem;margin:8px auto 10px;padding:6px 10px;max-width:1000px;border:1px dashed #334155;border-radius:8px;background:#0e1626}}
.state .hi{{color:#34d399;font-weight:700}}
.state .mid{{color:#fbbf24;font-weight:700}}
.state .lo{{color:#f87171;font-weight:700}}
.state b{{color:#e2e8f0}}
</style>
</head>
<body>
<h1>🔥 并集 rot8+温号1 命中趋势表</h1>
<div class="sub">热1-3,7-10(频≥25,漏15-62) / 冷1-3+6+10-12(漏top12,奇偶轮转) / 重top5(频≥30,漏2-10) / 温1 · 自210期累积 · 滚动回测(仅历史数据)</div>
<div class="rate">累计命中 <b>{ok}/{n}</b> = <b>{ok/n*100:.0f}%</b>（随机基线 {21/49*100:.0f}% · 期望 {ok/n*47-21:+.1f}/期）</div>
{state_html}
<table>
<tr><th>期号</th>{''.join(f'<th>{p+1}</th>' for p in range(21))}<th>特码</th></tr>
{trs}
{sum_tr}
{pred_tr}
</table>
<div class="legend">灰色=并集预测号 · 彩色球=命中(波色) · 汇总行=各码位累计命中(≥5次金色) · 状态行=近5期池命中数(展示用, 状态信号已证伪勿作加注依据) · 最后一行=下期预测</div>
</body>
</html>'''
out = '/Users/xiejinyu/macau-mark6/union-trend-rot8.html'
open(out, 'w').write(html)
print('已生成', out)
print(f'累计 {ok}/{n} = {ok/n*100:.0f}%  期望 {ok/n*47-21:+.1f}/期')
print(f'{ISSUE}期预测: {" ".join("%02d"%x for x in pred)}')
