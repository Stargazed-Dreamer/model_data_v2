# WorkBuddy Agent 专属作业规范（model_data v2）

> **本文档读者**：在 WorkBuddy 平台上运行的 agent（主 agent 与它派发的 subagent）。
> **定位**：是 [`multi_platform_subagent_guide.md`](./multi_platform_subagent_guide.md)（跨平台通用规范）的**平台补丁**。通用规范里的认领协议、文件命名、12 条红线、验收 checklist 全部继续有效，本文档只补充 WorkBuddy 环境特有的坑和必须额外执行的动作。
> **冲突时**：以本文档为准（因为它记录的是本平台实测过的环境事实）。
> **建立**：2026-08-28，基于 workbuddy-01 烂尾事故复盘 + 本机 git 弹窗问题。
> **⚠ 文中 `temp/*.py` 指针不入库**：`.gitignore` 第 6 行排除了 `/temp/`，那些脚本是 D2–D19 各轮整改的**本机一次性产物**，
> 克隆本仓库的人找不到它们，这是已知且刻意保留的状态（拍板于 2026-08-30）。它们的**判据、负对照数字和验收结论全部写在了正文里**，
> 复核请按这些做，不要按文件名找脚本；需要重做同类整改时，照正文口径新写一个即可。可复用的常驻工具只有 `scripts/` 下那几个。

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
#    ↑ ⚠ replace 语义上等于「来源数组为空就清空目标」，本事故见 §18；工具已默认拦截，
#      只有显式 --allow-empty-replace 才放行。**跑分数组（benchmarks.*）的合并必须用
#      union_by_key + §18 第 5 点那串主键**，不要用 replace。

# ⑥ 作业顺序：先收尾自己平台上未提交的批次，再认领新批次
# ⑦ 每批完成后立即 push，不要攒着 —— 烂尾比慢更严重
# ⑧ 范围：**只记录模型**。训练系统 / agent 系统 / 算法框架 / 分布式训练技术不是模型，
#    遇到这种认领项不要硬填字段表，按 §23 登记后走非范围处置（历史 7 条见 docs/non_model_records.jsonl）
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
| `WARN 有效上下文大于标称上下文` | `context_window_effective_tokens` > `context_window_tokens`，几乎都是把厂商「可扩展窗口」填进了有效栏 | 最大值归位到 `context_window_tokens`，原生值与扩展手段写进 `notes`。**不要**反过来把有效栏调小去迁就标称栏。（旧规矩「有效上下文为空须标『标称值，有效上下文待测』」已于 2026-08-30 废止，见执行细则 §2） |

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
| `docs/unconfirmed_models.jsonl` | 10 条完整记录，**逐字节原样**搬出（脚本内 `assert` 了 `json.dumps` 往返等于原文） | 唯一的数据留痕 + 可复跑的门禁对象（现 ERROR 0 / WARN 23） |
| `incoming/models/_quarantine/` | 其中 4 条对应的采集源文件 + `README.md` | 挡住自动回灌，见 17.2 |

> 这 23 条 WARN 全是**规则命中归档副本自身**，分两笔：**8 条**是 D7 新增的规则 4.3（六价键全 null 却填着 `currency="USD"`），
> **15 条**是 D9/D10 的规则 6.1（`self_reported` 条目只有 `name`、缺 `benchmark` 主键）。
> **归档文件刻意不跟着归一**——它的价值就在「与主库当时的字节完全一致」，改了就不是同一份证据了。
> 这 15 条也不是 D10 扩宽规则带来的回归：拿旧的「只有 `name` 才报」窄口径扫同一份文件，命中数同样是 15。
> 回流主库时（17.5）**必须先跑 D7 的 currency 归一 + D9/D10 的条目主键归一**，否则会把这两种已结案的老问题重新带进主库。

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

`docs/batch_claim_ledger.jsonl` 的 702 个 model_id 在 **D6 之后**这样分布：**主库 692 + 隔离档 10 + 缺失 0**。
> **D14 又变了一次**：7 条自证「对象不是模型」的记录再移出主库，现为 **主库 685 + 存疑隔离 10 + 非模型 7 + 缺失 0**，
> 非模型那 7 条归档在 `docs/non_model_records.jsonl`，见 §23。本节以下所有 692 一律按 685 读。
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
> 造成本类撞车（主键认不出 legacy 写法）的根因已由 **§19 的 D9 + D10 全部消除**（`name` 1293 条 + 其余三种写法 57 条），
> 剩下的才是真实测量冲突
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
>    **D11 之后加一条判据**：精确主键重复组数必须**等于 17**（14 组 E 档 + 3 组 AA 双镜像分歧，见 §20、§21）。
>    多出任何一组，都说明这次改动把两个不同测量压到了同一个合并主键上——合并时无法裁决取哪条。
> 4. 门禁 `WARN` 现值应为 **469**（= 规则 6.2 的 17 + 其余 452；D13 废止两条「上下文须独立实测」类 WARN 前是 706，
>    D14 移出 7 条非模型记录再去掉它们自身贡献的 5 条，见 §23）。
>    规则 6.2 命中数一涨，就是新增了主键撞车；「有效上下文大于标称上下文」新增命中，就是有人把扩展窗口填错了栏（§22）。
>    **D15 起再加一条判据**：规则 1.1 / 1.2（架构两栏枚举越界）命中数必须为 **0** ——
>    非 0 说明有人把自由文本又写回了 `architecture_type`，或给 `backbone_type` 造了枚举外的值（见 §24）。
> 5. **合并主键的唯一权威写法**（三处文档曾各写一份、D11 那份还漏了 `date`，故在此收口）：
>    `--array-key benchmark config date` + `--array-key-override benchmarks.arena_elo:sub_benchmark,date benchmarks.independent:benchmark,config,source_site,date`。
>    少写 `source_site` 会让 `independent` 里不同第三方站的同名基准互相覆盖（D12 前会吃掉 33 行）。

---

### 19. 【D9 + D10】`benchmarks` 条目多种写法并存：不是格式问题，是去重失效

**事实（先量后写）**：主库跑分条目原本 **canonical 加四种非 canonical 写法并存** ——

| 写法 | 条数 | 分布 | 处置 |
|---|---|---|---|
| legacy：只有 `name` | **1293** | self_reported 1241 / independent 50 / **arena_elo 2** | ✅ D9 已归一 |
| canonical：`benchmark`（arena_elo 为 `sub_benchmark`） | 3799 | 其余记录 | 不动 |
| `benchmark_name` | 30 | self_reported 29（8 条记录）+ independent 1 | ✅ D10 已归一 |
| `metric_name` | 23 | self_reported，仅 2 条记录 | ✅ D10 已归一 |
| `arena_elo` 误用 `benchmark` | 4 | `google:gemini-exp:1114` 一条记录 | ✅ D10 已归一（→ `sub_benchmark`） |
| 同时带 `benchmark` 与 `name` | 8 | self_reported（6 条两键同值、2 条不同值） | ⬜ canonical 主键已在、去重不失效，仅冗余，未动 |

受影响记录 156 条。legacy 行**不带** `mode` 键（`mode` 是 §18 里 nemotron 那 9 条特有的写法），
所以本步是纯改名，不含语义映射。

> **范围声明（D9 写盘后复查才发现的）**：D9 的拍板原文是「legacy `name` 写法全量归一」，脚本因此按
> `"name" in item` 圈定范围，上表中间三行**从未进入范围**，于是留下 57 个条目（11 条记录）主键算不出、
> 去重照样失效；更糟的是**当时的规则 6.1 只查 `name`，对这 57 条完全沉默** ——
> 「归一后门禁 WARN 没涨」绝不等于「写法已统一」。
> 教训：**归一化脚本的匹配条件就是它的盲区**，收尾必须另跑一次「缺 canonical 主键的全部条目」的独立计数，
> 不能拿脚本自己的命中数当残留数。（这 57 条已由 D10 清掉。）

**D10（2026-08-30 用户拍板「续做到全部 57 条，之后再扩规则 6.1」）**：`temp/d10_normalize_benchmark_keys2.py`
沿用 D9 的三条保险，另加两条：① 改名前逐条人工看过值 —— 三种别名的值都是「这条测量叫什么」，
与 canonical 主键同义，所以仍是纯改名；唯一勉强的是 `vicuna-13b-v1.3` 那条 `metric_name` 的值写成了一句
指标描述，**只改键名不改值**。② 预期数**同时锁记录数 11 与条目数 57**（只锁条目数会放过「改名波及别的记录」
这类错误），并统计改前/改后主键重复数组数（**22 → 22**，说明这 57 条不与任何已归一条目撞键，不会凭空造新冲突）。

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

**防回归**：门禁规则 6.1（WARN）。D9 时只查 `name`；**D10 之后已扩成「缺本数组 canonical 主键即报」，
不论条目用 `name` / `metric_name` / `benchmark_name`，`arena_elo` 还包括误用 `benchmark`**。
负对照用两个改前备份实测：**D10 改前 WARN 746 = 689 + 57**、**D9 改前 WARN 2039 = 689 + 1293 + 57**，
逐条命中；现库回到 **689**（规则 6.1 命中 0），说明这条规则只在写法不 canonical 时才开口，不会长期刷噪声。
> 顺序是「**先清数据、再收紧检查**」：D9 时若直接把规则扩成全写法版，WARN 会凭空多 57 条，
> 把 689 这个贯穿 D1–D10 的验收基线冲花，反而看不清后续整改有没有引入新问题。
> 数据清干净之后再扩，扩完仍应回到 689 —— 这个「回到」本身就是检查生效的证据。
> （**D1–D10 期间的 689 如今是 457**：D13 废止两条上下文 WARN 后常量段下降 232 条，见 §22。
>   「回到当时的常量段」这个思路不变，目标值以 §22 末尾的现基线为准。）

**规则 6.1 的唯一已知豁免**：`docs/unconfirmed_models.jsonl`（D6 隔离档）仍留着 **15 条** legacy `name` 条目，
拿门禁跑这个文件会照样报出来（该文件现为 ERROR 0 / WARN 23 = 15 + 8 条规则 4.3 的 currency）。
**这是刻意的**：归档的作用是「与搬出主库时逐字节一致」，归一它就不是同一份证据了（见 §17.1）。
689 这个基线只统计主库，隔离档不计入（主库基线 **D11 起 703、D12 起 706、D13 起 474、D14 起 469**，见 §20、§21、§22、§23）；但**回流主库前必须先过归一脚本**，否则等于把 D9/D10 已结案的问题重新引进来。

**归一化揭出的新问题**：改名后 6 个 `self_reported` 数组出现真实的 `(benchmark, config)` 重复
—— 此前被 `("None","None")` 掩盖。**同名基准分数冲突取哪一条**是独立拍板项，本次未自动删。
（→ 该拍板项即 **D11**，见 §20：量化后发现它主要不是「取哪一条」的裁决问题。）

> 这个 6 只是 **D9 脚本改动范围内的数**（脚本只在它改过的 156 条记录里查重）。全库独立复扫是
> **22 个数组 / 39 组重复键**：35 组同名不同分、4 组同名同分。典型的如同一基准挂着 3 个分数而 `config` 全为 `null`
> （`alibaba:qwen3-coder-480b-a35b` 的 SWE-bench Verified 0.658/0.67/0.696、
> `deepseek-…:deepseekmath-7b` 的 MATH 0.362/0.517/0.609）——多数更像**该用 `config`/`date`/`notes` 区分的不同测量**，
> 而不是「同一次测量记了两遍」。这又是一次「拿脚本自己的命中数当全库残留数」，与上面范围声明是同一个毛病：
> **查重要求独立跑一遍全库，不能复用归一化脚本的中间结果。**
> 独立复扫脚本：`temp/d9_residual_scan.py`，一次给三个口径 —— 缺 canonical 主键的条目（D10 后为 **0**，曾为 57）、
> 精确主键重复（22 数组 / 39 组）、以及**反方向**的近似重复：**7 组** 同基准、分数一模一样、
> 只因 `config` 里写了不同来源名而并存（`alibaba:qwen2-5-max` 的 GPQA Diamond 0.587，
> config 为 `default（benched.ai）` 与 `default（llmbase）`；§18 那对 T1/T3 的 GPQA Diamond 0.914
> 也是靠 `config` `null` vs `"xhigh"` 错开的）。
> 也就是说 `config` 现在同时被当成**评测配置**和**来源标注**用，语义不统一时去重两个方向都会失效：
> 该合的（同一次测量记两家转述）合不上，不该合的（airline / retail 两个子集）看着像重复。

---

### 20. 【D11】39 组主键撞车结案：毛病不是「两个分数打架」，是主键粒度不够

**先量后写**——拍板前先把 39 组逐条摊开（`temp/d11_groups_review.txt`），量出来的构成和当初的假设不一样：

| 观测 | 数值 | 意味着什么 |
|---|---|---|
| 组内 `confidence` 全同 | 38 / 39 | 「冲突时取高 confidence」**只能裁决 1 组**，作为通则无效 |
| 组内能靠 `date` 唯一区分 | 0 / 35 | 日期救不了 |
| 组内能靠 `source_type` 唯一区分 | 1 / 35 | 同上 |
| 组内能靠 `score_type` 唯一区分 | 4 / 35 | 少数派，且这四组的 `score_type` **本来就写对了** |
| 同名不同分且整组只有一个 `source_url` | **34 / 35** | 绝大多数**不是两个来源打架**，是同一来源的多个测量被压平 |

典型证据：`sber:fred-t5-xl` 的 `Russian SuperGLUE (RSG)` 一条基准挂着 **10 个条目**（1 个总分 + 9 个子任务，
子任务名只写在 `notes` 里，`config` 全空）；`hugging-face-bigscience:bloom` 的 HumanEval 三条 `pass@1/10/100`
`score_type` 写得清清楚楚，但主键 `(benchmark, config)` 里没这个字段，照样算成同一条。

**所以这不是「取哪一条」的裁决问题，是「主键不足以标识一次测量」的表示问题。**
拍板口径（2026-08-30）：按「`notes` 能否复原区别」分档处置。

| 档 | 判据 | 处置 | 组数 |
|---|---|---|---|
| **A** | notes 写明了区别且属评测设置（shot 数、prompting 方法、scaffolding/turns、投票策略、被测变体） | 把这句话**填进 `config`** | 15 |
| **B** | 区别只在 `score_type`（pass@k、PPL vs accuracy、Correctness vs 加速比）而 `score_type` 不在主键里 | `config` 追加该口径标识 | 5 |
| **C** | 同一大基准的多个子任务 | **拆进 `benchmark` 名**（`… (RSG) – MuSeRC`） | 1（含 10 条目） |
| **D** | 同名 + 同分 + 同来源的纯重复 | 删后到的一条，留 notes 更全的那条 | 4 |
| **E** | notes 也分不出谁是谁 | **不动**，交门禁报出来当待复测清单 | 14 |

合计 39。**分数一字未改**（独立复核：全库 `score` 字段 diff = 0），条目 5659 → 5655（净减 4 = D 档），
改动记录 18 条 / 编辑条目 56 个 / 删除条目 4 个，逐条反向还原（改回旧值 + 按原下标插回）与 `git HEAD` 逐字节相等。
脚本：`temp/d11_resolve_benchmark_conflicts.py`，计划表每条都带 `(期望基准名, 期望分数)` 做位置自校验——
下标一旦数错，期望值对不上就中止，不会静默改到别的条目。

**E 档 14 组为什么不动**：`microsoft-nvidia:megatron-turing-nlg-530b`（9 组，每基准 3 个分数、notes 只有
「开发集/测试集/标 \* 为 SOTA」这种公共描述，分不清哪列是哪个 shot）、`lg-ai-research:exaone-deep-2-4b`（2 组）、
`facebook-ai-research:multi-token-prediction-7b`（2 组）、`…aya-expanse-32b`（1 组，一条 notes 没写对手）。
要分开只能回原表重读，**属重采范围**，按「除重采外全做」的边界不在本轮动。

**本轮定的 `config` 语义边界**（此前没人写过，是 39 组和 7 组近似重复共同的根因）：

1. `config` 装**影响分数可比性的评测设置**，允许三类：① 常规评测配置（shot 数 / prompting 方法 / 脚手架与 turn 预算 / 解码与投票策略）；
   ② **被测变体标识**——仅用于「一条记录聚合了多个发布变体」的情形（如 SimPO 那条同时挂 Llama-3-8B v0.1 / v0.2 / gemma-2-9b-it）；
   ③ **指标口径标识**——仅用于 `score_type` 已写明但主键不含它的场合。
2. **禁止把来源名写进 `config`** —— 来源站的正身是 `source_site`（D12 新增，见 §21）。
   D11 写下这条时只有一句「来源是 `source_url` / `source_type` 的活」，等于把来源名赶到无处可放，
   而 `independent` 数组确实需要按来源区分测量 —— 存量的 **88 个条目 / 19 条记录**已在 D12 迁出。
3. 判据是「`benchmark` + `config` + `date`（`independent` 再加 `source_site`；必要时靠 `score_type` 或基准名承载口径）
   合起来足以唯一标识一次测量」；不够就补，别留着让去重失效。

> **没有顺手改合并主键**是当时有意为之：把 `array_key_default` 扩成 `(benchmark, score_type, config)` 才是 B 档的根治办法，
> 但那会改全局 merge 语义、影响此后所有批次的去重行为，属独立拍板项。B 档先用「`config` 追加口径标识」顶住，
> 代价是 `config` 里有 5 组信息与 `score_type` 冗余。
> **后记（D12 同日）**：实测「主键加 `score_type`」对残留 14 组的消解数是 **0**，这条已按实测关掉、不再拍板；
> 真正扩了主键的是 `independent` 的 `source_site`（同一问题在 88 个条目上的另一种表现，见 §21）。

**防回归**：门禁新增规则 6.2（WARN）—— 同一**合并去重主键**（`self_reported` 为 `(benchmark, config, date)`，
`independent` 为 `(benchmark, config, source_site, date)`，`arena_elo` 为 `(sub_benchmark, date)`，
与 §18 的 SOP 合并命令逐段一致）挂着 ≥2 条时，分数不同报「去重无从裁决」、分数也相同报「同一次测量记了两遍」。
> D11 当时把这段主键记成只含 `(benchmark, config)`，漏了 SOP 里的 `date`。对现存这 14 组无影响
> （它们全在 `self_reported` 且成员一律没有 `date`），但若哪天撞上的两条日期不同，粗键就会误报成「合并会丢」，
> 而实际合并根本不会碰它们。D12 已把 `BENCH_SUBKEY` 与 SOP 对齐。
沿用 §19 的顺序：**先清数据（A/B/C/D 25 组）再收紧检查**，规则只对剩下 14 组 E 档开口。
三份备份上的负对照（`其他` = D1–D10 那 689 条基线，三段全程不动，可用来确认新规则没有误伤）：

| 跑的库 | 规则 6.1 | 规则 6.2 | 其他 | 合计 |
|---|---|---|---|---|
| D9 改前 `d9bak` | 1350 | 28 | 689 | **2067** |
| D11 改前 `d11bak` | 0 | 39 | 689 | **728** |
| D11 改后 | 0 | 14 | 689 | **703** |
| D12 改后 | 0 | 17 | 689 | **706** |
| **D13 改后（现库）** | 0 | 17 | **457** | **474** ← 新基线 |

> 前三行的「其他 = 689」是当时的常量段；**D13 废止「有效上下文须独立实测」口径后，其中 232 条
> （缺测试方法说明 127 + 缺「待测」标注 105）随检查项一起删除，常量段降到 457**。
> 拿旧负对照备份复跑时，「其他」仍会是 689——那是备份对应的旧门禁，不是不一致。

> **D11 之后的 WARN 验收基线是 703，不再是 689。** 其中 14 条就是 E 档待复测清单本身，
> 由门禁自动维护——不再往数据里写 `conflict` 标记键，清单可随改随生，不会烂在数据里。
> （**同日 D12b 把基线推到 706 / 17 组**，多出的 3 组见 §21，性质与 E 档相同。**D13 又降到 474**，见 §22。）

---

### 21. 【D12 + D12b】`config` 里塞来源名不是脏数据，是主键缺了一段

D11 收尾时留了个待拍板项：「**7 组**近似重复 —— 同基准、分数一模一样，只因 `config` 写了不同来源名而并存，
剥掉来源名即可合并」。本轮先量了这个「7 组」。

**量的结果推翻了这个说法**（`temp/d12_source_in_config.py`，只读）。判据不能用「括号里有字母就算来源名」——
那样命中 314 条目 / 79 记录，全是误伤（`default`、`pass@1`、`Avg@64 + selector` 都是合法配置）。
改用**自证式判定**（括号里的内容必须能在**本条目自己的** `source_url` 主机名 / `source_type` 里找到）后：

| 口径 | 数 |
|---|---|
| `config` 写了来源名的条目 | **92 个 / 21 条记录**（不是 7 组） |
| 剥掉来源名后撞主键的组 | 33（6 组分数全同 + 27 组分数有差） |
| 按真实 SOP 主键会静默丢掉的行 | **33 行**（按 D11 记的粗键是 51 行；27 组里有 18 组靠 `date` 不同才侥幸不撞） |

而那 27 组「分数有差」根本不是冲突：`anthropic:claude-3-7-sonnet` 的 GPQA Diamond 挂着
0.6604 / 0.848 / 0.785，分别来自独立评测平台、serenitiesai、evals.report —— **不同第三方站各测一次，
正是 `independent` 数组存在的意义**。所以「剥掉来源名再合并」方向是反的，它会删掉多来源交叉验证本身。

**真问题**：一次独立测量的身份天然含「谁测的」，而 `(benchmark, config, date)` 里没有这一段。
采集者往 `config` 塞站点名，是因为没有别的键能放 —— D11 定下「禁止把来源名写进 `config`」却只给了
「来源交给 `source_url` / `source_type`」，那两个字段是**逐条目**的、不参与主键，等于把信息赶到无法承载身份的地方。

**处置（用户拍板 = 扩主键 + 新增字段）**：

1. 跑分条目新增 **`source_site`**（仅 `independent` 用；`self_reported` 的来源就是厂商自己，无需此字段）。
2. `benchmarks.independent` 的合并主键扩为 **`(benchmark, config, source_site, date)`**，
   三处文档的 SOP 合并命令与 `model_data_tool` 示例同日跟改（少写这段会让不同站的同名基准互相覆盖）。
3. 门禁 `BENCH_SUBKEY` 同步，并顺手修掉 D11 记错的主键（漏了 `date`，见 §20 的更正块）。
4. **D12 迁 88 条 / 19 记录**：`default（serenitiesai）` → `config="default"` + `source_site="serenitiesai"`；
   计划表逐条带 `(期望基准名, 期望分数)` 自校验位置，`temp/d12_plan.txt`。
5. **D12b 补迁 59 条 / 14 记录**：`Artificial Analysis（llm-registry）` 这一族。
   它们**必然过不了自证式判据** —— `source_url` 一律指向 `artificialanalysis.ai`，括号里写的是**实际读到的镜像站**
   （AA 的站在本机被 Cloudflare 拦）。同一毛病，另一半。**镜像站是读取路径、不是测量身份**，
   所以 `source_site` 记出处 `Artificial Analysis`、`config` 归 `default`、镜像站落 `notes`。
   实测 57 条带镜像名的条目里 **56 条的 notes 早就写了镜像站**，只有 1 条需要补写 —— 采集质量在这件事上帮了大忙。
   同轮审计排掉 1 条：`nvidia:nemotron-3-nano-30b-a3b` 的
   `config="Artificial Analysis Intelligence Index v3.0, post-trained variant"` 只是**以站名开头的真实评测描述**，
   拍平成 `default` 就是销毁信息 → 留在原地，判据是「括号外必须只剩站点名本身」。
6. 收尾又扫了一遍「整个 config 恰好等于某个主机名」的条目（防第三种形态），
   命中 5 条：2 条已在 D12b 计划内、3 条是本机比对把 CJK 剥成 `cursor` 造成的误报。**无第三种形态。**

