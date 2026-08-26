#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
clean_v1.py —— 阶段 0 数据清洗（修复 TEST_REPORT.md 之外、此前诊断发现的 v1 数据 bug）

修复项：
  1. meta.source_urls 数组元素内嵌换行符 → 按换行拆分为独立 URL 并去重（55 条受影响）
  2. model_id 前缀为 unknown 但可明确归属的记录 → 修复厂商 slug（PaLM→google、Qwen→alibaba 等）
  3. basic_info.vendor 字段与修复后的 slug 对齐（仅修复被改动的记录）

原则：
  - 不删除任何记录，不改动任何数值型字段；只修 URL 结构与厂商归属
  - 产出 model_data_v1_clean.jsonl，原文件不动
  - 每条修复都记入清洗日志

用法：
  python clean_v1.py
"""

import json
import os
import re
import sys
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "model_data_v1.jsonl")
OUT = os.path.join(HERE, "model_data_v1_clean.jsonl")
LOG = os.path.join(HERE, "clean_v1_log.md")

# unknown 前缀中可明确归属的模型 → 厂商 slug（依据公开事实：模型官方出处）
UNKNOWN_FIX = {
    # Google PaLM 系列
    "palm-2-l": "google",
    "palm-2-m": "google",
    "palm-2-s": "google",
    "palm-62b": "google",
    # 阿里 Qwen 系列（家族代号 / 尺寸变体归属阿里）
    "qwen-1-8b": "alibaba",
    "codeqwen1-5-7b": "alibaba",
    "qwen2-5-coder-0-5b": "alibaba",
    "qwen2-5-coder-14b": "alibaba",
    "qwen2-5-coder-3b-instruct": "alibaba",
    "qwen-3-6-27b": "alibaba",
    # 零一万物
    "yi-9b": "zero-one",
    # 智谱
    "chatglm2-6b": "zhipu",
    "xtrimopglm-1b": "zhipu",
    # OpenAI
    "text-davinci-003": "openai",
    # 华为盘古
    "pangu-5-0": "huawei",
    # 小米
    "super-xiaoai": "xiaomi",
}

# 修复 slug 时 basic_info.vendor 的规范名（与 build 脚本 VENDOR_MAP 的值一致）
VENDOR_NAME = {
    "google": "Google",
    "alibaba": "Alibaba",
    "zero-one": "01.AI",
    "zhipu": "Zhipu AI",
    "openai": "OpenAI",
    "huawei": "Huawei",
    "xiaomi": "Xiaomi",
}


def fix_source_urls(rec, log):
    urls = rec.get("meta", {}).get("source_urls") or []
    fixed = []
    for u in urls:
        if not isinstance(u, str):
            fixed.append(u)
            continue
        fixed.extend(p.strip() for p in u.split("\n") if p.strip())
    # 去重保序
    dedup = list(OrderedDict.fromkeys(fixed))
    # 内容或数量有变即回写（覆盖：内嵌换行拆分、末尾空白裁剪、重复项去除）
    if dedup != urls:
        rec["meta"]["source_urls"] = dedup
        log.append(f"- `{rec['model_id']}`：source_urls 拆分/裁剪/去重，{len(urls)} → {len(dedup)} 项")
        return True
    return False


def fix_vendor(rec, log):
    mid = rec["model_id"]
    slug, family, variant = mid.split(":", 2)
    if slug != "unknown":
        return False
    new_slug = UNKNOWN_FIX.get(family)
    if not new_slug:
        return False
    new_id = f"{new_slug}:{family}:{variant}"
    old_vendor = rec.get("basic_info", {}).get("vendor")
    rec["model_id"] = new_id
    rec["basic_info"]["vendor"] = VENDOR_NAME.get(new_slug, old_vendor)
    note = f"原 model_id `{mid}` 厂商前缀为 unknown，已按模型官方出处修正"
    old_notes = rec.get("basic_info", {}).get("notes")
    rec["basic_info"]["notes"] = note if not old_notes else f"{old_notes}；{note}"
    log.append(f"- `{mid}` → `{new_id}`（vendor: {old_vendor!r} → {VENDOR_NAME.get(new_slug)!r}）")
    return True


def main():
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    recs = []
    with open(SRC, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                recs.append(json.loads(line))

    log = ["# v1 数据清洗日志", "",
           f"> 输入：`model_data_v1.jsonl`（{len(recs)} 条）  ",
           "> 输出：`model_data_v1_clean.jsonl`（不删除任何记录，原文件不动）", ""]

    log.append("## 1. source_urls 换行拆分 / 去重")
    log.append("")
    n_url = sum(1 for r in recs if fix_source_urls(r, log))
    if not n_url:
        log.append("- 无需修复")

    log.append("")
    log.append("## 2. unknown 厂商归属修正")
    log.append("")
    n_vendor = sum(1 for r in recs if fix_vendor(r, log))
    if not n_vendor:
        log.append("- 无需修复")

    log.append("")
    log.append(f"**合计**：source_urls 修复 {n_url} 条；厂商归属修复 {n_vendor} 条。")

    with open(OUT, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(LOG, "w", encoding="utf-8") as f:
        f.write("\n".join(log) + "\n")

    print(f"done: {len(recs)} records -> {OUT}")
    print(f"source_urls fixed: {n_url}, vendor fixed: {n_vendor}")


if __name__ == "__main__":
    main()
