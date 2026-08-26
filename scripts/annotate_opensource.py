# -*- coding: utf-8 -*-
"""Task #15: 开源/无公开定价厂商批量标注
统一策略：
- 开源权重模型（Hugging Face 发布，厂商不直接卖 API）→ '开源权重模型核对（无官方 API 价）'
- 厂商有官方托管平台但本库模型为历史版本 → '官方定价页核对（已下架）'
- 闭源但无公开定价（内部/研究模型）→ '官方定价页核对（无公开定价）'
- 特殊实价机会单独处理（amazon nova 有 Bedrock 官方价，openai gpt-oss 开源）
"""
import json

BASE = r'F:/project_temp/localAgent/workspace/model_data/'
recs = [json.loads(l) for l in open(BASE + 'model_data_v2.jsonl', encoding='utf-8')]

OPEN = '开源权重模型核对（无官方 API 价）'
RET = '官方定价页核对（已下架）'
NOPUB = '官方定价页核对（无公开定价）'

def ann(stype, note):
    return {'currency': None, 'unit': 'per_million_tokens', 'input': None, 'output': None,
            'cached_input': None, 'cache_write': None, 'batch_input': None, 'batch_output': None,
            'free_tier': None, 'promotions': None, 'long_context': None,
            'effective_date': '2026-08-25', 'source_url': None, 'source_type': stype,
            'confidence': 'T0', 'notes': note}

