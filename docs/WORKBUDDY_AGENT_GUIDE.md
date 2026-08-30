# WorkBuddy Agent 专属作业规范（model_data v2）

> **本文档读者**：在 WorkBuddy 平台上运行的 agent（主 agent 与它派发的 subagent）。
> **定位**：是 [`multi_platform_subagent_guide.md`](./multi_platform_subagent_guide.md)（跨平台通用规范）的**平台补丁**。通用规范里的认领协议、文件命名、12 条红线、验收 checklist 全部继续有效，本文档只补充 WorkBuddy 环境特有的坑和必须额外执行的动作。
> **冲突时**：以本文档为准（因为它记录的是本平台实测过的环境事实）。
> **建立**：2026-08-28，基于 workbuddy-01 烂尾事故复盘 + 本机 git 弹窗问题。

---

## 0. 30 秒 TL;DR（开工前必读）

```bash
# ① 所有 git 操作必须用【用户本机 git】，绝不能用 WorkBuddy 自带的
export PATH="/e/System_Programes/Git/cmd:$PATH"   # 每个新 Bash 会话都要先执行
git --version        # 必须是 2.46.0.windows.1；若是 2.55.0 说明 PATH 没生效，停下重来

# ② 环境变量里的代理常是死的，push 前先绕开（见 §1.5）
unset HTTP_PROXY HTTPS_PROXY

# ③ Python 命令统一加 UTF8 前缀（Windows GBK 控制台会崩）
PYTHONUTF8=1 python scripts/validate_model_data.py <file>

# ④ 提交采集文件时必须 -f（.gitignore 第 29 行忽略了 incoming/models/*.jsonl）
git add -f incoming/models/<batch_id>__*.jsonl

# ⑤ 合并主库必须用 source_wins，不是 add（见 §13）
python scripts/model_data_tool.py merge --file model_data_v2.jsonl --incoming <f> \
  --on-null take_source --on-both source_wins --on-array replace --on-schema upgrade \
  --tie-breaker keep_target --apply

# ⑥ 作业顺序：先收尾自己平台上未提交的批次，再认领新批次
# ⑦ 每批完成后立即 push，不要攒着 —— 烂尾比慢更严重
```

---

## 1. 【红线 A】git 二进制：必须用用户本机的 git

### 1.1 问题现象

WorkBuddy 的 Bash 工具默认 PATH 里排在最前面的是 WorkBuddy 自带的 PortableGit（`/mingw64/bin/git`，v2.55.0）。用它 `git push` 会**弹出交互式凭据窗口**，agent 无法应答，进程挂死，任务烂尾。

### 1.2 根因

两套 git 的 system 级 `credential.helper` 不同，凭据不互通：

| git | 版本 | `credential.helper`(system) | push 行为 |
|---|---|---|---|
| `/e/System_Programes/Git/cmd/git`（用户本机） | 2.46.0.windows.1 | `manager` | 读 Windows 凭据管理器，**静默通过** |
| `/mingw64/bin/git`（WorkBuddy 自带） | 2.55.0.windows.3 | `helper-selector` | **弹交互窗**，agent 卡死 |

用 `type -a git` 可以看到两个都在，PortableGit 排前面。

### 1.3 唯一正确做法

**方式一（推荐，一次设置整会话有效）**：

```bash
export PATH="/e/System_Programes/Git/cmd:$PATH"
git --version    # 校验：必须输出 2.46.0.windows.1
```

**方式二（显式绝对路径，最保险，适合写进脚本）**：

```bash
/e/System_Programes/Git/cmd/git -C <REPO> push
```

> ⚠️ Bash 工具的**每个新会话**都要重新 `export PATH`，shell state 不跨调用保留。
> 每次执行 push 前，先跑一次 `git --version` 自检；看到 2.55.0 就说明 PATH 没生效，**不要用**。

### 1.4 仓库信息

- remote：`https://github.com/Stargazed-Dreamer/model_data_v2.git`
- 默认分支：`main`
- 已配置 user.name / user.email（无需再设）

### 1.5 【新坑】环境变量代理是死的，push 前必须绕开

**现象**：`git push` / `git pull` 报
```
fatal: unable to access 'https://github.com/...': Failed to connect to 127.0.0.1 port 9910 after 2037 ms
```

**原因**：环境里设了 `HTTP_PROXY=http://127.0.0.1:9910/` / `HTTPS_PROXY=http://127.0.0.1:9910/`（`WORKBUDDY_PROXY_SOURCE=system`），但那个本地代理进程**没在运行**。git 会乖乖走代理然后连不上——注意这不报「代理错误」，而是伪装成网络不通，很容易误判成「没网」。

**解法**：直接 `unset HTTP_PROXY HTTPS_PROXY` 走直连。本机实测直连 GitHub 是通的。

```bash
unset HTTP_PROXY HTTPS_PROXY
git push origin main        # 立刻成功
```

> 每个新 Bash 会话都要重新 `unset`，shell state 不跨调用保留。
> 排障时别用 `env | grep -i proxy` 全量打印——本仓库环境下那个变量会连带吐出几十万字符，直接把上下文冲垮。用 `env -u HTTP_PROXY ...` 或者直接 `unset` 后重试即可。

---

## 2. 【红线 B】采集文件必须 `git add -f`

根 `.gitignore` 第 29 行有：

```
/incoming/models/*.jsonl
!/incoming/models/_samples/
!/incoming/models/_m_context.md
```

即 `incoming/models/` 下只有 `_samples/` 和 `_m_context.md` 入库，**所有采集产出默认被忽略**。

- 提交时必须 `git add -f incoming/models/<batch_id>__*.jsonl`
- 忘记 `-f` 的后果：`git status` 干净，你以为提交成功了，实际只推了 ledger，文件从未进仓库 —— 合并阶段拿不到数据
- 提交后自检：`git ls-files incoming/models/ | grep <batch_id>` 必须能列出你的文件

---

## 3. 环境差异速查（WorkBuddy 平台实测）

| 项 | 值 / 做法 |
|---|---|
| shell | Git Bash（POSIX），路径用 `/` 正斜杠 |
| 仓库根 `<REPO>` | `F:/project_temp/localAgent/workspace/model_data` |
| Python | 系统 Python 可用；跑脚本一律加 `PYTHONUTF8=1` 前缀 |
| 控制台编码 | GBK，脚本里的 emoji/CJK 输出不加 UTF8 前缀会崩 |
| 网络 | `docs.claude.com` / `platform.openai.com` 直连不可达，信息源以 WebSearch 摘要为准并按红线降级标 T3 |
| 不可调 | 不要调 `cmd.exe` / PowerShell 子进程（安全策略会拦截），用纯 bash |

---

## 4. 平台 ID

- 格式：`workbuddy-<NN>`，NN 为两位序号
- 启动会话时先读 ledger，取一个**当前未被占用**的最小编号（已被 `workbuddy-01` 占用）
- 一个会话内所有批次用同一个 ID，便于留痕和接管判定

---

## 5. 标准作业流程（SOP）

```
S1 环境自检   export PATH=... ; git --version 必须 2.46.0 ; git pull --rebase
S2 收尾      读 ledger，找 claimed_by == 本平台ID 且 status != submitted 的批次
             → 文件已在磁盘：validate → 改 submitted → add -f → push（见 §6）
             → 文件缺失：补齐采集，或按 §7 判定后回退 pending
S3 认领      按通用规范 §2.2 的 CAS 协议，认领 2-4 个 pending 批次，立即 commit+push
S4 采集      每个 model_id 派发一个 subagent（任务书模板见通用规范 §3，须附 §5 全部红线）
S5 门禁      每个文件跑 validate_model_data.py，ERROR 必须 = 0（WARN 可接受）
S6 提交      改 ledger 为 submitted + 填 submitted_files → add -f 文件 → commit → push
S7 复核      git ls-files 确认文件确实入库；git status 干净；主库 model_data_v2.jsonl 无 diff
```

**每批做完就 push**，不要攒。通用规范 §8.3-13 也是这个要求，但本平台要当成硬约束：见 §7 烂尾教训。

---

## 6. 收尾动作的正确姿势（高频场景）

