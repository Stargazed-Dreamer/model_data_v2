#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_test_records.py —— 测试用：模拟「遵循 prompt.md 的采集 agent」产出两家公司的模型记录。

产出：
  test_collected_anthropic_zhipu.jsonl  —— 7 条，严格按 prompt.md 三段式 model_id（点号 family）
  test_enrich_existing.jsonl            —— 1 条，故意复用 DB 中已有 ID（连字符 + :base）以测试「合并进已有记录」路径

仅用于 pipeline 测试，不代表数据已核实。
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
COLLECTED = "2026-08-24"

def blank_benchmarks():
    return {"self_reported": [], "independent": [], "arena_elo": []}

def blank_modality(notes_in=None, notes_out=None, notes_nat=None):
    return {
        "input": {"text": True, "image": None, "audio": None, "video": None,
                  "pdf": None, "code": True, "web": None, "notes": notes_in},
        "output": {"text": True, "code": True, "image": False, "audio": False,
                   "speech": False, "notes": notes_out},
        "native_multimodal": {"input_image": None, "input_audio": None, "input_video": None,
                              "output_image": False, "output_audio": False, "notes": notes_nat},
    }

def blank_pricing():
    return {
        "currency": "USD", "unit": "per_million_tokens",
        "input": None, "output": None,
        "cached_input": None, "cache_write": None,
        "batch_input": None, "batch_output": None,
        "free_tier": None, "promotions": None, "long_context": None,
        "effective_date": None, "source_url": None, "source_type": None,
        "confidence": None, "notes": None,
    }

records = []

# ============ Anthropic ============
# Claude Opus 5
p = blank_pricing()
p.update({"input": 5.0, "output": 25.0, "cached_input": 0.50, "cache_write": 6.25,
          "effective_date": "2026-08-24",
          "source_url": "https://docs.anthropic.com/en/docs/about-claude/models/overview",
          "source_type": "官方定价页", "confidence": "T0",
          "notes": "输入/输出价差 5x；cached_input 为缓存读取价 $0.50（约标准输入 10%），cache_write 为缓存写入价 $6.25（1.25x）；Batch API 折扣未在概览页列出，暂缺官方值（null）；价格取自官方模型概览页（anthropic.com/pricing 直连抓取失败，改用官方 docs 概览，价格同源）"})
m = blank_modality(notes_in="图像原生理解；PDF 经工具链解析；视频/音频未原生支持（null）",
                   notes_nat="图像原生；音频/视频未原生")
m["input"]["image"] = True; m["native_multimodal"]["input_image"] = True
m["input"]["pdf"] = True
records.append({
    "schema_version": "1.1",
    "model_id": "anthropic:claude-opus:5",
    "basic_info": {"full_name": "Claude Opus 5", "version": "5", "vendor": "Anthropic",
                   "release_date": "2026-06", "positioning": ["旗舰", "推理增强", "工具调用增强"],
                   "access": {"open_weights": False, "api": True, "local_deployment": False,
                              "notes": "Opus 5 为旗舰档；thinking 自适应开启"}},
    "architecture": {"total_params_b": None, "active_params_b": None, "architecture_type": "Unknown",
                     "context_window_tokens": 1000000, "context_window_effective_tokens": None,
                     "knowledge_cutoff": "2026-05",
                     "notes": "官方未披露参数量与架构类型；标称 1M 上下文（最大输出 128K），有效上下文未独立测试；知识截止 2026-05"},
    "benchmarks": blank_benchmarks(),
    "pricing": p,
    "modality": m,
    "meta": {"collected_at": COLLECTED, "verified_at": None, "verification_status": "待验证",
             "source_urls": ["https://docs.anthropic.com/en/docs/about-claude/models/overview"],
             "notes": "官方定价页(anthropic.com/pricing)直连不可达，数据来自官方 docs 概览页（同属官方域、价格同源）；本测试轮未采集跑分"},
})

# Claude Sonnet 5
p = blank_pricing()
p.update({"input": 3.0, "output": 15.0, "cached_input": 0.20, "cache_write": 2.50,
          "effective_date": "2026-09-01",
          "source_url": "https://docs.anthropic.com/en/docs/about-claude/models/overview",
          "source_type": "官方定价页", "confidence": "T0",
          "notes": "介绍价 $2/$10 至 2026-08-31，标准价 $3/$15 自 2026-09-01 起；cached_input $0.20，cache_write $2.50；Batch 折扣未列（null）"})
