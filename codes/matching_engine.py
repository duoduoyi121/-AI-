import numpy as np
from datetime import datetime
from ai_service import AIService
import re

class AdvancedMatchingEngine:
    def __init__(self):
        self.ai_service = AIService()
        self.weights = {
            'image_similarity': 0.35,
            'text_similarity': 0.30,
            'time_proximity': 0.15,
            'location_proximity': 0.15,
            'category_match': 0.05
        }
        self.match_thresholds = {
            'high': 0.8,
            'medium': 0.6,
            'low': 0.4
        }
        
        # 地点相似度映射
        self.location_similarity = {
            '图书馆': {'图书馆': 1.0, '教学楼': 0.3, '食堂': 0.2, '宿舍区': 0.2, '操场': 0.1},
            '教学楼': {'图书馆': 0.3, '教学楼': 1.0, '食堂': 0.4, '宿舍区': 0.3, '操场': 0.2},
            '食堂': {'图书馆': 0.2, '教学楼': 0.4, '食堂': 1.0, '宿舍区': 0.5, '操场': 0.3},
            '宿舍区': {'图书馆': 0.2, '教学楼': 0.3, '食堂': 0.5, '宿舍区': 1.0, '操场': 0.4},
            '操场': {'图书馆': 0.1, '教学楼': 0.2, '食堂': 0.3, '宿舍区': 0.4, '操场': 1.0},
            '体育馆': {'图书馆': 0.2, '教学楼': 0.3, '食堂': 0.3, '宿舍区': 0.4, '操场': 0.8},
            '校门口': {'图书馆': 0.2, '教学楼': 0.3, '食堂': 0.3, '宿舍区': 0.3, '操场': 0.2},
            '停车场': {'图书馆': 0.2, '教学楼': 0.3, '食堂': 0.3, '宿舍区': 0.4, '操场': 0.3}
        }
    
    def calculate_comprehensive_score(self, lost_item, found_item):
        """
        计算综合匹配得分
        :param lost_item: 失物信息字典
        :param found_item: 招领信息字典
        :return: 匹配得分和各维度得分详情
        """
        scores = {}
        
        # 图像相似度
        scores['image'] = self._calculate_image_similarity(lost_item, found_item)
        
        # 文本相似度
        scores['text'] = self._calculate_text_similarity(lost_item, found_item)
        
        # 时间接近度
        scores['time'] = self._calculate_time_proximity(lost_item, found_item)
        
        # 地点接近度
        scores['location'] = self._calculate_location_proximity(lost_item, found_item)
        
        # 类别匹配
        scores['category'] = self._calculate_category_match(lost_item, found_item)
        
        # 计算综合得分
        total_score = (
            scores['image'] * self.weights['image_similarity'] +
            scores['text'] * self.weights['text_similarity'] +
            scores['time'] * self.weights['time_proximity'] +
            scores['location'] * self.weights['location_proximity'] +
            scores['category'] * self.weights['category_match']
        )
        
        return round(min(1.0, total_score), 4), scores
    
    def _calculate_image_similarity(self, lost_item, found_item):
        """计算图像相似度"""
        lost_image = lost_item.get('images', '').split(',')[0] if lost_item.get('images') else None
        found_image = found_item.get('images', '').split(',')[0] if found_item.get('images') else None
        
        if not lost_image or not found_image:
            return 0.5
        
        try:
            return self.ai_service.calculate_image_similarity(lost_image, found_image)
        except:
            return 0.5
    
    def _calculate_text_similarity(self, lost_item, found_item):
        """计算文本相似度 - 使用多种算法综合"""
        lost_name = lost_item.get('name', '').lower()
        found_name = found_item.get('name', '').lower()
        lost_desc = lost_item.get('description', '').lower()
        found_desc = found_item.get('description', '').lower()
        
        if not lost_desc or not found_desc:
            return 0.3
        
        # 1. 名称相似度
        name_score = self._calculate_string_similarity(lost_name, found_name)
        
        # 2. 描述相似度
        desc_score = self._calculate_string_similarity(lost_desc, found_desc)
        
        # 3. 关键词匹配
        keyword_score = self._calculate_keyword_match(lost_desc, found_desc)
        
        # 4. 颜色匹配
        color_score = self._calculate_color_match(lost_desc, found_desc)
        
        # 综合文本相似度
        final_score = name_score * 0.3 + desc_score * 0.4 + keyword_score * 0.2 + color_score * 0.1
        
        return round(final_score, 4)
    
    def _calculate_string_similarity(self, str1, str2):
        """计算字符串相似度（编辑距离）"""
        if not str1 or not str2:
            return 0.0
        
        # 使用莱文斯坦距离
        m, n = len(str1), len(str2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if str1[i-1] == str2[j-1]:
                    dp[i][j] = dp[i-1][j-1]
                else:
                    dp[i][j] = min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1]) + 1
        
        max_len = max(m, n)
        similarity = 1 - dp[m][n] / max_len if max_len > 0 else 1.0
        return similarity
    
    def _calculate_keyword_match(self, text1, text2):
        """计算关键词匹配度"""
        # 提取关键词（去除停用词）
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        
        words1 = set(w for w in re.findall(r'\w+', text1) if w not in stop_words and len(w) > 1)
        words2 = set(w for w in re.findall(r'\w+', text2) if w not in stop_words and len(w) > 1)
        
        if not words1 or not words2:
            return 0.3
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) if union else 0.0
    
    def _calculate_color_match(self, text1, text2):
        """计算颜色匹配度"""
        colors = {'红色', '蓝色', '绿色', '黄色', '黑色', '白色', '紫色', '橙色', '粉色', '灰色', '棕色', '银色', '金色'}
        
        colors1 = set(c for c in colors if c in text1)
        colors2 = set(c for c in colors if c in text2)
        
        if not colors1 and not colors2:
            return 0.5  # 都没有提到颜色
        
        if colors1 and colors2:
            if colors1 & colors2:  # 有共同颜色
                return 1.0
            else:
                return 0.1  # 颜色冲突
        
        return 0.5  # 只有一个提到颜色
    
    def _calculate_time_proximity(self, lost_item, found_item):
        """计算时间接近度"""
        try:
            lost_time = self._parse_time(lost_item.get('lost_time') or lost_item.get('time'))
            found_time = self._parse_time(found_item.get('found_time') or found_item.get('time'))
            
            if not lost_time or not found_time:
                return 0.5
            
            time_diff = abs((lost_time - found_time).total_seconds() / 3600)  # 小时
            
            if time_diff <= 1:
                return 1.0
            elif time_diff <= 6:
                return 0.9
            elif time_diff <= 12:
                return 0.8
            elif time_diff <= 24:
                return 0.7
            elif time_diff <= 48:
                return 0.5
            elif time_diff <= 72:
                return 0.3
            else:
                return max(0, 0.2 - (time_diff - 72) / 200)
        except:
            return 0.5
    
    def _calculate_location_proximity(self, lost_item, found_item):
        """计算地点接近度"""
        lost_loc = lost_item.get('location', '')
        found_loc = found_item.get('location', '')
        
        if not lost_loc or not found_loc:
            return 0.5
        
        # 完全匹配
        if lost_loc == found_loc:
            return 1.0
        
        # 检查地点相似度映射
        for key, similarities in self.location_similarity.items():
            if key in lost_loc:
                for loc, score in similarities.items():
                    if loc in found_loc:
                        return score
        
        # 部分匹配
        lost_parts = set(re.findall(r'\w+', lost_loc))
        found_parts = set(re.findall(r'\w+', found_loc))
        
        common = lost_parts & found_parts
        if common:
            return 0.6
        
        return 0.2
    
    def _calculate_category_match(self, lost_item, found_item):
        """计算类别匹配度"""
        lost_category = lost_item.get('category', '')
        found_category = found_item.get('category', '')
        
        if not lost_category or not found_category:
            return 0.5
        
        if lost_category == found_category:
            return 1.0
        
        # 检查是否属于同一父类别
        parent_categories = {
            '电子设备': ['手机', '电脑', '耳机', '平板', '充电器'],
            '证件卡片': ['身份证', '学生证', '银行卡', '校园卡'],
            '箱包': ['背包', '手提包', '行李箱', '钱包'],
            '书籍文具': ['书籍', '文具', '笔记本', '教材'],
            '服饰': ['衣服', '鞋子', '帽子', '围巾'],
            '钥匙': ['钥匙', '钥匙串', '门禁卡']
        }
        
        for parent, children in parent_categories.items():
            lost_in = lost_category in children or lost_category == parent
            found_in = found_category in children or found_category == parent
            
            if lost_in and found_in:
                return 0.8
        
        return 0.3
    
    def _parse_time(self, time_str):
        """解析时间字符串"""
        if not time_str:
            return None
        
        formats = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d']
        for fmt in formats:
            try:
                return datetime.strptime(time_str, fmt)
            except:
                continue
        return None
    
    def get_match_level(self, score):
        """获取匹配等级"""
        if score >= self.match_thresholds['high']:
            return 'high'
        elif score >= self.match_thresholds['medium']:
            return 'medium'
        elif score >= self.match_thresholds['low']:
            return 'low'
        return 'none'
    
    def get_match_level_text(self, score):
        """获取匹配等级文本"""
        level = self.get_match_level(score)
        level_map = {
            'high': '高匹配',
            'medium': '中匹配',
            'low': '低匹配',
            'none': '不匹配'
        }
        return level_map.get(level, '未知')
    
    def batch_match(self, lost_item, found_items):
        """批量匹配"""
        results = []
        for found_item in found_items:
            score, details = self.calculate_comprehensive_score(lost_item, found_item)
            match_level = self.get_match_level(score)
            if match_level != 'none':
                results.append({
                    'found_item': found_item,
                    'score': score,
                    'match_level': match_level,
                    'match_level_text': self.get_match_level_text(score),
                    'details': details
                })
        
        results.sort(key=lambda x: x['score'], reverse=True)
        return results
    
    def get_top_matches(self, lost_item, found_items, top_n=5):
        """获取前N个最佳匹配"""
        matches = self.batch_match(lost_item, found_items)
        return matches[:top_n]
    
    def auto_match_all(self, lost_items, found_items):
        """自动匹配所有物品"""
        all_matches = []
        
        for lost_item in lost_items:
            matches = self.batch_match(lost_item, found_items)
            for match in matches:
                all_matches.append({
                    'lost_item': lost_item,
                    'found_item': match['found_item'],
                    'score': match['score'],
                    'match_level': match['match_level'],
                    'details': match['details']
                })
        
        # 按得分排序
        all_matches.sort(key=lambda x: x['score'], reverse=True)
        return all_matches
    
    def get_match_explanation(self, lost_item, found_item, score, details):
        """获取匹配解释"""
        explanations = []
        
        if details['text'] > 0.7:
            explanations.append("文本描述高度相似")
        elif details['text'] > 0.5:
            explanations.append("文本描述较为相似")
        
        if details['time'] > 0.7:
            explanations.append("时间非常接近")
        elif details['time'] > 0.5:
            explanations.append("时间较为接近")
        
        if details['location'] > 0.7:
            explanations.append("地点相同或非常接近")
        elif details['location'] > 0.5:
            explanations.append("地点较为接近")
        
        if details['category'] > 0.8:
            explanations.append("物品类别一致")
        
        if not explanations:
            explanations.append("基于综合特征匹配")
        
        return {
            'score': score,
            'level': self.get_match_level_text(score),
            'explanations': explanations,
            'details': details
        }
