class ConfirmationSystem:
    def __init__(self):
        self.confirmed_items = {}
    
    def confirm_item(self, lost_item_id, found_item_id, is_match):
        """
        确认失物与招领物品是否匹配
        :param lost_item_id: 失物ID
        :param found_item_id: 招领物品ID
        :param is_match: 是否匹配
        :return: 确认结果
        """
        if lost_item_id not in self.confirmed_items:
            self.confirmed_items[lost_item_id] = []
        
        if is_match:
            # 记录匹配成功
            return {
                'status': 'success',
                'message': '匹配成功！',
                'lost_item_id': lost_item_id,
                'found_item_id': found_item_id
            }
        else:
            # 记录不匹配的物品
            self.confirmed_items[lost_item_id].append(found_item_id)
            return {
                'status': 'continue',
                'message': '继续推荐下一个',
                'lost_item_id': lost_item_id,
                'found_item_id': found_item_id,
                'confirmed_items': self.confirmed_items[lost_item_id]
            }
    
    def get_confirmed_items(self, lost_item_id):
        """
        获取失物已确认不是的物品列表
        :param lost_item_id: 失物ID
        :return: 已确认不是的物品ID列表
        """
        return self.confirmed_items.get(lost_item_id, [])