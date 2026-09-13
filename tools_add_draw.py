#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""入库一期开奖: 双CSV追加 + index.html DRAWS 整行json重建 + title bump + 全项复查。

用法:
    python3 tools_add_draw.py            # 取接口最新一期
    python3 tools_add_draw.py 2026255    # 指定期号(走 expect 接口)

教训(2026-09-11 upd254.py): 曾因"对 src 做 title 替换、却用替换前的 lines 拼回写盘"
导致 title 静默丢失而脚本照常打印成功。本脚本全程在同一个字符串上做替换后写盘,
并且写盘后重新读盘复查(不是复查内存变量)。
"""
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request

REPO = os.path.dirname(os.path.abspath(__file__))
CSVS = [os.path.expanduser("~/macau_mark6_data.csv"),
        os.path.join(REPO, "macau_mark6_data.csv")]
INDEX = os.path.join(REPO, "index.html")
DOMSTUB = os.path.join(REPO, "verify_index_dom.js")
API_LATEST = "https://macaumarksix.com/api/macaujc2.com"
API_EXPECT = "https://history.macaumarksix.com/history/macaujc2/expect/{e}"

fail = []


def check(cond, msg):
    print(("  ✅ " if cond else "  ❌ ") + msg)
    if not cond:
        fail.append(msg)
    return cond


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    expect = sys.argv[1] if len(sys.argv) > 1 else None
    if expect:
        data = get(API_EXPECT.format(e=expect))
    else:
        data = get(API_LATEST)
    if isinstance(data, dict):                      # expect 接口包一层 {"data":[...]}
        data = data["data"]
    rec = data[0] if isinstance(data, list) else data
    expect = str(rec["expect"])
    codes = rec["openCode"].split(",")
    waves = rec["wave"].split(",")
    zods = rec["zodiac"].split(",")
    date = rec["openTime"][:10]
    print(f"接口: {expect} {date} 平{' '.join(codes[:6])} | 特{codes[6]} "
          f"({zods[6]}, {waves[6]})")

    if not check(len(codes) == 7 and len(waves) == 7 and len(zods) == 7,
                 f"接口字段数 7/7/7 (实得 {len(codes)}/{len(waves)}/{len(zods)})"):
        return 1
    row = ",".join([expect, date] + codes + waves + zods)

    # ---- 1. 双 CSV 查重 + 追加 ----
    csv_rows = sum(1 for _ in open(CSVS[0], encoding="utf-8")) - 1
    for p in CSVS:
        txt = open(p, encoding="utf-8").read()
        if not check(f"\n{expect}," not in txt and not txt.startswith(f"{expect},"),
                     f"{os.path.basename(os.path.dirname(p)) or '~'}/{os.path.basename(p)} 无 {expect} 重复行"):
            return 1
        n0 = txt.count("\n") + (0 if txt.endswith("\n") else 1)
        if not txt.endswith("\n"):
            txt += "\n"
        open(p, "w", encoding="utf-8").write(txt + row + "\n")
        n = sum(1 for _ in open(p, encoding="utf-8"))
        check(n == n0 + 1, f"{os.path.dirname(p).split('/')[-1]}/CSV 行数 {n0} → {n}")

    # ---- 2. index.html: 备份 → DRAWS 整行重建 → title bump ----
    shutil.copy2(INDEX, INDEX + f".bak-{expect}")
    src = open(INDEX, encoding="utf-8").read()
    m = re.search(r"var DRAWS = (\[.*?\]);\n", src, re.S)
    if not check(bool(m), "找到 DRAWS 单行"):
        return 1
    old = json.loads(m.group(1))
    old_last = old[-1]["i"]
    check(len(old) == csv_rows, f"DRAWS 原条数 {len(old)} = CSV 数据行数 {csv_rows}")
    check(int(expect) == int(old_last) + 1, f"期号连续: {old_last} → {expect}")

    entry = {"i": expect, "d": date,
             "f": [int(c) for c in codes[:6]], "s": int(codes[6])}
    new = old + [entry]
    new_json = json.dumps(new, ensure_ascii=False, separators=(", ", ": "))
    check(new_json[:-1].startswith(m.group(1)[:-1]), "前序条目逐字一致")

    src = src[:m.start(1)] + new_json + src[m.end(1):]          # 同一个 src 上替换
    tm = re.search(r"<title>v(\d+)", src)
    if not check(bool(tm), "找到 title 版本号"):
        return 1
    old_ver = tm.group(1)
    src = src[:tm.start(1)] + str(int(expect) + 1) + src[tm.end(1):]   # 同一个 src 上替换
    open(INDEX, "w", encoding="utf-8").write(src)

    # ---- 3. 重新读盘复查(不复查内存变量) ----
    disk = open(INDEX, encoding="utf-8").read()
    t = re.search(r"<title>([^<]*)", disk).group(1)
    check(f"v{int(expect)+1}-" in t, f"title 已落盘: {t[:28]} (原 v{old_ver})")
    check(disk.count("var DRAWS = [[") == 0, "无数组套数组(白屏事故判据)")
    d2 = json.loads(re.search(r"var DRAWS = (\[.*?\]);\n", disk, re.S).group(1))
    check(len(d2) == len(new) and d2[-1] == entry,
          f"DRAWS 落盘 {len(d2)} 条, 末条 {d2[-1]['i']} 特{d2[-1]['s']}")

    dl = subprocess.run(["diff", INDEX + f".bak-{expect}", INDEX],
                        capture_output=True, text=True).stdout.splitlines()
    hunks = [l for l in dl if re.match(r"^\d+[acd]\d+", l)]     # normal diff 的大小写标记行
    check(len(hunks) == 2 and all(re.match(r"^(5|197)", h) for h in hunks),
          f"diff 恰好 2 处变动(title+DRAWS), 实得 {hunks}")

    if os.path.exists(DOMSTUB):
        big = max(re.findall(r"<script>(.*?)</script>", disk, re.S), key=len)
        open("/tmp/js1.js", "w", encoding="utf-8").write(big)
        r = subprocess.run(["node", DOMSTUB], capture_output=True, text=True, cwd=REPO)
        out = r.stdout + r.stderr
        el = re.search(r"elements created: (\d+)", out)
        ch = re.search(r"charts instantiated: (\d+)", out)
        check("EVAL_OK" in out, "domstub EVAL_OK (无运行时崩溃/白屏)")
        check(bool(el) and int(el.group(1)) >= 40, f"domstub 元素 {el.group(1) if el else '?'} (≥40)")
        check(bool(ch) and int(ch.group(1)) >= 6, f"domstub 图表 {ch.group(1) if ch else '?'} (≥6)")

    print("\n" + ("🔴 有失败项, 未通过" if fail else "🟢 全部通过 → 可 push"))
    print(f"新行: {row}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
