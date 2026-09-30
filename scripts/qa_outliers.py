# -*- coding: utf-8 -*-
"""全库离群体检器（D34 `temp/d34_scan_outliers.py` 的 D46 重建、D52 扩容版）。

原脚本随 temp 清理失传（回收站/工作区/git 历史均无，2026-09-13 核实），D46 按
D34 CHANGELOG 留痕的检查口径 + `temp/d34_a_class_report.md` 的 A1-A8 方向重建为 **16 项**
（13 项注册检查 + r1/r2/v3 三项跨记录检查），并留了一条 D50 待办「扩容至 D34 原 31 项口径」。

**D52（2026-10-01）完成扩容：16 → 31 项**。新增 15 项，全部按 D34 遗留产物 `temp/d34_scan_a_class.py`
的原始判定实现与阈值还原（该脚本当时没进库、所幸未被清理，本轮**逐条抄口径**而非重新发明）：

| 新增 | 来源 | 口径 |
|---|---|---|
| a2 | D34 A2 | knowledge_cutoff 早于 release_date |
| a3 | D34 A3 | active/total 比例异常（<0.05 或 >0.95） |
| a4a | D34 A4 | input.image=true 但 output.image / native.output_image 未显式记录 |
| a4b | D34 A4 | input.pdf=true 而 input.image 非 true |
| a5 | D34 A5 | 定位「旗舰」但 input 价 < $1 |
| a6 | D34 A6 | 同厂商同代系指纹簇（family 去分隔符去变体后缀后相同却出现 >1 个 model_id / 写法） |
| a7 | D34 A7 | version 字段与 full_name 重复（冗余） |
| a8a/b/c | D34 A8 | license 商用受限 / 已填但未分类 / open_weights=true 却未填 |
| p1 | 新增 | 价格半填（input 与 output 只有一边） |
| p2 | 新增 | batch 价不低于标准价（batch 应更便宜） |
| b1 | 新增 | 同记录内 (sub_benchmark, date) 重复的 arena 条目 |
| b2 | 新增 | 跑分条目缺 confidence / source_url |
| n1 | 新增 | model_id variant 段为空或含非法字符 |

定位是**体检不是门禁**（门禁唯一权威仍是 validate_model_data.py）：
  - `硬错`：几乎必是数据错误（倒挂、缓存价>输入价、出域等）
  - `疑点`：需要人工看，历史上多为口径差或知情保留（D34 教训：13 条激活>总参
    系名义值/精确值精度差、160 条知识截止早于发布系正常语义，均不动）

用法：PYTHONUTF8=1 python scripts/qa_outliers.py [--out temp/d<轮>/outliers_report.txt]
"""
import argparse
import collections
import datetime
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.path.join(ROOT, 'model_data_v2.jsonl')
TODAY = datetime.date.today()


def load():
    rows = []
    for line in open(MAIN, encoding='utf-8'):
        if line.strip():
            rows.append(json.loads(line))
    return rows


def rd_of(r):
    return (r.get('basic_info') or {}).get('release_date')


def arch_of(r):
    return r.get('architecture') or {}


def notes_of(r):
    return ' '.join([(r.get('basic_info') or {}).get('notes') or '',
                     arch_of(r).get('notes') or '',
                     (r.get('meta') or {}).get('notes') or ''])


# ---- D52 扩容：常量表与辅助（逐条抄自 temp/d34_scan_a_class.py，见模块 docstring）----
VARIANT_SUFFIXES = ['instruct', 'conversational', 'dialogue', 'chat',
                    'base', 'sft', 'dpo', 'rlhf', 'awq', 'gptq',
                    'gguf', 'fp16', 'bf16', 'int4', 'int8']

