# -*- coding: utf-8 -*-
"""生成 M 型试点骨架：GPT-5.6 家族 3 条（sol-none/sol-max/terra-none）。
定价/上下文/缓存字段按已核实 T0 事实预填；positioning/modality/self_reported 留待 subagent 补。
"""
import json, os

OUT = os.path.join(os.path.dirname(__file__), "..", "incoming", "models")

FAMILY = [
    ("openai:gpt-5-6-sol-none:base", "gpt-5.6-sol_none", "sol 标准推理档"),
    ("openai:gpt-5-6-sol-max:base", "gpt-5.6-sol_max", "sol 深度推理档（max）"),
    ("openai:gpt-5-6-terra-none:base", "gpt-5.6-terra_none", "terra 轻量档"),
]

def make(mid, full, desc):
    return {
        "schema_version": "1.1",
        "model_id": mid,
        "basic_info": {
            "full_name": full,
            "version": "5.6",
            "vendor": "OpenAI",
            "release_date": "2026-07",
            "positioning": [],
            "access": {"open_weights": False, "api": True, "local_deployment": False,
                        "notes": None},
            "notes": desc,
        },
        "architecture": {
            "total_params_b": None, "active_params_b": None,
            "architecture_type": "Unknown",
            "context_window_tokens": 1050000,
            "context_window_effective_tokens": None,
            "knowledge_cutoff": None,
            "notes": "标称 1.05M 上下文；参数量官方未披露；>272K 输入触发长上下文价",
        },
        "benchmarks": {"self_reported": [], "independent": [], "arena_elo": []},
        "pricing": {
            "currency": "USD", "unit": "per_million_tokens",
            "input": 4.0, "output": 20.0, "cached_input": 0.40, "cache_write": 5.00,
            "batch_input": 2.0, "batch_output": 10.0,
            "free_tier": None, "promotions": None,
            "long_context": [{"threshold": ">272000", "input": 8.0, "output": 30.0}],
            "effective_date": "2026-08-25",
            "source_url": "https://platform.openai.com/docs/pricing",
            "source_type": "官方定价页", "confidence": "T0",
            "notes": "Standard 短上下文价 $4/$20，缓存读 $0.40/写 $5.00；Batch/Flex $2/$10；>272K 输入 $8/输出 $30。与主库现值一致，本次仅结构规范化补 long_context 键",
        },
        "modality": {
            "input": {"text": None, "image": None, "audio": None, "video": None,
                       "pdf": None, "code": None, "web": None, "notes": None},
            "output": {"text": None, "code": None, "image": None, "audio": None,
                        "speech": None, "notes": None},
            "native_multimodal": {"input_image": None, "input_audio": None,
                                   "input_video": None, "output_image": None,
                                   "output_audio": None, "notes": None},
        },
        "meta": {
            "collected_at": "2026-08-25", "verified_at": None,
            "verification_status": "待验证",
            "source_urls": ["https://platform.openai.com/docs/pricing"],
            "notes": "M 型试点：骨架由主 agent 预填已核实定价/上下文，subagent 补 positioning/modality/self_reported 后合并",
        },
    }

for mid, full, desc in FAMILY:
    path = os.path.join(OUT, mid.replace(":", "__") + ".jsonl")
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(make(mid, full, desc), ensure_ascii=False) + "\n")
    print("written:", os.path.basename(path))