磁盘上已有 `<batch_id>__*.jsonl` 但 ledger 还停在 `claimed` 时：

```bash
# 1) 门禁（每个文件都要跑，ERROR 必须 0）
PYTHONUTF8=1 python scripts/validate_model_data.py \
  "incoming/models/b9w6-openai__openai__text-ada-001__base.jsonl"

# 2) 改 ledger：status=submitted，填 submitted_at / submitted_files / submitted_by
#    （用 Python 原地改写，保持单行压缩 JSON、UTF-8 无 BOM、其余行原样）

# 3) 提交（注意 -f）
export PATH="/e/System_Programes/Git/cmd:$PATH"
git add docs/batch_claim_ledger.jsonl
git add -f incoming/models/b9w6-openai__*.jsonl
git commit -m "submit: b9w6-openai (5/5) by workbuddy-02"
git push

# 4) 自检：文件必须能被 ls-files 列出
git ls-files incoming/models/ | grep b9w6-openai
```

---

## 7. 防烂尾：超时批次的接管规则

### 7.1 事故复盘（务必记住）

2026-08-27 14:26，agent `workbuddy-01` 认领了 3 个批次（b9w6-openai / b9w7-openai / b12w4-anthropic，共 15 个模型），15 个文件**已全部采集落盘**（合计约 100KB），但**从未更新 ledger、从未 push**。后果：

- 其他平台看 ledger 以为这 3 批"有人在做"，不会接管 → 进度虚占
- 文件因 `.gitignore` 未入库 → 远端完全没有这批数据
- 合并阶段按 `status=submitted` 扫描，**这 15 个模型会被整体漏掉**

### 7.2 判定与处理

| 情况 | 判定 | 动作 |
|---|---|---|
| `claimed` 且 `claimed_by` == 本平台 ID | 自家烂尾 | **直接接管收尾**（§6），`claimed_by` 保持原值，notes 追加 `[recovered by <新ID> @ <now>]` |
| `claimed` 且超时 > 24h（他人平台） | stale | 可接管：`claimed_by` 改本平台 ID，notes 留痕"接管原平台 X 超时未交" |
| `claimed` 且未超时（他人平台，< 24h） | **进行中** | **禁止抢**。可能是对方正在采集或即将 submit，只在报告里提示用户 |
| `claimed` 但磁盘已有完整文件（他人，未超时） | 对方将交 | **不动**，仅报告 |
| `claimed` 但**用户已确认该 agent 停摆**（额度超限 / 进程被杀 / 明确不再回来） | 立即接管 | 超时规则不再适用，按 §7.4 三分类处置 |

> 判定超时用 `claimed_at` 与当前时间比较。`claimed_at` 有 `+08:00` 和 `+00:00` 两种写法，**比较前统一转 UTC**。

### 7.4 接管停摆批次的三分类（关键）

用户确认某批 agent 不会再回来后，对它名下所有 `claimed` 批次**逐个分类处置**，不要一刀切：

| 磁盘文件情况 | 判定 | 动作 |
|---|---|---|
| 文件存在、`json.loads` 通过、数据已在主库 | 采完了，只差收尾 | 改 `submitted` + 填 `submitted_files` + `add -f` 入库，`claimed_by` **保持原值** |
| 文件存在但 **`json.loads` 抛异常** | 写到一半被截断 | 隔离到 `backups/quarantine/<名>.corrupt-<日期>`，改 `pending` + 清空 `claimed_by`，notes 写明需重采 |
| 文件根本不存在 | 认领了但零产出 | 改 `pending` + 清空 `claimed_by` / `claimed_at`，notes 留痕（同 §11.3） |

> ⚠️ **必须逐文件 `json.loads` 验证，不能只看文件大小。** 实测一个 7472 字节的文件看着正常，实际 JSON 字符串未闭合——agent 正在写盘时被截停。按大小判断会把它误判成「已完成」而补提交，把坏数据固化进仓库。

**判定集体停摆的辅助信号**：统计 ledger 里 `submitted_at` 的小时分布，若某时刻之后归零而 `claimed_at` 全停在同一时刻，基本可确认（本轮实测：05:39~05:43 认领 12 批，05 时还有 59 批/小时，06 时起归零）。

### 7.3 强制自检（会话结束前必做）

- [ ] 本平台 ID 下**没有任何** `status=claimed` 的残留批次
- [ ] 所有提交过的批次，`git ls-files incoming/models/ | grep <batch_id>` 有输出
- [ ] `git status` 干净（无未提交的 ledger / 文件改动）
- [ ] `git log` 最新 commit 含本轮所有批次号

**"文件写完就报告完成"不算完成。ledger 改完 + push 成功 + ls-files 能查到，才算完成。**

---

## 8. 文件命名与 model 字段（易错点）

- 文件名：`<batch_id>__<vendor>__<model>__<variant>.jsonl`（model_id 的 `:` 全部替换为 `__`，**双下划线**）
- JSON 内的 `model_id` 保持三段式原样（`vendor:model:variant`），**不要**在 JSON 里也替换
- **variant 以 ledger 的 `models` 字段为准**（多为 `base`），不要把 model 名尾段当 variant
  - 例：`microsoft:phi-3-mini-4k-instruct:base` → 文件 `...__phi-3-mini-4k-instruct__base.jsonl`
  - 反例（错误）：把 `phi-3-mini-4k-instruct` 拆成 model=`phi-3-mini` + variant=`4k-instruct`
- `submitted_files` 字段填**相对仓库根的路径**（`incoming/models/<文件名>`），历史记录里两种写法都有，新提交统一用带路径的完整形式

### 8.1 超长文件名降级规则（Windows 路径 260 上限）

多机构联合署名批次的 `batch_id` 可能极长（本库最长 479 字符），且文件名里 `vendor` 段与 `batch_id` 内容重复，导致路径爆表：

```
b56w1-allen-institute-for-ai-...-of-maryland__b56w1-allen-institute-for-ai-...-of-maryland__olmo-3-1-32b-think__base.jsonl
→ 绝对路径 706 字符，Windows 直接抛 OSError [Errno 22] Invalid argument，文件根本写不出来
```

**判定**：若标准命名 `<batch_id>__<vendor>__<model>__<variant>.jsonl` 的**绝对路径长度 > 250 字符**，降级为：

```
incoming/models/<bNNwM>__<model>__<variant>.jsonl
```

其中 `<bNNwM>` 是 `batch_id` 第一个 `-` 之前的部分（如 `b56w1`）。已核验：全库 305 个批次的短标识**两两不冲突（0 冲突）**，降级后最长绝对路径 133 字符，全部安全。

**影响面**：全库 702 个应产出文件中有 **26 个超限，涉及 19 个批次**（最长为 `b97w1-rwkv-foundation-...`，路径 1041 字符）。这些批次**无法用标准命名落盘**，必须走降级。

> ⚠️ **降级只解决「写盘」，不解决「入库」。** 绝对路径在 **250~260 字符之间**的文件，Python 能写，但 `git add -f` 会报 `error: open("...")`：
> ```
> error: open("incoming/models/b118w1-beijing-institute-of-technology-academy-of-military-science-minzu-university-of-china__..."): Filename too long
> ```
> 解法（一次性，全平台受益）：`git config core.longpaths true`（仓库级，仅改 `.git/config`，不影响远端、不影响他人工作）。
> 实测：89 个补入库文件中有 2 个卡在这里（绝对路径 264 / 312 字符），开启后一次通过。**建议新机器部署时就先设上**（可并进 `DEPLOY.md` §3.3）。

**注意**：降级后合并阶段照样工作——合并工具按 ledger 的 `submitted_files` 定位文件，不靠文件名反推 batch_id；`bNNwM` 前缀本身仍是有效批次标记。JSON 内的 `model_id` 保持三段式原样，不受影响。

---

## 9. 故障速查

