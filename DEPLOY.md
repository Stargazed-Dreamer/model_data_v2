# DEPLOY.md — model_data v2 多平台并发采集部署说明

仓库地址：https://github.com/Stargazed-Dreamer/model_data_v2

> **用途**：把 model_data v2 仓库部署到一台新电脑，让多个 agent 平台并发采集大模型数据。
>
> **谁读这份文档**：
> - **用户**（你）：负责一次性前置（建远程仓库）+ 把本文档带到新电脑
> - **部署 agent**（新电脑上的 agent）：读本文档 + 完成部署
> - **采集 agent**（每个平台上的 agent）：读 `docs/multi_platform_subagent_guide.md` 开工
>
> **跑通状态**（2026-08-27 本机 pilot）：CAS 认领→派发 subagent→单文件门禁→落盘→更新认领表→commit 全链路已验证；4 个 commit 链在 main 分支。

---

## 一、整体架构（一张图看完）

```
┌─────────────────────────────────────────────────────────────────────┐
│  远程 git 仓库（GitHub/Gitee 私有仓库，用户一次性创建）                 │
│  - docs/batch_claim_ledger.jsonl  ← 所有平台共享的批次认领表            │
│  - docs/multi_platform_subagent_guide.md  ← 采集 agent 必读指南         │
│  - model_data_v2.jsonl  ← 主库（只由最终合并 agent 改）                │
│  - incoming/models/*.jsonl  ← 各平台提交的采集产出                     │
│  - scripts/  ← 校验 + 合并工具                                         │
└─────────────────────────────────────────────────────────────────────┘
                                ▲ ▼ git push/pull
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│ 电脑 A         │      │ 电脑 B         │      │ 电脑 C         │
│ (本机/init 机) │      │ (新部署)       │      │ (以后新部署)    │
│               │      │               │      │               │
│ 平台 1: Trae  │      │ 平台 1: Trae  │      │ 平台 1: Codex │
│ 平台 2: Claude│      │ 平台 2: Claude│      │ ...           │
│ ...           │      │ ...           │      │               │
│               │      │               │      │               │
│ 共享一个本地   │      │ 共享一个本地   │      │ 共享一个本地   │
│ git 工作目录   │      │ git 工作目录   │      │ git 工作目录   │
└───────────────┘      └───────────────┘      └───────────────┘
```

**关键性质**：
- 每台电脑 = 一个本地 git 工作目录（clone 出来）
- 同一台电脑上的多个 agent 平台 = 共享读这一个目录，各自开 subagent
- 跨电脑协调 = 通过 git push/pull 同步认领表 `batch_claim_ledger.jsonl`
- 没有"中心调度器"，靠 CAS（Compare-And-Swap）协议抢批次

---

## 二、前置（用户一次性做，在 init 机上）

> **init 机** = 我（写本文档的 agent）所在的这台电脑，仓库已经 init + first commit 完成。本节用户在 init 机上做。

### 2.1 创建私有远程仓库

去 **GitHub / Gitee / 自建 GitLab** 创建一个**私有**仓库（不要 public，里面有商业模型数据）：

- **GitHub**：`https://github.com/new` → Repository name = `model_data_v2` → **Private** → **不要**勾选 "Add a README" / "Add .gitignore" / "Add license"（仓库必须是空的，否则 push 冲突）→ Create repository
- **Gitee**：`https://gitee.com/projects/new` → 私有 → 不要勾选任何初始化文件
- **自建 GitLab**：New project → Create blank → Private

记下远程 URL，形如：
- GitHub HTTPS：`https://github.com/<user>/model_data_v2.git`
- GitHub SSH：`git@github.com:<user>/model_data_v2.git`
- Gitee HTTPS：`https://gitee.com/<user>/model_data_v2.git`

### 2.2 把本地仓库 push 到远程

在 init 机上，**git bash 或 PowerShell** 打开 `workspace/model_data/` 目录，执行：

