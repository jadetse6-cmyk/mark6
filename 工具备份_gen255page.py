# -*- coding: utf-8 -*-
"""生成 255 期三层卡本地页面(仅本地, 不上线)。数据源: local-255-three-layer.txt + 引擎输出。"""

RED = set([1, 2, 7, 8, 12, 13, 18, 19, 23, 24, 29, 30, 34, 35, 40, 45, 46])
BLUE = set([3, 4, 9, 10, 14, 15, 20, 25, 26, 31, 36, 37, 41, 42, 47, 48])

ZOD = {}
_names = ['马', '蛇', '龙', '兔', '虎', '牛', '鼠', '猪', '狗', '鸡', '猴', '羊']
for i in range(1, 50):
    ZOD[i] = _names[(i - 1) % 12]

WX = {}
for _n in [4, 5, 12, 13, 26, 27, 34, 35, 42, 43]: WX[_n] = '金'
for _n in [8, 9, 16, 17, 24, 25, 38, 39, 46, 47]: WX[_n] = '木'
for _n in [1, 14, 15, 22, 23, 30, 31, 44, 45]: WX[_n] = '水'
for _n in [2, 3, 10, 11, 18, 19, 32, 33, 40, 41, 48, 49]: WX[_n] = '火'
for _n in [6, 7, 20, 21, 28, 29, 36, 37]: WX[_n] = '土'

# 码, 肖票, 码票(n/6), 车道, 漏, 频, 通道
D = [
    (3, 3, 4, '热', 49, 39, '补位'), (6, 3, 3, '热', 42, 49, 'sx'),
    (7, 3, 5, '温', 21, 28, '三层+sx'), (13, 2, 4, '冷', 107, 33, '补位'),
    (20, 1, 5, '重', 6, 39, 'sx'), (21, 3, 3, '重', 11, 35, 'sx'),
    (26, 2, 3, '热', 32, 35, '补位'), (28, 2, 4, '冷', 83, 33, 'sx'),
    (29, 1, 4, '冷', 63, 31, 'sx'), (34, 2, 4, '冷', 181, 22, '补位'),
    (36, 1, 4, '冷', 55, 31, 'sx'), (37, 2, 5, '温', 38, 27, 'sx'),
    (40, 2, 5, '重', 7, 37, '补位'), (42, 3, 4, '', 22, 35, '补位'),
    (45, 3, 5, '冷', 102, 32, '三层'),
]
REC = [7, 45, 20, 37, 28, 29, 36, 6, 21, 40, 3, 13]
SAFE = [34, 42, 26]

WCOL = {'red': '#dc2626', 'blue': '#2563eb', 'green': '#059669'}


def wave(n):
    if n in RED:
        return 'red'
    if n in BLUE:
        return 'blue'
    return 'green'


def ball(n, size=34):
    c = WCOL[wave(n)]
    return (f'<span class="ball" style="width:{size}px;height:{size}px;background:{c};'
            f'font-size:{size*0.42:.1f}px">{n:02d}</span>')


def row(nums, size=32):
    return '<div class="balls">' + ''.join(ball(n, size) for n in nums) + '</div>'


idx = {d[0]: d for d in D}
trows = []
for n in [d[0] for d in D]:
    _, zt, nt, ln, om, fq, ch = idx[n]
    cls = 'ch3' if ch == '三层+sx' else ('chf' if ch == '补位' else '')
    trows.append(
        f'<tr class="{cls}"><td><b>{n:02d}</b></td>'
        f'<td style="color:{WCOL[wave(n)]}">{ZOD[n]}</td>'
        f'<td>{WX[n]}</td><td>{zt}票</td><td>{nt}/6</td><td>{ln or "—"}</td>'
        f'<td>{om}</td><td>{fq}</td><td>{ch}</td></tr>')

