# -*- coding: utf-8 -*-
"""治理回测: 摘席 / 加席 对组合的影响。
口径与引擎 run() 内 auto_bt 完全一致 (234~LAST, 快照口径优先, 去重并集整卡)。
红线: 席位自身命中率低 ≠ 可砍 —— 摘席会同时降低门槛, 必须只看组合回测。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_three_layer as g

BASE_ZW = list(g.ZW_LIST)
BASE_NW = list(g.NW_LIST)


def bt(ZW, NW):
    g.ZW_LIST, g.NW_LIST = ZW, NW
    tot = hit = cod = 0
    miss = []
    for i in range(234, g.LAST + 1):
        f = 2026000 + i
        if f not in g.idx:
            continue
        snap = f'{g.SNAP_DIR}/快照-{i}期.txt'
        if __import__('os').path.exists(snap):
            per_i, NS_i = g.parse_zodiac(snap), g.parse_number(snap)
        else:
            per_i, NS_i = g.parse_zodiac(), g.parse_number()
        r = g.three_layer(per_i, NS_i, i, g.idx[f])
        if r is None:
            continue
        s = g.draws[g.idx[f]]['s']
        fills = [g.hot_rec(g.idx[f], z) for z in g.bare_zodiac(r)]
        card = set(r['final']) | set(fills) | g.sx_union(NS_i, i)
        ok = s in card
        tot += 1
        hit += ok
        cod += len(card)
        if not ok:
            miss.append(i)
    exp = hit / tot * 47 - cod / tot if tot else 0.0
    return dict(tot=tot, hit=hit, cod=cod / tot if tot else 0.0, exp=exp, miss=miss)


def show(tag, ZW, NW):
    r = bt(ZW, NW)
    if r['tot'] == 0:
        # 0/0 不是"零命中", 是这配置一期卡都出不来(层闸门拦掉) —— 必须说清楚, 否则像模像样地骗人
        print(f'{tag:<34} ❌ 全部期出不了卡 (层闸门拦截, 非零命中)')
        return r
    print(f'{tag:<34} {r["hit"]:>2}/{r["tot"]}  {r["cod"]:>5.1f}码  '
          f'{r["exp"]:>+6.1f}/期  漏{r["miss"]}')
    return r


print(f'基线白名单 生肖={BASE_ZW}')
print(f'           号码={BASE_NW}')
print(f'窗口 234~{g.LAST}  (快照口径)\n')

base = show('【基线】现状', BASE_ZW, BASE_NW)
print('\n──── 摘席 (⚠️ 低命中席位, 每次摘一个) ────')
for seat in ['二国中特', '红肖', '非内幕·头数']:
    if seat in BASE_ZW:
        show(f'摘 {seat}', [x for x in BASE_ZW if x != seat], BASE_NW)
    else:
        show(f'摘 {seat}', BASE_ZW, [x for x in BASE_NW if x != seat])

print('\n──── 摘席 (三个 ⚠️ 一起摘) ────')
show('摘 二国+红肖+头数',
     [x for x in BASE_ZW if x not in ('二国中特', '红肖')],
     [x for x in BASE_NW if x != '非内幕·头数'])

print('\n──── 加席 (🔥 热外卡) ────')
show('加 头数中特必中', BASE_ZW, BASE_NW + ['头数中特必中'])
show('加 汉奸9肖', BASE_ZW + ['汉奸9肖'], BASE_NW)
show('加 两个 🔥', BASE_ZW + ['汉奸9肖'], BASE_NW + ['头数中特必中'])

print('\n──── 换席 (摘⚠️ 换 🔥) ────')
show('摘红肖 → 加汉奸', [x for x in BASE_ZW if x != '红肖'] + ['汉奸9肖'], BASE_NW)
show('摘头数 → 加头数中特必中',
     BASE_ZW, [x for x in BASE_NW if x != '非内幕·头数'] + ['头数中特必中'])
show('摘二国+红肖 → 加汉奸', [x for x in BASE_ZW if x not in ('二国中特', '红肖')] + ['汉奸9肖'], BASE_NW)