```bash
# 把 <REMOTE_URL> 替换成上一步的远程 URL
cd /f/project_temp/localAgent/workspace/model_data   # 或 PowerShell: cd f:\project_temp\localAgent\workspace\model_data
git remote add origin <REMOTE_URL>
git push -u origin main
```

如果 push 报 `failed to push some refs`，说明远程仓库不是空的（你勾选了 README 之类的）。两个修法：

1. **重新建一个空仓库**（推荐）
2. 或者强制覆盖远程：`git push -u origin main --force`（会删掉远程上你勾选时生成的 README/.gitignore，本地版会取而代之）

### 2.3 验证远程同步

```bash
git fetch origin
git log --oneline origin/main
# 应该看到 4 个 commit：
# af87f09 fix(.gitignore): 用 **/_merged_archive/ 覆盖所有 _merged_archive 路径
# 55f26b4 submit: b9w1-openai by trae-cn-glmm-local-test (pilot, 1/5)
# 96d45c9 claim: b9w1-openai by trae-cn-glmm-local-test (local pilot)
# de10d2b init: model_data v2 仓库初始化（多平台并发采集基线）
```

### 2.4 把本文档 + 远程 URL 带到新电脑

把以下两样东西带到新电脑：
1. **远程仓库 URL**（一串字符）
2. **本文档 DEPLOY.md**（可以 U 盘拷、邮件发自己、放云盘）

新电脑上的部署 agent 读本文档就能开工。

---

## 三、新电脑部署（部署 agent 执行）

> **部署 agent** = 用户在新电脑上启动一个 agent（Trae / Claude Code / Codex CLI / Cursor 等），把本文档路径喂给它，它读完后完成部署。
>
> 部署 agent 与后续的采集 agent **可以是同一个**，也可以不同；部署完成后该 agent 可以直接转为采集 agent 开工。

### 3.1 环境检查

```bash
# 1. git 必须装
git --version              # 应输出 git version 2.x

# 2. python 3.10+ 必须装
python --version            # 应输出 Python 3.10+；Windows 可能要 py --version
python -c "import json; print('ok')"

# 3. （可选）uv 包管理器，用于跑 Python 脚本更快
# 不装也行，所有脚本只用标准库，无需 pip install
```

如未装：
- **git**：`https://git-scm.com/downloads` 下载安装
- **python**：`https://www.python.org/downloads/` 下载 3.10+，安装时勾选 "Add to PATH"
- **uv**（可选）：`pip install uv` 或 `curl -LsSf https://astral.sh/uv/install.sh | sh`

### 3.2 选定部署目录

挑一个目录作为本地工作目录。建议：
- **Windows**：`D:\model_data` 或 `C:\Users\<user>\model_data`（避免 `C:\Program Files` 这类需管理员权限的路径）
- **Linux/macOS**：`~/model_data` 或 `/opt/model_data`

目录名**不要**含中文/空格（避免后续 PowerShell / Python 路径转义麻烦）。

### 3.3 clone 仓库

```bash
# <REMOTE_URL> = 用户给的远程 URL
# <DEPLOY_DIR> = 上一步选的目录
cd <DEPLOY_DIR 的父目录>
git clone <REMOTE_URL> model_data
cd model_data

# 验证
git log --oneline           # 应看到 4 个 commit
ls                          # 应看到 docs/ scripts/ incoming/ intermediate/ model_data_v2.jsonl .gitignore
```

### 3.4 配置本机 git 身份

如果这台电脑没配过 git 用户名/邮箱：

```bash
git config user.name "<你想起的名字>"
git config user.email "<你想起的邮箱>"
# 例如：git config user.name "Alice-PC" / git config user.email "alice@example.com"
```

注意：**不要**用 `--global`（避免污染其他项目），用仓库级配置（不带 `--global`）。

### 3.5 跑一遍校验脚本验证主库完整