html = f'''<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>255期 三层卡</title><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0b1220;color:#e2e8f0;font-family:-apple-system,"PingFang SC",sans-serif;padding:14px;line-height:1.5}}
h1{{text-align:center;color:#fbbf24;font-size:1.15rem}}
.sub{{text-align:center;color:#94a3b8;font-size:.72rem;margin:4px 0 14px}}
.card{{background:#111a2e;border:1px solid #233;border-radius:12px;padding:13px;margin:0 auto 11px;max-width:900px}}
.card h3{{color:#94a3b8;font-size:.82rem;margin-bottom:9px;font-weight:600}}
.balls{{display:flex;gap:7px;justify-content:center;flex-wrap:wrap;margin:6px 0}}
.ball{{display:inline-flex;border-radius:50%;color:#fff;font-weight:800;align-items:center;justify-content:center;box-shadow:0 2px 6px rgba(0,0,0,.5)}}
.tier{{margin-bottom:11px}}
.tlabel{{font-weight:700;font-size:.78rem;display:block;margin-bottom:4px}}
.t1 .tlabel{{color:#fbbf24}} .t2 .tlabel{{color:#38bdf8}} .t3 .tlabel{{color:#64748b}}
.note{{color:#64748b;font-size:.68rem;text-align:center;margin-top:6px}}
table{{border-collapse:collapse;width:100%;font-size:.72rem}}
th,td{{border:1px solid #2d3a52;padding:4px 5px;text-align:center}}
th{{color:#94a3b8;background:#0f1830;font-size:.67rem}}
tr.ch3{{background:#1a1710}} tr.chf{{background:#0f2430}}
.stats{{display:flex;gap:9px;flex-wrap:wrap;justify-content:center}}
.stat{{background:#0f1830;border:1px solid #2d3a52;border-radius:10px;padding:7px 13px;text-align:center;min-width:104px}}
.stat b{{display:block;font-size:1rem;color:#fbbf24}} .stat span{{font-size:.63rem;color:#94a3b8}}
.warn{{background:#1a1410;border-left:3px solid #fbbf24;padding:9px;border-radius:6px;font-size:.72rem;color:#cbd5e1;line-height:1.65}}
.warn b{{color:#fbbf24}}
.zod{{text-align:center;font-size:.74rem;color:#94a3b8;margin-top:7px}}
.zod b{{color:#e2e8f0}} .in{{color:#4ade80}} .out{{color:#fb923c}}
</style></head><body>
<h1>🎯 255 期 三层交集卡</h1>
<div class="sub">数据至 254 期 · 快照-255期(开奖前锁定, 无前视) · 开奖 2026-09-12 21:32 GMT+8（本地 17:32）</div>

<div class="card"><h3>整卡 15 码</h3>
{row([d[0] for d in D], 34)}
<div class="note">🔴红波 🔵蓝波 🟢绿波 · 圈内肖 <b>鼠牛龙狗</b>(各3票) · 码票满分 无(最高 5/6)</div></div>

<div class="card"><h3>分层</h3>
<div class="tier t1"><span class="tlabel">★ 推荐码 12</span>{row(REC, 33)}</div>
<div class="tier t2"><span class="tlabel">保底码 3</span>{row(SAFE, 33)}</div>
<div class="note">排序规则A（通道 → 码票 ↓ → 车道数 ↓ → 码号 ↑），只用当期已知信息</div></div>

<div class="card"><h3>本期结构 —— 交集塌成单行</h3>
<div class="warn">
<b>咕【火土木】∩ 羊【土水金】= 只有「土」</b> → <code>06 07 20 21 28 29 36 37</code>（8码），这就是 sx。<br>
<b>三层核心只有 2 码</b> <code>07 45</code> —— 本卡核心层贡献极小，主力全在 sx 与补位。<br>
最终池 = 三层核心 2 ∪ sx 8 ∪ 补位 6 = <b>15 码</b>。补位 6 码是本轮最大的一次补位。<br><br>
<b>⚠️ 五行覆盖极不均衡</b>：土行 8/8 <b>全中</b> · 金行 4/10 · 火行 2/12 · 水行 1/9 · <b>木行 0/10</b>。<br>
交集一刀砍掉「火」「木」两整行（咕独有=火、木；羊独有=水、金）。补位把 <code>42 26 13 34</code>（金）和 <code>40 03</code>（火）捞了回来，<b>但木行 10 码无一入池</b> —— 若本期开木行（08 09 16 17 24 25 38 39 46 47），本卡直接全灭。
</div>
<div class="zod">圈内4肖 <span class="in"><b>鼠牛龙狗</b></span> ｜ 圈外 <span class="out"><b>蛇兔马鸡</b>(2票) <b>猪虎猴羊</b>(1票)</span>（照例列出，不并池，经补位通道进池）</div>
</div>

<div class="card"><h3>逐码明细</h3>
<div style="overflow-x:auto"><table>
<tr><th>码</th><th>肖</th><th>五行</th><th>肖票</th><th>码票</th><th>车道</th><th>遗漏</th><th>频次</th><th>通道</th></tr>
{''.join(trows)}
</table></div>
<div class="note">金底=三层核心 · 蓝底=补位码 · 车道为模型层（热/冷/重/温）</div></div>

<div class="card"><h3>账目与治理</h3>
<div class="stats">
<div class="stat"><b>85%</b><span>滚动 216-254 (23/27)</span></div>
<div class="stat"><b>90.5%</b><span>真实段 234-254 (19/21)</span></div>
<div class="stat"><b>+20.9</b><span>期望 / 期</span></div>
<div class="stat"><b>9/10</b><span>近 10 期</span></div>
<div class="stat"><b>21.7码</b><span>均码 (真实段)</span></div>
</div>
<div class="warn" style="margin-top:10px">
<b>治理</b>：生肖·二国中特 60% ⚠️、红肖 50% ⚠️ 低于 67% 基线（左右二肖 70%）；号码·非内幕·头数 67% ⚠️(基线71%)。均无 2/3 连漏 → 不动作。<br>
外卡两个 🔥（头数中特必中 10/10、汉奸9肖 9/10）跑 auto_bt 加席双双 ❌ 不达标被拦（第五次拦截）。<br>
<b>漏期</b>：244、251。
</div></div>

<div class="card"><h3>⚠️ 概率提醒</h3>
<div class="warn">
本卡仅 <b>15 码 / 49 码 ≈ 31%</b> 覆盖，<b>随机命中率约 31%</b>，低于近期 20 码卡的 ~44%。<br>
真实段 19/21 = 90.5% 是在<b>均 21.7 码</b>的卡上取得的；<b>本卡明显偏小</b>，历史命中率不能直接套用。<br>
21 期样本下 1 期 = 4.8pp，90% 这个数字本身不确定性很大。分层（推荐12/保底3）的价值是<b>资金效率</b>，不是提高命中率。<br>
<b>叠加本期结构风险</b>：交集塌成土行单行 + 木行零覆盖，一旦偏离土/金行，卡的作用会明显弱于往期。
</div></div>

<div class="note" style="padding-bottom:20px">本地文件 · 不上线 · 生成源 local-255-three-layer.txt</div>
</body></html>'''

p = '/Users/xiejinyu/macau-mark6/local-255-pred.html'
open(p, 'w', encoding='utf-8').write(html)
print('已写入', p, len(html), '字节')
print('波色自检 253期:', [wave(x) for x in (5, 35, 15, 28, 13, 49, 16)],
      '(应 green,red,blue,green,red,green,green)')
print('生肖自检 253期:', [ZOD[x] for x in (5, 35, 15, 28, 13, 49, 16)], '(应 虎猴龙兔马马兔)')
print('五行自检 土行:', sorted([n for n in WX if WX[n] == '土']) == [6, 7, 20, 21, 28, 29, 36, 37],
      '| 覆盖五行数:', len({WX[n] for n in [d[0] for d in D]}))
print('卡自检:', sorted(d[0] for d in D) == sorted(REC + SAFE))
