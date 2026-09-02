#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D22 第二步：批量修复规则 6.3 剩余 71 条丙档两栏矛盾。

按 D22 第一步实测分布：
  - 70 条同型错误（source_type='T0-自报' ↔ confidence='T0-自报-转述'）：
    来源类型按 source_url 域映射（arXiv/HF/ModelScope/官方博客/GitHub.io 等），
    confidence 一律升一级 'T0-自报-转述' → 'T0-自报'（原始页面可直访，去掉 -转述）。
  - 1 条 wizardlm-2-7b（source_type='T0-自报-转述' ↔ confidence='T3'）：
    原 confidence='T3' 正确（官方页已下架、只能从第三方数据库转述），
    只把 source_type 改成来源描述「第三方聚合（datalearner）」，confidence 不动。

总计：71 条改动。预期：
  - 规则 6.3 命中 71 → 0
  - WARN 104 → 33（常量段 16 + 规则 6.2 的 17 = 33，其余规则命中都为 0）
  - 含「自报」条目数 2567 → 2566（wizardlm 那条不再含「自报」，其余 70 条仍含）
"""
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

# === 修复规则表 ===
# 按 (model_id, source_url) → (new_source_type, new_confidence)
# 70 条同型错误：
COMMON_OLD_STYPE = "T0-自报"
COMMON_OLD_CONF = "T0-自报-转述"
COMMON_NEW_CONF = "T0-自报"

# URL 类型 → new_source_type 映射（70 条同型错误）
URL_TO_NEW_STYPE = [
    # (URL 子串, new_source_type)
    ("arxiv.org", "官方技术报告（自报）"),
    ("huggingface.co", "官方 Model Card（自报）"),
    ("modelscope.cn", "官方 Model Card（自报）"),
    ("ai.google.dev", "官方 Model Card（自报）"),
    ("developers.googleblog.com", "官方技术博客（自报）"),
    ("qwenlm.github.io", "官方技术博客（自报）"),
]

# 1 条 wizardlm-2-7b 特殊处理
WIZARDLM_MID = "microsoft:wizardlm-2-7b:base"
WIZARDLM_OLD_STYPE = "T0-自报-转述"
WIZARDLM_OLD_CONF = "T3"
WIZARDLM_NEW_STYPE = "第三方聚合（datalearner）"
WIZARDLM_NEW_CONF = "T3"  # 不变


def map_url_to_stype(url):
    """按 URL 域返回新的 source_type；找不到返回 None。"""
    if not url:
        return None
    u = str(url).lower()
    for needle, new_st in URL_TO_NEW_STYPE:
        if needle in u:
            return new_st
    return None


def main():
    data_path = Path("model_data_v2.jsonl")
    if not data_path.exists():
        print(f"❌ 数据文件不存在: {data_path}", file=sys.stderr)
        sys.exit(2)

    # === 备份数据 ===
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = data_path.with_name(f"{data_path.name}.d22bak-{ts}")
    shutil.copy2(data_path, bak)
    print(f"✅ 备份: {bak}")

    # === 改前实测（验证不变量基线）===
    import hashlib
    before_md5 = hashlib.md5(data_path.read_bytes()).hexdigest()
    print(f"改前 md5: {before_md5}")

    # === 第一遍：dry-run 统计要改的条目数 ===
    common_changes = 0
    wizardlm_changes = 0
    with data_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            mid = rec.get("model_id", "?")
            for section in ("self_reported", "independent", "arena_elo"):
                for it in (rec.get("benchmarks") or {}).get(section, []) or []:
                    st = it.get("source_type")
                    cf = it.get("confidence")
                    if st == COMMON_OLD_STYPE and cf == COMMON_OLD_CONF:
                        # 必须能映射到新 source_type
                        new_st = map_url_to_stype(it.get("source_url"))
                        if new_st is None:
                            print(f"⚠️  无法映射 URL: {mid} url={it.get('source_url')!r}",
                                  file=sys.stderr)
                            continue
                        common_changes += 1
                    elif (mid == WIZARDLM_MID and st == WIZARDLM_OLD_STYPE
                          and cf == WIZARDLM_OLD_CONF):
                        wizardlm_changes += 1
    print(f"\n第一遍 dry-run:")
    print(f"  70 条同型错误候选: {common_changes}")
    print(f"  wizardlm 特殊条目: {wizardlm_changes}")
    total = common_changes + wizardlm_changes
    print(f"  总改动条目: {total}（预期 71）")
    if total != 71:
        print(f"❌ 总数不对，停止修复", file=sys.stderr)
        sys.exit(1)

    # === 第二遍：实际修改 ===
    changed_common = 0
    changed_wizardlm = 0
    out_lines = []
    with data_path.open("r", encoding="utf-8") as f:
        for line in f:
            stripped = line.rstrip("\n")
            if not stripped.strip():
                out_lines.append(line)
                continue
            rec = json.loads(stripped)
            mid = rec.get("model_id", "?")
            for section in ("self_reported", "independent", "arena_elo"):
                items = (rec.get("benchmarks") or {}).get(section, [])
                if not isinstance(items, list):
                    continue
                for it in items:
                    if not isinstance(it, dict):
                        continue
                    st = it.get("source_type")
                    cf = it.get("confidence")
                    # 70 条同型错误
                    if st == COMMON_OLD_STYPE and cf == COMMON_OLD_CONF:
                        new_st = map_url_to_stype(it.get("source_url"))
                        if new_st is None:
                            continue
                        it["source_type"] = new_st
                        it["confidence"] = COMMON_NEW_CONF
                        changed_common += 1
                    # 1 条 wizardlm 特殊处理
                    elif (mid == WIZARDLM_MID and st == WIZARDLM_OLD_STYPE
                          and cf == WIZARDLM_OLD_CONF):
                        it["source_type"] = WIZARDLM_NEW_STYPE
                        it["confidence"] = WIZARDLM_NEW_CONF  # 不变，写明
                        changed_wizardlm += 1
            out_lines.append(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")

    # 写回
    with data_path.open("w", encoding="utf-8", newline="\n") as f:
        f.writelines(out_lines)

    print(f"\n第二遍实际修改:")
    print(f"  70 条同型错误修复: {changed_common}")
    print(f"  wizardlm 特殊修复: {changed_wizardlm}")
    print(f"  总改动: {changed_common + changed_wizardlm}")

    # === 改后实测 ===
    after_md5 = hashlib.md5(data_path.read_bytes()).hexdigest()
    print(f"\n改后 md5: {after_md5}")
    print(f"md5 变化: {before_md5} → {after_md5}")

    # === 自检：规则 6.3 命中数 ===
    import re
    TIER_ONLY = re.compile(r"^T[0-4](?:-自报)?(?:-转述)?(?:-第三方)?$")
    remaining = 0
    has_zibao = 0
    with data_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            for section in ("self_reported", "independent", "arena_elo"):
                for it in (rec.get("benchmarks") or {}).get(section, []) or []:
                    st = it.get("source_type")
                    if not st:
                        continue
                    if "自报" in str(st):
                        has_zibao += 1
                    if TIER_ONLY.match(str(st)):
                        remaining += 1
    print(f"\n自检:")
    print(f"  规则 6.3 命中（TIER_ONLY 残留）: {remaining}（预期 0）")
    print(f"  含「自报」条目数: {has_zibao}（预期 2566 = 2567 - 1）")


if __name__ == "__main__":
    main()