**代价（已量化并接受）**：`anthropic:claude-opus-4-5:20251101` 有 **3 组**「同一次 AA 测量被两个镜像各抄一次」
（GPQA Diamond 0.81 vs 0.87、MMLU-Pro 0.889 vs 0.9 是**两份互相矛盾的转写**；SWE-bench Verified 0.809 vs 0.809
是**两条镜像读值一致的真重复**）。
`source_site` 记出处后这三组主键相同 → 规则 6.2 报出来，**同主键组 14 → 17、WARN 703 → 706**。
分歧的 2 组本该由复测定谁对；同分那组删任一条都不丢分数，但会少一条独立读取路径的印证，故**一并留给复测、不手动裁决**。
靠把镜像名塞进主键来「避开冲突」只是把同一个病往下挪一层。**当时的验收基线：WARN 706、同主键组 17**
（同主键组 17 至今有效；WARN 已被 **D13 降到 474**，见 §22）。

> **没有为「`config` 又被人塞来源名」加门禁规则**。想加过（判据：剥掉括号后同键、raw config 却不同），
> 但合法配置里本来就带括号（`HELM classic（355 条评测样本）`、`GPT-5.6 Sol (max)`、
> `Artificial Analysis Intelligence Index v3.0, post-trained variant`），任何「括号即来源名」的启发式
> 都会误伤这些；换成站点黑名单则要靠人维护清单。现在 `source_site` 已是主键的一段，
> 新数据真撞车时 6.2 会自己开口，这条检查的边际价值不如它的误报成本。

**验收**：记录 940 / 跑分条目 5655 全程不变；与 `git HEAD` 逐条比对，字段级差异只有
`config` 145 处 + `source_site` 145 处新增 + `notes` 1 处追加，**`score` 改动 0**；
`source_site` 只出现在 `independent`（145 条）；两步迁移各自断言「反转后与改前逐字节相同」。
脚本：`temp/d12_add_source_site.py`、`temp/d12b_artificial_analysis.py`（都支持 dry-run 出计划表）。

---

### 22. 【D13】一条没人记得来历的口径，撑起了全库 1/3 的警告

§21 那句「新的验收基线：WARN 706」已被本轮取代，现基线见本点末尾。

**拍板**：`context_window_effective_tokens`（有效上下文）**不再要求独立实测**。原口径「未经独立测试（T1）
一律填 `null`」在本仓库文档里查不到制定理由，用户 2026-08-30 判定：厂商标称值不算说谎，真正的差别是
长文尾端效果衰减，而这一栏的含义本就是「官方支持到多长」，不是「多长以内效果不掉」→ **口径废止**。

**为什么该废（数据自证）**：全库 208 条填了有效值，只有 **8 条**是旧口径设想的样子；**173 条**是标称值的
原样抄写（其中 100 条连备注都没有），另有 **27 条**两栏填反。门禁为这条口径专设两项检查，命中
**127 + 105 = 232 条**，占当时 706 条 WARN 的 33%。规矩与实际数据背离到这个程度，补写备注只是给旧口径续命。

**新口径**（已写进 `执行细则.md` §2、`prompt.md` 字段字典、`agent_prompt_per_model.md`、本指南 §14）：
- 有效栏允许厂商标称 / 厂商自报 / 社区实测，**出处写进 `notes` 即可**，没有任何依据才留 `null`；
- 官方给了「原生 X / 可扩展到 Y」的，**标称栏填最大值 Y**（那才是官方支持上限），X 与扩展手段写进 `notes`；
- **硬不变量：有效栏不得大于标称栏**。门禁据此把两条旧 WARN 换成一条「有效上下文大于标称上下文」。

**27 条填反记录的归位（方案 A）**：较大值进标称栏、有效栏置空、备注补一句归位说明。
其中 20 条备注本是空的（Qwen2.5/Qwen3 全系那批 32,768 vs 131,072），另外几类的原始出处全部保留。
**改备注是必须的**：有 7 条的备注里写着 `context_window_tokens=32768` / `context_window_effective_tokens=131072`
这种**字段-值绑定**文字，只改值不改文字就会与 D4 清过的「备注与数值自相矛盾」同类复发 →
脚本把这类字面改成 `原生窗口=` / `可扩展上限=`，把 `标称上下文 N tokens` 改成 `原生上下文 N tokens`，数字与出处一字不动。

**一处例外（不要照抄「最大值归标称栏」）**：`deepseek:deepseek-v3:0324` 标称 131,072 / 有效 163,840。
它的备注写得很清楚：131,072 来自官方 GitHub README `Context Length 128K`（**T0 直采**），
163,840 是第三方站点（aisharenet / llm-stats / OpenRouter）一致转述的 RoPE 扩展上限（**T3，非官方直采**）。
把 163,840 挪进标称栏＝**用三方数覆盖官方数**，违反「不冒充 T0」这条没被废止的红线。
所以该条标称栏**保持 131,072**，只清空有效栏，两个数与各自出处全部留在备注里。
> 推论：将来若再遇到「有效 > 标称」，先看备注里那个较大值的**来源等级**，别直接搬。

**验收**：记录 940→940、跑分条目 5655→5655、`score` 零改动；改动只落在 27 条记录的
`context_window_effective_tokens`（27）、`context_window_tokens`（26）、`notes`（27）三处；
有效上下文非空 208 → **181**；残留倒挂 0。
**D13 后基线：940 条 / ERROR 0 / WARN 474（= 457 + 规则 6.2 的 17）/ 结构漂移 0 / 精确主键重复 17 组**
（同日 D14 移出 7 条非模型后为 **933 / 469**，见 §23）。
脚本：`temp/d13_fix_effective_context.py`（dry-run 出 `temp/d13_plan.txt`，反转逐字节复原为验收条件）。

---

### 23. 【D14】「我们只记录模型」——删掉的不是脏数据，是一条从没写下来的范围假设

**用户原话**：「我们的数据库里面不要这些训练框架什么的，我们只记录模型。」（2026-08-31 拍板）

这句之前它**不是一条规则**，全库没有一处写过这个默认假设。翻 `prompt.md` / `执行细则.md` /
`multi_platform_subagent_guide.md` 的采集范围条款，只写了「702 个花名册模型」——**名册里有，就算该记**。
而名册里确实混着 `megascale`（一篇训练系统的论文）、`alphaevolve`（一个 agent 系统）、
`distro`（一种分布式训练技术）、`omni-epic`（一个调外部基础模型的算法框架）。采集人老实按字段表填，
填到 `architecture_type`（架构类型）时无可奈何，只能在值里写 "not a model"。
**这些记录不是脏数据，是范围错配**——所以整改的对象是范围声明，不是那几条记录的质量。

**移出判据：只认记录自己的声明。** 满足其一才进候选：
① `architecture_type` 值本身就是系统/框架类描述；
② `notes`（备注）里有指向**本条对象身份**的自证句（「由于它不是模型」「是系统而非单模型」「agent 系统而非基础模型」…）。

命中 7 条，逐条把原文打出来人工核对后搬走。结果：**940 → 933 条**、跑分条目 5655 → 5642（带走 13 个）、
WARN 474 → **469**（归档那 7 条自身贡献 5 条，469 + 5 = 474 严丝合缝）、ERROR 仍 0、精确主键重复 17 组不变。

**为什么宽松关键词不可用。** 第一版判据是「`框架|系统|平台|pipeline`」，全库命中 **79 条**。逐条读原文，
几乎全是误伤：
- 「训练框架 hai-llm，a100/h800 集群」—— 是 DeepSeek-Coder 的**训练工具**，对象当然是模型；
- 「此为 api 侧限制**非模型**上下文上限」—— 是上下文口径的说明文字（D13 那一族）；
- 「专为代理式 AI **多智能体系统**设计」—— 是某个 NVIDIA 模型的**用途定位**；
- 「官方博客 webfetch 仅返回页面**框架**」—— 是采集过程记录。

这些短语各自指向的东西，跟「本条记录的对象是不是一个模型」毫无关系。
**教训与 §21 的 `source_site` 判定同构：判据必须指向本条记录自己的身份声明，不能是字段里出现过的词。**

**两条局限，如实登记，别当已收口。**
1. **只抓得到自证的**。采集者没在备注里写「我不是模型」的系统级条目，这套判据扫不出来。
   真要闭合范围，得有人逐条读 933 条的 `positioning` / `full_name` —— 那是**人工全库复核**，不是脚本活。
2. **乙档 3 条按用户点定保留**：`xai:grok-4-heavy`（值 "Multi-agent orchestration (Heavy tier)"，但它是对外
   售卖的旗舰档位、带定价与 Arena 分）、`inspur:haiyue`（值「复合式 AI…多智能体协同架构」）、
   `huawei:pangu-5-0`（备注自陈「系列级发布而非单一模型」）。它们卡在「模型」与「系统/系列」的缝里，
   **将来若要清须重新拍板，不要按本轮这 7 条自行外推**。

**花名册口径（第三次变更）**：702 个 model_id 现为 **主库 685 + 存疑隔离 10 + 非模型 7 + 缺失 0**。
这 7 个 id 与 D6 那 10 条一样**不得当「漏采」重派** —— 它们的批次真 `submitted` 过，采集人没做错任何事。

**留痕与回流**：原文**逐字节**存 `docs/non_model_records.jsonl`（7 行），5 个采集文件移入
`incoming/models/_out_of_scope/`（`_quarantine/` 已被 D6 用作「存疑」，处置理由不同，不混放）。
回流只有一种正经理由：**证明该对象其实是一个模型**，然后走 §17.5 同款流程（补证据 → 单文件过门禁 ERROR 0 →
显式点名合并 → 从归档删该行）。目录扫描合并捞不到它们，但显式点名能 —— **别把移动文件当屏障，真正的判据是归档文件本身**。

**现基线（D14 起）：933 条 / ERROR 0 / WARN 469（= 452 + 规则 6.2 的 17）/ 结构漂移 0 / 精确主键重复 17 组。**
脚本：`temp/d14_nonmodel_scan2.py`（只读出候选）、`temp/d14b_quarantine_nonmodel.py`（dry-run 报差额，`--apply` 才写盘）。

---

### 24. 【D15】一栏塞两种语义：`architecture_type` 拆成「稀疏性 + 主干结构」两栏

**事实（先量后写）**：`architecture.architecture_type` 名义上是四值枚举，实际存了 **190 种自由写法**
（D15 改前 933 条备份实测；越出旧枚举的有 **186 种 / 289 处**。§23 之前提到的 195 是 D14 前 940 条快照，被移出的
7 条系统级记录自成一类写法）——
`"Transformer (decoder-only, GQA, RoPE, RMSNorm, SwiGLU)"`、`"Hybrid Mamba2-Transformer (24 Mamba-2 + 4 self-attention + 28 MLP layers, sequential layer-wise mix)"`、
`"Sparse MoE — MLA + MTP + 高稀疏比（256 路由专家 + 1 共享专家，每 token 激活 8 专家）"` 都挤在同一栏里。后果不是难看，是**这一栏根本没法聚合**：
想统计「有多少 MoE 模型」，得先穷举这 190 种写法里哪些含 MoE 意思。
拆栏范围 **300 条 = 越界 290 条（越出旧枚举的 289 条 + 值为 `null` 的 1 条）+ 恰好写作 `"Hybrid"` 的 10 条**
（后者也在范围内，因为 `Hybrid` 在这批数据里
同时被用来指「稀疏性混合」和「骨干混合」，是个语义撞车的值）。

**两轮拍板**：第 15 轮「拆成两栏：稀疏性枚举 + 主干结构枚举」→ `architecture_type` 收窄为
`Dense / MoE / Hybrid / Unknown`，新增 `architecture.backbone_type` 取
`Transformer / Transformer-Decoder / Transformer-Encoder / Transformer-Encoder-Decoder / Mamba-SSM / RNN-LinearAttention / Diffusion / CNN / MLP / Hybrid / Unknown`。
第 16 轮「借力本条备注，不许通识反推」→ 值文本判不动时**允许**读**同一条记录自己的** `architecture.notes` 里的明文声明，
**禁止**用外部通识（名字里有 Llama 就判 Transformer）或参照同系列兄弟条目。
两栏都要求**原文不丢**：值比枚举具体时，原话照抄进 notes 结尾的 `；原架构表述：「原话」`。

**判定顺序（每条四步，任一步出值即止）**：
① 读本条 `architecture_type` 原文（先剥否定表述）→ ② 判不动才读本条 `architecture.notes` →
③ 裸 `"Hybrid"` 且本条备注定不了轴向时**定向为骨干轴 `Hybrid` + 稀疏性 `Unknown`**（本库采集者写 "Hybrid" 绝大多数指骨干混合，D11/D12 取证）→
④ 三处都判不出 → 两栏 `Unknown`，原文进 notes 留证。另有 **5 条人工裁定表**（`OVERRIDE`），每条都必须写明是本条自己的哪句证据。

**判据必须自带证据**：`temp/d15_split_architecture.py` 默认 dry-run，把 **87 条触发借力的记录连同命中词的 ±28 字上下文**
全部打印出来逐条核对，并统计**被闸门挡掉的 39 处命中**。方向上刻意偏保守：**判不动就 `Unknown`**（少填可补，错填会误导聚合）。

**这套闸门是一处一处误伤修出来的**（每一条都先有假阳性样本才加规则，别当通用先验抄）：
- **否定剥离**：`非 MoE`、`not moe`、`MoE 未披露`、`非Transformer`；并列式 `非Dense/MoE/Transformer` 三个词都得剥，
  只剥 `非 MoE` 会把中间的 `dense` 读成肯定声明。`non-MoE`（连字符英文）漏剥过一次，稠密模型被判成 MoE。
- **词边界**：notes 是长篇散文，裸子串必误伤 —— `dense` 命中 `densely`；`\bexperts?\b` 把 Mixture-of-Depths 的
  「expert-choice 路由」读成 MoE；裸 `attention` 把 "Lightning Attention" 读成第二骨干，凭空造出 `Hybrid`。
- **`Dense(768→128)` 是全连接层记法**不是稀疏性声明；但括号后必须紧跟**数字**才算层记法，
  否则把真声明 `Dense (non-MoE) decoder` 一起误杀（实测 `trillion-labs:tri-21b`）。
- **限定语窗口要按子句切，不是按字符数**：`stepfun:step-1` 的「架构为密集 Transformer」被**上一子句**的
  「未披露精确参数量」用 ±30 字窗口误挡；改成取命中所在子句（强句读切分 + ±40 字封顶）后正确。
- **中文「密集 / 稠密」两种写法都在用**，只列 `稠密` 会漏。
- **兄弟型号不算本条证据**：`ant-group:bailing-pro` 的备注写「后续 Ling-2.6-flash 已确认采用 MoE，但原始百灵 Pro 官方仅称 Transformer」——
  这句的 MoE 归属**后继型号**，正是第 16 轮禁令要挡的那类。这类靠 `OVERRIDE` 单条钉死，不为一个样本改全局规则。
- 同理被 `REJECT_WIN` 挡掉的：「是否为 MoE…未确认」「故不填 MoE 避免无源断言」「业界推测为 dense 但官方未明示」
  「与 Transformer 的自注意力机制不同」「相较标准自回归解码」（拿标准做法作对照，不是声明本条骨干）。

**结果与验收**：写盘 **299 条**（范围内 300 条减去 `xai:grok-3-mini` —— 它 `architecture_type` 本就是 `null`
且备注明写「未公开架构细节」，不给它造 `"Unknown"`）。
- 全库稀疏性栏：`Dense 324 / MoE 150 / Hybrid 1 / Unknown 457 / null 1`（933 条全部落在枚举内，兜底校验 0 越界）。
- 主干栏：`Transformer-Decoder 120 / Transformer 84 / Unknown 31 / Hybrid 27 / RNN-LinearAttention 13 /
  Transformer-Encoder 8 / Transformer-Encoder-Decoder 8 / Diffusion 3 / MLP 3 / Mamba-SSM 2`。
- `backbone_type` 只写在参与拆栏的 299 条上（**缺键 = 该条未参与拆栏，不是错误**），键序紧跟 `architecture_type`。
- 记录数 933 / 跑分项 5642 全程锁定；反向还原**逐字节**等于改前文件；备份 `model_data_v2.jsonl.d15bak-*` 与提交前 HEAD `md5` 相同。
- 门禁：**改前 WARN 758 → 改后 469**。这 289 条差额正是新规则 1.1 命中「自由文本写法」的数量，
  即新规则精确指向 D15 修掉的那个毛病；ERROR 全程 0。

**新规则 1.1 / 1.2 为什么是 WARN 不是 ERROR**（数量都实测过）：`docs/non_model_records.jsonl` 越界 **4 条**、
`docs/unconfirmed_models.jsonl` 越界 **2 条** —— 归档按**行 byte-exact** 留存，用的就是拆栏前的自由文本，
判 ERROR 会让历史验收信号失真（§17.5 的归档同理）；更直接的是 `incoming/models/` 下 **158 个采集文件各含 1 条**
拆栏前写法，门禁在合并时是**逐文件**跑的，判 ERROR 会把后续合并整批挡住。
**升 ERROR 的三个前置**（别只按「新库命中 0」就升）：① 下一次采集周期结束、新入库记录 1.1/1.2 命中为 0；
② `incoming/models/` 那 158 个存量采集文件已合并完毕或按新口径重写；
③ 两份 `docs/*.jsonl` 归档要么明确排除在门禁管辖外（它们按 byte-exact 留存、永不改写），要么接受对归档单独按 WARN 计。

**遗留（没做，不是漏了）**：
1. **633 条未参与拆栏** —— 它们的值本来就写作 `Dense`/`MoE`/`Unknown`，是合规的，但**主干信息为零**；
   其中 373 条 `architecture_type="Unknown"` 若放开 notes 借力还能捞回一部分骨干，本轮刻意不做（范围只覆盖拍板时的 300 条）。
2. **9 条两轴都 `Unknown`**（改后库实测）：`universite-de-technologie-de-compi-gne-cnrs-google:transe`（KG 嵌入）、
   `massachusetts-institute-of-technology-mit:pandemonium`、`rock-ai-shanghai-stonehill-technology:yan`
   （明说「摒弃 Transformer」，绝不能判成 Transformer）、`unknown:hierarchical-lm`、
   `aircas-pcl:kongtian-lingmou-3-0`、`fmmu:pathorchestra`、`wuxi-sixiang-digital-intelligence-technology-co-ltd:jinshi`，
   外加 §23 乙档保留的 `inspur:haiyue` 与 `xai:grok-4-heavy`。这 9 条原文里就没有骨干或稀疏性声明，**不是分类器漏判**，
   原文已逐字留证在 notes。
3. `backbone_type` 是**新键**，下游读主库的脚本要认这个键才有意义；本轮只改了采集侧口径（§字段字典 + 两份 subagent 任务书）。

脚本：`temp/d15_split_architecture.py`（dry-run 出计划并打印逐条证据，`--apply` 才写盘）、
`temp/d15_plan.txt`（过目用的判定表）、`temp/d15_changelog.txt`（300 行逐条 before→after 含证据串）。

---

### 25. 【D16】同一字段四种形状：`pricing.free_tier` 归一与 `available` 的真实语义

**症状**：`pricing.free_tier` 在库里同时存在四种形状 —— `null` 718 / 对象 134 / 纯文字 52 / 裸布尔 29。下游按规范路径 `free_tier.available` 读取时后两类直接取不到值（字符串无此属性、裸布尔也没有），聚合统计静默漏计。

**根因是文档与门禁互相矛盾**（本轮最值得记的一课，与 §15「三个会被文档误导的地方」同族）：
- `docs/prompt.md` 字段说明原文写着 `如 "每月 100 万 token 免费"`，**教的是字符串写法**；
- 门禁 `SUB_BLOCK_KEYS` 白名单是对象，但结构漂移检查（0.1）的 `cmp_block` **对非 dict 直接 return**；
- 于是采集 agent 照文档写 → 门禁不报 → 漂移静默累积到 81 条才在 D16 被发现。
- **改数据不改文档等于下批采集再犯**：D16 同日把四份采集文档 + 门禁规则 4.4 一起补齐。

**两轮拍板**：第 18 轮「**统一成结构化对象**」→ 形状与门禁白名单一致，键序固定 `available, rpm, rpd, tpm, notes`。第 19 轮「**任一途径免费即 true**」，附一条限定：「但是是标注**存在免费渠道**，免费不免费还是看具体的官方 API 定价」。

**`available` 的语义边界**（本轮真正的产物，比改数据重要）：
1. 语义是「**存在某条免费途径**」（官方 App / Web / 聊天页 / Playground / 新用户赠送额度 …任一），**不是**「这个模型免费」。
2. 因此 `available=true` **绝不参与、也不得抵消价格判断**：是否免费只看 `pricing.input / output / cached_input / batch_*` 及各自的 `confidence`。合并与统计脚本**不得**用 `available` 反推价格。
3. `available=true` 时 `notes` **必须写清是哪条渠道**，否则该键失去可核性。
4. 判不动就 `null` —— 偏差方向是少填，不是多填。

**四个分叉的裁定**（2026-08-31 逐条拍板，可直接当判据用）：
- **A** 随订阅提供 / 付费计划内含用量额度 → **不算**免费渠道（`null`）。渠道本身要花钱。
- **B** 官方免费 API 试用 key（限速、非商用）→ **不算**（`null`）。免费的是 key，不是额度体系。
- **C** 只存在过、现已过期（「曾提供」「限时已结束」、额度随模型下线失效）→ `false`。「曾」不是「存在」。
- **D** 同句既有订阅背景又有现存免费渠道 → **`true`**。订阅只是背景，不抵消现存渠道。

**判据工程上的四个坑**（都实测踩过）：
- **模板句误伤**：采集方按红线写的「未检索到免费层信息，置 null 不伪造」里也有「免费层」三字 —— 肯定词匹配到的是**没查到的东西**，不是查到的渠道。必须配「未检索到/未确认」语境否决，且凡与采集方模板句冲突的翻案一律转人工裁，不静默改。
- **兄弟型号量词**：「平台对新用户**通常**提供免费额度」「多数模型有」是平台级/兄弟级声明，不得算到本条头上（与 §24 的 `bailing-pro` 同构）。
- **排他表述**：「X 免费版**仅限** Grok 3 / Grok 4」是在说 Grok 4 Heavy **没有** —— 句中含「免费」却是反证。
- **脚本自身的 bug 也是盲区**：写盘脚本的断言循环遍历了全部 933 条，未改动记录的 `touched` 天然为空集 → 必然触发「动了 pricing 的其他键」假警报，第一次 `--apply` 就被它挡下（数据本身没问题）。**规律：断言的适用范围要跟着「只约束被改动的行」走，不能图省事遍历全表。**

**验收数字**：改动 **84 条**（形状迁移 81 = 文字 52 + 裸布尔 29，dict 改 `available` 3）；记录 933→933、条目 5642→5642、`score` 零改动、键序 215 条全部一致、`available` 分布 `True 120 / False 36 / null 59`。门禁新增规则 **4.4**（非对象形状即 WARN），**负对照用改前备份实测命中 81**（550 = 469 + 81），改后命中 0。备份 md5 与提交前 `git HEAD` 相同，反向还原逐字节复原。

**已登记遗留**：
- 5 条 `available=null` 且 notes 无判定信息（未纳入本轮扫描）：`mistral:magistral-small-1-0`「模型已从官方 API 退役」按分叉 C 应为 `false`，**因 notes 未命中扫描判据而漏网，是唯一一条真漏**；`google:gnmt`（Google 翻译网页/App 免费，按组 1 裁定 App/Web 不计入，口径一致）、`deepseek:deepseekmath-v2` 与 `prime-intellect:opendiloco-1-1b`（开源权重自托管，属 `basic_info.access`）、`qihoo-360:qiyuan-3-0`（占位记录，未检索到）—— 这四条维持 `null` 与口径一致。
- **一处口径张力待复查**：str 侧 `google:gemini-3-flash`「Gemini APP 默认免费使用」裁定 `true`，而 dict 侧组 1（`deepseek-v4-pro` 官方 chat 免费 Web/App 对话、Gemini App 免费档）裁定 `null`。两者同构却结论相反，源于用户两次拍板间的细微口径漂移，需最终定夺统一方向。

---

### 26. 【D17 / D17b / D17c】口径自己打架：`free_tier.available` 从「任一途径免费」收窄为「官方 API 有免费额度」

> 本节记的是**同一条口径分三遍走完**的全过程。第一遍（D17）以为做完了；第二遍（D17b）用更强的检测器照出第一遍的判据自身有五处盲区，追加四项裁定后又改判 45 条；第三遍（D17c）照出第六处盲区，并且发现第二遍**写进库里的一句改判理由是错的**、已被逐字节复制进 23 条记录。**「改完了」和「改干净了」之间隔着两遍复查**，这是本节最该被后人读到的东西。