m = blank_modality(notes_in="图像原生理解；PDF 经工具链；视频/音频未原生", notes_nat="图像原生")
m["input"]["image"] = True; m["native_multimodal"]["input_image"] = True; m["input"]["pdf"] = True
records.append({
    "schema_version": "1.1",
    "model_id": "anthropic:claude-sonnet:5",
    "basic_info": {"full_name": "Claude Sonnet 5", "version": "5", "vendor": "Anthropic",
                   "release_date": "2026-06", "positioning": ["中端", "推理增强", "工具调用增强"],
                   "access": {"open_weights": False, "api": True, "local_deployment": False, "notes": None}},
    "architecture": {"total_params_b": None, "active_params_b": None, "architecture_type": "Unknown",
                     "context_window_tokens": 1000000, "context_window_effective_tokens": None,
                     "knowledge_cutoff": "2026-01",
                     "notes": "官方未披露参数量；标称 1M 上下文（最大输出 128K），有效未测；知识截止 2026-01"},
    "benchmarks": blank_benchmarks(),
    "pricing": p, "modality": m,
    "meta": {"collected_at": COLLECTED, "verified_at": None, "verification_status": "待验证",
             "source_urls": ["https://docs.anthropic.com/en/docs/about-claude/models/overview"],
             "notes": "价格来自官方 docs 概览页；本测试轮未采集跑分"},
})

# Claude Haiku 4.5
p = blank_pricing()
p.update({"input": 1.0, "output": 5.0, "cached_input": 0.10, "cache_write": 1.25,
          "effective_date": "2026-08-24",
          "source_url": "https://docs.anthropic.com/en/docs/about-claude/models/overview",
          "source_type": "官方定价页", "confidence": "T0",
          "notes": "cached_input $0.10，cache_write $1.25；Batch 折扣未列（null）"})
m = blank_modality(notes_in="图像原生理解；PDF 经工具链；视频/音频未原生", notes_nat="图像原生（部分档）")
m["input"]["image"] = True; m["native_multimodal"]["input_image"] = True; m["input"]["pdf"] = True
records.append({
    "schema_version": "1.1",
    "model_id": "anthropic:claude-haiku:4.5",
    "basic_info": {"full_name": "Claude Haiku 4.5", "version": "4.5", "vendor": "Anthropic",
                   "release_date": "2025-10", "positioning": ["轻量"],
                   "access": {"open_weights": False, "api": True, "local_deployment": False, "notes": None}},
    "architecture": {"total_params_b": None, "active_params_b": None, "architecture_type": "Unknown",
                     "context_window_tokens": 200000, "context_window_effective_tokens": None,
                     "knowledge_cutoff": "2025-07",
                     "notes": "官方未披露参数量；标称 200K 上下文（最大输出 64K），有效未测；知识截止 2025-07（来源间有 2025-02 与 2025-07 冲突，取 docs 概览 2025-07）"},
    "benchmarks": blank_benchmarks(),
    "pricing": p, "modality": m,
    "meta": {"collected_at": COLLECTED, "verified_at": None, "verification_status": "待验证",
             "source_urls": ["https://docs.anthropic.com/en/docs/about-claude/models/overview"],
             "notes": "价格来自官方 docs 概览页；本测试轮未采集跑分"},
})

# ============ Zhipu (GLM) ============
# GLM-5.3
p = blank_pricing()
p.update({"input": 1.40, "output": 4.40, "cached_input": 0.26,
          "effective_date": "2026-08-22",
          "source_url": "https://tokenrate.dev/models/glm-5-3",
          "source_type": "独立评测平台", "confidence": "T1",
          "notes": "官方 BigModel 定价页未列出 GLM-5.3（仅 GLM-4 系列），价格来自 OpenRouter/tokenrate 独立价格追踪；官方域未含此模型，已降级采集（决策1）；缓存价 $0.26 未区分读/写"})
m = blank_modality(notes_in="图像原生理解（GLM 系列支持图像输入）；PDF 经工具链；视频/音频未原生", notes_nat="图像原生")
m["input"]["image"] = True; m["native_multimodal"]["input_image"] = True; m["input"]["pdf"] = True
records.append({
    "schema_version": "1.1",
    "model_id": "zhipu:glm-5.3:base",
    "basic_info": {"full_name": "GLM-5.3", "version": "5.3", "vendor": "Zhipu AI",
                   "release_date": "2026-08", "positioning": ["旗舰", "推理增强"],
                   "access": {"open_weights": True, "api": True, "local_deployment": True,
                              "notes": "Z.AI 开放权重（社区/HF），同时提供官方 API"}},
    "architecture": {"total_params_b": None, "active_params_b": None, "architecture_type": "Unknown",
                     "context_window_tokens": 1048576, "context_window_effective_tokens": None,
                     "knowledge_cutoff": None,
                     "notes": "官方未披露参数量；标称 1,048,576 上下文（来自 OpenRouter/第三方，官方页未列 GLM-5.3）；有效上下文未测"},
    "benchmarks": blank_benchmarks(),
    "pricing": p, "modality": m,
    "meta": {"collected_at": COLLECTED, "verified_at": None, "verification_status": "待验证",
             "source_urls": ["https://tokenrate.dev/models/glm-5-3", "https://open.bigmodel.cn/pricing"],
             "notes": "官方域 BigModel 未收录 GLM-5.3，数据经独立价格追踪平台间接核实（决策1 降级）；参数/跑分未官方确认；本测试轮未采集跑分"},
})

