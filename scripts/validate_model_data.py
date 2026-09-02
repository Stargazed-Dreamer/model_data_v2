#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_model_data.py —— 记录级校验器（P5 修复，执行细则 #11 十一项自查的机械化）

对 JSONL 数据集逐条跑合规检查，输出违规清单（Markdown 报告 + stdout 摘要）。
阶段 0（基线）与阶段 3（质检门禁）共用。

检查分级：
  ERROR  —— 结构性/语义性违规，必须修复（缺必备键、pricing 四必采字段缺失、
            positioning 非数组或越界、confidence 与 source_type 不自洽、
            score 越界、日期格式错误、model_id 非三段式、source_urls 内嵌换行）
  WARN   —— 执行细则要求但历史数据普遍未满足的项（未披露参数量的 notes 声明、
            上下文有效值大于标称值、降级采集声明），供增量采集时避免、合并前评估
            2026-08-30 上下文口径修订：不再检查「有效上下文须注明独立测试方法」「为空须标
            待测」——该规矩与全库实际背离（208 条填值里 173 条抄标称），已废止，只留倒挂一条
            2026-08-29 新增两类：①多余的顶层键（数据卡在 schema 外，下游按路径读为
            null）；②嵌套块内的非规范键名（命名漂移，聚合统计会漏计）
            2026-08-30 跑分条目再加两项：6.1 缺 canonical 主键（写法漂移 → 合并主键算成空值 → 去重失效）；
            6.2 合并主键撞车（同一主键挂着多个条目 → 分数不同时机器无从裁决取哪一条）。
            主键与 SOP 合并命令一致：self_reported=(benchmark,config,date)，
            independent=(benchmark,config,source_site,date)（D12 新增 source_site），arena_elo=(sub_benchmark,date)
            2026-08-31 D15 拆栏再加两项：1.1 `architecture_type` 越出稀疏性四值枚举、
            1.2 `backbone_type` 越出主干结构枚举（拆栏前的自由文本写法正命中 1.1）
            2026-09-02 D18b 加 6.3（来源类型栏整栏写的是纯可信度等级值）；
            D18e 加 6.4（来源类型栏把等级值当**前缀**缀在来源描述前，存量已由 D18d 剥净 → 加上时命中 0，纯防回归）；
            D20 加 6.5（来源类型栏把等级值当**括号后缀**写在来源描述后，6.4 的镜像形，存量已由 D20 剥净 → 同样命中 0）

用法：
  python validate_model_data.py <file.jsonl> [--report <out.md>]