| 现象 | 原因 | 解法 |
|---|---|---|
| `git push` 卡住不动 / 弹窗 | 用了 WorkBuddy 自带 git | `export PATH="/e/System_Programes/Git/cmd:$PATH"`，校验版本 2.46.0 |
| `git status` 干净但远端没文件 | 漏了 `git add -f` | 重跑 `git add -f` + commit + push，`git ls-files` 验证 |
| `git add -f` 报 `error: open("...") Filename too long` | 绝对路径 250~260 字符，撞 Windows 上限 | `git config core.longpaths true` 后重试（见 §8.1 补充） |
| 主库校验 ERROR=0，但源文件校验 ERROR>0 | 越界 `positioning` 标签在合并时被**静默丢弃**，主库落成 `[]` | 两边都要看：主库干净 ≠ 源文件合规 ≠ 数据完整。按 §8.2-9 修源文件；主库回填见 §12 |

### 12. 主库单字段编辑：`set` 子命令（2026-08-29 新增）

> **背景**：在此之前 `model_data_tool.py` 只有 `read`/`compare`/`table`/`list`（只读）+ `merge`。想改主库里一个已合并字段只能重跑 `merge --apply`，而 merge 会用源文件覆盖整条记录，可能冲掉合并时自动补全的骨架结构——**收益小于风险**。故补一个 `set` 专治这个场景。

```bash
# 1) 先 dry-run（默认就是 dry-run，不加 --apply 绝不写盘）
PYTHONUTF8=1 python scripts/model_data_tool.py set \
  --file model_data_v2.jsonl \
  --models "vendor:model:base" \
  --field basic_info.positioning \
  --value '["工具调用增强"]' \
  --expect '[]'          # 乐观锁：当前值必须等于它，否则整体放弃

# 2) 确认预览无误，加 --apply 真写
```

| 参数 | 作用 |
|---|---|
| `--models` | 一个或多个 `model_id`，同一字段同一值批量改 |
| `--field` | 点号路径，如 `basic_info.positioning` |
| `--value` | **JSON 字面量**：字符串要带引号 `'"中端"'`；数组 `'["旗舰","中端"]'`；`null` 直接写 `null` |
| `--expect` | **强烈建议带上**。当前值不等于它 → 一条都不写（乐观锁，防改错记录） |
| `--create-path` | 中间层缺失时补空对象。**默认拒绝**，避免静默造出结构 |
| `--apply` | 真正写入；不加则只预览 |
| `--no-backup` | 关闭自动备份。**默认开启**（写入前生成 `<file>.bak`） |
| `--no-gate` | 写入后不跑门禁。**默认开启门禁复检**，并打印 ERROR/WARN 的前后差值 |

**安全设计（与 `merge` 一致：显式、无隐藏默认、dry-run 优先）**：

- **all-or-nothing**：任一记录校验失败（model_id 不存在 / 乐观锁不匹配 / 路径不可写）→ **全部放弃**，不会写一半
- 写入走 `_save()` 原子替换（临时文件 + `os.replace`），中断不会产生半个文件
- 写入后自动调 `validate_model_data.check_record` 复检受影响记录；ERROR 变多会明确告诉你怎么回滚

> ⚠️ `--file` 的 `.bak` 每次写入都会**覆盖**，不是历史快照。要留版本请自己 `cp` 到 `/backups/`（该目录已 gitignore）。
>
> 实测：本轮用 `set` 把 `carrotai` 的 `positioning` 从 `[]` 补回 `["工具调用增强"]`；写入前后逐条比对——950 条、model_id 集合完全一致、仅目标 1 条内容变化、全库仍 ERROR 0。另在副本上故意写越界标签验证门禁集成，工具正确报出 ERROR 1 并给出回滚指引。

### 12.1 历史结论（2026-08-29 之前，仅供参考）

`scripts/model_data_tool.py` 曾只有 `read` / `compare` / `table` / `list`（**只读**）+ `merge`（默认 dry-run，`--apply` 才写）。**没有单字段 set / update 命令。**

### 13. 合并主库：是「填骨架」不是「加记录」（重要，极易踩错）

> **2026-08-29 实测发现**：主库 `model_data_v2.jsonl` 里的 950 条记录中，**702 条花名册模型的骨架早已预填**（来源为 HF API 快照：full_name、vendor、release_date、参数量、access 三态、部分 pricing 都已有值，modality 多为全 null）。
> 所以采集完成后合并时，目标记录**已存在**，merge 走的是 `set_field` / `fill_null` 路径，**不是** `add_record`。

**后果**：若按直觉用 `--on-both conflict`，每条会报 10~16 处冲突、一个字段都不写，白跑一趟。

正确命令（本轮 19 个模型全部 0 冲突通过）：

```bash
python scripts/model_data_tool.py merge \
  --file model_data_v2.jsonl \
  --incoming incoming/models/<file>.jsonl \
  --on-null take_source \
  --on-both source_wins \
  --on-array replace \
  --on-schema upgrade \
  --tie-breaker keep_target \
  --apply
```

- `--on-both source_wins`：采集值覆盖骨架值（骨架多为 HF 快照，人工采集更准）
- `--on-null take_source`：骨架为 null 的字段用采集值填上
- 骨架独有的字段（如 `pricing.promotions`）会被保留，merge 是递归合并不是整体替换
- 合并前后**主库记录数不变**（950 条），这是正常的——不是没生效
- ⚠️ **`--on-array replace` 会把「来源数组为空」当成清空指令**（详见 §18）。
  采集分片经常只填 `benchmarks.self_reported`，`independent` / `arena_elo` 留 `[]`，
  replace 就把目标里已有的条目整组抹掉，且合并计划里一行提示都没有。
  工具已加**空数组保护**：来源为空且目标非空时默认保留目标并在计划里记 `skip`；
  确需清空必须显式加 `--allow-empty-replace`。合并后务必比对一次跑分条目总数，见 §18 的取证脚本。

> ⚠️ 骨架里有些字段与实采结论冲突，例如 fugaku-llm 骨架写 `api=true`（HF 快照推导）而实查无官方 API。按 `source_wins` 会被实采值纠正，并在 `access.notes` 里写明差异。

### 14. 门禁三个高频踩点（本轮全部踩过一遍）

| 现象 | 原因 | 解法 |
|---|---|---|
| `ERROR basic_info.release_date='2003' 非 ISO 8601` | 只写了年份 | 必须是 `YYYY-MM-DD` 或 `YYYY-MM`；只有年份时**宁可记 null 并在 meta.notes 说明**，不要编造月份 |
| `WARN 参数量全空但 architecture.notes 未声明` | notes 里没出现规定字串 | `architecture.notes` 必须含**字面**「未披露」或「待补」。写「论文未以现代口径披露」**不算**——校验器做的是子串匹配 |
| `WARN 有标称上下文但有效上下文为空` | 填了 `context_window_tokens` 但 `context_window_effective_tokens` 为 null | notes 里写明「标称值，有效上下文待测」 |

另外两个隐性规则：
- 骨架里 `positioning` 常是 `[]`，用 `--on-array replace` 且来源非空时会被正常覆盖为采集值；**采集值必须是六值枚举子集**，否则合并时会被静默丢弃（见 §9）
- 只写年份的历史模型（如 Bengio 2003 NPLM），`positioning` 六个标签**没有一个适用**，此时应记 `[]` 并说明，不要硬套标签

- 想修主库里某个已合并记录的单个字段，**只能重跑 `merge --apply`**，没有其他正当路径
- 但重跑 merge 会用源文件覆盖目标记录，可能把合并时自动补全的骨架结构冲掉
> **2026-08-29 更新：上面这段已过时。** 当天给 `model_data_tool.py` 补了 `set` 子命令，专治「改主库单个字段」，见 §12。保留原文是为了留痕——如果你在旧版本工具上，仍是这个约束。