```bash
# Windows PowerShell
$env:PYTHONUTF8='1'
python scripts/validate_model_data.py model_data_v2.jsonl

# Linux/macOS
PYTHONUTF8=1 python scripts/validate_model_data.py model_data_v2.jsonl

# 应输出：ERROR 0 项 / WARN ~119 项（WARN 不阻塞，是规范性提醒）
```

### 3.6 验证样本 + 认领表

```bash
# 样本文件存在（供 subagent 学格式）
ls incoming/models/_samples/                                   # 应看到 sample_google_*.jsonl + sample_openai_*.jsonl
# 共享上下文存在
ls incoming/models/_m_context.md                              # 应存在
# 认领表存在且可读
python -c "import json; n=sum(1 for _ in open('docs/batch_claim_ledger.jsonl', encoding='utf-8')); print(f'ledger lines: {n}')"
# 应输出 ledger lines: 305
```

### 3.7 报告部署完成

部署 agent 完成后向用户报告：

```
部署完成。
- 仓库路径：<DEPLOY_DIR>/model_data
- git 用户名：<你配的>
- 主库校验：ERROR=0 / WARN=N（填实际数）
- 认领表批次：305 条（其中 1 条已 submitted = b9w1-openai pilot，1 条已 submitted = ada 文件；其余 304 条 pending）
- 可用 agent 平台：列出本机已装的（如 Trae / Claude Code / Codex / Cursor 等）
- 下一步：每个平台 agent 读 docs/multi_platform_subagent_guide.md 开工
```

---

## 四、各 agent 平台开工（每个平台都做）

> **采集 agent** = 用户在每个 agent 平台上启动的 agent。它的工作就是读指南、认领批次、派发 subagent、验收、提交。

### 4.1 启动一个采集 agent

打开 agent 平台（Trae / Claude Code / Codex / Cursor / ...），在工作目录 `<DEPLOY_DIR>/model_data` 启动会话，给它一句话：

```
你是 model_data v2 多平台并发采集的主 agent。读 docs/multi_platform_subagent_guide.md 全文，按指南开工。
本平台 ID = <起个名，如 trae-cn-glmm / claude-opus / codex-cli>
```

### 4.2 agent 该做的事（一句话总览）

详见 `docs/multi_platform_subagent_guide.md`，这里只列大纲：

1. **读指南**：`docs/multi_platform_subagent_guide.md` §1-§7
2. **读共享上下文**：`incoming/models/_m_context.md`
3. **读认领表**：`docs/batch_claim_ledger.jsonl`，找 `status=pending` 的批次
4. **认领 N 个批次**（N=本平台可同时开的 subagent 数，建议 3-5）：
   - `git pull --rebase`
   - 改本地副本：把 N 个 pending 批次的 `status` 改为 `claimed`、`claimed_by=<平台ID>`、`claimed_at=<ISO8601>`
   - `git add docs/batch_claim_ledger.jsonl && git commit -m "claim: <batch_id列表> by <平台ID>" && git push`
   - push 失败 = 被抢，`git pull --rebase` 后重试
5. **派发 subagent**：按指南 §3 模板，为每个 model_id 派一个 subagent
6. **验收**：每个 subagent 完成后，主 agent 跑 `python scripts/validate_model_data.py <file>` 确认 ERROR=0
7. **落盘**：通过门禁的文件已在 `incoming/models/`（subagent 直接写到这里）
8. **更新认领表 + 提交**：
   - 把对应批次 `status` 改为 `submitted`、`submitted_at`、`submitted_files=[...]`
   - `git add docs/batch_claim_ledger.jsonl incoming/models/<batch_id>__*.jsonl`
   - `git commit -m "submit: <batch_id列表> by <平台ID>"`
   - `git push`
9. **退出**：所有认领批次都 submitted 后，agent 退出。**不要合并主库**——合并是最后阶段高端合并 agent 的事。

### 4.3 平台 ID 命名规范