# GLM-5 (MoE demo)
p = blank_pricing()
p.update({"input": 1.00, "output": 3.20,
          "effective_date": "2026-04",
          "source_url": "https://www.claudemarket.ai/blog/best-glm-models-for-openclaw",
          "source_type": "行业媒体", "confidence": "T3",
          "notes": "价格来自第三方博客，非官方/非独立追踪，待核实；官方 BigModel 页 GLM-5 价格以人民币列示，此处为博客美元估值"})
m = blank_modality(notes_in="图像原生理解；视频/音频未原生", notes_nat="图像原生")
m["input"]["image"] = True; m["native_multimodal"]["input_image"] = True; m["input"]["pdf"] = True
bench = blank_benchmarks()
bench["independent"] = [
    {"benchmark": "SWE-bench Verified", "score": 0.778, "score_type": "pass@1", "config": "default",
     "date": "2026-04", "source_url": "https://www.claudemarket.ai/blog/best-glm-models-for-openclaw",
     "source_type": "行业媒体", "confidence": "T3", "gap_to_self_reported": None,
     "notes": "来自第三方博客 claudemarket.ai，非官方/非独立评测平台，仅供参考"},
    {"benchmark": "AIME 2026", "score": 0.927, "score_type": "accuracy", "config": "default",
     "date": "2026-04", "source_url": "https://www.claudemarket.ai/blog/best-glm-models-for-openclaw",
     "source_type": "行业媒体", "confidence": "T3", "gap_to_self_reported": None,
     "notes": "来自第三方博客，仅供参考"},
]
records.append({
    "schema_version": "1.1",
    "model_id": "zhipu:glm-5:base",
    "basic_info": {"full_name": "GLM-5", "version": "5", "vendor": "Zhipu AI",
                   "release_date": "2026-04", "positioning": ["旗舰", "推理增强"],
                   "access": {"open_weights": True, "api": True, "local_deployment": True, "notes": "开放权重（MIT）+ 官方 API"}},
    "architecture": {"total_params_b": 744, "active_params_b": 40, "architecture_type": "MoE",
                     "context_window_tokens": 200000, "context_window_effective_tokens": None,
                     "knowledge_cutoff": None,
                     "notes": "MoE：总参 744B / 激活 40B（来自第三方博客）；标称上下文 200K，但另有来源称 GLM-5.x 达 1M，存在冲突，待官方确认"},
    "benchmarks": bench,
    "pricing": p, "modality": m,
    "meta": {"collected_at": COLLECTED, "verified_at": None, "verification_status": "待验证",
             "source_urls": ["https://www.claudemarket.ai/blog/best-glm-models-for-openclaw", "https://open.bigmodel.cn/pricing"],
             "notes": "参数/价格/跑分均来自第三方博客（T3），非官方直读；上下文窗口存在 200K 与 1M 的来源冲突；官方 BigModel 页未列 GLM-5 美元价"},
})

# GLM-4.6V (vision demo)
p = blank_pricing()
p.update({"input": 0.30, "output": 0.90, "cached_input": 0.06,
          "effective_date": "2026-08-22",
          "source_url": "https://tokenrate.dev/models/glm-4-6v",
          "source_type": "独立评测平台", "confidence": "T1",
          "notes": "来自 OpenRouter/tokenrate 独立价格追踪；cached_input $0.06（缓存读取价）"})
m = blank_modality(notes_in="视觉理解模型，图像原生输入", notes_nat="图像原生（视觉理解）")
m["input"]["image"] = True; m["native_multimodal"]["input_image"] = True
records.append({
    "schema_version": "1.1",
    "model_id": "zhipu:glm-4.6v:base",
    "basic_info": {"full_name": "GLM-4.6V", "version": "4.6", "vendor": "Zhipu AI",
                   "release_date": None, "positioning": ["多模态"],
                   "access": {"open_weights": None, "api": True, "local_deployment": None, "notes": "视觉理解模型，提供官方 API"}},
    "architecture": {"total_params_b": None, "active_params_b": None, "architecture_type": "Unknown",
                     "context_window_tokens": 131072, "context_window_effective_tokens": None,
                     "knowledge_cutoff": None, "notes": "官方未披露参数量；标称 131K 上下文"},
    "benchmarks": blank_benchmarks(),
    "pricing": p, "modality": m,
    "meta": {"collected_at": COLLECTED, "verified_at": None, "verification_status": "待验证",
             "source_urls": ["https://tokenrate.dev/models/glm-4-6v", "https://open.bigmodel.cn/pricing"],
             "notes": "价格来自独立价格追踪平台；视觉理解模型，图像原生输入、无图像输出"},
})