| Python 报 UnicodeEncodeError | GBK 控制台 | 命令前加 `PYTHONUTF8=1` |
| 门禁报 positioning 越界 | 用了受控词表外的标签 | 六值枚举：`旗舰/中端/轻量/推理增强/多模态/工具调用增强`，越界标签按通用规范 §8.2-9 映射或删除 |
| 门禁报顶层键数量不对 | `access` 被提到顶层 | `access` 必须嵌在 `basic_info.access` 内；8 个顶层键固定 |
| subagent 返回空但疑似已写盘 | Task 结果丢失（发生率约 40%） | **先查磁盘再决定是否重派**，不要盲目重跑 |
| `push` 被拒（远程有新 commit） | 被其他平台抢先 | `git pull --rebase`，检查自己 claim 的批次是否被抢；被抢则放弃该批，取下一批 pending |
| `git ls-files \| grep <batch_id>` 查不到刚提交的文件 | grep 把 `^` 锚在了行首，但输出行首是 `incoming/models/` | 写成 `git ls-files incoming/models/ \| grep "incoming/models/<batch_id>__"` |
| 派发 subagent 返回 `429 queue.userLimit.title` / `429 queue.waiting.title` | 平台级并发 agent 上限，与项目无关，重试无效 | 见下方 §11 |

---

### 15. 【2026-08-29 复核新增】三个会被文档误导的地方

**15.1 门禁不检查「多余的顶层键」——上文 §14 表里那行「门禁报顶层键数量不对」是不成立的**

`validate_model_data.py` 的顶层检查只有这一句：

```python
for k in TOP_KEYS:
    if k not in rec:                      # 只问「必备键在不在」
        errors.append(f"缺顶层必备键 `{k}`")
```

它**不问「有没有多余的键」**，也完全不校验嵌套层的键名。所以把 `positioning`/`context_window`/`access` 写到顶层，门禁照样 ERROR 0。

实测漏网的 2 条：`google:gemini-1-0-pro-001:base`、`nvidia:llama-nemotron-ultra-253b:base`
——后者的 `positioning=["旗舰","推理增强"]`、`context_window`、`deployment` 全卡在顶层，
按 schema 路径（`basic_info.positioning`）读出来是 null，**数据真实存在但对下游不可见**。
另有 21 条（2.2%）含非规范嵌套键（`basic_info.name`/`developer`、`architecture.parameters_total` 等）。

> 2026-08-29 已给门禁补上这两项检查，**级别为 WARN**（不改动既有 ERROR 验收口径）。

**15.2 `intermediate/roster.jsonl` 不是采集名册**

它是阶段 0 的 v1 差异清单（506 行），从未随 M 型扩容更新，702 条里有 444 条不在其中。
现已改名 `roster_v1diff_DEPRECATED.*` 并加了横幅。**名册唯一权威 = `docs/batch_claim_ledger.jsonl`** 的 `models[].model_id` 去重。

踩过的坑：用 roster 比对「骨架残留」得到 80 条（错），用 ledger 得到 26 条（对）。

**15.3 「ERROR 0」的正确读法**

它表示「**无已检项违规**」，不表示 schema 干净、也不表示数据齐全。同理 `model_id 存在于主库` 是恒真判据（骨架早已预填，见 §13），
判断是否真的入库完成，**只能看 `meta.collected_at` 是否已离开骨架快照日 `2026-08-24`**。

---

### 16. 【2026-08-29 整改轮新增】schema 转正三项 + 定价置信度改为 ERROR 级

**16.1 三个字段从「野键」转正为规范键**（`validate_model_data.py` 的 `SCHEMA_BLOCK_KEYS` 已加白名单）

| 字段 | 类型 | 取值口径 |
|---|---|---|
| `basic_info.license` | 自由文本 | 官方模型卡/HF 仓库 LICENSE 原文；闭源模型写「闭源 API」。**严禁凭 `open_weights` 反推**，未采集填 `null` |
| `architecture.max_output_tokens` | 整数 | 官方单次最大输出 token 数，**与 `context_window_tokens` 是两个字段，勿混填** |
| `architecture.reasoning_model` | 布尔 | 是否推理型/思考型；厂商未声明填 `null`，勿按「能力强」臆断 |

转正原因：主库已有 8/4/4 条实值在用。`incoming/models/_samples/` 两个权威样例也已同步补上这三个键（值先置 `null`）。
在白名单加上它们之前，下游按规范路径读取会得到 null——**数据真实存在但不可见**，与 §15.1 同一类失效。

**16.2 `pricing.confidence` 现在是 ERROR 级检查**（此前只查 `benchmarks.*.confidence`，定价侧长期无人管）

```python
pconf = pricing.get("confidence")
if pconf is not None and pconf not in CONFIDENCE_ENUM:
    errors.append(...)
```

受控词表定义在 `docs/prompt.md` 的 `confidence` 枚举行（现为 442 行）：`T0 / T0-自报 / T0-自报-转述 / T1 / T2 / T3 / T4`；未采集填 `null`（`null` 不算越界）。
历史漏网的 4 条越界值 `中 / 低 / high / N/A` 已在 D2 整改归位。
另注意：`T0-自报-转述` 按决策 2（prompt.md:267）**只适用于 benchmark 自报分**，出现在 pricing 上属于误用，一律降级。

**16.3 踩过的坑：权威样例自己带着 3 个 ERROR**

`incoming/models/_samples/sample_openai_gpt-5-5-none.jsonl` 的 `positioning`
原本是 `["旗舰","智能体","编码","知识工作"]`——后三个全是越界标签，**样例自己过不了门禁**。
subagent 是照抄样例的，等于把错误标签批量复制。已按通用规范 §8.2-9 修正为 `["旗舰","工具调用增强"]`
（`智能体`/`编码`→`工具调用增强`；`知识工作` 是纯场景描述，**删除而非映射**）。

> 教训：改白名单或改样例后，必须把样例自己喂给门禁复跑。样例 ERROR 0 且漂移 0 才算闭环。

**16.4 「未披露」字面判定已放宽为词序无关**

原规则 `"未披露" not in notes`，匹配不到同样合法的 **「未官方披露」**（误报 4 条，含权威样例）。
现改为 `NOT_DISCLOSED_RE = 未[^\s，。；;、]{0,3}披露|待补`，不允许跨越句读。

仍然成立的通则：**门禁里凡是靠 notes 字面判定的规则，都是「文案契约」而不是语义检查**——
写 notes 时优先套用受控措辞；改措辞前先想清楚会不会触发误报（D4 清样板句时正是这条咬人，见 §14 第 2 点）。

**16.5 新规则 4.2：`pricing.source_type` 声称无价却仍挂着价格 → WARN**

门禁此前只查 `source_type` 的**键名**，不查它的**语义**，于是「标签说查无官方价、值却填着 $0.65/$2.75」
这类自相矛盾能一路通过验收。2026-08-29 补上（措辞清单见 `NO_PRICE_CLAIMS`），命中即要求二选一：改标签或剔 null。

同批整改（D5）：6 条 —— 3 条按记录自身证据剔 null
（`meta:meta-llama-3-70b-instruct` 价格实为 replicate 托管价，而它自己的 notes 写明「第三方托管价不混录」；
`zhipu:chatglm2-6b` / `zhipu:autoglm-rumination` 的 0.0 属以零冒充「查无此价」，违红线 1），
3 条更正 `source_type` 文案（`aya-expanse-32b` 旧标签过期、`minimax-m2-1` 把 `T0` 写进了 source_type 槽、
`stepfun:step-3-5-flash` 写成英文 `official`）。

**仍留 3 条 WARN 未清，且刻意不清**——需要外部核实才能定方向，不能靠猜：
`meta:muse-spark-1-1` / `muse-spark-1-2`（价来自头条号 UGC，且 notes 是从 llama 记录复制的样板、与本模型无关）、
`microsoft:mai-code-1-flash`（notes 自述「无法精确核实，不硬填」却仍填了 UGC 价）。
另注意 `zhipu:glm-4-7-flash` 的 0.0/0.0 **是真价不是残留**——官方定价页明列「免费」，这类真零严禁一并剔掉。

**16.6 新规则 4.3：六个价键全 null 却仍填 `currency` → WARN（D7，2026-08-29）**

口径：**无价即无币种**。留 `"USD"` 会被分析端读成「已按美元核实过、确认无价」，与红线 1「查不到不硬填」冲突。

