# -*- coding: utf-8 -*-
"""查"摘席后卡是否单调不缩"。若不单调, 找出反例并定位是哪一步缩的。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_three_layer as g

ZW = list(g.ZW_LIST)
NW = list(g.NW_LIST)


def load(i):
    snap = f'{g.SNAP_DIR}/快照-{i}期.txt'
    if os.path.exists(snap):
        return g.parse_zodiac(snap), g.parse_number(snap)
    return g.parse_zodiac(), g.parse_number()


def card(i, wl_zw, wl_nw):
    g.ZW_LIST, g.NW_LIST = wl_zw, wl_nw
    per, NS = load(i)
    r = g.three_layer(per, NS, i, g.idx[2026000 + i])
    if r is None:
        return None
    fills = [g.hot_rec(g.idx[2026000 + i], z) for z in g.bare_zodiac(r)]
    sx = g.sx_union(NS, i)
    return dict(final=set(r['final']), fills=set(fills), sx=sx,
                card=set(r['final']) | set(fills) | sx,
                CI=r['CI'], zn=r['zn'])


PER = [i for i in range(234, g.LAST + 1) if 2026000 + i in g.idx]
print(f'窗口 {PER[0]}~{PER[-1]}\n')

for seat in ZW:
    sub = [x for x in ZW if x != seat]
    shrink = []
    for i in PER:
        a = card(i, ZW, NW)
        b = card(i, sub, NW)
        if not a or not b:
            continue
        if not a['card'] <= b['card']:
            lost = sorted(a['card'] - b['card'])
            shrink.append((i, lost, a, b))
    print(f'摘 {seat:<8} 卡非超集(丢码)的期数: {len(shrink)}')
    for i, lost, a, b in shrink[:4]:
        s = g.draws[g.idx[2026000 + i]]['s']
        print(f'   {i}期 丢码 {lost} 特码={s} ({"命中" if s in a["card"] else "漏"}→'
              f'{"命中" if s in b["card"] else "漏"})')
        print(f'        基线:|final|={len(a["final"])} |fill|={len(a["fills"])} '
              f'|sx|={len(a["sx"])} 卡={len(a["card"])} 圈肖={sorted(a["CI"])}')
        print(f'        摘后:|final|={len(b["final"])} |fill|={len(b["fills"])} '
              f'|sx|={len(b["sx"])} 卡={len(b["card"])} 圈肖={sorted(b["CI"])}')
        print(f'        基线final={sorted(a["final"])}')
        print(f'        摘后final={sorted(b["final"])}')

g.ZW_LIST, g.NW_LIST = ZW, NW
