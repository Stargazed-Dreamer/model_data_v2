# -*- coding: utf-8 -*-
"""D41 五项裁定落地。

1. 移除 4 条 arena 段位错置条目（search / LiveCodeBench Pro / gdpval / agent）
2. bytedance:dola-seed-2-0-pro:base 保留（加留痕）
3. vendor 统一：basic_info.vendor 首字母大写（品牌惯用写法）+ 同厂多写法合并；
   model_id 前缀归一为小写 slug（52 条大写前缀）
4. Qwen 3 世代 model_id 统一为 qwen-3-* 连字符式（39 个 family）
5. license 46 条空白 → 留档（见 docs/LICENSE_GAP_BACKLOG.md，本脚本不动）

用法：python temp/d41_apply.py [--apply]
"""
import json
import os
import sys
import collections

SRC = 'model_data_v2.jsonl'

# ---------------------------------------------------------------- 1. arena 段位错置
ODD_SUB = {'search', 'LiveCodeBench Pro', 'gdpval', 'agent'}

# ---------------------------------------------------------------- 2. 保留留痕
KEEP_NOTE = ('【D41 用户裁定：保留】信息过薄（仅 arena 数据，无 release_date / 定价 / 架构），'
             'AA 与 OpenRouter 均无此模型；经裁定保留，待后续信源补充。')

# ---------------------------------------------------------------- 3a. vendor 同厂多写法合并
VENDOR_MERGE = {
    # Google
    'Google DeepMind': 'Google',
    # Meta
    'Meta AI': 'Meta',
    'Meta (Meta AI)': 'Meta',
    # DeepSeek
    'DeepSeek（深度求索）': 'DeepSeek',
    # Alibaba
    'Alibaba (阿里通义千问 Qwen Team)': 'Alibaba',
    'Alibaba (Qwen Team)': 'Alibaba',
    'Alibaba (Tongyi Lab)': 'Alibaba',
    'Alibaba Tongyi Lab (通义实验室)': 'Alibaba',
    'Alibaba Cloud': 'Alibaba',
    'Alibaba (Alibaba International Digital Commerce, MarcoPolo Team, AIDC-AI)': 'Alibaba',
    # ByteDance
    'ByteDance (字节跳动)': 'ByteDance',
    'ByteDance Seed Team': 'ByteDance',
    'ByteDance Seed': 'ByteDance',
    # Moonshot
    'Moonshot AI (月之暗面)': 'Moonshot AI',
    'Moonshot': 'Moonshot AI',
    # Zhipu
    'Zhipu AI (Z.ai internationally)': 'Zhipu AI',
    'Zhipu AI (北京智谱华章科技股份有限公司)': 'Zhipu AI',
    'Z.ai (Zhipu AI)': 'Zhipu AI',
    # Sber
    'Sber（SberDevices / SaluteDevices，ai-forever 组织）': 'Sber',
    'Sber（Сбер / Sberbank，GigaChat 团队）': 'Sber',
    'Sber（Сбер / Sberbank，HF 组织 ai-sage / ai-forever）': 'Sber',
    # Huawei
    'huawei': 'Huawei',
    '华为（华为云 Huawei Cloud）': 'Huawei',
    '华为（华为云 Huawei Cloud / 昇腾 Ascend 团队 / 诺亚方舟实验室）': 'Huawei',
    'salesforce': 'Salesforce',
    # Qihoo
    'qihoo-360 (奇虎 360 / 三六零 601360.SH)': 'Qihoo 360',
    'qihoo-360': 'Qihoo 360',
    # 其他大小写/写法变体
    'Meituan': 'Meituan', 'meituan': 'Meituan',
    'Xiaomi': 'Xiaomi', 'xiaomi': 'Xiaomi',
    'Allen Institute for AI': 'Allen Institute for AI', 'allenai': 'Allen Institute for AI',
    'allen-institute-for-ai': 'Allen Institute for AI',
    'Tsinghua University': 'Tsinghua University', 'tsinghua': 'Tsinghua University',
    'tsinghua-university': 'Tsinghua University',
    'ModelBest': 'ModelBest', 'modelbest': 'ModelBest',
    '面壁智能 / OpenBMB (ModelBest)': 'ModelBest',
    'OpenBMB（面壁智能 ModelBest + 清华大学自然语言处理实验室）': 'ModelBest',
    '4Paradigm': '4Paradigm', '4paradigm': '4Paradigm',
    'Mistral AI': 'Mistral AI', 'mistral': 'Mistral AI',
}