根因不在采集人，在文档：`docs/prompt.md` 的 pricing 字段说明原文写的是 **「`currency`：默认 `"USD"`」**，
照文档写就必然产出「有币种、无价格」的记录——存量 645 条无价记录里 USD 323 / null 318 / 连 unit 也 null 4 条，
正好对半分裂（2026-08-25 那句「不伪造 USD 默认值」从未落地过）。
已改文档为「有价格时填 USD；六价键全 null 时必须 null」，用 `temp/d7_currency_null.py` 把 323 条归一
（改动 323 行 / 仅 currency 一个字段 / 前后逐条 `check_record` 无新增 ERROR），并同步改了三处采集侧文档。

`unit` 不在此约束内，继续保留 `per_million_tokens`：它是量纲声明、不携带「已核实」语义，下游做单位换算需要它一直在。

> 与 §14 的关系：§14 那类是「文案契约误报」，这一类是**文档给的默认值本身就是伪造值**——采集端没做错任何事。
> 改口径必须同时改文档，否则加多少条门禁规则都是白堵。

---

### 17. 【2026-08-29 整改轮新增】「存疑」记录的隔离档机制（D6）

采集人在 `meta.verification_status` 里写的 **`存疑`** 是正式信号，含义是「我知道这条立不住，但按 SOP 不能自己删」。
2026-08-29 逐条复核后确认 10 条全部查无立得住的依据，经用户拍板**全部移出主库**，主库 950 → **940 条**。

**17.1 隔离档分两处，缺一不可**

| 位置 | 内容 | 作用 |
|---|---|---|
| `docs/unconfirmed_models.jsonl` | 10 条完整记录，**逐字节原样**搬出（脚本内 `assert` 了 `json.dumps` 往返等于原文） | 唯一的数据留痕 + 可复跑的门禁对象（现 ERROR 0 / WARN 8） |
| `incoming/models/_quarantine/` | 其中 4 条对应的采集源文件 + `README.md` | 挡住自动回灌，见 17.2 |

> 那 8 条 WARN 全部是 D7 新增的规则 4.3（六价键全 null 却填着 `currency="USD"`）命中归档副本自身。
> **归档文件刻意不跟着归一**——它的价值就在「与主库当时的字节完全一致」，改了就不是同一份证据了。
> 回流主库时（17.5）再按新口径修正即可。

另外 6 条在 `incoming/models/` 下**没有对应采集文件**（已按原名、§8.1 降级名、缩短名穷举核实为 0 命中），
所以 `docs/unconfirmed_models.jsonl` 那一行是它们唯一的证据。**不要清理这个文件。**

**17.2 为什么「挪进子目录」就够了**

`model_data_tool.py` 的 `merge --incoming <目录>` 展开目录用的是 **非递归** `os.listdir`
（`scripts/model_data_tool.py:1087-1091`，只取该层 `.jsonl`，且跳过 `.` 开头）。
所以 `_quarantine/` 里的文件不会被目录式合并扫到；而 `add_record` 对主库缺失的 model_id 会**直接新增**
（同文件 565-569 行），也就是说：只要文件还躺在 `incoming/models/` 顶层，任何一次目录合并都会把这 10 条**静默复活**。
子目录是一道不需要改代码的屏障——`_samples/` 用的也是同一个原理。

反过来说，显式点名（`--incoming incoming/models/_quarantine/xxx.jsonl` 或 `@清单`）**是能绕过这道屏障的**，
所以移动文件只是防误操作，真正的判据是 `docs/unconfirmed_models.jsonl` 里那条「查无依据」的记录。

**17.3 花名册口径重新基线（重要，别让进度回退）**

`docs/batch_claim_ledger.jsonl` 的 702 个 model_id 现在这样分布：**主库 692 + 隔离档 10 + 缺失 0**。
「702/702 采集完毕」这句话仍然成立，但**不要**因为主库只剩 692 条就把这 10 个当「漏采」重新派发重采——
它们不是没采到，是采到了且复核后判为立不住。要重开只有在**拿到新的官方证据**时，按 17.5 走。

**17.4 `ledger.submitted_files` 不能当存在性判据**

全库 1066 条 `submitted_files` 里有 **791 条指向不存在的路径**（本整改前就如此），且混着带/不带
`incoming/models/` 前缀两种写法。历史惯例是合并后不保留源文件。判断「某模型的采集成果还在不在」，
请查主库 + `docs/unconfirmed_models.jsonl`，不要查 ledger 的这个字段。

**17.5 如果将来确实拿到官方证据，怎么放回来**

1. 读 `docs/unconfirmed_models.jsonl` 取出该条，改字段并补 `source_url` / `effective_date` / 合规 `confidence`；
2. 单文件跑门禁，**ERROR 必须 0**；
3. 用 `merge --incoming <该文件> --on-both source_wins --apply`（显式点名，别指望目录扫描），或 `set` 子命令改主库；
4. 从 `docs/unconfirmed_models.jsonl` 删掉对应行，并在 `incoming/models/_quarantine/README.md` 的留痕区记一句。

> 通用教训：主库「有一条记录」和「这条记录可信」是两件事。采集人的存疑标记必须有人在收尾时消费掉，
> 否则它会以 WARN 的形式永远留在库里，最后没人知道这 10 条到底算不算数。

---

### 18. 【2026-08-29 最严重发现】补合并用 `--on-array replace` 静默抹掉了已采集跑分

**事实**：commit `85b9fae`（阶段 3「补合并 277 条从未入库的采集成果」）执行 §13 那条标准命令时，
`--on-array replace` 把主库里**已经采到的跑分条目整组覆盖成空**。两种口径都量了一遍：

| 口径 | 记录数 | 条目数 | 构成 |
|---|---|---|---|
| 数组长度缩水（取证脚本） | 75 | 196 | independent 164 / arena_elo 29 / self_reported 3 |
| 按主键比对（恢复脚本，更宽） | 81 | 215 | 含长度没变但具体条目被换掉的记录 |
| **回补后确认的真实损失** | **81** | **206** | independent 177 / arena_elo 29（`85b9fae` 造成） |

> 另有 1 条 `independent`（`eurus-2-7b-prime` 的 GPQA Diamond T1）在 **d922620 之前**就丢了、基线 943b6f2 里本来也没有，
> 恢复脚本按单一基线看不见它，是回补后复跑取证脚本才发现的 ⇒ 一并找回，**累计回补 82 条记录 / 207 个条目**。
> 教训：恢复基线只能保证「基线之后」的损失被找回，务必用「全历史最大长度」复扫一遍。

> 第 2 行比第 3 行多的 9 条全在 `self_reported`，且全部属于 `nvidia:llama-nemotron-ultra-253b:base` 一条记录。
> 逐条核对后判定**不算损失**：943b6f2 那 9 条是 legacy `name`/`mode` 写法（其中 8 条同数组内逐字重复），
> 当前库里的 6 条是后来重新核实的 canonical `benchmark`/`sub_benchmark` + `confidence` 写法，
> 同名基准分数还与之矛盾 —— 那次 replace 对这条记录是**合法的 schema 升级**。
> 教训：**「数组变短了」只是嫌疑，不等于数据被破坏**；回补前必须逐条比对新旧表示是否同一测量。

丢的不是 HF 骨架填充值，是**前几轮人工采集的真数据**：例如 `cohere:cohere-command-a` 的三条
Arena Elo（DataLearner 镜像 + 原始来源说明 + T1 + `is_primary` 标注）被整体清零。

**机制**：采集分片常常只填 `self_reported`，`independent` / `arena_elo` 留 `[]`。
`_merge_value` 里「来源为空就不动」只判 `source is None`，**空容器不算空**，于是空数组直接进
`_merge_list` 的 REPLACE 分支把目标整组替换掉。合并计划里连一行提示都没有。

**三条本可以早点发现的线索**（都值得记住）：

1. **填充率反常**：质检报告 §3.2 当时记录的「花名册 702 的 independent 覆盖反而低于 v1 遗留」，
   真实原因就是这次覆盖，不是样本构成差异。覆盖后全库 `independent>0` 只剩 22%，
   而未被动过的 08-24 骨架记录是 72%（59/82）——同一年代同源数据不该差三倍。
   回补 207 个条目后升到 **33.8%（318/940）**，差距仍在但已回到可解释区间。