RESTRICTED_PATTERNS = [
    ('AGPL', 'AGPL - 网络传染性，商用受限'),
    ('GPL', 'GPL - 传染性 copyleft，商用受限'),
    ('CC-BY-NC', 'CC-BY-NC - 非商用'),
    ('CC-BY-SA', 'CC-BY-SA - 相同方式共享（SA 限制）'),
    ('CC-BY-ND', 'CC-BY-ND - 禁止演绎'),
    ('Non-Commercial', '声明非商用'),
    ('NonCommercial', '声明非商用'),
    ('NC ', '可能含非商用条款'),   # ⚠ 本项由 chk_a8a 特殊处理为 \bNC\b（区分大小写），见该函数 docstring
    ('Research', '仅研究用'),
    ('research-only', '仅研究用'),
    ('非商用', '声明非商用'),
    ('仅研究', '仅研究用'),
]
OPEN_HINTS = ['apache', 'mit', 'bsd', 'llama', 'open', 'apache-2']

_VARIANT_OK = re.compile(r'^[A-Za-z0-9._\-+]+$')

# 「NC」独立词（区分大小写 + 词边界）——避免匹配到域名/公司名里的 "inc "（见 chk_a8a）
_NC_WORD = re.compile(r'\bNC\b')

# ---- 非生成式模型（嵌入 / 重排 / 稀疏检索）识别 ----
# 这类模型只按输入 token 计费、**本无输出 token 价**，凡涉及「output 价」的判据（如 p1 半填）
# 一律不适用。D52 实测：初版只匹配族名含 `embed`，漏掉了 Voyage AI 全家（族名是 voyage-3.5 等，
# 不含 embed 字样）⇒ 4 条 embedding 被误报为「价格半填」。故判据扩为「正则覆盖族名/vendor」。
NON_GEN_RE = re.compile(
    r'embed|rerank|colbert|splade|bge|gte-|e5-|voyage|jina-emb', re.I)


def is_non_generative(r):
    """嵌入 / 重排 / 检索类模型（无文本生成输出）→ True。

    用族名 + vendor 双路匹配（`capabilities` 字段在本库多为 null，不可依赖）。
    """
    bi = r.get('basic_info') or {}
    fam = family_of(r) or ''
    vdr = bi.get('vendor') or ''
    mid = r.get('model_id') or ''
    return bool(NON_GEN_RE.search(fam) or NON_GEN_RE.search(vdr) or NON_GEN_RE.search(mid))


def parse_date(s):
    """宽松解析 YYYY[-MM[-DD]] → datetime.date，失败返回 None。"""
    if not isinstance(s, str):
        return None
    m = re.match(r'^(\d{4})(?:-(\d{1,2}))?(?:-(\d{1,2}))?', s.strip())
    if not m:
        return None
    y, mo, d = int(m.group(1)), int(m.group(2) or 1), int(m.group(3) or 1)
    try:
        return datetime.date(y, mo, d)
    except ValueError:
        return None


def family_of(r):
    mid = r.get('model_id') or ''
    parts = mid.split(':')
    return parts[1] if len(parts) > 1 else ''


def variant_of(r):
    mid = r.get('model_id') or ''
    parts = mid.split(':')
    return parts[2] if len(parts) > 2 else ''


def fingerprint_family(family):
    """归一 family：去分隔符 + 去变体后缀（D34 A6 原实现）。"""
    if not family:
        return ''
    s = re.sub(r'[-_.\s]+', '', family.lower())
    for suf in sorted(VARIANT_SUFFIXES, key=len, reverse=True):
        s = s.replace(suf, '')
    return s


# ---- 检查项注册表：id -> (族, 级别, 描述, 判定函数(r) -> 详情str/None) ----
def chk_o1(r):
    rd = rd_of(r)
    if not rd:
        return 'release_date 缺失'
    if not re.match(r'^\d{4}(-\d{2}){0,2}$', rd or ''):
        return f'格式非法 {rd}'
    try:
        parts = [int(x) for x in rd.split('-')]
        if len(parts) == 1:
            return None
        d = datetime.date(parts[0], parts[1], parts[2] if len(parts) > 2 else 1)
    except ValueError:
        return f'非法日期 {rd}'
    if d > TODAY + datetime.timedelta(days=1):
        return f'未来日期 {rd}'
    if d < datetime.date(2022, 1, 1):
        return f'早于 2022 边界 {rd}'
    return None


def chk_o2(r):
    tp = arch_of(r).get('total_params_b')
    if tp is not None and not (0.05 <= tp <= 100000):
        return f'total_params_b={tp}'
    return None