# ---------------------------------------------------------------- 3b. 首字母小写 → 品牌惯用写法（62 种）
VENDOR_CASE = {
    # 品牌自身写法含小写首字母，保留原样
    'xAI': 'xAI',
    # 缩写/特殊大小写品牌
    'lg': 'LG', 'tii': 'TII', 'sdaia': 'SDAIA', 'mbzuai': 'MBZUAI', 'lmsys': 'LMSYS',
    'iflytek': 'iFlytek', 'stepfun': 'StepFun', 'sambanova': 'SambaNova',
    'inclusionAI': 'InclusionAI', 'lighton': 'LightOn', 'nexusflow': 'NexusFlow',
    'character-ai': 'Character.AI', 'creditease': 'CreditEase', 'g42': 'G42',
    # 品牌全称补全
    'sha-ai-lab': 'Shanghai AI Laboratory',
    'nous': 'Nous Research',
    'kunlun': 'Kunlun Tech',
    'singapore-ai': 'AI Singapore',
    'stability': 'Stability AI',
    'voyage': 'Voyage AI',
    'unicom': 'China Unicom',
    'princeton': 'Princeton University',
    'sk-telecom': 'SK Telecom',
    'nstc-taiwan': 'NSTC (Taiwan, China)',
    'z-ai-zhipu-ai-tsinghua-university': 'Zhipu AI',
    # 品牌常规写法
    'typhoon': 'Typhoon', 'inception-labs': 'Inception Labs', 'cisco': 'Cisco',
    'lenovo': 'Lenovo', 'insait': 'Insait', 'preferred-networks': 'Preferred Networks',
    'sea-ai-lab': 'Sea AI Lab', 'silo-ai': 'Silo AI', 't-bank': 'T-Bank',
    'kotoba-technologies': 'Kotoba Technologies', 'trend-micro': 'Trend Micro',
    'jondurbin': 'Jondurbin', 'aleph-alpha': 'Aleph Alpha', 'unisound': 'Unisound',
    'harbin-institute-of-technology': 'Harbin Institute of Technology',
    'massachusetts-institute-of-technology-mit': 'Massachusetts Institute of Technology (MIT)',
    'chengdu-university-of-traditional-chinese-medicine':
        'Chengdu University of Traditional Chinese Medicine',
    'china-post-consumer-finance-co-ltd': 'China Post Consumer Finance Co., Ltd.',
    'guangzhou-lingju-information-technology-co-ltd':
        'Guangzhou Lingju Information Technology Co., Ltd.',
    'beijing-weimeng-chuangke-network-technology':
        'Beijing Weimeng Chuangke Network Technology',
    'beijing-institute-of-technology-academy-of-military-science-minzu-university-of-china':
        'Beijing Institute of Technology / Academy of Military Science / Minzu University of China',
    'fudan-university-shanghai-qiji-zhifeng': 'Fudan University / Shanghai Qiji Zhifeng',
    'speakleash-cyfronet-agh': 'SpeakLeash / Cyfronet AGH',
    'ece-tw3': 'ECE-TW3',
    'eth-zurich': 'ETH Zurich',
}

# ---------------------------------------------------------------- 3c. model_id 大写前缀 → 小写 slug
PREFIX_SLUG = {
    'Alibaba': 'alibaba', 'Google': 'google', 'Cohere': 'cohere', 'DeepSeek': 'deepseek',
    'Meta': 'meta', 'IBM': 'ibm', 'Microsoft': 'microsoft', 'ModelBest': 'modelbest',
    'Hugging Face': 'huggingface', 'Databricks': 'databricks', 'Tencent': 'tencent',
    'NVIDIA': 'nvidia', 'Deep Cogito': 'deep-cogito', 'Baidu': 'baidu',
    'xAI': 'xai',
    # 语义错误前缀（vendor 已知却写 unknown）
    'unknown': 'ireader-technology',
}


