import { useEffect, useState } from 'react'
import { api } from './api'

export let ENTRY_TYPES = ['想法', '知识', '资料', '记录', '规则']
export let DOMAINS = ['身心', '生活', '能力', '财务', '方向']
export let SOURCES = ['我', '图片', '文件']

export const SOURCE_LABELS = { 自己: '我', 截图: '图片', 我: '我', 图片: '图片', 文件: '文件' }
export const TYPE_LABELS = { 句子: '想法', 决策: '规则' }

export let TOPICS_BY_DOMAIN = {
  身心: ['ADHD', '情绪', '药物', '运动', '睡眠', '身体'],
  生活: ['马德里', '居住', '证件', '合同', '关系', '日常'],
  能力: ['西班牙语', 'AI', '编程', '服务器', '产品', '学习'],
  财务: ['债务', '收入', '消费', '投资', '房产', '交易'],
  方向: ['目标', '底线', '规则', '决策', '复盘', '正向循环'],
}
export let ALL_TOPICS = Object.values(TOPICS_BY_DOMAIN).flat()

export let SUB_TOPICS_BY_TOPIC = {
  ADHD: ['注意力', '执行力', '拖延', '冲动', '情绪调节', '工作记忆', '时间管理', '药物配合', '反馈机制', '环境设计', '外部提醒', '任务启动', '行为激活', '认知 CBT', '情绪 CBT', '行动 CBT', '成人 ADHD CBT', '未细分'],
  情绪: ['愤怒', '焦虑', '恐惧', '烦躁', '无奈', '委屈', '低落', '自责', '羞耻', '孤独', '压力', '兴奋', '开心', '满足', '平静', '调节', '未细分'],
  药物: ['专注达', '褪黑素', '补剂', '剂量', '药效', '反跳', '副作用', '处方', '药盒', '未细分'],
  运动: ['开始运动', '训练记录', '俯卧撑', '深蹲', '卷腹', '平板支撑', '热身', '拉伸', '居家训练', '出汗', '姿态', '未细分'],
  睡眠: ['入睡', '熬夜', '早起', '睡眠质量', '午睡', '作息', '失眠', '褪黑素', '未细分'],
  身体: ['皮肤', '肠胃', '疼痛', '体重', '饮食', '性健康', '体检', '疲劳', '未细分'],
  马德里: ['交通', 'EMT', '地铁', '区域', '房源', '办事', '生活便利', '未细分'],
  居住: ['租房', '买房', '搬家', '房间', '社区', '房东', '未细分'],
  证件: ['NIE', '居留', '护照', '社保', 'Cl@ve', '住家证明', '政府材料', '未细分'],
  合同: ['租房合同', '工作合同', '服务合同', '押金', '条款', '签字', '未细分'],
  关系: ['朋友', '伴侣', '父母', '兄弟', '家庭', '边界', '冲突', '沟通', '借钱', '未细分'],
  日常: ['通勤', '上班', '下班', '吃饭', '购物', '清洁', '出门', '回家', '时间线', '未细分'],
  西班牙语: ['词块', '语法', '冠词', '动词', '名词', '听力', '口语', '阅读', '写作', 'A1', 'A2', '未细分'],
  AI: ['ChatGPT', 'Claude', 'OpenRouter', 'Agent', 'Prompt', 'OCR', '自动化', '工作流', '未细分'],
  编程: ['Python', 'JavaScript', 'React', 'FastAPI', 'PostgreSQL', '脚本', 'Bug', 'API', '未细分'],
  服务器: ['VPS', '1Panel', 'Nginx', 'Cloudflare', 'Docker', '备份', '部署', '安全', '未细分'],
  产品: ['ZBrain', 'z-image', 'z-sports', 'PWA', 'UI', '内容坐标', '数据库', '未细分'],
  学习: ['学习方法', '理解', '复述', '内化', '构建体系', '阅读', '记忆', '复习', '输入', '输出', '练习', '学习计划', '验收', '未细分'],
  债务: ['欠款', '还款', '朋友借钱', '止血', '债务风险', '清算', '未细分'],
  收入: ['工资', '副业', '项目收入', '技能变现', '稳定收入', '未细分'],
  消费: ['订阅', '冲动消费', '预算', '购买决策', '省钱', '账单', '未细分'],
  投资: ['ETF', 'VUAA', 'EQQB', '长期定投', '养老金', '股票', '组合', '投资风险', '未细分'],
  房产: ['买房', '卖房', '房贷', '估值', 'Nota Simple', '区域', '产权', '赠与', '未细分'],
  交易: ['合约', 'Binance', '杠杆', '爆仓', '风控', '冲动交易', '复盘', '禁止交易', '交易周期', '扛单', '重仓', '未细分'],
  目标: ['今日目标', '本周目标', '年度目标', '四年计划', '长期目标', '健康', '技能', '存款', '未细分'],
  底线: ['不新增债务', '不交易', '不伤害自己', '不冲动', '生存优先', '止损', '未细分'],
  规则: ['不做清单', '行为限制', '执行规则', '冲动控制', '睡眠规则', '运动规则', '消费规则', '未细分'],
  决策: ['已决定', '选择', '放弃', '暂缓', '路线', '优先级', '落子无悔', '未细分'],
  复盘: ['错误', '原因', '教训', '改进', '反面样本', '亏损复盘', '未细分'],
  正向循环: ['行动转化', '运动转化', '情绪转化', '学习循环', '存钱循环', '睡眠循环', '自我建设', '今天完成', '未细分'],
}

