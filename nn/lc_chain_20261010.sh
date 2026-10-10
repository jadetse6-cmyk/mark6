#!/bin/bash
# 2026-10-10 nn 学习体检链: 学习曲线(真实 vs 打乱) + 正对照(植入信号 q=0.5/0.1/0.05/0.02)
# 口径: mlp+aux(登记口径) / ext 14 折 / ti300..1733 / 8 种子 / epochs=300 + 早停
# 自检: leg1 的 members 应与 nn8_aux_ext_20261007.npz 逐位一致(仪器纯附加的证据)
cd /Users/xiejinyu/macau-mark6 || exit 1
D=nn/runs
L=$D/lc_chain_20261010.log
rm -f $D/lc_chain_20261010.done
: > $L
run() {
  name=$1; shift
  echo "[$(date '+%F %T')] START $name" >> $L
  python3 "$@" > $D/$name.txt 2>&1
  rc=$?
  echo "[$(date '+%F %T')] END $name exit=$rc" >> $L
  if [ $rc -ne 0 ]; then echo "FAIL $name" >> $L; exit 1; fi
}
run lc_aux_real_20261010    nn/run_ext_window.py --aux --seeds 8 \
    --save $D/lc_aux_real_20261010.npz --log-curves $D/lc_aux_real_curves_20261010.npz
run lc_aux_shuffle_20261010 nn/run_ext_window.py --aux --shuffle --seeds 8 \
    --save $D/lc_aux_shuffle_20261010.npz --log-curves $D/lc_aux_shuffle_curves_20261010.npz
run lc_plant50_20261010     nn/learn_curve.py --q 0.5  --seeds 8 \
    --save $D/lc_plant50_20261010.npz --log-curves $D/lc_plant50_curves_20261010.npz
run lc_plant10_20261010     nn/learn_curve.py --q 0.1  --seeds 8 \
    --save $D/lc_plant10_20261010.npz --log-curves $D/lc_plant10_curves_20261010.npz
run lc_plant05_20261010     nn/learn_curve.py --q 0.05 --seeds 8 \
    --save $D/lc_plant05_20261010.npz --log-curves $D/lc_plant05_curves_20261010.npz
run lc_plant02_20261010     nn/learn_curve.py --q 0.02 --seeds 8 \
    --save $D/lc_plant02_20261010.npz --log-curves $D/lc_plant02_curves_20261010.npz
echo "OK $(date '+%F %T')" > $D/lc_chain_20261010.done
