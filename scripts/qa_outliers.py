# -*- coding: utf-8 -*-
"""全库离群体检器（D34 `temp/d34_scan_outliers.py` 的 D46 重建版）。

原脚本随 temp 清理失传（回收站/工作区/git 历史均无，2026-09-13 核实），本版按
D34 CHANGELOG 留痕的检查口径 + `temp/d34_a_class_report.md` 的 A1-A8 方向重建，
检查项注册表见 CHECKS，分四族：离群(o) / 矛盾(c) / 重复(r) / 覆盖与命名(v)。
定位是**体检不是门禁**（门禁唯一权威仍是 validate_model_data.py）：
  - `硬错`：几乎必是数据错误（倒挂、缓存价>输入价、出域等）
  - `疑点`：需要人工看，历史上多为口径差或知情保留（D34 教训：13 条激活>总参
    系名义值/精确值精度差、160 条知识截止早于发布系正常语义，均不动）

用法：PYTHONUTF8=1 python scripts/qa_outliers.py [--out temp/d46_outliers_report.txt]
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
    ]
    rows = load()
    lines = [f'# 全库离群体检（D46 重建版 qa_outliers.py）',
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
    lines.append(f'---{chr(10)}汇总：{summary} | r1={len(dup)} | r2={len(badcase)}')
    out = '\n'.join(lines)
    print(out)
    if args.out:
        path = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(out + '\n')
        print(f'\n报告 -> {path}')


if __name__ == '__main__':
    main()
