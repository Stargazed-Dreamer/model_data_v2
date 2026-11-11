# -*- coding: utf-8 -*-
"""
D59 / S2 采集包生成器（接手会话 2026-11-11 补跑）。

背景：Qoder 会话 29afb6cb 在 06:32 被报错 145 打断，断点在「S2 准备阶段」——
批次号 b353w1 / 厂商前缀 / 共享上下文 / 样板都已查明，但尚未写任何 S2 产物。
S1 范围由用户两轮 AskUserQuestion 拍板定死：采 15 条 + 丙类 4 条字段更新（后者已落库）。

证据口径（本脚本不联网，全部复用 S0 阶段已本地化的一手材料）：
  - temp/d59/d59_s0_candidates.jsonl  —— 29 条候选的核查结论（含 T0/T1/T2/T3 定级与 evidence URL）
  - temp/d59/or_verify.json            —— OpenRouter 469 模型快照（11-11 06:23 复验），定价/ctx/描述
  - temp/d59/*.html|txt|json          —— 三路 subagent 抓回的官方页与 HF API 回显
  - model_data_v2.jsonl               —— 同族既有记录的字段口径

红线：没查到 = null；不伪造 T0；OpenRouter 转售价**不冒充官方刊例价**（只进 notes 留痕）；
      参数量未披露必须在 architecture.notes 声明；日期按「OR created / HF createdAt 不是发布日」铁律。

用法： PYTHONUTF8=1 python scripts/d59_s2_build.py
重复运行会覆盖 15 个产物文件，并把台账里 b353w1 那一行整体替换（不会重复追加）。
按 scripts/dNN_*.py 轮次脚本惯例随仓库入库，避免 D52 那类「脚本随 temp/ 清理丢失」的退化。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "incoming" / "models"
LEDGER = ROOT / "docs" / "batch_claim_ledger.jsonl"
COLLECTED_AT = "2026-11-11"
BATCH = "b353w1"

MI_KEYS = ("text", "image", "audio", "video", "pdf", "code", "web")
MO_KEYS = ("text", "code", "image", "audio", "speech")
NM_KEYS = ("input_image", "input_audio", "input_video", "output_image", "output_audio")


def F(mid, name, ver, vendor, rd, pos, lic, ow, api, local,
      tp=None, ap=None, atype="Unknown", btype="Unknown", ctx=None, maxout=None, cutoff=None,
      pin=None, pout=None, pcached=None, pcw=None, pbi=None, pbo=None,
      purl=None, ptype=None, pconf=None,
      mi=None, mo=None, nm=None, urls=None, *,
      bi, access, arch, pricing, mi_note, mo_note, nm_note, meta):
    """一条事实 -> 完整 schema 1.1 记录。未提供的一律显式 null。"""
    has_price = any(v is not None for v in (pin, pout, pcached, pcw, pbi, pbo))
    # 未披露参数量的声明是门禁硬要求（规则 1），统一兜底，避免任何一条漏写
    if tp is None and ap is None and "未披露参数量" not in arch:
        arch = "官方未披露参数量。" + arch

    def blk(keys, overrides, note):
        d = {k: None for k in keys}
        d.update(overrides or {})
        d["notes"] = note
        return d

    rec = {
        "schema_version": "1.1",
        "model_id": mid,
        "basic_info": {
            "full_name": name, "version": ver, "vendor": vendor, "release_date": rd,
            "positioning": pos,
            "access": {"open_weights": ow, "api": api, "local_deployment": local, "notes": access},
            "license": lic,
            "notes": bi,
        },
        "architecture": {
            "total_params_b": tp, "active_params_b": ap,
            "architecture_type": atype, "backbone_type": btype,
            "context_window_tokens": ctx, "context_window_effective_tokens": ctx,
            "max_output_tokens": maxout, "reasoning_model": None,
            "knowledge_cutoff": cutoff, "notes": arch,
        },
        "benchmarks": {"self_reported": [], "independent": [], "arena_elo": []},
        "pricing": {
            "currency": "USD" if has_price else None,
            "unit": "per_million_tokens",
            "input": pin, "output": pout, "cached_input": pcached, "cache_write": pcw,
            "batch_input": pbi, "batch_output": pbo,
            "free_tier": None, "promotions": None, "long_context": None,
            "effective_date": COLLECTED_AT if has_price else None,
            "source_url": purl, "source_type": ptype, "confidence": pconf,
            "notes": pricing,
        },
        "modality": {
            "input": blk(MI_KEYS, mi, mi_note),
            "output": blk(MO_KEYS, mo, mo_note),
            "native_multimodal": blk(NM_KEYS, nm, nm_note),
        },
        "meta": {
            "collected_at": COLLECTED_AT, "verified_at": None,
            "verification_status": "待验证",
            "source_urls": urls or [],
            "notes": meta,
        },
    }
    # effective/标称两栏同值：门禁规则 2 只要求 effective <= 标称，此处在 arch notes 说明
    if ctx is not None:
        rec["architecture"]["notes"] += (
            f" context_window_effective_tokens 取官方标称 {ctx}（未独立实测，按执行细则 §2 口径）。"
        )
    return rec


COMMON_MI_NOTE = "证据不足的模态一律留 null，不用 false 冒充「官方明确不支持」。"
COMMON_MO_NOTE = "除文本输出外，官方未给出图像/音频/语音输出能力的一手表述，故留 null。"
COMMON_NM_NOTE = "官方未给出原生多模态编码器架构的一手表述，五项均留 null。"

FACTS = [
    # ---------------- 甲：本轮新发布 7 条 ----------------
    F("anthropic:claude-fable-5.2:base", "Claude Fable 5.2", "5.2", "Anthropic", "2026-11-09",
      ["旗舰", "推理增强", "工具调用增强"], "闭源 API (proprietary, API-only)",
      False, True, False,
      ctx=1000000,
      pin=8.0, pout=40.0, pcached=0.2, pcw=10.0, pbi=4.0, pbo=20.0,
      purl="https://www.anthropic.com/news/claude-fable-and-mythos-5-2",
      ptype="官方发布公告（自报）", pconf="T0",
      mi={"text": True, "image": True, "code": True},
      mo={"text": True, "code": True},
      urls=["https://www.anthropic.com/news/claude-fable-and-mythos-5-2",
            "https://openrouter.ai/anthropic/claude-fable-5.2",
            "https://claude.com/pricing"],
      bi="Anthropic 2026-11-09 官方新闻稿同时发布 Claude Fable 5.2 与 Mythos 5.2，发布日取该稿日期（T0）。库内已有 claude-fable-5.1:base（rd=2026-09-01，$10/$50），5.2 为其后继独立版本，按先例立行。positioning 依据官方新闻稿「most capable model for the most demanding technical work，在 coding / reasoning / vision 上较 5.1 有增益」归纳。",
      access="官方新闻稿与 OpenRouter 均以 API 形式提供，未见任何权重发布或本地部署说明，故 open_weights=false / api=true / local_deployment=false。库内 Fable 5.1 同为闭源 API。",
      arch="官方未披露参数量与架构细节，architecture_type / backbone_type 按红线置 Unknown，禁止凭同系列兄弟条目反推。context_window_tokens 取 OpenRouter 该条目的 context_length=1000000（与官方 1M 口径一致）。",
      pricing="官方新闻稿明示 $8/$40 每百万 token（较 Fable 5.1 的 $10/$50 降 20%），fast mode $16/$80。OpenRouter 同条目挂牌 prompt=$8 / completion=$40 / cache_read=$0.20 / cache_write(5m)=$10 / cache_write(1h)=$16，与官方稿一致，故主字段采用官方价；batch_input/batch_output=$4/$20 取自 OpenRouter 该模型的 :batch 服务档（同一模型不同计费档，非独立型号，按服务档不立行口径并入本行定价）。⛔ 未把 :batch 另立记录。effective_date 取本次采集日（官方稿未标注价格生效日）。",
      mi_note="text=true 为模型基本能力；image=true 依据官方新闻稿与 OpenRouter 描述「gains over Fable 5.1 in ... vision」；code=true 依据官方定位为技术/编码工作模型。" + COMMON_MI_NOTE,
      mo_note="text / code 输出为官方定位的编码与推理工作形态。" + COMMON_MO_NOTE,
      nm_note=COMMON_NM_NOTE,
      meta="裁定：独立模型，立行。依据官方 11-09 新闻稿有独立发布条目、OpenRouter 有独立 model id（anthropic/claude-fable-5.2，created=2026-11-09）与独立定价，且与库内 5.1 是明确的前后继关系。S1 三问：是模型 / 是新版本（非服务档或量化变体）/ 在范围（rd 2026-11-09）。服务档 :batch 已在同批剔除不立行（见 S0 候选丁类）。benchmarks 三数组留空：S2 单模型模板规定 arena_elo / independent 由平台统一采集，本轮官方新闻稿亦未公布任何基准分数。待复核：官方定价页未单独核对，1h cache write 与 fast mode 价格仅 OpenRouter 有量化值，已写入 pricing.notes。"),

    F("anthropic:claude-mythos-5.2:base", "Claude Mythos 5.2", "5.2", "Anthropic", "2026-11-09",
      ["旗舰"], "闭源 API (proprietary, trusted-access)",
      False, True, False,
      ctx=1000000,
      pin=8.0, pout=40.0, pcached=0.2,
      purl="https://www.anthropic.com/news/claude-fable-and-mythos-5-2",
      ptype="行业媒体转述官方发布", pconf="T3",
      mi={"text": True, "image": True},
      mo={"text": True},
      urls=["https://www.anthropic.com/news/claude-fable-and-mythos-5-2",
            "https://www.anthropic.com/news"],
      bi="Anthropic 2026-11-09 官方新闻稿与 Fable 5.2 同批发布。官方称 Mythos 5.2 与 Fable 5.2 是同一底层模型、仅安全限制不同，经 Cyber / LifeSciences 验证计划申请访问（trusted-access twin）。库内已有 claude-mythos-5.1:base 独立行（trusted-access）⇒ 按既有先例立行，而非并入 Fable 5.2 或只写防重 notes。",
      access="trusted-access 申请制，仅以 API 形式提供，无开放权重与本地部署口径，故 open_weights=false / api=true / local_deployment=false。",
      arch="官方未单列 Mythos 5.2 的参数量与架构；因官方称与 Fable 5.2 同一底层模型，这里 context_window_tokens 暂沿用其 1M 标称值并在本栏标注为推定值，待官方规格页确认后定档。architecture_type / backbone_type 置 Unknown。",
      pricing="⛔ 官方新闻稿未单独列出 Mythos 5.2 刊例价，OpenRouter 目录亦无该条目。本行 $8/$40/$0.20 是依据「与 Fable 5.2 同一底层模型」沿用其官方价，属推定，故 confidence 标 T3 而非 T0，并在本栏留痕；不得据此声称已核实官方定价。cache_write / batch_input / batch_output 官方与第三方均无 Mythos 专属值，置 null。库内 Mythos 5.1 的定价同样是媒体转述（T3）口径，与此一致。",
      mi_note="与 Fable 5.2 同一底层模型，text / image 输入沿用其口径；其余官方未提，留 null。",
      mo_note="官方未给出该变体的输出模态差异，仅 text=true。",
      nm_note=COMMON_NM_NOTE,
      meta="裁定：立行（依据库内 claude-mythos-5.1:base 的 trusted-access 独立行先例 + 官方独立发布条目）。⚠ 官方称与 Fable 5.2 同一底层模型、仅安全限制不同 —— 这与「同一 checkpoint 变体不立行」的服务档口径表面冲突，但 5.1 已确立独立行判例且本轮 S1 已把 Mythos 5.2 列入采集清单，故按判例立行；若后续官方明确两者同 model id，应合并并在 notes 留痕。S0 台账补漏：该模型不在 OpenRouter，纯差集扫描捞不到，是 news 台账路径才发现的。待复核：售价、上下文窗口均为沿用推定（T3）。"),

    F("tencent:hunyuan-hy4:base", "Hunyuan Hy4（正式版）", "4", "Tencent", "2026-11-04",
      ["旗舰", "多模态", "工具调用增强", "推理增强"], None,
      False, True, False,
      tp=770.0, ap=49.0, atype="MoE", ctx=1048576,
      purl="https://cloud.tencent.com/document/product/1823/130055",
      ptype="官方定价页核对（正式版未单列）", pconf="T0",
      mi={"text": True, "image": True, "code": True},
      mo={"text": True, "code": True},
      urls=["https://www.tencent.com/zh-cn/tencent-launches-hy4.html",
            "https://openrouter.ai/tencent/hy4",
            "https://cloud.tencent.com/document/product/1823/130055",
            "https://huggingface.co/tencent"],
      bi="腾讯 2026-11-04 官方发布页宣布 Hy4 正式版（GA）。库内只有 hunyuan-hy4-preview:base（rd=2026-08、open_weights=true / Apache-2.0）。正式版在 OpenRouter 与腾讯云各有独立 model id，OpenRouter 描述原文「The official release of Hy4 delivers comprehensive and substantial improvements over Hy4 Preview」⇒ 判定为**不同 checkpoint**，按 S1「独立测量身份」口径另立行，不并入 preview。发布日取官方发布页 11-04（T0），另有同花顺 T2 佐证。",
      access="⚠ 正式版权重截至本轮核查**未放出**：本人 HF API 复验 tencent 组织只有 Hy4-Preview 仓库，无 GA 权重仓或许可声明 ⇒ open_weights=false / local_deployment=false；OpenRouter 与腾讯云均以 API 形式提供 ⇒ api=true。与 preview 行（Apache-2.0、开放权重）形成明确差异，这也是判定不同 checkpoint 的旁证之一。license 置 null：官方未公布正式版权重许可，不照抄 preview 的 Apache-2.0。",
      arch="770B 总 / 49B 激活 MoE、原生 1M 上下文，沿用 Hy4 系列官方规格（preview 行库内已按此记录，T0）；正式版首发视觉理解与 Computer Use 能力。官方未给出主干结构（decoder-only 等）的一手表述，backbone_type 置 Unknown；max_output_tokens / knowledge_cutoff / reasoning_model 官方未列，置 null。",
      pricing="⛔ 官方腾讯云定价页只列 Hy4-Preview 的 $0.834/$2.501；正式版 GA 的挂牌价只见于 OpenRouter（prompt=$0.417 / completion=$1.2505 / cache_read=$0.021，每百万 token），属**第三方转售价**，按 _m_context.md 红线禁止冒充官方刊例价填入主字段 ⇒ 六个价键与 currency 全部置 null，数值仅在本栏留痕。source_type 记的是「已核对官方渠道确认未单列」这个核实动作，故 confidence=T0 不属伪造。待腾讯云正式版定价页上线后重采。",
      mi_note="官方发布页称正式版首带视觉能力，故 image=true；text / code 为编码与生产力场景的基本输入形态。" + COMMON_MI_NOTE,
      mo_note="文本与代码输出为官方定位的 agentic / 生产力工作流形态。" + COMMON_MO_NOTE,
      nm_note=COMMON_NM_NOTE,
      meta="★ 用户 S1 拍板点④「preview→正式版按官方是否同 checkpoint 逐个判」的判定结果：**Hy4 GA 立独立行**。证据：①OpenRouter 独立条目 tencent/hy4（created 2026-11-04）与 tencent/hy4-preview 并存且描述明写 substantial improvements over Preview；②官方发布页独立发布条目；③preview 开放权重而 GA 权重未放出。三者共同指向不同 checkpoint，不是同一模型的服务档。⛔ 未把 preview 的 Apache-2.0 许可、$0.834/$2.501 定价或 open_weights=true 移植到本行。待复核：GA 权重放出后需重采 access / license，届时本行与 preview 是否合并应重新裁定。"),

    F("meta:muse-ember:base", "Muse Ember", "1.0", "Meta", "2026-11-09",
      ["轻量", "推理增强", "多模态", "工具调用增强"],
      "闭源 API (proprietary, 无开放权重)",
      False, True, False,
      ctx=1048576, maxout=512000,
      pin=0.1, pout=0.5, pcached=0.004, pcw=0.125,
      purl="https://m.163.com/dy/article/LBBV5VEH0511D2LM.html",
      ptype="行业媒体转述官方发布", pconf="T3",
      mi={"text": True, "image": True, "audio": True, "video": True, "pdf": True},
      mo={"text": True},
      nm={"input_image": True, "input_audio": True, "input_video": True},
      urls=["https://m.163.com/dy/article/LBBV5VEH0511D2LM.html",
            "https://openrouter.ai/meta/muse-ember"],
      bi="Meta 2026-11-09 发布 Muse Ember（model id 记作 muse-ember-1.0）。⚠ 中文稿里出现的「11 月 10 日」是北京时间**报道日**，不是发布日，release_date 取 11-09（与 OpenRouter created 一致）。ai.meta.com / developer.meta.com 本轮实测全域 000 不可达，Meta 官方一手缺位 ⇒ 定级 T2/T3，按降级采集口径处理。positioning 依据「smallest and most efficient model ... designed for complex reasoning execution and the work agents repeat all day: tool calls, coding agent subtasks, routing」归纳。",
      access="权重私有、纯托管服务，OpenRouter 以 API 形式提供，官方及媒体均未给出开放权重或本地部署路径 ⇒ open_weights=false / api=true / local_deployment=false。",
      arch="官方未披露参数量，architecture_type / backbone_type 置 Unknown，禁止凭 Muse 系列兄弟条目反推。context_window_tokens 取 OpenRouter context_length=1048576（约 1M），max_output_tokens=512000 取中文转述稿；两者均为第三方口径，已在来源处标注 T3。knowledge_cutoff / reasoning_model 官方未列，置 null。",
      pricing="价格来自中文媒体转述稿（$0.10/$0.50、cached $0.004）与 OpenRouter 挂牌（prompt=$0.10 / completion=$0.50 / cache_read=$0.004 / cache_write=$0.125，每百万 token），两者一致，但**均非 Meta 官方自营刊例价** ⇒ confidence=T3，source_type=行业媒体转述官方发布（与库内 meta:muse-wonder:base 同口径）。batch_input / batch_output 官方与 OpenRouter 均未列，置 null。待 Meta 官方定价页可达后升级定级。",
      mi_note="中文转述稿明写原生支持 text / image / audio / video / PDF 输入，据此置 true；code / web 官方未单列，留 null。",
      mo_note="仅文本输出有明确表述；图像/音频/语音输出官方未提，留 null。",
      nm_note="中文稿称上述多模态为原生能力，故 input_image / input_audio / input_video 置 true；输出侧两项无依据，留 null。⚠ 该判定建立在 T3 转述上，定级不可升 T0。",
      meta="裁定：独立模型，立行。S1 三问：是模型（非训练系统 / 非服务档）/ 是新发布（库内 Meta 只有 muse-wonder、muse-spark 系列，无 Muse Ember）/ 在范围（rd 2026-11-09）。★ 降级采集声明：ai.meta.com 与 developer.meta.com 本轮全域不可达，本条规格经媒体转述稿 + OpenRouter 快照交叉核实，未直读 Meta 官方一手，所有 T3 项均已在对应字段留痕。待复核：官方域恢复后重采参数量、定价与许可。"),

    F("ricursive:ripple-65b-preview:base", "Ripple-65B-Preview", "65B-Preview",
      "Ricursive Intelligence", "2026-11-04",
      ["中端", "工具调用增强"], "Apache-2.0",
      True, None, True,
      tp=65.0, ap=None, atype="Dense", btype="Transformer", ctx=1048576,
      purl="https://huggingface.co/ricursiveAI/Ripple-65B-Preview",
      ptype="开源权重模型核对（无官方 API 价）", pconf="T0",
      mi={"text": True, "code": True},
      mo={"text": True},
      urls=["https://huggingface.co/ricursiveAI/Ripple-65B-Preview",
            "https://huggingface.co/api/models/ricursiveAI/Ripple-65B-Preview",
            "https://openrouter.ai/ricursiveai/ripple-65b-preview"],
      bi="★ 新厂商首条（库内 ricursive 前缀 0 条）。Ricursive Intelligence 2026-11-04 发布 Ripple-65B-Preview，发布日取 HF 仓库 createdAt 2026-11-04T02:41 与 OpenRouter created 一致的日期，并经本人 HF API 复验（HTTP 200、16 个 safetensors、license=apache-2.0、downloads 6480）。⚠ 厂商名 `ricursive` **不是拼写错误**，官方域名是 ricursive.com（不是 .ai）；⛔ 与 `Recursive`（Recursive Flint，Richard Socher）是两家不同公司，禁止合并。",
      access="HF 仓库直读 200、16 个 safetensors、Apache-2.0 ⇒ open_weights=true / local_deployment=true。厂商是否有自营 API 刊例价未查到一手证据，api 置 null（不肯定也不否定）。",
      arch="HF 模型卡明写 65B 稠密 Transformer（非 MoE）、d_model=5120 / 80 层、12T tokens 从零预训练、原生 ctx 1,048,576 ⇒ architecture_type=Dense、backbone_type=Transformer（均有本条一手原文，非凭名字反推）。active_params_b 稠密模型无独立激活参，置 null；knowledge_cutoff / max_output_tokens / reasoning_model 官方未列，置 null。",
      pricing="⛔ OpenRouter 挂牌 $0.20/$0.60（cache_read $0.05，每百万 token）属**第三方转售价**，厂商自营 API 刊例价未查到 ⇒ 六个价键与 currency 全置 null，数值仅在本栏留痕，不冒充官方价。source_type 记「已核对官方渠道确认无自营刊例价」这一核实动作，confidence=T0 不属伪造。",
      mi_note="OpenRouter 描述「65B model with native tool calling, served in BF16」，据此 text / code=true；未见图像/音频/视频/PDF 输入表述，留 null。",
      mo_note="仅文本输出有依据。" + COMMON_MO_NOTE,
      nm_note=COMMON_NM_NOTE,
      meta="裁定：独立模型，立行（库内该厂商 0 条，S1 第 1/2/3 问全部通过）。★ 新厂商前缀 `ricursive` 按官方名 Ricursive Intelligence 取，vendor 显示名与 OpenRouter 的组织名 ricursiveAI 分开记。⛔ 与 Recursive Flint（本轮被用户拍板剔除）是两家，S0 候选已明确禁止合并。待复核：厂商自营 API 刊例价、知识截止日。"),

    F("baidu:ernie-5.5-flash-base:base", "ERNIE-5.5-Flash-Base", "5.5-Flash-Base",
      "Baidu", "2026-11-05",
      ["旗舰", "推理增强"], "ERNIE 5.5 Flash Base Model License v1.0",
      True, None, True,
      tp=280.0, ap=14.0, atype="MoE", ctx=1048576,
      purl="https://ernie.baidu.com/release/",
      ptype="开源权重模型核对（无官方 API 价）", pconf="T0",
      mi={"text": True},
      mo={"text": True},
      urls=["https://ernie.baidu.com/release/",
            "https://huggingface.co/baidu/ERNIE-5.5-Flash-Base",
            "https://huggingface.co/baidu/ERNIE-5.5-Flash-Base-BF16"],
      bi="★ 台账补漏：OpenRouter 上只有 ERNIE-5.5-Flash-Preview，**Base 才是开放权重那个**。官方 release 页（200 可达）明确列 5.5 Flash Base 于 2026-11-05 发布，故 release_date 取 11-05（T0）。本人 HF API 复验 baidu/ERNIE-5.5-Flash-Base HTTP 200（createdAt 2026-10-21、lastModified 2026-11-05、128 个 safetensors），另有 -BF16 仓。库内 Baidu 7 条最新只到 ernie-5.1（2026-05-09）。⛔ 勿把 Preview 的 OR 描述（280B 总参）当成另一条模型的规格——S0 已把 Preview 退回观察，理由是官方与 HF 组织页均无该 checkpoint 对应物。",
      access="HF 官方组织仓与 -BF16 量化仓均直读 200、许可为自定义 ERNIE 5.5 Flash Base Model License v1.0 ⇒ open_weights=true / local_deployment=true；厂商是否对该 Base 单列自营 API 价未取到一手证据，api 置 null。",
      arch="HF 模型卡：280B 总 / 14B 激活、43 层、33.5T tokens、训练 128K → 推理 1M。总参与激活参并列给出 ⇒ architecture_type=MoE；官方未给主干结构一手表述，backbone_type 置 Unknown。context_window_tokens 取推理侧 1,048,576，训练侧 128K 在本栏留痕。knowledge_cutoff / max_output_tokens / reasoning_model 官方未列，置 null。",
      pricing="⛔ 未查到该 Base checkpoint 的厂商自营 API 刊例价（官方 release 页只列发布条目，不列定价；OpenRouter 只有 Preview 的挂牌 $0.28/$1.13，属另一 checkpoint 且为第三方转售价，按 S0 结论不得移植）⇒ 六个价键与 currency 全置 null。source_type 记核对动作，confidence=T0。",
      mi_note="Base 是无后训练的 completions 基座，仅文本输入有依据；其余官方未提，留 null。",
      mo_note="仅文本输出有依据。",
      nm_note=COMMON_NM_NOTE,
      meta="裁定：独立模型，立行。S1 三问：是模型（Base checkpoint，非服务档 / 非量化变体）/ 是新的（库内 Baidu 最新到 5.1）/ 在范围（2026-11-05）。★ 许可留痕：ERNIE 5.5 Flash Base Model License v1.0 规定 ≤$50M 年收入需通知并标注 Powered by ERNIE，且排除欧盟/英国/韩国使用。⛔ 同批的 -BF16 仓是量化变体，按 D35 口径不立行；ERNIE-5.5-Flash-Preview 已退回观察（官方与 HF 组织页均无对应 checkpoint，OR 的 280B 疑抄自 Base）。待复核：Base 的官方 API 定价与知识截止日。"),

    F("meituan:longcat-2.5:base", "LongCat-2.5（正式开放权重版）", "2.5", "Meituan", None,
      ["旗舰", "多模态", "工具调用增强"], None,
      True, None, True,
      ctx=1048576,
      purl="https://longcat.chat/platform/docs/zh/api-pay-as-you-go",
      ptype="官方定价页核对（正式版未单列）", pconf="T0",
      mi={"text": True},
      mo={"text": True},
      urls=["https://huggingface.co/meituan-longcat/LongCat-2.5",
            "https://huggingface.co/meituan-longcat/LongCat-2.5-W4A4",
            "https://longcat.chat/platform/docs/zh/api-pay-as-you-go"],
      bi="★ 用户 S1 拍板点④「preview→正式版按官方是否同 checkpoint 逐个判」的第二条。本人 HF API 复验 meituan-longcat/LongCat-2.5 createdAt 2026-11-04（另有 -W4A4 同日）。⚠ **release_date 置 null**：同事查到「11-02 发布 / 11-10 开源」与 HF createdAt 11-04 三个口径冲突，按跟踪源清单 §4 日期铁律（HF createdAt 是仓库日不是发布日）与红线「查不到不硬填」，留待二查。库内已有 longcat-2.5-preview:base（rd=2026-09-25、open_weights=false、闭源 API）。",
      access="HF 有 GA 独立权重仓 ⇒ open_weights=true / local_deployment=true；OpenRouter 无 GA 条目，厂商是否对 GA 单列自营 API 未取到一手证据，api 置 null。license 置 null：官方未给出 GA 权重许可的一手表述，不照抄库内 LongCat-2.0 的 MIT。",
      arch="官方未披露 GA 版参数量与架构细节，architecture_type / backbone_type 置 Unknown。context_window_tokens=1048576 沿用库内 preview 行官方口径（longcat.chat 接口文档 context_length），⚠ 属同族沿用值而非 GA 版独立取证，待官方 GA 模型卡确认。knowledge_cutoff / max_output_tokens / reasoning_model 置 null。",
      pricing="⛔ 官方 longcat.chat 按量付费页只列 LongCat-2.5-Preview 与 LongCat-2.0 的 $0.30/$1.20，GA 版未见单列；OpenRouter 亦无 GA 条目 ⇒ 六个价键与 currency 全置 null，不把 preview 价移植到本行。source_type 记核对动作，confidence=T0。",
      mi_note="GA 版权重仓已知为文本模型；preview 行的 image=true 属另一 checkpoint，不移植。" + COMMON_MI_NOTE,
      mo_note="仅文本输出有依据。",
      nm_note=COMMON_NM_NOTE,
      meta="★ 判定结果：**立独立行**。证据：①HF 有独立的 GA 权重仓（createdAt 11-04）与 -W4A4 量化仓，而 preview 行明确记为 open_weights=false 且在 notes 里写「第三方称官方承诺另行开源本代权重」⇒ GA 权重兑现是相对 preview 的实质产物差异；②OpenRouter 无 GA 条目，说明它不是「同一模型的服务档」；③两者发布时间相隔一个半月。⚠ 但官方**未逐字声明** GA 与 preview 是否同一 checkpoint，本行按「独立测量身份（独立权重仓 + 独立许可口径）」立行，并在本栏留痕；若官方后续明确为同 checkpoint，应合并回 preview 行并归零 r1/r2。⛔ -W4A4 是量化变体，按 D35 不立行。待二查：发布日（三口径冲突）、GA 权重许可、参数量、Arena 独立跑分。"),

    # ---------------- 乙：上轮漏采 8 条 ----------------
    F("google:gemini-4-carbon:base", "Gemini 4 Carbon", "4 Carbon", "Google", "2026-10-28",
      ["旗舰", "推理增强", "多模态", "工具调用增强"],
      "闭源 API (proprietary, API-only)",
      False, True, False,
      ctx=1048576,
      pin=2.0, pout=10.0, pcached=0.1, pcw=0.1875,
      purl="https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-carbon/",
      ptype="官方发布公告（多源交叉）", pconf="T1",
      mi={"text": True, "image": True, "audio": True, "video": True},
      mo={"text": True},
      urls=["https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-carbon/",
            "https://openrouter.ai/google/gemini-4-carbon"],
      bi="★ 上轮漏采：发布日 2026-10-28 **早于**上轮采集截止 10-31，纯差集式 S0 结构上捞不到。本轮靠 S0-b 榜单全量反推发现（LMArena 2026-11-08 快照文本榜 #1、elo=1527，反推工具误把它归进 naming_diff 并错配到 gemini-4-argon，人工翻前 60 条才提出）。官方原文「complements rather than replaces Argon」⇒ 与库内 gemini-4-argon:base 是**同代并列档、非后继**，应另立行。⚠ blog.google / deepmind.google / ai.google.dev 本轮复测全域 000 不可达，日期经两个 agent 独立多源交叉 ⇒ 定级 T1，不冒充 T0。",
      access="仅 API 托管，无开放权重表述 ⇒ open_weights=false / api=true / local_deployment=false。",
      arch="官方未披露参数量与架构细节，architecture_type / backbone_type 置 Unknown。context_window_tokens 取 OpenRouter context_length=1048576。knowledge_cutoff / max_output_tokens / reasoning_model 官方未列，置 null。",
      pricing="官方发布公告给出介绍价 $2/$10 每百万 token，期后恢复 $4/$20；OpenRouter 挂牌 prompt=$2 / completion=$10 / cache_read=$0.10 / cache_write=$0.1875（另有 image/audio/web_search 等按次计价，未纳入本库六价键）。因官方域本轮不可直读、价格经多源交叉与 OpenRouter 快照印证 ⇒ confidence=T1，并在本栏留痕「期后价 $4/$20」。batch_input / batch_output 取 :batch 服务档但不并入本行定价，置 null。",
      mi_note="OpenRouter 描述「takes text, image, audio, video and file input」，据此 text/image/audio/video=true；pdf（file 是否含 PDF 无明确表述）、code、web 留 null。",
      mo_note="仅文本输出有依据（描述称 produces text）。",
      nm_note=COMMON_NM_NOTE,
      meta="裁定：独立模型，立行。★ 两条方法论留痕：①**非差集路径的价值**——rd 早于上轮截止，纯差集永远捞不到，本条靠榜单全量反推 + 人工复核准入；②**反推工具的模糊匹配不可尽信**——difflib 把 Carbon 错配到 Argon 判为 naming_diff，与 D39 的 Claude Opus 5 误配同类。⚠ OR 上架 11-10 滞后发布日 13 天，再次印证「OR created ≠ 发布日」铁律。arena_elo 数组留空：按 S2 单模型模板由平台统一采集，LMArena #1/elo 1527 仅作发现线索，不自行写入。待复核：官方域恢复后重采参数量、期后定价与 Arena 分数。"),

    F("liquid:lfm3-1.7b:base", "LFM3-1.7B", "3", "Liquid AI", "2026-10-27",
      ["轻量"], "LFM Open License v1.0",
      True, None, True,
      tp=1.73, ap=None, atype="Dense", btype="Hybrid", ctx=262144,
      purl="https://www.liquid.ai/blog/lfm3",
      ptype="开源权重模型核对（无官方 API 价）", pconf="T0",
      mi={"text": True},
      mo={"text": True},
      urls=["https://www.liquid.ai/blog/lfm3",
            "https://huggingface.co/LiquidAI/LFM3-1.7B",
            "https://huggingface.co/LiquidAI"],
      bi="★ 上轮漏采：发布日 2026-10-27 早于上轮截止 10-31，OpenRouter 上架 11-06 滞后 10 天，纯差集捞不到。本人 HF API 复验 LiquidAI/LFM3-1.7B HTTP 200、createdAt 10-23、license=other、downloads 82718。库内 Liquid AI 已有 4 条（lfm2.5 系列）。本轮用户拍板**只采 LFM3-1.7B 文本版**，同批 5 个多模态兄弟仓不采。",
      access="HF 官方仓权重直读 200、LFM Open License v1.0 ⇒ open_weights=true / local_deployment=true；未查到厂商自营 API 刊例价，api 置 null。",
      arch="官方博客 / HF 模型卡：1.73B、ctx 256K（输入+输出合计）、tri-hybrid 24 层 = 13 门控短卷积 + 5 滑窗注意力(窗口 256) + 6 全局注意力、22T tokens。architecture_type 按稀疏性置 Dense（1.73B 无 MoE 路由），backbone_type 按三种层混合置 Hybrid；⚠ **架构不是 CfC**（旧代 LFM 的 Liquid 神经网络口径），本栏按本代官方原文重判，未沿用系列旧结论。active_params_b 稠密模型无独立激活参，置 null；knowledge_cutoff / max_output_tokens / reasoning_model 官方未列，置 null。",
      pricing="⛔ 未查到厂商自营 API 刊例价；OpenRouter 的 lfm-3-1.7b:free 是第三方免费服务档，不构成官方价 ⇒ 六个价键与 currency 全置 null。source_type 记核对动作，confidence=T0。",
      mi_note="文本版，仅 text=true；官方未提图像/音频/视频/PDF/代码/网页输入，留 null。",
      mo_note="仅文本输出有依据。",
      nm_note=COMMON_NM_NOTE,
      meta="裁定：独立模型，立行。★ 家族范围按用户拍板只收 LFM3-1.7B 文本版：HF 组织页实测还有 LFM3-VL-2B / LFM3-Audio-2B / LFM3-Omni-2B / d1-2B / d1-Omni-2B（均 createdAt 10-27），以及大量 GGUF / MLX / ONNX 量化仓 —— 多模态兄弟仓本轮不采，量化仓按 D35 口径永久不立行，均在此留痕防重。待复核：知识截止日、厂商自营 API 定价。"),

    F("zhipu:glm-5.3-flashx-legal:base", "GLM-5.3-FlashX-Legal", "5.3", "Zhipu AI",
      "2026-10-12", ["推理增强", "中端"], None,
      None, True, None,
      ctx=1048576,
      purl="https://docs.bigmodel.cn/cn/guide/start/model-overview",
      ptype="官方模型清单核对（无独立刊例价）", pconf="T0",
      mi={"text": True, "image": True, "video": True},
      mo={"text": True},
      urls=["https://docs.bigmodel.cn/cn/guide/start/model-overview",
            "https://openrouter.ai/z-ai/glm-5.3-flashx-legal"],
      bi="法律域 mid-training + post-training 变体，有独立 model code 且列在官方核心模型清单内。发布日 2026-10-12 出自 z.ai/blog/assets/glm-legal-C520yt-y.js（200），⚠ 另一路核查**未复现**该日期 ⇒ 标待二查，本行暂取 10-12 并留痕。基于 GLM-5.3-Flash；Harvey LAB 19.2%（+12.5）；Beta 申请制。★ 母体 GLM-5.3-FlashX 经查是 Flash 的同底座**速度档**（官方页标题即「GLM-5.3-Flash/FlashX」，320B-A18B、共用技术报告，FlashX 仅 200 tokens/s）⇒ FlashX 本身不立行，已在 zhipu:glm-5.3-flash:base 的 notes 补防重（丙类第 4 条）。",
      access="⚠ 开放权重口径冲突：HF zai-org 无 Legal 仓库、官方无开源表述，但 Vals AI 标 open-weight ⇒ open_weights 置 **null**（不肯定也不否定），local_deployment 同置 null；官方核心模型清单与 OpenRouter 均提供 API ⇒ api=true。license 置 null。",
      arch="官方未披露 Legal 变体自身的参数量与架构；母体 GLM-5.3-Flash/FlashX 的 320B-A18B 属**另一型号规格**，按红线禁止移植 ⇒ 两栏参数量置 null。context_window_tokens=1048576 取 OpenRouter 该条目 context_length。architecture_type / backbone_type 置 Unknown（母体 MoE 不反推）。",
      pricing="⛔ OpenRouter 挂牌 $0.37/$1.25（cache_read $0.075，每百万 token）属第三方转售价，官方模型清单未给 Legal 变体独立刊例价 ⇒ 六个价键与 currency 全置 null，数值仅在本栏留痕。source_type 记核对动作，confidence=T0。",
      mi_note="OpenRouter 描述「native multimodal model that accepts text, image, and video input and produces text」，据此 text/image/video=true；其余留 null。",
      mo_note="描述明写 produces text；其余留 null。",
      nm_note=COMMON_NM_NOTE,
      meta="裁定：独立模型，立行。依据：法律域后训练变体有**独立 model code**、在官方核心模型清单内、OpenRouter 独立条目与独立定价 —— 与「同底座服务档（FlashX）」不是一回事：服务档只改速度配置，本条改的是训练数据与能力域，属独立测量身份。⛔ 母体 FlashX 不立行（丙类第 4 条已在 glm-5.3-flash 补防重 notes）；Harvey LAB 19.2%(+12.5) 属厂商自报跑分，本轮未取得可独立引用的官方基准文件 URL，按「每个 benchmarks 条目必须带 source_url」红线**不入库**，仅在此留痕。待二查：发布日 10-12（另一路未复现）、开放权重口径（Vals AI 与 HF 组织页冲突）。"),

    F("iflytek:spark-x2.6:base", "Spark X2.6", "X2.6", "iFlytek", "2026-10-22",
      ["旗舰", "推理增强"], "闭源 API (proprietary, API-only)",
      False, True, False,
      tp=293.0, ap=30.0, atype="MoE", ctx=1048576,
      purl="https://maas.xfyun.cn/doc/guide/2%E3%80%81%E6%A8%A1%E5%9E%8B%E4%BB%8B%E7%BB%8D/2.1.1%20Spark-X2.6.html",
      ptype="官方定价页核对（JS 壳未取证）", pconf="T0",
      mi={"text": True},
      mo={"text": True},
      urls=["https://maas.xfyun.cn/doc/guide/2%E3%80%81%E6%A8%A1%E5%9E%8B%E4%BB%8B%E7%BB%8D/2.1.1%20Spark-X2.6.html",
            "https://github.com/llm2014/llm_benchmark"],
      bi="D58 遗留（致知小众榜照出的三个 2026 新模型之一）。库内讯飞实测只有 2 条：spark-4.0(2024-06-27) / spark-x1(2025-01-15)，X2 / X2.5 中间代际亦缺。发布日 10-22 取多数媒体口径（少数写 10-24）。★ 本行采**云端版**（293B-A30B、ctx 1M、权重未开放）；同代还有 X2.6-4B 开源版（HF XHToken、apache-2.0，架构同 X2.5-4B 靠后训练提升，effort none/low/high）与 X2.6-Preview（256K），本轮按 S1 只立云端版一行，其余留痕不立行。",
      access="云端版权重未开放，官方 MaaS 以 API 形式提供 ⇒ open_weights=false / api=true / local_deployment=false；license 记专有闭源 API。",
      arch="官方 MaaS 文档给出云端版 293B 总 / 30B 激活、ctx 1M ⇒ architecture_type=MoE；官方未给主干结构一手表述，backbone_type 置 Unknown。knowledge_cutoff / max_output_tokens / reasoning_model 官方未列，置 null。⚠ 293B-A30B 属云端版规格，4B 开源版与 Preview 版规格不同，不混填。",
      pricing="⚠ 定价待二查：二手口径一致称「限时 输入 0.9 / 缓存命中 0.08 / 输出 3.6 元每百万 token」，但官方 MaaS 页是 JS 壳、本轮未取到可引用正文 ⇒ 六个价键与 currency 全置 null，二手数值仅在本栏留痕，不填入主字段（且为 CNY，按红线需可查汇率折算后才可入库，本轮无汇率依据）。source_type 记核对动作，confidence=T0。",
      mi_note="官方 MaaS 文档仅明确文本输入；其余官方未提，留 null。",
      mo_note="仅文本输出有依据。",
      nm_note=COMMON_NM_NOTE,
      meta="裁定：独立模型，立行（云端版）。★ 三个测量身份的处置：云端版立本行；X2.6-4B 开源版与 X2.6-Preview 属同型号不同规格档，本轮按 S1 不另立行，在此留痕防重；若后续官方给出独立 model id 与独立跑分，按「独立测量身份」口径重判。⛔ 未把 4B 版的 apache-2.0 许可或 Preview 的 256K ctx 移植到本行。待二查：官方定价正文（JS 壳）、发布日 10-22 vs 10-24。"),

    F("huawei:openpangu-2.0-pro:base", "openPangu-2.0-Pro", "2.0-Pro", "Huawei",
      "2026-07-31", ["旗舰", "推理增强"],
      "OPENPANGU MODEL LICENSE 2.0（代码 Apache-2.0）",
      True, None, True,
      tp=505.0, ap=18.0, atype="MoE", ctx=524288,
      purl="https://huggingface.co/openpangu/openPangu-2.0-Pro",
      ptype="开源权重模型核对（无官方 API 价）", pconf="T0",
      mi={"text": True},
      mo={"text": True},
      urls=["https://huggingface.co/openpangu/openPangu-2.0-Pro",
            "https://huggingface.co/openpangu"],
      bi="D58 遗留。本人 HF 组织页复验 openPangu-2.0-Pro createdAt 2026-07-30（另有 -Int8 同日）。⚠ 库内 Huawei 5 条是 pangu-5.0 / pangu-ultra / pangu-pro-moe / metamath×2；**pangu-5.0（2024-06-21 闭源行业线）≠ openPangu（开源子品牌）**，前缀沿用库内 huawei。系列发布 2026-06-12 HDC，本行 release_date 取 HF 组织页标注的 07-31（T0 台账口径）。⚠ 华为云 MaaS 11-06 停售、11-30 下线，影响 api/access 字段判定。",
      access="权重上架 HF / ModelScope / GitCode、OPENPANGU MODEL LICENSE 2.0 ⇒ open_weights=true / local_deployment=true。⚠ 华为云 MaaS 本轮 11-06 停售、11-30 下线，自营 API 可用性正在变化，无可稳定引用的一手刊例价 ⇒ api 置 null（不肯定也不否定）。",
      arch="HF 模型卡：505B 总 / 18B 激活、512K ctx、~34T tokens、MLA + DSA + SWA(1:2)、4 流 mHC、3 头 MTP、Muon ⇒ architecture_type=MoE；官方未给主干结构枚举内的一手表述，backbone_type 置 Unknown。knowledge_cutoff / max_output_tokens / reasoning_model 官方未列，置 null。",
      pricing="⛔ HF 模型卡未列定价，厂商自营 API 刊例价未取到一手证据，且华为云 MaaS 正停售下线 ⇒ 六个价键与 currency 全置 null。source_type 记核对动作，confidence=T0。",
      mi_note="HF 模型卡为文本大模型，仅 text=true；其余官方未提，留 null。",
      mo_note="仅文本输出有依据。",
      nm_note=COMMON_NM_NOTE,
      meta="裁定：独立模型，立行。★ 与 openPangu-2.0-Flash **分立两行**：两者有各自独立的 HF 仓库、独立参数量（505B-A18B vs 92B-A6B）与独立 createdAt，符合 S1「独立测量身份」口径，不合并成一条 openPangu-2.0。⛔ -Int8 量化仓按 D35 口径并入本行不立行。待复核：华为云 MaaS 下线后 api 字段、知识截止日。"),

    F("huawei:openpangu-2.0-flash:base", "openPangu-2.0-Flash", "2.0-Flash", "Huawei",
      "2026-06-30", ["轻量", "推理增强"],
      "OPENPANGU MODEL LICENSE 2.0（代码 Apache-2.0）",
      True, None, True,
      tp=92.0, ap=6.0, atype="MoE", ctx=524288,
      purl="https://huggingface.co/openpangu/openPangu-2.0-Flash",
      ptype="开源权重模型核对（无官方 API 价）", pconf="T0",
      mi={"text": True},
      mo={"text": True},
      urls=["https://huggingface.co/openpangu/openPangu-2.0-Flash",
            "https://huggingface.co/openpangu"],
      bi="D58 遗留。本人 HF 组织页复验 openPangu-2.0-Flash createdAt 2026-06-30（-Int8 同日）。92B 总 / 6B 激活、512K ctx，许可同 Pro。⚠ 与 Pro 是否合为一条「openPangu-2.0」曾列为 S1 待判，本轮按独立测量身份口径**分立两行**（见 meta.notes）。",
      access="权重上架 HF / ModelScope / GitCode、OPENPANGU MODEL LICENSE 2.0 ⇒ open_weights=true / local_deployment=true；华为云 MaaS 停售中，api 置 null。",
      arch="HF 模型卡：92B 总 / 6B 激活、512K ctx ⇒ architecture_type=MoE；官方未给主干结构一手表述，backbone_type 置 Unknown。knowledge_cutoff / max_output_tokens / reasoning_model 官方未列，置 null。",
      pricing="⛔ 同 Pro：无厂商自营 API 刊例价一手证据 ⇒ 六个价键与 currency 全置 null。source_type 记核对动作，confidence=T0。",
      mi_note="HF 模型卡为文本大模型，仅 text=true。",
      mo_note="仅文本输出有依据。",
      nm_note=COMMON_NM_NOTE,
      meta="裁定：独立模型，立行（与 Pro 分立）。理由：独立 HF 仓库、独立参数量档位（92B-A6B vs 505B-A18B）、独立 createdAt（06-30 vs 07-30）、独立 model card ⇒ 不是同一模型的服务档或量化变体，符合「full_name 可区分 + 独立测量身份」保底判据。⛔ -Int8 量化仓按 D35 不立行。待复核：华为云 MaaS 下线后 api 字段。"),

    F("meituan:longcat-2.0:base", "LongCat-2.0", "2.0", "Meituan", "2026-06-30",
      ["旗舰", "推理增强", "工具调用增强"], "MIT",
      True, True, True,
      tp=1600.0, ap=48.0, atype="MoE", ctx=1048576,
      pin=0.3, pout=1.2, pcached=0.006,
      purl="https://longcat.chat/platform/docs/zh/api-pay-as-you-go",
      ptype="官方定价页", pconf="T0",
      mi={"text": True},
      mo={"text": True},
      urls=["https://huggingface.co/meituan-longcat/LongCat-2.0",
            "https://longcat.chat/platform/docs/zh/api-pay-as-you-go",
            "https://openrouter.ai/meituan/longcat-2.0"],
      bi="D58 遗留 + D38 已查证但一直未采（**纯漏采**：OpenRouter 07-20 就上架，不属于任何近轮差集窗口，只有榜单全量反推能照出）。本人 HF 组织页复验 createdAt 2026-07-05、downloads 3024、仍在架未下架。⛔ 四个日期口径按铁律分档：**release_date 取 2026-06-30（新华网正式发布，T0）**；HF 建仓 07-05、官方开源公告 07-12（tech.meituan.com）、OpenRouter 上架 07-20 都不是发布日。",
      access="HF 官方组织仓 MIT 许可、权重在架 ⇒ open_weights=true / local_deployment=true；longcat.chat 官方按量付费页把 LongCat-2.0 列入计费模型清单 ⇒ api=true。",
      arch="1.6T 总 / 48B 激活 MoE、原生 1M ctx、>35T tokens、AI ASIC superpods、LongCat Sparse Attention、135B N-gram Embedding（HF 模型卡 / 官方开源公告）。⛔ D38 记录的「ScMoE + 零计算专家」措辞本轮在现卡**无法证实**，按红线不照抄旧结论，故 architecture.notes 只保留本轮可复验项。backbone_type 官方未给枚举内一手表述，置 Unknown；knowledge_cutoff / max_output_tokens / reasoning_model 置 null。⚠ OpenRouter 写 context_length=1048756（疑为 1048576 笔误），本行取官方 1,048,576 并留痕。",
      pricing="官方 longcat.chat 按量付费页对 LongCat-2.5-Preview 与 LongCat-2.0 统一列出 $0.30 / $1.20 每百万 token（缓存命中 $0.006），与库内 longcat-2.5-preview:base 的 T0 定价同源；OpenRouter 挂牌同为 $0.30/$1.20，可作交叉印证。故本行采用官方价，confidence=T0。cache_write / batch_input / batch_output 官方页未单列，置 null。",
      mi_note="OR 描述为 sparse MoE **language model**，仅文本输入有依据；其余官方未提，留 null。",
      mo_note="仅文本输出有依据。",
      nm_note=COMMON_NM_NOTE,
      meta="裁定：独立模型，立行。★ 本条是「榜单全量反推必做」的又一个实证：D38 就查证过存在，却因后续几轮 S0 退回纯差集式，一路挂到 D59 才入库（与 D52 的 glm-5.3-max 同类）。⛔ 未沿用 D38 旧结论中本轮无法复现的架构措辞；⛔ LongCat-2.0-FP8 / -INT8 量化变体按 D35 口径不立行。待复核：知识截止日、最大输出 token 数。"),

    F("moondream:moondream-3.1:base", "Moondream 3.1", "3.1", "Moondream", "2026-07-07",
      ["轻量", "多模态"], "moondream-model-license-1.0",
      True, None, True,
      tp=9.0, ap=2.0, atype="MoE", ctx=32000,
      purl="https://moondream.ai/blog/moondream-3-1-beyond-benchmarks",
      ptype="开源权重模型核对（无官方 API 价）", pconf="T0",
      mi={"text": True, "image": True},
      mo={"text": True},
      urls=["https://moondream.ai/blog/moondream-3-1-beyond-benchmarks",
            "https://openrouter.ai/moondream/moondream3.1-9b-a2b"],
      bi="D57 观察清单遗留，库内实测 0 条（**新厂商前缀 moondream**）。★ 日期本轮修正为 **2026-07-07**（原以为 10 月，OpenRouter 10-15 只是上架日）⇒ 属 7 月缺口而非本轮窗口，靠榜单全量反推才捞到。9B 总 / 2B 激活 MoE VLM，新许可 moondream-model-license-1.0。",
      access="官方博客宣布开放权重与新许可 ⇒ open_weights=true / local_deployment=true；未取到厂商自营 API 刊例价一手证据，api 置 null（OpenRouter 有第三方托管，不作为 api 判定依据）。",
      arch="官方博客 / OpenRouter 描述：9B 总 / 2B 激活 mixture-of-experts、视觉语言模型、ctx 32K ⇒ architecture_type=MoE；官方未给主干结构枚举内一手表述，backbone_type 置 Unknown。knowledge_cutoff / max_output_tokens / reasoning_model 官方未列，置 null。",
      pricing="⛔ OpenRouter 挂牌 $0.30/$2.50（每百万 token）属第三方转售价，厂商自营 API 刊例价未取到一手证据 ⇒ 六个价键与 currency 全置 null，数值仅在本栏留痕。source_type 记核对动作，confidence=T0。",
      mi_note="视觉语言模型（VQA / captioning / OCR / 视觉推理），text / image=true；其余官方未提，留 null。",
      mo_note="仅文本输出有依据（描述、caption、OCR 文本）。",
      nm_note=COMMON_NM_NOTE,
      meta="裁定：独立模型，立行（Moondream 3 Preview 的后继，OpenRouter 有独立条目 moondream/moondream3.1-9b-a2b）。★ 新厂商首条，前缀 moondream / vendor 显示名 Moondream。⚠ 日期修正留痕：D57 观察清单原按 10 月记录，本轮查证为 07-07 发布、10-15 上架，再次印证「OR created ≠ 发布日」。⛔ 前代 Moondream 3 Preview 未单独立行（与库内 0 条 Moondream 记录一致，本轮只采 3.1 GA）；若后续需要补前代，按独立条目另案处理。待复核：厂商自营 API 定价、知识截止日。"),
]


def main():
    assert len(FACTS) == 15, len(FACTS)
    OUT.mkdir(parents=True, exist_ok=True)
    written = []
    for rec in FACTS:
        mid = rec["model_id"]
        fname = BATCH + "__" + mid.replace(":", "__") + ".jsonl"
        path = OUT / fname
        path.write_text(json.dumps(rec, ensure_ascii=False, separators=(",", ":")),
                        encoding="utf-8")
        written.append("incoming/models/" + fname)

    led_lines = [l for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    kept = [l for l in led_lines if not (json.loads(l).get("batch_id") == BATCH)]
    entry = {
        "batch_id": BATCH, "vendor": "multi",
        "models": [r["model_id"] for r in FACTS],
        "status": "submitted", "claimed_by": "workbuddy-takeover-d59",
        "claimed_at": "2026-11-11T13:30:00+08:00", "wave": 1, "round": "D59",
        "notes": "接手 Qoder 会话 29afb6cb（06:32 报错 145 断在 S2 准备阶段）后补跑。S1 范围由用户两轮 AskUserQuestion 拍板：甲 7（Fable 5.2 / Mythos 5.2 / Hy4 GA / Muse Ember / Ripple-65B / ERNIE-5.5-Flash-Base / LongCat-2.5 GA）+ 乙 8（Gemini 4 Carbon / LFM3-1.7B / GLM-5.3-FlashX-Legal / Spark X2.6 / openPangu-2.0 Pro+Flash / LongCat-2.0 / Moondream 3.1）= 采 15 条；剔除 Particle-1 / Recursive Flint / PrismML Ternary Bonsai / Elorian Glimpse 与 LFM3 多模态兄弟仓。丙类 4 条字段更新已由 Qoder 落库（1028/ERROR 0/WARN 0，git diff 4 增 4 删），不在本批。★ Hy4 GA 与 LongCat-2.5 GA 按用户拍板「按官方是否同 checkpoint 逐个判」判定均为立独立行，依据写在各记录 meta.notes。S2 证据全部复用 S0 阶段本地化的一手材料（temp/d59/ 页面、OpenRouter 469 模型快照、HF API 回显），未联网重采；因证据已在手，本轮由接手会话集中生成而非逐模型派 subagent，产出仍按 S2 目录/命名/门禁口径。",
        "submitted_at": "2026-11-11T13:30:00+08:00",
        "submitted_files": written,
    }
    kept.append(json.dumps(entry, ensure_ascii=False))
    LEDGER.write_text("\n".join(kept) + "\n", encoding="utf-8")

    print("产物", len(written), "条 ->", OUT)
    for w in written:
        print("  ", w)
    print("台账", BATCH, "已登记；条目数", len(led_lines), "->", len(kept))


if __name__ == "__main__":
    main()