2. **验收口径盲区**：阶段 3 的验收是「ERROR 数量」+「记录数不变」。数组内容被清空既不报 ERROR
   也不改记录数，所以合并「成功」了。**任何只数记录条数的验收都看不见字段级破坏。**
3. **WARN 下降当好消息**：那次合并后 WARN 684→678。跑分条目变少 → 「自报分 source_type 未含自报」
   这类 WARN 自然变少。**WARN 下降要先问「是修好了还是删掉了」，不能直接记成绩。**

**已落地的修复**：

- `scripts/model_data_tool.py` 加**空数组保护**：`on_array=replace` 且来源为空、目标非空时保留目标，
  并在计划里显式记一条 `skip`；确要清空必须传新参数 `--allow-empty-replace`。
  `describe()` 会打印 `on_array=replace(空数组保护:开/关)`，让每次合并计划都能审计到这个开关。
- 验证脚本 `temp/d8_verify_empty_array_guard.py`：复现事故场景，断言保护开启时骨架条目保住且来源真实数据仍写入、
  显式放行时仍可清空。**注意**：验证合并结果必须取 `_merge_into` 的返回值——
  `merge_incoming(dry_run=True)` 的结果只在 `working` 深拷贝里，读 `store.records` 会得到未合并的目标，
  断言会因错误的原因通过（我第一版就踩了这个）。
- 取证脚本 `temp/d8_benchmark_loss_forensics.py`：遍历全部改过主库的提交，对每个 model_id 记录三个数组的
  **历史最大长度**，与当前比较 ⇒ 找出所有「曾经有、现在没有」的数组缩水。这个方法是通用的，
  下次合并验收直接跑它。

**恢复（已执行）**：`temp/d8_restore_benchmarks.py --apply` 按主键**只回补不覆盖**——把基线提交里有、
当前没有的条目并回来，当前已有条目一律不动。保险含「序列化风格全库一致才允许整体重序列化」
「除 benchmarks 外语义逐字节等价」「逐条前后 `check_record` 不得新增 ERROR」。
随后 `temp/d8_fix_over_restore.py` 撤掉多回补的 9 条（见上表下的说明），
`temp/d8_restore_eurus_independent.py` 找回基线之外丢的 1 条，**累计净回补 82 条记录 / 207 个条目**。

回补后复检（与 HEAD 逐条比对）：非 `benchmarks` 字段改动 0、数组缩水 0、主键重复数与回补前持平 163、
`arena_elo` 多 `is_primary` 仍只有早于事故的 `alibaba:qwen-3-8-max` 一条、门禁 940 条 ERROR 0 / WARN 689。
全历史取证复扫现报 **1 条缩水**，即上表登记过的 `nvidia:llama-nemotron-ultra-253b` 合法升级 —— 属预期例外，不是未修完。

> **遗留：跨 schema 重复。** 主键 `(benchmark, config)` 认不出 legacy `name` 写法的条目（一律算 `("None","None")`），
> 所以同名同测量的两条会并存。实测 207 条里（多出的那 1 条落进的是空数组，不可能撞）只有 5 条与 HEAD 同名、
> 2 条名与分都撞
> （如 `openai:gpt-5-2-2025-12-11-xhigh:base` 的 GPQA Diamond 0.914：T1 直连 epoch.ai 一条 + T3 经 token.app 转述一条）。
> 两条各自带完整来源，**刻意不自动删**——去重口径属于「同名基准冲突取谁」的拍板项，已进待办队列。
> 造成本类撞车（主键认不出 legacy 写法）的根因已由 **§19 的 D9 归一化部分消除**（仅 `name` 一种写法，
> 尚余 57 条），剩下的才是真实测量冲突
> （D9 改动记录内 6 个数组；全库独立复扫 22 个数组 / 39 组，见 §19 末段）。

> **收尾必做自检**（写进 SOP）：每次 `merge --apply` 或回补之后跑三条，都要看结果而不是只看退出码：
>
> 1. `python temp/d8_benchmark_loss_forensics.py` —— 要求「缩水条目数 0」；
>    非 0 时逐条判定是破坏还是**合法 schema 升级**，属后者的登记进 §18 例外清单（现仅 1 条：`nvidia:llama-nemotron-ultra-253b`）；
> 2. `python temp/d8_check_restore_conflicts.py <写入前的 ref>` —— 把新增条目按「查无同名 / 同名同分 / 同名不同分」分类。
>    同名同分是纯重复嫌疑，同名不同分是真实的测量冲突；两者都不自动处置，只列清单等拍板。
> 3. `python temp/d9_residual_scan.py` —— **全库**三个口径：缺 canonical 主键的条目（任何写法）、
>    精确主键重复、`config` 语义混用造成的近似重复。必须独立跑：前两条命令都只覆盖「本次改动范围」，
>    而复扫 D9 才发现全库重复是 22 个数组、不是脚本自报的 6 个。

---

### 19. 【D9】`benchmarks` 条目多种写法并存：不是格式问题，是去重失效

**事实（先量后写）**：主库跑分条目一直有四种 schema 并存 ——

| 写法 | 条数 | 分布 | 本步处置 |
|---|---|---|---|
| legacy：只有 `name` | **1293** | self_reported 1241 / independent 50 / **arena_elo 2** | ✅ 已归一 |
| canonical：`benchmark`（arena_elo 为 `sub_benchmark`） | 3799 | 其余记录 | 不动 |
| `benchmark_name` | 30 | self_reported 29（8 条记录）+ independent 1 | ⬜ **D9 范围外，未处理** |
| `metric_name` | 23 | self_reported，仅 2 条记录 | ⬜ **同上** |
| `arena_elo` 误用 `benchmark` | 4 | `google:gemini-exp:1114` 一条记录 | ⬜ **同上** |
| 同时带 `benchmark` 与 `name` | 8 | self_reported（6 条两键同值、2 条不同值） | ⬜ 主键已在，去重不失效，仅冗余 |

受影响记录 156 条。legacy 行**不带** `mode` 键（`mode` 是 §18 里 nemotron 那 9 条特有的写法），
所以本步是纯改名，不含语义映射。

> **范围声明（写盘后复查才知道的）**：D9 的拍板原文是「legacy `name` 写法全量归一」，脚本因此按 `"name" in item` 圈定范围，
> 上表后四行**从未进入范围**，也就一直留着 57 个条目（11 条记录）主键算不出、去重照样失效。
> 更糟的是**规则 6.1 只查 `name`，对这 57 条完全沉默** —— 「归一后门禁 WARN 没涨」不等于「写法已统一」。
> 教训：**归一化脚本的匹配条件就是它的盲区**，收尾必须另跑一次「缺 canonical 主键的全部条目」的独立计数，
> 不能拿脚本自己的命中数当残留数。

**为什么必须修**：两套写法并存的代价不是「不好看」，是**合并与去重静默失效**——
合并主键 `(benchmark, config)` 对 legacy 行永远算出 `("None","None")`，
于是同一次测量可以并存两份而不被任何检查发现。D8 回补时撞出来的那 5 条就是这么来的。

**拍板与做法**（2026-08-30 用户拍板「全量机械归一」）：`temp/d9_normalize_benchmark_keys.py`，三条硬约束：

1. **可逆**：按记录下来的位置把主键换回 `name`，结果必须与原始行逐字节相等。
   这才是本步真正的验收 —— 写盘后又用 `git show HEAD` 反向核对一遍，156 行全部还原成功、值零改动。
2. **键序保持**：在原位置改名，不追加到末尾，否则 diff 里全是无关抖动。
3. 逐条前后 `check_record` 不得新增 ERROR；整体重序列化前先证明 940 行序列化风格一致。

**踩到的坑**：一开始按「一律换成 `benchmark`」写，预期 1291 条却数出 1293 ——
差的 2 条在 `arena_elo`，而 **`arena_elo` 的 canonical 主键是 `sub_benchmark` 不是 `benchmark`**。
是数量对不上逼出了这个细节；若当时把预期改成 1293 收工，就会静默留下 2 条键名写错、门禁又查不出的记录。
**归一化脚本的目标键必须按数组分别定义；条数对不上绝不能用「改预期数」来消音。**

