# WorkBuddy Agent 专属作业规范（model_data v2）

> **本文档读者**：在 WorkBuddy 平台上运行的 agent（主 agent 与它派发的 subagent）。
> **定位**：是 [`multi_platform_subagent_guide.md`](./multi_platform_subagent_guide.md)（跨平台通用规范）的**平台补丁**。通用规范里的认领协议、文件命名、12 条红线、验收 checklist 全部继续有效，本文档只补充 WorkBuddy 环境特有的坑和必须额外执行的动作。
> **冲突时**：以本文档为准（因为它记录的是本平台实测过的环境事实）。
> **建立**：2026-08-28，基于 workbuddy-01 烂尾事故复盘 + 本机 git 弹窗问题。
> **⚠ 文中 `temp/*.py` 指针不入库**：`.gitignore` 第 6 行排除了 `/temp/`，那些脚本是 D2–D14 各轮整改的**本机一次性产物**，
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
