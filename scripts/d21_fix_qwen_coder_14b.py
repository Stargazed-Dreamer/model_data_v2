#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D21 修复脚本：alibaba:qwen2-5-coder-14b:base 的 14 条 self_reported 跑分条目。

背景：该模型全部 14 条 self_reported 条目的 source_type='T0-自报'（纯等级值，命中规则 6.3）、
confidence='T0-自报-转述'（与 source_type 矛盾）。经 WebFetch 核实 source_url 指向的
arXiv:2409.12186 是 Qwen 团队官方发布的《Qwen2.5-Coder Technical Report》
（作者含 Binyuan Hui / Junyang Lin 等 Qwen 核心成员），属厂商一手自报来源，
confidence 应为 T0-自报（而非 T0-自报-转述）。

改动：
  source_type:  'T0-自报'          → '官方技术报告（自报）'（库内已有 295 条的既有写法）
  confidence:   'T0-自报-转述'      → 'T0-自报'

改动范围：仅 alibaba:qwen2-5-coder-14b:base 的 self_reported 节，14 个条目。
不改其他模型、不改 independent / arena_elo 节。
"""
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

TARGET_MID = "alibaba:qwen2-5-coder-14b:base"
OLD_STYPE = "T0-自报"
OLD_CONF = "T0-自报-转述"
NEW_STYPE = "官方技术报告（自报）"
NEW_CONF = "T0-自报"


def main():
    data_path = Path("model_data_v2.jsonl")
    if not data_path.exists():
        print(f"ERROR: {data_path} 不存在", file=sys.stderr)
        sys.exit(2)

    # 1. 备份
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = data_path.with_name(f"{data_path.name}.d21bak-{ts}")
    shutil.copy2(data_path, bak)
    print(f"备份: {bak}")

    # 2. 逐行读写，只改目标记录
    changed_count = 0
    lines_out = []
    with open(data_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                lines_out.append(line)
                continue
            rec = json.loads(stripped)
            if rec.get("model_id") == TARGET_MID:
                sr = (rec.get("benchmarks") or {}).get("self_reported") or []
                for item in sr:
                    if (item.get("source_type") == OLD_STYPE
                            and item.get("confidence") == OLD_CONF):
                        item["source_type"] = NEW_STYPE
                        item["confidence"] = NEW_CONF
                        changed_count += 1
                # 保持原有的行尾换行
                lines_out.append(json.dumps(rec, ensure_ascii=False) + "\n")
            else:
                lines_out.append(line)

    # 3. 写回
    with open(data_path, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(lines_out)

    print(f"改动条目数: {changed_count}")
    if changed_count != 14:
        print(f"WARNING: 预期改动 14 条，实际 {changed_count} 条", file=sys.stderr)
        sys.exit(1)
    print("完成")


if __name__ == "__main__":
    main()