def chk_o3(r):
    a = arch_of(r)
    tp, ap = a.get('total_params_b'), a.get('active_params_b')
    if tp is not None and ap is not None and ap > tp + 1e-9:
        tag = '硬错' if not re.search(r'名义|精度|approx|nominal', notes_of(r), re.I) else '疑点(有精度注)'
        return f'active({ap}) > total({tp}) [{tag}]'
    return None


def chk_o4(r):
    ctx = arch_of(r).get('context_window_tokens')
    # 上界 10.5M：Llama-4-Scout 官方口径即 10M；下界 256：T5 系编码-解码真实窗口可低至 512
    if ctx is not None and not (256 <= ctx <= 10_500_000):
        return f'context_window_tokens={ctx}'
    return None


def chk_o5(r):
    for b in (r.get('benchmarks') or {}).get('self_reported') or []:
        s = b.get('score')
        if isinstance(s, (int, float)) and not (0 <= s <= 1):
            return f'self_reported {b.get("benchmark")} score={s}'
    return None


def chk_o6(r):
    for b in (r.get('benchmarks') or {}).get('arena_elo') or []:
        s = b.get('score')
        if isinstance(s, (int, float)) and not (0 <= s <= 3000):
            return f'{b.get("sub_benchmark") or b.get("benchmark")} elo={s}'
    return None


def _price_num(v):
    return v if isinstance(v, (int, float)) else None


def chk_c1(r):
    p = r.get('pricing') or {}
    ci, inp = _price_num(p.get('cached_input')), _price_num(p.get('input'))
    if ci is not None and inp is not None and inp > 0 and ci > inp:
        return f'cached_input({ci}) > input({inp})——缓存命中价高于输入价不可能'
    return None


def chk_c2(r):
    p = r.get('pricing') or {}
    ci, inp = _price_num(p.get('cached_input')), _price_num(p.get('input'))
    if ci is not None and inp is not None and inp > 0 and not (0.005 <= ci / inp <= 1.0):
        return f'cached/input 比值异常 {ci / inp:.2f}（全库常见 0.03~0.5）'
    return None


def chk_c3(r):
    kc = arch_of(r).get('knowledge_cutoff')
    if kc:
        try:
            y, m = int(kc[:4]), int(kc[5:7])
            if datetime.date(y, m, 1) > TODAY + datetime.timedelta(days=60):
                return f'knowledge_cutoff 超前今天 {kc}'
        except (ValueError, IndexError):
            return f'knowledge_cutoff 格式 {kc}'
    return None


def chk_c4(r):
    mi = ((r.get('modality') or {}).get('input') or {})
    mo = ((r.get('modality') or {}).get('output') or {})
    if mi.get('image') is True and mo.get('text') is not True:
        return f'图像输入模型 output.text={mo.get("text")}'
    return None


def chk_c5(r):
    pos = ' '.join((r.get('basic_info') or {}).get('positioning') or [])
    tp = arch_of(r).get('total_params_b')
    if '旗舰' in pos and tp is not None and tp < 10:
        return f'定位旗舰但 total={tp}B'
    if any(k in pos for k in ('轻量', '端侧')) and tp is not None and tp > 100:
        return f'定位轻量/端侧但 total={tp}B'
    return None


def chk_c6(r):
    lic = (r.get('basic_info') or {}).get('license')
    if lic is not None and not isinstance(lic, str):
        return f'license 形状非字符串（D34 事故形状）：{type(lic).__name__}'
    return None


def chk_v1(r):
    """model_id 前缀 vs basic_info.vendor 脱钩（A7 方向，宽匹配仅报硬脱钩）。"""
    mid = r.get('model_id') or ''
    vendor = (r.get('basic_info') or {}).get('vendor') or ''
    if ':' not in mid or not vendor:
        return None
    pref = mid.split(':')[0].replace('-', '').lower()
    v = re.sub(r'[^a-z0-9]', '', vendor.lower())
    # 前缀是 vendor 的子串或反之视为关联（google/googledeepmind），否则报
    if pref and v and pref not in v and v not in pref:
        # 已知历史例外（D41 归并产生）：ant→alibaba 等
        KNOWN = {('inclusionai', 'antgroup'), ('alibaba', 'antgroup'),
                 ('qihoo360', 'qihoo'), ('meituan', 'meituantechnologies')}
        if (pref, v) in KNOWN:
            return None
        return f'前缀 {mid.split(":")[0]} vs vendor {vendor}'
    return None


