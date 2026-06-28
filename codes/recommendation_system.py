from scoring_engine import ScoringEngine

class RecommendationSystem:
    def __init__(self):
        self.scoring_engine = ScoringEngine()
    
    def get_recommendations(self, lost_item, found_items):
        """
        获取失物的推荐招领物品列表
        :param lost_item: 失物信息
        :param found_items: 招领物品列表
        :return: 按得分排序的推荐列表
        """
        recommendations = []
        
        for found_item in found_items:
            score = self.scoring_engine.calculate_score(lost_item, found_item)
            recommendations.append({
                'found_item': found_item,
                'score': score
            })
        
        # 按得分降序排序
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        
        return recommendations
    
    def get_next_recommendation(self, lost_item, found_items, confirmed_items):
        """
        获取下一个推荐（排除已确认的物品）
        :param lost_item: 失物信息
        :param found_items: 招领物品列表
        :param confirmed_items: 已确认不是的物品ID列表
        :return: 下一个推荐的招领物品
        """
        # 过滤掉已确认的物品
        filtered_found_items = [item for item in found_items if item.get('id') not in confirmed_items]
        
        # 获取推荐列表
        recommendations = self.get_recommendations(lost_item, filtered_found_items)
        
        # 返回第一个推荐（得分最高的）
        return recommendations[0] if recommendations else None