`<平台名>-<模型名>`，例如：
- `trae-cn-glmm`（Trae CN 上的 GLM-5.2）
- `claude-opus-4-5`（Claude Code 上的 Opus 4.5）
- `codex-cli-gpt5`（Codex CLI 上的 GPT-5）
- `cursor-claude`（Cursor 上的 Claude）
- `windsurf-sonnet`（Windsurf 上的 Sonnet）

每个平台起一个唯一 ID。同平台不同会话可加后缀 `-s2` / `-s3` 区分。

### 4.4 多平台共享同一台电脑的目录

- 同一台电脑上的多个 agent 平台 **共享同一个 git 工作目录**（不要让每个平台 clone 一份！）
- 各平台的 git 操作要小心：A 平台正在 commit 时 B 平台不要同时 push
- 简单办法：每个平台认领前先 `git pull --rebase`，commit 后立即 `git push`，把"持有本地未推送 commit"的时间缩到最短
- **万一两个平台同时改了认领表**：后 push 的会失败，pull --rebase 后看冲突——通常只冲突认领表那行，手工 merge 选两边的 claim（两个批次都认领成功）即可

---

## 五、常见问题

### 5.1 Windows GBK 控制台崩溃

所有 Python 命令前必须加 UTF8 前缀，否则合并工具的 emoji 输出会让 GBK 控制台崩：

```powershell
# PowerShell
$env:PYTHONUTF8='1'
python scripts/validate_model_data.py ...

# cmd
set PYTHONUTF8=1 && python scripts/validate_model_data.py ...
```

Linux/macOS 无此问题，但加 `export PYTHONUTF8=1` 也无害。

### 5.2 行尾 CRLF / LF

`.gitattributes` 强制所有 `.jsonl/.md/.py` 用 LF。Windows clone 时 git 会按 `core.autocrlf` 设置自动处理。

**不要**在 Windows 上手动把文件转成 CRLF，否则单行 JSONL 会被插入 `\r` 导致解析问题。

如果 `git diff` 显示整个文件都变了（明明只改了一行），多半是行尾被某个编辑器改了：

```bash
git config core.autocrlf false
git config core.safecrlf false
git checkout -- <file>
```

### 5.3 git push 失败（CAS 抢占）

正常情况——说明别的平台先 push 了：

```bash
git pull --rebase
# 如果有冲突，多半在 docs/batch_claim_ledger.jsonl 同一行
# 手工编辑解决：保留两边都改了的 claim（如果认领的是不同批次，就两个都留）
git add docs/batch_claim_ledger.jsonl
git rebase --continue
git push
```

### 5.4 subagent 返回空 / "toolcall_result is missing"

经验上前 8 批次约 40% 的 subagent 调用会丢结果。**先查磁盘**：

```bash
ls incoming/models/<batch_id>__*.jsonl
```

文件存在 → 直接验收，不用重派。文件不存在 → 重派（同一 subagent 任务书重发一次，最多 5 次）。

### 5.5 git push 报 "no remote configured"

部署 agent 忘了 push 远程，或者 clone 时没把 origin 带上。修：

```bash
git remote add origin <REMOTE_URL>
git push -u origin main
```

### 5.6 Python 脚本报 ModuleNotFoundError

所有脚本只用标准库（`json` / `os` / `re` / `argparse` / `datetime` / `pathlib` / `collections`），不应该报缺包。如果报了，检查：
- 是不是用了 `uv run python`？换成 `python`
- 是不是 Python 版本太老？`python --version` 应 ≥ 3.10

### 5.7 校验脚本报 "schema_version missing"

多半是 subagent 把 `access` 提成了顶层键（应该嵌在 `basic_info.access` 内）。修：

```python
# 一行修复
import json
p = r'<文件路径>'
r = json.loads(open(p, encoding='utf-8').read())
if 'access' in r:
    r['basic_info']['access'] = r.pop('access')
    open(p, 'w', encoding='utf-8', newline='\n').write(json.dumps(r, ensure_ascii=False, separators=(', ', ': ')) + '\n')
```

