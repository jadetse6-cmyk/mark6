#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NN 家族横向对比 —— 多个 npz 拉平成同一套口径, 便于真实 vs 打乱 vs 各配置直读。

    python3 nn/family_compare.py nn/runs/nn8_real_ext_*.npz nn/runs/nn8_attn_ext_*.npz ...

口径与 ext_analysis.py 一致: 每期 k 码命中按伯努利(k/49)近似, z=(h-e)/sqrt(np(1-p))。
⚠️ 它只做"拉平显示", 不做任何新判定; 分段没有 ti 锚点(按期数对半劈), 与 ext_analysis
   的 300/1000 锚不同 —— 对半劈用于稳定性目视, 精读仍以 ext_analysis(带锚)为准。
"""
import sys

import numpy as np

KS = (14, 21)


def hits(scores, y, K):
    order = np.argsort(-scores, axis=1)
    return int((order[:, :K] == y[:, None]).any(axis=1).sum())


def line(name, n, h, K):
    e = n * K / 49.0
    z = (h - e) / (n * (K / 49.0) * (1 - K / 49.0)) ** 0.5
    return (f'  {name:<16} {h:>7.1f}/{n:<5} 随机 {e:>6.1f}'
            f'  提升 {(h - e) / e * 100:+6.1f}%  z={z:+5.2f}')


for path in sys.argv[1:]:
    z = np.load(path)
    M, E, tgt = z['members'], z['ens'], z['tgt']
    S, T = M.shape[0], M.shape[1]
    y = tgt - 1
    print(f'\n=== {path}  ({S} 成员 · {T} 期) ===')
    for seg, lo, hi in (('全窗', 0, T), ('前半', 0, T // 2), ('后半', T // 2, T)):
        n = hi - lo
        yy = y[lo:hi]
        for K in KS:
            hm = np.array([hits(M[s, lo:hi], yy, K) for s in range(S)], dtype=float)
            print(line(f'成员均值 top{K}', n, hm.mean(), K)
                  + f'   [成员散布 {hm.min():.0f}~{hm.max():.0f}]')
        for K in KS:
            print(line(f'集成 top{K}', n, hits(E[lo:hi], yy, K), K))