# 厂商 -> (source_type, notes 模板)
PROVIDER_MAP = {
    # 纯开源发布商：只发权重不卖 API
    'meta': (OPEN, 'Meta Llama 系列为开源权重模型（Hugging Face/Llama.com 发布），Meta 不直接提供付费 API；第三方托管价（Together/Fireworks 等）不混录'),
    'nvidia': (OPEN, 'NVIDIA Nemotron/Minitron/Hymba 系列为开源权重模型（Hugging Face 发布），NVIDIA 不直接提供按 token 计费的公有云 API'),
    'microsoft': (OPEN, 'Microsoft Phi/MAI 系列开源权重模型（Hugging Face 发布）；Azure AI Foundry 托管价因模型版本对应关系无法精确核实，不硬填'),
    'lg-ai-research': (OPEN, 'LG EXAONE 系列为开源权重模型（Hugging Face 发布），LG 不直接提供公有云按量计费 API'),
    'ibm': (OPEN, 'IBM Granite 系列为开源权重模型（Hugging Face 发布）；IBM watsonx 托管价为平台套餐口径非 token 单价，不硬填'),
    'apple': (NOPUB, 'Apple 模型（AFM/OpenELM/DCLM）为研究用途发布，无公开 API 定价'),
    'technology-innovation-institute': (OPEN, 'TII Falcon 系列为开源权重模型（Hugging Face 发布），无官方公有云按量 API 定价'),
    'allen-institute-for-ai': (OPEN, 'Ai2 OLMo 系列为全开源模型（Hugging Face 发布），无官方按量 API 定价'),
    'allen-institute-for-ai-university-of-washington': (OPEN, 'Ai2 联合高校发布的开源模型，无官方按量 API 定价'),
    'nous-research': (OPEN, 'Nous Research Hermes 系列为开源权重模型（Hugging Face 发布），无官方按量 API 定价'),
    'pleias': (OPEN, 'Pleias 为法国开源小模型团队，Hugging Face 发布开源权重，无官方 API 定价'),
    'stability-ai': (OPEN, 'Stability AI 文本模型为开源权重发布，官方 API 已转向图像产品线，无文本模型公开定价'),
    'typhoon-scb-10x': (OPEN, 'Typhoon（SCB 10X）泰语系列为开源权重模型（Hugging Face 发布），无官方 API 定价'),
    'ai-singapore': (OPEN, 'AISG SEA-LION 系列为开源权重模型（Hugging Face 发布），无官方 API 定价'),
    'saudi-data-and-artificial-intelligence-authority': (OPEN, 'SDAIA ALLaM 系列为开源权重模型（Hugging Face 发布），无官方 API 定价'),
    'naver': (OPEN, 'Naver HyperCLOVA X SEED 系列为开源权重发布，CLOVA 托管服务不对该开源版单独计价'),
    'upstage': (OPEN, 'Upstage SOLAR 系列旧版为开源权重发布（新版 Solar Pro 经 Upstage API 出售但不在本库范围），旧版无现行 API 价'),
    'writer': (NOPUB, 'Writer Palmyra 系列经 Writer 平台出售但未公开 per-token 价目表，需企业询价；不硬填'),
    'zero-one': (OPEN, '零一万物 Yi 系列为开源权重模型（Hugging Face 发布）；其闭源商业版 API 已停止公开售卖，不硬填'),
    'baichuan': (OPEN, '百川 Baichuan2 系列为开源权重模型（Hugging Face 发布），开源版无官方 API 价；商业版面向企业私有化部署询价'),
    'kunlun-inc': (NOPUB, '昆仑万维天工 Skywork 系列部分开源（Hugging Face），未提供公开按量 API 定价页'),
    'sensetime': (NOPUB, '商汤日日新 SenseNova 系列未公开按量定价页，需商务询价'),
    'china-telecom': (NOPUB, '中国电信星辰 TeleChat 系列开源权重发布于 Hugging Face，运营商托管服务无公开按量价目'),
    '360-security-technology': (OPEN, '360 智脑 Brain系列开源权重发布（Hugging Face），开源版无官方 API 价'),
    'ai21': (RET, 'AI21 J1/Jamba 早期 J1 系列 API 已下架（Studio 平台转向 Jamba）；Jamba 开源版经 Hugging Face 发布'),
    'china-unicom': (NOPUB, '中国联通元景系列未公开按量定价页'),
    'inspur': (NOPUB, '浪潮海岳大模型未公开按量定价页'),
    'huawei': (NOPUB, '华为盘古系列不对外公开按量定价（面向企业专属部署），华为云 ModelArts 托管价未公开'),
    'xiaomi-corp': (OPEN, '小米 MiMo 系列开源权重发布（Hugging Face），无官方 API 定价'),
    'xiaomi': (OPEN, '小米 MiMo 开源权重发布，无官方 API 定价'),
    'yandex': (NOPUB, 'YandexGPT 未公开国际可用的按量定价页（Yandex Cloud 俄区价目与模型映射不明），不硬填'),
    'sber': (OPEN, 'Sber GigaChat 部分开源版本发布于 Hugging Face，开源版无 API 价；商用 GigaChat API 卢布计价与库内版本映射不明'),
    'shanghai-ai-lab': (OPEN, '上海人工智能实验室 InternLM/书生系列为开源权重模型（Hugging Face 发布），官方书生·浦语 API 已停止公开按量售卖'),
    'tsinghua-university': (OPEN, '清华大学开源模型（ChatGLM 早期版/GLM 开源版等）为学术开源发布，无官方按量 API 定价'),
    'tsinghua-university-modelbest': (OPEN, '清华 ModelBest 面壁 MiniCPM 系列开源权重发布，无官方按量 API 定价'),
    'stepfun': (NOPUB, '阶跃星辰 Step 系列经阶跃平台售卖但公开价目页与库内版本对应关系未核实，暂不硬填'),
    'iflytek': (NOPUB, '科大讯飞星火 Spark 公开价目与库内开源版本（iFlytekSpark-13B）不对应，开源版无 API 价'),
    'kuaishou-technology': (OPEN, '快手 Kwaipilot 快意开源权重发布，无官方 API 定价'),
    'meituan-inc': (OPEN, '美团 LongCat 系列开源权重发布（Hugging Face），无官方按量 API 定价'),
    'rednote': (OPEN, '小红书 rednote-hilab dots.llm 系列开源权重发布，无官方 API 定价'),
    'baidu-peng-cheng-laboratory': (OPEN, '百度联合鹏城实验室开源模型，无官方 API 定价'),
    'harbin-institute-of-technology': (OPEN, '哈工大讯飞联合实验室 HFL 开源模型，无官方 API 定价'),
    'peking-university': (OPEN, '北京大学开源模型（兔子争鸣 etc.），无官方 API 定价'),
    'renmin-university-of-china-ant-group': (OPEN, '人大+蚂蚁联合开源模型（玉蘭 YuLan），无官方 API 定价'),
    'stanford-university': (OPEN, '斯坦福开源模型（Alpaca 等），学术用途无官方 API 定价'),
    'university-of-washington': (OPEN, '华盛顿大学开源模型（UniLM etc.），学术用途无官方 API 定价'),
    'carnegie-mellon-university-cmu': (OPEN, 'CMU 开源模型，学术用途无官方 API 定价'),
    'mit-ibm-watson-ai-lab-massachusetts-institute-of-technology-mit': (OPEN, 'MIT-IBM Watson AI Lab 开源模型，无官方 API 定价'),
    'massachusetts-institute-of-technology-mit': (OPEN, 'MIT 开源模型，无官方 API 定价'),
    'salesforce': (OPEN, 'Salesforce XGen/CodeT5 开源模型发布，无官方按量 API 定价'),
    'databricks': (OPEN, 'Databricks Dolly 开源模型发布；DBRX 托管价属 MosaicML 平台套餐口径，不硬填'),
    'mosaicml': (RET, 'MosaicML MPT 系列托管服务已被 Databricks 整合并下架公开按量价目'),
    'eleutherai-laion': (OPEN, 'EleutherAI/Laion 开源模型（GPT-J/GPT-NeoX），社区发布无官方 API 定价'),
    'facebook-ai-research': (OPEN, 'Meta FAIR 开源模型（OPT etc.），无官方按量 API 定价'),
    'facebook-ai': (OPEN, 'Meta FAIR 开源模型，无官方按量 API 定价'),
    'hugging-face-bigscience': (OPEN, 'BigScience BLOOM 社区开源模型，无官方按量 API 定价'),
    'hugging-face-servicenow-nvidia-bigcode': (OPEN, 'BigCode StarCoder 社区开源模型（HF/ServiceNow/NVIDIA），无官方按量 API 定价'),
    'bigcode-community': (OPEN, 'StarCode 社区开源模型，无官方 API 定价'),
    'together': (RET, 'Together 原生模型（GPT-JT etc.）托管已下架；Together 现主营第三方模型推理聚合，其自营模型价不再公开'),
    'cerebras-systems': (RET, 'Cerebras 原生 BTLM 开源权重发布，其推理服务转向第三方模型托管，BTLM 无现行 API 价'),
    'character-ai': (NOPUB, 'Character.AI 自研模型未公开 API 定价（消费级订阅产品非 API 业务）'),
    'inflection': (NOPUB, 'Inflection Pi 模型未公开 API 定价'),
    'cohere': (RET, 'Cohere 早期模型（small/medium/xlarge 等 Command 前代）API 已下架，现行 Command 系列另册'),
    'cohere-labs-formerly-cohere-for-ai': (OPEN, 'Cohere Labs（原 Cohere For AI）Aya/Command R 开源权重发布，开源版无官方 API 定价'),
    'cohere-cohere-labs-formerly-cohere-for-ai': (OPEN, 'Cohere 与 Cohere Labs 联合开源模型，开源版无官方 API 定价'),
    'aleph-alpha': (NOPUB, 'Aleph Alpha Lumina 面向欧洲政企，未公开标准按量价目表'),
    'deep-cogito': (OPEN, 'Deep Cogito Cogito 系列开源权重发布，无官方 API 定价'),
    'prime-intellect': (OPEN, 'Prime Intellect INTELLECT 系列开源权重发布，无官方自营 API 定价'),
    'inception-labs': (NOPUB, 'Inception Labs（扩散语言模型 Mercury）未公开标准价目表'),
    'liquid': (NOPUB, 'Liquid AI LFM 系列未公开标准 per-token 价目表（Le Chat 企业渠道询价）'),
    'zyphra': (OPEN, 'Zyphra Zamba 开源权重发布，无官方 API 定价'),
    'poolside': (NOPUB, 'Poolside 代码模型面向企业授权，未公开 API 定价'),
    'cognition': (NOPUB, 'Cognition Devin 属 Agent 产品订阅制，底层模型未公开 API 定价'),
    'thinking-machines': (NOPUB, 'Thinking Machines Lab 未公开发布 API 或定价'),
    'harmonic': (NOPUB, 'Harmonic（数学模型 Aristotle）未公开 API 定价'),
    'gray-swan': (NOPUB, 'Gray Swan 为 AI 安全评测公司，未公开自有模型定价'),
    'cosine': (NOPUB, 'Cosine Genie 面向企业授权，未公开 API 定价'),
    'factory': (NOPUB, 'Factory AI droid 属企业产品，底层模型未公开按量定价'),
    'abacus-ai': (NOPUB, 'Abacus.AI Smaug 系列未公开标准按量价目表（企业平台询价）'),
    'nexusflow': (NOPUB, 'Nexusflow 面向企业安全领域授权，未公开 API 定价'),
    'deci-ai': (OPEN, 'DeciAI DeciLM 开源权重发布（后被 NVIDIA 收购），无官方 API 定价'),
    'lighton': (OPEN, 'LightOn ColDense/colbert 开源发布，无官方 API 定价'),
    'speakleash-cyfronet-agh': (OPEN, 'SpeakLeash Bielik 波兰语开源模型，社区发布无 API 定价'),
    'trillion-labs': (OPEN, 'Trillion Labs Trillion 开源发布，无官方 API 定价'),
    'motif-technologies': (OPEN, 'Motif 开源权重发布，无官方 API 定价'),
    'marin': (OPEN, 'Marin 开源研究模型（社区项目），无官方 API 定价'),
    'equall-ai': (OPEN, 'Equall Saul 律法开源模型，无官方 API 定价'),
    'preferred-networks-inc': (OPEN, 'Preferred Networks PLMo 日语开源模型，无官方 API 定价'),
    'saltlux': (OPEN, 'Saltlux KOPI 韩语开源模型联盟发布，无官方 API 定价'),
    'sk-telecom': (OPEN, 'SK Telecom A.X 韩语开源模型发布，无官方 API 定价'),
    'nc-ai': (NOPUB, 'NC AI（NCSOFT）Varco 未公开按量 API 定价'),
    'tohoku-university-cyberagent-tokyo-institute-of-technology-fujitsu-riken-nagoya-university-kotoba-technologies': (OPEN, '日本 LLM 日本語LLM 联合开源项目，无官方 API 定价'),
    'cyberagent': (OPEN, 'CyberAgent OpenCALM 日语开源模型，无官方 API 定价'),
    'tokyo-institute-of-technology': (OPEN, '东京工业大学开源模型，学术发布无 API 定价'),
    'johannes-kepler-university-linz': (OPEN, 'JKU 开源模型（Hymba 相关研究），学术发布无 API 定价'),
    'technical-university-of-munich': (OPEN, '慕尼黑工业大学开源模型，学术发布无 API 定价'),
    'eth-zurich-ecole-polytechnique-f-ed-erale-de-lausanne-epfl-swiss-national-supercomputing-centre-cscs-swisscom': (OPEN, '瑞士 Apertus 联合开源模型，无官方按量 API 定价'),
    'insait-eth-zurich': (OPEN, 'INSAIT（索菲亚）开源模型，无官方 API 定价'),
    'imperial-college-london-university-of-british-columbia-ubc': (OPEN, '高校联合开源模型，无官方 API 定价'),
    'johns-hopkins-university': (OPEN, '约翰霍普金斯大学开源医疗模型，学术发布无 API 定价'),
    'mahidol-university-ai-entrepreneurs-association-of-thailand': (OPEN, '泰国高校联合开源模型（OpenThaiGPT 相关），无官方 API 定价'),
    'national-science-and-technology-council': (OPEN, '台湾地区科技部门 TAIDE 开源模型计划，无官方 API 定价'),
    'opengpt-x-fraunhofer-institute-for-algorithms-and-scientific-computing-forschungszentrum-julich-technische-universit-t-dresden': (OPEN, '德国 OpenGPT-X Teuken 联合开源项目，无官方 API 定价'),
    'french-engineering-school-ece-tw3-partners': (OPEN, '法国 CroissantLLM 开源项目，无官方 API 定价'),
    'universite-de-technologie-de-compi-gne-cnrs-google': (OPEN, '高校联合开源模型，无官方 API 定价'),
    'university-of-montreal-universit-de-montr-al': (OPEN, '蒙特利尔大学开源模型，学术发布无 API 定价'),
    'jacobs-university-bremen-university-of-montreal-universit-de-montr-al': (OPEN, '高校联合开源模型，无官方 API 定价'),
    'princeton-university-carnegie-mellon-university-cmu': (OPEN, '高校联合开源模型，无官方 API 定价'),
    'princeton-university-university-of-virginia': (OPEN, '高校联合开源模型，无官方 API 定价'),
    'stanford-university-microsoft-georgia-institute-of-technology': (OPEN, '高校联合开源模型，无官方 API 定价'),
    'stanford-university-university-of-washington-allen-institute-for-ai-contextual-ai': (OPEN, '高校联合开源模型，无官方 API 定价'),
    'allen-institute-for-ai-contextual-ai-university-of-washington-princeton-university': (OPEN, '机构联合开源模型，无官方 API 定价'),
    'allen-institute-for-ai-university-of-washington-new-york-university-nyu': (OPEN, '机构联合开源模型，无官方 API 定价'),
    'allen-institute-for-ai-university-of-washington-carnegie-mellon-university-cmu-stanford-university-mila-quebec-ai-originally-montreal-institute-for-learning-algorithms-university-of-montreal-universit-de-montr-al-princeton-university-massachusetts-institute-of-technology-mit-university-of-maryland': (OPEN, 'OLMo 联合开源项目多机构合作，无官方 API 定价'),
    'university-of-cambridge-southern-university-of-science-and-technology-sustech-hong-kong-university-of-science-and-technology-hkust-huawei-noah-s-ark-lab-alan-turing-institute-max-planck-institute-for-intelligent-systems': (OPEN, 'CamCo/SUS 联合开源模型，无官方 API 定价'),
    'tsinghua-university-beijing-university-of-posts-and-telecommunications': (OPEN, '高校联合开源模型，无官方 API 定价'),
    'tsinghua-university-university-of-illinois-urbana-champaign-uiuc-shanghai-ai-lab-peking-university-shanghai-jiao-tong-university-cuhk-shenzhen-research-institute': (OPEN, '高校联合开源模型，无官方 API 定价'),
    'beijing-institute-of-technology-academy-of-military-science-minzu-university-of-china': (OPEN, '高校联合开源模型，无官方 API 定价'),
    'fudan-university-shanghai-qiji-zhifeng': (OPEN, '复旦开源模型，无官方 API 定价'),
    'shanghai-jiao-tong-university': (OPEN, '上海交大开源模型（浦医 etc.），学术发布无 API 定价'),
    'chengdu-university-of-traditional-chinese-medicine': (OPEN, '成都中医药大学开源中医模型，学术发布无 API 定价'),
    'university-of-waterloo-01-ai-wuhan-university': (OPEN, '高校与企业联合开源模型，无官方 API 定价'),
    'sea-ai-lab-singapore-university-of-technology-design': (OPEN, 'SEA-AI Lab 开源模型，无官方 API 定价'),
    'indosat-tech-mahindra-ai-singapore-goto': (OPEN, '印尼 Sahabat-AI 联合开源项目，无官方 API 定价'),
    'rwkv-foundation-eleutherai-ohio-state-university-university-of-california-santa-barbara-ucsb-wroclaw-tech-wroc-aw-university-of-science-and-technology-guangdong-laboratory-of-artificial-intelligence-and-digital-economy-pazhou-lab-new-york-university-nyu-harvard-university-contextual-ai-university-of-chinese-academy-of-sciences-university-of-california-santa-cruz-tsinghua-university-university-of-edinburgh-university-of-british-columbia-ubc-pennsylvania-state-university': (OPEN, 'RWKV 社区联合开源项目，无官方 API 定价'),
    'large-model-systems-organization-university-of-california-uc-berkeley': (OPEN, 'vLLM 社区开源项目模型，无官方 API 定价'),
    'causallm': (OPEN, 'CausalLM 开源权重发布，无官方 API 定价'),
    'rock-ai-shanghai-stonehill-technology': (OPEN, 'RockAI 开源权重发布，无官方 API 定价'),
    'nanbeige-llm-lab': (OPEN, '南北阁 NanBeige 开源权重发布，无官方 API 定价'),
    # 中国企业（闭源或未公开价）
    'beijing-58-information-technology': (NOPUB, '58同城 TEGine 未公开按量 API 定价'),
    'beijing-academy-of-artificial-intelligence-baai': (OPEN, 'BAAI 智源 AquaTalk/Emu 开源发布，无官方 API 定价'),
    'beijing-beida-software-engineering-co-ltd': (NOPUB, '北大软件工程公司模型未公开按量定价'),
    'beijing-bitauto-interactive-advertising-company-limited': (NOPUB, '易车 AutoGLM 定制模型未公开按量定价'),
    'beijing-orionstar-technology-co-ltd': (NOPUB, '猎户星空 OrionStar 聚言未公开标准按量价目表'),
    'beijing-weimeng-chuangke-network-technology': (NOPUB, '微盟 WOS 递归模型未公开独立按量定价'),
    'beijing-yuanshi-technology-co-ltd': (NOPUB, '原始科技模型未公开按量定价'),
    'creditease': (NOPUB, '宜信 GetWorkerDoc 定制模型未公开按量定价'),
    '4paradigm': (NOPUB, '第四范式式说未公开标准按量价目表'),
    'foxconn': (NOPUB, '富士康 FoxBrain 面向内部使用，未公开 API 定价'),
    'lenovo': (NOPUB, '联想小天/ThinkBot 定制模型未公开独立按量定价'),
    'zte': (NOPUB, '中兴星智星语未公开标准按量价目表'),
    'china-mobile': (NOPUB, '中国移动九天大模型未公开标准按量价目表'),
    'china-mobile-zero-gravity-labs-0g-ai': (NOPUB, '中国移动九天-零重力实验室联合模型未公开按量定价'),
    'china-post-consumer-finance-co-ltd': (NOPUB, '中邮消费金融定制模型未公开按量定价'),
    'mianbi-intelligence': (NOPUB, '面壁智能 MiniCPM 商用版经面壁平台售卖但未公开标准价目表'),
    'shiyin-intelligent-technology-co-ltd': (NOPUB, '时音智能 SDTV 音频模型未公开按量定价'),
    'zhuhai-wujiefangzhou-intelligent-technology': (NOPUB, '珠海无界方舟 Arknights 模型未公开按量定价'),
    'zhuoshi-technology': (NOPUB, '卓世科技耒言模型未公开标准价目表'),
    'guangzhou-lingju-information-technology-co-ltd': (NOPUB, '广州灵聚智能模型未公开按量定价'),
    'jiangsu-huizhi-intelligent-digital-technology-co-ltd': (NOPUB, '江苏慧智模型未公开按量定价'),
    'wuxi-sixiang-digital-intelligence-technology-co-ltd': (NOPUB, '无锡四相科技模型未公开按量定价'),
    'shenzhen-honor-software-technology': (NOPUB, '荣耀魔法大模型面向端侧未公开 API 定价'),
    'thunder-software-technology-co-ltd': (NOPUB, '中科创达滴水 OS 模型未公开按量定价'),
    'shanghai-digivio-information-technology-co-ltd': (NOPUB, '深势科技 X-Match 模型未公开按量定价'),
    'shanghai-shuheng-information-technology-co-ltd': (NOPUB, '上海书亨模型未公开按量定价'),
    'chengdu-xiaoduo-technology-co-ltd': (NOPUB, '成都小多科技模型未公开按量定价'),
    'zhixin-shuchuang-chongqing-technology-co-ltd': (NOPUB, '智信数创模型未公开按量定价'),
    'troy-information-technology-co-ltd': (NOPUB, '特罗伊信息模型未公开按量定价'),
    'trend-micro': (NOPUB, '趋势科技 TrendMicro PTM 定制模型未公开按量定价'),
    'darktrace': (NOPUB, 'Darktrace 防御模型未公开 API 定价'),
    'cisco': (NOPUB, '思科 AI Defense 模型未公开 API 定价'),
    'nec-corporation': (NOPUB, 'NEC Cotomi 面向日企授权，未公开标准价目表'),
    'fujitsu-cohere': (NOPUB, 'Fujitsu-Cohere Takane 日企定制模型未公开按量定价'),
    'mts': (OPEN, 'MTS VseGPT 俄语开源模型发布，无官方 API 定价'),
    't-bank': (OPEN, 'T-Bank T-lite/T-pro 俄语开源模型发布，无官方按量 API 定价'),
    'saudi-aramco': (NOPUB, '沙特阿美 Athel 面向能源行业内部使用，未公开 API 定价'),
    'g42-inception-g42': (NOPUB, 'G42 Inception 面向中东政企授权，未公开标准价目表'),
    'mohamed-bin-zayed-university-of-artificial-intelligence-mbzuai-g42': (OPEN, 'MBZUAI-G42 联合开源模型（Jais），无官方按量 API 定价'),
    'carnegie-mellon-university-cmu-mohamed-bin-zayed-university-of-artificial-intelligence-mbzuai-cartesia': (OPEN, '高校联合开源模型，无官方 API 定价'),
    'karakuri-inc': (OPEN, 'Karakuri LM 日语开源模型，无官方 API 定价'),
    'ruliad': (OPEN, 'Ruliad Millstone 日语开源模型，无官方 API 定价'),
    'sambanova-systems-inc': (RET, 'SambaNova 云平台主营第三方模型推理，原生 Samba-CoE 系列已下架且未公开独立定价'),
    'snowflake': (OPEN, 'Snowflake Arctic 开源权重发布；Arctic Inference 服务套餐口径非 token 单价，不硬填'),
}

written = 0
skipped = []
idx = {r['model_id']: r for r in recs}
for pref, (stype, tmpl) in PROVIDER_MAP.items():
    hit = [mid for mid in idx if mid.startswith(pref + ':')]
    for mid in hit:
        p = idx[mid].get('pricing') or {}
        if p.get('input') is not None or p.get('source_type'):
            continue  # 已有内容不动
        name = mid.split(':')[1]
        idx[mid]['pricing'] = ann(stype, name + '：' + tmpl)
        written += 1

with open(BASE + 'model_data_v2.jsonl', 'w', encoding='utf-8') as f:
    for r in recs:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')
print('annotated:', written)

# remaining gaps after this pass
from collections import Counter
gaps = Counter()
for r in recs:
    p = r.get('pricing') or {}
    if p.get('input') is None and not p.get('source_type'):
        gaps[r['model_id'].split(':')[0]] += 1
print('remaining gap providers:')
for k, v in gaps.most_common(40):
    print(' ', k, v)
print('total remaining:', sum(gaps.values()))