**防回归**：门禁新增规则 6.1（WARN）—— 条目缺本数组主键、只有 `name` 即报。
负对照实测：拿归一前的备份跑门禁得 **WARN 1982 = 689 + 1293**，逐条命中；
归一后现库仍是 689，说明这条规则只在 legacy 写法存在时才开口，不会长期刷噪声。
> 规则暂只覆盖 `name`。要扩成「缺 canonical 主键即报」必须**等上表那 57 条也归一之后**再扩——
> 先扩规则会让 WARN 凭空多 57 条，把 689 这个贯穿 D1–D9 的验收基线冲花，反而看不清后续整改有没有引入新问题。
> 顺序应当是「先清数据、再收紧检查」，而不是反过来用新增 WARN 给存量数据留档。

**归一化揭出的新问题**：改名后 6 个 `self_reported` 数组出现真实的 `(benchmark, config)` 重复
—— 此前被 `("None","None")` 掩盖。**同名基准分数冲突取哪一条**是独立拍板项，本次未自动删。

> 这个 6 只是 **D9 脚本改动范围内的数**（脚本只在它改过的 156 条记录里查重）。全库独立复扫是
> **22 个数组 / 39 组重复键**：35 组同名不同分、4 组同名同分。典型的如同一基准挂着 3 个分数而 `config` 全为 `null`
> （`alibaba:qwen3-coder-480b-a35b` 的 SWE-bench Verified 0.658/0.67/0.696、
> `deepseek-…:deepseekmath-7b` 的 MATH 0.362/0.517/0.609）——多数更像**该用 `config`/`date`/`notes` 区分的不同测量**，
> 而不是「同一次测量记了两遍」。这又是一次「拿脚本自己的命中数当全库残留数」，与上面范围声明是同一个毛病：
> **查重要求独立跑一遍全库，不能复用归一化脚本的中间结果。**
> 独立复扫脚本：`temp/d9_residual_scan.py`，一次给三个口径 —— 缺 canonical 主键的条目（57）、
> 精确主键重复（22 数组 / 39 组）、以及**反方向**的近似重复：**7 组** 同基准、分数一模一样、
> 只因 `config` 里写了不同来源名而并存（`alibaba:qwen2-5-max` 的 GPQA Diamond 0.587，
> config 为 `default（benched.ai）` 与 `default（llmbase）`；§18 那对 T1/T3 的 GPQA Diamond 0.914
> 也是靠 `config` `null` vs `"xhigh"` 错开的）。
> 也就是说 `config` 现在同时被当成**评测配置**和**来源标注**用，语义不统一时去重两个方向都会失效：
> 该合的（同一次测量记两家转述）合不上，不该合的（airline / retail 两个子集）看着像重复。

---

## 11. 并发上限（429）的处理

派发 subagent 采集时可能撞上平台级并发上限，报错形如 `429 queue.userLimit.title` 或 `429 queue.waiting.title`。**这是账号/平台维度的限制，与项目配置无关，立刻重试通常仍失败。**

应对顺序：

1. **降低并发**：一次派 8 个很容易触发，降到一次 3-4 个可正常跑；再降到 1 个若仍 429，说明上限已被占满（可能有上一批 subagent 尚未释放）
2. **不要干等**：等待期间先把已完成批次的验收与 push 做掉
3. **仍无法派发时，必须回退**：已 `claimed` 但采集不出来的批次，**一律改回 `pending` 并清空 `claimed_by` / `claimed_at`**，notes 留痕「平台并发上限，退回待认领」。理由同 §7——留着 claimed 会虚占进度，其他 agent 不会接管 claimed 批次，等于阻塞
4. 回退后向用户报告限流情况，等上限释放后重新认领即可（批次回到 pending 后数据与流程无损）

> 实测：一轮连续派发 8 个 → 陆续出现 429；降到 3 个一组正常；后期完全占满时连 1 个都派不出，此时应回退收尾而非反复重试。

---

## 10. 维护

- 维护者：WorkBuddy 平台主 agent
- 原则：**只增不删**，修改在文末留痕
- 触发修改：发现新的 WorkBuddy 环境坑、git 路径变化、接管判定规则调整

### 留痕

- 2026-08-28 v1 首发。来源：workbuddy-01 三批次烂尾（15 模型未提交未入库）+ 本机 git 与 PortableGit 凭据助手不兼容导致 push 弹窗。确立红线 A（本机 git）、红线 B（`git add -f`）、§7 防烂尾接管规则与结束前强制自检。
- 2026-08-28 v1.1 首次实战验证（agent `workbuddy-02`），三项结论：①红线 A 有效——本机 git 一次性推送 13 个堆积 commit 全程静默无弹窗；②红线 B 的缺口比预想大——除烂尾批次外，另有 5 个已 submitted 批次共 25 个文件因漏 `add -f` 从未入库；③§7.2「未超时他人 claimed 不抢」判断正确——trae-cn-glmm 认领的 b33w1/b44w1 在其 claim 后约 1 小时内自行完成提交，抢工会造成重复劳动。另补 §9 一条 `git ls-files` grep 前缀的实测坑。

> 排查经验补充：判断「磁盘缺失的采集文件是否真丢」时，先查主库 `model_data_v2.jsonl` 是否已含该 model_id。本次 82 个 submitted 批次中有 262 个文件不在磁盘，但逐一比对后确认 **262 个全部已在主库**（0 真丢失），属「采集→合并→文件未保留」的正常链路，无需重采。避免据此误判为数据丢失而重复劳动。
- 2026-08-28 v1.2：新增 §8.1 超长文件名降级规则（Windows 260 上限）与 §11 并发上限（429）处理。本轮（agent `workbuddy-02`）累计完成 18 批 61 模型采集 + 40 个历史文件收尾入库，全程本机 git 零弹窗；末期遇平台 subagent 并发上限，已按 §11 将 8 批回退 pending 并留痕，未留 claimed 残留。
- 2026-08-29 v1.3（agent `workbuddy-03`，纯收尾轮，未采集、未 push）：① 补 §8.1 的 `core.longpaths` 坑——降级命名只保证**写盘**，250~260 字符的路径仍会让 `git add -f` 失败，必须 `git config core.longpaths true`；② 本轮把 89 个「已 submitted 但从未入库」的采集文件补入 git（commit `9503626`），全部门禁 ERROR=0，数据早已合并进主库（0 丢失）。加上 v1.1/v1.2 的 36+40 个，历史漏 `add -f` 的缺口至此基本扫清。
  - **收尾轮的方法论（可复用）**：`git ls-files incoming/models/` 与磁盘 `incoming/models/*.jsonl` 求差集 → 用 `batch_id.split('-')[0]` 短标识反查 ledger（降级命名的文件前缀不含完整 batch_id，直接 `split('__')[0]` 会查不到，判成「无主文件」）→ 按 ledger status 分流，`submitted` 的才收，`claimed` 的一律不动 → 逐个 `git add -f`（`xargs` 会报 environment too large，用 Python `subprocess`）→ 提交前 `git diff --cached --name-only` 确认 index 里没有别人的东西。
  - **本轮实测的停滞判定**：12 个 `claimed` 批次全部停在 05:39~05:43，7 小时零新提交；其中 8 个文件已落盘（7 个数据已进主库、1 个是**写了一半的截断 JSON**），4 个连文件都没有。判定「已 submitted 未入库」和「在途未完成」时，**必须逐文件解析 JSON 是否完整**，只看文件大小会漏掉截断文件（本例 7.4KB 看着正常，实际字符串未闭合）。
