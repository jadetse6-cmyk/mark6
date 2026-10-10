#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扩窗复跑 —— 把 nn_signal_test.py 的滚动折从 ti1000 往前来推到 ti300。

    python3 nn/run_ext_window.py --seeds 8 --save nn/runs/nn8_real_ext_20261005.npz
    python3 nn/run_ext_window.py --seeds 8 --shuffle --save nn/runs/nn8_shuffle_ext_20261005.npz

目的只有一个: 把当前读数(+2% 量级)的【误差棒收窄 ~40%】(734 → 1434 期)。
它不制造优势、不改任何口径 —— 登记口径(SEEDS=3 / NN_TOPK=(14,21) / aux=OFF)
一个字不动, 本脚本只是在 import 之后、于内存里替换 FOLDS, 命令行参数原样透传。

🔴 纪律:
  - nn_signal_test.py 一行不改(它是登记口径所在, 改它 = 改结论)。
  - 折表只向【更早】延伸, 原有 7 折的窗口逐项不变 ⇒ 其尾段 734 期应与
    nn/runs/nn8_*_20261005.npz 的读数逐位复现, 这是本脚本的免费自检。
  - ⚠️ 最早几折 (300-500) 训练段只有 100~300 期 (部署形态 ~1600 期), 模型明显
    欠训练 —— 那几折的数字解读时要单列, 别把它和"今天的配方"混为一谈。
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import nn_signal_test as T  # noqa: E402

_OLD = list(T.FOLDS)                     # [(1000,1100)...(1600,1734)]
_LAST_END = _OLD[-1][1]                  # 1734: 老表最后一折的右端, 原样保留
_OLD_N = _LAST_END - _OLD[0][0]          # 734

# ti 300..1600 每 100 期一折 + 原样的末折 (1600,1734)
T.FOLDS = [(lo, lo + 100) for lo in range(300, 1600, 100)] + [(1600, _LAST_END)]
_NEW_N = T.FOLDS[-1][1] - T.FOLDS[0][0]  # 1434

# 自检: 折必须首尾相接、且老 7 折逐项原样在场 —— 错了宁愿崩, 别输出一份错窗口的数字
for (a0, b0), (c0, d0) in zip(T.FOLDS, T.FOLDS[1:]):
    assert b0 == c0, f'折不连续: {b0} != {c0}'
assert T.FOLDS[0][0] == 300 and T.FOLDS[-1][1] == _LAST_END
assert all(f in T.FOLDS for f in _OLD), '老折有丢失, 尾段复现自检会失效'

if __name__ == '__main__':
    print('🔧 扩窗: 评估区间 ti %d..%d (%d 期) → ti %d..%d (%d 期)   [%d 折]'
          % (_OLD[0][0], _LAST_END - 1, _OLD_N,
             T.FOLDS[0][0], _LAST_END - 1, _NEW_N, len(T.FOLDS)))
    print('   老 7 折窗口逐项不变 ⇒ 尾段 %d 期应与 20261005 标准跑读数一致(自检)' % _OLD_N)
    print()
    T.main()