---

## 六、部署验证清单

部署 agent 跑完前三节后，逐项打勾：

- [ ] git 已装（`git --version` 输出 2.x）
- [ ] python 3.10+ 已装（`python --version` 输出 3.10+）
- [ ] 仓库已 clone 到 `<DEPLOY_DIR>/model_data`
- [ ] `git log --oneline` 看到 4 个 commit（init → claim → submit → gitignore fix）
- [ ] `git remote -v` 显示 origin 指向远程 URL
- [ ] `git config user.name` / `user.email` 已配
- [ ] `python scripts/validate_model_data.py model_data_v2.jsonl` 输出 ERROR=0
- [ ] `incoming/models/_samples/` 有 2 个样本文件
- [ ] `incoming/models/_m_context.md` 存在
- [ ] `docs/batch_claim_ledger.jsonl` 305 行可读
- [ ] 第一个采集 agent 能读 `docs/multi_platform_subagent_guide.md` 全文

全部打勾 → 部署完成，可以让每个平台的采集 agent 开工。

---

## 七、用户在新电脑上的最小操作（不依赖部署 agent）

如果不想用部署 agent，用户也可以手动 4 步搞定：

```bash
# 1. 装 git + python（首次）
#    Windows: 装 https://git-scm.com 和 https://python.org 的最新版
#    macOS: brew install git python
#    Linux: sudo apt install git python3

# 2. clone 仓库
cd <你想放的目录>
git clone <REMOTE_URL> model_data
cd model_data

# 3. 配 git 身份（每台电脑一次）
git config user.name "<你起的名字>"
git config user.email "<你的邮箱>"

# 4. 在任意 agent 平台启动一个会话，喂给它这句话：
#    "你是 model_data v2 多平台并发采集的主 agent。读 docs/multi_platform_subagent_guide.md 全文，按指南开工。本平台 ID = <起个名>"
```

---

## 八、以后再加新电脑

完全重复 §三 或 §七 即可。每台新电脑只需要：
- 装好 git + python
- clone 一次仓库
- 配 git 身份
- 启动 agent 平台读指南开工

新电脑不需要在本机登记，靠 git push/pull 自动跟其他电脑协调。

---

## 九、最终合并阶段（所有采集完成后）

不在本文档范围，简单提一句：当所有批次 status=`submitted` 或 `failed` 后，由一个高端合并 agent（如 Claude Opus 4.5 / GPT-5 Pro）做：

1. 扫描 `incoming/models/*.jsonl` 所有文件
2. 按 batch_id 字母序逐个合并到 `model_data_v2.jsonl`（用 `scripts/model_data_tool.py merge --apply`）
3. 全库门禁 `scripts/validate_model_data.py model_data_v2.jsonl --report final.md`
4. 对 status=`failed` 或合并后 fill_score 仍极低的模型重跑
5. 最终 commit + push

详见 `docs/multi_platform_subagent_guide.md` §7。

---

## 十、参考路径速查

| 用途 | 路径（相对仓库根） |
|---|---|
| 本部署说明 | `DEPLOY.md` |
| 采集 agent 必读指南 | `docs/multi_platform_subagent_guide.md` |
| 共享上下文（红线 + 字段口径） | `incoming/models/_m_context.md` |
| 批次认领表 | `docs/batch_claim_ledger.jsonl` |
| 主库（不要直接改） | `model_data_v2.jsonl` |
| 单文件门禁工具 | `scripts/validate_model_data.py` |
| 合并工具（最终阶段用） | `scripts/model_data_tool.py` |
| 样本（学格式用） | `incoming/models/_samples/sample_*.jsonl` |
| 模型清单（参考） | `intermediate/roster.jsonl` |

---

**全文完。祝部署顺利。**
