#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生肖层透视: 逐期拆出生肖层到底贡献了什么 (快照优先, 无快照期标"前视")。

用法: python3 tools_zodiac_view.py [起始期]      # 默认 234

回答三个问题:
  ① 肖级: 特肖落在圈内/圈外的比例 vs 随机基线(圈肖数/12)
  ② 票数: 3票(圈)/2票/1票/0票 各档命中占比 —— 票数对选肖有没有选择力
  ③ 通道: 生肖层产出(final∪补位) 与 sx 各自独立能不能命中; 生肖层独有码救回哪几期
代码坑(记忆红线): g.draws[t]['s'] 是特码【号码】不是肖, 必须 g.Z[s] 转换。
"""
import os
import sys
from collections import Counter, defaultdict

import gen_three_layer as g

START = int(sys.argv[1]) if len(sys.argv) > 1 else 234
per, NS = g.parse_zodiac(), g.parse_number()

rec = []
for i in range(START, g.LAST + 1):
    f = 2026000 + i
    if f not in g.idx:
        continue
    snap = f'{g.SNAP_DIR}/快照-{i}期.txt'
    clean = os.path.exists(snap)
    per_i, NS_i = (g.parse_zodiac(snap), g.parse_number(snap)) if clean else (per, NS)
    r = g.three_layer(per_i, NS_i, i, g.idx[f])
    if r is None:
        continue
    s = g.draws[g.idx[f]]['s']
    z = g.Z[s]
    fills = [g.hot_rec(g.idx[f], zz) for zz in g.bare_zodiac(r)]
    sx = g.sx_union(NS_i, i)
    zout = set(r['final']) | set(fills)            # 生肖层产出
    card = zout | sx
    rec.append(dict(i=i, s=s, z=z, clean=clean, votes=r['zc'][z], zn=r['zn'],
                    nci=len(r['CI']), inci=z in r['CI'], nfinal=len(r['final']),
                    fills=fills, zout=zout, sx=sx, card=card,
                    hit_final=s in r['final'], hit_fill=s in fills,
                    hit_sx=s in sx, hit_card=s in card,
                    only_zod=(s in (zout - sx)), only_sx=(s in (sx - zout))))

clean_rec = [x for x in rec if x['clean']]
dirty = [x['i'] for x in rec if not x['clean']]
print(f'══ 生肖层透视 {START}-{g.LAST} ({len(rec)}期; 快照口径 {len(clean_rec)}期'
      f'{", 无快照(前视)=" + str(dirty) if dirty else ""}) ══\n')

# ── ① 肖级 ──
for tag, rr in (('全窗口', rec), ('仅快照期', clean_rec)):
    if not rr:
        continue
    hz = sum(1 for x in rr if x['inci'])
    base = sum(x['nci'] / 12 for x in rr) / len(rr)
    print(f'① 肖级({tag} {len(rr)}期): 特肖∈圈 {hz}/{len(rr)} = {hz/len(rr)*100:.1f}% '
          f'| 圈均 {base*12:.1f}肖 = 随机基线 {base*100:.1f}% | 净 {hz/len(rr)*100-base*100:+.1f}pp')

# ── ② 票数分层 (票数=该肖拿到的白名单席位票) ──
print('\n② 特肖票数分层 (圈线=3票/3席; 每肖随机基线 1/12=8.3%):')
vc = Counter(x['votes'] for x in rec)
for v in sorted(vc, reverse=True):
    k = vc[v]
    tag = '← 圈内' if v >= 3 else ('裸肖' if v == 2 else '圈外')
    print(f'   {v}票: {k:>2}期 = {k/len(rec)*100:>5.1f}%  (随机 8.3%)  {tag}')

# ── ③ 通道 ──
print('\n③ 命中通道 (互相独立看, 不等于整卡):')
f_hit = sum(1 for x in rec if x['hit_final'])
fl_hit = sum(1 for x in rec if x['hit_fill'])
z_hit = sum(1 for x in rec if x['s'] in x['zout'])
sx_hit = sum(1 for x in rec if x['hit_sx'])
c_hit = sum(1 for x in rec if x['hit_card'])
n = len(rec)
for name, h, sz in (('生肖·final(三层核心)', f_hit, sum(x['nfinal'] for x in rec)/n),
                    ('生肖·补位', fl_hit, sum(len(x['fills']) for x in rec)/n),
                    ('生肖层整体(final∪补位)', z_hit, sum(len(x['zout']) for x in rec)/n),
                    ('sx 三行双源', sx_hit, sum(len(x['sx']) for x in rec)/n),
                    ('整卡(final∪补位∪sx)', c_hit, sum(len(x['card']) for x in rec)/n)):
    print(f'   {name:<22} {h:>2}/{n} = {h/n*100:>5.1f}%  均{sz:.1f}码  '
          f'期望{h/n*47-sz:+.1f}/期')
print(f'   只生肖层能中(sx没有)  : {sum(1 for x in rec if x["only_zod"])}期 '
      f'{[x["i"] for x in rec if x["only_zod"]]}')
print(f'   只sx能中(生肖层没有)  : {sum(1 for x in rec if x["only_sx"])}期 '
      f'{[x["i"] for x in rec if x["only_sx"]]}')
print(f'   两边都漏              : {[x["i"] for x in rec if not x["hit_card"]]}')

# ── ④ 逐期表 ──
print('\n④ 逐期:')
for x in rec:
    ch = ''.join(t for t, ok in (('核心', x['hit_final']), ('补位', x['hit_fill']),
                                 ('sx', x['hit_sx'])) if ok) or '全灭'
    print(f'  {x["i"]} 特{x["s"]:>2}{x["z"]} 票{x["votes"]} '
          f'({"圈内" if x["inci"] else "圈外"}) 核心{x["nfinal"]:>2}码 '
          f'补位{len(x["fills"])} sx{len(x["sx"]):>2}码 卡{len(x["card"]):>2}码 '
          f'{"✅" if x["hit_card"] else "❌"} {ch}{"" if x["clean"] else " [前视]"}')