# GLM-4-Plus (official RMB -> USD conversion demo)
p = blank_pricing()
p.update({"input": 0.70, "output": 0.70,
          "effective_date": "2026-08-24",
          "source_url": "https://open.bigmodel.cn/pricing",
          "source_type": "官方定价页", "confidence": "T0",
          "notes": "官方源为人民币：输入=输出 ¥5/百万 token（BigModel 单一标价）；按假设汇率 7.13（2026-08，未实时核实）折算为 USD 0.70；官方源非 USD"})
m = blank_modality(notes_in="文本模型；图像/视频/音频未披露（null）", notes_nat=None)
records.append({
    "schema_version": "1.1",
    "model_id": "zhipu:glm-4-plus:base",
    "basic_info": {"full_name": "GLM-4-Plus", "version": "4", "vendor": "Zhipu AI",
                   "release_date": None, "positioning": ["旗舰"],
                   "access": {"open_weights": False, "api": True, "local_deployment": False, "notes": "官方 API 模型"}},
    "architecture": {"total_params_b": None, "active_params_b": None, "architecture_type": "Unknown",
                     "context_window_tokens": 128000, "context_window_effective_tokens": None,
                     "knowledge_cutoff": None, "notes": "官方未披露参数量；标称 128K 上下文"},
    "benchmarks": blank_benchmarks(),
    "pricing": p, "modality": m,
    "meta": {"collected_at": COLLECTED, "verified_at": None, "verification_status": "待验证",
             "source_urls": ["https://open.bigmodel.cn/pricing"],
             "notes": "价格来自官方 BigModel 定价页（人民币），已按假设汇率折算 USD；本测试轮未采集跑分"},
})

# ---- 写出主文件 ----
out1 = os.path.join(HERE, "test_collected_anthropic_zhipu.jsonl")
with open(out1, "w", encoding="utf-8", newline="\n") as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"写出 {len(records)} 条 -> {os.path.basename(out1)}")

# ----  enrichment 测试文件：故意复用 DB 已有 ID（连字符 + :base） ----
enrich = [{
    "schema_version": "1.1",
    "model_id": "zhipu:glm-5-3:base",   # 与 model_data_v1.jsonl 中已有记录同 ID
    "basic_info": {"full_name": "GLM-5.3", "version": "5.3", "vendor": "Zhipu AI",
                   "release_date": "2026-08", "positioning": ["旗舰", "推理增强"],
                   "access": {"open_weights": True, "api": True, "local_deployment": True, "notes": None}},
    "architecture": {"total_params_b": None, "active_params_b": None, "architecture_type": "Unknown",
                     "context_window_tokens": 1048576, "context_window_effective_tokens": None,
                     "knowledge_cutoff": None,
                     "notes": "官方未披露参数量；标称 1,048,576 上下文（来自 OpenRouter/第三方）"},
    "benchmarks": blank_benchmarks(),
    "pricing": {"currency": "USD", "unit": "per_million_tokens",
                "input": 1.40, "output": 4.40, "cached_input": 0.26, "cache_write": None,
                "batch_input": None, "batch_output": None, "free_tier": None, "promotions": None,
                "long_context": None, "effective_date": "2026-08-22",
                "source_url": "https://tokenrate.dev/models/glm-5-3", "source_type": "独立评测平台",
                "confidence": "T1",
                "notes": "官方 BigModel 未列 GLM-5.3，价格来自 OpenRouter/tokenrate（T1）"},
    "modality": {"input": {"text": True, "image": True, "audio": None, "video": None, "pdf": True,
                           "code": True, "web": None, "notes": "图像原生理解；PDF 经工具链"},
                "output": {"text": True, "code": True, "image": False, "audio": False, "speech": False, "notes": None},
                "native_multimodal": {"input_image": True, "input_audio": None, "input_video": None,
                                      "output_image": False, "output_audio": False, "notes": "图像原生"}},
    "meta": {"collected_at": COLLECTED, "verified_at": None, "verification_status": "待验证",
             "source_urls": ["https://tokenrate.dev/models/glm-5-3"],
             "notes": "enrichment 测试：复用 DB 已有 ID，复核 pricing/modality"},
}]
out2 = os.path.join(HERE, "test_enrich_existing.jsonl")
with open(out2, "w", encoding="utf-8", newline="\n") as f:
    for r in enrich:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"写出 {len(enrich)} 条 -> {os.path.basename(out2)}")