**症状**：D16 结案当天就已登记「一处口径张力」，但复查发现它不是一条遗留，而是**全字段级的语义分裂**，具体表现为 6 类矛盾：
- `docs/prompt.md` 字段说明写的是**宽口径**（「存在某条免费途径：官方 App / Web / 聊天页 / Playground / 新用户赠送额度…任一」），而 D16 第四轮「组 1」裁定却按**窄口径**把两条官方 App/Web 免费对话判成 `null` —— 文档与裁定直接对撞；
- **同一模型的两条记录结论相反**：`gemini-3-1-pro-preview-high` = `true` vs `-customtools` = `null`；`deepseek-v4-pro:0813` = `false` vs `-none:base` = `null`；
- **开源权重一整类被劈成两半**：15 条 `true` / 1 条 `null`，判据完全同构；
- `available` 的值与同记录 notes 的自述相反（「值说 true，notes 说置 null 不伪造」）；
- 已退役模型仍挂 `true`；
- 依据只到消费者 App 的记录与依据到官方 API 的记录混在同一个 `true` 里，下游无法区分。

**根因**：D16 只统一了**形状**（四种写法 → 一种对象），没有统一**语义**。形状统一后，两套语义被装进同一个键，矛盾从「读不到值」变成「读到的值不可比」——后者更隐蔽，因为门禁和聚合都不会报错。

**拍板（2026-09-02，第 20 轮）**：**窄口径**。`available` = 「**vendor 官方 API 接口当前是否有免费额度**」。一律**不算**的渠道：官方 App / 网页聊天端 / Playground、消费者订阅内含额度、开源权重免费下载与自托管、第三方托管的免费档（OpenRouter `:free` / Cerebras 免费 key / HuggingFace serverless）、官方限速的 API 试用 key。本字段记**当前**状态，不记历史状态。判据分两组写进 `prompt.md`：有正面依据说明官方 API 侧没有/不再有 → `false`；依据没落到官方 API 头上或干脆查不到 → `null`。

**追加拍板（同日，第 21 轮，第二遍开工前的四项裁定）**：
- **Q1 平台级额度不算到本条**：23 条阿里云记录的唯一依据是「新用户开通百炼后 90 天内各模型有免费额度（以控制台为准）」——平台级话术 + 自陈「以控制台为准」，未经官方页逐模型确证 → 按裁定 6 记 `null`，并登记待重采（读 `help.aliyun.com/zh/model-studio/billing` 的**免费额度列** + `new-free-quota` 页）。与 D16 组 3 对 `alibaba:qwen-3-5-flash` 的同类判定归一。
- **Q2 legacy ≠ retired**：已从官方定价页移除 / 标为 legacy / `verification_status='已过期'`，但**未明示 retired 且可调用性未实测** → `null`（不是 `false`）。落在 `google:gemini-3-1-pro-preview-high`（顺带与孪生条 `-customtools` 归一）与 `bytedance:doubao-pro`。
- **Q3 窄口径不要求额度以 token 计量**：排除的是渠道（App/网页/Playground、消费端订阅内含、开源权重下载、第三方托管），不是计量单位。`amazon:amazon-q-developer` 的 Free Tier（每月 50 次 agentic 请求 + 1000 行代码/月 Java 转换）是 AWS 自有服务的独立免费用量档、不是塞在 Pro 档订阅里的附带权益 → 裁定 1 不适用，保 `true`，`rpm/rpd/tpm` 因无 token 速率概念置 `null`。
- **Q4 vendor 自有 Free API endpoint 算**：`nvidia:nemotron-3-ultra` 的 `build.nvidia.com` → `integrate.api.nvidia.com/v1`（带 `model` 参数）是 NVIDIA 自有托管 API 的免费端点 → 保 `true`；其 `free_tier.notes` 原为 `null`（依据散在 `access.notes` / `pricing.notes`），本轮补写，同时把 `pricing.notes` 里那条已作废的旧规范文字（「按规范开源权重模型 pricing 全 null + free_tier=true」）就地改写。

**范围测算的教训（第一遍最该记住的流程错误）**：提请拍板时给的选项预览里写「约 27 条」，逐条审下来实为 **67 条**（多一倍）；预览里预估的改后分布「是 59 / 否 77 / 空 79」也是错的，实际「是 57 / 否 77 / 空 81」。**规律：提请拍板的范围数字必须由逐条判定表算出，不能由抽样外推。** 发现偏差后先停下来把真实范围摊给用户重拍一次，没有默默按小范围做、也没有默默扩大范围。

**25 条 `free_tier.notes` 为 `null` 的记录怎么判**：这是本轮的方法论产出 —— **`notes` 为 `null` 不等于「无依据」**。这批记录的依据全在兄弟字段里：`basic_info.access.notes`（是否真有官方 API）、`pricing.notes`（常直接写着「free_tier=true 指 OpenRouter 提供…」）、`pricing.source_type`（「开源权重模型核对（无官方 API 价）」本身就是正面确证）。判定任何一栏之前，必须先把同记录的相关字段整段读一遍；否则只能靠猜或者一刀切置 `null`，两者都会造新错。

#### 26.1 判据工程的六个盲区（全部实测踩过，每一条都有具体样本）

第一遍写的分类器跑完自认为干净。第二遍把它的每条正则拿出来单独试，照出**五处系统性失明**；第三遍做同族复扫时又照出**第六处**。规律：**判据的匹配条件就是它的盲区**（与 §19 的 D9 教训同族），每写一条正则都要问「它读不到什么」，而且**改完一轮之后要拿更强的检测器回头再扫一遍自己**——第二遍之所以能找到第一遍的盲区，靠的不是更仔细，而是换了个参照物（从「计划文件的建议值」换成「记录自身的当前值」）。

1. **证据面只有一栏**：分类器只读 `pricing.free_tier.notes`，于是 25 条 notes 为 `null` 的记录在它眼里全是「无依据」，而它们的依据正躺在 `access.notes` / `pricing.notes` / `source_type` 里。
2. **`RETIRED` 正则漏日期插入**：「已**于 2026-06-01**下线」中间插了日期就匹配不上「已下线」，一条确证退役的记录因此没被判 `false`。
3. **`API_FREE` 是无锚点肯定词正则 → 否定失明**：「**无**官方托管 API **免费层**」里的「免费层」被当成**支持 `true`** 的证据命中。更糟的是这条正则还被用来**否决** UNCONF / APPWEB 两条规则、并把 `true` 直接保下来——一个否定失明的判据当了仲裁者。样本：`google:gemma-4-31b-it-minimal`、`meta:llama-3-2-3b`、`mistral:mistral-small-v24-09`、`xai:grok-4-20-0309-reasoning` 四条的 notes 都在自陈「无/没有免费层」，值却是 `true`。
4. **`NO_API` 是 7 条短语手抄表**：正面确证「厂商没有第一方托管 API」的写法远不止 7 种，`meta:llama-3-2-11b-vision-instruct` 的「Meta 官方不提供统一 API token 定价」就不在表内 → 该判 `false` 的被判成 `null`。
5. **矛盾句检测器三重失明**：① 24 条句式**全部要求前缀**，「免费层可用性 available=true。」这类裸写整片扫不到；② 每个字段**命中一条就 `break`**，同字段第二处矛盾被藏起来；③ **零条「断言 false」的句式**，任何写成「记 false」的句子都不在扫描范围内。三条都补掉后，检测器改为拿**记录自身的当前值**当参照物（原来拿一份一次性计划文件当基准，改判一轮就过期，会让它永远报 0），并加「历史提及豁免」——`原记/原句/原为/旧值` 等前缀 10 字内出现的取值字样是**引述被推翻的旧值**，不是对当前值的主张，不豁免会把第一遍自己的修正全部误报。
6. **`PLAT` 平台级话术正则漏词序/形态变体**（第三遍才发现）：第二遍圈「平台级笼统额度」用的是手写短语表（「新用户开通百炼」「开通百炼后」「以控制台为准」…），而 `qwen2-5-max` 写「自**开通百炼**/模型发布/申请通过之日起」、`qwen3-6-35b-a3b-none` 写「阿里云**百炼开通后**90天内**各**100万Token」、`qwen3-embedding` 写「自**开通百炼起** 90 天」——**三种词序/形态变体全部不在表内**，3 条平台级笼统话术就这么留在了 `true` 里。

#### 26.1b 判定顺序与证据时效的四个坑（第一遍记录，与 26.1 的匹配盲区是两类问题）

26.1 讲的是「正则读不到什么」，这四条讲的是「读到了也要按正确次序和时效来裁」：

- **优先级倒置**：「notes 自承未检索到」（→ `null`）必须排在「正面确证无官方托管 API」（→ `false`）**之前**。顺序反了，NVIDIA 研究模型（`megatron-bert` / `minitron-8b` / `nemotron-3-5-lightning`）会被误判 `false`，正确答案是 `null`。
- **将来时不是已退役**：「计划关停 2027-05-07」「deprecation track」「will be deprecated」被 `RETIRED` 正则误命中，须单列一条 `FUTURE` 规则把它压住。（第二遍的 Q2 裁定把这条延伸成正式口径：**legacy ≠ retired**。）
- **`T0` 直采不豁免时效检查**：`nemotron-3-nano-30b-a3b` 有 T0 原文 `'Free Endpoint: Available'`，但同页标注停用日 2026-08-25 早于判定日 2026-09-02 → 记 `false`。**证据等级高 ≠ 证据没过期。**
- **兄弟型号不许沾光**（裁定 6 延伸）：`typhoon-2-1-gemma-12b` 的 OpenTyphoon 免费 API 只覆盖 instruct 变体，base 条不得据此记 `true`。

#### 26.2 审计脚本自己也有盲区（第三遍的第二个发现）

为找第 6 条盲区写的复扫正则（笼统量词 `各/每个/通常/多数` + 免费额度，且无 per-model 引用）在 16 条存活 `true` 上报了 **5** 条，逐条读原文后**2 条是误报**：`google:gemini-3-6-flash-high` 与 `gemini-3-7-flash-high` 命中的是「Google Search/Maps grounding **各 5000 次/月**免费」——那是 **Grounding 附加额度**，量词的作用域不是模型免费档；模型自身的免费档由官方定价页逐模型给出（输入/输出/上下文缓存均免费）。**规律：量词正则不解析作用域，命中之后必须回原文确认量词修饰的是谁。** 两条登记为审计豁免（写进脚本常量 `AUDIT_FALSE_POSITIVES`）而不是悄悄放宽正则——豁免要有名字、要能被复查。

#### 26.3 三条关于「改自述文本」的教训

1. **只追加改判理由不等于消掉矛盾句，原句必须就地改写。** 第二遍写盘前屏障报出 8 处残留，其中 4 处是这个错：给记录追加了「[改判] 原句自陈…与 available=true 直接矛盾」，但**原句还留在原地**继续主张旧值。这正是第一遍犯过的错逐字重演。修法是把原句里的取值断言就地替换（`NOTE_FIX` 从 6 条加到 10 条），并在检测器里加「历史提及豁免」让引述旧值不再被误判为主张。
2. **改写句里不能出现检测器自己的字面句式。** 另外 4 处残留是我**新写的理由句**里带了字面 `available=true`、或引用了「故 free_tier 各字段置 null」——被自己的正则重新命中。统一改写成「已自相矛盾」「为由把整段置空」这类不含字面句式的措辞。**改自述文本时，改写结果必须能通过用来发现它的那个检查。**
3. **批量追加的理由句里若含「别的记录如何」的断言，必须逐条实测，不能顺手列举。**（第三遍的核心发现）第二遍给 23 条阿里云记录追加的同一句理由里写着「同族 qwen-plus / qwen2-5-max / qwen3-6-35b-a3b-none / qwen3-embedding **四条因已持本模型专属数字并引用官方页**，本轮保 true」。实测**只有 `qwen-plus` 一条成立**（它真引了 billing 定价页 qwen-plus 行的免费额度列，等值 8 CNY）；另三条持的仍是平台级笼统话术。这句话被**逐字节复制进 23 条记录**（实测 variants=1），等于把一个错误断言批量写进了库。修法：第三遍把 23 处全部就地改写 + 把 3 条按裁定 6 归一。**一句话被批量复制时，它的错误也被批量复制；凡是理由句里提到别的记录，逐个去读那条记录。**

#### 26.4 两处被实测推翻的旧结论（本节第一版写错的地方）

第一遍收尾时本节写过两句，第三遍逐条实测后都不成立，**保留在这里当反面样本**：

- ~~「§25 登记的 4 条维持 `null` 的记录，理由已写进 notes」~~ → 实测这 4 条（`google:gnmt` / `deepseek:deepseekmath-v2` / `prime-intellect:opendiloco-1-1b` / `qihoo-360:qiyuan-3-0`）的 notes 在第一遍里**一个字都没改**，理由是**采集时本就写在那里的**。正确措辞：「notes 里本就写有理由，本轮核对后维持原值」。**把「本来就有」写成「我做的」，会让后人以为这批记录的 notes 是被整改过的、从而不敢再动。**
- ~~症状清单里的「同一模型两记录结论相反」由第一遍归一~~ → 实测两组都**不是**第一遍解决的：`gemini-3-1-pro-preview-high`（`true`）直到第二遍 Q2 裁定才与孪生条 `-customtools`（`null`）归一；`deepseek-v4-pro-none:base`（`null`）直到第二遍 G4 才与 `:0813`（`false`）归一。**规律：症状清单里的每一项，收尾时必须逐条回验是否真被消解——「已列出」不等于「已解决」，尤其是被列在「症状」段而不是「处置」段的那些。**
  - 顺带一条**不要误修**的说明：`deepseek-v4-pro` 族改完后是 `:0813`=false、`-none:base`=false、`:base`=null，看着仍不一致，但这是红线在正常工作——`:base` 的 `free_tier.notes` 为空，**零证据**，按「查不到 = null」就该是 `null`；另两条有正面确证。**取值不同是因为证据不同，不是矛盾。**

#### 26.5 文档示例是判据的一部分（第三遍的第三个发现）

本轮查出 `docs/prompt.md` 里三处**同一类**缺陷：文档教的写法本身过不了门禁，或教的判定方向是错的。

1. **`free_tier` 示例把平台级话术教成 `true`，且错了两代。** 用 `git log -S` 逐字追到：D16 的提交 `b185006` 就把「开通后 N 天内各模型有免费额度」这类**平台级**话术当 `available=true` 的正例写进了文档；第一遍改口径时我只**换了措辞、没换判定方向**（仍留 `true`）。于是窄口径拍板后，文档继续教宽口径的答案。**改口径时必须回头检查示例的判定方向——光换措辞等于没改。** 现已换成正例（`zhipu:glm-4-7-flash`，定价页逐模型三栏全列「免费」，T0）+ 反例（平台话术 → `null`），并把两代错误留痕在示例旁边。
2. **规范单行示例漏了四必采键之一 `cache_write`。** 该键缺失是**门禁 ERROR 级**（`PRICING_MUST_KEYS`），也就是说**任何人照抄那条「规范示例」都产不出能过门禁的记录**。已补齐（`"cache_write":18.75`）。
3. **`source_type` 的字段说明与「来源类型下拉」都只给裸写法**（`官方技术报告` / `Model Card`），而门禁对 `self_reported` 且 `confidence ∈ {T0, T0-自报, T0-自报-转述}` 却不含「自报」的条目报 WARN。**下拉表就是采集的抄写源**，实测库里 4108 条自报分中 **436 条**踩在这条 WARN 上（`官方技术报告` 111 / `行业媒体聚合官方发布` 196 / `官方模型卡` 42 …），而带「自报」的正确写法本来就有 198 + 198 条在用。已在两处补上带「自报」的取值并注明只能从这三项里选；存量 436 条登记 D18。

**规律：文档示例不是说明文字，是判据的一部分——采集照抄示例，示例错就是全库错；而门禁只校验记录、不校验文档，所以这类错误永远不会被门禁自己报出来。** 判据改了，示例必须同批改；示例改了，必须拿门禁验一遍。

