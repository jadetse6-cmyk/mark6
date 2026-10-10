#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扩窗跑(1434 期)的事后分析 —— 尾段复现自检 + 分段 + 分折。

    python3 nn/ext_analysis.py nn/runs/nn8_real_ext_20261005.npz --vs nn/runs/nn8_real_20261005.npz

--vs 给标准窗(734 期)的 npz 时做复现自检: 扩窗跑的【尾段 734 期】应与它逐位相同
(同一批折、同一批种子、同样的训练窗口 ⇒ 确定性复现)。不一致 = 拼接/切窗有错,
数字一律别用。🔴 自检不通过时脚本照常打印数字, 但在开头明确标红 —— 读的人自己看。
"""
import argparse
import numpy as np

LO_EXT = 300
LO_STD = 1000
KS_MEMBER = (10, 14, 15, 20, 21, 22)
K_ENS = (14, 21)


def hit_counts(scores, y, K):
    order = np.argsort(-scores, axis=1)
    return int((order[:, :K] == y[:, None]).any(axis=1).sum())


def line(name, n, h, K):
    exp = n * K / 49.0
    z = (h - exp) / np.sqrt(n * (K / 49.0) * (1 - K / 49.0))
    print(f'  {name:<14} {h:>7.1f}/{n}  随机 {exp:>7.1f}  提升 {(h - exp) / exp * 100:+5.1f}%  z={z:+5.2f}')


ap = argparse.ArgumentParser()
ap.add_argument('npz')
ap.add_argument('--vs', default=None, help='标准窗 npz, 做尾段复现自检')
a = ap.parse_args()

z = np.load(a.npz)
M, E, tgt = z['members'], z['ens'], z['tgt']
S, T, _ = M.shape
y = tgt - 1
print(f'{a.npz}\n  {S} 成员 · {T} 期 · ti {LO_EXT}..{LO_EXT + T - 1}')

if a.vs:
    zo = np.load(a.vs)
    Mo, Eo, to = zo['members'], zo['ens'], zo['tgt']
    tail = T - len(to)
    ok_m = np.array_equal(M[:, tail:], Mo)
    ok_e = np.array_equal(E[tail:], Eo)
    ok_t = np.array_equal(tgt[tail:], to)
    dm = float(np.abs(M[:, tail:] - Mo).max())
    de = float(np.abs(E[tail:] - Eo).max())
    print(f'  尾段复现 vs {a.vs}:')
    print(f'    members 逐位相同={ok_m} (max|Δ|={dm:.2g})   ens={ok_e} ({de:.2g})   tgt={ok_t}')
    if not (ok_m and ok_e and ok_t):
        print('  🔴 尾段没复现 —— 拼接/切窗有问题, 下面的数字别用')
print()

for name, lo, hi in (('全窗 300..1733', 0, T),
                     ('早段 300..999', 0, LO_STD - LO_EXT),
                     ('晚段 1000..1733', LO_STD - LO_EXT, T)):
    n = hi - lo
    yy = y[lo:hi]
    print(f'── {name} ({n} 期) ──')
    for K in KS_MEMBER:
        h = float(np.mean([hit_counts(M[s, lo:hi], yy, K) for s in range(S)]))
        line(f'成员均值 top{K}', n, h, K)
    for K in K_ENS:
        line(f'集成 top{K}', n, hit_counts(E[lo:hi], yy, K), K)
    print()

FOLDS = [(lo, lo + 100) for lo in range(300, 1600, 100)] + [(1600, LO_EXT + T)]
print('── 分折 (成员均值命中数) ──')
for (a0, b0) in FOLDS:
    i0, i1 = a0 - LO_EXT, b0 - LO_EXT
    n = i1 - i0
    h14 = float(np.mean([hit_counts(M[s, i0:i1], y[i0:i1], 14) for s in range(S)]))
    h21 = float(np.mean([hit_counts(M[s, i0:i1], y[i0:i1], 21) for s in range(S)]))
    print(f'  ti {a0:>4}..{b0 - 1:<4} ({n:>3}期)  top14 {h14:>6.1f}/{n} (随机 {n * 14 / 49:>5.1f})'
          f'   top21 {h21:>6.1f}/{n} (随机 {n * 21 / 49:>5.1f})')