# ==================== D52 新增 14 项（每记录）====================
def chk_a2(r):
    rd, kc = parse_date(rd_of(r)), parse_date(arch_of(r).get('knowledge_cutoff'))
    if rd and kc and kc < rd:
        return f'knowledge_cutoff({arch_of(r).get("knowledge_cutoff")}) 早于 release_date({rd_of(r)})'
    return None


def chk_a3(r):
    tp, ap = arch_of(r).get('total_params_b'), arch_of(r).get('active_params_b')
    if tp and ap and ap <= tp:
        ratio = ap / tp
        if ratio < 0.05 or ratio > 0.95:
            return f'active/total 比例异常 {ratio:.4f}（total={tp} active={ap}）'
    return None


def chk_a4a(r):
    mod = r.get('modality') or {}
    if (mod.get('input') or {}).get('image') is True:
        oi = (mod.get('output') or {}).get('image')
        noi = (mod.get('native_multimodal') or {}).get('output_image')
        if oi is None or noi is None:
            return f'视觉输入模型但 output.image={oi} / native.output_image={noi} 未显式记录'
    return None


def chk_a4b(r):
    """input.pdf=true 而 input.image 非 true。

    D52 实测校准：初版按「硬错」分级，跑出 3 条，人工核后**不是「几乎必错」**：
      * deepl:deepl-llm —— modality.input.notes 原文写明「input.pdf=true 指 DeepL 文档翻译
        **产品**支持 PDF/docx/pptx 输入」，即 pdf 标记的是产品能力而非模型视觉能力 ⇒ 口径问题
      * mistral:mistral-large-3 / mistral-large:2411 —— 来源数据未含多模态信息、属采集缺口
    两条都属「口径 / 缺口」而非不可能值，故降为「疑点」（保留检出，不静默丢弃）。
    """
    inp = (r.get('modality') or {}).get('input') or {}
    if inp.get('pdf') is True and inp.get('image') is not True:
        return f'input.pdf=true 但 input.image={inp.get("image")}'
    return None


def chk_a5(r):
    pos = ' '.join((r.get('basic_info') or {}).get('positioning') or [])
    p = r.get('pricing') or {}
    cur = p.get('currency')
    inp = _price_num(p.get('input'))
    if '旗舰' in pos and inp is not None and inp < 1.0 and cur in ('USD', None):
        return f'定位旗舰但 input=${inp}（< $1）'
    return None


def chk_a7(r):
    v = (r.get('basic_info') or {}).get('version')
    fn_ = (r.get('basic_info') or {}).get('full_name') or ''
    if v is not None and str(v).strip() and str(v).strip().lower() in fn_.lower():
        return f'version={v!r} 与 full_name={fn_!r} 冗余重复'
    return None


def chk_a8a(r):
    """license 商用受限（AGPL/GPL/CC-BY-NC 等）。

    D52 修复（判据缺陷）：原实现对全部模式做 `pat.lower() in lic.lower()`，
    其中 `'NC '` 会**误命中域名里的 "inc "**（实测：`… sales@perceptron.inc 获取商业许可` 被判「可能含非商用条款」）。
    现对 `'NC '` 改用**区分大小写的词边界正则** `\\bNC\\b`，其余模式保持原子串匹配。
    实测影响面：全库当前**无任何记录**仅靠 `"nc "` 命中该项（0 条），故本修复为纯消误报、不动基线。
    """
    lic = (r.get('basic_info') or {}).get('license')
    if isinstance(lic, str) and lic.strip():
        for pat, desc in RESTRICTED_PATTERNS:
            hit = bool(_NC_WORD.search(lic)) if pat == 'NC ' else (pat.lower() in lic.lower())
            if hit:
                return f'license={lic!r} —— {desc}'
    return None


