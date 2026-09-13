# -*- coding: utf-8 -*-
"""拆解"摘席=降门槛"这条解释: 门槛效应 vs 票数效应各占多少。
比较 基线 与 摘席 在每个历史期的: 有效席位数N / 整数门槛(ceil(N*0.67)) / 圈内规模。
"""
import sys, os, math
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_three_layer as g

ZW = list(g.ZW_LIST)
NW = list(g.NW_LIST)


def load(i):
    snap = f'{g.SNAP_DIR}/快照-{i}期.txt'
    if os.path.exists(snap):
        return g.parse_zodiac(snap), g.parse_number(snap)
    return g.parse_zodiac(), g.parse_number()


def zstats(per, iss, wl):
    vz = {a: b for a, b in per.get(iss, {}).get('sys', {}).items()
          if a in wl and 0 < len(b) < 10}
    if not vz:
        return None
    N = len(vz)
    zc = Counter()
    for v in vz.values():
        zc.update(v)
    need = math.ceil(N * 0.67)          # 整数票门槛
    circ = {z for z in g.ZS12 if zc[z] >= N * 0.67}
    return N, need, len(circ)


def nstats(NS, iss, wl):
    nd = {a: b for a, b in NS.get(iss, {}).items() if a in wl}
    if not nd:
        return None
    N = len(nd)
    nv = Counter()
    for s in nd.values():
        nv.update(s)
    need = math.ceil(N * 0.67)
    circ = {n for n in range(1, 50) if nv[n] >= N * 0.67}
    return N, need, len(circ)


PER = [i for i in range(234, g.LAST + 1) if 2026000 + i in g.idx]
print(f'窗口 {PER[0]}~{PER[-1]} 共 {len(PER)} 期\n')

print('══ 生肖层 ══')
print(f'{"配置":<28}{"平均N":>7}{"平均门槛":>9}{"平均圈内肖":>11}')
rows = [('基线(3席)', ZW)]
for s in ZW:
    rows.append((f'摘 {s}', [x for x in ZW if x != s]))
for tag, wl in rows:
    Ns, needs, circs = [], [], []
    for i in PER:
        per, NS = load(i)
        r = zstats(per, i, wl)
        if r:
            Ns.append(r[0]); needs.append(r[1]); circs.append(r[2])
    print(f'{tag:<28}{sum(Ns)/len(Ns):>7.2f}{sum(needs)/len(needs):>9.2f}{sum(circs)/len(circs):>11.2f}')

print('\n══ 号码层 ══')
print(f'{"配置":<28}{"平均N":>7}{"平均门槛":>9}{"平均圈内码":>11}')
rows = [('基线(7席)', NW)]
for s in NW:
    rows.append((f'摘 {s}', [x for x in NW if x != s]))
for tag, wl in rows:
    Ns, needs, circs = [], [], []
    for i in PER:
        per, NS = load(i)
        r = nstats(NS, i, wl)
        if r:
            Ns.append(r[0]); needs.append(r[1]); circs.append(r[2])
    print(f'{tag:<28}{sum(Ns)/len(Ns):>7.2f}{sum(needs)/len(needs):>9.2f}{sum(circs)/len(circs):>11.2f}')

print('\n══ 门槛是否真的变化 (逐席, 与基线比整数门槛) ══')
for layer, wl, fn in [('生肖', ZW, 'z'), ('号码', NW, 'n')]:
    for s in wl:
        sub = [x for x in wl if x != s]
        chg = same = 0
        for i in PER:
            per, NS = load(i)
            a = zstats(per, i, wl) if fn == 'z' else nstats(NS, i, wl)
            b = zstats(per, i, sub) if fn == 'z' else nstats(NS, i, sub)
            if not a or not b:
                continue
            if a[1] == b[1]:
                same += 1
            else:
                chg += 1
        print(f'  {layer}·摘 {s:<14} 门槛变化 {chg} 期 / 不变 {same} 期')