const listeners = new Set()
let loadPromise = null

function notify() {
  listeners.forEach((fn) => fn())
}

function buildSections() {
  return [
    {
      title: '类型 = 内容形态',
      items: [
        ['想法', '我的理解、判断、感悟、句子、认知沉淀'],
        ['知识', '外部经验、教程、解释、可学习内容'],
        ['资料', '合同、证件、药盒、票据、配置、需要留存的材料'],
        ['记录', '我的时间线、状态、情绪、用药、运动、睡眠'],
        ['规则', '底线、决策、行为准则、不做清单'],
      ].filter(([name]) => ENTRY_TYPES.includes(name)),
    },
    {
      title: '领域 = 人生大区',
      items: [
        ['身心', '身体、大脑、情绪、ADHD、药物、运动、睡眠、健康'],
        ['生活', '马德里、居住、证件、合同、关系、家庭、日常、办事'],
        ['能力', '西班牙语、AI、编程、项目、服务器、产品、学习、写作'],
        ['财务', '债务、收入、消费、投资、房产、交易、风控、养老金'],
        ['方向', '目标、底线、长期规划、人生策略、正向循环、自我重建'],
      ].filter(([name]) => DOMAINS.includes(name)),
    },
    {
      title: '主题 = 主要讲什么',
      items: Object.entries(TOPICS_BY_DOMAIN).map(([domain, topics]) => [domain, topics.join(' / ')]),
    },
  ]
}

export let CLASSIFICATION_SECTIONS = buildSections()

function applySchema(schema) {
  if (!schema) return
  if (Array.isArray(schema.entry_types)) ENTRY_TYPES = schema.entry_types
  if (Array.isArray(schema.domains)) DOMAINS = schema.domains
  if (Array.isArray(schema.sources)) SOURCES = schema.sources
  if (schema.topics_by_domain && typeof schema.topics_by_domain === 'object') {
    TOPICS_BY_DOMAIN = schema.topics_by_domain
  }
  if (schema.sub_topics_by_topic && typeof schema.sub_topics_by_topic === 'object') {
    SUB_TOPICS_BY_TOPIC = schema.sub_topics_by_topic
  }
  ALL_TOPICS = Object.values(TOPICS_BY_DOMAIN).flat()
  CLASSIFICATION_SECTIONS = buildSections()
  notify()
}

export function loadClassificationSchema() {
  if (!loadPromise) {
    loadPromise = api.classificationSchema().then(applySchema).catch(() => null)
  }
  return loadPromise
}

export function useClassificationSchema() {
  const [version, setVersion] = useState(0)
  useEffect(() => {
    const listener = () => setVersion((v) => v + 1)
    listeners.add(listener)
    loadClassificationSchema()
    return () => listeners.delete(listener)
  }, [])
  return {
    version,
    ENTRY_TYPES,
    DOMAINS,
    SOURCES,
    TOPICS_BY_DOMAIN,
    SUB_TOPICS_BY_TOPIC,
    ALL_TOPICS,
    CLASSIFICATION_SECTIONS,
  }
}

export function displaySource(value, fallback = '我') {
  return SOURCE_LABELS[value] || fallback
}

export function displayType(value) {
  return TYPE_LABELS[value] || value || ''
}
