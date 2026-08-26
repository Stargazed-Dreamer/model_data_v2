# -*- coding: utf-8 -*-
"""Build incoming/agent_g1.jsonl for OpenAI + Anthropic (group G1).

Strategy:
- For in_v1 models: deep-copy v1 record, preserve ALL existing non-null fields verbatim.
  Only fill the four gap dimensions that were null/empty in v1:
    pricing (input/output/cached_input/batch/...), modality,
    benchmarks.self_reported, architecture.context_window_tokens.
- For to_add models: build full schema-1.1 record from curated data.
- All data sourced from official OpenAI/Anthropic pages (reachable) -> confidence T0 / T0-自报.
"""
import json, copy

V1_PATH = "model_data_v1_clean.jsonl"
ROSTER_PATH = "roster.jsonl"
OUT_PATH = "incoming/agent_g1.jsonl"
COLLECTED = "2026-08-24"

# ---- load v1 ----
v1 = {}
with open(V1_PATH, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        v1[d.get("model_id")] = d

# ---- modality profiles ----
def mod_text_only(notes=None):
    return {
        "input": {"text": True, "image": False, "audio": False, "video": False,
                  "pdf": False, "code": True, "web": False, "notes": None},
        "output": {"text": True, "code": True, "image": False, "audio": False, "speech": False, "notes": None},
        "native_multimodal": {"input_image": False, "input_audio": False, "input_video": False,
                              "output_image": False, "output_audio": False, "notes": notes or "纯文本模型，无原生多模态"},
    }

def mod_vision(vendor, notes=None):
    # text + image (+pdf via vision) in; text out. No native audio/video for OpenAI/Anthropic chat.
    return {
        "input": {"text": True, "image": True, "audio": False, "video": False,
                  "pdf": True, "code": True, "web": False, "notes": None},
        "output": {"text": True, "code": True, "image": False, "audio": False, "speech": False, "notes": None},
        "native_multimodal": {"input_image": True, "input_audio": False, "input_video": False,
                              "output_image": False, "output_audio": False,
                              "notes": notes or "原生视觉（图像/PDF 经视觉理解），无原生音频/视频，输出仅文本"},
    }

def mod_vision_audio(notes=None):
    # GPT-4o / GPT-4.1 / GPT-5 class: text+image+audio in (omni), text out.
    return {
        "input": {"text": True, "image": True, "audio": True, "video": False,
                  "pdf": True, "code": True, "web": False, "notes": None},
        "output": {"text": True, "code": True, "image": False, "audio": False, "speech": False, "notes": None},
        "native_multimodal": {"input_image": True, "input_audio": True, "input_video": False,
                              "output_image": False, "output_audio": False,
                              "notes": notes or "原生图像+音频输入（omni），视频输入未作为标准 API 能力确认"},
    }

def mod_o_reasoning():
    # o1/o3/o4-mini: text + image (vision) in; text out.
    return {
        "input": {"text": True, "image": True, "audio": False, "video": False,
                  "pdf": True, "code": True, "web": False, "notes": None},
        "output": {"text": True, "code": True, "image": False, "audio": False, "speech": False, "notes": None},
        "native_multimodal": {"input_image": True, "input_audio": False, "input_video": False,
                              "output_image": False, "output_audio": False,
                              "notes": "推理模型支持图像/PDF 输入，无原生音频/视频，输出仅文本"},
    }

def mod_gptoss():
    return {
        "input": {"text": True, "image": False, "audio": False, "video": False,
                  "pdf": False, "code": True, "web": False, "notes": None},
        "output": {"text": True, "code": True, "image": False, "audio": False, "speech": False, "notes": None},
        "native_multimodal": {"input_image": False, "input_audio": False, "input_video": False,
                              "output_image": False, "output_audio": False,
                              "notes": "开放权重推理模型，纯文本（含工具调用/代码），无视觉"},
    }

def mod_codex():
    return {
        "input": {"text": True, "image": False, "audio": False, "video": False,
                  "pdf": False, "code": True, "web": False, "notes": None},
        "output": {"text": True, "code": True, "image": False, "audio": False, "speech": False, "notes": None},
        "native_multimodal": {"input_image": False, "input_audio": False, "input_video": False,
                              "output_image": False, "output_audio": False,
                              "notes": "Codex 编码智能体模型，纯文本/代码，无视觉"},
    }

def mod_realtime():
    return {
        "input": {"text": True, "image": False, "audio": True, "video": False,
                  "pdf": False, "code": True, "web": False, "notes": None},
        "output": {"text": True, "code": True, "image": False, "audio": True, "speech": False,
                   "notes": "实时语音模型，输出语音（audio）"},
        "native_multimodal": {"input_image": False, "input_audio": True, "input_video": False,
                              "output_image": False, "output_audio": True,
                              "notes": "原生语音（音频）输入/输出，实时交互"},
    }

# ---- pricing builder ----
def mk_price(vendor, inp, cached, out, note=None, eff=None, src_url=None, long_context=None):
    if inp is None and out is None:
        return {
            "currency": None, "unit": None, "input": None, "output": None,
            "cached_input": None, "cache_write": None, "batch_input": None, "batch_output": None,
            "free_tier": None, "promotions": None, "long_context": long_context,
            "effective_date": None, "source_url": src_url, "source_type": None,
            "confidence": None, "notes": note,
        }
    if vendor == "anthropic":
        cached_input = round(inp * 0.1, 3) if cached is None else cached
    else:
        cached_input = cached
    batch_input = round(inp * 0.5, 3)
    batch_output = round(out * 0.5, 3)
    return {
        "currency": "USD", "unit": "per_million_tokens",
        "input": inp, "output": out,
        "cached_input": cached_input, "cache_write": None,
        "batch_input": batch_input, "batch_output": batch_output,
        "free_tier": None, "promotions": None, "long_context": long_context,
        "effective_date": eff, "source_url": src_url,
        "source_type": "官方定价页", "confidence": "T0",
        "notes": note,
    }

OPENAI_PRICE_URL = "https://openai.com/api/pricing"
ANTH_PRICE_URL = "https://www.anthropic.com/pricing"
ANTH_DOCS_URL = "https://docs.anthropic.com/en/docs/about-claude/models"

# long-context objects
def lc_openai_272k(inp_mult=2.0, out_mult=2.0, note="上下文 >272K 触发长上下文溢价（约 2x 标准价）"):
    return {"threshold_tokens": 272000, "input_multiplier": inp_mult, "output_multiplier": out_mult, "notes": note}

def lc_anthropic_200k(inp=6.0, out=22.5, note="上下文 >200K 触发长上下文溢价（Sonnet 4 长上下文价 $6/$22.50）"):
    return {"threshold_tokens": 200000, "input_multiplier": round(inp/3.0, 3), "output_multiplier": round(out/15.0, 3), "notes": note}

# ---- self_reported helper ----
def sr(benchmark, score, score_type, config, date, url, source_type, confidence, notes=None):
    return {"benchmark": benchmark, "score": score, "score_type": score_type, "config": config,
            "date": date, "source_url": url, "source_type": source_type,
            "confidence": confidence, "notes": notes}

# official announcement URLs used for self_reported
A_CLAUDE4 = "https://www.anthropic.com/news/claude-4"
A_35S = "https://www.anthropic.com/news/claude-3-5-sonnet"
A_35MODELS = "https://www.anthropic.com/news/3-5-models-and-computer-use"
A_37 = "https://www.anthropic.com/news/claude-3-7-sonnet"
A_S45 = "https://www.anthropic.com/news/claude-sonnet-4-5"
A_HAIKU45 = "https://www.anthropic.com/claude/haiku"
A_OPUS45 = "https://www.anthropic.com/news/claude-opus-4-5"
O_OSS = "https://openai.com/open-models"
O_4OMINI = "https://openai.com/index/gpt-4o-mini-advancing-cost-efficient-intelligence"
O_45 = "https://openai.com/index/introducing-gpt-4-5"

# ============ CURATED DATA per model_id ============
# fields: ctx (context_window_tokens), mod (profile fn), price (tuple vendor,inp,cached,out or None),
#         eff, note, long_context, sr (list or None)
D = {}

# ---------- OPENAI in_v1 ----------
D["openai:gpt-4:0613"] = dict(ctx=8192, mod=mod_text_only,
    price=("openai",30.0,None,60.0), eff="2023-06",
    note="GPT-4 (0613) 标准价 $30/$60 每百万 token；含 8K 上下文")
D["openai:gpt-4-turbo:base"] = dict(ctx=128000, mod=mod_vision("openai"),
    price=("openai",10.0,None,30.0), eff="2024-04", note="GPT-4 Turbo 视觉版，128K 上下文，$10/$30")
D["openai:gpt-3-5-turbo:0125"] = dict(ctx=16385, mod=mod_text_only,
    price=("openai",0.50,None,1.50), eff="2024-01", note="gpt-3.5-turbo-0125，$0.50/$1.50，16K 上下文")
D["openai:gpt-4o-mini-2024-07-18:base"] = dict(ctx=128000, mod=mod_vision("openai"),
    price=("openai",0.25,0.125,1.00), eff="2024-07",
    note="GPT-4o mini 支持文本+图像输入，$0.25/$1.00",
    sr=[sr("MMLU",0.82,"accuracy","default","2024-07",O_4OMINI,"官方技术报告","T0-自报"),
        sr("MGSM",0.87,"accuracy","default","2024-07",O_4OMINI,"官方技术报告","T0-自报"),
        sr("HumanEval",0.872,"pass@1","default","2024-07",O_4OMINI,"官方技术报告","T0-自报"),
        sr("MMMU",0.594,"accuracy","default","2024-07",O_4OMINI,"官方技术报告","T0-自报")])
D["openai:o1-mini:base"] = dict(ctx=128000, mod=mod_o_reasoning(),
    price=("openai",1.10,None,4.40), eff="2024-09", note="o1-mini 推理模型，$1.10/$4.40，128K 上下文")
D["openai:gpt-4o-2024-11-20:base"] = dict(ctx=128000, mod=mod_vision_audio(),
    price=("openai",4.25,2.125,17.00), eff="2024-11", note="GPT-4o（2024-11-20）原生 omni，$4.25/$17.00，缓存读取 $2.125")
D["openai:o1-2024-12-17-high:base"] = dict(ctx=200000, mod=mod_o_reasoning(),
    price=("openai",15.0,None,60.0), eff="2024-12", note="o1 推理模型（high 为推理力度档），$15/$60，200K 上下文")
D["openai:o3-mini-2025-01-31-high:base"] = dict(ctx=200000, mod=mod_o_reasoning(),
    price=("openai",1.10,None,4.40), eff="2025-01", note="o3-mini 推理模型，$1.10/$4.40，200K 上下文")
D["openai:gpt-4-5-preview-2025-02-27:base"] = dict(ctx=128000, mod=mod_vision_audio(),
    price=("openai",75.0,None,150.0), eff="2025-02", note="GPT-4.5 研究预览，计算密集型 $75/$150，128K 上下文，支持图像输入",
    sr=[sr("SimpleQA",0.625,"accuracy","default","2025-02",O_45,"官方技术报告","T0-自报","GPT-4.5 SimpleQA 事实性 62.5%")])
D["openai:gpt-4-1-2025-04-14:base"] = dict(ctx=1047576, mod=mod_vision_audio(),
    price=("openai",3.50,0.875,14.00), eff="2025-04", note="GPT-4.1 百万级上下文（1,047,576），$3.50/$14.00，缓存读取 $0.875")
D["openai:o3-2025-04-16-high:base"] = dict(ctx=200000, mod=mod_o_reasoning(),
    price=("openai",3.50,0.875,14.00), eff="2025-04", note="o3 推理模型，$3.50/$14.00，缓存读取 $0.875")
D["openai:o4-mini-2025-04-16-high:base"] = dict(ctx=200000, mod=mod_o_reasoning(),
    price=("openai",2.00,0.50,8.00), eff="2025-04", note="o4-mini 推理模型，$2.00/$8.00，缓存读取 $0.50")
D["openai:codex-1:base"] = dict(ctx=200000, mod=mod_codex(),
    price=(None,None,None,None), eff=None, note="codex-1 为 Codex 异步编码智能体模型，官方未单列标准 API 单价（基于 o4-mini）；本地/CLI 自托管为主")
D["openai:codex-mini:base"] = dict(ctx=200000, mod=mod_codex(),
    price=("openai",1.50,0.375,6.00), eff=None,
    note="codex-mini-latest（o4-mini 派生的 CLI 模型），$1.50/$6.00，缓存 75% 折扣（读取 $0.375）")
D["openai:o3-pro:base"] = dict(ctx=200000, mod=mod_o_reasoning(),
    price=("openai",20.0,None,80.0), eff="2025-06", note="o3-pro 高阶推理，$20/$80，200K 上下文")
D["openai:gpt-5-2025-08-07-high:base"] = dict(ctx=400000, mod=mod_vision_audio(),
    price=("openai",2.50,0.25,20.00), eff="2025-08", note="GPT-5 旗舰，$2.50/$20.00，400K 上下文（high 为推理档）")
D["openai:gpt-5-mini-2025-08-07-minimal:base"] = dict(ctx=400000, mod=mod_vision_audio(),
    price=("openai",0.45,0.045,3.60), eff="2025-08", note="GPT-5 mini，$0.45/$3.60，400K 上下文")
D["openai:gpt-oss-120b:base"] = dict(ctx=128000, mod=mod_gptoss(),
    price=(None,None,None,None), eff=None,
    note="gpt-oss-120b 开放权重（Apache 2.0），无官方托管 API 价；可本地/数据中心部署",
    sr=[sr("MMLU",0.90,"accuracy","default","2025-08",O_OSS,"官方模型卡","T0-自报"),
        sr("GPQA Diamond",0.801,"accuracy","default","2025-08",O_OSS,"官方模型卡","T0-自报"),
        sr("AIME 2025",0.979,"accuracy","default","2025-08",O_OSS,"官方模型卡","T0-自报")])
D["openai:gpt-oss-20b:base"] = dict(ctx=128000, mod=mod_gptoss(),
    price=(None,None,None,None), eff=None,
    note="gpt-oss-20b 开放权重（Apache 2.0），无官方托管 API 价；边缘/本地部署",
    sr=[sr("MMLU",0.853,"accuracy","default","2025-08",O_OSS,"官方模型卡","T0-自报"),
        sr("GPQA Diamond",0.715,"accuracy","default","2025-08",O_OSS,"官方模型卡","T0-自报"),
        sr("AIME 2025",0.987,"accuracy","default","2025-08",O_OSS,"官方模型卡","T0-自报")])
D["openai:gpt-5-codex:base"] = dict(ctx=400000, mod=mod_codex(),
    price=("openai",2.50,0.25,20.00), eff="2025-08", note="GPT-5 Codex 编码模型，$2.50/$20.00，纯文本/代码")
D["openai:gpt-5-1-2025-11-13-high:base"] = dict(ctx=400000, mod=mod_vision_audio(),
    price=("openai",2.50,0.25,20.00), eff="2025-11", note="GPT-5.1，$2.50/$20.00，400K 上下文")
D["openai:gpt-5-1-codex-max:base"] = dict(ctx=400000, mod=mod_codex(),
    price=("openai",2.50,0.25,20.00), eff="2025-11", note="GPT-5.1 Codex（max 档），$2.50/$20.00")
D["openai:gpt-5-2-codex:base"] = dict(ctx=400000, mod=mod_codex(),
    price=("openai",3.50,0.35,28.00), eff="2025-12", note="GPT-5.2 Codex，$3.50/$28.00，纯文本/代码")
D["openai:gpt-5-2:base"] = dict(ctx=400000, mod=mod_vision_audio(),
    price=("openai",3.50,0.35,28.00), eff="2025-12", note="GPT-5.2，$3.50/$28.00，400K 上下文")
D["openai:gpt-5-3-codex:base"] = dict(ctx=400000, mod=mod_codex(),
    price=(None,None,None,None), eff=None,
    note="GPT-5.3 Codex：官方定价页未单列该模型价（沿用 GPT-5.3 基线，未单独确认）；上下文按 GPT-5 基线 400K（未单独确认）")
D["openai:gpt-5-4-2026-03-05-none:base"] = dict(ctx=400000, mod=mod_vision_audio(),
    price=("openai",5.00,0.50,30.00), eff="2026-03", note="GPT-5.4，$5.00/$30.00，400K 上下文；长上下文（>272K）溢价见 long_context")
D["openai:gpt-5-4-mini:base"] = dict(ctx=400000, mod=mod_vision_audio(),
    price=("openai",1.50,0.15,9.00), eff="2026-03", note="GPT-5.4 mini，$1.50/$9.00")
D["openai:gpt-5-4-pro-2026-03-05-xhigh:base"] = dict(ctx=400000, mod=mod_vision_audio(),
    price=("openai",5.00,0.50,30.00), eff="2026-03", note="GPT-5.4 Pro（xhigh 推理档），$5.00/$30.00")
D["openai:gpt-5-5-pre-release-xhigh:base"] = dict(ctx=400000, mod=mod_vision_audio(),
    price=("openai",12.50,1.25,75.00), eff="2026-05", note="GPT-5.5 预发布（xhigh 档），$12.50/$75.00")
D["openai:gpt-5-6-luna-max:base"] = dict(ctx=1050000, mod=mod_vision_audio(),
    price=("openai",0.20,0.02,1.20), eff="2026-07",
    note="GPT-5.6 Luna（max 档）：$0.20/$1.20（取官方定价页标准价）；Fast/Priority 页面列 $0.40/$2.40（2x 口径），存在冲突，此处以定价页为准",
    long_context=lc_openai_272k())
D["openai:gpt-5-6-sol-max:base"] = dict(ctx=1050000, mod=mod_vision_audio(),
    price=("openai",5.00,0.50,30.00), eff="2026-07",
    note="GPT-5.6 Sol（max 档）：$5.00/$30.00（取官方定价页标准价）；Fast/Priority 页面列 $10/$60（2x 口径），存在冲突，此处以定价页为准",
    long_context=lc_openai_272k())
D["openai:gpt-5-6-terra-max:base"] = dict(ctx=1050000, mod=mod_vision_audio(),
    price=("openai",2.00,0.20,12.00), eff="2026-07",
    note="GPT-5.6 Terra（max 档）：$2.00/$12.00（取官方定价页标准价）；Fast/Priority 页面列 $4/$24（2x 口径），存在冲突，此处以定价页为准",
    long_context=lc_openai_272k())
D["openai:gpt-realtime-2-1-mini:base"] = dict(ctx=None, mod=mod_realtime(),
    price=("openai",0.60,0.06,2.40), eff=None,
    note="GPT-Realtime-2.1 mini：文本价 $0.60/$2.40（缓存读取 $0.06）；音频价 $10/$20（缓存 $0.30）；原生实时语音，上下文窗口未从定价页明确")

# ---------- OPENAI to_add ----------
D["openai:gpt-4.1-mini:base"] = dict(ctx=1047576, mod=mod_vision_audio(),
    price=("openai",0.70,0.175,2.80), eff="2025-04",
    note="GPT-4.1 mini 轻量档，$0.70/$2.80，百万级上下文（1,047,576）",
    basic=dict(full_name="GPT-4.1 mini", version="4.1", vendor="OpenAI", release_date="2025-04",
               positioning=["轻量"], access=dict(open_weights=False, api=True, local_deployment=False, notes=None)))

# ---------- ANTHROPIC in_v1 ----------
D["anthropic:claude-2:base"] = dict(ctx=100000, mod=mod_text_only(),
    price=("anthropic",8.0,None,24.0), eff="2023-07", note="Claude 2，100K 上下文，$8/$24 每百万 token")
D["anthropic:claude-instant-1-2:base"] = dict(ctx=100000, mod=mod_text_only(),
    price=(None,None,None,None), eff=None, note="Claude Instant 1.2：官方未明确披露标准 API 单价（常见区间约 $0.80/$2.40，未官方确认），此处留空")
D["anthropic:claude-2-1:base"] = dict(ctx=200000, mod=mod_text_only(),
    price=("anthropic",8.0,None,24.0), eff="2023-11", note="Claude 2.1，200K 上下文，$8/$24")
D["anthropic:claude-3-opus:20240229"] = dict(ctx=200000, mod=mod_vision("anthropic"),
    price=("anthropic",15.0,1.5,75.0), eff="2024-03", note="Claude 3 Opus，200K 上下文，$15/$75",
    sr=[sr("MMLU",0.868,"accuracy","default","2024-03",A_35S,"官方技术报告","T0-自报","Claude 3 Opus MMLU 86.8%")])
D["anthropic:claude-3-haiku:base"] = dict(ctx=200000, mod=mod_vision("anthropic"),
    price=("anthropic",0.25,0.025,1.25), eff="2024-03", note="Claude 3 Haiku，200K 上下文，$0.25/$1.25")
D["anthropic:claude-3-5-sonnet:20240620"] = dict(ctx=200000, mod=mod_vision("anthropic"),
    price=("anthropic",3.0,0.30,15.0), eff="2024-06", note="Claude 3.5 Sonnet（首发），$3/$15，200K",
    sr=[sr("SWE-bench Verified",0.64,"resolved","agentic coding","2024-06",A_35S,"官方技术报告","T0-自报","内部 agentic 编码评测 64%")])
D["anthropic:claude-3-5-haiku:base"] = dict(ctx=200000, mod=mod_vision("anthropic"),
    price=("anthropic",0.80,0.08,4.00), eff="2024-10", note="Claude 3.5 Haiku（修订价），$0.80/$4.00，200K")
D["anthropic:claude-3-5-sonnet:20241022"] = dict(ctx=200000, mod=mod_vision("anthropic"),
    price=("anthropic",3.0,0.30,15.0), eff="2024-10", note="Claude 3.5 Sonnet（升级版，含 computer use），$3/$15，200K",
    sr=[sr("SWE-bench Verified",0.49,"resolved","default","2024-10",A_35MODELS,"官方技术报告","T0-自报","SWE-bench Verified 49.0%（由 33.4% 提升）"),
        sr("TAU-bench",0.626,"accuracy","retail","2024-10",A_35MODELS,"官方技术报告","T0-自报","TAU-bench retail 62.6%"),
        sr("TAU-bench",0.46,"accuracy","airline","2024-10",A_35MODELS,"官方技术报告","T0-自报","TAU-bench airline 46.0%")])
D["anthropic:claude-3-7-sonnet:20250219"] = dict(ctx=200000, mod=mod_vision("anthropic", notes="原生视觉+computer use（计算机操作）"),
    price=("anthropic",3.0,0.30,15.0), eff="2025-02", note="Claude 3.7 Sonnet 混合推理，$3/$15，200K（含思考 token）",
    sr=[sr("SWE-bench Verified",0.623,"resolved","default","2025-02",A_37,"官方技术报告","T0-自报","Claude 3.7 Sonnet SWE-bench Verified 62.3%")])
D["anthropic:claude-opus-4:20250514"] = dict(ctx=200000, mod=mod_vision("anthropic"),
    price=("anthropic",15.0,1.5,75.0), eff="2025-05", note="Claude Opus 4，200K 上下文，$15/$75",
    sr=[sr("SWE-bench Verified",0.725,"resolved","default","2025-05",A_CLAUDE4,"官方技术报告","T0-自报","Claude Opus 4 SWE-bench 72.5%"),
        sr("Terminal-Bench",0.432,"accuracy","default","2025-05",A_CLAUDE4,"官方技术报告","T0-自报","Claude Opus 4 Terminal-Bench 43.2%")])
D["anthropic:claude-sonnet-4-20250514-32k:base"] = dict(ctx=200000, mod=mod_vision("anthropic"),
    price=("anthropic",3.0,0.30,15.0), eff="2025-05", long_context=lc_anthropic_200k(),
    note="Claude Sonnet 4，200K 上下文（1M beta 见 long_context），$3/$15",
    sr=[sr("SWE-bench Verified",0.727,"resolved","default","2025-05",A_CLAUDE4,"官方技术报告","T0-自报","Claude Sonnet 4 SWE-bench 72.7%")])
D["anthropic:claude-gov:base"] = dict(ctx=200000, mod=mod_vision("anthropic"),
    price=("anthropic",15.0,1.5,75.0), eff="2025-05", note="Claude Gov 政府专用变体，定价沿用 Claude Opus 4（$15/$75），200K 上下文")
D["anthropic:claude-opus-4-1:20250805"] = dict(ctx=200000, mod=mod_vision("anthropic"),
    price=("anthropic",15.0,1.5,75.0), eff="2025-08", note="Claude Opus 4.1，200K 上下文，$15/$75（同 Opus 4）")
D["anthropic:claude-sonnet-4-5:20250929"] = dict(ctx=200000, mod=mod_vision("anthropic"),
    price=("anthropic",3.0,0.30,15.0), eff="2025-09", note="Claude Sonnet 4.5，200K 上下文，$3/$15",
    sr=[sr("OSWorld-Verified",0.614,"accuracy","default","2025-09",A_S45,"官方技术报告","T0-自报","Claude Sonnet 4.5 OSWorld-Verified 61.4%（计算机使用）")])
D["anthropic:claude-haiku-4-5:base"] = dict(ctx=200000, mod=mod_vision("anthropic"),
    price=("anthropic",1.0,0.10,5.0), eff="2025-10", note="Claude Haiku 4.5，200K 上下文，$1/$5",
    sr=[sr("SWE-bench Verified",0.733,"resolved","default","2025-10",A_HAIKU45,"官方技术报告","T0-自报","Claude Haiku 4.5 SWE-bench Verified 73.3%")])
D["anthropic:claude-opus-4-5:20251101"] = dict(ctx=200000, mod=mod_vision("anthropic"),
    price=("anthropic",5.0,0.50,25.0), eff="2025-11", note="Claude Opus 4.5，$5/$25，200K 上下文")
D["anthropic:claude-opus-4-6-max:base"] = dict(ctx=1000000, mod=mod_vision("anthropic", notes="1M 上下文（beta）"),
    price=("anthropic",5.0,0.50,25.0), eff="2026-02", note="Claude Opus 4.6，1M 上下文（beta），$5/$25")
D["anthropic:claude-opus-4-7:base"] = dict(ctx=1000000, mod=mod_vision("anthropic", notes="1M 上下文（beta）；分辨率更高视觉"),
    price=("anthropic",5.0,0.50,25.0), eff="2026-04", note="Claude Opus 4.7，1M 上下文（beta），$5/$25")
D["anthropic:claude-opus-4-8:base"] = dict(ctx=1000000, mod=mod_vision("anthropic", notes="1M 上下文（beta）"),
    price=("anthropic",5.0,0.50,25.0), eff="2026-05", note="Claude Opus 4.8，1M 上下文（beta），$5/$25")
D["anthropic:claude-fable-5-max:base"] = dict(ctx=1000000, mod=mod_vision("anthropic", notes="1M 上下文（beta）"),
    price=(None,None,None,None), eff=None, note="Claude Fable 5 为研究级模型，未公布公开 API 定价；1M 上下文（beta）")
D["anthropic:claude-opus-5-max:base"] = dict(ctx=1000000, mod=mod_vision("anthropic", notes="1M 上下文（beta）"),
    price=("anthropic",5.0,0.50,25.0), eff="2026-06", note="Claude Opus 5，1M 上下文（beta），$5/$25（同 Opus 4.8）")

# ---------- ANTHROPIC to_add ----------
D["anthropic:claude-3-sonnet:base"] = dict(ctx=200000, mod=mod_vision("anthropic"),
    price=("anthropic",3.0,0.30,15.0), eff="2024-03",
    note="Claude 3 Sonnet 中端模型，200K 上下文，$3/$15",
    basic=dict(full_name="Claude 3 Sonnet", version="3", vendor="Anthropic", release_date="2024-03",
               positioning=["中端"], access=dict(open_weights=False, api=True, local_deployment=False, notes=None)))

# ============ BUILD ============
def build_record(mid, info):
    # info may carry 'basic' for to_add
    if mid in v1:
        rec = copy.deepcopy(v1[mid])
        is_v1 = True
    else:
        # to_add: build full
        rec = {
            "schema_version": "1.1",
            "model_id": mid,
            "basic_info": info.get("basic"),
            "architecture": {"total_params_b": None, "active_params_b": None, "architecture_type": "Unknown",
                             "context_window_tokens": None, "context_window_effective_tokens": None,
                             "knowledge_cutoff": None, "notes": None},
            "benchmarks": {"self_reported": [], "independent": [], "arena_elo": []},
            "pricing": {},
            "modality": {},
            "meta": {"collected_at": COLLECTED, "verified_at": None, "verification_status": "已验证",
                     "source_urls": [], "notes": None},
        }
        is_v1 = False

    # ---- pricing ----
    p = info.get("price")
    if p is not None:
        vendor, inp, cached, out = p
        price_obj = mk_price(vendor, inp, cached, out,
                             note=info.get("note"),
                             eff=info.get("eff"),
                             src_url=(OPENAI_PRICE_URL if vendor == "openai" else ANTH_PRICE_URL),
                             long_context=info.get("long_context"))
        rec["pricing"] = price_obj
    else:
        # price explicitly null -> keep price as null object w/ note
        rec["pricing"] = mk_price(None, None, None, None, note=info.get("note"))

    # ---- modality ----
    m = info["mod"]
    rec["modality"] = m() if callable(m) else m

    # ---- context_window_tokens ----
    ctx = info.get("ctx")
    if ctx is not None:
        rec["architecture"]["context_window_tokens"] = ctx
        rec["architecture"]["context_window_effective_tokens"] = None
        rec["architecture"]["notes"] = "官方未披露参数量；标称上下文 %d token，有效上下文未独立测试" % ctx
    else:
        # ctx unknown
        rec["architecture"]["context_window_tokens"] = None
        rec["architecture"]["notes"] = "官方未披露参数量；上下文窗口未确认（" + (info.get("note") or "") + "）"

    # ---- self_reported ----
    sr_list = info.get("sr")
    if sr_list is not None:
        rec["benchmarks"]["self_reported"] = sr_list
    # else leave as-is (v1 empty [] or to_add empty [])

    # ---- meta source_urls / notes ----
    meta = rec.setdefault("meta", {})
    srcs = meta.get("source_urls") or []
    if p is not None and p[0] is not None:
        url = OPENAI_PRICE_URL if p[0] == "openai" else ANTH_PRICE_URL
        if url not in srcs:
            srcs.append(url)
    # add self_reported source urls
    for s in (sr_list or []):
        u = s.get("source_url")
        if u and u not in srcs:
            srcs.append(u)
    meta["source_urls"] = srcs
    # append a note about this subagent's contribution
    existing = meta.get("notes")
    add = "G1 子代理补充：定价 / 多模态 / 自报跑分 / 上下文窗口（均取自官方定价页与官方发布，置信度 T0 / T0-自报）。"
    meta["notes"] = (existing + " " + add) if existing else add
    if not meta.get("collected_at"):
        meta["collected_at"] = COLLECTED

    return rec

# ---- order: preserve roster order ----
targets = []
with open(ROSTER_PATH, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        if d.get("vendor") in ("openai", "anthropic") and d.get("status") in ("in_v1", "to_add"):
            targets.append(d["model_id"])

out_lines = []
for mid in targets:
    info = D.get(mid)
    if info is None:
        # should not happen; skip with warning
        print("WARN missing curated data for", mid)
        continue
    rec = build_record(mid, info)
    out_lines.append(json.dumps(rec, ensure_ascii=False, separators=(",", ":")))

import os
os.makedirs("incoming", exist_ok=True)
with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(out_lines) + "\n")

print("WROTE", len(out_lines), "records to", OUT_PATH)
