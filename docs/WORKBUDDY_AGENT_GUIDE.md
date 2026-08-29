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

# ② Python 命令统一加 UTF8 前缀（Windows GBK 控制台会崩）
PYTHONUTF8=1 python scripts/validate_model_data.py <file>

# ③ 提交采集文件时必须 -f（.gitignore 第 29 行忽略了 incoming/models/*.jsonl）
git add -f incoming/models/<batch_id>__*.jsonl

# ④ 作业顺序：先收尾自己平台上未提交的批次，再认领新批次
# ⑤ 每批完成后立即 push，不要攒着 —— 烂尾比慢更严重
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

### 12. 主库写入的唯一路径（重要）

`scripts/model_data_tool.py` 的子命令只有 `read` / `compare` / `table` / `list`（**只读**）+ `merge`（默认 dry-run，`--apply` 才写）。**没有单字段 set / update 命令。**

- 想修主库里某个已合并记录的单个字段，**只能重跑 `merge --apply`**，没有其他正当路径
- 但重跑 merge 会用源文件覆盖目标记录，可能把合并时自动补全的骨架结构冲掉
- 因此：**改主库的收益 < 风险时，宁可不动，留到阶段 3 质检统一处理**，并在交接文档里写明

> 本轮实例：3 条记录的 `positioning` 被合并工具丢成 `[]`（源文件用了越界标签）。只修了源文件让它过门禁，主库没动——全库 950 条里本就有 359 条 `positioning` 为空（37.8%），为 1 条记录重跑 merge 不划算。
| Python 报 UnicodeEncodeError | GBK 控制台 | 命令前加 `PYTHONUTF8=1` |
| 门禁报 positioning 越界 | 用了受控词表外的标签 | 六值枚举：`旗舰/中端/轻量/推理增强/多模态/工具调用增强`，越界标签按通用规范 §8.2-9 映射或删除 |
| 门禁报顶层键数量不对 | `access` 被提到顶层 | `access` 必须嵌在 `basic_info.access` 内；8 个顶层键固定 |
| subagent 返回空但疑似已写盘 | Task 结果丢失（发生率约 40%） | **先查磁盘再决定是否重派**，不要盲目重跑 |
| `push` 被拒（远程有新 commit） | 被其他平台抢先 | `git pull --rebase`，检查自己 claim 的批次是否被抢；被抢则放弃该批，取下一批 pending |
| `git ls-files \| grep <batch_id>` 查不到刚提交的文件 | grep 把 `^` 锚在了行首，但输出行首是 `incoming/models/` | 写成 `git ls-files incoming/models/ \| grep "incoming/models/<batch_id>__"` |
| 派发 subagent 返回 `429 queue.userLimit.title` / `429 queue.waiting.title` | 平台级并发 agent 上限，与项目无关，重试无效 | 见下方 §11 |

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