- 2026-08-29 v1.4（agent `workbuddy-03`，同日第二阶段——用户确认 3 个 Trae agent **额度超限集体停摆**后接管）：
  - 新增 **§7.2 末行 + §7.4 接管三分类**：用户确认停摆后超时规则不再适用，按「文件完整 / 文件截断 / 零产出」三类分别处置。核心是**逐文件 `json.loads`**，并按 `submitted_at` 小时分布辅助判定集体停摆。
  - 新增 **§9 一条 + §12**：`models_data_tool.py` **没有单字段写入命令**，主库只能靠 `merge --apply` 改；因此「主库 ERROR=0」不等于源文件合规——越界 `positioning` 在合并时被静默丢成 `[]`。改主库收益 < 风险时宁可不动，留给阶段 3。
  - **接管战绩**：7 批补提交（含 3 批越界标签修复后过门禁）、5 批退回 pending（4 批零产出 + 1 批截断文件隔离）、**claimed 残留清零**、工作区转干净。进度 676 → **683 / 702（97.3%）**。
  - **一个流程性结论**：本轮共发现 **96 个**（89+7）已合并进主库却从未入库的源文件。说明现有合并流程**既不入库源文件、也不清理它们**——所以「磁盘有文件」和「文件在仓库里」是两件事，每个采集阶段结束都必须单独扫一遍 `git ls-files` 差集，否则这些数据只有主库一条命。
- 2026-08-29 v1.5（用户提议「改一下 tool 脚本方便编辑」后落地）：给 `scripts/model_data_tool.py` 新增 **`set` 子命令**，补上主库单字段编辑这条缺失路径。设计沿用项目既有哲学——**默认 dry-run、`--apply` 才写、自动备份、原子替换、all-or-nothing**，另加两条保险：`--expect` 乐观锁、`--create-path` 默认拒绝（不静默造结构），写入后自动调 `validate_model_data.check_record` 复检并打印 ERROR/WARN 前后差值。详见 **§12**（§12.1 保留了改造前的历史结论作留痕）。
  - 顺带把 §7.4 里「主库 positioning 被吞、但没敢动主库」的遗留项了结：用 `set` 把 `carrotai` 的 `positioning` 从 `[]` 补回 `["工具调用增强"]`，全库仍 ERROR 0。
  - 给后来人的提醒：改主库前先 `cp` 一份到 `/backups/`，因为工具自动生成的 `<file>.bak` **每次写入都会覆盖**，不是历史快照。
- 2026-08-29 v1.6（agent `workbuddy-04` 采集轮，**花名册 702 个模型全部采集完毕**）：
  - 新增 **§1.5 死代理坑**：环境变量 `HTTP_PROXY/HTTPS_PROXY` 指向 `127.0.0.1:9910` 但该进程常不在运行，git 会伪装成「网络不通」。`unset HTTP_PROXY HTTPS_PROXY` 后直连即通。另注：排查时**不要** `env | grep proxy` 全量打印。
  - 新增 **§13 合并是「填骨架」不是「加记录」**：主库 950 条里 702 条骨架已由 HF API 快照预填，合并必须用 `--on-both source_wins`，用 `conflict` 会 0 写入。这条如果不知道，新人会卡死在「为什么全冲突」。
  - 新增 **§14 门禁三个高频踩点**：release_date 只写年份会 ERROR（须 YYYY-MM/YYYY-MM-DD，否则记 null）；参数量为空时 notes 必须含**字面**「未披露」或「待补」（子串匹配，近义写法不算）；标称上下文需注明「待测」。
  - 新增 **§7.4 之外的实战补充**：认领批次后**必须先 `git add docs/batch_claim_ledger.jsonl` 再 commit**——只改文件不 add，git 会报「no changes added to commit」静默失败，批次的认领状态根本没进仓库。
  - **占位记录条款（§8.2-14）的两个实战案例**：① `omni-epic` 经核查**不是语言模型**，而是调用基础模型生成 RL 环境的开放式算法框架；② `digivio`（上海数聚威）**无任何可归因的公开信息**（搜到的 Digivo/Divio/Digievo 全是同名不同主体）。两者都按占位记录落盘（门禁通过、ledger 照常 submitted），并在 notes 里写明「建议高端合并阶段决定保留/改指/删除」，而不是编造字段、也不是退回 pending 让别人重复踩坑。
  - **本轮战绩**：接手时剩余 26 个模型，4 波共采集 **16 批 19 个模型**（k2-think / sailor-7b-chat / fugaku-llm / eurus-2-7b-prime / seed-diffusion-preview / omni-epic / sahabat-ai / teuken-7b / rwkv-5-7b / rwkv-6-3b / metamath-70b / metamath-7b / index-1-9b / jinshi / brain2qwerty / digivio / rnnsearch-50 / neural-lm / nplm），全部 ERROR=0，合并 0 冲突，每波单独 commit+push。**全库 305/305 批次 submitted，702/702 模型入主库，0 缺失，主库 950 条 ERROR 0。**
- 2026-08-29 v1.7（用户发起的**全库整改轮**，不采集、只修质量与仓库卫生）：新增 §15（三处文档与代码不符）、§16（schema 转正 3 字段 + `pricing.confidence` 升 ERROR + 规则 4.2 + 文案契约通则）、§17（「存疑」记录隔离档机制）。数据侧 D1-D6 六批整改，脚本一律放 `temp/`（gitignore）且每步带「改动条数必须等于预期」和「逐条前后跑 `check_record`，不得新增 ERROR」两道保险。仓库侧清死脚本、删可再生 HF 缓存、失效名册改名加弃用说明。**主库 950 → 940 条，ERROR 0 / WARN 689 / 结构漂移 0。**
- 2026-08-29 v1.8（整改轮 D7 + 合并安全取证）：新增 **§16.6**（门禁规则 4.3「无价即无币种」，323 条 `currency` 归一为 null，根因是 prompt.md 字段说明写着「默认 USD」）、**§13 空数组危险标注**、**§18**（本轮最严重发现：`85b9fae` 的补合并用 `--on-array replace` 静默抹掉 81 条记录 / 215 个已采集跑分条目；含三条本可早发现的线索、取证方法、恢复脚本现状）。给 `model_data_tool.py` 的 replace 分支加了**空数组保护**并新增 `--allow-empty-replace` 显式放行位。顺带修 `incoming/models/_m_context.md` 里写死的 `meta.collected_at = "2026-08-25"`（照抄会让全库采集时间戳失真）。
- 2026-08-30 v1.9（D8 跑分回补执行完毕）：§18 的恢复脚本 `--apply` 已跑，并用 `temp/d8_fix_over_restore.py` 撤掉多回补的 9 条 legacy `self_reported`（该记录的数组变短实为合法 schema 升级，不是损失）；回补后复跑全历史取证又发现 1 条早于恢复基线丢失的 T1 条目（单一基线看不见它），由 `temp/d8_restore_eurus_independent.py` 找回。**累计净回补 82 条记录 / 207 个条目**，全库 `independent>0` 从 22% 升到 33.8%，取证复扫仅剩 1 条已登记的合法升级例外。§18 表格补第三种口径、收尾自检补 `temp/d8_check_restore_conflicts.py`（跨 schema 同名/同分冲突扫描），并开出一个新待拍板项：同名基准冲突取哪一条 + 全库 1293 条 legacy `name` 写法条目是否归一化（该项已由 v2.0 完成）。
- 2026-08-30 v2.0（整改轮 D9：`benchmarks` 条目 schema 归一）：新增 **§19**。全库 1293 条 legacy `name` 写法条目（self_reported 1241 / independent 50 / arena_elo 2，涉及 156 条记录）机械归一为 canonical 主键 —— 前两个数组换 `benchmark`、`arena_elo` 换 `sub_benchmark`。改完用 `git show HEAD` 反向归一核对，156 行全部逐字节还原、值零改动；门禁新增规则 6.1 防回归，负对照用归一前备份实测 WARN 1982 = 689 + 1293。归一后揭出 6 个 `self_reported` 数组存在真实 `(benchmark, config)` 重复，转入「同名基准分数冲突取哪一条」待拍板队列。**主库 940 条 ERROR 0 / WARN 689 不变。**
  - **写盘后复查修正两处口径**（都记进 §19）：① D9 按 `"name" in item` 圈范围，所以另有 **57 条（11 条记录）** 用 `benchmark_name` / `metric_name` / `arena_elo` 误用 `benchmark`，主键照样算不出、规则 6.1 照样沉默，**未归一**；② 主键重复只在改动记录内数出 6 个数组，**全库独立复扫是 22 个数组 / 39 组**（35 组同名不同分、4 组同名同分）。教训：归一化脚本的匹配条件就是它的盲区，残留数与冲突数必须独立跑全库。
