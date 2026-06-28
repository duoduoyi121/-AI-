import numpy as np
from PIL import Image
import requests
from io import BytesIO
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import re
import random


class AIService:
    def __init__(self):
        """初始化AI服务层，加载模型并初始化对话上下文和相关规则引擎"""
        self.image_model = None
        self.text_model = None
        self.tokenizer = None
        self.device = None

        # 对话上下文缓存，key为 user_id，value 为上下文字典
        self._chat_contexts: Dict[int, Dict[str, Any]] = {}

        # 尝试加载AI模型，如果失败则使用备用方案
        try:
            import torch
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            self._load_text_model()
        except ImportError:
            print("警告: torch未安装，AI功能将使用备用方案")
        except Exception as e:
            print(f"警告: AI模型加载失败 - {e}")

        # ========== 物品类别关键词映射 ==========
        self._category_keywords: Dict[str, List[str]] = {
            '电子设备': ['手机', '电脑', '平板', '笔记本', '耳机', '充电器', '数据线',
                       '移动电源', 'U盘', '硬盘', '相机', '电子', '设备', '数码',
                       'iPad', 'iPhone', 'MacBook', 'watch', '手环'],
            '证件卡片': ['身份证', '学生证', '校园卡', '银行卡', '会员卡', '社保卡',
                       '驾驶证', '护照', '工作证', '饭卡', '胸卡', '门禁卡'],
            '箱包': ['背包', '书包', '手提包', '行李箱', '旅行箱', '挎包', '腰包',
                    '钱包', '卡包', '袋子', '箱子', '行李', '拉杆箱'],
            '书籍文具': ['书', '课本', '教材', '笔记本', '文具', '笔', '尺子',
                        '橡皮', '文件夹', '本子', '资料', '打书', '文件'],
            '服饰': ['衣服', '外套', '裤子', '鞋子', '帽子', '围巾', '手套',
                    'T恤', '衬衫', '裙子', '袜子', '眼镜', '手表', '首饰'],
            '钥匙': ['钥匙', '钥匙串', '钥匙扣', '门卡', '锁匙'],
            '其他': []
        }

        # ========== 高发时段划分 ==========
        self._time_slots: List[Dict[str, Any]] = [
            {'name': '早晨(6:00-8:00)', 'start': 6, 'end': 8},
            {'name': '上午(8:00-12:00)', 'start': 8, 'end': 12},
            {'name': '午间(12:00-14:00)', 'start': 12, 'end': 14},
            {'name': '下午(14:00-18:00)', 'start': 14, 'end': 18},
            {'name': '傍晚(18:00-20:00)', 'start': 18, 'end': 20},
            {'name': '晚间(20:00-24:00)', 'start': 20, 'end': 24},
        ]

        # ========== 保管方式推荐规则 ==========
        self._storage_rules: Dict[str, List[str]] = {
            '电子设备': ['存放于带锁的失物柜中，保持干燥', '使用防静电袋包裹后放入储物箱',
                        '充电设备需标注是否已充电'],
            '证件卡片': ['放入专用证件收纳盒，按类别分类', '第一时间录入系统并通知失主所在院系',
                        '建议扫描备份后妥善保管'],
            '箱包': ['存放于储物柜中，较大背包可挂放', '检查所有口袋是否有贵重物品',
                    '用标签注明拾取地点和时间'],
            '书籍文具': ['按学科分类放于书架上', '笔记本内如有姓名请及时联系失主',
                        '建议录入书名信息便于搜索'],
            '服饰': ['清洗后折叠放于储物柜', '贵重衣物（如品牌外套）单独存放',
                    '标注颜色和尺码便于识别'],
            '钥匙': ['挂于钥匙专用挂板上并编号', '登记钥匙特征（颜色、品牌、挂件）',
                    '勿与其他金属物品混放以免刮花'],
            '其他': ['存放于通用失物保管柜中', '按拾取日期分类摆放',
                    '对于易碎品需标注"小心轻放"']
        }

        # ========== 认领建议规则 ==========
        self._claim_advice_rules: Dict[str, Dict[str, Any]] = {
            '电子设备': {
                'advice': '认领电子设备时，请尽量提供设备的唯一标识信息，如IMEI号、序列号、MAC地址等。'
                          '若能提供设备解锁密码或展示设备内的个人账户信息，将大大提高认领成功率。',
                'required_proof': ['IMEI/序列号', '解锁密码', '设备内照片', '购买凭证'],
                'tips': ['提前准备好设备包装盒（上有序列号）', '可在手机设置中查看IMEI信息']
            },
            '手机': {
                'advice': '认领手机时，建议通过拨打该手机号码、提供解锁密码或展示手机联系人等方式证明所有权。'
                          '如果手机已关机，请提供手机型号、颜色、手机壳特征等详细信息。',
                'required_proof': ['手机号码验证', '解锁密码', '手机IMEI号', '购买发票'],
                'tips': ['可让朋友拨打你的号码进行验证', '提供手机内壁贴纸信息']
            },
            '证件卡片': {
                'advice': '认领证件时，请提供证件上的姓名和证件号后四位进行验证。'
                          '若由他人代领，需出示代领人身份证件及失主授权证明。',
                'required_proof': ['姓名核实', '证件号后四位', '本人身份证', '授权委托书（代领）'],
                'tips': ['提前准备好身份证复印件', '确认证件上的照片是你本人']
            },
            '箱包': {
                'advice': '认领箱包时，请准确描述包内物品，特别是具有个人特征的物品。'
                          '若能提供包内重要物品的照片作为佐证，认领流程会更顺利。',
                'required_proof': ['包内物品清单', '包内特殊物品描述', '品牌及颜色'],
                'tips': ['回忆包内有哪些独特的物品', '包里可能有的票据或卡片信息']
            },
            '书籍文具': {
                'advice': '认领书籍文具时，请提供书籍名称、扉页签名或笔记特征等信息。'
                          '如为教材，可提供课程名称和教师姓名辅助确认。',
                'required_proof': ['书名确认', '扉页签名', '笔记特征', '课程信息'],
                'tips': ['检查书籍扉页是否有姓名或学号', '提供课本封面照片便于匹配']
            },
            '服饰': {
                'advice': '认领服饰时，请准确描述品牌、颜色、尺码和特殊标记。'
                          '若服饰内有个人物品（如口袋中的耳机），一并描述可提高可信度。',
                'required_proof': ['品牌描述', '颜色尺码', '特殊标记', '内袋物品'],
                'tips': ['确认服饰内是否有私人物品', '注意服饰上的独特标识或修补痕迹']
            },
            '钥匙': {
                'advice': '认领钥匙时，请描述钥匙的数量、品牌特征和钥匙扣样式。'
                          '若能现场演示钥匙能打开对应的锁具即可直接确认。',
                'required_proof': ['钥匙数量', '品牌特征', '钥匙扣描述', '现场开锁验证'],
                'tips': ['描述钥匙上是否有特殊标记', '携带钥匙串的照片便于比对']
            },
            '其他': {
                'advice': '请尽可能提供物品的详细特征信息，包括颜色、品牌、尺寸、特殊标记等。'
                          '若有物品的照片或购买凭证，将有助于快速确认身份。',
                'required_proof': ['详细特征描述', '品牌信息', '购买凭证'],
                'tips': ['回忆物品的独特之处', '检查是否有刻字或标记']
            }
        }

        # ========== 通知模板 ==========
        self._notification_templates: Dict[str, str] = {
            'match_found': '【系统通知】{username}您好！您在{location}{action}的{item_name}已找到匹配，'
                           '匹配度{score}%。请前往查看详情。',
            'match_updated': '【匹配更新】{username}您好！您{action}的{item_name}匹配状态已更新为{status}。',
            'claim_received': '【认领通知】{username}您好！有用户申请认领您{item_type}的{item_name}，'
                              '请及时处理认领请求。',
            'claim_approved': '【认领通过】{username}您好！您的认领申请已通过审核，'
                              '请前往{location}领取您的{item_name}。',
            'claim_rejected': '【认领未通过】{username}您好！您的认领申请未通过审核，'
                              '原因：{reason}。如有疑问请联系管理员。',
            'item_expiring': '【物品提醒】{username}您好！您{item_type}的{item_name}即将超过保管期限，'
                             '请及时处理。',
            'credit_changed': '【积分变动】{username}您好！您的信用积分{action}了{points}分，'
                              '当前积分：{current_score}分。',
            'system_announcement': '【系统公告】{content}',
        }

    # ========================================================================
    #  以下为保留的现有方法（完全兼容原有接口）
    # ========================================================================

    def _load_text_model(self):
        """
        加载文本处理模型
        实际项目中应使用预训练的BERT模型
        """
        try:
            from transformers import BertTokenizer, BertModel
            self.tokenizer = BertTokenizer.from_pretrained('bert-base-chinese')
            self.text_model = BertModel.from_pretrained('bert-base-chinese').to(self.device)
            self.text_model.eval()
        except:
            # 如果模型加载失败，使用模拟实现
            self.text_model = None
            self.tokenizer = None

    def get_image_features(self, image_path: str) -> np.ndarray:
        """
        提取图像特征
        :param image_path: 图像路径或URL
        :return: 图像特征向量（128维）
        """
        try:
            if isinstance(image_path, str) and image_path.startswith('http'):
                # 从URL加载图像
                response = requests.get(image_path)
                image = Image.open(BytesIO(response.content))
            else:
                # 从本地路径加载图像
                image = Image.open(image_path)

            # 模拟128维特征向量
            features = np.random.rand(128)
            return features
        except:
            # 如果特征提取失败，返回随机特征
            return np.random.rand(128)

    def get_text_features(self, text: str) -> np.ndarray:
        """
        提取文本特征
        :param text: 文本内容
        :return: 文本特征向量（768维）
        """
        try:
            if self.text_model and self.tokenizer:
                import torch
                inputs = self.tokenizer(text, return_tensors='pt', padding=True,
                                        truncation=True, max_length=128)
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                with torch.no_grad():
                    outputs = self.text_model(**inputs)
                # 使用[CLS] token的嵌入作为文本特征
                features = outputs.last_hidden_state[:, 0, :].cpu().numpy().squeeze()
                return features
            else:
                # 模拟768维特征向量
                return np.random.rand(768)
        except:
            # 如果特征提取失败，返回随机特征
            return np.random.rand(768)

    def calculate_image_similarity(self, image1: str, image2: str) -> float:
        """
        计算图像相似度
        :param image1: 第一个图像路径或URL
        :param image2: 第二个图像路径或URL
        :return: 相似度得分 (0-1)
        """
        try:
            if not image1 or not image2:
                return 0.5

            # 提取特征
            features1 = self.get_image_features(image1)
            features2 = self.get_image_features(image2)

            # 计算余弦相似度
            similarity = np.dot(features1, features2) / (
                np.linalg.norm(features1) * np.linalg.norm(features2)
            )
            # 确保相似度在0-1之间
            similarity = max(0, min(1, similarity))
            return similarity
        except:
            # 如果计算失败，返回默认值
            return 0.5

    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        计算文本相似度
        :param text1: 第一个文本
        :param text2: 第二个文本
        :return: 相似度得分 (0-1)
        """
        try:
            # 提取特征
            features1 = self.get_text_features(text1)
            features2 = self.get_text_features(text2)

            # 计算余弦相似度
            similarity = np.dot(features1, features2) / (
                np.linalg.norm(features1) * np.linalg.norm(features2)
            )
            # 确保相似度在0-1之间
            similarity = max(0, min(1, similarity))
            return similarity
        except:
            # 如果计算失败，使用简单的词袋模型
            text1_words = set(text1.lower().split())
            text2_words = set(text2.lower().split())
            common_words = text1_words & text2_words
            total_words = text1_words | text2_words
            return len(common_words) / len(total_words) if total_words else 0.5

    def predict_item_category(self, image: Optional[str] = None,
                              text: Optional[str] = None) -> Dict[str, str]:
        """
        预测物品类别和细分类型

        :param image: 图像路径或URL
        :param text: 文本描述
        :return: {'category': 主类别, 'sub_category': 细分类型}
        """
        # 物品类别列表
        categories = [
            '电子设备', '证件卡片', '箱包', '书籍文具',
            '服饰', '钥匙', '其他'
        ]

        # 细分类型关键词映射
        sub_category_keywords = {
            '电子设备': {
                '手机': ['手机', 'iPhone', '华为', '小米', 'OPPO', 'vivo'],
                '平板': ['平板', 'iPad'],
                '笔记本电脑': ['笔记本', '电脑', 'MacBook', '联想', '戴尔'],
                '耳机/音箱': ['耳机', '音箱', 'AirPods'],
                '智能手表/手环': ['手表', '手环', 'watch', 'Apple Watch'],
                '相机': ['相机', '单反', '微单'],
                'U盘/硬盘': ['U盘', '硬盘', '移动硬盘'],
                '充电器/数据线': ['充电器', '数据线', '充电线']
            },
            '证件卡片': {
                '身份证': ['身份证'],
                '学生证': ['学生证'],
                '校园卡': ['校园卡', '饭卡'],
                '银行卡': ['银行卡', '信用卡'],
                '驾驶证': ['驾驶证', '驾照'],
                '护照': ['护照']
            },
            '箱包': {
                '双肩包': ['双肩包', '背包', '书包'],
                '单肩包/挎包': ['挎包', '单肩包'],
                '手提包': ['手提包'],
                '钱包/卡包': ['钱包', '卡包'],
                '行李箱': ['行李箱', '旅行箱', '拉杆箱']
            },
            '服饰': {
                '上衣/T恤': ['T恤', '上衣', '衬衫'],
                '外套': ['外套', '夹克'],
                '裤子': ['裤子', '牛仔裤'],
                '鞋子': ['鞋子', '运动鞋', '皮鞋'],
                '帽子': ['帽子'],
                '眼镜': ['眼镜']
            },
            '其他': {
                '水杯/保温杯': ['水杯', '保温杯', '杯子'],
                '雨伞': ['雨伞', '伞'],
                '钥匙': ['钥匙', '钥匙串']
            }
        }

        try:
            if text:
                # 基于文本关键词匹配进行类别预测
                predicted_category = None
                for category, keywords in self._category_keywords.items():
                    for keyword in keywords:
                        if keyword in text:
                            predicted_category = category
                            break
                    if predicted_category:
                        break

                if not predicted_category:
                    features = self.get_text_features(text)
                    category_index = int(np.sum(features) * len(categories) % len(categories))
                    predicted_category = categories[category_index]

                # 预测细分类型
                predicted_sub = None
                if predicted_category in sub_category_keywords:
                    for sub_cat, sub_keywords in sub_category_keywords[predicted_category].items():
                        for kw in sub_keywords:
                            if kw in text:
                                predicted_sub = sub_cat
                                break
                        if predicted_sub:
                            break

                return {
                    'category': predicted_category,
                    'sub_category': predicted_sub or ''
                }
            elif image:
                features = self.get_image_features(image)
                category_index = int(np.sum(features) * len(categories) % len(categories))
                return {
                    'category': categories[category_index],
                    'sub_category': ''
                }
            else:
                return {'category': '其他', 'sub_category': ''}
        except:
            return {'category': '其他', 'sub_category': ''}

    def enhance_description(self, description: str) -> str:
        """
        增强物品描述
        :param description: 原始描述
        :return: 增强后的描述
        """
        # 使用规则增强描述
        enhancements = {
            '蓝色': '蓝色，颜色鲜艳',
            '黑色': '黑色，外观整洁',
            '红色': '红色，非常显眼',
            '绿色': '绿色，颜色清新',
            '白色': '白色，干净整洁',
            '钱包': '钱包，可能包含证件和现金',
            '手机': '手机，可正常开机',
            '笔记本电脑': '笔记本电脑，外观完好',
            '背包': '背包，有肩带和拉链',
            '钥匙': '钥匙，可能有钥匙扣',
            '身份证': '身份证，重要证件',
            '学生证': '学生证，校园身份凭证'
        }

        enhanced = description
        for key, value in enhancements.items():
            if key in description:
                enhanced = enhanced.replace(key, value)

        return enhanced

    # ========================================================================
    #  以下为新增的AI助手核心方法
    # ========================================================================

    # --------------------------------------------------------------------------
    #  1. 对话回复 —— 基于规则引擎的意图识别与回复生成
    # --------------------------------------------------------------------------
    def chat(self, message: str, user_id: Optional[int] = None,
             context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        智能对话回复，基于规则引擎识别用户意图并生成友好的中文回复。

        支持的意图类型：
          - query_my_items: 查询"我的物品/失物/招领"
          - publish_guide: 查询"怎么/如何...登记/发布"
          - match_info: 查询"匹配/找到/寻找"
          - claim_info: 查询"认领/领取"
          - system_stats: 查询"统计/数据/多少"
          - help_list: 查询"帮助/功能/能做什么"
          - greeting: 问候语（你好/嗨/hello等）
          - unknown: 其他未匹配的通用回复

        :param message: 用户输入的消息文本
        :param user_id: 用户ID（可选），用于上下文追踪
        :param context: 额外的上下文信息（可选），如登录状态、页面信息等
        :return: 包含回复文本、意图类型、推荐操作的字典
        """
        # ---------- 初始化/更新上下文 ----------
        ctx = self._chat_contexts.setdefault(user_id or 0, {
            'user_id': user_id,
            'session_start': datetime.now(),
            'message_count': 0,
            'last_intent': None,
            'is_logged_in': False,
            'last_topics': [],
        })
        if context:
            ctx.update(context)
        ctx['message_count'] += 1

        # 清洗用户输入
        cleaned = message.strip()

        # ---------- 意图识别 ----------
        intent, matched_pattern = self._recognize_intent(cleaned)

        # 更新上下文的最后意图
        ctx['last_intent'] = intent

        # ---------- 根据意图生成回复 ----------
        if intent == 'greeting':
            reply = self._build_greeting_reply(ctx, matched_pattern)
        elif intent == 'query_my_items':
            reply = self._build_my_items_reply(ctx, matched_pattern)
        elif intent == 'publish_guide':
            reply = self._build_publish_guide_reply(ctx, matched_pattern)
        elif intent == 'match_info':
            reply = self._build_match_info_reply(ctx, matched_pattern)
        elif intent == 'claim_info':
            reply = self._build_claim_info_reply(ctx, matched_pattern)
        elif intent == 'system_stats':
            reply = self._build_system_stats_reply(ctx, matched_pattern)
        elif intent == 'lost_prevention':
            reply = self._build_lost_prevention_reply(ctx, matched_pattern)
        elif intent == 'category_help':
            reply = self._build_category_help_reply(ctx, matched_pattern)
        elif intent == 'location_help':
            reply = self._build_location_help_reply(ctx, matched_pattern)
        elif intent == 'credit_info':
            reply = self._build_credit_info_reply(ctx, matched_pattern)
        elif intent == 'contact_admin':
            reply = self._build_contact_admin_reply(ctx, matched_pattern)
        elif intent == 'help_list':
            reply = self._build_help_list_reply()
        else:
            reply = self._build_unknown_reply(cleaned)

        # ---------- 添加上下文提示 ----------
        reply_with_hint = reply + '\n\n✨ 您还可以问我：关于"发布物品"、"如何认领"、"查找匹配"、"系统数据"等，随时为您解答！'

        ctx['last_topics'].append(intent)
        if len(ctx['last_topics']) > 5:
            ctx['last_topics'].pop(0)

        return {
            'reply': reply_with_hint,
            'intent': intent,
            'matched_pattern': matched_pattern,
            'context': {
                'user_id': user_id,
                'is_logged_in': ctx.get('is_logged_in', False),
                'message_count': ctx['message_count'],
            }
        }

    def _recognize_intent(self, text: str) -> Tuple[str, Optional[str]]:
        """
        识别用户消息的意图。

        返回 (意图名称, 匹配到的模式)
        """
        # 意图识别规则：按优先级从高到低匹配
        intent_patterns: List[Tuple[str, List[str]]] = [
            ('greeting', [
                '你好', '您好', '嗨', 'hello', 'hi', 'hey', '早上好', '下午好',
                '晚上好', '你好呀', '在吗', '在不在', '哈喽', '喂',
            ]),
            ('query_my_items', [
                '我的物品', '我的失物', '我的招领', '我发布的', '我的发布',
                '我丢', '我捡', '看看我的', '我的记录', '我的匹配',
            ]),
            ('publish_guide', [
                '怎么发布', '怎么登记', '如何发布', '如何登记', '怎样发布',
                '怎样登记', '发布指南', '登记指南', '怎么上传', '如何上传',
                '不会发布', '不会登记', '怎么发失物', '怎么发招领',
            ]),
            ('match_info', [
                '匹配', '找到', '寻找', '查找匹配', '匹配结果', '智能匹配',
                '怎么匹配', '如何匹配', '匹配推荐', '推荐匹配',
            ]),
            ('claim_info', [
                '认领', '领取', '怎么认领', '如何认领', '怎样认领',
                '认领流程', '认领指南', '怎么领取', '如何领取',
                '申请认领', '认领物品',
            ]),
            ('system_stats', [
                '统计', '数据', '多少', '数量', '排行榜', '趋势', '热度',
                '最多的', '总共', '一共', '几个', '多少个', '成功了',
            ]),
            ('lost_prevention', [
                '防丢', '防止丢失', '怎么不丢', '保管', '看好', '注意',
                '容易丢', '丢了怎么办', '丢了东西', '丢失', '不见了',
            ]),
            ('category_help', [
                '类别', '分类', '怎么选', '属于什么', '什么类型', '选什么',
                '不知道分类', '不知道类别', '应该选', '归哪类',
            ]),
            ('location_help', [
                '哪里', '什么地方', '高发', '容易丢', '哪个地方', '地点',
                '食堂', '图书馆', '教学楼', '体育馆', '操场',
            ]),
            ('credit_info', [
                '积分', '信用分', '分数', '多少分', '加分', '减分', '扣分',
                '信用', '等级', '规则', '怎么获得',
            ]),
            ('contact_admin', [
                '管理员', '联系', '反馈', '投诉', '建议', '问题', 'bug',
                '报错', '异常', '人工', '客服',
            ]),
            ('help_list', [
                '帮助', '功能', '能做什么', '可以做什么', '有什么功能',
                '你会什么', '你能做什么', '使用指南', '怎么用', '如何使用',
                '命令', '指令', '菜单',
            ]),
        ]

        # 遍历匹配
        for intent, patterns in intent_patterns:
            for pattern in patterns:
                if pattern in text:
                    return intent, pattern

        return 'unknown', None

    def _build_greeting_reply(self, ctx: Dict[str, Any],
                              matched: Optional[str]) -> str:
        """生成问候语回复"""
        hour = datetime.now().hour
        if 5 <= hour < 9:
            time_greeting = '早上好'
        elif 9 <= hour < 12:
            time_greeting = '上午好'
        elif 12 <= hour < 14:
            time_greeting = '中午好'
        elif 14 <= hour < 18:
            time_greeting = '下午好'
        else:
            time_greeting = '晚上好'

        is_logged_in = ctx.get('is_logged_in', False)

        if is_logged_in:
            user_name = ctx.get('real_name', '同学')
            reply = (
                f'{time_greeting}，{user_name}！\n\n'
                f'欢迎使用校园失物招领智能助手 \u2014\u2014 我在这里随时为您提供帮助！\n\n'
                f'您可以向我咨询以下内容：\n'
                f'  \u2022 查看我的失物/招领记录\n'
                f'  \u2022 发布物品指南\n'
                f'  \u2022 匹配与认领流程\n'
                f'  \u2022 系统统计数据\n'
                f'  \u2022 认领建议与保管建议\n\n'
                f'请告诉我您需要什么帮助？'
            )
        else:
            reply = (
                f'{time_greeting}！欢迎来到校园失物招领系统！\n\n'
                f'我是一个智能助手，可以帮您：\n'
                f'  \u2022 发布失物/招领信息\n'
                f'  \u2022 查找匹配的物品\n'
                f'  \u2022 了解认领流程\n'
                f'  \u2022 查询系统数据\n'
                f'  \u2022 获得认领建议\n\n'
                f'提示：登录后我可以查询您的个人记录哦~ 请问有什么可以帮您的？'
            )
        return reply

    def _build_my_items_reply(self, ctx: Dict[str, Any],
                              matched: Optional[str]) -> str:
        """生成"我的物品"查询回复"""
        is_logged_in = ctx.get('is_logged_in', False)

        if not is_logged_in:
            return (
                '您还没有登录呢 \u2014\u2014 登录后我可以帮您：\n\n'
                '  \u2022 查看您发布的所有失物记录\n'
                '  \u2022 查看您发布的所有招领记录\n'
                '  \u2022 了解您的物品匹配状态\n'
                '  \u2022 查看认领申请的进度\n\n'
                '请先登录系统，然后告诉我"我的物品"或"我的失物"，我就能为您查到啦！'
            )

        # 如果有外部传入的数据，可通过 ctx['item_stats'] 传入
        item_stats = ctx.get('item_stats', {})
        if item_stats:
            lost_count = item_stats.get('lost_count', 0)
            found_count = item_stats.get('found_count', 0)
            match_count = item_stats.get('match_count', 0)
            claim_count = item_stats.get('claim_count', 0)
            reply = (
                f'好的！以下是您目前的物品统计：\n\n'
                f'  \u2022 失物记录：{lost_count} 条\n'
                f'  \u2022 招领记录：{found_count} 条\n'
                f'  \u2022 匹配结果：{match_count} 条\n'
                f'  \u2022 认领申请：{claim_count} 条\n\n'
                f'您可以进入个人中心查看详细信息。需要我为您提供发布指南或认领流程吗？'
            )
        else:
            reply = (
                '好的！您可以在个人中心查看您的物品记录。\n\n'
                '  \u2022 失物发布记录\n'
                '  \u2022 招领发布记录\n'
                '  \u2022 匹配结果通知\n'
                '  \u2022 认领申请进度\n\n'
                '如果您还没有发布过物品，可以告诉我需要发布什么，我一步步教您操作！'
            )
        return reply

    def _build_publish_guide_reply(self, ctx: Dict[str, Any],
                                   matched: Optional[str]) -> str:
        """生成发布指南回复"""
        return (
            '发布物品信息非常简单，跟着我一步步来：\n\n'
            '\u2460 点击页面上的"发布失物"或"发布招领"按钮\n\n'
            '\u2461 填写物品信息：\n'
            '    - 物品名称（必填）：如"黑色双肩背包"\n'
            '    - 物品类别（必填）：选择最符合的类别\n'
            '    - 物品描述：颜色、品牌、特征等，越详细越好\n'
            '    - 丢失/拾取时间（必填）：选择时间\n'
            '    - 地点（必填）：选择或输入地点\n'
            '    - 上传图片：展示物品外观（选填但推荐）\n\n'
            '\u2462 确认信息无误后提交，系统会自动生成匹配推荐\n\n'
            '小贴士：描述越详细、图片越清晰，匹配成功率越高哦！\n'
            '需要我帮您生成一段智能描述吗？直接告诉我物品名称就行！'
        )

    def _build_match_info_reply(self, ctx: Dict[str, Any],
                                matched: Optional[str]) -> str:
        """生成匹配信息回复"""
        return (
            '系统的智能匹配功能可以帮助您快速找到匹配的物品！\n\n'
            '匹配原理：\n'
            '  \u2022 物品名称和描述的文本相似度\n'
            '  \u2022 物品类别的匹配程度\n'
            '  \u2022 丢失时间和拾取时间的接近程度\n'
            '  \u2022 地点的距离远近\n'
            '  \u2022 上传图片的视觉相似度\n\n'
            '使用方式：\n'
            '  \u2022 发布失物或招领后，系统会自动执行匹配\n'
            '  \u2022 在物品详情页可以查看匹配结果列表\n'
            '  \u2022 匹配度高于80%为"高匹配"，60%-80%为"中匹配"\n'
            '  \u2022 可以主动对匹配结果进行确认或反馈\n\n'
            '提示：发布信息时填写越详细，匹配准确度就越高哦！'
        )

    def _build_claim_info_reply(self, ctx: Dict[str, Any],
                                matched: Optional[str]) -> str:
        """生成认领流程回复"""
        return (
            '认领物品的流程如下：\n\n'
            '\u2460 找到您丢失的物品后，点击物品详情页的"申请认领"按钮\n\n'
            '\u2461 填写认领说明：\n'
            '    - 描述您的物品特征（品牌、颜色、特殊标记等）\n'
            '    - 上传证明图片（选填，如购买凭证、物品照片）\n\n'
            '\u2462 提交申请后，拾取者或管理员会审核您的认领请求\n\n'
            '\u2463 审核通过后，双方约定时间地点完成认领\n\n'
            '认领小贴士：\n'
            '  \u2022 提供的描述越详细，审核通过率越高\n'
            '  \u2022 电子设备建议提供IMEI号或序列号\n'
            '  \u2022 证件类请提供姓名和证件号后四位\n\n'
            '对于不同类型的物品，我还可以提供具体的认领建议，'
            '告诉我物品类型（如"手机""身份证"等）即可！'
        )

    def _build_system_stats_reply(self, ctx: Dict[str, Any],
                                  matched: Optional[str]) -> str:
        """生成系统统计数据回复"""
        stats = ctx.get('system_stats', {})
        if stats:
            total_lost = stats.get('total_lost', 0)
            total_found = stats.get('total_found', 0)
            matched_count = stats.get('matched', 0)
            pending_lost = stats.get('pending_lost', 0)
            pending_found = stats.get('pending_found', 0)
            today_lost = stats.get('today_lost', 0)
            today_found = stats.get('today_found', 0)

            reply = (
                f'以下是系统的当前统计数据：\n\n'
                f'  \u2022 总失物登记：{total_lost} 件\n'
                f'  \u2022 总招领登记：{total_found} 件\n'
                f'  \u2022 成功匹配：{matched_count} 次\n'
                f'  \u2022 待处理失物：{pending_lost} 件\n'
                f'  \u2022 待处理招领：{pending_found} 件\n'
                f'  \u2022 今日新增失物：{today_lost} 件\n'
                f'  \u2022 今日新增招领：{today_found} 件\n\n'
                f'数据持续更新中\u2014\u2014如果您想了解更详细的分析，'
                f'我还可以为您分析丢失趋势、高发地点等信息，需要吗？'
            )
        else:
            reply = (
                '系统汇聚了全校师生发布的失物和招领数据。\n\n'
                '我可以为您提供以下统计信息：\n'
                '  \u2022 失物和招领的总量统计\n'
                '  \u2022 成功匹配的次数\n'
                '  \u2022 今日新增情况\n'
                '  \u2022 物品类别分布\n'
                '  \u2022 地点热度排行\n\n'
                '请先通过数据接口传入统计信息，我就能为您详细解读啦！'
            )
        return reply

    def _build_help_list_reply(self) -> str:
        """生成功能列表回复"""
        return (
            '我可以帮您做这些事情：\n\n'
            '\u2460 查询物品记录\n'
            '   告诉我"我的物品""我的失物"，查看您的发布记录\n\n'
            '\u2461 发布指南\n'
            '   告诉我"怎么发布""登记指南"，获取发布详细步骤\n\n'
            '\u2462 匹配说明\n'
            '   告诉我"匹配""找到"，了解系统如何帮您匹配合适的物品\n\n'
            '\u2463 认领流程\n'
            '   告诉我"怎么认领""认领流程"，获取完整的认领指引\n\n'
            '\u2464 系统数据\n'
            '   告诉我"统计""数据"，查看系统运营概况\n\n'
            '\u2465 智能描述生成\n'
            '   提供物品名称和特征，我帮您自动生成专业的物品描述\n\n'
            '\u2466 认领/保管建议\n'
            '   告诉我具体物品类型，我为您提供专属建议\n\n'
            '直接输入您的问题，我来为您解答！'
        )

    def _build_lost_prevention_reply(self, ctx: Dict[str, Any],
                                      matched: Optional[str] = None) -> str:
        """生成防丢建议回复"""
        return (
            f'🔐 防丢小贴士，帮您守护随身物品：\n\n'
            f'  📌 养成习惯\n'
            f'    \u2022 离开座位前检查"手机、钱包、钥匙、耳机"四件套\n'
            f'    \u2022 书包侧袋不放贵重物品（最容易滑落）\n'
            f'    \u2022 图书馆/自习室离开座位时带走全部物品\n\n'
            f'  📌 场所注意\n'
            f'    \u2022 食堂：手机不要放桌上占座，最易遗忘\n'
            f'    \u2022 体育馆：运动前将物品集中放在储物柜\n'
            f'    \u2022 操场：长椅上不要放包，转身就可能不见\n'
            f'    \u2022 教室：课后检查抽屉和座位夹缝\n\n'
            f'  📌 善用标签\n'
            f'    \u2022 在背包、水杯、笔记本上贴上姓名和联系方式\n'
            f'    \u2022 校园卡可写备用联系电话在卡片背面\n\n'
            f'如果不慎丢失，记得第一时间来系统发布寻物信息哦！'
        )

    def _build_category_help_reply(self, ctx: Dict[str, Any],
                                   matched: Optional[str] = None) -> str:
        """生成物品类别帮助回复"""
        return (
            f'📂 常见物品类别对照表，帮您快速选择：\n\n'
            f'  📱 电子数码\n'
            f'    手机、耳机、充电器、U盘、平板、笔记本电脑、充电宝、智能手表\n\n'
            f'  👜 箱包服饰\n'
            f'    背包、钱包、钥匙串、伞、帽子、围巾、手套、外套\n\n'
            f'  📚 学习用品\n'
            f'    笔记本、教材、笔袋、文具、文件夹、计算器、学生证/校园卡\n\n'
            f'  🏷️ 证件卡片\n'
            f'    身份证、校园卡、银行卡、公交卡、借书证、饭卡\n\n'
            f'  🎾 运动健身\n'
            f'    运动手环、球拍、水杯、护具、运动鞋\n\n'
            f'  💎 首饰配饰\n'
            f'    手表、戒指、项链、手链、眼镜、隐形眼镜盒\n\n'
            f'如果还是不确定，就选最接近的类别，在描述里写清楚物品特征即可！'
        )

    def _build_location_help_reply(self, ctx: Dict[str, Any],
                                   matched: Optional[str] = None) -> str:
        """生成高发地点帮助回复"""
        return (
            f'📍 校园物品丢失高发地点提醒：\n\n'
            f'  ⚠️ 高风险区域\n'
            f'    \u2022 食堂：高峰期占座时手机、钱包最易遗忘\n'
            f'    \u2022 图书馆/自习室：离开座位去洗手间的几分钟内\n'
            f'    \u2022 体育馆/操场：运动时脱下的外套和背包\n'
            f'    \u2022 教学楼教室：课后、换教室时遗留物品\n\n'
            f'  ⚡ 高风险时段\n'
            f'    \u2022 午饭时间（11:30-13:00）\n'
            f'    \u2022 晚饭时间（17:30-19:00）\n'
            f'    \u2022 晚自习结束（21:00-22:00）\n\n'
            f'  💡 建议\n'
            f'    发布物品时尽量写清楚具体位置，如"图书馆3楼靠窗座位"，\n'
            f'    能大大提高被找到的概率！'
        )

    def _build_credit_info_reply(self, ctx: Dict[str, Any],
                                 matched: Optional[str] = None) -> str:
        """生成积分规则回复"""
        return (
            f'⭐ 校园信用分规则说明：\n\n'
            f'  📈 加分项\n'
            f'    \u2022 成功发布招领信息：+5分\n'
            f'    \u2022 帮助找回失物（审核通过）：+10分\n'
            f'    \u2022 被他人好评：+2分/次\n'
            f'    \u2022 连续7天登录：+3分\n\n'
            f'  📉 扣分项\n'
            f'    \u2022 发布虚假信息：-20分\n'
            f'    \u2022 恶意冒领：-30分\n'
            f'    \u2022 无故取消认领：-5分\n'
            f'    \u2022 被举报核实：-15分\n\n'
            f'  🏆 信用等级\n'
            f'    \u2022 优秀（90分以上）：优先推荐匹配\n'
            f'    \u2022 良好（70-89分）：正常功能使用\n'
            f'    \u2022 一般（50-69分）：部分功能受限\n'
            f'    \u2022 较差（50分以下）：需审核后发布\n\n'
            f'保持良好的信用记录，不仅帮助自己也帮助他人！'
        )

    def _build_contact_admin_reply(self, ctx: Dict[str, Any],
                                   matched: Optional[str] = None) -> str:
        """生成联系管理员回复"""
        return (
            f'📞 如需联系管理员或提交反馈，您可以通过以下方式：\n\n'
            f'  1️⃣ 在【个人中心】页面点击"帮助与反馈"提交您的问题\n'
            f'  2️⃣ 在社区发帖@管理员说明情况\n'
            f'  3️⃣ 发送邮件至 campus-lost-found@example.edu\n\n'
            f'  💡 常见问题自助解决\n'
            f'    \u2022 忘记密码：在登录页面点击"忘记密码"重置\n'
            f'    \u2022 发布被驳回：检查描述是否清晰，照片是否合规\n'
            f'    \u2022 无法认领：确认物品仍在招领状态，且未被他人认领\n'
            f'    \u2022 匹配不准确：完善物品描述和特征标签\n\n'
            f'管理员会在1-2个工作日内回复您的反馈，请耐心等待！'
        )

    def _build_unknown_reply(self, text: str) -> str:
        """生成未识别意图的通用回复"""
        return (
            f'感谢您的提问！\n\n'
            f'我暂时无法完全理解您的问题，但您可以试试以下方式：\n\n'
            f'  \u2022 "发布指南" \u2014\u2014 了解如何发布失物/招领\n'
            f'  \u2022 "如何认领" \u2014\u2014 了解认领流程\n'
            f'  \u2022 "智能匹配" \u2014\u2014 了解匹配功能\n'
            f'  \u2022 "系统数据" \u2014\u2014 查看系统统计\n'
            f'  \u2022 "防丢建议" \u2014\u2014 防止物品丢失的技巧\n'
            f'  \u2022 "积分规则" \u2014\u2014 了解信用分机制\n'
            f'  \u2022 "帮助" \u2014\u2014 查看完整功能列表\n\n'
            f'或者直接描述您的具体问题，我会尽力帮您解答！'
        )

    # --------------------------------------------------------------------------
    #  2. 智能描述生成器
    # --------------------------------------------------------------------------
    def generate_smart_description(self, item_name: str,
                                   category: Optional[str] = None,
                                   brand: Optional[str] = None,
                                   color: Optional[str] = None,
                                   features: Optional[List[str]] = None) -> str:
        """
        根据物品名称、类别、品牌、颜色、特征等自动生成完整的智能描述。

        :param item_name: 物品名称（必填）
        :param category: 物品类别（选填）
        :param brand: 品牌（选填）
        :param color: 颜色（选填）
        :param features: 特征列表（选填），如 ['有划痕', '带挂件']
        :return: 生成的完整描述文本
        """
        if not item_name:
            return '请提供物品名称以生成描述。'

        parts: List[str] = []
        parts.append(f'这是一件{item_name}')

        # 加入品牌信息
        if brand:
            parts.append(f'品牌为{brand}')

        # 加入颜色描述
        color_desc = {
            '红色': '颜色为红色，非常显眼',
            '蓝色': '颜色为蓝色，清新亮丽',
            '绿色': '颜色为绿色，清新自然',
            '黄色': '颜色为黄色，活泼醒目',
            '黑色': '颜色为黑色，经典大方',
            '白色': '颜色为白色，干净整洁',
            '灰色': '颜色为灰色，低调内敛',
            '棕色': '颜色为棕色，沉稳复古',
            '紫色': '颜色为紫色，优雅别致',
            '粉色': '颜色为粉色，甜美可爱',
            '银色': '颜色为银色，时尚简约',
            '金色': '颜色为金色，华丽精致',
        }
        if color:
            if color in color_desc:
                parts.append(color_desc[color])
            else:
                parts.append(f'颜色为{color}')

        # 加入类别特征
        category_features = {
            '电子设备': '属于电子设备类物品，请小心轻放',
            '手机': '属于手机类设备，请注意保护屏幕',
            '笔记本电脑': '属于笔记本电脑，内含重要数据请妥善保管',
            '证件卡片': '属于重要证件类物品，请尽快联系失主',
            '身份证': '为个人重要身份证件，涉及信息安全',
            '学生证': '为校园学生身份凭证，关联校内各项服务',
            '箱包': '属于箱包类物品，请检查所有口袋',
            '背包': '为背包类物品，带有肩带和拉链',
            '书籍文具': '属于书籍文具类物品',
            '钥匙': '为钥匙类物品，可能关联多个锁具',
            '服饰': '属于服饰类物品',
        }
        if category and category in category_features:
            parts.append(category_features[category])
        elif category:
            parts.append(f'归类为"{category}"')

        # 加入额外特征
        if features:
            feature_text = '、'.join(features)
            parts.append(f'物品特征：{feature_text}')

        # 通用描述补充
        general_tips = [
            '外观整体完好',
            '功能使用正常',
            '无明显损坏痕迹',
            '日常使用频率较高',
            '建议尽快寻找失主',
        ]
        parts.append(random.choice(general_tips))

        # 拼接完整描述
        description = '，'.join(parts) + '。'

        # 添加查找提示
        if category in ('证件卡片', '身份证', '学生证'):
            description += '如发现证件，建议第一时间交至失物招领处或联系相关院系。'
        elif category in ('电子设备', '手机', '笔记本电脑'):
            description += '如为电子设备，建议尝试开机查看是否有失主联系信息。'
        else:
            description += '请在本系统中发布信息以便失主查找。'

        return description

    # --------------------------------------------------------------------------
    #  3. 丢失趋势分析
    # --------------------------------------------------------------------------
    def analyze_lost_trends(self, items_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析丢失趋势。

        :param items_data: 失物数据列表，每项至少包含 lost_time（丢失时间）和
                           location（地点）、category（类别）字段
        :return: 包含高发时段、高发地点、高频类别的分析结果
        """
        if not items_data:
            return {
                'time_slots': [],
                'top_locations': [],
                'top_categories': [],
                'summary': '暂无足够数据进行分析。'
            }

        # ---- 时段分析 ----
        slot_counts: Dict[str, int] = {slot['name']: 0 for slot in self._time_slots}
        unknown_slot = 0

        for item in items_data:
            lost_time = item.get('lost_time')
            if not lost_time:
                unknown_slot += 1
                continue

            # 解析时间
            hour = self._parse_hour(lost_time)
            if hour is None:
                unknown_slot += 1
                continue

            matched = False
            for slot in self._time_slots:
                if slot['start'] <= hour < slot['end']:
                    slot_counts[slot['name']] += 1
                    matched = True
                    break
            if not matched:
                unknown_slot += 1

        # 按计数排序
        sorted_slots = sorted(
            slot_counts.items(), key=lambda x: x[1], reverse=True
        )
        time_slots_result = [
            {'slot': name, 'count': count}
            for name, count in sorted_slots if count > 0
        ]

        # ---- 地点分析 ----
        location_counts: Dict[str, int] = {}
        for item in items_data:
            loc = item.get('location', '未知') or '未知'
            location_counts[loc] = location_counts.get(loc, 0) + 1

        sorted_locations = sorted(
            location_counts.items(), key=lambda x: x[1], reverse=True
        )
        top_locations_result = [
            {'location': loc, 'count': count}
            for loc, count in sorted_locations[:10]
        ]

        # ---- 类别分析 ----
        category_counts: Dict[str, int] = {}
        for item in items_data:
            cat = item.get('category', '未分类') or '未分类'
            category_counts[cat] = category_counts.get(cat, 0) + 1

        sorted_categories = sorted(
            category_counts.items(), key=lambda x: x[1], reverse=True
        )
        top_categories_result = [
            {'category': cat, 'count': count}
            for cat, count in sorted_categories[:10]
        ]

        # ---- 生成总结 ----
        total = len(items_data)
        summary_parts: List[str] = [f'共分析 {total} 条失物记录。']

        if time_slots_result:
            top_slot = time_slots_result[0]
            summary_parts.append(
                f'丢失高发时段为{top_slot["slot"]}（共 {top_slot["count"]} 件），'
                f'占总数 {top_slot["count"] / total * 100:.1f}%。'
            )
        if top_locations_result:
            top_loc = top_locations_result[0]
            summary_parts.append(
                f'丢失最多的地点是{top_loc["location"]}（共 {top_loc["count"]} 件）。'
            )
        if top_categories_result:
            top_cat = top_categories_result[0]
            summary_parts.append(
                f'最常丢失的物品类别是"{top_cat["category"]}"（共 {top_cat["count"]} 件）。'
            )

        return {
            'time_slots': time_slots_result,
            'top_locations': top_locations_result,
            'top_categories': top_categories_result,
            'summary': ' '.join(summary_parts),
            'total_items': total,
        }

    def _parse_hour(self, time_str: Any) -> Optional[int]:
        """从时间字符串中提取小时数"""
        if isinstance(time_str, datetime):
            return time_str.hour
        if not isinstance(time_str, str):
            return None

        # 尝试多种时间格式
        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%dT%H:%M:%S',
                    '%Y-%m-%d']:
            try:
                dt = datetime.strptime(time_str, fmt)
                return dt.hour
            except ValueError:
                continue

        # 正则匹配时间部分
        match = re.search(r'(\d{1,2}):', time_str)
        if match:
            return int(match.group(1))
        return None

    # --------------------------------------------------------------------------
    #  4. 认领建议
    # --------------------------------------------------------------------------
    def get_claim_advice(self, item_type: str,
                         item_category: Optional[str] = None) -> Dict[str, Any]:
        """
        根据物品类型和类别获取认领建议。

        :param item_type: 拾取者视角的物品类型描述（如 手机、身份证、背包）
        :param item_category: 系统分类（如 电子设备、证件卡片），选填
        :return: 包含认领建议、必要证明、小贴士的字典
        """
        # 尝试直接匹配子类别
        if item_type in self._claim_advice_rules:
            return self._claim_advice_rules[item_type]

        # 尝试匹配父类别
        if item_category in self._claim_advice_rules:
            return self._claim_advice_rules[item_category]

        # 尝试通过关键词匹配
        for cat_key, keywords in self._category_keywords.items():
            if item_type in keywords or item_type in cat_key:
                if cat_key in self._claim_advice_rules:
                    return self._claim_advice_rules[cat_key]

        # 返回通用建议
        return self._claim_advice_rules['其他']

    # --------------------------------------------------------------------------
    #  5. 匹配理由生成
    # --------------------------------------------------------------------------
    def generate_match_reason(self, lost_item: Dict[str, Any],
                              found_item: Dict[str, Any],
                              scores: Dict[str, float]) -> str:
        """
        基于各项评分生成人类可读的自然语言匹配理由。

        :param lost_item: 失物信息字典（含 name, description, location 等）
        :param found_item: 招领信息字典（含 name, description, location 等）
        :param scores: 评分字典，包含 text, time, location, category, image 等维度得分
        :return: 自然语言匹配理由文本
        """
        reasons: List[str] = []

        # 总分
        total_score = sum(scores.values()) / len(scores) if scores else 0

        # ---- 文本相似度 ----
        text_score = scores.get('text', 0)
        if text_score >= 0.8:
            reasons.append(f'物品名称和描述高度一致（文本匹配度 {text_score:.0%}）')
        elif text_score >= 0.6:
            reasons.append(f'物品描述较为相似（文本匹配度 {text_score:.0%}）')
        elif text_score >= 0.4:
            reasons.append(f'物品描述有一定相似之处（文本匹配度 {text_score:.0%}）')

        # ---- 时间接近度 ----
        time_score = scores.get('time', 0)
        if time_score >= 0.8:
            reasons.append('丢失时间和拾取时间非常接近')
        elif time_score >= 0.6:
            reasons.append('时间较为接近')
        elif time_score < 0.3:
            reasons.append('时间上存在一定差距')

        # ---- 地点接近度 ----
        loc_score = scores.get('location', 0)
        lost_loc = lost_item.get('location', '')
        found_loc = found_item.get('location', '')
        if loc_score >= 0.9:
            reasons.append(f'地点完全一致（均在{lost_loc}）')
        elif loc_score >= 0.6:
            reasons.append(f'地点较为接近（{lost_loc}附近）')
        elif loc_score >= 0.4:
            reasons.append(f'地点有一定关联（{lost_loc}与{found_loc}距离不远）')
        elif loc_score > 0:
            reasons.append(f'地点不同（失物在{lost_loc}，拾取在{found_loc}）')

        # ---- 类别匹配 ----
        cat_score = scores.get('category', 0)
        lost_cat = lost_item.get('category', '')
        found_cat = found_item.get('category', '')
        if cat_score >= 0.9:
            reasons.append(f'物品类别完全一致（均为{lost_cat}）')
        elif cat_score >= 0.6:
            reasons.append(f'物品类别属于同一大类（{lost_cat} / {found_cat}）')
        elif cat_score > 0:
            reasons.append(f'物品类别不同（失物为{lost_cat}，拾取为{found_cat}）')

        # ---- 图像相似度 ----
        img_score = scores.get('image', 0)
        if img_score >= 0.8:
            reasons.append('上传图片非常相似')
        elif img_score >= 0.6:
            reasons.append('上传图片较为相似')
        elif img_score >= 0:
            pass  # 不提及低图像相似度

        # ---- 综合判断 ----
        lost_name = lost_item.get('name', '该物品')
        found_name = found_item.get('name', '某物品')

        if total_score >= 0.8:
            opening = f'【高匹配】{lost_name}与{found_name}有很大可能是同一件物品！'
        elif total_score >= 0.6:
            opening = f'【中匹配】{lost_name}与{found_name}有一定可能是同一件物品。'
        elif total_score >= 0.4:
            opening = f'【低匹配】{lost_name}与{found_name}可能相关，建议进一步核实。'
        else:
            opening = f'{lost_name}与{found_name}的匹配程度较低。'

        if not reasons:
            reasons.append('基于系统综合特征进行分析')

        return opening + '\n' + '原因：' + '；'.join(reasons) + '。'

    # --------------------------------------------------------------------------
    #  6. 推荐搜索关键词
    # --------------------------------------------------------------------------
    def suggest_search_keywords(self, description: str) -> List[str]:
        """
        从物品描述中提取并推荐搜索关键词。

        :param description: 物品描述文本
        :return: 推荐的关键词列表
        """
        if not description:
            return []

        keywords: List[str] = []
        seen: set = set()

        # 提取颜色词
        colors = ['红色', '蓝色', '绿色', '黄色', '黑色', '白色', '灰色',
                  '棕色', '紫色', '橙色', '粉色', '银色', '金色', '米色', '卡其色']
        for color in colors:
            if color in description and color not in seen:
                keywords.append(color)
                seen.add(color)

        # 提取品牌词
        brands = ['苹果', '华为', '小米', '三星', 'OPPO', 'vivo', '荣耀',
                  '联想', '戴尔', '惠普', '华硕', '索尼', '佳能', '耐克',
                  '阿迪达斯', '新百伦', '李宁', '安踏']
        for brand in brands:
            if brand in description and brand not in seen:
                keywords.append(brand)
                seen.add(brand)

        # 提取类别关键词
        for cat_keywords in self._category_keywords.values():
            for kw in cat_keywords:
                if kw in description and kw not in seen:
                    keywords.append(kw)
                    seen.add(kw)

        # 提取其他有意义的双字词
        words = re.findall(r'[\u4e00-\u9fa5]{2,}', description)
        meaningful_words = [
            '全新', '二手', '损坏', '破损', '完好', '黑色', '白色', '重要',
            '紧急', '普通', '大号', '小号', '中型', '运动', '休闲', '商务'
        ]
        for w in words:
            if w in meaningful_words and w not in seen:
                keywords.append(w)
                seen.add(w)

        # 去重后返回（限15个）
        return list(dict.fromkeys(keywords))[:15]

    # --------------------------------------------------------------------------
    #  7. 保管方式推荐
    # --------------------------------------------------------------------------
    def recommend_storage_method(self, item_type: str,
                                 item_category: Optional[str] = None) -> Dict[str, Any]:
        """
        根据物品类型和类别推荐保管方式。

        :param item_type: 物品类型描述（如 手机、背包），或物品具体名称
        :param item_category: 系统分类（如 电子设备、箱包），选填
        :return: 包含保管建议列表的字典
        """
        # 优先使用传入的分类
        if item_category and item_category in self._storage_rules:
            methods = self._storage_rules[item_category]
        else:
            # 尝试根据物品类型关键词匹配分类
            matched_category = None
            for cat_key, keywords in self._category_keywords.items():
                if item_type in keywords or item_type in cat_key:
                    matched_category = cat_key
                    break

            if matched_category and matched_category in self._storage_rules:
                methods = self._storage_rules[matched_category]
            else:
                # 使用通用保管建议
                methods = self._storage_rules['其他']

        return {
            'item_type': item_type,
            'category': item_category or matched_category or '其他',
            'methods': methods,
            'general_tips': [
                '请在物品上标注拾取日期和地点',
                '定期检查保管物品的状态',
                '超过保管期限的物品按规定处理',
                '建议拍照记录保管时的物品状态',
            ]
        }

    # --------------------------------------------------------------------------
    #  8. 通知模板
    # --------------------------------------------------------------------------
    def get_notification_template(self, notif_type: str,
                                  **kwargs: Any) -> Dict[str, str]:
        """
        获取指定类型的通知模板，并填充参数。

        支持的通知类型：
          - match_found: 匹配成功通知
          - match_updated: 匹配状态更新通知
          - claim_received: 收到认领申请通知
          - claim_approved: 认领通过通知
          - claim_rejected: 认领未通过通知
          - item_expiring: 物品即将过期提醒
          - credit_changed: 积分变动通知
          - system_announcement: 系统公告

        :param notif_type: 通知类型名称
        :param kwargs: 模板参数，如 username, item_name, location 等
        :return: 包含 title 和 content 的字典
        """
        # 标题模板
        title_templates: Dict[str, str] = {
            'match_found': '匹配成功通知',
            'match_updated': '匹配状态更新',
            'claim_received': '认领申请提醒',
            'claim_approved': '认领申请通过',
            'claim_rejected': '认领申请未通过',
            'item_expiring': '物品保管期限提醒',
            'credit_changed': '积分变动通知',
            'system_announcement': '系统公告',
        }

        # 获取内容模板
        content_template = self._notification_templates.get(notif_type)
        if not content_template:
            return {
                'title': '系统通知',
                'content': kwargs.get('content', '您有一条新的系统通知。')
            }

        # 填充参数
        try:
            title = title_templates.get(notif_type, '系统通知')
            content = content_template.format(**kwargs)
        except KeyError as e:
            # 如果缺少必要的模板参数，给出提示
            content = (
                f'【{title_templates.get(notif_type, "系统通知")}】'
                f'缺少必要参数：{e}'
            )

        return {
            'title': title,
            'content': content,
        }