**可执行护栏**：`temp/d17c_example_gate.py` 把 `docs/prompt.md` 里的 ```jsonl 代码块抽出来直接喂门禁，并做**负对照**（摘掉一个必采键，断言门禁必须失败）——护栏本身要能被证明会失败，否则「exit 0」毫无信息量。实测：正对照 `exit 0 / ERROR 0 / WARN 0`，负对照 `exit 1 / ERROR 1`（`pricing.cache_write 必采字段缺失（即使无值也必须显式为 null）`）。**局限**：只有整条记录的 ```jsonl 块可机检，分对象的 ```json 片段（如 `benchmarks` 对象示例）喂不进门禁，只能人肉对着必采键清单核——上面第 1 项就出在这类片段里，改完请复看。

**矛盾句扫描的盲区（第一遍的第二个发现）**：第一轮只扫 `pricing.free_tier.notes` 一栏，查出 **12** 处自述矛盾；改成**全记录递归扫描所有字符串字段**后查出 **24** 处 —— 另外 12 处落在 `pricing.notes`(9) / `meta.notes`(2) / `pricing.long_context.notes`(1)。**规律：同一句断言常被抄进同记录的多个 notes 栏，扫描范围必须等于「记录里所有自由文本」，不能等于「字段名看起来相关的那一栏」。** 顺带照出一条存量缺陷：`yandex:yandexgpt-3` 与 `yandexgpt-4-pro` 把 1072 字的 `pricing.notes` **整段复制**进 `free_tier.notes` 与 `long_context.notes`（三处逐字节相同）。本轮只保持三者相等（同句改 3 处），复制缺陷本身登记 D18。

**护栏升级**：从 D16 的「按段比较」（benchmarks 段 / 非 pricing 段 / pricing 其他键各自断言相等）升级为**逐叶深比对 + 路径白名单**：递归比对改前改后每个叶子，同时断言每一层 dict 的键集与键序、每个 list 的长度都没变，任何差异路径不在白名单内即中止；未改动行**逐字节原样输出**并断言相等。

**「`git show HEAD == 现盘`」这道前置断言在多遍整改里必然失效**（第二遍踩到）：第一遍写盘后未提交，HEAD 就永远不可能等于工作区，脚本一开头就 assert 失败。改成 **md5 钉三个状态**：① 输入态 md5 必须等于上一遍的收尾产物；② HEAD md5 必须等于本轮动手前的状态；③ 上一遍的备份文件与 `git show HEAD:` 必须**逐字节相等**（三者互相咬合，任一处错位都会中止）。**且 md5 必须按二进制读算**——文本模式的换行翻译不保证 `raw.encode("utf-8")` 与磁盘字节相同。写盘后的独立复核仍用 `git show HEAD:` 取原版重算一遍累计增量，不复用写盘脚本自身的任何结论。

**屏障从两道加到四道**：① 再跑一次判定，值与建议值不符的残留必须为 0；② **用同一套矛盾句正则对写盘后的库再扫一遍，命中必须为 0**；③（第三遍新增）**笼统量词复扫的存活 `true` 必须精确等于已登记的审计豁免集合**；④（第三遍新增）**被判定为错的那句话在库里必须搜不到**。第 ③ ④ 道的意义是把「我以为改干净了」变成可执行的等式——不是「残留 ≤ N」，而是「残留 == 已知白名单」。

**验收数字（三遍累计，全部独立复算）**：

| | 第一遍 D17 | 第二遍 D17b | 第三遍 D17c | 累计 vs HEAD |
|---|---|---|---|---|
| `available` 改判 | 67（t→f 37 / t→n 26 / n→f 4） | 45（t→f 11 / t→n 30 / n→f 4） | 3（t→n 3） | **115**（t→f 48 / t→n 59 / n→f 8） |
| notes 改动 | 24 处 / 19 条 | 57 处 / 47 条 | 26 处 / 26 条（3 追加 + 23 纠错） | 63 处 |
| 触及记录 | 69 | 47（另 +1 条补写 `zhipu:glm-4-7-flash` 的空 notes） | 26 | **120** |
| 改后 `available` | 是 57 / 否 77 / 空 81 | 是 16 / 否 92 / 空 107 | **是 13 / 否 92 / 空 110** | — |

全程不变量：记录 933→933、跑分条目 5642→5642、`score` **零改动**、`model_id` 顺序一致、顶层键序一致、`free_tier` 键序变体 **1**、形状仍 `null 718 / dict 215`、未改动行逐字节相同、越界路径 **0**。**门禁 933 条 / ERROR 0 / WARN 469 三遍全部不变**（规则 4.4 只查形状，215 条改后仍全是 dict，本轮无需新增门禁规则）。叶子路径累计：`pricing.free_tier.available` 115 / `.notes` 63 / `pricing.notes` 14 / `meta.notes` 3 / `basic_info.access.notes` 1 / `pricing.long_context.notes` 1。

md5 链（本机备份均在 `.gitignore` 内）：HEAD `b185006` = 动手前 = `1ac14680…5021` → 第一遍 `d1076e74…f4c` → 第二遍 `9230b365…57d` → 补写 zhipu `0ef00749…cc2` → 第三遍 `5d2b4eef…50c`。

**存活 `true` 13 条**（每条都在 notes 里写清了是哪条官方 API 渠道，无一条 notes 为空）：`alibaba:qwen-plus`（billing 定价页 per-model 免费额度列，等值 8 CNY）、`amazon:amazon-q-developer`（AWS 自有 Free Tier，非 token 计量，Q3）、`cohere:north-mini-code`、`google:gemini-2-5-pro` / `gemini-3-5-flash-minimal` / `gemini-3-6-flash-high` / `gemini-3-6-flash-minimal` / `gemini-3-7-flash-high` / `gemini-embedding`（AI Studio Free Tier，官方定价页 'Free of charge' T0）、`mistral:mistral-moderation`（model card 'Price: Free' T0）、`nvidia:nemotron-3-ultra`（自有 Free API endpoint，Q4）、`voyage-ai:voyage-code-2`（前 50M tokens 免费 T0）、`zhipu:glm-4-7-flash`（open.bigmodel.cn 定价页 input/output/cache 三栏全列「免费」T0）。

**遗留处置与登记**：
- §25 登记的 5 条 `available=null` 全部处置：`mistral:magistral-small-1-0` → `false`（D16 那条「唯一真漏」至此补上），`google:gnmt` / `deepseek:deepseekmath-v2` / `prime-intellect:opendiloco-1-1b` / `qihoo-360:qiyuan-3-0` 按窄口径仍为 `null`，**notes 里本就写有理由**（本轮实测四条 notes 均未改动）；
- §25 登记的「口径张力」由第 20 轮拍板消解，`gemini-3-flash`（App 免费）已从 `true` 改为 `null`；
- 两处**事实冲突登记而不静默裁决**：① `mistral:open-mistral-nemo:2407`（`true`，「截至 2026-08-27 采集时 API 端点仍可调用」）与孪生条 `mistral:mistral-nemo-base:2407`（`false`，「2026-05-22 标记 Deprecated、2026-07-31 API 退役，docs.mistral.ai/models/overview 退役表直采 T0」）直接对撞 —— 已在 `access.notes` 追加 `[D17b 冲突登记]`，**原句逐字节保留**，待重采定夺；② 23 + 3 = **26 条阿里云记录待重采**官方 per-model 免费额度表（`billing` 页免费额度列 + `new-free-quota` 页），落实专属数字后可翻回真值。
- 其余登记 D18：yandex 两条 notes 三栏整段复制；~~**436 条 `self_reported` 的 `source_type` 不含「自报」**（门禁 WARN，抄写源是文档下拉表，见 §26.5 第 3 项）~~ **→ D18 已结案，见 §27**（308 条挂后缀归一、128 条空值门禁放过并改登记为待重采）；`docs/交接_2026-09-01_D16结案.md` 把远端仓库写成「GitHub 私有」，实为**公共**仓库（已改正）——写交接文档时对「远端可见性」这类安全相关事实必须实测，不能凭印象。
- D18 结案时**新登记、本轮不修**的两类（详见 §27 末）：**39 条**可信度 `T0-自报-转述` 但 `source_type` 写的是可直读官方文件，两者必有一错，判哪个错要真实转述源 → 属重采；**128 条** `source_type` 为空，门禁已放过，**对门禁完全不可见，只能靠 §27 清单追踪**。
- 已修（不再挂账）：`docs/prompt.md` 规范单行示例漏了四必采键之一 `cache_write` —— 已补齐，并加了可执行护栏 `temp/d17c_example_gate.py`（拿门禁验文档自己的示例 + 负对照），详见 **§26.5**。

---

### 27. 【D18】一条 WARN 混报两类缺陷：自报分 `source_type` 补「自报」+ 裸 `T0` 可信度归位

§26.5 查出「436 条自报分的 `source_type` 缺『自报』，抄写源是文档下拉表」。文档侧当天就补了，本轮清存量。第 22 轮拍板三件事：**范围 = 修能修的 + 门禁放过空值**；**原本带括号的 8 种写法（42 条）原样挂后缀、容忍双括号**；**自报分段的裸 `T0` 可信度一并改成 `T0-自报`**。

**数据面（写盘 423 个条目 / 73 条记录）**：

- `source_type` 改 **308 条**，三条规则且**全部不删也不注入「转述」**（保真断言：原写法含「转述」⇔ 新写法含「转述」，实测 0 条偏移）：
  - **R1 复用**（156 条）：`原写法 +「（自报）」` 库里已在用就直接用那个 —— `官方技术报告（自报）` 97、`官方模型卡（自报）` 42、`行业媒体转述官方发布（自报）` 17；
  - **R2 换尾括号**（7 条）：原写法以 `（转述）`/`(转述)` 结尾的换成 `（自报分转述）`，对齐库里 260 条的既有模式，避免 `官方技术报告（转述）（自报）` 这种三重括号；
  - **R3 新增变体**（145 条）：其余原写法逐字保留、只在末尾挂 `（自报）`。
- `confidence` 改 **122 条**（`T0` → `T0-自报`）。**裸 `T0` 只出现在自报分段**，`independent` / `arena_elo` 一条都没有；122 条**无一含「转述」**，故不会触发「转述来源不得配 T0/T0-自报」那条 ERROR（改前实测风险条数 0）。

**门禁面**：`self_reported` 的「建议体现自报属性」原本对 `source_type` 为空也报，等于把**两类不同缺陷混成一条 WARN** —— 「主张了一个中立来源」是写错，「根本没主张来源类型」是缺失。改成空值不报（`and stype and`），缺失那批登记待重采。

**WARN 逐级记账**（每级差额都能对上号，这是本轮的负对照）：

| 步骤 | WARN | 差额 | 差额是什么 |
|---|---|---|---|
| D17c 收尾 | 469 | — | = 常量段 452 + 主键撞车 17 |
| 只改门禁、不动数据 | **341** | −128 | 恰为 `source_type` 空值的条数 |
| 再改数据（308 条补「自报」） | **33** | −308 | 恰为非空写法缺「自报」的条数 |

剩余 **33** 的构成全部可解释：`knowledge_cutoff` 格式 9、参数量缺未披露声明 3、`pricing.source_type` 与价格值矛盾 3、有定价缺 `source_url` 1、规则 6.2 主键撞车 17。**常量段从 452 降到 16**，自报分那 436 条归零。ERROR 全程 0，记录 933→933、跑分条目 5642→5642、`score` 多重集相同、未改动行 **860/933 逐字节相同**（= 触及 73 条记录）、叶子差异路径 **越界 0**（白名单只有 `benchmarks.self_reported[i].source_type` 与 `.confidence`）、逆还原逐字节复原为 HEAD `5d2b4eef…5021` 的原文；改后 md5 `b5eaf743ebbe462613b3613e04168755`。

**本轮最该被记住的三条**：

1. **提请拍板前，数量必须按「缺陷类」全库数一遍，不能只数「本轮筛出来的那批」。** 我给用户报的是「31 条裸 `T0`」——那是**在 436 条 WARN 组内**数的；按缺陷类（自报分段 + 裸 `T0`）全库数其实是 **122 条**，另外 91 条的 `source_type` 已写对、只有可信度漏改，**因为不触发任何门禁信号所以从没进入过我的视野**。用户是在一个偏小 4 倍的数字上做的决定，发现后立刻停下来重报并重问。**筛选条件会悄悄给数量定了范围；报数时要说清「这是按什么口径数出来的」。**
2. **一条 WARN 只该对应一类缺陷。** 空值与写错混报时，436 这个数既不能当「要改多少」也不能当「缺多少」，改完也无法验收（改数据只减 308，减不到 436）。拆开后每一级的差额都恰好等于一个可独立测量的量。
3. **变换统一比好看重要，因为逆还原是验收手段。** 双括号那 42 条本可以改成插入式（`官方GitHub README(对比表·自报)`）读着更顺，但那要求判断末尾括号是全角还是半角、要不要改括号宽度，逆还原就得多一条规则。**统一挂后缀 → 逆还原只需剔后缀**，验收成本压到最低。

**复核脚本自己也会错（本轮踩到）**：写盘后我另写了一份独立复核，逆还原那一项报「与 HEAD 不逐字节相等」。查下来是**复核脚本的 bug 不是数据的 bug** —— 回填时用 `ia.get("source_type")` 无条件赋值，而 `dict.get()` 对**不存在的键返回 `None`**，于是给本来没有该键的条目凭空造了个 `source_type: null`，键集与键序都变了。**修法**：只在「两边都有该键且值不同」时回填，并同时断言每个条目的键集/键序一致（`assert list(ia.keys()) == list(ib.keys())`）。**规律：用 `.get()` 做回填/复原时，缺键与「值为 null」是两回事，混起来就会造键；凡是逆还原报不等，先怀疑复核脚本，再怀疑数据。**

**本轮不修、只登记的四类矛盾**：

- **可信度 `T0-自报-转述`（经转述获得）但 `source_type` 写的是可直读官方文件** —— 两者必有一错，要判哪个错得知道真实转述源 → **属重采**。本轮**不注入「转述」**（无证据即伪造）。**这条登记的口径必须写清，否则下一轮会数错两次**：
  - **窄口径 39 条**（本轮实际登记的那批，判据 = `source_type` 既不含「转述」也不含「自报」），改前的 9 种写法与条数：`官方发布公告` 16、`官方技术报告` 6、`官方社区公告（OpenAI 员工发布）` 4、`官方System Card` 3、`vendor_cited_third_party` 3、`官方发布公告原文` 2、`官方系统卡 PDF` 2、`官方研究博文` 2、`官方发布博客（GA 公告）` 1。**陷阱①：这 9 个串本轮全部被挂了 `（自报）` 后缀，库里已搜不到**，照原串 grep 会得 0；改后的对应串是 `官方发布公告（自报）` 16、`官方技术报告（自报）` 6、`官方社区公告（OpenAI 员工发布）（自报）` 4、`官方System Card（自报）` 3、`vendor_cited_third_party（自报）` 3、`官方发布公告原文（自报）` 2、`官方系统卡 PDF（自报）` 2、`官方研究博文（自报）` 2、`官方发布博客（GA 公告）（自报）` 1（已按记录+数组下标逐条定位核对，39→39 一一对应）。**但这些串也不再唯一标识这 39 条** —— 例如 `官方技术报告（自报）` 配 `T0-自报-转述` 的库里有 56 条，只有 6 条属本批。**陷阱①的硬证（D18b 复算）**：把登记时的窄判据**原样重跑在改后库**上，`self_reported` 段得 **0 条**（三段全扫只剩 1 条：`nvidia:nemotron-3-nano-30b-a3b:base` 的 `independent[0]`，值 `行业媒体聚合官方发布`，与本批无关）；同一判据跑在**改前快照**上得 **39 条 / 9 种**，与上面列的分布逐项吻合。**结论：判据本身已被本轮的写盘动作作废，这 39 条只能按「记录 + 数组下标」定位，重跑判据找不回来。**
  - **宽口径 438 条**（**判据原文**：`confidence == "T0-自报-转述"` 且 `source_type` **非空**、不含「转述」，不再排除已带「自报」字样的；**作用域仅 `self_reported` 段** —— D18b 复算时因为漏了这个作用域，三段全扫得到 440 而误以为文档写错，故把各口径都记下来：三段全扫 **440**、仅 `self_reported` 但计入空值 **458**、两者都放宽 **460**），**改前改后都是 438，本轮一条没减**（改前快照与现库各独立跑一遍，两边同为 438；写法**种类 42 → 41** 而条数不变，说明本轮挂后缀把某两种写法并成了一种）。**陷阱②：39 是 438 的子集，不是这个缺陷类的全量。** 438 条里含 41 种写法，最大三项是 `T0-自报` 83（**可信度值被写进了来源类型栏，是「值放错栏」另一类缺陷**；这 83 条同时被规则 6.3 报出 —— 两类缺陷在同一条目上重叠，但**WARN 不重复计**，因为「438 类」只是登记项、本身不是门禁规则）、`官方技术报告（自报）` 56、`官方自报` 36。
  - **教训 1 在同一轮里第三次应验**：31 vs 122（可信度裸 `T0`）、128 vs 775（来源类型缺失）、39 vs 438（转述对撞）—— **每一个「我数出来的数」都是被某个筛选条件圈过的子集**。加固版规矩：**登记任何遗留清单时，必须同时写下判据原文、该判据的命中数、以及放宽判据后的命中数**；只写一个数等于给下一轮埋雷。
- **128 条** `source_type` 为空**且可信度在 T0 家族内**（写盘后实测分布：`T0-自报` 108 / `T0-自报-转述` 20；改前是 `T0-自报` 84 / `T0` 24 / `T0-自报-转述` 20，其中那 24 条裸 `T0` 已随本轮可信度归位一起改掉）—— 门禁已不再报，登记为**来源类型缺失待重采**。**注意代价**：门禁放过后这批对门禁完全不可见，只能靠本清单追踪，别再指望 WARN 数提醒你。
- **顺带量出来一个更大的缺口（本轮不处置）**：自报分段 `source_type` 为空**合计 775 条**（**D18c 补注作用域**：775 = 仅 `self_reported` 段，与下文「128 + 647」逐项吻合；**三段全扫为 782 条**，多出 `independent` 5 + `arena_elo` 2），上面那 128 条只是「可信度落在 T0 家族」因而曾被门禁看见的部分；剩下 **647 条连 `confidence` 键都不存在**（实测 647/647 都带 `source_url`，所以 ERROR 级的缺 URL 检查不报、T0 家族前置条件又把 WARN 挡掉）。**这正是本轮教训 1 的同一类口径陷阱**：报「128 条缺失」时必须说清那是门禁可见子集，不是全库缺失数。647 条的来源类型与可信度双缺，待重采。**→ D18c（§27.2）后这个数变了：自报分段来源类型缺失 775 → **1290**（三段 782 → **1300**），且从此有**两种形状**（原本「无键」775 条 + 本轮新置的「值为 null」515 条）—— 将来重测缺失数必须两种都数，只数一种会少 515。同时 647 条里的一部分已补上可信度栏，见 §27.2。**
- **~~⚠️ 门禁判据本身有个洞，本轮没堵~~ → ✅ D18b 已补上留痕（门禁规则 6.3，见 §27.1）（最要紧的一条）**：那条 WARN 的判据是**纯子串匹配** `"自报" in source_type`，于是**把可信度值当来源类型写的条目天然满足它** —— `"source_type": "T0-自报"` 含「自报」二字，门禁放过，可这一栏**零来源信息**（它说的是可信度等级，不是「什么文件/页面」）。实测：跑分三段的 `source_type` 写成纯等级值的共 **607 条 / 62 条记录**（`T0-自报` 379、`T0-自报-转述` 200、`T0` 22、`T2-第三方` 3、`T3` 2、`T3-转述` 1；分段 `self_reported` 600 / `independent` 4 / `arena_elo` 3），另有 ~~405~~ **406 条**（**D18b 复算更正**：宽判据「值以 `T0`–`T4` 开头」合计 **1013 条**，`^T[0-4]` / `^\s*T[0-4]` / `startswith("T")` 三种写法实测一致、零分歧，1013 − 607 = 406；先前那个 405 少算 1）把 `T0` 之类前缀缀在真实来源描述前（如 `T0 官方一手技术报告（自报）`，信息不丢、前缀冗余，**规则 6.3 刻意不覆盖这类**）。**含义：本轮把这条 WARN 打到 0，有一部分是空心的** —— 归零只说明「不再有不带自报字样的裸写法」，**不等于**「来源类型栏都写了来源类型」。**为什么没把判据升成语义判断**：那要维护一张合法来源类型白名单（现库 `source_type` 191 种写法、含「自报」的 178 种；**D18c 补注作用域：191 = 仅 `self_reported` 段（该段非空 3333 条），三段全扫为 237 种（非空 4860 条）；而含「自报」的 178 种与作用域无关** —— `independent` 段含自报 **0 条**、`arena_elo` 段含自报 **3 条 / 3 种**，且这 3 种写法在自报段也出现过，故三段并集仍是 178），维护成本与误伤面未评估；且直接升 ERROR 会与 §24 规则 1.1/1.2 的处置口径不一致（那两条也刻意停在 WARN）。~~存量待拍板~~ → **D18 收尾时提请拍板，用户选「只加门禁留痕，数据一字不动」**：新增 WARN 级**规则 6.3**，607 条原样在册、由门禁自动维护清单，实现与验收见 **§27.1**；新增侧仍由 `docs/prompt.md` 步骤 3 的显式禁令挡。**这是 §26.1「判据工程盲区」的又一例：判据查的是字符串表面属性，不是字段语义。**

**D18 收尾基线：933 条 / ERROR 0 / ~~WARN 33~~（= 常量段 16 + 规则 6.2 的 17）/ 结构漂移 0 / 精确主键重复 17 组。** 旧文档里以 469 为基线的表述自此过时，但历史行的 469 是对的（对应改前门禁与改前数据）。**→ D18b 加规则 6.3 后为 WARN ~~640~~，见 §27.1；D18c 迁移乙档 + 清甲档冗余后现基线为 WARN 122，见 §27.2。**

#### 27.1 【D18b】给上面第四类缺陷补上留痕：门禁规则 6.3（只加留痕、数据一字不动）

**拍板（2026-09-02，第 23 轮）**：D18 结案后单独提请裁定「来源类型栏写了可信度等级值这 607 条怎么处置」，用户选 **「只加门禁留痕，数据一字不动」** —— 加一条 WARN 级规则把这 607 条全部照出来，让门禁自己维护这份清单，**数据一条不改**。与 §24 规则 1.1/1.2 刻意停在 WARN 是同一口径。

**为什么没选「一律置空」（提请拍板前量出来的三档，这一步救了 399 条）**：按「同一条目还有没有 `confidence` 键」把 607 条切开，是三档而不是一档——

| 档 | 条数 | 情形 | 一律置空的代价 |
|---|---|---|---|
| 甲 | **123** | 两栏写的是同一个等级 | 零损失（等级已在 `confidence` 里） |
| 乙 | **399** | **连 `confidence` 键都不存在** | **销毁该条目唯一的等级线索**（涉 37 条记录） |
| 丙 | **85** | 两栏矛盾（84 × `T0-自报` vs `T0-自报-转述`、1 × `T0-自报-转述` vs `T3`） | 置空等于把矛盾连同证据一起抹掉，判哪个错要知道真实转述源 → **属重采** |

我最初就是按「607 条一律置空」去想的，**量完发现那会毁掉乙档 399 条的唯一线索，于是停下来重报重问**。这与 §27 教训 1 同源：**动手前先把「一个数」拆成「几种读法各自多少条」**。

**实现（`scripts/validate_model_data.py`，规则 6.3）**：

- 判据是**正则而不是 `CONFIDENCE_ENUM` 成员判定**：`^T[0-4](?:-自报)?(?:-转述)?(?:-第三方)?$`。实测有 `T2-第三方` 3 条、`T3-转述` 1 条**落在枚举外**，按枚举成员判会漏掉这 4 条（607 → 603）——**枚举是「合法可信度值」的表，不是「长得像可信度值」的表**，这里要查的是后者。
- **三段都查**。`arena_elo` 段此前**完全不读 `source_type`**，该段那 3 条对旧门禁彻底不可见；只改 `self_reported`/`independent` 会漏 3 条（607 → 604）。
- 这条正则**只决定「要不要记一条 WARN 留痕」，绝不驱动任何数据改写**（与用户 2026-09-02 立的「解析不许写死、形状识别只用于留痕」同一原则）。
- **刻意不覆盖**「等级值当前缀缀在真实来源描述前」那 **406 条**（如 `T0 官方一手技术报告（自报）`）：那类信息不丢、只是前缀冗余，混进来会让这条 WARN 同时背两类缺陷 —— 正是 §27 教训 2（一条 WARN 只该对应一类缺陷）禁止的。
  **D18d 补注（2026-09-02）**：这 406 条的**数据**已由 D18d 处置完毕（405 条剥掉前缀、1 条表外 `T1.5-第三方评测` 原样不动，见 §27.3），但**「规则 6.3 不覆盖这类」的取舍没变、理由也仍然成立** —— 不覆盖不是因为漏了，是因为一条 WARN 只该背一类缺陷。现库该类命中已降到 **1**（就是那条表外值），是否另补一条 WARN 级规则 6.4 属单独拍板项（现库命中会是 **0**，纯防回归）。

**验收（全部实测，两个独立计算互相咬合）**：

| 检查 | 结果 |
|---|---|
| 门禁 × ~~现库~~**当时库** | 933 条 / **ERROR 0** / **WARN 640** / exit 0（**这是 D18b 结案时的数；D18c 已把 518 条迁走 → 现库 WARN 122，见 §27.2**） |
| WARN 差额记账 | **640 − 33 = 607**，恰等于独立脚本实测的规则 6.3 命中数（D18c 后同一等式变成 **640 − 122 = 518**） |
| 分段命中 | `self_reported` **600** / `independent` **4** / `arena_elo` **3** = 607，与独立脚本逐项一致 |
| 值分布 | `T0-自报` 379 / `T0-自报-转述` 200 / `T0` 22 / `T2-第三方` 3 / `T3` 2 / `T3-转述` 1 |
| **数据零改动** | md5 仍为 `b5eaf743ebbe462613b3613e04168755`（改前改后同一串；**D18c 已改数据 → 现 md5 `3c88eec4b25afe2e107e4fc5d1a84d77`**） |
| **负对照** | 新门禁 × **改前备份** = WARN **948** = 341 + **607** → 这 607 条**改前改后完全同数**，D18 既没造出也没修掉任何一条 |
| 旧门禁对照 | 旧门禁 × ~~现库~~**当时库** = 33、旧门禁 × 改前备份 = 341（四个组合各自可解释；**D18c 后新门禁 × 现库 = 122**） |
| 文档示例护栏 | `temp/d17c_example_gate.py` 正对照 exit **0** / 负对照 exit **1**，与 D17c 时相同（`prompt.md` 的示例未被新规则误伤） |
| 剩余 33 条构成 | 与新规则命中**零重叠**：`knowledge_cutoff` 格式 9、参数量缺未披露声明 3、`pricing.source_type` 与价格值矛盾 3、有定价缺 `source_url` 1、规则 6.2 主键撞车 17 |

**升 ERROR 的条件**（沿用 §24 规则 1.1/1.2 的写法，避免下一轮凭感觉升级）：下一个采集周期**新记录命中 0**，且这 607 条已重采补全来源类型或按拍板处置完毕。在此之前它必须停在 WARN —— ~~现库~~**当时**存量 607 条（**D18c 已处置 518 条，现剩 89 条 = 丙档 85（两栏矛盾，属重采）+ 枚举外 4（等级本身有争议，见 §27.2）**），判 ERROR 会让门禁对全库直接失败，历史验收信号全部失真。

**仍开着的遗留（规则 6.3 只负责「照出来」，不负责修）**：

- ~~**乙档 399 条要的是「迁移」不是「置空」**：把等级值搬进 `confidence`、来源类型留给重采。但 `T2-第三方` 3 条与 `T3-转述` 1 条**不在 `CONFIDENCE_ENUM` 内**，逐字迁移会立刻造出 ERROR（`confidence` 不在枚举内），得先决定是扩枚举还是改写成 `T2` / `T3`。~~
  **→ ✅ D18c 已结案（见 §27.2）**：第 24 轮拍板「乙档迁移 + 甲档清冗余」。实际迁移 **395** 条（= 399 − 表外 4），甲档 **123** 条一并置空，合计 **518** 个条目。**表外那 4 条既没扩枚举也没改写成 `T2` / `T3`，而是原样不动、单独登记** —— 因为它们的等级本身就有争议，机械改写等于替采集者做判断（理由逐条见 §27.2）。
- **丙档 85 条属重采**（两栏矛盾，无本条证据可裁决）。
- ~~**406 条冗余前缀类无任何门禁信号**，只能靠本清单追踪。~~
  **→ ✅ D18d 已结案（见 §27.3）**：405 条剥掉前缀、1 条表外 `T1.5-第三方评测` 原样不动。但**「无任何门禁信号」这半句没变** —— 规则 6.3 只管「整栏就是一个等级值」，剥完前缀这类写法（如 `T0 官方自报`）在库里归零了，可门禁**仍然不会报**任何一次新写进来的前缀；现在挡它的只有 `prompt.md` 的显式禁令，而文档自己错过两代（§26.5），不能指望它兜住。
- 与 §27 第一类宽口径 438 条**重叠 83 条**（那 83 条的 `source_type` 就是 `T0-自报`）：同一条目背两类缺陷，修的时候要一次修完，别修了一类就以为清了。
  **D18c 复核**：这 83 条**全部落在丙档**（可信度 `T0-自报-转述` × 来源类型 `T0-自报`，丙档共 84 条），丙档本轮一字未动 → **重叠仍是 83 条，一条没减**。别因为规则 6.3 的命中从 607 掉到 89 就以为这批也清了。

**两条教训**：

1. **说「某缺陷已清零」之前，先问判据查的是字段语义还是字符串表面属性。** D18 把「自报分 `source_type` 缺自报」那条 WARN 打到 0，其中 **607 条是空心的** —— 它们含「自报」二字纯粹因为写的是可信度值。归零只证明「不再有裸写法」，不证明「来源类型栏写了来源类型」。这是 §26.1「判据工程盲区」的又一例，也是本轮唯一一处**由上一轮的成功验收照出来的缺陷**。
2. **复算文档里的数字，先确认判据的作用域，再决定是文档错还是自己错。** 本轮复算同时撞到两种情况：宽口径我按三段全扫得 **440**、文档写 **438** —— 查下来是**文档对、我漏了「仅 `self_reported` 段 + 剔除空值」这个作用域**；而冗余前缀类文档写 **405**、实测 **406** —— 这次是**文档真错**。**同一次复算里两种情况并存**：不能因为前一个数对上就放过后一个，也不能因为后一个错了就推翻前一个。已把作用域写进 §27 的判据原文（连带记下放宽作用域后的 440 / 458 / 460），下一个复算的人不必再猜。

**现基线（D18b 收尾）：933 条 / ERROR 0 / WARN ~~640~~（= 常量段 16 + 规则 6.2 的 17 + 规则 6.3 的 607）/ 结构漂移 0 / 精确主键重复 17 组。** 数据 md5 与 D18 收尾时**完全相同**（本轮零数据改动），凡以 WARN 33 为基线的表述自此过时。**→ D18c 改了数据，现基线为 WARN 122、md5 `3c88eec4b25afe2e107e4fc5d1a84d77`，见 §27.2。**


#### 27.2 【D18c】把 §27.1 的乙档迁进正确的栏目，顺带清掉甲档冗余（518 个条目）

**拍板（2026-09-02，第 24 轮）**：§27.1 登记「乙档 399 条要的是迁移不是置空」后单独提请裁定，用户选 **「乙档迁移 + 甲档清冗余」** —— 乙档把等级值逐字搬进可信度栏、来源类型栏置空；甲档（可信度栏已有同值）的来源类型栏一并置空。

**这一批为什么值得做**：乙档 399 条**根本没有 `confidence` 键**（涉 37 条记录），等级信息只写在来源类型栏里。这意味着 §5「任何跑分结论不得仅基于 `T0-自报`」这类规则对它们**根本无从执行** —— 下游读不到可信度。迁移是**把信息搬回它该在的栏目**，不是清洗。

**三档身份由本轮脚本独立重算**（不信任上一轮的中间结果），与 §27.1 登记的 123 / 399 / 85 逐项吻合：

| 档 | 判据 | 条数 | 本轮处置 |
|---|---|---|---|
| 甲 | 有 `confidence` 键且与 `source_type` **逐字相同** | 123（全在 `self_reported`） | `source_type` 置 `null`，可信度栏不动 —— 纯冗余清理、零信息损失 |
| 乙 | **没有 `confidence` 键** | 399（`self_reported` 393 / `independent` 4 / `arena_elo` 2） | 迁移 **395** 条；表外 **4** 条原样不动 |
| 丙 | 有 `confidence` 键但与 `source_type` **不同** | 85（`self_reported` 84 / `arena_elo` 1） | **一字未动** —— 两栏矛盾、无本条证据可裁决，属重采 |

**表外 4 条为什么原样不动**（逐字迁移会立刻把 WARN 换成 ERROR，因为值不在 `CONFIDENCE_ENUM` 内；而机械改写成 `T2` / `T3` 等于替采集者做判断）：

| 条目 | 写的值 | 争议 |
|---|---|---|
| `cognition:swe-1-6:base` / `self_reported[1]` | `T3-转述` | 网址是头条、备注明写「**转述自 Cognition 官方博客**」→ 按 §5.1 与决策 2，厂商自报分经媒体转述本该记 `T0-自报-转述`；记成 `T3` 等于把**厂商的话**当成**媒体的话** |
| `mistral:mistral-large-3:base` / `independent[5][6][7]` | `T2-第三方` ×3 | 三条**同址同标**（网址均为 OpenRouter，第三方托管转述）；其中 **`[5]` 的备注明写「Artificial Analysis 评测」**（`[6][7]` 备注只有基准名，沿用同一来源标注），而 §5.1 把 Artificial Analysis 列为 **T1 独立评测**的典型例子 → 该记 `T1` 还是「T1 经转述」，机械推不出来（枚举里也没有 `T1-转述` 这种值） |

**变换定义**（两条，都可逆）：

1. 乙档 395 条：`confidence` ← 原 `source_type` 值（**逐字搬运，不改写、不归一**），新键插在 `source_type` **紧后面**（库里 4198/4351 条同时有两键时就是这个顺序，也是 `prompt.md` 示例的顺序）；随后 `source_type` ← `null`。
2. 甲档 123 条：只把 `source_type` ← `null`，就地赋值，键序键集都不变。

**为什么置 `null` 而不是删键**：① `prompt.md` 明文「缺失或未披露的数据一律填 `null`」；② 键留着 → 键序不变 → **逆还原只需按值回填，不必记录插入位置**（删键就得记下原下标，多一条会错的地方）；③ 与 D17 的 `available: null`、D16 的五键 `free_tier` 对象同口径。**代价**：来源类型缺失从此有**两种形状**（原本「无键」775 条 + 本轮「值为 null」515 条），将来测缺失数必须两种都数。

**验收（全部先在内跑完才落盘）**：

| 项 | 结果 |
|---|---|
| 前置断言 | 现盘 md5 == 备份 md5 == D18 收尾值 `b5eaf743ebbe462613b3613e04168755`；序列化往返 **933/933 逐字节相同**（`json.dumps(rec, ensure_ascii=False)`，默认分隔符 —— 本库不是压缩写法，先验过才敢用「未改动行逐字节」当 rail） |
| 记录 / 条目 | 933 → 933、5642 → 5642 |
| `score` 多重集 | 相同（5642 个值） |
| 未改动行 | **880/933 逐字节相同**，改动落在 **53** 条记录 |
| 叶子级 diff | 越界路径 **0**（白名单仅 `benchmarks.<段>[i].source_type\|confidence`）；差异 **913** 处 = 乙档 395×2 + 甲档 123×1，与改动定义逐项对上 |
| 逆还原 | 与改前**逐字节相等**（md5 复原为 `b5eaf743…8755`）。删 `confidence` 用 `del`，**不是**置 `null` —— 那会留下原本没有的键（§27 记过这个坑） |
| 键序 | 乙档新增的 `confidence` 紧跟 `source_type`，越位 **0** 条 |
| 迁移保真 | 可信度栏值 ≠ 原来源类型栏值：**0**；来源类型栏未置 null：**0**；除 `confidence` 外多出别的键：**0**；其他键值被改：**0** |
| 甲档保真 | 来源类型栏未置 null：**0**；**可信度栏被改动：0**（甲档只许动一栏）；键集变化：**0** |
| 剩余 89 条身份 | 改后仍被规则 6.3 照出的 **89** 条 == 丙档 85 ∪ 表外 4（按 记录+段+下标 逐条比身份），且这 89 条**一字未动** |
| 未参与条目 | 5124 条中被改动 **0** 条；518 + 5124 = 5642 |
| `benchmarks` 以外 | 顶层非 `benchmarks` 键有差异的记录数 **0** |
| 门禁 | 933 / **ERROR 0** / **WARN 640 → 122**，exit 0 |
| 文档示例护栏 | `temp/d17c_example_gate.py` 正对照 exit **0** / 负对照 exit **1**（本轮未改门禁，护栏应不变，实测不变） |

**WARN 记账（比总数更硬的是「其余各类逐条不变」）**：

| 类别 | 改前 | 改后 | 差 |
|---|---|---|---|
| 规则 6.3 整栏等级值 | 607 | **89** | **−518** |
| 规则 6.2 主键撞车 | 17 | 17 | 0 |
| `knowledge_cutoff` 非 YYYY-MM | 9 | 9 | 0 |
| 参数量缺未披露声明 | 3 | 3 | 0 |
| `pricing.source_type` 与价格值矛盾 | 3 | 3 | 0 |
| 有定价缺 `source_url` | 1 | 1 | 0 |
| **合计** | **640** | **122** | **−518** |

差额 **518 全部落在规则 6.3 一类**，其余五类逐条不变 —— 这正是本轮的可执行等式：**640 − 122 = 518 = 改动条目数**。另有一项改前实测的负对照：`建议体现「自报」属性`那条 WARN 改前改后都是 **0** 命中（迁移后有 22 条可信度变成裸 `T0`，但它们的来源类型栏已置空，那条判据有 `and stype` 前置 → 不报）。**这也正是「只补可信度栏、来源类型栏留着」那个备选方案会多吃 22 条 WARN 的原因**，提请拍板时已量化。

**改后面的存量变化**：

| 量 | 改前 | 改后 |
|---|---|---|
| 可信度栏有键条目 | 4540 | **4935**（+395） |
| 来源类型「无键」 | 775（自报分段）/ 782（三段） | 775 / 782（未变） |
| 来源类型「值为 null」 | 0 / 0 | **515 / 518**（本轮新增的形状） |
| 来源类型缺失合计 | 775 / 782 | **1290 / 1300** |
| 规则 6.3 命中 | 607 | **89**（`self_reported` 85 / `independent` 3 / `arena_elo` 1） |
| 来源类型非空写法种类 | 237 | **235**（`T0` 与 `T3` 两种写法自此在库里消失 —— 它们的每一处出现都被本轮置空了） |

**仍开着的遗留**：① 表外 **4 条**（上表那两条争议，须回原始来源定夺 → 属重采或另请拍板）；② 丙档 **85 条**（两栏矛盾，属重采），其中 **83 条**同时落在 §27 第一类宽口径 438 的重叠里；~~③ **406 条冗余前缀类**（如 `T0 官方一手技术报告（自报）`）仍**无任何门禁信号**，规则 6.3 刻意不覆盖~~ **→ ✅ D18d 已结案（见 §27.3）：405 条剥掉前缀、1 条 `T1.5-第三方评测` 原样不动；但「无任何门禁信号」这一点没变，剥完之后仍然没有规则拦得住新采集再写一遍**；④ 来源类型缺失涨到 **1290 / 1300**，门禁放过空值 → 这批对门禁完全不可见，只能靠本清单追踪。

**两条教训**：

1. **「置空会销毁唯一线索」这条在 §27.1 救回 399 条，本轮把它兑现成迁移动作 —— 但迁移前必须先量「值在不在合法值表内」。** 若当初按「一律迁移」动手，那 4 条会把 WARN 换成 **ERROR**（`confidence` 不在枚举内），门禁直接对全库失败。**规律：把信息从 A 栏搬到 B 栏之前，先确认 B 栏的合法值表能接住 A 栏的写法**；接不住的那几条要单独拎出来，不要为了让变换统一而改写它们。
2. **打印语句与断言不一致时，以断言为准，但那行打印必须当场修掉。** 本轮收尾核对脚本第一版打印「改后命中里本轮被改过的条目数：89（必须为 0）」，紧随其后的断言却通过了 —— 因为打印用了 `eo[k] is not en[k]`，对两个分别解析出来的 dict 恒为真。**断言才是取证件，打印只是给人看的**；但若不修，下一个人（包括未来的我）会照着那个 89 写文档。已改为按值比较并重跑，报告与断言一致。

**文档同日改**：`prompt.md` 两处 —— 「别把可信度值当来源类型写」那段把 607 的分布划掉、补 D18c 后的 **89 条 / 12 条记录**实测分布与剩 89 条构成，指南指针扩到 §27.1 / §27.2；**可信度等级那一行下新增显式禁令**「这七个值是穷举，写枚举外值门禁直接判 ERROR」，并把表外 4 条的两处争议原文抄进去当反例（新采集只准写这七个值，「第三方」「转述」这类限定写进 `source_type` / `notes`）。`qa_report.md` 抬头十五→**十七处**、第 16 项的乙档遗留划掉指向新增的**第 17 项**、§1 与 §6.2 的 WARN 演进行同步到 122、抬头 `temp/*.py` 声明的轮次范围 `D2–D15` → `D2–D18c`（第 16/17 项已引用 D18b/D18c 的本机脚本）。`docs/交接_2026-09-01_D16结案.md` 横幅补 D18c 与新基线。记忆两处同步（`docs/memory/project/project-stage3-gaps.md` 为权威副本 + 平台目录，md5 逐字比对）。

**现基线：933 条 / ERROR 0 / WARN 122（= 常量段 16 + 规则 6.2 的 17 + 规则 6.3 的 89）/ 结构漂移 0 / 精确主键重复 17 组。** 数据 md5 `b5eaf743ebbe462613b3613e04168755` → **`3c88eec4b25afe2e107e4fc5d1a84d77`**，备份 `model_data_v2.jsonl.d18cbak-20260902-201552`（已被 `.gitignore` 忽略）。凡以 WARN 640 为基线的表述自此过时，但历史行的 640 是对的。

---

### §27.3 D18d：剥掉来源类型栏的冗余等级前缀（405 条，2026-09-02 同日续）

**第 25 轮拍板「全剥 406 + 补挂「自报」+ 粘连的迁进可信度栏」**，处置 §27.1 刻意不覆盖、§27.2 遗留 ③ 登记的那批：`source_type` 把可信度等级值**当前缀**缀在真实来源描述前（如 `T0 官方自报`、`T0-自报 官方一手`）。

**判据与数量（三个口径一起给）**：

| 口径 | 判据原文 | 命中 |
|---|---|---|
| 以等级开头 | `source_type` 非空 且 `^\s*T[0-4]` | 495 |
| 纯等级值（= 规则 6.3 现存量） | 整栏就是一个等级值 | 89 |
| **前缀类（本轮对象）** | **以等级开头 − 纯等级值** | **406** |

D18b 记的是 `1013 − 607 = 406`；本轮实测 `495 − 89 = 406`，**两个算式在不同库快照上得同一个数** → D18c 一条没碰这类。涉及 **52 条记录 / 32 种写法**，分段 自报 399 / 独立 7（`arena_elo` 0）。

**关键发现：406 条里没有一条是「两栏等级打架」。** 按同一条目的 `confidence` 分三档：同值 **84**（前缀纯冗余）/ `confidence` **更具体 316**（前缀 `T0`→`T0-自报` 292、`T0`→`T0-自报-转述` 21、`T0-自报`→`T0-自报-转述` 3）/ `confidence` **无键 6**。也就是说前缀要么重复、要么是欠具体的那一半 —— **这是「可以机械剥」的前提**，若有一档是真矛盾就必须停下来另请拍板（丙档 85 条就是那种，本轮一字未动）。

**变换（三条规则，互斥且穷尽）**：

1. **剥前缀**：`source_type` ← 去掉开头的等级值与其后分隔符，**正文一个字不动**。切分只靠「已知等级值表最长匹配 + 其后分隔符」，不写死任何一条具体写法。
2. **补挂「（自报）」**：剥完后若 `section == self_reported` 且**终态** `confidence` ∈ T0 家族且新值不含「自报」→ 末尾挂后缀（与 D18 同一规矩、同样容忍双括号）。命中 **55** 条。
3. **迁移等级**：6 条 `confidence` 无键的里，**5** 条 `T0-自报-技术报告`（等级与描述**粘连无分隔符**，`google:gemma-2-27b:base` 自报段 `[0]`–`[4]`）复用 D18c 的变换把 `T0-自报` 逐字搬进 `confidence`（新键插在 `source_type` 紧后）、来源类型留 `技术报告` 再走规则 2；**第 6 条 `T1.5-第三方评测`（`deepseek:deepseekmoe-16b:base` / `independent[0]`）原样不动** —— `T1.5` 不在 `CONFIDENCE_ENUM` 内，搬进去即 ERROR，机械改写成 `T1`/`T2` 又等于替采集者做判断（与 §27.2 表外 4 条同一处置）。

**实际写盘 405 个条目 / 51 条记录**（= 406 − 表外 1）。

**提请拍板时量化了备选方案的副作用**：「只剥不补挂」会让 **55** 条的「自报」二字消失（那 55 条的自报属性**只活在前缀里**）→ 新撞门禁「建议体现自报属性」WARN，**122 变 177**；补挂后新增 **0**。这正是 D18 那一轮的规矩在本轮的复用：**变换统一比好看重要，因为逆还原是验收手段**。

**验收（`temp/d18d_verify.py` 独立复算，只读备份与现盘对推，刻意不复用变换脚本的任何函数）**：

| 检查 | 结果 |
|---|---|
| 前置断言 | 现盘 md5 == HEAD == 备份 `3c88eec4b25afe2e107e4fc5d1a84d77`；序列化往返 933/933 逐字节；文件纯 LF（CR 0 个） |
| 双锁 | 记录 933 → 933；跑分条目 5642 → 5642 |
| 记录身份 | `model_id` 序列逐一相同；顶层键集与键序逐一相同 |
| 叶子级 diff | 差异叶子 **410**；**越界路径 0**（白名单仅 `benchmarks.<段>[i].source_type｜confidence`）；被触及条目 **405**（只改来源类型 400 + 两栏都改 5）；差异叶子 ≥3 的条目 **0** |
| 分数零改动 | `(score, score_type, benchmark, config)` 多重集相同（5642 项） |
| **逆还原** | 逐条通过 **405/405**；头部只能是「一个等级值 + 分隔符」→ 不存在第二种拆法；**两分支同时成立 0 条**（否则逆还原不唯一、本项 rail 失效）；补挂与必要性逐条相符 |
| 键序 | 5 条新增 `confidence` 键紧跟 `source_type`、值在 `CONFIDENCE_ENUM` 内、旧值以该等级值开头 —— 全通过 |
| 未改动行 | **882 / 933** 逐字节相同（改动落在 51 条记录） |
| **信息零损失** | 判据：被剥的等级值改后必须仍能在同一条目的 `confidence` 里读到（同值或更具体）→ 不满足 **0** 条；分布 更具体 **316** / 同值 **89**（= 84 + 迁移的 5） |
| 剥离后形状 | 空值 **0**、整栏是等级值 **0**（不新撞规则 6.3）、仍以 `T0`–`T4` 开头 **0**（无双重前缀） |
| 表外 1 条 | `T1.5-第三方评测` 改前改后**逐键相同** |
| 门禁 | 933 / **ERROR 0** / **WARN 122 → 122**，exit 0；门禁脚本 md5 `f70bcb836488860eb2708dd67625449e` **一字未改** |
| **负对照** | 门禁 × 改前备份 = **同样 122**；且两份报告**除标题里的文件名外逐字节相同**（194 行 / WARN 分类逐条同文） |
| 文档示例护栏 | `temp/d17c_example_gate.py` 正对照 exit **0** / 负对照 exit **1**（`prompt.md` 的示例未被本轮误伤） |

**「两份门禁报告逐字节同文」是本轮最该记住的一条验收结论**：它说明这次改动**对门禁完全不可见** —— 122 条 WARN 改前改后同一批、同一段文字。价值是**语义的**（这一栏终于写它名字所说的东西），不是分数的、也不是门禁的。**推论：剥完之后仍然没有任何规则拦得住新采集再写一遍前缀**，唯一的防线是 `prompt.md` 里的显式禁令，而 §26.5 已经证明文档自己错过两代。（是否补一条 WARN 级规则 6.4 单独提请拍板 —— 现库命中会是 **0**，属纯防回归。）

**改后存量变化**：

| 量 | 改前 | 改后 |
|---|---|---|
| 以等级开头 | 495 | **90**（= 纯等级值 89 + 表外 1；差额 **405** = 本轮改动条目数） |
| 前缀类命中 | 406 | **1** |
| 规则 6.3 命中 | 89 | **89**（本轮一条不碰纯等级值） |
| 来源类型非空条目 | 4342 | **4342**（本轮既不新造 `null` 也不删键） |
| 非空写法种类 | 235 | **228**（消失 **31** 种、新出现 **24** 种、两版共有 204；`235 − 31 + 24 = 228`） |
| 含「自报」写法种类 | 178 | **171** |
| **含「自报」条目数** | **2567** | **2567（一条不变）** |
| 含「转述」写法种类 / 条目 | 62 / 641 | **61 / 636**（少的 5 条见下） |
| 可信度栏有键条目 | 4935 | **4940**（+5） |
| 来源类型缺失三形状 | 非空 4342 + 无键 782 + 值为 null 518 | 同（**正好瓜分 5642**，改前改后都是） |

**「含自报条目 2567 → 2567 一条不变」是本轮的保真断言**：种类数从 178 收到 171 只说明**重复写法被合并**，没有任何条目被加上或摘掉「自报」属性。**验收这一栏时必须两个数一起看** —— 只看种类数会分不清「归一」与「改判」。

**5 条丢「转述」二字的已逐条核过**：`china-mobile:jiutian-139moe:base` 自报段 `[0]`–`[4]`，`T0-自报-转述（官方技术报告）` → `（官方技术报告）（自报）`；这 5 条的 `confidence` **本来就是 `T0-自报-转述`**，转述属性没丢，只是不再在来源类型栏里重复一遍。新值读感不佳（括号开头 + 双括号尾），属**已知的外观遗留**，本轮不改 —— 改写正文会引入第二类变换、要另配一套 rail。

**四条教训**：

1. **逆还原脚本不得假定「那个后缀是本轮挂上去的」。** 验收脚本第一版无条件剥掉末尾的「（自报）」，于是在 20 条 `T0 官方一手技术报告（自报）` 上报「旧值不以新值主体结尾」—— 那个后缀是 **D18** 挂的、本轮一个字没动。修法：**两分支对推**（A 旧值以新值原样结尾 = 本轮没挂；B 新值以后缀结尾且旧值以「新值去后缀」结尾 = 本轮挂了），并**断言两分支同时成立的条目数为 0** —— 不为 0 就说明头部有两种拆法、逆还原不唯一，整条 rail 直接失效。**这是三轮里第三次「验收脚本自己的 bug 报出假警」**（D18 是 `.get()` 凭空造键、D18c 是 `is not` 比两个 dict 恒真），规律：**逆还原报不等，先怀疑验收脚本，再怀疑数据；但修完必须补一条「唯一性」断言，否则改对了也说不清。**
2. **正则字符类里的 `-` 必须放最后（或转义）。** `[ \t:：、,，)）-—]` 被解析成 `）`→`—` 的**范围**（U+FF09 → U+2014），Python 直接报 `bad character range`；**运气在于起止反了才报错** —— 若写成 `[...)-—]`（`)` 是 U+0029）就是一个**合法**范围，会静默匹配包括全部 CJK 在内的约 8000 个字符，判据全废而不报错。**判据里的每个字符类都要拿正反例逐个自测**（本轮 10 个：`T0 `/`T0-自报`/`T0-自报-`/`T1:`/`T0-自报-转述` 该过，`T0 官方`/`官方自报`/`T0-自报 官方一手`/`T9 `/`T05 ` 该拦）。
3. **报数前先确认作用域 —— 这条第三次应验。** 我按 §27.2 的「自报分段」口径预测缺失形状是 775 / 515，而验收脚本扫的是三段，真值 **782 / 518**。自洽检验是**三形状必须正好瓜分 5642**（`4342 + 782 + 518`），改前改后都要成立；有这个等式在，作用域写错会当场暴露。
4. **「零信息损失」必须逐条论证，不能断言「应该没丢」。** 判据写成了可执行的形式：*被剥掉的等级值，改后必须仍能在同一条目的 `confidence` 里读到（同值，或 confidence 是它的更具体形式）* → 405/405 通过、不满足 0 条。**没有这条判据，「前缀是冗余的」就只是我的印象**；有了它，这个印象变成一个能被推翻的断言。

**仍开着的遗留**：① 表外 **1 条** `T1.5-第三方评测`（`T1.5` 不是合法等级，属重采或另请拍板）；② ~~**没有任何门禁规则照这类前缀**，剥完之后防回归只剩文档禁令（规则 6.4 待拍板，现库命中会是 0）~~ **→ ✅ D18e 已结案（见 §27.4）**：第 26 轮拍板补了 WARN 级**规则 6.4**，现库命中确为 **0**、WARN 基线仍是 122，防回归**不再只有文档禁令在守**；③ 写法**仍不收敛**：228 种里本轮新造出 24 种，剥后 31 种结果只有 **7 种**是库里原有的 —— 这一栏要真正归一得另起一轮；④ 5 条 `（官方技术报告）（自报）` 读感不佳（外观遗留）；⑤ 丙档 **85 条**、§27.2 表外 **4 条**、来源类型缺失 **1300**（三段）全部原样在册。

**文档同日改**：`prompt.md` 两处 —— 把「另有 406 条…」划掉换成 D18d 结案实测（405 / 55 / 5 / 1 与零损失论证），并**新增面向新采集的显式禁令**「不得把等级值当前缀写进 `source_type`」，同时如实写明「目前没有任何门禁规则照这类，只有本文档在守」；含自报写法种类 178 → 171 就地更正，并补上「种类数会降但含自报**条目数**不该动（2567 → 2567）」这条验收口径。`qa_report.md` 抬头十七→**十八处**、新增**第 18 项**、WARN 演进行补 D18d（122 不变，改的是数据不是门禁）。`docs/交接_2026-09-01_D16结案.md` 横幅补 D18d 与新 md5。记忆两处同步。

**现基线：933 条 / ERROR 0 / WARN 122（= 常量段 16 + 规则 6.2 的 17 + 规则 6.3 的 89）/ 结构漂移 0 / 精确主键重复 17 组。** 数据 md5 `3c88eec4b25afe2e107e4fc5d1a84d77` → **`3553105b811c7104199d7de2b8052e91`**，备份 `model_data_v2.jsonl.d18dbak-20260902-210735`（已被 `.gitignore` 忽略）。**WARN 数与 D18c 收尾时完全相同** —— 本轮改的是数据的语义，不是门禁的口径，别把「WARN 没动」误读成「这轮什么都没做」。

---

### §27.4 D18e：给前缀类补门禁留痕 = WARN 级规则 6.4（2026-09-02 同日续，零数据改动）

**第 26 轮拍板「补，用『等级值 + 分隔符 + 主体』形」**，处置 §27.3 遗留 ②：D18d 把存量剥净之后，**没有任何机制阻止新采集把它写回来**，挡它的只有 `prompt.md` 一句禁令 —— 而 §26.5 已实证文档自己错过两代、且门禁只校验记录不校验文档。

**判据形是三选一，先把三个形都量过再提请拍板**（`temp/d18e_rule64_measure.py`，现库与改前备份各跑一遍）：

| 判据形 | 判据原文 | 现库命中 | 改前备份命中 | 差额 | 与规则 6.3 重叠 |
|---|---|---|---|---|---|
| A 以等级开头就算 | 非空 ∧ `^\s*T[0-4]` ∧ ¬纯等级值 | 1 | 406 | 405 | 0（构造上互斥） |
| B 等级值 + 分隔符 + 主体（**未加前置**） | `^\s*T[0-4](…)?[sep]+.+$` | 89 | 494 | 405 | **89（全部重复计）** |
| **B′ = B + ¬纯等级值前置（选定）** | 同上 ∧ `not TIER_ONLY_STYPE_RE` | **0** | **405** | **405** | **0** |
| C 只看开头（最宽，含纯等级值） | 非空 ∧ `^\s*T[0-4]` | 90 | 495 | 405 | 89 |

**三个形的差额都是 405，恰等于 D18d 的实写条目数** —— 这反过来给 D18d 又添了一道独立负对照（D18d 自己的等式是「以等级开头 495 → 90」，与这里的 A/C 两形互相印证）。

**选 B′ 而不选 A 的理由**：A 形现库命中 **1**，就是 §27.3 刻意不动的那条表外值 `T1.5-第三方评测`（`deepseek:deepseekmoe-16b:base` 独立段第 1 条），它会把 WARN 基线从 122 推到 **123**，而且是**以「前缀冗余」的名义**报一条真正的缺陷是「等级值不在 `CONFIDENCE_ENUM` 内」的条目 —— 与本轮和 D18b 两次援引的「一条 WARN 只背一类缺陷」直接冲突。B′ 形照不到它（`T1.5` 后接的是 `.` 不是分隔符），**这是有意的**：那条仍由 §27.3 清单与 `prompt.md` 追踪，等「枚举外可信度值」那一项单独处置。

**选定判据的实现要点（三条都写在 `TIER_PREFIX_STYPE_RE` 上方注释里）**：

1. **调用处那道 `and not TIER_ONLY_STYPE_RE.match(stype)` 前置是必需的，不是保险。** 分隔符表含 `-`，少了它 `"T0-自报"` 会被解析成「`T0` + 分隔符 `-` + 主体 `自报`」而同时命中 6.3 —— 实测重复计 **89 条**（上表 B 形那一行就是这个 bug 的量）。两条规则各背一类：6.3 = 整栏就是一个等级值（零来源信息）；6.4 = 等级值只是前缀（来源信息在，但一栏背两种语义）。
2. **分隔符字符类里 `-` 必须放在最末**（`[ \t:：、,，)）—-]`）。写成 `)）-—` 会把 `）-—` 解析成 U+FF09→U+2014 的范围而报 `bad character range`；**更糟的是若 ASCII `)` 排在前面，那是个合法的反向范围，会静默匹配约 8000 个 CJK 字符** —— 报错比沉默安全，这条在 §27.3 教训 2 已经栽过一次。
3. **跑分三段都查**。`arena_elo` 段此前完全不读 `source_type`，D18b 补 6.3 时才纳入；6.4 同样要在该段查，否则该段的前缀写法照旧不可见（改前备份实测本段命中 **0**，但判据不能靠这个省略 —— 下一批采集未必也是 0）。

**验收（零数据改动，所以 rails 全在门禁侧）**：

- **2×2 负对照矩阵，四个组合各自可解释**：旧门禁 × 现库 = **122**、旧门禁 × 改前备份 = **122**（印证 D18d 那句「两份报告除标题外逐字节相同」）、新门禁 × 现库 = **122**（规则 6.4 命中 0 → 基线一条不增）、新门禁 × 改前备份 = **527 = 122 + 405**（差额恰等于 D18d 实写条目数）。
- **现库 WARN 构成逐项复核**：规则 6.3 的 89 + 规则 6.2 的 17 + 常量段 16 + **规则 6.4 的 0** = **122**，且 933 条 / ERROR 0 / exit 0。
- **五个探针的正对照（本轮最要紧的一道）**：现库命中为 **0**，意味着「这条规则真的会响」在真库上**拿不到任何证据** —— 写错变量名、放错循环、正则不匹配，都会静默表现为「命中 0」，与「库里真干净」在门禁输出上**完全无法区分**。所以必须自己造探针（`temp/d18e_probe.py`）。载体挑 `alibaba:qwen2-1-5b:base`（全库 95 条合格载体之一），三条挑选条件：原值非空且本身不触发 6.3/6.4、`confidence` 不在 T0 家族（否则「建议体现自报属性」会跟着 `source_type` 变、混淆计数）、整条记录无任何 6.3/6.4 命中。

  | 探针 | `source_type` | ERROR | WARN | 6.4 响 | 6.3 响 | 判定 |
  |---|---|---|---|---|---|---|
  | P0 | 原样不动（只走一遍重写） | 0 | 122 | 否 | 否 | PASS |
  | P1 | `T0 官方自报` | 0 | **123** | **是** | 否 | PASS |
  | P2 | `T0-自报` | 0 | **123** | 否 | **是** | PASS |
  | P3 | `T1.5-第三方评测` | 0 | 122 | 否 | 否 | PASS |
  | P4 | `官方技术报告（自报）` | 0 | 122 | 否 | 否 | PASS |

  P0 另有一道前置：重写后的临时文件与真库 **md5 逐字节相同**（`3553105b…`）—— 若重写本身引入差异，P1–P4 的计数差里就混着序列化噪音，无从归因。P1 证明规则接通了、P2 证明与 6.3 互斥、P3 证明刻意不覆盖表外值这条取舍真的生效、P4 证明本来就该这么写的值不误伤。
- **数据文件 md5 `3553105b811c7104199d7de2b8052e91` 一字未变**，`git status` 只有门禁脚本一个改动项。
- **文档示例护栏** `temp/d17c_example_gate.py` 仍正对照 exit 0 / 负对照 exit 1（`prompt.md` 的 ```jsonl 示例里没有前缀写法，所以新规则不打它 —— 这本身也是一次确认）。
- **门禁脚本 md5 `f70bcb836488860eb2708dd67625449e` → `6ea4de427c0875375b9fd83f6f0cf1c3`**（D18c 与 D18d 两轮都没动过它，本轮是这三轮里唯一一次改门禁）。这条与上一条「数据 md5 一字未变」是一对：**本轮动的是门禁 md5，D18d 动的是数据 md5** —— 两轮 WARN 都停在 122，读的人靠「哪个 md5 动了」分辨是「改了数据而门禁照不到」还是「改了门禁而现库本来就干净」。

**一条教训（本轮唯一，但是第四次同类）**：**验收脚本自己的判据错，会报出与被验对象无关的假警。** 探针第一版五个里四个 FAIL，看着像「规则 6.4 没接通或互斥性破了」，实际门禁全对 —— 错在探针用 `MSG_63 in rep` 做**整份报告范围**的子串匹配，而真库本来就有 **89 条**规则 6.3 的 WARN，这句恒真。修法是**按 `## \`model_id\`` 标题精确截出载体自己那一段再搜**（注意 `alibaba:qwen2-1-5b:base` 与 `alibaba:qwen2-0-5b:base` 只差一个字符，子串匹配会串到隔壁段），并补一道防呆：**期望至少一条要响时，载体段必须非空** —— 否则截段失败会静默返回空串，让 P0/P3/P4 假通过、P1/P2 假失败，诊断信息还指错方向。这是 D18 的 `.get()` 凭空造键、D18c 的 `is not` 比两个 dict 恒真、D18d 的无条件剥后缀之后的**第四次**。规律补一句：**判据的作用域要与被验对象的作用域一致 —— 验一条记录就在那条记录的段落里搜，别在整份报告里搜。**

**升 ERROR 的条件**沿用 §24 规则 1.1/1.2 与 §27.1 规则 6.3：下一个采集周期新记录命中 0（现库已经是 0，所以这个条件从加上那一刻就成立一半）且存量已处置 —— 但**本轮刻意不升**，与 1.1/1.2/6.3 停在 WARN 的口径一致。

**仍开着的遗留**：① ~~表外 `T1.5-第三方评测` **1 条**（6.4 刻意照不到，属「枚举外可信度值」那一项，与 §27.2 表外 4 条同类）~~ **✅ 已由 §27.5（D19）结案**；② ~~§27.2 表外 **4 条**（`T2-第三方` 3 + `T3-转述` 1，等级本身有争议）~~ **✅ 已由 §27.5（D19）结案**；③ 丙档 **85 条**属重采；④ 来源类型缺失 **1300**（三段，两种形状）门禁放过、只能靠清单追踪（D19 后 **1305** = 无键 782 + 值为 null 523）；⑤ 该栏**仍不收敛**（228 种写法，D19 后 **225**）；⑥ 5 条双括号观感遗留。

**文档同日改**：`prompt.md` 一处 —— 把 D18d 写下的「目前没有任何门禁规则照这类，这条禁令只有本文档在守」划掉换成 D18e 实况（规则 6.4 会报、现库命中 0、与 6.3 互斥、刻意照不到表外那条），指针扩到 **§27.4**；本指南 §27.3 遗留 ② 加删除线指向本节、抬头 `temp/*.py` 轮次范围 `D2–D18d` → `D2–D18e`；`qa_report.md` 抬头十八→**十九处**、新增**第 19 项**；`docs/交接_2026-09-01_D16结案.md` 横幅补 D18e 与门禁脚本 md5 变化。记忆两处同步。

**现基线：933 条 / ERROR 0 / WARN 122（= 常量段 16 + 规则 6.2 的 17 + 规则 6.3 的 89 + 规则 6.4 的 0）/ 结构漂移 0 / 精确主键重复 17 组。** 数据 md5 **`3553105b811c7104199d7de2b8052e91` 一字未变**（本轮零数据改动）。**WARN 数与 D18d 收尾时相同，但这次的原因和上次不一样**：D18d 是「改了数据而门禁照不到」，D18e 是「改了门禁而现库本来就干净」—— 两轮都表现为 122 不变，读的人要靠 md5 分辨是哪一类（数据 md5 变 = 前者，门禁 md5 变 = 后者）。

---

### §27.5 D19：来源类型栏里 5 条「枚举外可信度值」按记录内证据逐条定级（5 个条目，2026-09-02 同日续）

**第 27 轮拍板原文**：**「按建议逐条定级」** —— 三档判据扫出来的 5 条表外值，按本条记录内的证据逐条判定等级，不按兄弟条目、不替采集者猜。

**这类缺陷是什么**：`source_type` 那一栏写了**不在 `CONFIDENCE_ENUM` 七个值之内**的等级写法（`T3-转述`、`T2-第三方`、`T1.5-第三方评测`）。它是 §27.2（D18c）表外 4 条与 §27.3（D18d）表外 1 条**留下的同一批**，两轮都因为「逐字迁移进 `confidence` 会直接造 ERROR（枚举外值），机械改写成 `T2`/`T3` 又等于替采集者做判断」而**刻意原样不动**。本轮把它做完。

**判据口径（报数必须带的三个数，别只报一个）**：
- **窄口径**：`source_type` 整栏就是一个 `CONFIDENCE_ENUM` 之外的等级写法 → **5 条**（本轮处置对象）。
- **中口径**：`source_type` 栏内**任何位置**出现等级形状 → 111 条，其中开头形 90 条已被规则 6.3 / 6.4 / 本轮覆盖，**差额 21 条是 D19 顺带发现的一个从没被登记过的缺陷类**（括号后缀形，见下「遗留 ①」与 `temp/d19_suffix_class.py`）。
- **宽口径**：递归扫**全记录所有字段** → 命中 2 条但**全不在 `source_type`**，是 `pricing.notes` 与 `meta.notes` 的自由文本（两条 gemini 记录，如「定价来自历史公开记录 (T3-转述)」）。**教训：字段级判据必须按字段路径扫，递归扫自由文本会造出假命中，看起来像「还有遗留」。**

**五条定级（逐条给依据，这是本轮唯一有判断含量的地方）**

| 记录 | 位置 | 旧 `source_type` | 新 `confidence` | 定级依据 |
|---|---|---|---|---|
| `cognition:swe-1-6:base` | 自报[1] | `T3-转述` | **`T0-自报-转述`** | `prompt.md` 决策 2 明文：厂商自报分经行业媒体转述且官方报告不可直访 → **必须**标此值。原记 `T3` 把「转述载体」当成了「可信度」，恰好是决策 2 要纠正的那个错法 |
| `mistral:mistral-large-3:base` | 独立[5] | `T2-第三方` | **`T1`** | 本条 `notes` 明写「Artificial Analysis 评测」，§5.1 把 AA 明确列为 T1 独立评测 |
| 同上 | 独立[6] | `T2-第三方` | **`T2`** | 本条**无任何来源归属证据**。禁止抄兄弟条目 [5] 的结论；只能按 `source_url` 是 OpenRouter 转述定 T2 |
| 同上 | 独立[7] | `T2-第三方` | **`T2`** | 同上 |
| `deepseek:deepseekmoe-16b:base` | 独立[0] | `T1.5-第三方评测` | **`T3`** | §5.1 距离原则：媒体报道第三方评测是**二手转述**。`T1.5` 这个等级在枚举里根本不存在，是采集者自造的中间档 |

**变换规则**（沿 §27.2 乙档做法，两条）：① `confidence` ← 定级值，**新键紧插在 `source_type` 之后**（库里两键并存的 4198/4351 主流键序，这样键序不变、逆还原只需 `del` 一个键）；② 随后 `source_type` ← **`null`**（不删键），登记待重采 —— 因为定完级以后那一栏就没有可信的内容了，留着旧的表外字符串等于留一个门禁照不到的错值。

**验收（`temp/d19_apply.py`，rails 全部先在内存跑完才 `--apply`）**：前置断言现盘 md5 == `git HEAD` blob == `3553105b…`、门禁脚本 md5 == D18e 那一版 `6ea4de42…`（本轮不该碰它）、序列化往返 **933/933 逐字节**；五条旧值与「该条目原本没有 `confidence` 键」逐条锁定、五个新值全在 `CONFIDENCE_ENUM` 内（→ 不新增 ERROR）、新键位置断言；记录 933→933、跑分条目 5642→5642、`score` 多重集相同（5478 个非空分数）、叶子差异 **10 处**（5 条 × 两栏）且**越界路径 0**、未参与的 **5637 条被改动 0**、**逆还原与改前逐字节相等**并补「实际执行 5 次而非 0 次」的计数防呆、**`model_id` 全库唯一已断言**（此前 D6–D18e 所有脚本都**隐含**这个假设而从没验过，而库里有 17 组重复主键 —— 假设不是显然的）、不变量含「自报」条目 **2567 → 2567 一条不变**（§27.3 建立的那道 rail 仍然成立）。**改后存量**：非空 4342 → **4337**、值为 null 518 → **523**、无键 782 → **782**（本轮不新造无键）、可信度栏有键 4940 → **4945**、非空写法 **228 → 225 种**。**门禁 933 / ERROR 0 / WARN 122 → 118**，差额 **−4 全部落在规则 6.3（89 → 85）**，其余六类逐条不变 —— 四条而不是五条减 6.3，因为第 5 条（`T1.5`）本来就在 6.3/6.4 之外、它减的是「表外」那一项而不是 WARN。

**本轮教训（同类第五次，且是最贵的一次）**：验收断言写成 `(mb + mvb, ma + mva) == ((782,518),(782,523))` —— `mb + mvb` 是**整数加法**（1300），拿它跟元组比恒不等 → 这道 rail **假失败**，而同一条语句里打印出来的四个数**全对**。前四次：D18 `.get()` 凭空造键、D18c `is not` 比两个 separately-parsed dict 恒真、D18d 无条件剥掉别轮的 suffix、D18e 探针在整份报告里搜只属于一条记录的消息。**规律补全：判据的作用域、操作数的类型都要与被验对象一致；而且「假失败」和「假通过」一样贵 —— 它会把人推向完全错误的方向去改本没有问题的数据代码。** 另两条：**① 隐含假设要写成断言**（`model_id` 唯一性被所有脚本用了十几轮而从没验过）；**② 定级不许抄兄弟条目**，同一记录里 `[5]` 有 AA 证据、`[6][7]` 没有，就必须是 `T1` / `T2` / `T2` 三个不同结果 —— 一致性能省事，但那是拿别人的证据给自己的条目背书。

**仍开着的遗留**：① **【下一项，证据已备齐】等级值当「括号后缀」写在来源类型栏 21 条 / 3 条记录**（`官方模型卡自报（T0 直采）` 10 / `官方自报（T0 官方一手）` 7 / `官方论文自报（T0 直采）` 3 / `官方 GitHub 自报（T0 直采）` 1）—— 是 §27.3 前缀类的**镜像**，`confidence` 全是 `T0-自报`、与括号里的 `T0` **一致 21 / 不一致 0 / 无键 0** → 与 D18c 甲档同类，剥掉是零损失而非迁移；剥完主体仍含「自报」→ **新触发那条 WARN 0 条**；这类**至今无任何门禁规则照它**（6.3 只管整栏纯等级值、6.4 只管开头形）。② 丙档 85 条属重采。③ 来源类型缺失 **1305**（无键 782 + null 523）。④ 该栏仍不收敛（**225 种**）。⑤ 5 条双括号观感遗留。

**文档同日改**：`prompt.md` 一处 —— 把「另有 5 条枚举外写法登记待单独处置」换成 D19 结案（五条定级结果与依据），并新增「定级不许抄兄弟条目」这条口径，指针扩到 **§27.5**；本指南 §27.4 遗留 ①② 加删除线指向本节、抬头 `temp/*.py` 轮次范围 `D2–D18e` → `D2–D19`；`qa_report.md` 抬头十九→**二十处**、新增**第 20 项**、§1 与 §6.2 基线同步 118；新增 **`docs/交接_2026-09-02_D19结案_换平台接手卡.md`**（面向零上下文读者的全面落盘档：现状态、命令原文、环境陷阱、待拍板清单、红线、被推翻的直觉十条）。记忆两处同步。

**现基线：933 条 / ERROR 0 / WARN 118（= 规则 6.3 的 85 + 规则 6.2 的 17 + `knowledge_cutoff` 9 + 参数量声明 3 + 定价矛盾 3 + 缺 `source_url` 1 + 规则 6.4 的 0）/ 结构漂移 0 / 精确主键重复 17 组；数据 md5 `3553105b811c7104199d7de2b8052e91` → `ceff15e9a12709ab3d49679f3d1560f5`，门禁脚本 md5 `6ea4de427c0875375b9fd83f6f0cf1c3` 一字未动，备份 `model_data_v2.jsonl.d19bak-20260902-224225`。**

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
- 2026-08-30 v2.1（整改轮 D10：把 D9 漏掉的三种写法也归一，并按顺序扩规则 6.1）：`temp/d10_normalize_benchmark_keys2.py` 归一 **57 条 / 11 记录**（`benchmark_name` 30、`metric_name` 23、`arena_elo` 误用 `benchmark` 4），验收同 D9（逐条反向还原逐字节相等、同时锁记录数与条目数、逐条 `check_record` 不新增 ERROR），另加「改前/改后主键重复数组数」对照（22 → 22，未凭空造新冲突）。数据清干净后才把**规则 6.1 扩成「缺 canonical 主键即报」**，负对照用两个改前备份实测 **746 = 689 + 57**（D10 前）与 **2039 = 689 + 1293 + 57**（D9 前），现库回到 **940 条 ERROR 0 / WARN 689、缺 canonical 主键 0**。剩 8 条同时带 `benchmark` 与 `name` 的冗余条目主键已在、不影响去重，未动。
  - **另记**：`docs/unconfirmed_models.jsonl`（D6 隔离档）里 15 条 legacy `name` 条目**刻意不归一**（归档价值在与搬出时逐字节一致），登记为规则 6.1 的唯一已知豁免，见 §19 末与 §17.1。
- 2026-08-30 v2.2（整改轮 D11：39 组主键撞车结案）：新增 **§20**。先量化再定口径，推翻了「两个来源分数打架」的设想 —— **38/39 组内 `confidence` 全同**（「取高 confidence」只能裁决 1 组、`date` 0 组、`source_type` 1 组），**35 组同名不同分里 34 组整组只有一个 `source_url`** → 真实毛病是**主键不足以标识一次测量**。按「notes 能否复原区别」分五档处置：A 15 组填 `config`、B 5 组把 `score_type` 口径追加进 `config`、C 1 组（RSG 10 条子任务）拆进 `benchmark` 名、D 4 组纯重复删后到的一条、**E 14 组不动，交门禁新规则 6.2 报出来当待复测清单**。`temp/d11_resolve_benchmark_conflicts.py` 计划表逐条带 `(期望基准名, 期望分数)` 自校验位置；验收 = 反向还原与 `git HEAD` 逐字节相等 + 独立复核全库 `score` diff 0 + 条目 5659→5655 + 改动记录 18/编辑 56/删除 4 全部等于预期。**首次写下 `config` 的语义边界**（三类合法内容 + 禁止写来源名 + 「基准+配置+score_type+date 足以唯一标识一次测量」），三处采集文档同日补齐。规则 6.2 负对照三份备份：**2067 = 689+1350+28**（D9 前）、**728 = 689+39**（D11 前）、现库 **703 = 689+14** —— `其他` 一段全程 689 未动。**WARN 验收基线自本步起为 703。** 未拍板的两项已登记：7 组 `config` 写来源名的近似重复、合并主键是否扩成 `(benchmark, score_type, config)`。
- 2026-08-30 v2.3（整改轮 D12 + D12b：来源名迁出 `config`，新增 `source_site`）：新增 **§21**。D11 登记的「7 组」经独立复扫实为 **92 条条目 / 21 条记录**（判定法：`config` 括号段只要出现在**本条自己的** `source_url` 主机名/路径或 `source_type` 里就算来源名，避免「有括号的英文段」这种启发式误伤 314 条合法配置）。处置：`independent` 数组新增 `source_site` 字段并纳入合并主键，`config` 只留评测配置。`temp/d12_add_source_site.py` 迁 **88 条 / 19 记录**；随后发现该判定的结构性盲区 —— `Artificial Analysis（镜像站）` 一族来源名永远不等于自己的主机名，`temp/d12b_artificial_analysis.py` 补迁 **59 条 / 14 记录**（57 条带镜像站名，镜像属「读取路径」不是「测量身份」→ `source_site` 写_origin_、镜像写进 `notes`）。两轮合计净改动 **145 条条目 / 23 条记录，全部落在 `independent`**（`config` 145 + 新增 `source_site` 145 + `notes` 追加 1），`score` 改动 **0**，记录 940→940、条目 5655→5655。验收同前两轮回向还原逐字节相等（两轮各自反转自校验通过）。**顺带改正 D11 自身的一处文档错误**：§20 把合并主键写成 `(benchmark, config)`，实际 SOP 一直是 `--array-key benchmark config date`（`arena_elo` 为 `sub_benchmark,date`），已补 `date` 并在 §18 新增第 5 点把权威主键字符串钉死；门禁规则 6.2 的分段键同步改成 `BENCH_SUBKEY`（`self_reported`=`config,date`、`independent`=`config,source_site,date`、`arena_elo`=`date`）。代价与收益都量化后如实登记：拆来源后**同一基准跨源并存不再被主键吞掉**，规则 6.2 照出 **3 组新的 Artificial Analysis 双镜像并存**（2 组分数互相矛盾、1 组两镜像读值一致的真重复），精确主键重复组数 14 → **17**，**WARN 基线 703 → 706**；`score_type` 加进主键对残留组消解数实测 **0**，故未扩（B 档另论）。未新增「`config` 含来源名」门禁规则：可行启发式要么误伤要么需手工维护站点黑名单，收益不抵维护成本。**新基线：940 条 / ERROR 0 / WARN 706 / 结构漂移 0 / 精确主键重复 17 组。**
- 2026-08-30 v2.4（文档口径收尾，无数据改动）：① TL;DR 第 ⑤ 条的合并命令补上 `--on-array replace` 警示（§18 事故的语义根源）并把跑分数组的正确合并口径指向 §18 第 5 点的主键；② 长期挂着的「文中 33 处引用的 14 个 `temp/*.py` 被 `.gitignore` 排除、克隆后指针悬空」经拍板按**只加声明、不动文件**处置 —— 两份文档抬头各写一条「`temp/*.py` 不入库，复核以正文记录的判据与负对照数字为准」，脚本仍留在本机。
- 2026-08-30 v2.5（整改轮 D13：上下文「须独立实测」口径废止）：新增 **§22**。`context_window_effective_tokens` 不再要求独立第三方实测 —— 该口径在仓库文档里查不到制定理由，且与全库实际背离（208 条填值里 173 条抄标称、只有 8 条符合设想），用户拍板**废止口径、173 条原样保留**。四份文档同日改写：`执行细则.md` §2（规则/示例/边界全部重写并留修订记录）、`prompt.md` 字段字典与「绕过方法」段、`agent_prompt_per_model.md` 采集任务书、本文 §14 踩点表。门禁删掉为该口径服务的两条 WARN（实测命中 127 + 105 = **232**，WARN 706 → 501），换成一条结构不变量 **「有效上下文大于标称上下文」即 WARN**；该检查随即照出 **27 条两栏填反**的记录（厂商「原生 X / 可扩展到 Y」被填成标称 X / 有效 Y），按方案 A 归位：大值进标称栏、有效栏置空、备注补归位说明，`deepseek:deepseek-v3:0324` **例外**（其大值 163,840 自证为 T3 三方转述，不可覆盖官方 T0 的 131,072 → 只清有效栏）。净改动 27 条记录（`context_window_effective_tokens` 27 / `context_window_tokens` 26 / `notes` 27），备注里 7 条 `context_window_*=` 字段-值绑定文字同步改名以免自相矛盾；记录 940→940、条目 5655→5655、`score` 零改动、有效上下文非空 208 → 181，反转逐字节复原为验收条件。**新基线：940 条 / ERROR 0 / WARN 474（= 457 + 规则 6.2 的 17）/ 结构漂移 0 / 精确主键重复 17 组。**
- 2026-08-31 v2.6（整改轮 D14：主库范围收窄为「只记录模型」）：新增 **§23**。用户口径「数据库里不要训练框架什么的，我们只记录模型」——这是一条**从没写下来的范围假设**，之前从没被检验过，所以库里混进了 7 条自己声明不是模型的条目（agent 系统 / 训练系统 / 编排框架）。`temp/d14_nonmodel_scan2.py` 的判据**只认记录自己的自我声明**（`architecture_type` 或 `notes` 里明文写「不是模型」「agent 系统」「训练框架」等），第一版用「含框架/系统字样」的松口径扫出 **79 条命中，几乎全是误伤**（「训练框架 hai-llm」「非模型上下文上限」「专为代理式 AI 多智能体系统设计」「仅返回页面框架」），据此收紧为自我声明口径后 13 条命中、逐条人工裁决为 **7 删 + 3 留（乙档边界条目）+ 4 否**。处置：`temp/d14b_quarantine_nonmodel.py` 原样搬到 `docs/non_model_records.jsonl`，5 个对应采集文件移入 `incoming/models/_out_of_scope/`（与 §17 的 `存疑` 隔离档**是两套机制**，一个是质量存疑、一个是范围外）。验收：`md5(排序(主库 + 归档)) == md5(排序(改前备份))` 逐字节相等、两份文件分别跑门禁、记录 940→933 / 条目 5655→5642 / 花名册 692 → **685**（685 + 隔离 10 + 非模型 7 + 缺失 0 = 702）。**已声明的局限**：只删得掉「自己声明了不是模型」的条目，不自我声明的非模型要靠人工全库过一遍才能发现。§17.3 花名册口径同步重基线。**新基线：933 条 / ERROR 0 / WARN 469（= 452 + 规则 6.2 的 17）/ 结构漂移 0 / 精确主键重复 17 组。**
- 2026-08-31 v2.7（整改轮 D15：`architecture_type` 拆成稀疏性 + 主干结构两栏）：新增 **§24**。第 15、16 两轮拍板 —— 一栏里塞了 **190 种自由写法**（既有稀疏性又有骨干，机器无法聚合），拆成 `architecture_type`（`Dense/MoE/Hybrid/Unknown`）+ 新栏 `architecture.backbone_type`（11 值枚举），判不动时**只许借力本条自己的 `architecture.notes` 明文声明、禁止通识反推**，原文照抄进 notes 的 `；原架构表述：「原话」`。范围 **300 条 = 越界 290（越出旧枚举 289 + 值 `null` 1）+ 纯 `"Hybrid"` 10**，实写 **299 条**（`xai:grok-3-mini` 原值本为 `null`，备注原文即「`architecture_type=null`：xAI 闭源未公开架构细节」→ 不给已自陈未披露的记录凭空造键，整条不动）。判定表先给用户逐条过目再动数据：87 条借力全部打印命中词 ±28 字上下文，39 处命中被闸门挡掉，5 条走人工裁定表。过程中修掉的判据缺陷各有样本：`non-MoE` 连字符否定漏剥、`Dense (non-MoE)` 被层记法闸门误杀、限定语窗口按 ±30 字符切会越界吞掉上一子句（stepfun:step-1）改为**按子句切**、中文「密集」与「稠密」两种写法、以及 `bailing-pro` 的 MoE 主语其实是后继型号 Ling-2.6-flash（兄弟型号声明不得算到本条头上）。门禁新增 **1.1 / 1.2** 两条枚举包含性检查，**刻意停在 WARN**：归档副本按行 byte-exact 留存、仍是拆栏前的自由文本，判 ERROR 会失真历史验收信号；升 ERROR 的条件写在 §24。验收：反向还原逐字节等于改前文件、备份 md5 与提交前 HEAD 相同、记录 933→933 / 条目 5642→5642 / `score` 零改动、键序 `backbone_type` 紧跟 `architecture_type` 全部 299 条无一例外、兜底校验两栏 0 越界；**WARN 改前 758 → 改后 469**（差额 289 正是新规则 1.1 在旧数据上的命中数），ERROR 全程 0，规则 1.1/1.2 现库命中 0。**基线数值不变：933 条 / ERROR 0 / WARN 469 / 结构漂移 0 / 精确主键重复 17 组。**已登记遗留：633 条未参与拆栏（值本就合规但**主干信息为零**，其中 373 条 `Unknown` 若放开 notes 借力可再捞一批，本轮按拍板范围不做）、9 条两轴皆 `Unknown`、`backbone_type` 尚无任何下游脚本消费。
- 2026-08-31 v2.8（整改轮 D16：`pricing.free_tier` 四种形状归一 + `available` 语义定边界）：新增 **§25**。四种形状 `null 718 / dict 134 / str 52 / bool 29` → 目标形状统一为含 `available, rpm, rpd, tpm, notes` 五键的对象。**根因是文档与门禁互相矛盾**：`prompt.md` 教字符串写法、门禁的结构漂移检查 `cmp_block` 对非 dict 直接 return，于是采集照文档写、门禁不报，漂移静默累积到 81 条才被发现 —— 与 §16.6（D7）「文档写着默认 USD 于是全库填 USD」是同一类病。两轮拍板：第 18 轮统一成对象；第 19 轮「任一途径免费即 true」+ 限定「标注的是**存在免费渠道**，免费与否仍看官方 API 定价」。第四轮逐条拍板四个分叉：订阅内含→`null`、API 试用 key→`null`、已过期渠道→`false`、订阅背景+现存渠道→`true`；范围由 81 条扩到纳入 51 条 dict 候选（同口径逐条判，其中 9 条分三组提请裁定）。判据按**子句切分**逐句独立判再聚合（沿用 §24 的教训），20 条用户裁定**由规则独立复现 20 / 覆盖 0**，据此认为规则泛化成立才用于 dict 候选。过程中修掉的判据缺陷：采集方「未检索到…置 null 不伪造」模板句里的「免费层」被肯定词误命中（配语境否决 + 冲突转人工裁）、兄弟型号量词（「通常/多数模型」）、「无免费层**信息**」是没查到而非没有、「未给出」不在否决表导致 yandex 两条误判、DeepSeek「免费 Web/App」漏了渠道词、以及同一行被重复入列。**写盘脚本自身的断言遍历全表导致假警报**（未改动行 `touched` 天然空集）挡下第一次 `--apply`，已改为只约束被改动的行。验收：改动 **84 条**（形状迁移 81 + dict 改 `available` 3），记录 933→933、条目 5642→5642、`score` 零改动、键序 215 条全一致、`available` 分布 `True 120 / False 36 / null 59`，备份 md5 == 提交前 `git HEAD`、反向还原逐字节复原。门禁新增规则 **4.4**（非对象形状即 WARN），负对照改前备份实测命中 **81**（550 = 469 + 81），改后 0。文档同日补齐四处（`prompt.md` 字段说明 / 模板 / 示例记录、`agent_prompt_per_model.md` 采集任务书、`执行细则.md` 执行示例）+ 本指南 §25。**基线数值不变：933 条 / ERROR 0 / WARN 469 / 结构漂移 0 / 精确主键重复 17 组。**已登记遗留：5 条 `available=null` 未纳入扫描（其中 `mistral:magistral-small-1-0` 已退役按分叉 C 应为 `false`，是唯一真漏）；以及**一处口径张力**——`gemini-3-flash`（App 免费→`true`）与组 1 的两条官方 App/Web 免费对话（→`null`）同构却结论相反，待用户最终定夺。
- 2026-09-02 v2.9（整改轮 D17 / D17b / D17c：`free_tier.available` 语义收窄，**同一条口径分三遍走完**）：重写 **§26**（原为 D17 单遍版，现覆盖三遍全弧线并拆出 §26.1/26.1b/26.2/26.3/26.4/26.5 六个子节）。第 20 轮拍板把该字段从 D16 的**宽口径**（「存在某条免费途径：App/Web/Playground/新用户赠送额度…任一」）收窄为**窄口径**（「vendor 官方 API 接口当前是否有免费额度」），排除官方 App/网页端/Playground、消费端订阅内含、开源权重下载与自托管、第三方托管免费档（OpenRouter `:free` / Cerebras / HF serverless）、API 试用 key，且只记当前状态。第 21 轮追加四项裁定：**Q1** 平台级额度不算到本条（23 条阿里云「开通百炼后 90 天内各模型有免费额度（以控制台为准）」→ `null` + 登记待重采）；**Q2** legacy ≠ retired（从定价页移除/标 legacy 但未明示 retired 且可调用性未实测 → `null` 而非 `false`）；**Q3** 窄口径不要求额度以 token 计量（`amazon-q-developer` 的「50 次 agentic 请求/月 + 1000 行代码/月」保 `true`）；**Q4** vendor 自有 Free API endpoint 算（`nvidia:nemotron-3-ultra` 的 `integrate.api.nvidia.com/v1` 免费端点保 `true`，并补写原本为 `null` 的 notes 依据）。**三遍各自改判 67 / 45 / 3 条，累计 `available` 改判 115 处（t→f 48 / t→n 59 / n→f 8）、触及 120 条记录、notes 改 63 处**；终态 `available` **是 13 / 否 92 / 空 110**（D16 收尾时是 120/36/59），形状仍 `null 718 / dict 215`、键序变体 1。全程记录 933→933、跑分条目 5642→5642、`score` **零改动**、未改动行逐字节相同、越界路径 0，**门禁 933 / ERROR 0 / WARN 469 三遍均不变**（规则 4.4 只查形状，本轮无需新增门禁规则）。**本轮最该被读到的不是数字，是六个判据盲区**（§26.1）：证据面只读一栏、`RETIRED` 漏日期插入、`API_FREE` 无锚点肯定词导致**否定失明**（「无官方托管 API 免费层」被当成支持 `true` 的证据，还当了仲裁者去否决别的规则）、`NO_API` 是 7 条短语手抄表、矛盾句检测器三重失明（句式全要求前缀 + 命中即 break + 零条 false 断言）、`PLAT` 平台级话术表漏词序变体（「百炼开通后」「自开通百炼起」「各100万Token」三种写法全不在表内）。另记 **§26.2 审计脚本自身的作用域盲区**（笼统量词正则把 google 两条的「Grounding 各 5000 次/月」误当模型免费档，2 条误报登记为具名豁免而非悄悄放宽正则）、**§26.3 三条改自述文本的教训**（只追加理由不等于消掉矛盾句，原句必须就地改写；改写句里不能出现检测器自己的字面句式；批量追加的理由句里凡提到「别的记录如何」必须逐条实测——第二遍那句「四条因已持本模型专属数字并引用官方页」被逐字节复制进 23 条，实测只有 1 条成立）、**§26.4 两处被实测推翻的旧结论**（4 条维持 `null` 的记录理由是采集时本就写有的、不是本轮写的；症状清单里的「同模型两记录结论相反」第一遍并没消解，是第二遍 Q2/G4 才归一的——「已列出」不等于「已解决」）。**护栏两处升级**：① 多遍整改里 `git show HEAD == 现盘` 这道前置断言必然失效（第一遍写盘未提交），改为 **md5 钉三个互相咬合的状态**（输入态 == 上一遍产物 / HEAD == 本轮动手前 / 上一遍备份与 HEAD 逐字节相等），且 md5 必须按**二进制**读算；② 屏障从两道加到四道，第 ③④ 道把「我以为改干净了」写成**可执行的等式**（笼统量词复扫结果 == 具名豁免集合、被判定为错的那句话在库里搜不到），不是「残留 ≤ N」。**两处事实冲突登记而不静默裁决**：`open-mistral-nemo:2407`（`true`，「API 端点仍可调用」）与孪生条 `mistral-nemo-base:2407`（`false`，T0 退役表直采「2026-07-31 API 退役」）直接对撞，已追加冲突登记、**原句逐字节保留**待重采；26 条阿里云记录待重采官方 per-model 免费额度表。文档同日改：`prompt.md` 字段说明整段重写为窄口径 + 判据两组 + 口径变更留痕更新到三遍累计数字；**新增 §26.5「文档示例是判据的一部分」**——查出 `prompt.md` 三处同类缺陷并全修：① `free_tier` 示例把平台级话术教成 `true` 且**错了两代**（`git log -S` 实证 D16 提交 `b185006` 就写错，第一遍只换措辞没换判定方向），现换成正例（`zhipu:glm-4-7-flash` T0 逐模型）+ 反例（平台话术 → `null`）；② 规范单行示例漏了 ERROR 级必采键 `cache_write`（照抄它产不出能过门禁的记录），已补齐；③ `source_type` 字段说明与「来源类型下拉」只给裸写法，而门禁要求 `self_reported` 的该值自带「自报」——**下拉表就是采集的抄写源**，实测 4108 条自报分里 **436 条**踩这条 WARN，已在两处补上带「自报」的取值（存量登记 D18）。并加**可执行护栏** `temp/d17c_example_gate.py`：把文档自己的 ```jsonl 示例抽出来喂门禁 + 负对照（摘掉一个必采键断言必须失败），实测正对照 `exit 0 / ERROR 0 / WARN 0`、负对照 `exit 1 / ERROR 1`；`qa_report.md` 抬头计数十三→十四处、第 13 项里被推翻的宽口径两句与 D16 分布快照加删除线并指向新增的第 14 项（D17 三遍全弧线）；`docs/交接_2026-09-01_D16结案.md` 的「远端 GitHub 私有」改为**公共**（实测），并在「绝对禁止」行补上**不得把 `docs/memory/`、`temp/`、`*.d1*bak-*` 备份入库或对其 `git add -f`**（三条路径均已 `git check-ignore` 实证被忽略）。**基线数值不变：933 条 / ERROR 0 / WARN 469 / 结构漂移 0 / 精确主键重复 17 组。**
- 2026-09-02 v3.0（整改轮 D18：自报分 `source_type` 补「自报」+ 裸 `T0` 可信度归位）：新增 **§27**，清掉 §26.5 查出的存量。第 22 轮四项拍板：**范围 = 修能修的 + 门禁放过空值**；原本带括号的 8 种写法（42 条）**原样挂后缀、容忍双括号**（保变换统一 → 逆还原只需剔后缀）；裸 `T0` 可信度一并改（先按 31 条拍、实测发现是 122 条后**停下来重报重问**，改判「122 条全改」）。数据面写盘 **423 个条目 / 73 条记录**：`source_type` 改 **308 条**（R1 复用库里已有写法 156 / R2 换尾括号 `（转述）`→`（自报分转述）` 7 / R3 新增变体 145；保真断言「原写法含转述 ⇔ 新写法含转述」实测 0 偏移，**全程不删不注入「转述」**）、`confidence` 改 **122 条**（`T0`→`T0-自报`；实测裸 `T0` 只存在于自报分段，`independent`/`arena_elo` 各 0，且 122 条无一含转述 → 触发 ERROR 的风险条数改前实测 0）。门禁面：`self_reported` 的「建议体现自报属性」原本对 `source_type` 为空也报，把**「主张了中立来源」（写错）与「根本没主张来源类型」（缺失）混成一条 WARN**，改为空值不报（加 `and stype`）。**WARN 逐级记账 469 → 341 → 33**，两级差额 −128 / −308 各自恰为一个可独立测量的量（空值条数 / 非空缺「自报」条数），常量段 452 → 16。验收：记录 933→933、跑分条目 5642→5642、`score` 多重集相同、未改动行 **860/933 逐字节相同**、叶子差异**越界路径 0**（白名单仅 `benchmarks.self_reported[i].source_type|confidence`）、逆还原逐字节复原、md5 `5d2b4eef…50c` → `b5eaf743ebbe462613b3613e04168755`。**三条教训**：① **提请拍板前数量必须按「缺陷类」全库数，不能只数本轮筛出来的那批**（31 是在 436 条 WARN 组内数的，真值 122；另 91 条因 `source_type` 已写对而不触发任何门禁信号，从没进入视野——用户是在偏小 4 倍的数字上做的决定）；② **一条 WARN 只该对应一类缺陷**（混报时 436 既不能当「要改多少」也不能当「缺多少」，改完无法验收）；③ **变换统一比好看重要，因为逆还原是验收手段**。**复核脚本自己也会错**：独立复核的逆还原报「与 HEAD 不逐字节相等」，根因是回填时用 `ia.get("source_type")` 无条件赋值，而 `dict.get()` 对不存在的键返回 `None`，凭空造出 `source_type: null` 改了键集与键序；修法为「只在两边都有该键且值不同时回填」+ 断言 `list(ia.keys()) == list(ib.keys())`。规律：**用 `.get()` 做回填/复原时，缺键与值为 null 是两回事；凡逆还原报不等，先怀疑复核脚本，再怀疑数据**。**登记四类不修的矛盾，且每类都写下判据与放宽后的命中数**（教训 1 在同一轮里第三次应验：31 vs 122、128 vs 775、39 vs 438）：① 可信度 `T0-自报-转述` 但来源类型写可直读官方文件 —— 窄口径 **39 条**（不含转述也不含自报）/ 宽口径 **438 条**（只要求不含转述，本轮一条没减），且窄口径那 9 个串被本轮挂了后缀**已搜不到**，§27 给出改后对应串与「不再唯一标识」的提醒（`官方技术报告（自报）` 配该可信度库里 56 条，只 6 条属本批）；438 条里最大一项 `T0-自报` 83 是**可信度值写进了来源类型栏**，属另一类缺陷。② `source_type` 为空且可信度在 T0 家族 = **128 条**（写盘后 `T0-自报` 108 / `T0-自报-转述` 20），门禁放过后**对门禁完全不可见**，只能靠 §27 清单追踪。③ 自报分段 `source_type` 为空**合计 775 条**，其余 **647 条连 `confidence` 键都不存在**（647/647 都带 `source_url`，故 ERROR 级缺 URL 检查不报、T0 家族前置又挡掉 WARN）。④ **门禁判据本身有个洞，本轮没堵**（**→ v3.1 / §27.1 已补上留痕：规则 6.3**）：那条 WARN 是**纯子串匹配** `"自报" in source_type`，于是把可信度值当来源类型写的条目（`"source_type": "T0-自报"`）天然满足它、能过门禁却**零来源信息** —— 实测跑分三段共 **607 条 / 62 条记录**（`T0-自报` 379、`T0-自报-转述` 200、`T0` 22、`T2-第三方` 3、`T3` 2、`T3-转述` 1），另有 ~~405~~ **406 条**（**v3.1 复算更正**）把 `T0` 前缀缀在真实来源描述前（信息不丢、前缀冗余）。**含义：这条 WARN 归零有一部分是空心的**，归零只说明「不再有裸写法」，不等于「来源类型栏都写了来源类型」。没改判据的理由：升成语义判断要维护合法来源类型白名单（现库 191 种写法、含自报 178 种；**D18c 补注：191 = 仅 `self_reported` 段，三段全扫 237 种；含自报 178 种与作用域无关**），成本与误伤面未评估，且直接升 ERROR 与 §24 规则 1.1/1.2 刻意停在 WARN 的口径不一致 → 存量待拍板，新增已在 `prompt.md` 用显式禁令挡住。**这是 §26.1「判据工程盲区」的又一例：判据查的是字符串表面属性，不是字段语义。** 文档同日改四处：`prompt.md` 两处示例（```json 片段与规范单行）的 `source_type` 补 `（自报）`、字段说明加「`self_reported` 条目的 `source_type` 必须自带『自报』二字」、来源类型下拉表的说明按实测重写（**门禁真实判据只是「含『自报』二字」，下拉那三项是推荐取值不是穷举**，库里现有 178 种含自报写法，`（转述）` 结尾的写 `（自报分转述）` 不要叠成三重括号；并新增「⚠️ 别把可信度值当来源类型写」禁令，附 607 条实测数）—— 下拉表就是采集的抄写源，见 §26.5 第 3 项；本指南 §26 遗留清单里那条 436 加删除线指向 §27；`qa_report.md` 抬头十四→十五处并新增第 15 项。**新基线：933 条 / ERROR 0 / WARN 33（= 常量段 16 + 规则 6.2 的 17）/ 结构漂移 0 / 精确主键重复 17 组。**
- 2026-09-02 v3.1（整改轮 D18b：给「来源类型栏写了可信度等级值」补门禁留痕，**零数据改动**）：新增 **§27.1**。第 23 轮拍板 **「只加门禁留痕，数据一字不动」** → 门禁新增 WARN 级**规则 6.3**：跑分条目的 `source_type` **整栏就是一个可信度等级值**即报。判据用正则 `^T[0-4](-自报)?(-转述)?(-第三方)?$` 而**不是 `CONFIDENCE_ENUM` 成员判定**（实测 `T2-第三方` 3 条、`T3-转述` 1 条在枚举外，按枚举判会漏 4 条：607 → 603；**枚举是「合法可信度值」的表，不是「长得像可信度值」的表**）；**三段都查**（`arena_elo` 段此前完全不读 `source_type`，那 3 条对旧门禁彻底不可见）；正则**只决定是否记一条 WARN，绝不驱动数据改写**。**提请拍板前先量化，救回 399 条**：607 条按「同一条目有没有 `confidence` 键」分三档 —— 甲 123 两栏一致（置空零损失）、乙 **399 条连 `confidence` 键都没有**（`source_type` 是唯一等级线索，置空即销毁，涉 37 条记录）、丙 85 两栏矛盾（属重采）；我最初按「607 条一律置空」在想，量完**停下来重报重问**。验收：门禁 933 / **ERROR 0** / **WARN 33 → 640**（差额 **607** 恰等于独立脚本实测命中数，分段 600 / 4 / 3 逐项一致）、**数据 md5 `b5eaf743ebbe462613b3613e04168755` 一字未变**、负对照「新门禁 × 改前备份 = **948** = 341 + 607」证明这批 D18 既没造出也没修掉、文档示例护栏 `temp/d17c_example_gate.py` 仍 pos exit 0 / neg exit 1、剩余 33 条与新规则命中**零重叠**。**刻意不覆盖**冗余前缀类 **406 条**（如 `T0 官方一手技术报告（自报）`，信息不丢、只是前缀冗余；一条 WARN 只背一类缺陷，见 §27 教训 2）。**升 ERROR 的条件**沿用 §24 规则 1.1/1.2：下一个采集周期新记录命中 0 且存量已处置。**仍开着的遗留**：乙档 399 条要的是**迁移**不是置空（且那 4 条枚举外写法逐字迁移会立刻造 ERROR，得先决定扩枚举还是改写）、丙档 85 条属重采、406 条冗余前缀类无门禁信号、与 §27 第一类宽口径 438 条**重叠 83 条**（修时要一次修完）。**同时更正两处先前写错/写漏的数**：① 冗余前缀类 ~~405~~ → **406**（宽判据「以 `T0`–`T4` 开头」合计 **1013**，`^T[0-4]` / `^\s*T[0-4]` / `startswith("T")` 三种写法实测一致、零分歧）；② §27 第一类的**窄口径 39 条判据在改后库上重跑只得 0 条**（改前快照重跑仍是 39 条 / 9 种、分布逐项吻合）—— 判据已被本轮写盘动作作废，那 39 条只能按「记录 + 数组下标」定位；并把**宽口径 438 的判据作用域补全**（`confidence == "T0-自报-转述"` 且 `source_type` 非空不含「转述」，**仅 `self_reported` 段**；放宽作用域后为 440 / 458 / 460），因为本轮复算正是漏了作用域才误判文档写错 —— **同一次复算里「我漏口径」与「文档真错」两种情况并存**，不能因为一个数对上就放过后一个。**两条教训**见 §27.1（说「已清零」前先问判据查的是语义还是字符串表面属性；复算先确认判据作用域）。**新基线：933 条 / ERROR 0 / WARN 640（= 常量段 16 + 规则 6.2 的 17 + 规则 6.3 的 607）/ 结构漂移 0 / 精确主键重复 17 组。**
- 2026-09-02 v3.2（整改轮 D18c：把等级值迁进可信度栏 + 清甲档冗余，**518 个条目**）：新增 **§27.2**。第 24 轮拍板 **「乙档迁移 + 甲档清冗余」**。乙档 = 来源类型栏整栏是等级值且**没有 `confidence` 键**的 399 条，其中 **395** 条把等级值**逐字搬进**可信度栏（新键插在 `source_type` 紧后面，与库里 4198/4351 的主流键序一致）、来源类型栏置 `null`；甲档 = 可信度栏已有**同值**的 123 条，只把来源类型栏置 `null`（零信息损失）。**表外 4 条原样不动**（`T2-第三方` 3 + `T3-转述` 1）：逐字迁移会造 ERROR（不在 `CONFIDENCE_ENUM` 内），机械改写成 `T2`/`T3` 又等于替采集者做判断 —— 这 4 条的等级本身有争议（一条备注明写「转述自 Cognition 官方博客」却记成行业媒体级 T3；三条同址同标的备注里有一条明写「Artificial Analysis 评测」而 §5.1 把 AA 列为 T1，网址又是 OpenRouter 转述）。丙档 85 条两栏矛盾，一字未动，属重采。**置 `null` 而不是删键**：`prompt.md` 明文「缺失一律填 null」、键序不变 → 逆还原只需按值回填不必记插入位置、与 D17 的 `available: null` 同口径；代价是来源类型缺失从此有**两种形状**（无键 775 + 值为 null 515），将来测缺失数必须两种都数。验收（全部先在内跑完才落盘）：前置断言现盘 md5 == 备份 == `b5eaf743…8755`、**序列化往返 933/933 逐字节相同**（本库是 `ensure_ascii=False` + 默认分隔符，不是压缩写法，先验过才敢拿「未改动行逐字节」当 rail）、记录 933→933、条目 5642→5642、`score` 多重集相同、未改动行 **880/933**、叶子 diff **越界路径 0**（差异 913 处 = 乙档 395×2 + 甲档 123×1）、**逆还原逐字节复原**、乙档新增键越位 0、迁移保真四项全 0、甲档「可信度栏被改动 0」、**剩余 89 条 == 丙档 85 ∪ 表外 4（按记录+段+下标逐条比身份）且一字未动**、未参与的 5124 条被改动 0、`benchmarks` 以外差异记录 0、门禁 **933 / ERROR 0 / WARN 640 → 122**、文档示例护栏仍 pos 0 / neg 1。**WARN 记账：差额 518 全部落在规则 6.3 一类，其余五类（主键撞车 17、`knowledge_cutoff` 9、参数量声明 3、定价矛盾 3、缺 `source_url` 1）逐条不变** → 可执行等式 **640 − 122 = 518 = 改动条目数**。改后面：可信度栏有键 4540 → **4935**、来源类型缺失 775 → **1290**（三段 782 → **1300**）、规则 6.3 命中 607 → **89**、非空写法 237 → **235 种**（`T0` 与 `T3` 两种自此在库里消失）。**提请拍板时量化了备选方案的副作用**：「只补可信度栏、来源类型栏留着」会让 22 条裸 `T0` 新撞「建议体现自报属性」→ WARN 640 → **662**（+22），且规则 6.3 一条不减；本方案置空后那条判据有 `and stype` 前置 → 新增 WARN **0**。**两条教训**见 §27.2（搬栏前先确认目标栏的合法值表接得住源栏的写法；打印与断言不一致时以断言为准但必须当场修掉打印）。文档同日改四处：`prompt.md` 的 607 分布划掉换成 D18c 后的 89 条 / 12 条记录、**可信度等级行下新增「七个值是穷举，写枚举外值直接 ERROR」禁令**（附表外 4 条的两处争议当反例）；`qa_report.md` 抬头十五→十七处并新增第 17 项；`docs/交接_2026-09-01_D16结案.md` 横幅补 D18c；记忆两处同步。详见 §27.2 末「文档同日改」。
- 2026-09-02 v3.3（整改轮 D18d：剥掉 `source_type` 里的等级值前缀，**405 个条目**）：新增 **§27.3**。第 25 轮拍板 **「全剥 406 + 补挂「自报」+ 6 条粘连的迁进可信度栏」**（选项描述即执行口径：剥掉全部 406 条的前缀；对**只在前缀里**体现自报属性的补挂「（自报）」以免 WARN 上涨；5 条粘连写法 `T0-自报-技术报告` 复用 D18c 的迁移变换；表外 1 条原样不动、单独登记）。**口径按构造给出，不用正则猜**：前缀类 = 以等级开头（`source_type` 非空 ∧ `^\s*T[0-4]`）**−** 纯等级值（规则 6.3 的正则）= **406**；这与 D18b 在另一个快照上记的 `1013 − 607 = 406` 同数，反过来证明 D18c 一条没碰过这类。前缀抽取用**长度降序的 25 种等级写法表做最长匹配**，再吃掉分隔符（`SEP = " \t:：、,，)）-—"`）。范围 **52 条记录 / 32 种写法**（`self_reported` 399 / `independent` 7）。**本轮最该被读到的一个发现**：406 条里**没有一条是真正的两栏矛盾** —— 可信度栏同值 84、比前缀更具体 316（292 + 21 + 3）、无键 6，也就是说前缀携带的等级信息在同一条目的 `confidence` 里**逐条都能读到**，剥掉是零损失的。三条变换规则：① 剥前缀 + 吃分隔符；② `T0-自报-技术报告` 5 条走 D18c 的迁移（等级值搬进 `confidence`、新键插在 `source_type` 紧后面）；③ 自报分段 ∧ 可信度在 T0 家族 ∧ 剥完不含「自报」→ 末尾补挂「（自报）」，实测 **55 条**。**实写 405 条 / 51 条记录**（`source_type` 400 + 同时两栏 5）。**提请拍板时量化了备选方案的副作用**：「只剥不补挂」会让 **55 条**丢掉自报标记 → 新触发「建议体现自报属性」WARN 55 条 → **122 变 177**；本方案补挂后新增 **0**。验收（全部先在内跑完才落盘）：前置断言现盘 md5 == HEAD blob == 备份 == `3c88eec4…d77`、序列化往返 933/933 逐字节、记录 933→933、跑分条目 5642→5642、`score` 多重集相同、未改动行 **882/933**、叶子 diff **410 处 / 越界路径 0**（白名单仅 `benchmarks.(self_reported|independent|arena_elo)[i].(source_type|confidence)`）、**逆还原逐条通过 405/405 且两分支同时成立的歧义条目 0**（若不为 0，头部就有两种拆法、整道 rail 失效）、可执行等式 **以等级开头 495 → 90 = 纯等级值 89 + 表外 1，差额 405 == 改动条目数**、形状三分 **4342 + 782 + 518 == 5642** 改前改后各自成立（本轮既不新造 null 也不删键）、表外 `T1.5-第三方评测` 逐键相同、**信息零损失按可执行判据逐条论证 405/405 通过（更具体 316 / 同值 89）**、门禁 **933 / ERROR 0 / WARN 122 → 122**、文档示例护栏仍 pos 0 / neg 1。**最强也最该如实说的一条证据**：改前改后两份门禁报告**除标题里的文件名外逐字节相同**（各 194 行、六类 WARN 数量逐项一致）→ 这轮改动**对门禁完全不可见**，价值是纯语义的，不能包装成质量指标提升；**推论是现在没有任何机制阻止它回归**，只有 `prompt.md` 的禁令在守，而文档自己错过两代（§26.5）。**本轮建立的新保真不变量**：含「自报」的**条目数 2567 → 2567 一条不变**，而**写法种类 178 → 171** —— 两个数必须一起看，否则「归一重复写法」与「给条目加上/摘掉自报属性」在验收上无法区分。改后存量：非空写法 **235 → 228 种**、可信度栏有键 **4935 → 4940**、前缀类命中 **406 → 1**（只剩表外那条）、规则 6.3 **89 → 89**（本轮一条不碰纯等级值）、来源类型缺失 **1300 → 1300**（三段无键 782 + 值为 null 518，两种形状都数了）。**四条教训**见 §27.3（① 验收脚本自己出 bug 造成假警报已是第三次，且本轮的修法是把「唯一性」写成断言而不是修完就算；② 报数前先确认判据的作用域，这已是第三次栽在同一处；③ 用集合比不用计数比；④ 「WARN 没动」不等于「这轮什么都没做」，要拿得出逐字节同构的报告和一条语义不变量当证据）。**仍开着的遗留**：表外 `T1.5-第三方评测` 1 条（本轮新登记）、5 条 `（官方技术报告）（自报）` 双括号观感遗留、前缀类无任何门禁规则（是否补 WARN 级规则 6.4 属单独拍板，现库命中 **0**）、该栏仍不收敛（**228 种**写法里 D18d 新造 24 种、31 种剥离结果里只有 7 种是库里原有的）。文档同日改两处：`prompt.md` 的 178 种划掉换成 **171 种（D18d 后）**并新增「种类数会降、含自报的条目数不该动」的验收口径（2567 → 2567）、406 条那段划掉换成 D18d 结案块 + **新增前瞻禁令「新采集不得把等级值当前缀写进 `source_type`」**并写明「目前没有任何门禁规则照这类，这条禁令只有本文档在守」；本指南 §27.1 两处 406 的表述加删除线指向 §27.3、抬头 `temp/*.py` 轮次范围 `D2–D18c` → `D2–D18d`；`qa_report.md` 抬头十七→十八处并新增第 18 项；`docs/交接_2026-09-01_D16结案.md` 横幅补 D18d；记忆两处同步。**新基线：933 条 / ERROR 0 / WARN 122（= 常量段 16 + 规则 6.2 的 17 + 规则 6.3 的 89）/ 结构漂移 0 / 精确主键重复 17 组；数据 md5 `3c88eec4b25afe2e107e4fc5d1a84d77` → `3553105b811c7104199d7de2b8052e91`。**
- 2026-09-02 v3.4（整改轮 D18e：给前缀类补门禁留痕 = WARN 级**规则 6.4**，**零数据改动**）：新增 **§27.4**。第 26 轮拍板 **「补，用『等级值 + 分隔符 + 主体』形」**，处置 §27.3 遗留 ②：D18d 把存量剥净之后**没有任何机制阻止新采集把它写回来**，挡它的只有 `prompt.md` 一句禁令，而 §26.5 已实证文档自己错过两代、且门禁只校验记录不校验文档。**判据形是三选一，先把三个形都在现库与改前备份上量过再提请拍板**（`temp/d18e_rule64_measure.py`）：A 形「以等级开头就算」（非空 ∧ `^\s*T[0-4]` ∧ ¬纯等级值）现库 **1** / 备份 **406**；B 形「等级值 + 分隔符 + 主体」**未加前置**时现库 **89** / 备份 **494**、与规则 6.3 **重复计 89 条**；**B′ = B + ¬纯等级值前置（选定）** 现库 **0** / 备份 **405**、与 6.3 **零重叠**；C 形「只看开头」最宽，现库 **90** / 备份 **495**。**四个形的差额都是 405，恰等于 D18d 的实写条目数** —— 这反过来给 D18d 又添一道独立负对照（D18d 自己的等式是「以等级开头 495 → 90」，与 A/C 两形互相印证）。**选 B′ 不选 A 的理由**：A 形现库那 1 条命中就是 §27.3 刻意不动的表外值 `T1.5-第三方评测`，会把基线从 122 推到 **123**，而且是**以「前缀冗余」的名义**报一条真缺陷是「等级值不在 `CONFIDENCE_ENUM` 内」的条目 —— 与 D18b/D18e 两次援引的「一条 WARN 只背一类缺陷」直接冲突；B′ 照不到它（`T1.5` 后接 `.` 不是分隔符）**是有意的**。**三条实现要点**（都写在 `TIER_PREFIX_STYPE_RE` 上方注释里）：① 调用处那道 `and not TIER_ONLY_STYPE_RE.match(stype)` 前置**是必需的、不是保险** —— 分隔符表含 `-`，少了它 `"T0-自报"` 会被解析成「`T0` + 分隔符 `-` + 主体 `自报`」而同时命中 6.3，重复计 89 条（上表 B 形那行就是这个 bug 的量）；② 分隔符字符类里 `-` **必须放最末**（`[ \t:：、,，)）—-]`），写成 `)）-—` 会把 `）-—` 解析成 U+FF09→U+2014 的范围而报 `bad character range`，**更糟的是若 ASCII `)` 排前面那是个合法反向范围，会静默匹配约 8000 个 CJK 字符**（报错比沉默安全，§27.3 教训 2 已栽过一次）；③ **跑分三段都查** —— `arena_elo` 段此前完全不读 `source_type`，D18b 补 6.3 时才纳入，6.4 同样要查（改前备份实测本段命中 **0**，但判据不能靠这个省略）。验收（零数据改动，rails 全在门禁侧）：**2×2 负对照矩阵四个组合各自可解释** —— 旧门禁 × 现库 **122**、旧门禁 × 改前备份 **122**（印证 D18d「两份报告除标题外逐字节相同」）、新门禁 × 现库 **122**（6.4 命中 0 → 基线一条不增）、新门禁 × 改前备份 **527 = 122 + 405**；现库 WARN 构成逐项复核 89 + 17 + 16 + **0** = **122**；**五个探针的正对照是本轮最要紧的一道** —— 现库命中为 **0** 意味着「这条规则真的会响」在真库上**拿不到任何证据**，写错变量名、放错循环、正则不匹配都会静默表现为「命中 0」，与「库里真干净」在门禁输出上**完全无法区分**，所以必须自己造探针（`temp/d18e_probe.py`，载体 `alibaba:qwen2-1-5b:base`，全库 **95** 条合格载体之一，三条挑选条件：原值非空且本身不触发 6.3/6.4、`confidence` 不在 T0 家族否则「建议体现自报属性」会跟着 `source_type` 变而混淆计数、整条记录无任何 6.3/6.4 命中）：P0 原样重写 → WARN **122** 且临时文件与真库 **md5 逐字节相同**（若重写本身引入差异，P1–P4 的计数差里就混着序列化噪音、无从归因）；P1 `T0 官方自报` → **123** 且只 6.4 响（证明规则接通）；P2 `T0-自报` → **123** 且只 6.3 响（证明互斥）；P3 `T1.5-第三方评测` → **122** 两条都不响（证明「刻意不覆盖表外值」这条取舍真的生效）；P4 `官方技术报告（自报）` → **122** 两条都不响（证明本来就该这么写的值不误伤）；**数据文件 md5 `3553105b811c7104199d7de2b8052e91` 一字未变**、`git status` 只有门禁脚本一个改动项；文档示例护栏 `temp/d17c_example_gate.py` 仍 pos exit 0 / neg exit 1（`prompt.md` 的 ```jsonl 示例里没有前缀写法，新规则不打它 —— 这本身也是一次确认）；**门禁脚本 md5 `f70bcb836488860eb2708dd67625449e` → `6ea4de427c0875375b9fd83f6f0cf1c3`**（D18c 与 D18d 两轮都没动过它，本轮是这三轮里唯一一次改门禁）。**一条教训（本轮唯一，但已是第四次同类）**：**验收脚本自己的判据错，会报出与被验对象无关的假警** —— 探针第一版五个里四个 FAIL，看着像「规则 6.4 没接通或互斥性破了」，实际门禁全对，错在探针用 `MSG_63 in rep` 做**整份报告范围**的子串匹配，而真库本来就有 89 条规则 6.3 的 WARN，这句恒真；修法是**按 `## \`model_id\`` 标题精确截出载体自己那一段再搜**（注意 `alibaba:qwen2-1-5b:base` 与 `alibaba:qwen2-0-5b:base` 只差一个字符，子串匹配会串到隔壁段），并补一道防呆 **期望至少一条要响时载体段必须非空** —— 否则截段失败会静默返回空串，让 P0/P3/P4 假通过、P1/P2 假失败、诊断信息还指错方向。这是 D18 的 `.get()` 凭空造键、D18c 的 `is not` 比两个 dict 恒真、D18d 的无条件剥后缀之后的**第四次**，规律补一句：**判据的作用域要与被验对象的作用域一致 —— 验一条记录就在那条记录的段落里搜，别在整份报告里搜。** **升 ERROR 的条件**沿用 §24 规则 1.1/1.2 与 §27.1 规则 6.3（下一个采集周期新记录命中 0 且存量已处置 —— 现库已经是 0，所以这个条件从加上那一刻就成立一半），但**本轮刻意不升**，与 1.1/1.2/6.3 停在 WARN 的口径一致。**仍开着的遗留**：表外 `T1.5-第三方评测` **1 条**（6.4 刻意照不到，属「枚举外可信度值」那一项，与 §27.2 表外 **4 条** 同类，合计 **5 条**待单独处置）、丙档 **85 条**属重采、来源类型缺失 **1300**（三段，两种形状）门禁放过只能靠清单追踪、该栏**仍不收敛**（228 种写法）、5 条双括号观感遗留。文档同日改四处：`prompt.md` 一处 —— 把 D18d 写下的「目前没有任何门禁规则照这类，这条禁令只有本文档在守」划掉换成 D18e 实况（规则 6.4 会报、现库命中 0、与 6.3 互斥、刻意照不到表外那条），指针扩到 **§27.4**；本指南 §27.3 遗留 ② 加删除线指向本节、抬头 `temp/*.py` 轮次范围 `D2–D18d` → `D2–D18e`；`qa_report.md` 抬头十八→**十九处**并新增**第 19 项**；`docs/交接_2026-09-01_D16结案.md` 横幅补 D18e 与门禁脚本 md5 变化；记忆两处同步。**新基线：933 条 / ERROR 0 / WARN 122（= 常量段 16 + 规则 6.2 的 17 + 规则 6.3 的 89 + 规则 6.4 的 0）/ 结构漂移 0 / 精确主键重复 17 组；数据 md5 `3553105b811c7104199d7de2b8052e91` 一字未变，门禁脚本 md5 `f70bcb836488860eb2708dd67625449e` → `6ea4de427c0875375b9fd83f6f0cf1c3`。** **WARN 数与 D18d 收尾时相同但原因相反**：D18d 是「改了数据而门禁照不到」，D18e 是「改了门禁而现库本来就干净」—— 两轮都表现为 122 不变，读的人要靠**哪个 md5 动了**分辨（数据 md5 变 = 前者，门禁 md5 变 = 后者）。
- 2026-09-02 v3.5（整改轮 D19：来源类型栏 5 条「枚举外可信度值」按记录内证据逐条定级，**5 个条目**）：新增 **§27.5**。第 27 轮拍板 **「按建议逐条定级」**，一次做完 §27.2 与 §27.3 两轮**刻意原样不动**留下的同一批 5 条表外值（逐字迁进 `confidence` 会造 ERROR，机械改写成 `T1`/`T2`/`T3` 又等于替采集者做判断，所以必须逐条读记录内证据定级）。定级结果：`cognition:swe-1-6:base` 自报[1] `T3-转述` → **`T0-自报-转述`**（`prompt.md` 决策 2 明文：厂商自报分经媒体转述且官方不可直访必须标此值，原记 `T3` 把「转述载体」当成了「可信度」）；`mistral:mistral-large-3:base` 独立[5] `T2-第三方` → **`T1`**（本条 notes 明写 Artificial Analysis 评测，§5.1 把 AA 列为 T1）、独立[6][7] → **`T2`**（本条无来源归属证据，**禁止抄兄弟条目 [5]**，只按 url 是 OpenRouter 转述定级）；`deepseek:deepseekmoe-16b:base` 独立[0] `T1.5-第三方评测` → **`T3`**（§5.1 距离原则：媒体报道第三方评测是二手转述；`T1.5` 这个等级在枚举里根本不存在）。**变换**沿 D18c 乙档：`confidence` ← 定级值、新键**紧插在 `source_type` 之后**（4198/4351 的主流键序 → 键序不变、逆还原只需 `del`），随后 `source_type` ← **`null`**（不删键）登记待重采。验收（全部先在内存跑完才落盘）：现盘 md5 == HEAD blob == `3553105b…`、门禁脚本 md5 仍 `6ea4de42…`（本轮不该碰它）、序列化往返 933/933 逐字节、五条旧值与「原本无 `confidence` 键」逐条锁定、五个新值全在枚举内、记录 933→933 / 条目 5642→5642 / `score` 多重集相同、叶子 diff **10 处 / 越界 0**、未参与 **5637 条改动 0**、**逆还原逐字节相等**并补「实际执行 5 次而非 0 次」的计数防呆、**`model_id` 全库唯一首次写成断言**（D6–D18e 所有脚本都隐含它而从没验过，而库里有 17 组重复主键）、含「自报」条目 **2567 → 2567**（D18d 那道 rail 仍成立）。改后存量：非空 4342 → **4337**、值为 null 518 → **523**、无键 782 → **782**、可信度有键 4940 → **4945**、写法 **228 → 225 种**。门禁 **933 / ERROR 0 / WARN 122 → 118**，**−4 全部落在规则 6.3（89 → 85）**，其余六类逐条不变（是 4 不是 5：`T1.5` 那条本就在 6.3/6.4 之外，它减的是「表外」那一类而不是 WARN）。**三档判据口径**（本轮按用户「报数必须说清口径」的规矩扫了三遍，中口径顺带挖出一个从没登记过的新缺陷类）：窄口径整栏表外值 **5**、中口径栏内任意位置出现等级形状 **111**（开头形 90 已覆盖 → **差额 21 条是「括号后缀」形**，如 `官方模型卡自报（T0 直采）`，`confidence` 全是 `T0-自报` 且**一致 21 / 不一致 0 / 无键 0**、剥完主体仍含「自报」→ 新增 WARN 0，**至今无规则照它**）、宽口径递归扫全记录所有字段命中 2 条但**全不在 `source_type`**（两条 gemini 的 `pricing.notes` / `meta.notes` 自由文本）→ **字段级判据必须按字段路径扫，递归扫自由文本会造出「还有遗留」的假命中**。**三条教训**见 §27.5：① 验收断言 `(mb + mvb, ma + mva) == ((782,518),(782,523))` 里 `mb + mvb` 是**整数加法**、跟元组比恒不等 → rail **假失败**而同一条打印的四个数全对（同类**第五次**；规律：判据的作用域**与操作数类型**都要和被验对象一致，假失败和假通过一样贵，它会把人推向错误的方向）；② **隐含假设要写成断言**；③ **定级不许抄兄弟条目**，同一记录 `[5]` 有 AA 证据而 `[6][7]` 没有，就必须是 `T1`/`T2`/`T2` 三个不同结果。文档同日改：`prompt.md` 把「另有 5 条枚举外写法待单独处置」划掉换成结案 + 新增「定级不许抄兄弟条目」口径；本指南 §27.4 遗留 ①② 加删除线指向 §27.5、抬头轮次范围 `D2–D18e` → `D2–D19`；`qa_report.md` 抬头十九→**二十处**并新增**第 20 项**；**新增 `docs/交接_2026-09-02_D19结案_换平台接手卡.md`**（用户额度见底、要换平台且上下文全丢，故为**零上下文读者**写的全面落盘档：一分钟接手表、命令原文、环境陷阱、现状态确切数字、待拍板清单按建议排序、红线八条、被推翻的直觉十条）；记忆两处同步。**新基线：933 条 / ERROR 0 / WARN 118（= 规则 6.3 的 85 + 规则 6.2 的 17 + 常量段 16 + 规则 6.4 的 0）/ 结构漂移 0 / 精确主键重复 17 组；数据 md5 `3553105b811c7104199d7de2b8052e91` → `ceff15e9a12709ab3d49679f3d1560f5`，门禁脚本 md5 一字未动，备份 `model_data_v2.jsonl.d19bak-20260902-224225`。**