def chk_a8b(r):
    lic = (r.get('basic_info') or {}).get('license')
    if isinstance(lic, str) and lic.strip():
        if not any(pat.lower() in lic.lower() for pat in RESTRICTED_PATTERNS_MIN) \
                and not any(k in lic.lower() for k in OPEN_HINTS):
            return f'license={lic!r} 未分类（非开源友好亦非已登记受限）'
    return None


def chk_a8c(r):
    acc = (r.get('basic_info') or {}).get('access') or {}
    lic = (r.get('basic_info') or {}).get('license')
    if acc.get('open_weights') is True and not (isinstance(lic, str) and lic.strip()):
        return 'open_weights=true 但 license 未填'
    return None


def chk_p1(r):
    """价格半填。

    D52 实测校准：初版按「硬错」分级，跑出来 16 条里 **11 条是 embedding 类**
    （voyage-* / *-embedding / gigaembeddings / codestral-embed / text-embedding-3-*），
    而嵌入模型**只按输入 token 计费、本就没有输出 token 价**（官方定价页原文即「按输入 token 计费」）
    ⇒ 那不是缺陷、是行业事实，判据本身设计有误。已改为：跳过非生成式模型（`is_non_generative`）
    + 降为「疑点」。剩余命中为真实的价格覆盖缺口（输出价官方未单列 / 文本破损），
    属完整性缺口而非不可能值。
    """
    if is_non_generative(r):
        return None
    p = r.get('pricing') or {}
    i, o = _price_num(p.get('input')), _price_num(p.get('output'))
    if (i is None) != (o is None):
        return f'价格半填：input={i} / output={o}'
    return None


def chk_p2(r):
    """batch 价**严格**高于标准价。

    D52 实测校准：初版用 `>=`，跑出 3 条，其中 bytedance:doubao-function-call-model 是
    `batch == 标准价` 且 pricing.notes 已写明官方口径（「doubao-pro-32k 在批量推理表中标价与在线
    推理相同，未享 50% 折扣」，T0 官方定价页）⇒ 相等是**官方事实、有注证**，不是错误。
    故改判据为严格 `>`，只报「批量比标准还贵」这种不可能的内部矛盾。
    """
    p = r.get('pricing') or {}
    i, o = _price_num(p.get('input')), _price_num(p.get('output'))
    bi, bo = _price_num(p.get('batch_input')), _price_num(p.get('batch_output'))
    bad = []
    if i is not None and bi is not None and bi > i:
        bad.append(f'batch_input({bi}) > input({i})')
    if o is not None and bo is not None and bo > o:
        bad.append(f'batch_output({bo}) > output({o})')
    return '；'.join(bad) if bad else None


def chk_b1(r):
    seen = collections.Counter()
    for b in (r.get('benchmarks') or {}).get('arena_elo') or []:
        seen[(b.get('sub_benchmark'), str(b.get('date')))] += 1
    dup = [f'{k[0]}/{k[1]}×{v}' for k, v in seen.items() if v > 1]
    return '同 (sub_benchmark,date) 重复：' + '、'.join(dup) if dup else None


def chk_b2(r):
    miss = []
    for seg in ('self_reported', 'independent'):
        for b in (r.get('benchmarks') or {}).get(seg) or []:
            for k in ('confidence', 'source_url'):
                if not b.get(k):
                    miss.append(f'{seg}:{b.get("benchmark")} 缺 {k}')
    return '；'.join(miss[:3]) + (f'（共 {len(miss)} 处）' if len(miss) > 3 else '') if miss else None


def chk_n1(r):
    v = variant_of(r)
    if not v:
        return f'model_id 缺 variant 段：{r.get("model_id")}'
    if not _VARIANT_OK.match(v):
        return f'variant 段含非法字符：{v!r}'
    return None


