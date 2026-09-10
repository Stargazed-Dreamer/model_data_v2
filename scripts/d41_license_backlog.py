# -*- coding: utf-8 -*-
"""D41 第 5 项：license 空白留档。生成 docs/LICENSE_GAP_BACKLOG.md。"""
import json
import re
import collections

SRC = 'model_data_v2.jsonl'
OUT = 'docs/LICENSE_GAP_BACKLOG.md'

HF_RE = re.compile(r'https?://huggingface\.co/([A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*)')
# 非模型仓库的 HF 路径前缀（api/models/... 、papers/2308.xxx 等是误抽）
HF_BAD_OWNER = {'api', 'papers', 'datasets', 'spaces', 'blog', 'docs', 'collections', 'organizations'}
HF_BAD_REPO = {'models', 'datasets', 'spaces'}


def hf_repos(items):
    out = []
    for it in items:
        for m in HF_RE.finditer(str(it)):
            owner, repo = m.group(1).split('/', 1)
            if owner.lower() in HF_BAD_OWNER or repo.lower() in HF_BAD_REPO:
                continue
            if m.group(1) not in out:
                out.append(m.group(1))
    return out


def main():
    ow_true, ow_none = [], []
    n_closed_blank = 0
    for line in open(SRC, encoding='utf-8'):
        if not line.strip():
            continue
        r = json.loads(line)
        b = r['basic_info']
        if b.get('license'):
            continue
        ow = b.get('access', {}).get('open_weights')
        if ow is False:
            n_closed_blank += 1
            continue
        urls = r['meta'].get('source_urls') or []
        repos = hf_repos(urls + [b.get('access', {}).get('notes') or '', (b.get('notes') or '')])
        row = (r['model_id'], str(b.get('vendor') or ''), ow, repos, len(urls),
               r['meta'].get('verification_status') or '')
        if ow is True:
            ow_true.append(row)
        elif ow is None:
            ow_none.append(row)

    L = []
    L.append('# license 空白留档（D41 第 5 项，用户裁定「留档后续再做」）')
    L.append('')
    L.append('> 生成时间：2026-09-10（D41）｜数据源：`model_data_v2.jsonl`（937 条）')
    L.append('> 触发：D40 报告 §七.5「license 仍有 46 条空白」，用户 D41 裁定 **留档后续再做**，本轮不补。')
    L.append('')
    L.append('## 一、口径说明')
    L.append('')
    L.append('「license 空白」**不是**指全库 412 条 `basic_info.license` 为空的记录——其中绝大多数是'
             '闭源商业模型（`access.open_weights=false`），本就没有开源许可证可言。')
    L.append('有采集意义的缺口只有两类：')
    L.append('')
    L.append('| 类别 | 条数 | 含义 |')
    L.append('|---|---|---|')
    L.append(f'| **A 类：`open_weights=true` 但 license 空** | **{len(ow_true)}** | 开放权重模型却查不到许可证，属真实缺口 |')
    L.append(f'| B 类：`open_weights=null` 且 license 空 | {len(ow_none)} | 是否开源本身未确认，先确认开源再谈许可证 |')
    L.append(f'| （参考）`open_weights=false` 且 license 空 | {n_closed_blank} | 闭源，无采集意义 |')
    L.append('')
    L.append('## 二、A 类：开放权重但 license 空白（46 条，本轮留档）')
    L.append('')
    L.append('| # | model_id | vendor | verification_status | 源链接数 | 源链接中的 HF repo | 备注 |')
    L.append('|---|---|---|---|---|---|---|')
    for i, (mid, v, ow, repos, n, vs) in enumerate(ow_true, 1):
        rp = '<br>'.join(repos) if repos else '—'
        note = '' if repos else '**无 HF repo 线索，需人工定点**'
        L.append(f'| {i} | `{mid}` | {v} | {vs} | {n} | {rp} | {note} |')
    L.append('')
    L.append('## 三、B 类：开源状态未确认且 license 空（16 条，前置条件未满足）')
    L.append('')
    L.append('| # | model_id | vendor | verification_status | 源链接数 |')
    L.append('|---|---|---|---|---|')
    for i, (mid, v, ow, repos, n, vs) in enumerate(ow_none, 1):
        L.append(f'| {i} | `{mid}` | {v} | {vs} | {n} |')
    L.append('')
    L.append('## 四、后续补采方法（D40 已验证有效，本轮未执行）')
    L.append('')
    L.append('1. **权威源**：`https://huggingface.co/api/models/{repo}` 返回的 `tags` 数组里读 `license:X`。')
    L.append('   - 比从页面/README 正则抽文本可靠得多（D40 实测正则把 `HF`、`Under the MIT` 误判为许可证名）。')
    L.append('   - 现成脚本：`scripts/d40_license_hf.py`（含 `repo_matches_model()` 同尺寸一致性校验）。')
    L.append('2. **必配一致性校验**：从记录文本抽 repo id 时可能抽错仓库。做法是把 repo 名与记录里的'
             '参数量 token 取**交集，空则拒写**（别要求全等，`mamba-2-2-7b` ↔ `mamba2-2.7b` 这类写法差异会被误拒）。'
             'D40 实测拦下 `g42:jais-70b` ← `inception42/jais-13b` 的错配。')
    L.append('3. **无 HF repo 线索的**：需人工定点（官方 Model Card / 权重下载页 / GitHub 仓库 LICENSE）。'
             'D40 曾统计 A 类中约 32 条属此类；本轮按更严格的 HF **模型库**正则口径（排除 `api/models/*`、'
             '`papers/*` 等非模型路径）复核为 **10 条**，差异来自口径而非数据变化，以本轮 10 条为准。')
    L.append('4. **闭源商业模型不要强补**：`open_weights=false` 时 license 留空是本库既有惯例，不是缺口。')
    L.append('')
    L.append('## 五、D40 已完成的填充（本轮基线）')
    L.append('')
    L.append('D40 通过 HF API 写入 36 条（含一致性校验拒绝 3 条、无 license tag 11 条、无 repo 线索 32 条），'
             '`license` 填充率 51.0% → 56.0%。本轮（D41）**未新增填充**，仅留档。')
    L.append('')

    open(OUT, 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')
    print('已写', OUT)
    print('A 类', len(ow_true), '条｜B 类', len(ow_none), '条')
    noh = sum(1 for r in ow_true if not r[3])
    print('A 类中无 HF repo 线索:', noh)


if __name__ == '__main__':
    main()