def main():
    apply = '--apply' in sys.argv
    recs = []
    with open(SRC, encoding='utf-8') as f:
        for line in f:
            if line.strip():
                recs.append(json.loads(line))

    # ---------------- 覆盖率断言：首字母小写的 vendor 必须显式映射（不留静默兜底） ----------------
    allv = {str(r['basic_info'].get('vendor') or '') for r in recs}
    unmapped = sorted(v for v in allv
                      if v and v[0].islower() and v not in VENDOR_MERGE and v not in VENDOR_CASE)
    if unmapped:
        print('!! 未显式映射的首字母小写 vendor（会走首字母大写兜底）：')
        for v in unmapped:
            print('   ', v)
    else:
        print('覆盖率断言通过：首字母小写 vendor 全部有显式映射')
    print()

    # ---------------- 预检：重命名后的 model_id 碰撞 ----------------
    def newmid(mid):
        p, fam, var = mid.split(':')
        p2 = PREFIX_SLUG.get(p, p)
        if fam.startswith('qwen3'):
            fam = 'qwen-3' + fam[len('qwen3'):]
        return f'{p2}:{fam}:{var}'

    mapping = collections.defaultdict(list)
    for r in recs:
        mapping[newmid(r['model_id'])].append(r['model_id'])
    coll = {k: v for k, v in mapping.items() if len(v) > 1}
    # 与未改名记录之间的碰撞
    renamed = {newmid(r['model_id']) for r in recs if newmid(r['model_id']) != r['model_id']}
    stat = collections.Counter()
    for k, v in coll.items():
        if len(set(v)) > 1:
            stat['重命名后互相碰撞'] += 1
            print(f'  !! 碰撞 {k} <- {v}')
    print(f'重命名后碰撞组: {stat["重命名后互相碰撞"]}')

    vchg = collections.Counter()
    pchg = collections.Counter()
    qchg = collections.Counter()
    achg = collections.Counter()
    out = []
    orig_mids = []
    for r in recs:
        mid = r['model_id']
        orig_mids.append(mid)
        p, fam, var = mid.split(':')

        # 3b vendor 字段
        bi = r['basic_info']
        old_v = str(bi.get('vendor') or '')
        new_v = VENDOR_MERGE.get(old_v, old_v)
        if new_v == old_v and old_v and old_v[0].islower():
            new_v = VENDOR_CASE.get(old_v, old_v[0].upper() + old_v[1:])
        if new_v != old_v:
            vchg['vendor 字段改动'] += 1
            vchg[f'源={old_v}'] += 1
            bi['vendor'] = new_v
            tag = '【D41 vendor 归一】原 vendor: %s→%s' % (old_v, new_v)
            bi['notes'] = (bi.get('notes') + '；' + tag) if bi.get('notes') else tag

        # 3c + 4 model_id
        p2 = PREFIX_SLUG.get(p, p)
        fam2 = 'qwen-3' + fam[len('qwen3'):] if fam.startswith('qwen3') else fam
        if (p2, fam2) != (p, fam):
            newmid_ = f'{p2}:{fam2}:{var}'
            if p2 != p:
                pchg['前缀改动'] += 1
            if fam2 != fam:
                qchg['qwen family 改动'] += 1
            r['model_id'] = newmid_
            tag = '【D41 命名归一】原 model_id: %s→%s' % (mid, newmid_)
            if p2 != p:
                tag += '（vendor 段归一为小写 slug）'
            if fam2 != fam:
                tag += '（Qwen 3 世代统一为 qwen-3-* 连字符式）'
            r['meta']['notes'] = (r['meta'].get('notes') + '；' + tag) if r['meta'].get('notes') else tag

        # 1 arena 段位错置移除
        ar = r['benchmarks'].get('arena_elo') or []
        keep = []
        for e in ar:
            if e.get('sub_benchmark') in ODD_SUB:
                achg['移除 arena 条目'] += 1
                tag = ('【D41 arena 段位错置移除】删除 arena_elo 条目 sub_benchmark=%r'
                       '（非 LMArena 标准段位：text/coding/math/vision/webdev；用户 D41 裁定移除，'
                       '如为独立榜单应迁 independent 段，本轮按裁定直接移除）' % e.get('sub_benchmark'))
                r['meta']['notes'] = (r['meta'].get('notes') + '；' + tag) if r['meta'].get('notes') else tag
            else:
                keep.append(e)
        if len(keep) != len(ar):
            r['benchmarks']['arena_elo'] = keep

        # 2 dola-seed 保留留痕
        if r['model_id'] == 'bytedance:dola-seed-2-0-pro:base':
            r['meta']['notes'] = (r['meta'].get('notes') + '；' + KEEP_NOTE) if r['meta'].get('notes') else KEEP_NOTE
            achg['保留留痕'] += 1

        out.append(r)

    print()
    print('--- 变更统计 ---')
    print(f'  vendor 字段改动: {vchg["vendor 字段改动"]} 条 / {len([k for k in vchg if k.startswith("源=")])} 种源值')
    print(f'  model_id 前缀改动: {pchg["前缀改动"]} 条')
    print(f'  model_id qwen family 改动: {qchg["qwen family 改动"]} 条')
    print(f'  arena 条目移除: {achg["移除 arena 条目"]} 条')
    print(f'  保留留痕: {achg["保留留痕"]} 条')
    print()
    print('--- vendor 改前→改后（按条数） ---')
    for k, c in vchg.most_common(40):
        if k.startswith('源='):
            print(f'  {c:4d}  {k[2:]}')

    print()
    print('--- model_id 前缀改动清单 ---')
    pc = collections.Counter()
    qc = collections.Counter()
    for r0, r1 in zip(orig_mids, out):
        a, b = r0, r1['model_id']
        if a.split(':')[0] != b.split(':')[0]:
            pc[f'{a.split(":")[0]} -> {b.split(":")[0]}'] += 1
        if a.split(':')[1] != b.split(':')[1]:
            qc[f'{a.split(":")[1]} -> {b.split(":")[1]}'] += 1
    for k, c in sorted(pc.items()):
        print(f'  {c:4d}  {k}')
    print(f'--- qwen family 改动清单（{sum(qc.values())} 条 / {len(qc)} 个 family） ---')
    for k, c in sorted(qc.items()):
        print(f'  {c:2d}  {k}')

    if not apply:
        print()
        print('[DRY-RUN] 未写盘')
        return

    bak = 'backups/model_data_v2.pre-d41-normalize-{}.jsonl'.format(
        __import__('time').strftime('%Y%m%d-%H%M%S'))
    os.makedirs('backups', exist_ok=True)
    with open(SRC, encoding='utf-8') as f, open(bak, 'w', encoding='utf-8', newline='\n') as g:
        g.write(f.read())
    with open(SRC, 'w', encoding='utf-8', newline='\n') as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(f'\n[APPLIED] 记录 {len(out)} 条；备份 {bak}')


if __name__ == '__main__':
    main()