退出码：0 = 无 ERROR（可能有 WARN），1 = 存在 ERROR，2 = 文件读取失败
"""

import argparse
import json
import re
import sys

# 刻意不随白名单扩容升版本：新增键全部可选，旧记录读取路径不变；
# 升成 1.2 会让 950 条存量记录同时命中下面的 schema_version WARN，把验收信号变成噪音。
SCHEMA_VERSION = "1.1"

TOP_KEYS = ["schema_version", "model_id", "basic_info", "architecture",
            "benchmarks", "pricing", "modality", "meta"]

# 规范键白名单。权威来源 = incoming/models/_samples/ 下的样板文件（M 型 subagent 照抄的对象），
# 取两个样例的并集（google 样例结构最全）。
# 2026-08-29 扩三项：basic_info.license / architecture.max_output_tokens /
# architecture.reasoning_model —— 主库已有 8/4/4 条实值在用，转正以免下游读不到。
SCHEMA_BLOCK_KEYS = {
    "basic_info": {"full_name", "version", "vendor", "release_date",
                   "positioning", "access", "license", "notes"},
    # backbone_type 是 D15（2026-08-31）拆栏新增列：缺键 = 该条未参与拆栏（原值本就在
    # 旧四值枚举内），不是错误；有键则必须落在 ARCH_BACKBONE_ENUM 内（规则 1.2）。
    "architecture": {"total_params_b", "active_params_b", "architecture_type",
                     "backbone_type",
                     "context_window_tokens", "context_window_effective_tokens",
                     "max_output_tokens", "reasoning_model",
                     "knowledge_cutoff", "notes"},
    "benchmarks": {"self_reported", "independent", "arena_elo"},
    "pricing": {"currency", "unit", "input", "output", "cached_input", "cache_write",
                "batch_input", "batch_output", "free_tier", "promotions", "long_context",
                "effective_date", "source_url", "source_type", "confidence", "notes"},
    "modality": {"input", "output", "native_multimodal"},
    "meta": {"collected_at", "verified_at", "verification_status", "source_urls", "notes"},
}
SUB_BLOCK_KEYS = {
    "basic_info.access": {"open_weights", "api", "local_deployment", "notes"},
    "pricing.free_tier": {"available", "rpm", "rpd", "tpm", "notes"},
    "pricing.long_context": {"threshold_tokens", "input", "output",
                             "cached_input", "notes"},
}
PRICING_MUST_KEYS = ["cached_input", "cache_write", "batch_input", "batch_output"]
ALL_PRICE_KEYS = ["input", "output"] + PRICING_MUST_KEYS
# 「查无官方价」类文案：逐个显式列，不用模糊正则——通配写法会把「无价目表」「无法定价」
# 这类不相干表述也吞进来，反而造出新的误报。新增措辞时在此补一行。
NO_PRICE_CLAIMS = ("无官方 API 价", "无 API 定价", "无API定价", "无官方定价",
                   "无公开定价", "无独立 API 定价", "无 API 计费")
POSITIONING_ENUM = {"旗舰", "中端", "轻量", "推理增强", "多模态", "工具调用增强"}
# D15（2026-08-31 拍板「拆成两栏：稀疏性枚举 + 主干结构枚举」）：architecture_type 收窄成
# 稀疏性四值，原来塞在一栏里的自由文本（"Decoder-only Transformer (GQA, RoPE)" 等 190 种写法）
# 拆到 backbone_type。原文不丢，照抄进 architecture.notes 的「原架构表述」。
ARCH_SPARSITY_ENUM = {"Dense", "MoE", "Hybrid", "Unknown"}
ARCH_BACKBONE_ENUM = {"Transformer", "Transformer-Decoder", "Transformer-Encoder",
                      "Transformer-Encoder-Decoder", "Mamba-SSM", "RNN-LinearAttention",
                      "Diffusion", "CNN", "MLP", "Hybrid", "Unknown"}
CONFIDENCE_ENUM = {"T0", "T0-自报", "T0-自报-转述", "T1", "T2", "T3", "T4"}
# 规则 6.6（D24 拍板「WARN 留痕」，与 D18b 同模式：数据一字未动、只加门禁）：
#     来源类型栏的写法应在受控词表内。三段分设枚举（self_reported 来源应是厂商官方文件/页面，
#     independent 来源应是独立第三方评测，arena_elo 来源应是竞技场分镜像）。该栏写法达 225→223 种自由
#     文本，top 10 占 63.4% / top 50 占 84.2% / 尾部 123 种仅占 6.6%，多样性主要来自「来源类型 × 自报
#     属性 × 限定词后缀」三个正交维度的自由组合。D24 草案 13+6+4 枚举值经全库测算可覆盖 100%（其中
#     直接命中 33.4% / 归一表命中 57.6% / 兜底「官方自报（其它）」9.0% 待重采补具体文件类型）。
#     现库非空 4337 条预计大量命中（223 - 13 枚举值 = 210 种写法会触发本条）—— 留 WARN 不 block 合并，
#     D25 起逐轮归一同义异写 + 限定词进 notes + 重采补具体文件类型，待现库命中 0 后再升 ERROR（与 6.4/6.5
#     升 ERROR 时机一致：现库命中 0 → 升级，不靠改前备份探针）。
# 本条只判等不归一：只在「值不在该段枚举内」时报 WARN，不试图把写法映射到枚举值。归一由 D25 改数据做。
# 与 6.3/6.4/6.5 的关系：四条判据作用域不同——6.3/6.4/6.5 查「等级值错误出现」（形状判据），
# 6.6 查「写法不在受控词表」（语义判据）。同一条目可同时命中，但 6.6 不重复照 6.3/6.4/6.5 的形状。
# 空值/无键不报（与 6.3 的 `if stype and ...` 同前置，避免「缺失」与「写错」混报，见 D18c 教训 ②）。
SOURCE_TYPE_ENUM_BY_SECTION = {
    "self_reported": {
        "官方技术报告（自报）",
        "官方 Model Card（自报）",            # HF Model Card / HuggingFace Model Card / 模型卡 全归此
        "官方 ModelScope 模型卡（自报）",
        "官方技术博客（自报）",              # blog / 技术博客 / 开发者博客 归此
        "官方 GitHub README（自报）",
        "官方产品页（自报）",
        "官方系统卡（自报）",                # System Card / 系统卡
        "官方发布公告（自报）",              # 公告 / changelog / updates
        "官方论文（自报）",                  # arXiv 论文，区分于技术报告
        "官方自报（多源复合）",              # 「技术报告 + GitHub README」等复合来源
        "行业媒体聚合官方发布（自报分转述）",  # 媒体聚合 + 厂商自报双重属性
        "行业媒体转述官方发布（自报）",        # 媒体转述但本质是厂商自报
        "官方自报（其它）",                  # 兜底：未明确文件类型的官方自报，待重采补具体文件类型
    },
    "independent": {
        "独立评测平台",                      # Artificial Analysis / LMSYS / Open LLM Leaderboard 等
        "第三方登记站",                      # datalearner / 各类聚合登记站
        "第三方评测机构聚合（转述）",        # Artificial Analysis 聚合数据
        "第三方基准测试聚合",                # GPT-Fathom 等
        "学术独立评测",                      # Stanford HELM / Epoch AI 等
        "独立第三方评测（其它）",            # 兜底
    },
    "arena_elo": {
        "LMArena 镜像（DataLearner），原始来源 LM Arena",
        "LMArena 镜像（其它），原始来源 LMArena",
        "独立评测平台",
        "第三方登记站",
    },
}
# 规则 6.3：来源类型栏整栏写的就是一个可信度等级值（如 "T0-自报"）。这种值天然含「自报」二字，
# 能过下面那条「建议体现自报属性」的子串判据，可它说的是等级、不是「什么文件/页面」，
# 来源信息为零 —— 判据查的是字符串表面属性而非字段语义（指南 §27）。
# 用正则而不是 CONFIDENCE_ENUM 成员判定：实测 "T2-第三方" 3 条、"T3-转述" 1 条在枚举外，
# 按枚举判会漏掉这 4 条（607 → 603）。
# 这条正则只决定「要不要记一条 WARN 留痕」，绝不驱动任何数据改写。
# 曾经刻意不覆盖「等级值当前缀缀在真实来源描述前」（如 "T0 官方一手技术报告（自报）"，实测 406 条）；
# 那批的**数据**已由 D18d 剥净（405 条，1 条表外原样登记），留痕由下面的规则 6.4 接管。
TIER_ONLY_STYPE_RE = re.compile(r"^T[0-4](?:-自报)?(?:-转述)?(?:-第三方)?$")
# 规则 6.4：来源类型栏把可信度等级值当**前缀**写在真实来源描述前（"T0 官方自报"、"T0-自报 官方一手"）。
# D18d 已把存量剥净，所以本条加上时现库命中为 0 —— 纯防新采集回归（2026-09-02 第 26 轮拍板）。
# 三件必须记住的事：
#   ① 调用处那道 `and not TIER_ONLY_STYPE_RE` 前置是**必需的**，不是保险：分隔符表含 `-`，
#      少了它 "T0-自报" 会被解析成「T0 + 分隔符 - + 主体 自报」而同时命中 6.3，重复计 89 条（实测）。
#      两条规则各背一类缺陷：6.3 = 整栏就是一个等级值（零来源信息）；6.4 = 等级值只是前缀（来源信息在、但一栏背两种语义）。
#   ② 分隔符字符类里 `-` 必须放在最末。写成 ")）-—" 会把 `）-—` 解析成 U+FF09→U+2014 的范围而报错；
#      更糟的是若 ASCII `)` 排在前面，那是个**合法的**反向范围，会静默匹配约 8000 个 CJK 字符。
#   ③ 刻意不覆盖 "T1.5-第三方评测"（表外 1 条）：`T1.5` 后面接的是 `.` 不是分隔符，本正则照不到它，
#      这是**有意**的 —— 它的缺陷是「等级值不在 CONFIDENCE_ENUM 内」而不是「前缀冗余」，
#      单独登记在指南 §27.3，别让一条 WARN 背两类缺陷。
# 同 6.3：只决定是否记 WARN，绝不驱动数据改写。
TIER_PREFIX_STYPE_RE = re.compile(r"^T[0-4](?:-自报)?(?:-转述)?(?:-第三方)?[ \t:：、,，)）—-]+.+$")
# 规则 6.5：来源类型栏把可信度等级值当**括号后缀**写在真实来源描述后（"官方模型卡自报（T0 直采）"）。
# 6.4 的镜像形，2026-09-02 第 28 轮拍板「补，并造探针」。存量 21 条已由 D20 剥净（只剥等级、
# 保留「直采」「官方一手」等采集者限定词），所以本条加上时现库命中为 0，纯防新采集回归。
# 三件必须记住的事：
#   ① 判据 = 任意位置含等级值 ∧ **不以等级值开头**。后半个前置是互斥的构造性保证，不可省：
#      6.3/6.4 都要求等级值在位置 0，所以凡满足本前置者按定义不属那两条。少了它，现库会
#      把 6.3 的 85 条重复报一遍（118 → 203），正是 D18e 躲开的那个坑。
#      再显式追加 `¬6.3 ∧ ¬6.4` 不改变命中集（实测现库 / D20 改前备份 / D18d 改前备份三盘均为
#      0 / 21 / 21），故不写进代码，别把它当第二道保险加回来。
#   ② 前置刻意写成 `^\s*T`（比 6.3/6.4 的 `^T` 更宽）：这样 " T0 官方自报" 这种**带前导空格的前缀形**
#      也不会被本条当成后缀形报出来 —— 本条宁可漏一格排版瑕疵，也不把一类缺陷报成另一类。
#   ③ 左边界 `[^A-Za-z]` 是为了不匹配嵌在字母串里的等级字样（如型号名 "…XT0"）。
#      实测把 `[0-4]` 放宽成 `[0-9]` 命中集一字不变（三盘同测）；`T1.5` 这类小数等级已由
#      `(?:\.[0-9]+)?` 覆盖，不需要额外分支。
# 同 6.3/6.4：只决定要不要记 WARN，绝不驱动数据改写。
TIER_ANYWHERE_STYPE_RE = re.compile(r"(?:^|[^A-Za-z])T[0-4](?:\.[0-9]+)?")
TIER_LEADING_STYPE_RE = re.compile(r"^\s*T[0-4](?:\.[0-9]+)?")
DATE_MD_RE = re.compile(r"^\d{4}-\d{2}$")
DATE_FULL_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# 「未披露」类声明词序变体很多（官方未披露 / 未官方披露 / 尚未披露），按字面匹配会把
# 已如实声明的记录误判成缺声明；不允许跨越句读，避免「未提及，…已披露」这类误通过。
NOT_DISCLOSED_RE = re.compile(r"未[^\s，。；;、]{0,3}披露|待补")
RELAY_MARK = "转述"
# 跑分条目里出现过的非 canonical 基准名键（D9 清了 `name`，D10 清了其余三种写法）。
# arena_elo 另有一个坑：写成 `benchmark` 也算非 canonical，它的主键是 `sub_benchmark`。
BENCH_NAME_ALIASES = ("name", "metric_name", "benchmark_name")
# 合并去重主键的副键段，须与 SOP 合并命令一致（见指南 §18 / COLLECTION_PLAN_v2）：
#   --array-key benchmark config date
#   --array-key-override benchmarks.arena_elo:sub_benchmark,date
#                                    benchmarks.independent:benchmark,config,source_site,date
# D11 一度把这段记成只含 config，漏了 date —— 会让 6.2 把「不同日期的复测」也报成撞车。
# D12 起 independent 再加 source_site：同一基准被多个第三方站各测一次是这张表的正常形态，
# 主键不含来源就会把「不同测量」误判成「同一测量记了两遍」。
BENCH_SUBKEY = {"self_reported": ("config", "date"),
                "independent": ("config", "source_site", "date"),
                "arena_elo": ("date",)}


def _bench_name(item, canonical_key):
    """取跑分条目的显示名用于报错定位：canonical 键 → 各种别名 → '?'。"""
    for k in (canonical_key,) + BENCH_NAME_ALIASES + (("benchmark",) if canonical_key != "benchmark" else ()):
        if item.get(k):
            return item[k]
    return "?"

MODALITY_BOOL_SECTIONS = {
    "input": ["text", "image", "audio", "video", "pdf", "code", "web", "notes"],
    "output": ["text", "code", "image", "audio", "speech", "notes"],
    "native_multimodal": ["input_image", "input_audio", "input_video",
                          "output_image", "output_audio", "notes"],
}


def _dup_measurements(items, name_key, sub_keys):
    """按**合并去重主键** (name_key, *sub_keys) 给跑分条目分组。

    产出 [(基准名, 副键值元组, 组内第二条的下标, [组内全部分数], 分数是否全同)]，只保留 ≥2 条的组。
    主键相同而分数不同 = 机器无从裁决取哪一条；主键与分数都相同 = 同一次测量记了两遍。
    两种都会静默并存进最终数据，所以由规则 6.2 报出来（口径见指南 §20）。
    """
    buckets = {}
    for i, it in enumerate(items or []):
        if not isinstance(it, dict) or it.get(name_key) is None:
            continue
        # 用 str() 兜住罕见的非哈希值（config 写成 dict/list 时不至于让门禁整个崩掉）
        key = (str(it[name_key]),) + tuple(str(it.get(k)) for k in sub_keys)
        buckets.setdefault(key, []).append((i, it.get("score")))
    out = []
    for key, rows in sorted(buckets.items(), key=lambda kv: str(kv[0])):
        if len(rows) >= 2:
            scores = [r[1] for r in rows]
            out.append((key[0], key[1:], rows[1][0], scores, len({str(s) for s in scores}) == 1))
    return out


def schema_drift_warnings(rec):
    """结构漂移检查：多余顶层键 + 嵌套块非规范键名。均记 WARN，不影响 ERROR 验收口径。"""
    out = []
    extra_top = set(rec) - set(TOP_KEYS)
    if extra_top:
        out.append("存在多余顶层键 %s —— 这些键在 schema 之外，下游按规范路径读取会得到 null"
                   % ", ".join(sorted(f"`{k}`" for k in extra_top)))

    def cmp_block(path, block, allow):
        if not isinstance(block, dict):
            return
        bad = set(block) - allow
        if bad:
            out.append("%s 含非规范键 %s（命名漂移，聚合统计会漏计）"
                       % (path, ", ".join(sorted(f"`{k}`" for k in bad))))

    for blk, allow in SCHEMA_BLOCK_KEYS.items():
        cmp_block(blk, rec.get(blk), allow)

    bi = rec.get("basic_info")
    if isinstance(bi, dict):
        cmp_block("basic_info.access", bi.get("access"), SUB_BLOCK_KEYS["basic_info.access"])
    pr = rec.get("pricing")
    if isinstance(pr, dict):
        for sub in ("free_tier", "long_context"):
            cmp_block(f"pricing.{sub}", pr.get(sub), SUB_BLOCK_KEYS[f"pricing.{sub}"])
    return out


def check_record(rec):
    """返回 (errors, warns)，均为字符串列表。"""
    errors, warns = [], []

    mid = rec.get("model_id", "<无 model_id>")

    # 0. 顶层结构
    for k in TOP_KEYS:
        if k not in rec:
            errors.append(f"缺顶层必备键 `{k}`")
    if rec.get("schema_version") != SCHEMA_VERSION:
        warns.append(f"schema_version={rec.get('schema_version')!r}，当前规范为 {SCHEMA_VERSION}")
    parts = str(mid).split(":")
    if len(parts) != 3 or not all(parts):
        errors.append(f"model_id 非三段式 `vendor:family:variant`：{mid!r}")

    # 0.1 结构漂移（多余顶层键 / 非规范键名）
    warns.extend(schema_drift_warnings(rec))

    # 1. 参数量未披露 → null + notes 声明
    arch = rec.get("architecture") or {}
    tp, ap = arch.get("total_params_b"), arch.get("active_params_b")
    anotes = arch.get("notes") or ""
    if tp is None and ap is None and not NOT_DISCLOSED_RE.search(anotes):
        warns.append("参数量全空但 architecture.notes 未声明「（官方）未披露」或「待补」")

    # 1.1 / 1.2 架构两栏枚举越界（D15）。都是 WARN 不是 ERROR：存量归档副本（docs/*.jsonl
    #     按行 byte-exact 留存）用的还是拆栏前的自由文本，判 ERROR 会让历史验收信号失真。
    #     null / 缺键一律沉默——前者是「未披露」的正规写法，后者是「该条未参与拆栏」。
    at, bt = arch.get("architecture_type"), arch.get("backbone_type")
    if at is not None and at not in ARCH_SPARSITY_ENUM:
        warns.append(f"architecture.architecture_type={at!r} 越出稀疏性枚举 "
                     f"{sorted(ARCH_SPARSITY_ENUM)}（D15 起本栏只填稀疏性，主干写法归 backbone_type）")
    if bt is not None and bt not in ARCH_BACKBONE_ENUM:
        warns.append(f"architecture.backbone_type={bt!r} 越出主干结构枚举 {sorted(ARCH_BACKBONE_ENUM)}")

    # 2. 上下文标称 / 有效：2026-08-30 起不再要求「有效值须有独立实测出处」
    #    （执行细则 §2 口径修订，旧规矩下 173 条抄标称 + 127 条 WARN 已证明规矩与现实背离）
    cw, cwe = arch.get("context_window_tokens"), arch.get("context_window_effective_tokens")
    if cw is not None and cwe is not None and cwe > cw:
        warns.append(f"有效上下文 {cwe} 大于标称上下文 {cw}"
                     "—— 疑似把厂商「可扩展窗口」填进了有效栏，最大值应归位到 context_window_tokens")

    # 3. 多模态三态：值必须是 true / false / null（类型检查）
    mod = rec.get("modality") or {}
    for sec, keys in MODALITY_BOOL_SECTIONS.items():
        block = mod.get(sec)
        if not isinstance(block, dict):
            errors.append(f"modality.{sec} 缺失或非对象")
            continue
        for k in keys:
            if k == "notes":
                continue
            if k not in block:
                errors.append(f"modality.{sec}.{k} 键缺失")
            elif block[k] not in (True, False, None):
                errors.append(f"modality.{sec}.{k} 必须是 true/false/null，实际 {block[k]!r}")

    # 4. 定价四必采字段存在性 + 币种单位
    pricing = rec.get("pricing") or {}
    for k in PRICING_MUST_KEYS:
        if k not in pricing:
            errors.append(f"pricing.{k} 必采字段缺失（即使无值也必须显式为 null）")
    if pricing.get("input") is not None or pricing.get("output") is not None:
        if pricing.get("currency") != "USD":
            errors.append(f"pricing.currency 必须为 USD，实际 {pricing.get('currency')!r}")
        if pricing.get("unit") != "per_million_tokens":
            errors.append(f"pricing.unit 必须为 per_million_tokens，实际 {pricing.get('unit')!r}")
        if not pricing.get("effective_date"):
            warns.append("有定价但缺 pricing.effective_date（定价必须精确到日）")
        if not pricing.get("source_url"):
            warns.append("有定价但缺 pricing.source_url")
    # 4.1 定价可信度必须在受控词表内（此前只校验 benchmarks 的 confidence，
    #     pricing.confidence 长期无人查，导致 28 条「中/低/high/N/A」越界值漏网）
    pconf = pricing.get("confidence")
    if pconf is not None and pconf not in CONFIDENCE_ENUM:
        errors.append(f"pricing.confidence={pconf!r} 不在枚举内"
                      f"（允许：{sorted(CONFIDENCE_ENUM)}；未采集应为 null）")

    # 4.2 source_type 与价格值自相矛盾：声称「查无官方价」却仍挂着价格。
    #     此前门禁对 source_type 只查键名不查语义，7 条同类矛盾长期无人发现。
    #     暂记 WARN：其中 3 条（muse-spark x2 / mai-code）需外部核实后才能定方向，
    #     直接升 ERROR 会把待拍板项混进验收口径。
    stype = str(pricing.get("source_type") or "")
    filled = [k for k in ALL_PRICE_KEYS if pricing.get(k) is not None]
    if filled and any(c in stype for c in NO_PRICE_CLAIMS):
        warns.append("pricing.source_type=%r 声称无官方价，但 %s 仍非 null —— 二者必有一处是残留，"
                     "需核实后要么改标签要么剔 null"
                     % (stype, ", ".join("pricing." + k for k in filled)))

    # 4.3 无价即无币种（2026-08-29 拍板口径）：六个价键全 null 时 currency 也应为 null。
    #     填 USD 会被下游读成「已按美元核实过、确认无价」，属红线 1 的伪造默认值。
    #     历史上 645 条无价记录里 USD 323 / null 318 对半分裂，D7 已一次性归一为 null，
    #     本条 WARN 只负责挡住后续采集再写回 USD。unit 不在此约束内（量纲默认值不携带「已核实」含义）。
    if not filled and pricing.get("currency") is not None:
        warns.append("pricing 六个价键全为 null，但 pricing.currency=%r —— 无价应填 null，"
                     "USD 等币种仅在确有价格时才有意义" % (pricing.get("currency"),))

    # 4.4 free_tier 形状漂移（D16）。根因是文档与门禁互相矛盾：prompt.md 曾教字符串写法，
    #     而结构漂移检查（0.1）的 cmp_block 对非 dict 直接 return，裸布尔/纯文字一律静默放行，
    #     于是采集照文档写 → 无人报警 → 漂移到 81 条（str 52 + bool 29）才被发现。
    #     D16 已一次性归一 84 条（见 temp/d16_changelog.txt）；本条 WARN 只负责挡住后续采集写回。
    ft = pricing.get("free_tier")
    ft_keys = SUB_BLOCK_KEYS["pricing.free_tier"]
    if ft is not None and not isinstance(ft, dict):
        shown = ft if isinstance(ft, str) else repr(ft)
        warns.append("pricing.free_tier 形状漂移：实际 %s（%s）"
                     " —— 规范为 null 或含 available/rpm/rpd/tpm/notes 五键的对象"
                     % (type(ft).__name__, shown[:40]))
    elif isinstance(ft, dict) and set(ft) != ft_keys:
        warns.append("pricing.free_tier 键集与规范不符：实际 %s（规范 %s）"
                     % (", ".join(sorted(ft)) or "空对象", ", ".join(sorted(ft_keys))))

    # 5. positioning：数组 + 枚举
    pos = (rec.get("basic_info") or {}).get("positioning")
    if pos is None:
        warns.append("basic_info.positioning 缺失（应为数组，可空）")
    elif not isinstance(pos, list):
        errors.append(f"basic_info.positioning 必须是数组，实际 {type(pos).__name__}")
    else:
        for p in pos:
            if p not in POSITIONING_ENUM:
                errors.append(f"positioning 标签越界：{p!r}（枚举：{sorted(POSITIONING_ENUM)}）")

    # 6. 跑分检查：score 范围、来源三要素、confidence 自洽
    bench = rec.get("benchmarks") or {}
    for section in ("self_reported", "independent"):
        for i, item in enumerate(bench.get(section) or []):
            nm = _bench_name(item, "benchmark")
            tag = f"benchmarks.{section}[{i}]({nm})"
            # 6.1 缺 canonical 主键（D9 归一 1293 条 `name`、D10 归一余下 57 条后扩到全写法）。
            #     多种写法并存的代价不是不好看，是**去重失效**：合并主键 (benchmark, config)
            #     对这类行一律算 ("None","None")，同一次测量会静默并存两份（见指南 §18 / §19）。
            if "benchmark" not in item:
                used = [k for k in BENCH_NAME_ALIASES if k in item]
                warns.append(f"{tag} 缺 benchmark 主键（实际键：{sorted(item) if not used else used}）"
                             f" —— 非 canonical 写法会被合并主键当成空值，导致去重失效")
            score = item.get("score")
            if score is not None and not (0 <= score <= 1):
                errors.append(f"{tag} score={score} 越界，应为 0–1 小数（百分制须除以 100）")
            if not item.get("source_url"):
                errors.append(f"{tag} 缺 source_url（采集即记录，来源不允许为空）")
            conf = item.get("confidence")
            if conf is not None and conf not in CONFIDENCE_ENUM:
                errors.append(f"{tag} confidence={conf!r} 不在枚举内")
            stype = item.get("source_type") or ""
            # 6.3 来源类型栏写成了纯可信度等级值（D18b 起 WARN 级留痕；D18c/D19/D20/D21/D22 逐轮修复后
            #     现库命中 0 → D22 拍板升 ERROR 级，与 6.4/6.5 时机一致）。该值天然含「自报」二字，
            #     能过下面的「建议体现自报属性」子串判据，可它说的是等级、不是「什么文件/页面」，
            #     来源信息为零 —— 判据查的是字符串表面属性而非字段语义（指南 §27）。
            if stype and TIER_ONLY_STYPE_RE.match(stype):
                errors.append(f"{tag} source_type={stype!r} 整栏写的是可信度等级值，零来源信息"
                             f" —— 等级应写进 confidence，来源类型应写「是什么文件/页面」（指南 §27）")
            # 6.4 来源类型栏把等级值当**前缀**写在来源描述前（D18e）。存量已由 D18d 剥净，加上时命中 0，
            #     纯防新采集回归。`not TIER_ONLY` 那道前置见 TIER_PREFIX_STYPE_RE 上方注释①，不可省。
            if stype and TIER_PREFIX_STYPE_RE.match(stype) and not TIER_ONLY_STYPE_RE.match(stype):
                warns.append(f"{tag} source_type={stype!r} 把可信度等级值当前缀写在来源描述前"
                             f" —— 等级应写进 confidence，本栏只写「是什么文件/页面」，不加前缀（指南 §27.3）")
            # 6.5 来源类型栏把等级值当**括号后缀**写在来源描述后（D20）。存量 21 条已由本轮剥净，
            #     加上时命中 0，纯防回归。`not TIER_LEADING` 那道前置见 TIER_ANYWHERE_STYPE_RE 上方注释①，不可省。
            if stype and TIER_ANYWHERE_STYPE_RE.search(stype) and not TIER_LEADING_STYPE_RE.match(stype):
                warns.append(f"{tag} source_type={stype!r} 把可信度等级值当括号后缀写在来源描述后"
                             f" —— 等级应写进 confidence，本栏只写「是什么文件/页面」，括号里不填等级（指南 §27.6）")
            if conf in ("T0", "T0-自报") and RELAY_MARK in stype:
                errors.append(f"{tag} confidence={conf} 与 source_type「{stype}」不自洽：转述来源不得配 T0/T0-自报")
            # source_type 为空 = 「没主张来源类型」，与「主张了却漏标自报」是两类缺陷，不报同一条 WARN
            # （2026-09-02 拍板）。空值那批登记在指南 §27 的遗留清单里待重采，门禁不再重复计一次。
            if section == "self_reported" and conf in ("T0", "T0-自报", "T0-自报-转述") and stype and "自报" not in stype:
                warns.append(f"{tag} 自报分 source_type={stype!r} 建议体现「自报」属性")
            # 6.6 来源类型栏写法应在受控词表内（D24 拍板 WARN 留痕，D26 升 ERROR：D25 五批归一后
            #     现库命中 0，与 6.4/6.5 升 ERROR 时机一致：现库命中 0 → 升级）。三段分设枚举，
            #     详见 SOURCE_TYPE_ENUM_BY_SECTION 上方注释。本条只判等不归一，归一由 D25 改数据做。
            if stype and stype not in SOURCE_TYPE_ENUM_BY_SECTION[section]:
                errors.append(f"{tag} source_type={stype!r} 不在 {section} 段受控枚举内"
                             f"（允许：{sorted(SOURCE_TYPE_ENUM_BY_SECTION[section])}）"
                             f" —— D25 归一后现库命中 0，D26 升 ERROR 防回归")
    for i, item in enumerate(bench.get("arena_elo") or []):
        tag = f"benchmarks.arena_elo[{i}]({_bench_name(item, 'sub_benchmark')})"
        # 同 6.1：arena_elo 的 canonical 主键是 sub_benchmark，写成 benchmark 也算非 canonical
        if "sub_benchmark" not in item:
            used = [k for k in BENCH_NAME_ALIASES + ("benchmark",) if k in item]
            warns.append(f"{tag} 缺 sub_benchmark 主键（实际键：{used or sorted(item)}）"
                         f" —— 非 canonical 写法会被合并主键当成空值，导致去重失效")
        if item.get("score") is None:
            errors.append(f"{tag} 缺 score")
        if not item.get("date"):
            errors.append(f"{tag} 缺快照 date")
        # 同 6.3：arena_elo 段此前完全不读 source_type，该段的同类写法（实测 3 条）对旧门禁彻底不可见。
        #     D22 起 6.3 升 ERROR，本段同步。
        stype = item.get("source_type") or ""
        if stype and TIER_ONLY_STYPE_RE.match(stype):
            errors.append(f"{tag} source_type={stype!r} 整栏写的是可信度等级值，零来源信息"
                         f" —— 等级应写进 confidence，来源类型应写「是什么文件/页面」（指南 §27）")
        # 同 6.4：本段也要查，否则该段的前缀写法照旧不可见（改前备份实测本段命中 0，但判据不能靠这个省略）。
        if stype and TIER_PREFIX_STYPE_RE.match(stype) and not TIER_ONLY_STYPE_RE.match(stype):
            warns.append(f"{tag} source_type={stype!r} 把可信度等级值当前缀写在来源描述前"
                         f" —— 等级应写进 confidence，本栏只写「是什么文件/页面」，不加前缀（指南 §27.3）")
        # 同 6.4：本段也要查后缀形（改前备份实测本段命中 0 —— 21 条全在 self_reported，
        #   但判据不能靠这个省略，否则新采集写在本段就照不到）。
        if stype and TIER_ANYWHERE_STYPE_RE.search(stype) and not TIER_LEADING_STYPE_RE.match(stype):
            warns.append(f"{tag} source_type={stype!r} 把可信度等级值当括号后缀写在来源描述后"
                         f" —— 等级应写进 confidence，本栏只写「是什么文件/页面」，括号里不填等级（指南 §27.6）")
        # 同 6.6：arena_elo 段同步查受控枚举（与 self_reported/independent 共用 SOURCE_TYPE_ENUM_BY_SECTION，
        #   但取该段自己的枚举集合）。详见 SOURCE_TYPE_ENUM_BY_SECTION 上方注释。
        if stype and stype not in SOURCE_TYPE_ENUM_BY_SECTION["arena_elo"]:
            errors.append(f"{tag} source_type={stype!r} 不在 arena_elo 段受控枚举内"
                         f"（允许：{sorted(SOURCE_TYPE_ENUM_BY_SECTION['arena_elo'])}）"
                         f" —— D25 归一后现库命中 0，D26 升 ERROR 防回归")

    # 6.2 合并主键撞车（D11，D12 起 independent 主键含 source_site）：
    #     同一主键挂着多条条目 —— 合并时去重无从裁决。
    #     分数不同 = 真冲突，得靠 config/score_type/基准名/来源站把「不同测量」分开；
    #     分数也相同 = 同一条记了两遍，删其一。主键算得出才会撞，所以这条只在写法 canonical 时才有意义。
    for section in ("self_reported", "independent"):
        for nm, subs, second_i, scores, same in _dup_measurements(
                bench.get(section), "benchmark", BENCH_SUBKEY[section]):
            tag = f"benchmarks.{section}[{second_i}]({nm})"
            key_desc = ", ".join(f"{k}={v!r}" for k, v in zip(BENCH_SUBKEY[section], subs))
            if same:
                warns.append(f"{tag} 与同数组另一条目主键与分数全同（{key_desc}）—— 同一次测量记了两遍，合并会留双份")
            else:
                warns.append(f"{tag} 与同数组其他条目主键相同（{key_desc}）却挂着 {len(scores)} 个不同分数 "
                             f"{sorted({str(s) for s in scores})} —— 去重无从裁决，须用 config/score_type/基准名区分子项")
    for nm, subs, second_i, scores, _same in _dup_measurements(bench.get("arena_elo"), "sub_benchmark", ("date",)):
        tag = f"benchmarks.arena_elo[{second_i}]({nm})"
        warns.append(f"{tag} 与同数组其他条目主键相同（date={subs[0]!r}）却挂着 {len(scores)} 个分数 "
                     f"{sorted({str(s) for s in scores})} —— 同一子榜同一快照记了多份")

    # 7. 日期格式
    rd = (rec.get("basic_info") or {}).get("release_date")
    if rd is not None and not (DATE_MD_RE.match(rd) or DATE_FULL_RE.match(rd)):
        errors.append(f"basic_info.release_date={rd!r} 非 ISO 8601（YYYY-MM 或 YYYY-MM-DD）")
    # knowledge_cutoff 规范到月，实测有 28 条写成 YYYY / YYYY-MM-DD / mid-2021。
    # 日级精度只是「比规范更细」不是错，降为 WARN 提示，不倒逼改数据（新检查一律先 WARN）。
    kc = arch.get("knowledge_cutoff")
    if kc is not None and not (DATE_MD_RE.match(str(kc)) or DATE_FULL_RE.match(str(kc))):
        warns.append(f"architecture.knowledge_cutoff={kc!r} 非 YYYY-MM（规范精确到月）")
    meta = rec.get("meta") or {}
    for fld in ("collected_at", "verified_at"):
        v = meta.get(fld)
        if v is not None and not DATE_FULL_RE.match(str(v)):
            errors.append(f"meta.{fld}={v!r} 应精确到日（YYYY-MM-DD）")
    ed = pricing.get("effective_date")
    # 历史定价常仅知生效月份，放宽到接受 YYYY-MM（执行细则 #10：月级须注明周期）
    if ed is not None and not (DATE_FULL_RE.match(str(ed)) or DATE_MD_RE.match(str(ed))):
        errors.append(f"pricing.effective_date={ed!r} 应精确到日或月（YYYY-MM-DD / YYYY-MM）")

    # 8. source_urls 无内嵌换行、非空字符串
    urls = meta.get("source_urls")
    if isinstance(urls, list):
        for u in urls:
            if not isinstance(u, str) or not u.strip():
                errors.append(f"meta.source_urls 含非法项：{u!r}")
            elif "\n" in u or "\r" in u:
                errors.append(f"meta.source_urls 项内嵌换行：{u[:60]!r}…")
    elif urls is not None:
        errors.append("meta.source_urls 必须是数组")

    # 9. 降级采集声明抽查（仅当所有定价/自报来源均为非官方时提示）
    mnotes = meta.get("notes") or ""
    vs = meta.get("verification_status")
    if vs not in (None, "已验证", "待验证", "存疑", "已过期"):
        errors.append(f"meta.verification_status={vs!r} 不在枚举内（已验证/待验证/存疑/已过期）")

    return errors, warns


def main():
    ap = argparse.ArgumentParser(description="模型数据集记录级校验器")
    ap.add_argument("file", help="待校验的 JSONL 文件")
    ap.add_argument("--report", default=None, help="输出 Markdown 报告路径（默认打印摘要）")
    args = ap.parse_args()

    try:
        with open(args.file, encoding="utf-8-sig") as f:
            recs = [json.loads(l) for l in f if l.strip() and not l.strip().startswith("//")]
    except (OSError, json.JSONDecodeError) as e:
        print(f"❌ 读取失败：{e}", file=sys.stderr)
        return 2

    total_e = total_w = 0
    rec_errors = 0
    lines = [f"# 校验报告：{args.file}", "", f"记录数：{len(recs)}", ""]
    for rec in recs:
        errs, warns = check_record(rec)
        if errs or warns:
            lines.append(f"## `{rec.get('model_id', '?')}`")
            for e in errs:
                lines.append(f"- **ERROR** {e}")
            for w in warns:
                lines.append(f"- WARN {w}")
            lines.append("")
        total_e += len(errs)
        total_w += len(warns)
        rec_errors += 1 if errs else 0

    summary = (f"校验完成：{len(recs)} 条，ERROR {total_e} 项（涉及 {rec_errors} 条记录），"
               f"WARN {total_w} 项")
    lines[:0] = [f"> {summary}", ""]

    text = "\n".join(lines)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(summary)
        print(f"报告已写入 {args.report}")
    else:
        print(text[:4000])
        print(summary)
    return 1 if total_e else 0


if __name__ == "__main__":
    sys.exit(main())