RESTRICTED_PATTERNS_MIN = [p for p, _ in RESTRICTED_PATTERNS]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='')
    args = ap.parse_args()

    CHECKS = [
        ('o1', '离群', '硬错', 'release_date 缺失/非法/未来/<2022', chk_o1),
        ('o2', '离群', '硬错', 'total_params_b 出合理界', chk_o2),
        ('o3', '矛盾', '分级', 'active > total 倒挂', chk_o3),
        ('o4', '离群', '硬错', 'context_window_tokens 出合理界', chk_o4),
        ('o5', '离群', '硬错', 'self_reported score 出 0-1', chk_o5),
        ('o6', '离群', '硬错', 'arena_elo 出合理界', chk_o6),
        ('c1', '矛盾', '硬错', 'cached_input > input', chk_c1),
        ('c2', '矛盾', '疑点', 'cached/input 比值出常见带', chk_c2),
        ('c3', '矛盾', '硬错', 'knowledge_cutoff 超前今天', chk_c3),
        ('c4', '矛盾', '硬错', '图像输入模型无文本输出', chk_c4),
        ('c5', '矛盾', '疑点', '定位与参数量级不匹配', chk_c5),
        ('c6', '矛盾', '硬错', 'license 形状（D34 事故）', chk_c6),
        ('v1', '命名', '疑点', 'model_id 前缀与 vendor 硬脱钩', chk_v1),
        # ---- D52 扩容（15 项，来源见模块 docstring；a6 为跨记录检查，在下方单独处理）----
        ('a2', '矛盾', '疑点', 'knowledge_cutoff 早于 release_date（D34 A2）', chk_a2),
        ('a3', '离群', '疑点', 'active/total 比例异常 <0.05 或 >0.95（D34 A3）', chk_a3),
        ('a4a', '矛盾', '疑点', '视觉输入模型 output_image 能力未显式记录（D34 A4）', chk_a4a),
        ('a4b', '矛盾', '疑点', 'input.pdf=true 而 input.image 非 true（D34 A4）', chk_a4b),
        ('a5', '矛盾', '疑点', '定位旗舰但 input 价 < $1（D34 A5）', chk_a5),
        ('a7', '命名', '疑点', 'version 字段与 full_name 冗余重复（D34 A7）', chk_a7),
        ('a8a', '合规', '疑点', 'license 商用受限（GPL/AGPL/CC-BY-NC 等，D34 A8）', chk_a8a),
        ('a8b', '合规', '疑点', 'license 已填但未分类（D34 A8）', chk_a8b),
        ('a8c', '合规', '疑点', 'open_weights=true 但 license 未填（D34 A8）', chk_a8c),
        ('p1', '矛盾', '疑点', '价格半填（input/output 只有一边）', chk_p1),
        ('p2', '矛盾', '疑点', 'batch 价不低于标准价', chk_p2),
        ('b1', '重复', '疑点', '同记录内 (sub_benchmark,date) 重复 arena 条目', chk_b1),
        ('b2', '覆盖', '疑点', '跑分条目缺 confidence / source_url', chk_b2),
        ('n1', '命名', '疑点', 'model_id variant 段缺失或含非法字符', chk_n1),
    ]
    rows = load()
    lines = [f'# 全库离群体检（qa_outliers.py · D52 扩容至 31 项）',
             f'> 基准：{MAIN.replace(chr(92), "/")} | 记录 {len(rows)} | 运行日 {TODAY}',
             '> 定位：体检不是门禁；`硬错`=几乎必错，`疑点`=人工判（D34 教训：多为口径差/知情保留）', '']
    findings = {}
    for cid, fam, level, desc, fn in CHECKS:
        hits = []
        for r in rows:
            try:
                d = fn(r)
            except Exception as e:
                d = f'检查器异常 {e}'
            if d:
                hits.append((r.get('model_id'), d))
        findings[cid] = hits
        lines.append(f"## {cid} {desc}（{fam}/{level}）—— {len(hits)} 条")
        for mid, d in hits[:15]:
            lines.append(f'- {mid}: {d}')
        if len(hits) > 15:
            lines.append(f'- ...（共 {len(hits)} 条）')
        lines.append('')

    # 重复族（跨记录，单独处理）
    by_vf = collections.defaultdict(list)
    for r in rows:
        bi = r.get('basic_info') or {}
        fn_ = (bi.get('full_name') or '').strip().lower()
        if fn_:
            by_vf[(bi.get('vendor'), fn_)].append(r.get('model_id'))
    dup = {k: v for k, v in by_vf.items() if len(v) > 1}
    findings['r1'] = dup
    lines.append(f'## r1 同厂商同 full_name 多 model_id（重复）—— {len(dup)} 组')
    for (v, f_), ids in list(dup.items())[:15]:
        lines.append(f'- {v} | {f_}: {" / ".join(ids)}')
    if len(dup) > 15:
        lines.append(f'- ...（共 {len(dup)} 组）')
    lines.append('')

    casecluster = collections.defaultdict(set)
    for r in rows:
        for seg in ('self_reported', 'independent'):
            for b in (r.get('benchmarks') or {}).get(seg) or []:
                n = b.get('benchmark')
                if isinstance(n, str) and n:
                    casecluster[n.casefold()].add(n)
    badcase = {k: v for k, v in casecluster.items() if len(v) > 1}
    findings['r2'] = badcase
    lines.append(f'## r2 基准名仅大小写异写（重复）—— {len(badcase)} 簇')
    for k, v in badcase.items():
        lines.append(f'- {" | ".join(sorted(v))}')
    lines.append('')

    # a6 同厂商同代系指纹簇（D34 A6 原实现：family 去分隔符 + 去变体后缀后成指纹）
    fp_groups = collections.defaultdict(list)
    for r in rows:
        bi = r.get('basic_info') or {}
        fp = fingerprint_family(family_of(r))
        if fp:
            fp_groups[(bi.get('vendor'), fp)].append((r.get('model_id'), family_of(r)))
    a6 = {}
    for (v, fp), members in fp_groups.items():
        ids_ = {m[0] for m in members}
        fams_ = {m[1] for m in members}
        if len(ids_) > 1 or len(fams_) > 1:
            a6[(v, fp)] = sorted(ids_)
    findings['a6'] = a6
    lines.append(f'## a6 同厂商同代系指纹簇（family 命名漂移/疑似重复，D34 A6）—— {len(a6)} 簇')
    for (v, fp), ids_ in list(a6.items())[:15]:
        lines.append(f'- vendor={v} 指纹={fp}（{len(ids_)} 条）: {" / ".join(ids_[:6])}'
                     + (' …' if len(ids_) > 6 else ''))
    if len(a6) > 15:
        lines.append(f'- ...（共 {len(a6)} 簇）')
    lines.append('')

    # 覆盖率
    total = len(rows)

    def filled(fn_):
        return sum(1 for r in rows if fn_(r))
    cov = [
        ('basic_info.release_date', lambda r: rd_of(r)),
        ('architecture.total_params_b', lambda r: arch_of(r).get('total_params_b')),
        ('architecture.active_params_b', lambda r: arch_of(r).get('active_params_b')),
        ('architecture.context_window_tokens', lambda r: arch_of(r).get('context_window_tokens')),
        ('basic_info.license', lambda r: (r.get('basic_info') or {}).get('license')),
        ('pricing.input', lambda r: _price_num((r.get('pricing') or {}).get('input'))),
    ]
    lines.append(f'## v3 关键字段填充率（覆盖率）')
    for name, fn_ in cov:
        n = filled(fn_)
        lines.append(f'- {name}: {n}/{total} ({n * 100 // total}%)')
    lines.append('')

    summary = ' | '.join(f'{cid}={len(findings.get(cid) or [])}' for cid, *_ in CHECKS)
    n_defect = len(CHECKS) + 3   # + r1 / r2 / a6 三项跨记录
    lines.append(f'---{chr(10)}汇总：{summary} | r1={len(dup)} | r2={len(badcase)} | a6={len(a6)}')
    lines.append(f'检查项：{len(CHECKS)} 项注册 + r1/r2/a6 三项跨记录 = {n_defect} 项缺陷检查，'
                 f'加 v3 覆盖率 ⇒ 共 {n_defect + 1} 项（D34 原口径 31 项）')
    out = '\n'.join(lines)
    print(out)
    if args.out:
        path = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(out + '\n')
        print(f'\n报告 -> {path}')


if __name__ == '__main__':
    main()
