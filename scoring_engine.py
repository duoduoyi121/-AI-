from ai_service import AIService

class ScoringEngine:
    def __init__(self):
        self.weights = {
            'image_similarity': 0.4,
            'text_similarity': 0.3,
            'time_proximity': 0.15,
            'location_proximity': 0.15
        }
        self.ai_service = AIService()
    
    def calculate_score(self, lost_item, found_item):
        score = 0
        
        # 计算图像相似度得分
        image_score = self._calculate_image_similarity(lost_item, found_item)
        score += image_score * self.weights['image_similarity']
        
        # 计算文本描述相似度得分
        text_score = self._calculate_text_similarity(lost_item, found_item)
        score += text_score * self.weights['text_similarity']
        
        # 计算时间接近度得分
        time_score = self._calculate_time_proximity(lost_item, found_item)
        score += time_score * self.weights['time_proximity']
        
        # 计算地点接近度得分
        location_score = self._calculate_location_proximity(lost_item, found_item)
        score += location_score * self.weights['location_proximity']
        
        return round(score, 2)
    
    def _calculate_image_similarity(self, lost_item, found_item):
        # 使用AI服务计算图像相似度
        if not lost_item.get('image') or not found_item.get('image'):
            return 0.5
        
        return self.ai_service.calculate_image_similarity(
            lost_item['image'], 
            found_item['image']
        )
    
    def _calculate_text_similarity(self, lost_item, found_item):
        # 使用AI服务计算文本相似度
        lost_desc = lost_item.get('description', '').lower()
        found_desc = found_item.get('description', '').lower()
        
        if not lost_desc or not found_desc:
            return 0.5
        
        return self.ai_service.calculate_text_similarity(
            lost_desc, 
            found_desc
        )
    
    def _calculate_time_proximity(self, lost_item, found_item):
        # 模拟时间接近度计算
        if not lost_item.get('time') or not found_item.get('time'):
            return 0.5
        
        # 简单模拟：时间差越小，得分越高
        # 假设时间格式为YYYY-MM-DD HH:MM
        import datetime
        lost_time = datetime.datetime.strptime(lost_item['time'], '%Y-%m-%d %H:%M')
        found_time = datetime.datetime.strptime(found_item['time'], '%Y-%m-%d %H:%M')
        
        time_diff = abs((lost_time - found_time).total_seconds() / 3600)  # 小时
        
        # 24小时内相似度为1，超过72小时相似度为0
        if time_diff <= 24:
            return 1.0
        elif time_diff >= 72:
            return 0.0
        else:
            return 1 - (time_diff - 24) / 48
    
    def _calculate_location_proximity(self, lost_item, found_item):
        # 模拟地点接近度计算
        if not lost_item.get('location') or not found_item.get('location'):
            return 0.5
        
        # 简单模拟：地点名称相同则相似度为1，否则为0.5
        if lost_item['location'] == found_item['location']:
            return 1.0
        else:
            # 检查是否在同一建筑物或区域
            lost_loc_parts = lost_item['location'].split()
            found_loc_parts = found_item['location'].split()
            for part in lost_loc_parts:
                if part in found_loc_parts:
                    return 0.7
            return 0.3