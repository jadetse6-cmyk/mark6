#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""学习体检报告 —— 读 lc_*_curves_20261010.npz + lc_*_20261010.npz, 打表。

    python3 nn/lc_report.py

口径: 每单元 = (折, 种子); 验证段长 100 期 ⇒ top14 随机期望 28.57, top21 = 42.86。
只用已有产物算数, 不产生任何新数字来源。
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(_HERE, 'runs')
LN49 = float(np.log(49))
LEGS = [('真实', 'lc_aux_real'), ('打乱', 'lc_aux_shuffle'),
        ('植入 q=0.50', 'lc_plant50'), ('植入 q=0.10', 'lc_plant10'),
        ('植入 q=0.05', 'lc_plant05'), ('植入 q=0.02', 'lc_plant02')]


def per_unit(z):
    """→ 逐 (折,种子) 单元的读数列表。"""
    tr, va, h14, h21 = z['tr_loss'], z['va_loss'], z['va_h14'], z['va_h21']
    be, se = z['best_ep'], z['stop_ep']
    F, S, _E = tr.shape
    rows = []
    for f in range(F):
        for s in range(S):
            n = int(se[f, s])
            b = int(be[f, s])
            rows.append(dict(
                tr0=float(tr[f, s, 0]), trL=float(tr[f, s, n - 1]),
                va0=float(va[f, s, 0]), vaB=float(va[f, s, b]), vaL=float(va[f, s, n - 1]),
                h0=int(h14[f, s, 0]), hB=int(h14[f, s, b]), hL=int(h14[f, s, n - 1]),
                h0_21=int(h21[f, s, 0]), hB_21=int(h21[f, s, b]), hL_21=int(h21[f, s, n - 1]),
                hm=int(np.nanmax(h14[f, s])), hm_21=int(np.nanmax(h21[f, s])),
                be=b, n=n))
    return rows


def mean(xs):
    return float(np.mean(xs))


def med(xs):
    return float(np.median(xs))


def main():
    # ── 自检: 真实腿 members 应对 nn8_aux_ext_20261007 逐位一致 ──
    print('── 自检 ──')
    ok_all = True
    try:
        a = np.load(os.path.join(R, 'lc_aux_real_20261010.npz'))
        b = np.load(os.path.join(R, 'nn8_aux_ext_20261007.npz'))
        same = np.array_equal(a['members'], b['members']) and np.array_equal(a['tgt'], b['tgt'])
        ok_all &= same
        print('  lc_aux_real members vs nn8_aux_ext_20261007: %s' % ('逐位一致 ✅' if same else '🔴 不一致'))
    except FileNotFoundError as e:
        ok_all = False
        print('  缺文件: %s' % e)

    # ── 学习曲线对照 ──
    print()
    print('── 学习动态 (每格 = 折×种子的一个单元, 共 112; 验证段 100 期) ──')
    stat = {}
    for name, tag in LEGS:
        z = np.load(os.path.join(R, tag + '_curves_20261010.npz'))
        rows = per_unit(z)
        stat[name] = rows
        f = lambda k: mean([r[k] for r in rows])
        print()
        print('【%s】' % name)
        print('  训练损失  首 %.3f → 末 %.3f  (下降 %+.1f%%)'
              % (f('tr0'), f('trL'), (f('trL') - f('tr0')) / f('tr0') * 100))
        print('  验证损失  首 %.4f → 最低 %.4f (中位 ep %.0f) → 末 %.4f   | 最低/ln49 = %.4f'
              % (f('va0'), f('vaB'), med([r['be'] for r in rows]), f('vaL'), f('vaB') / LN49))
        print('  验证top14 首 %.1f → 最低损失处 %.1f → 峰值 %.1f (中位 ep %.0f) → 末 %.1f  (随机 28.6)'
              % (f('h0'), f('hB'), f('hm'), med([r['hm'] for r in rows]), f('hL')))
        print('  验证top21 首 %.1f → 最低损失处 %.1f → 峰值 %.1f → 末 %.1f  (随机 42.9)'
              % (f('h0_21'), f('hB_21'), f('hm_21'), f('hL_21')))
        n_early = sum(1 for r in rows if r['n'] < 300)
        print('  早停: %d/112 提前停, 实跑 epoch 中位 %.0f' % (n_early, med([r['n'] for r in rows])))

    # ── 正对照: 标准读数 ──
    print()
    print('── 正对照 · 标准样本外读数 (1434 期, 口径 = eval_topk) ──')
    for name, tag in LEGS:
        if not tag.startswith('lc_plant'):
            continue
        z = np.load(os.path.join(R, tag + '_20261010.npz'))
        zc = np.load(os.path.join(R, tag + '_curves_20261010.npz'))
        mem, ens, tgt = z['members'], z['ens'], z['tgt']
        y = tgt - 1

        def hit(sc):
            od = np.argsort(-sc, axis=1)
            h14 = int((od[:, :14] == y[:, None]).any(1).sum())
            h21 = int((od[:, :21] == y[:, None]).any(1).sum())
            return h14, h21
        e14, e21 = len(y) * 14 / 49, len(y) * 21 / 49
        m14 = np.array([hit(m)[0] for m in mem], dtype=float)
        m21 = np.array([hit(m)[1] for m in mem], dtype=float)
        h14, h21 = hit(ens)
        z14 = (h14 - e14) / np.sqrt(len(y) * (14 / 49) * (1 - 14 / 49))
        z21 = (h21 - e21) / np.sqrt(len(y) * (21 / 49) * (1 - 21 / 49))
        rows = stat[name]
        print()
        print('【%s】集成 top14 %d/%d 提升 %+.1f%% z=%+.2f | top21 %d/%d 提升 %+.1f%% z=%+.2f'
              % (name, h14, len(y), (h14 - e14) / e14 * 100, z14,
                 h21, len(y), (h21 - e21) / e21 * 100, z21))
        print('    成员 top14 提升 %+.1f%% ~ %+.1f%% (中位 %+.1f%%)'
              % ((m14.min() - e14) / e14 * 100, (m14.max() - e14) / e14 * 100,
                 (np.median(m14) - e14) / e14 * 100))
        print('    验证top14: 首 %.1f → 最低损失处 %.1f → 峰值 %.1f'
              % (mean([r['h0'] for r in rows]), mean([r['hB'] for r in rows]),
                 mean([r['hm'] for r in rows])))
    print()
    print('自检总状态: %s' % ('全绿 ✅' if ok_all else '🔴 有失败项'))


if __name__ == '__main__':
    sys.exit(main())
