# -*- coding: utf-8 -*-
"""换席搜索: 把未启用的内幕席位换进白名单, 全组合回测 + 样本外(滚动)验证。

为什么要样本外: 记忆红线 —— 本项目实测"每期只用之前数据挑规则"的滚动优选
只有 3/11=27%, 输给任何固定规则。样本内挑出来的赢家极可能是过拟合。
所以两条都跑, 只有样本外也赢的才值得谈。
"""
import sys, os, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_three_layer as g

ZW0 = list(g.ZW_LIST)
NW0 = list(g.NW_LIST)
PER = [i for i in range(234, g.LAST + 1) if 2026000 + i in g.idx]

# ── 快照缓存: 每期只解析一次 ──
CACHE = {}
for i in PER:
    snap = f'{g.SNAP_DIR}/快照-{i}期.txt'
    if os.path.exists(snap):
        CACHE[i] = (g.parse_zodiac(snap), g.parse_number(snap))
    else:
        CACHE[i] = (g.parse_zodiac(), g.parse_number())
S = {i: g.draws[g.idx[2026000 + i]]['s'] for i in PER}


def evalc(ZW, NW):
    """→ 逐期 (是否命中, 卡大小) ; 某期出不了卡记为 None"""
    g.ZW_LIST, g.NW_LIST = ZW, NW
    out = []
    for i in PER:
        per, NS = CACHE[i]
        r = g.three_layer(per, NS, i, g.idx[2026000 + i])
        if r is None:
            out.append(None)
            continue
        fills = [g.hot_rec(g.idx[2026000 + i], z) for z in g.bare_zodiac(r)]
        card = set(r['final']) | set(fills) | g.sx_union(NS, i)
        out.append((S[i] in card, len(card)))
    return out


def agg(res):
    v = [x for x in res if x]
    tot = len(v)
    if not tot:
        return dict(tot=0, hit=0, cod=0.0, exp=0.0)
    hit = sum(1 for h, _ in v if h)
    cod = sum(c for _, c in v) / tot
    return dict(tot=tot, hit=hit, cod=cod, exp=hit / tot * 47 - cod)


# ── 候选席位 ──
Z_CAND = ['琴棋书画', '五肖', '东南西北', '汉奸9肖', '笔墨纸砚', '天地中特',
          '绝杀三肖9肖', '绝杀三肖9肖2', '文武中特', '天地中特2', '家禽']
N_CAND = ['头数中特必中', '非内幕·尾数', '非内幕·单双', '单双', '规律大小']

configs = {'【基线】现状': (ZW0, NW0)}
for c in Z_CAND:
    configs[f'加 生肖·{c}'] = (ZW0 + [c], NW0)
    for s in ZW0:
        configs[f'换 生肖·{s}→{c}'] = ([x for x in ZW0 if x != s] + [c], NW0)
for c in N_CAND:
    configs[f'加 号码·{c}'] = (ZW0, NW0 + [c])
    for s in NW0:
        configs[f'换 号码·{s}→{c}'] = (ZW0, [x for x in NW0 if x != s] + [c])

print(f'共 {len(configs)} 个配置, 窗口 {PER[0]}~{PER[-1]} ({len(PER)}期), 逐期评估中...', flush=True)
M = {}
for tag, (zw, nw) in configs.items():
    M[tag] = evalc(zw, nw)

base = agg(M['【基线】现状'])
print(f'\n【基线】现状  {base["hit"]}/{base["tot"]}  {base["cod"]:.1f}码  {base["exp"]:+.1f}/期\n')

print('══ 样本内排行 (全部 21 期, 只看 tot=21 的) ══')
rows = []
for tag in configs:
    a = agg(M[tag])
    if a['tot'] == len(PER):
        rows.append((tag, a))
rows.sort(key=lambda x: (-x[1]['hit'], -x[1]['exp']))
for tag, a in rows[:14]:
    mark = ' ←基线' if tag == '【基线】现状' else ''
    d = a['hit'] - base['hit']
    print(f'  {tag:<30}{a["hit"]:>2}/{a["tot"]}  {a["cod"]:>5.1f}码  {a["exp"]:>+6.1f}/期  '
          f'({d:+d}){mark}')
print(f'  ... 共 {len(rows)} 个配置可比')

# ── 样本外: 滚动优选 ──
print('\n══ 样本外 (滚动: 每期只用之前数据挑配置) ══')
START = 10   # PER 的【下标】: 用前10期(234-243)当历史, 从244起滚动
wf_hit = wf_cod = wf_n = 0
picks = []
for t in range(START, len(PER)):
    best, bs = None, None
    for tag in configs:
        h = [M[tag][k] for k in range(t) if M[tag][k]]
        if len(h) < t * 0.9:      # 之前期必须基本都能出卡
            continue
        hit = sum(1 for x, _ in h if x)
        cod = sum(c for _, c in h) / len(h)
        sc = (hit, hit / len(h) * 47 - cod)
        if bs is None or sc > bs:
            bs, best = sc, tag
    cur = M[best][t]
    if cur:
        picks.append((PER[t], best, cur[0]))
        wf_hit += cur[0]; wf_cod += cur[1]; wf_n += 1
print(f'  滚动优选结果: {wf_hit}/{wf_n}  {wf_cod/wf_n:.1f}码  '
      f'{wf_hit/wf_n*47 - wf_cod/wf_n:+.1f}/期')
hr = [M['【基线】现状'][k] for k in range(START, len(PER)) if M['【基线】现状'][k]]
print(f'  同期基线    : {sum(1 for x,_ in hr if x)}/{len(hr)}  '
      f'{sum(c for _,c in hr)/len(hr):.1f}码  '
      f'{sum(1 for x,_ in hr if x)/len(hr)*47 - sum(c for _,c in hr)/len(hr):+.1f}/期')
from collections import Counter
print('  实际挑了哪些:', Counter(p[1] for p in picks).most_common(5))
