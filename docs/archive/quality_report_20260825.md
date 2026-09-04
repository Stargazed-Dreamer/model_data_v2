# 模型数据库定价采集质量报告（2026-08-25 放量采集收官）

> 数据文件：`workspace/model_data/model_data_v2.jsonl`（schema 1.1，共 **927 条**记录）
> 终验脚本：`scripts/audit_final.py` → **ERROR 0 / WARN 0**

## 一、总体覆盖

| 指标 | 数值 |
|------|------|
| 总记录 | 927 |
| 实价记录（有 input/output/缓存等数值） | **165（17.8%）** |
| 标注记录（无价但注明原因） | 762（82.2%） |
| 空白记录（无价且无标注） | **0** |

对比本轮启动前基线（约 30 条实价），实价记录增长至 **5.5 倍**。

## 二、实价质量分级

| 分级 | 定义 | 条数 |
|------|------|------|
| T0 | 官方定价页直接核对 | 161 |
| T1 | 官方产品页营销价卡 | 3（MiniMax M3/M2.7/M2.5） |
| T2 | 官方旧版文档口径 | 1（腾讯 hunyuan-turbos，迁移期） |

币种分布：USD 124 条、CNY 41 条。

## 三、本轮新增批次（按厂商）

| 厂商 | 批次结果 | 备注 |
|------|---------|------|
| xAI | 7 实价 + 10 停服标注 | grok-4-5 $2/$6/缓存$0.30，长上下文双轨价齐全 |
| Perplexity | r1-1776 停服标注 | sonar 系列此前已有 |
| Moonshot | 5 实价 + 6 标注 | Mintlify `.md` 直取；kimi-k3 ¥20/¥100/缓存¥2 |
| MiniMax | 3 T1 实价 + 7 标注 | priceCard 营销价卡；输出价不单列不硬填 |
| Zhipu | 7 实价 + 3 标注 | CDP 渲染 SPA 提取；GLM-5.3 ¥8/¥28 |
| ByteDance | 2 实价 + 7 标注 | Quill Delta 文档走 CDP 渲染；doubao-pro ¥0.80/¥2.00 |
| Tencent | 1 T2 实价 + 3 标注 | TokenHub DNS 失败改用旧版计费文档 |
| Baidu | 4 全标注 | 仅第三方聚合价，按"不硬填"原则拒绝混录 |
| Ant-group | 13 全标注 | Ling/Ring 开源系列 + bailing-pro 闭源内部模型 |
| **Alibaba** | **26 实价 + 50 标注** | 百炼计费文档直取（T0）；qwen3.8-max ¥12/¥36、qwen-plus 阶梯三档、qwen3.5 系列 4 尺寸齐 |
| 开源厂商批量标注 | 416 + 119 + 2 = 537 条 | meta/nvidia/microsoft/lg/ibm/apple 等 234 个 provider 前缀统一标注 |

## 四、标注分类体系（762 条无价记录）

| source_type | 条数 | 含义 |
|-------------|------|------|
| 开源权重模型核对（无官方 API 价） | 383 | Hugging Face 发布权重，厂商不卖 API；第三方托管价不混录 |
| 官方定价页核对（无公开定价） | 179 | 闭源但需企业询价/订阅制/研究发布 |
| 官方定价页核对（已下架） | ~180 | 历史 API 已停服或快照移除 |
| 其他细分标注 | ~20 | 未单列/待查/preview 下架等 |

## 五、遗留待办（下轮可选）

1. `alibaba:qwen3-max-thinking` —— 可能已并入 qwen3-max 思考模式计费，待确认后补价
2. Amazon Nova 系列 —— Bedrock 价存在但 region 映射未精确核实
3. Voyage AI embedding 4 条 —— 价目存在待逐版本核对
4. MiniMax 3 条 T1 —— 待 platform.minimaxi.com 恢复后升级为精确分档 T0
5. 腾讯混元 —— TokenHub 迁移完成后将 turbos 从 T2 升级为现行 T0

## 六、数据卫生说明

- 所有删除类操作均进回收站，所有批次写入前有 `.bak` 备份（`.xaiFix.bak` 等 9 个）
- 原始页面存档于 `raw_pages/`（本轮新增约 30 个文件，含 CDP 渲染文本）
- 校验口径：每批写入后即跑校验（ERROR 0 才收批）；终验全库通过
