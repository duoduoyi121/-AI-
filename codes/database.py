import sqlite3
import os
from datetime import datetime, timedelta
import json


class DatabaseManager:
    def __init__(self, db_path='match_system.db'):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """初始化数据库，创建所有表并插入初始数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # ========== 用户表 ==========
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                phone TEXT UNIQUE,
                student_id TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                real_name TEXT NOT NULL,
                avatar TEXT,
                role TEXT DEFAULT 'user',
                status TEXT DEFAULT 'active',
                credit_score INTEGER DEFAULT 100,
                notification_enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # ========== 失物表 ==========
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lost_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                sub_category TEXT,
                brand TEXT,
                description TEXT NOT NULL,
                lost_time TIMESTAMP NOT NULL,
                location TEXT NOT NULL,
                location_detail TEXT,
                latitude REAL,
                longitude REAL,
                images TEXT,
                expected_reward REAL,
                urgency_level TEXT DEFAULT 'normal',
                status TEXT DEFAULT 'pending',
                match_count INTEGER DEFAULT 0,
                view_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # ========== 招领表 ==========
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS found_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                sub_category TEXT,
                description TEXT NOT NULL,
                found_time TIMESTAMP NOT NULL,
                location TEXT NOT NULL,
                location_detail TEXT,
                latitude REAL,
                longitude REAL,
                images TEXT,
                storage_method TEXT NOT NULL,
                contact_methods TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                match_count INTEGER DEFAULT 0,
                view_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # ========== 匹配表 ==========
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lost_item_id INTEGER,
                found_item_id INTEGER,
                score REAL NOT NULL,
                image_score REAL,
                text_score REAL,
                time_score REAL,
                location_score REAL,
                status TEXT DEFAULT 'pending',
                rank INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lost_item_id) REFERENCES lost_items(id),
                FOREIGN KEY (found_item_id) REFERENCES found_items(id)
            )
        ''')

        # ========== 确认记录表 ==========
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS confirmations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER,
                user_id INTEGER,
                result TEXT NOT NULL,
                skip_reason TEXT,
                rating INTEGER,
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (match_id) REFERENCES matches(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # ========== 通知表 ==========
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                related_item_id INTEGER,
                related_item_type TEXT,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # ========== 物品分类表 ==========
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                icon TEXT,
                description TEXT,
                parent_id INTEGER,
                sort_order INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # ========== 地点表 ==========
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                parent_id INTEGER,
                latitude REAL,
                longitude REAL,
                description TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # ========== 积分记录表 ==========
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS credit_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action_type TEXT NOT NULL,
                points INTEGER NOT NULL,
                description TEXT,
                related_item_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # ========== 系统配置表 ==========
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_key TEXT UNIQUE NOT NULL,
                config_value TEXT,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # ========== 认领表（全新） ==========
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_type TEXT NOT NULL,
                item_id INTEGER NOT NULL,
                claimant_user_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                proof_images TEXT,
                status TEXT DEFAULT 'pending',
                reviewer_id INTEGER,
                review_note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                FOREIGN KEY (claimant_user_id) REFERENCES users(id),
                FOREIGN KEY (reviewer_id) REFERENCES users(id)
            )
        ''')

        # ========== 第三方登录表（全新） ==========
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS oauth_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                provider TEXT NOT NULL,
                provider_uid TEXT NOT NULL,
                access_token TEXT,
                refresh_token TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(provider, provider_uid)
            )
        ''')

        # ========== 社区帖子表 ==========
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS community_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT,
                content TEXT NOT NULL,
                images TEXT,
                category TEXT,
                tags TEXT,
                likes_count INTEGER DEFAULT 0,
                comments_count INTEGER DEFAULT 0,
                views_count INTEGER DEFAULT 0,
                is_pinned INTEGER DEFAULT 0,
                is_essence INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # 兼容升级：为已有表添加新列
        try:
            cursor.execute('ALTER TABLE community_posts ADD COLUMN is_pinned INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute('ALTER TABLE community_posts ADD COLUMN is_essence INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass

        # ========== 社区评论表 ==========
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS community_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                parent_id INTEGER DEFAULT NULL,
                likes_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES community_posts(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (parent_id) REFERENCES community_comments(id)
            )
        ''')

        # ========== 社区点赞表 ==========
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS community_likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_type TEXT NOT NULL,
                target_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(target_type, target_id, user_id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # ========== 社区举报表 ==========
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS community_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_type TEXT NOT NULL,
                target_id INTEGER NOT NULL,
                reporter_user_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (reporter_user_id) REFERENCES users(id)
            )
        ''')

        # 仅在数据库首次创建时插入初始数据
        cursor.execute('SELECT COUNT(*) FROM system_configs')
        if cursor.fetchone()[0] == 0:
            self._init_seed_data(cursor)

        conn.commit()
        conn.close()

    def _init_seed_data(self, cursor):
        """插入初始种子数据（分类、地点、系统配置、管理员）"""
        # 初始化分类数据
        categories = [
            ('电子设备', '💻', '手机、电脑、平板等电子设备', None, 1),
            ('手机', '📱', '智能手机', 1, 1),
            ('电脑', '💻', '笔记本电脑、平板电脑', 1, 2),
            ('耳机', '🎧', '有线耳机、蓝牙耳机', 1, 3),
            ('证件卡片', '🪪', '身份证、学生证、银行卡等', None, 2),
            ('身份证', '🆔', '居民身份证', 2, 1),
            ('学生证', '🎓', '校园学生证', 2, 2),
            ('银行卡', '💳', '各类银行卡', 2, 3),
            ('箱包', '🎒', '背包、手提包、行李箱等', None, 3),
            ('背包', '🎒', '双肩背包、单肩包', 3, 1),
            ('手提包', '👜', '手提包、斜挎包', 3, 2),
            ('行李箱', '🧳', '拉杆箱、旅行箱', 3, 3),
            ('书籍文具', '📚', '书籍、笔记本、文具等', None, 4),
            ('书籍', '📖', '教材、课外书', 4, 1),
            ('文具', '✏️', '笔、本子、尺子', 4, 2),
            ('钥匙', '🔑', '各类钥匙、钥匙串', None, 5),
            ('服饰', '👕', '衣服、鞋子、帽子等', None, 6),
            ('其他', '📦', '其他物品', None, 7)
        ]

        for cat in categories:
            cursor.execute('''
                INSERT INTO categories (name, icon, description, parent_id, sort_order)
                VALUES (?, ?, ?, ?, ?)
            ''', cat)

        # 初始化地点数据
        locations = [
            ('教学楼', 'building', None, None, None, '校内教学区域'),
            ('图书馆', 'building', None, None, None, '图书借阅区域'),
            ('食堂', 'building', None, None, None, '餐饮区域'),
            ('宿舍区', 'building', None, None, None, '学生宿舍'),
            ('操场', 'area', None, None, None, '运动场地'),
            ('体育馆', 'building', None, None, None, '室内运动场馆'),
            ('校门口', 'area', None, None, None, '学校出入口'),
            ('停车场', 'area', None, None, None, '车辆停放区域'),
            ('实验楼', 'building', None, None, None, '实验教学区域'),
            ('行政楼', 'building', None, None, None, '办公区域')
        ]

        for loc in locations:
            cursor.execute('''
                INSERT INTO locations (name, type, parent_id, latitude, longitude, description)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', loc)

        # 初始化系统配置
        configs = [
            ('site_name', '校园智能失物招领系统', '系统名称'),
            ('match_threshold_high', '0.8', '高匹配阈值'),
            ('match_threshold_medium', '0.6', '中匹配阈值'),
            ('match_threshold_low', '0.4', '低匹配阈值'),
            ('auto_match_enabled', '1', '是否启用自动匹配'),
            ('notification_enabled', '1', '是否启用通知'),
            ('max_matches_per_item', '10', '每个物品最大匹配数'),
            ('credit_base', '100', '初始信用分'),
            ('reward_enabled', '1', '是否启用悬赏功能')
        ]

        for config in configs:
            cursor.execute('''
                INSERT INTO system_configs (config_key, config_value, description)
                VALUES (?, ?, ?)
            ''', config)

        # 添加默认管理员用户
        import hashlib
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, real_name, role, credit_score)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('admin', 'admin@school.edu.cn',
              hashlib.sha256('admin123'.encode()).hexdigest(),
              '管理员', 'admin', 100))

    def connect(self):
        """创建数据库连接，启用字典模式"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ========================================================================
    #  用户管理模块
    # ========================================================================

    def add_user(self, **kwargs):
        """添加新用户"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (username, email, phone, student_id, password_hash, real_name, avatar)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (kwargs['username'], kwargs.get('email'), kwargs.get('phone'),
              kwargs.get('student_id'), kwargs['password_hash'], kwargs['real_name'], kwargs.get('avatar')))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return user_id

    def get_user_by_username(self, username):
        """根据用户名获取用户信息"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        return dict(user) if user else None

    def get_user_by_id(self, user_id):
        """根据用户ID获取用户信息"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        return dict(user) if user else None

    def update_user(self, user_id, **kwargs):
        """更新用户基本信息"""
        conn = self.connect()
        cursor = conn.cursor()

        allowed_fields = ['email', 'phone', 'real_name', 'avatar', 'notification_enabled']
        updates = []
        values = []

        for field in allowed_fields:
            if field in kwargs:
                updates.append(f"{field} = ?")
                values.append(kwargs[field])

        if updates:
            values.append(datetime.now())
            values.append(user_id)
            cursor.execute(f'''
                UPDATE users SET {', '.join(updates)}, updated_at = ? WHERE id = ?
            ''', values)
            conn.commit()

        conn.close()

    def update_credit_score(self, user_id, points, action_type, description=None, related_item_id=None):
        """更新用户信用积分并记录变动"""
        conn = self.connect()
        cursor = conn.cursor()

        # 更新用户积分
        cursor.execute('''
            UPDATE users SET credit_score = credit_score + ? WHERE id = ?
        ''', (points, user_id))

        # 记录积分变动
        cursor.execute('''
            INSERT INTO credit_records (user_id, action_type, points, description, related_item_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, action_type, points, description, related_item_id))

        conn.commit()
        conn.close()

    def get_all_users(self, keyword=None, role=None, status=None, limit=None, offset=None):
        """获取所有用户列表，支持分页和搜索

        Args:
            keyword: 搜索关键词（匹配用户名、真实姓名、学号、邮箱）
            role: 按角色筛选（user/admin）
            status: 按状态筛选（active/banned）
            limit: 每页数量
            offset: 偏移量

        Returns:
            用户字典列表
        """
        conn = self.connect()
        cursor = conn.cursor()

        query = 'SELECT * FROM users WHERE 1=1'
        params = []

        if keyword:
            query += ' AND (username LIKE ? OR real_name LIKE ? OR student_id LIKE ? OR email LIKE ?)'
            kw = f'%{keyword}%'
            params.extend([kw, kw, kw, kw])

        if role:
            query += ' AND role = ?'
            params.append(role)

        if status:
            query += ' AND status = ?'
            params.append(status)

        query += ' ORDER BY created_at DESC'

        if limit is not None:
            query += ' LIMIT ?'
            params.append(limit)
        if offset is not None:
            query += ' OFFSET ?'
            params.append(offset)

        cursor.execute(query, params)
        users = cursor.fetchall()
        conn.close()
        return [dict(u) for u in users]

    def ban_user(self, user_id):
        """封禁用户，将状态设为 banned"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET status = 'banned', updated_at = ? WHERE id = ?
        ''', (datetime.now(), user_id))
        conn.commit()
        conn.close()

    def unban_user(self, user_id):
        """解封用户，将状态恢复为 active"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET status = 'active', updated_at = ? WHERE id = ?
        ''', (datetime.now(), user_id))
        conn.commit()
        conn.close()

    def delete_user(self, user_id):
        """删除用户及其关联的第三方账号记录"""
        conn = self.connect()
        cursor = conn.cursor()
        # 先删除关联的第三方账号
        cursor.execute('DELETE FROM oauth_accounts WHERE user_id = ?', (user_id,))
        # 再删除用户
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()

    def set_user_role(self, user_id, role):
        """设置用户角色

        Args:
            user_id: 用户ID
            role: 角色（user/admin）
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET role = ?, updated_at = ? WHERE id = ?
        ''', (role, datetime.now(), user_id))
        conn.commit()
        conn.close()

    def get_user_count(self):
        """获取用户总数"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        count = cursor.fetchone()[0]
        conn.close()
        return count

    # ========================================================================
    #  失物信息管理模块
    # ========================================================================

    def add_lost_item(self, **kwargs):
        """发布失物信息"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO lost_items (user_id, name, category, sub_category, brand, description,
                                  lost_time, location, location_detail, latitude,
                                  longitude, images, expected_reward, urgency_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (kwargs['user_id'], kwargs['name'], kwargs['category'], kwargs.get('sub_category'),
              kwargs.get('brand'), kwargs['description'], kwargs['lost_time'], kwargs['location'],
              kwargs.get('location_detail'), kwargs.get('latitude'), kwargs.get('longitude'),
              kwargs.get('images'), kwargs.get('expected_reward'), kwargs.get('urgency_level', 'normal')))
        conn.commit()
        item_id = cursor.lastrowid
        conn.close()
        return item_id

    def get_lost_items(self, status=None, category=None, user_id=None, limit=None, offset=None):
        """获取失物列表，支持条件筛选"""
        conn = self.connect()
        cursor = conn.cursor()

        query = 'SELECT * FROM lost_items WHERE 1=1'
        params = []

        if status:
            query += ' AND status = ?'
            params.append(status)
        if category:
            query += ' AND category = ?'
            params.append(category)
        if user_id:
            query += ' AND user_id = ?'
            params.append(user_id)

        query += ' ORDER BY created_at DESC'

        if limit:
            query += ' LIMIT ?'
            params.append(limit)
        if offset:
            query += ' OFFSET ?'
            params.append(offset)

        cursor.execute(query, params)
        items = cursor.fetchall()
        conn.close()
        return [dict(item) for item in items]

    def get_lost_item_by_id(self, item_id):
        """根据ID获取失物详情"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM lost_items WHERE id = ?', (item_id,))
        item = cursor.fetchone()
        conn.close()
        return dict(item) if item else None

    def update_lost_item_status(self, item_id, status):
        """更新失物状态"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE lost_items SET status = ?, updated_at = ? WHERE id = ?
        ''', (status, datetime.now(), item_id))
        conn.commit()
        conn.close()

    def increment_lost_view_count(self, item_id):
        """增加失物浏览次数"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE lost_items SET view_count = view_count + 1 WHERE id = ?
        ''', (item_id,))
        conn.commit()
        conn.close()

    def update_lost_item(self, item_id, **kwargs):
        """编辑失物信息

        Args:
            item_id: 失物ID
            kwargs: 可更新的字段（name, category, brand, description, lost_time,
                    location, location_detail, latitude, longitude, images,
                    expected_reward, urgency_level）
        """
        conn = self.connect()
        cursor = conn.cursor()

        allowed_fields = [
            'name', 'category', 'sub_category', 'brand', 'description', 'lost_time',
            'location', 'location_detail', 'latitude', 'longitude',
            'images', 'expected_reward', 'urgency_level'
        ]
        updates = []
        values = []

        for field in allowed_fields:
            if field in kwargs:
                updates.append(f"{field} = ?")
                values.append(kwargs[field])

        if updates:
            values.append(datetime.now())
            values.append(item_id)
            cursor.execute(f'''
                UPDATE lost_items SET {', '.join(updates)}, updated_at = ? WHERE id = ?
            ''', values)
            conn.commit()

        conn.close()

    def delete_lost_item(self, item_id):
        """删除失物记录"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM lost_items WHERE id = ?', (item_id,))
        conn.commit()
        conn.close()

    def audit_lost_item(self, item_id, status, reason=None):
        """审核失物信息（通过/拒绝）

        Args:
            item_id: 失物ID
            status: 审核状态（approved/rejected）
            reason: 审核原因（可选）
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE lost_items SET status = ?, updated_at = ? WHERE id = ?
        ''', (status, datetime.now(), item_id))
        conn.commit()
        conn.close()

    def get_lost_items_by_time(self, start_time, end_time):
        """按时间范围查询失物

        Args:
            start_time: 起始时间（datetime 或格式化字符串）
            end_time: 结束时间（datetime 或格式化字符串）

        Returns:
            失物字典列表
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM lost_items
            WHERE lost_time >= ? AND lost_time <= ?
            ORDER BY lost_time DESC
        ''', (start_time, end_time))
        items = cursor.fetchall()
        conn.close()
        return [dict(item) for item in items]

    # ========================================================================
    #  招领信息管理模块
    # ========================================================================

    def add_found_item(self, **kwargs):
        """发布招领信息"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO found_items (user_id, name, category, sub_category, description, found_time,
                                    location, location_detail, latitude, longitude,
                                    images, storage_method, contact_methods)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (kwargs['user_id'], kwargs['name'], kwargs['category'], kwargs.get('sub_category'),
              kwargs['description'], kwargs['found_time'], kwargs['location'], kwargs.get('location_detail'),
              kwargs.get('latitude'), kwargs.get('longitude'), kwargs.get('images'),
              kwargs['storage_method'], kwargs['contact_methods']))
        conn.commit()
        item_id = cursor.lastrowid
        conn.close()
        return item_id

    def get_found_items(self, status=None, category=None, user_id=None, limit=None, offset=None):
        """获取招领列表，支持条件筛选"""
        conn = self.connect()
        cursor = conn.cursor()

        query = 'SELECT * FROM found_items WHERE 1=1'
        params = []

        if status:
            query += ' AND status = ?'
            params.append(status)
        if category:
            query += ' AND category = ?'
            params.append(category)
        if user_id:
            query += ' AND user_id = ?'
            params.append(user_id)

        query += ' ORDER BY created_at DESC'

        if limit:
            query += ' LIMIT ?'
            params.append(limit)
        if offset:
            query += ' OFFSET ?'
            params.append(offset)

        cursor.execute(query, params)
        items = cursor.fetchall()
        conn.close()
        return [dict(item) for item in items]

    def get_found_item_by_id(self, item_id):
        """根据ID获取招领详情"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM found_items WHERE id = ?', (item_id,))
        item = cursor.fetchone()
        conn.close()
        return dict(item) if item else None

    def update_found_item_status(self, item_id, status):
        """更新招领状态"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE found_items SET status = ?, updated_at = ? WHERE id = ?
        ''', (status, datetime.now(), item_id))
        conn.commit()
        conn.close()

    def increment_found_view_count(self, item_id):
        """增加招领浏览次数"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE found_items SET view_count = view_count + 1 WHERE id = ?
        ''', (item_id,))
        conn.commit()
        conn.close()

    def update_found_item(self, item_id, **kwargs):
        """编辑招领信息

        Args:
            item_id: 招领ID
            kwargs: 可更新的字段（name, category, description, found_time,
                    location, location_detail, latitude, longitude, images,
                    storage_method, contact_methods）
        """
        conn = self.connect()
        cursor = conn.cursor()

        allowed_fields = [
            'name', 'category', 'sub_category', 'description', 'found_time',
            'location', 'location_detail', 'latitude', 'longitude',
            'images', 'storage_method', 'contact_methods'
        ]
        updates = []
        values = []

        for field in allowed_fields:
            if field in kwargs:
                updates.append(f"{field} = ?")
                values.append(kwargs[field])

        if updates:
            values.append(datetime.now())
            values.append(item_id)
            cursor.execute(f'''
                UPDATE found_items SET {', '.join(updates)}, updated_at = ? WHERE id = ?
            ''', values)
            conn.commit()

        conn.close()

    def delete_found_item(self, item_id):
        """删除招领记录"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM found_items WHERE id = ?', (item_id,))
        conn.commit()
        conn.close()

    def audit_found_item(self, item_id, status, reason=None):
        """审核招领信息（通过/拒绝）

        Args:
            item_id: 招领ID
            status: 审核状态（approved/rejected）
            reason: 审核原因（可选）
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE found_items SET status = ?, updated_at = ? WHERE id = ?
        ''', (status, datetime.now(), item_id))
        conn.commit()
        conn.close()

    # ========================================================================
    #  认领管理模块（全新）
    # ========================================================================

    def add_claim(self, **kwargs):
        """提交认领申请

        Args:
            kwargs: 认领信息字段
                - item_type: 物品类型（lost/found）
                - item_id: 物品ID
                - claimant_user_id: 认领人用户ID
                - description: 认领描述
                - proof_images: 证明图片（JSON字符串，可选）

        Returns:
            认领记录ID
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO claims (item_type, item_id, claimant_user_id, description, proof_images)
            VALUES (?, ?, ?, ?, ?)
        ''', (kwargs['item_type'], kwargs['item_id'], kwargs['claimant_user_id'],
              kwargs['description'], kwargs.get('proof_images')))
        conn.commit()
        claim_id = cursor.lastrowid
        conn.close()
        return claim_id

    def get_claims_by_item(self, item_type, item_id):
        """获取某物品的所有认领记录

        Args:
            item_type: 物品类型（lost/found）
            item_id: 物品ID

        Returns:
            认领记录字典列表
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT c.*, u.username, u.real_name, u.avatar
            FROM claims c
            LEFT JOIN users u ON c.claimant_user_id = u.id
            WHERE c.item_type = ? AND c.item_id = ?
            ORDER BY c.created_at DESC
        ''', (item_type, item_id))
        claims = cursor.fetchall()
        conn.close()
        return [dict(c) for c in claims]

    def get_claims_by_user(self, user_id):
        """获取某用户的所有认领记录

        Args:
            user_id: 用户ID

        Returns:
            认领记录字典列表
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM claims
            WHERE claimant_user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
        claims = cursor.fetchall()
        conn.close()
        return [dict(c) for c in claims]

    def get_all_claims(self, status=None, limit=None, offset=None):
        """获取所有认领记录（管理员视角），支持状态筛选和分页

        Args:
            status: 认领状态筛选（pending/approved/rejected/completed）
            limit: 每页数量
            offset: 偏移量

        Returns:
            认领记录字典列表
        """
        conn = self.connect()
        cursor = conn.cursor()

        query = '''
            SELECT c.*, u.username as claimant_name, u.real_name as claimant_real_name,
                   r.username as reviewer_name
            FROM claims c
            LEFT JOIN users u ON c.claimant_user_id = u.id
            LEFT JOIN users r ON c.reviewer_id = r.id
            WHERE 1=1
        '''
        params = []

        if status:
            query += ' AND c.status = ?'
            params.append(status)

        query += ' ORDER BY c.created_at DESC'

        if limit is not None:
            query += ' LIMIT ?'
            params.append(limit)
        if offset is not None:
            query += ' OFFSET ?'
            params.append(offset)

        cursor.execute(query, params)
        claims = cursor.fetchall()
        conn.close()
        return [dict(c) for c in claims]

    def review_claim(self, claim_id, status, reviewer_id, note=None):
        """审核认领申请"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE claims
            SET status = ?, reviewer_id = ?, review_note = ?, reviewed_at = ?
            WHERE id = ?
        ''', (status, reviewer_id, note, datetime.now(), claim_id))
        conn.commit()
        # 获取认领信息用于通知和积分
        cursor.execute('SELECT claimant_user_id, item_type, item_id FROM claims WHERE id = ?', (claim_id,))
        claim = cursor.fetchone()
        conn.close()
        return dict(claim) if claim else None

    def get_claim_by_id(self, claim_id):
        """根据ID获取认领详情

        Args:
            claim_id: 认领记录ID

        Returns:
            认领记录字典，不存在则返回None
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT c.*, u.username as claimant_name, u.real_name as claimant_real_name,
                   r.username as reviewer_name
            FROM claims c
            LEFT JOIN users u ON c.claimant_user_id = u.id
            LEFT JOIN users r ON c.reviewer_id = r.id
            WHERE c.id = ?
        ''', (claim_id,))
        claim = cursor.fetchone()
        conn.close()
        return dict(claim) if claim else None

    # ========================================================================
    #  匹配相关操作
    # ========================================================================

    def add_match(self, **kwargs):
        """添加匹配记录"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO matches (lost_item_id, found_item_id, score, image_score,
                                text_score, time_score, location_score, status, rank)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (kwargs['lost_item_id'], kwargs['found_item_id'], kwargs['score'],
              kwargs.get('image_score'), kwargs.get('text_score'), kwargs.get('time_score'),
              kwargs.get('location_score'), kwargs.get('status', 'pending'), kwargs.get('rank')))
        conn.commit()
        match_id = cursor.lastrowid
        conn.close()
        return match_id

    def get_matches_for_lost_item(self, lost_item_id):
        """获取失物对应的匹配列表"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT m.*, f.name as found_name, f.description as found_desc, f.location as found_location
            FROM matches m
            JOIN found_items f ON m.found_item_id = f.id
            WHERE m.lost_item_id = ?
            ORDER BY m.score DESC
        ''', (lost_item_id,))
        matches = cursor.fetchall()
        conn.close()
        return [dict(match) for match in matches]

    def get_matches_for_found_item(self, found_item_id):
        """获取招领对应的匹配列表"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT m.*, l.name as lost_name, l.description as lost_desc, l.location as lost_location
            FROM matches m
            JOIN lost_items l ON m.lost_item_id = l.id
            WHERE m.found_item_id = ?
            ORDER BY m.score DESC
        ''', (found_item_id,))
        matches = cursor.fetchall()
        conn.close()
        return [dict(match) for match in matches]

    def update_match_status(self, match_id, status):
        """更新匹配状态"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE matches SET status = ?, updated_at = ? WHERE id = ?
        ''', (status, datetime.now(), match_id))
        conn.commit()
        conn.close()

    # ========================================================================
    #  通知相关操作
    # ========================================================================

    def add_notification(self, **kwargs):
        """添加通知"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO notifications (user_id, type, title, content, related_item_id, related_item_type)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (kwargs['user_id'], kwargs['type'], kwargs['title'], kwargs['content'],
              kwargs.get('related_item_id'), kwargs.get('related_item_type')))
        conn.commit()
        notif_id = cursor.lastrowid
        conn.close()
        return notif_id

    def get_user_notifications(self, user_id, unread_only=False):
        """获取用户通知列表"""
        conn = self.connect()
        cursor = conn.cursor()

        query = 'SELECT * FROM notifications WHERE user_id = ?'
        params = [user_id]

        if unread_only:
            query += ' AND is_read = 0'

        query += ' ORDER BY created_at DESC'

        cursor.execute(query, params)
        notifications = cursor.fetchall()
        conn.close()
        return [dict(notif) for notif in notifications]

    def mark_notification_read(self, notification_id):
        """标记通知为已读"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE notifications SET is_read = 1 WHERE id = ?
        ''', (notification_id,))
        conn.commit()
        conn.close()

    def mark_all_notifications_read(self, user_id):
        """标记用户所有通知为已读"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0
        ''', (user_id,))
        conn.commit()
        conn.close()

    def update_claim_status(self, claim_id, status, reviewer_id=None, review_note=None):
        """更新认领状态"""
        conn = self.connect()
        cursor = conn.cursor()
        if status == 'cancelled':
            cursor.execute('''
                UPDATE claims SET status = ?, reviewed_at = CURRENT_TIMESTAMP WHERE id = ?
            ''', (status, claim_id))
        else:
            cursor.execute('''
                UPDATE claims SET status = ?, reviewer_id = ?, review_note = ?, reviewed_at = CURRENT_TIMESTAMP WHERE id = ?
            ''', (status, reviewer_id, review_note, claim_id))
        conn.commit()
        conn.close()

    # ========================================================================
    #  统计分析模块
    # ========================================================================

    def get_statistics(self):
        """获取系统基础统计数据"""
        conn = self.connect()
        cursor = conn.cursor()

        stats = {}

        # 总失物数
        cursor.execute('SELECT COUNT(*) FROM lost_items')
        stats['total_lost'] = cursor.fetchone()[0]

        # 总招领数
        cursor.execute('SELECT COUNT(*) FROM found_items')
        stats['total_found'] = cursor.fetchone()[0]

        # 已匹配数
        cursor.execute('SELECT COUNT(*) FROM matches WHERE status = "confirmed"')
        stats['matched'] = cursor.fetchone()[0]

        # 待处理失物
        cursor.execute('SELECT COUNT(*) FROM lost_items WHERE status = "pending"')
        stats['pending_lost'] = cursor.fetchone()[0]

        # 待处理招领
        cursor.execute('SELECT COUNT(*) FROM found_items WHERE status = "pending"')
        stats['pending_found'] = cursor.fetchone()[0]

        # 今日新增
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('SELECT COUNT(*) FROM lost_items WHERE date(created_at) = ?', (today,))
        stats['today_lost'] = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM found_items WHERE date(created_at) = ?', (today,))
        stats['today_found'] = cursor.fetchone()[0]

        # 分类统计
        cursor.execute('''
            SELECT category, COUNT(*) as count FROM lost_items
            WHERE status = 'pending' GROUP BY category ORDER BY count DESC
        ''')
        stats['category_stats'] = [dict(row) for row in cursor.fetchall()]

        # 地点统计
        cursor.execute('''
            SELECT location, COUNT(*) as count FROM lost_items
            WHERE status = 'pending' GROUP BY location ORDER BY count DESC LIMIT 10
        ''')
        stats['location_stats'] = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return stats

    def get_claim_success_rate(self):
        """计算认领成功率

        Returns:
            成功率（浮点数，0~1之间）
        """
        conn = self.connect()
        cursor = conn.cursor()

        # 总认领数
        cursor.execute('SELECT COUNT(*) FROM claims')
        total = cursor.fetchone()[0]

        if total == 0:
            conn.close()
            return 0.0

        # 成功认领数（approved + completed）
        cursor.execute('''
            SELECT COUNT(*) FROM claims WHERE status IN ('approved', 'completed')
        ''')
        success = cursor.fetchone()[0]

        conn.close()
        return round(success / total, 4)

    def get_high_frequency_items(self, limit=10):
        """获取高频丢失物品排行

        Args:
            limit: 返回数量上限

        Returns:
            列表，每项包含 name 和 count
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT name, COUNT(*) as count
            FROM lost_items
            GROUP BY name
            ORDER BY count DESC
            LIMIT ?
        ''', (limit,))
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def get_hotspot_locations(self, limit=10):
        """获取丢失高发地点排行

        Args:
            limit: 返回数量上限

        Returns:
            列表，每项包含 location 和 count
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT location, COUNT(*) as count
            FROM lost_items
            GROUP BY location
            ORDER BY count DESC
            LIMIT ?
        ''', (limit,))
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    def get_trend_data(self, days=30):
        """获取最近N天的趋势数据（每日新增失物数、招领数、认领数）

        Args:
            days: 天数

        Returns:
            列表，每项包含 date, lost_count, found_count, claim_count
        """
        conn = self.connect()
        cursor = conn.cursor()

        result = []
        for i in range(days - 1, -1, -1):
            day = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')

            cursor.execute('''
                SELECT COUNT(*) FROM lost_items WHERE date(created_at) = ?
            ''', (day,))
            lost_count = cursor.fetchone()[0]

            cursor.execute('''
                SELECT COUNT(*) FROM found_items WHERE date(created_at) = ?
            ''', (day,))
            found_count = cursor.fetchone()[0]

            cursor.execute('''
                SELECT COUNT(*) FROM claims WHERE date(created_at) = ?
            ''', (day,))
            claim_count = cursor.fetchone()[0]

            result.append({
                'date': day,
                'lost_count': lost_count,
                'found_count': found_count,
                'claim_count': claim_count
            })

        conn.close()
        return result

    def get_monthly_stats(self):
        """获取月度统计数据（最近12个月）

        Returns:
            列表，每项包含 month, lost_count, found_count, claim_count, match_count
        """
        conn = self.connect()
        cursor = conn.cursor()

        result = []
        for i in range(11, -1, -1):
            # 计算目标月份的起止日期
            now = datetime.now()
            target_month = now.month - i
            target_year = now.year
            while target_month <= 0:
                target_month += 12
                target_year -= 1

            month_str = f'{target_year}-{target_month:02d}'

            cursor.execute('''
                SELECT COUNT(*) FROM lost_items
                WHERE strftime('%Y-%m', created_at) = ?
            ''', (month_str,))
            lost_count = cursor.fetchone()[0]

            cursor.execute('''
                SELECT COUNT(*) FROM found_items
                WHERE strftime('%Y-%m', created_at) = ?
            ''', (month_str,))
            found_count = cursor.fetchone()[0]

            cursor.execute('''
                SELECT COUNT(*) FROM claims
                WHERE strftime('%Y-%m', created_at) = ?
            ''', (month_str,))
            claim_count = cursor.fetchone()[0]

            cursor.execute('''
                SELECT COUNT(*) FROM matches
                WHERE strftime('%Y-%m', created_at) = ? AND status = 'confirmed'
            ''', (month_str,))
            match_count = cursor.fetchone()[0]

            result.append({
                'month': month_str,
                'lost_count': lost_count,
                'found_count': found_count,
                'claim_count': claim_count,
                'match_count': match_count
            })

        conn.close()
        return result

    def get_claim_counts(self):
        """获取认领统计数量：总数、成功数、待处理数"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM claims')
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM claims WHERE status IN ('approved', 'completed')")
        success = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM claims WHERE status = 'pending'")
        pending = cursor.fetchone()[0]
        conn.close()
        return total, success, pending

    def get_hourly_distribution(self):
        """获取24小时物品丢失/发现时段分布（按实际 lost_time / found_time 统计）"""
        conn = self.connect()
        cursor = conn.cursor()
        result = []
        for hour in range(24):
            cursor.execute('''
                SELECT COUNT(*) FROM lost_items WHERE strftime('%H', lost_time) = ?
            ''', (f'{hour:02d}',))
            lost = cursor.fetchone()[0]
            cursor.execute('''
                SELECT COUNT(*) FROM found_items WHERE strftime('%H', found_time) = ?
            ''', (f'{hour:02d}',))
            found = cursor.fetchone()[0]
            result.append({'hour': f'{hour:02d}', 'count': lost + found, 'lost': lost, 'found': found})
        conn.close()
        return result

    def get_recovery_time_distribution(self):
        """获取物品找回时间分布分析（基于审核通过的认领记录）"""
        conn = self.connect()
        cursor = conn.cursor()
        # 联合查询：已审核通过的认领记录，关联物品丢失/发现时间
        cursor.execute('''
            SELECT l.lost_time, c.reviewed_at
            FROM claims c
            JOIN lost_items l ON c.item_id = l.id
            WHERE c.status = 'approved' AND c.item_type = 'lost' AND c.reviewed_at IS NOT NULL
            UNION ALL
            SELECT f.found_time, c.reviewed_at
            FROM claims c
            JOIN found_items f ON c.item_id = f.id
            WHERE c.status = 'approved' AND c.item_type = 'found' AND c.reviewed_at IS NOT NULL
        ''')
        rows = cursor.fetchall()
        conn.close()

        def parse_flexible_time(s):
            """兼容多种时间格式解析"""
            if not s:
                return None
            s = str(s).split('.')[0]  # 去掉毫秒
            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M'):
                try:
                    return datetime.strptime(s, fmt)
                except ValueError:
                    continue
            return None

        same_day = 0
        one_to_three = 0
        four_to_seven = 0
        eight_to_thirty = 0
        over_thirty = 0
        total_days = 0
        valid_count = 0

        for row in rows:
            try:
                item_time = parse_flexible_time(row[0])
                reviewed_time = parse_flexible_time(row[1])
                if not item_time or not reviewed_time:
                    continue
                diff = (reviewed_time - item_time).days
                total_days += diff
                valid_count += 1
                if diff <= 0:
                    same_day += 1
                elif diff <= 3:
                    one_to_three += 1
                elif diff <= 7:
                    four_to_seven += 1
                elif diff <= 30:
                    eight_to_thirty += 1
                else:
                    over_thirty += 1
            except (ValueError, TypeError):
                continue

        avg_days = round(total_days / valid_count, 1) if valid_count > 0 else 0
        return [
            {'label': 'avg', 'value': avg_days, 'count': avg_days},
            {'label': 'same_day', 'count': same_day},
            {'label': '1_3_days', 'count': one_to_three},
            {'label': '4_7_days', 'count': four_to_seven},
            {'label': '8_30_days', 'count': eight_to_thirty},
            {'label': 'over_30', 'count': over_thirty}
        ]

    # ========================================================================
    #  搜索增强模块
    # ========================================================================

    def search_items(self, keyword, item_type=None, category=None):
        """基础搜索（保留原有接口）"""
        conn = self.connect()
        cursor = conn.cursor()

        results = {'lost': [], 'found': []}

        if item_type in (None, 'lost'):
            query = '''
                SELECT * FROM lost_items
                WHERE (name LIKE ? OR description LIKE ? OR location LIKE ?)
            '''
            params = [f'%{keyword}%', f'%{keyword}%', f'%{keyword}%']

            if category:
                query += ' AND category = ?'
                params.append(category)

            query += ' AND status = "pending" ORDER BY created_at DESC'

            cursor.execute(query, params)
            results['lost'] = [dict(row) for row in cursor.fetchall()]

        if item_type in (None, 'found'):
            query = '''
                SELECT * FROM found_items
                WHERE (name LIKE ? OR description LIKE ? OR location LIKE ?)
            '''
            params = [f'%{keyword}%', f'%{keyword}%', f'%{keyword}%']

            if category:
                query += ' AND category = ?'
                params.append(category)

            query += ' AND status = "pending" ORDER BY created_at DESC'

            cursor.execute(query, params)
            results['found'] = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return results

    def search_items_advanced(self, keyword=None, item_type=None, category=None,
                               location=None, start_time=None, end_time=None,
                               sort_by='created_at', sort_order='DESC'):
        """高级搜索，支持多条件组合和排序

        Args:
            keyword: 关键词（匹配名称、描述）
            item_type: 物品类型（lost/found），None表示同时搜索
            category: 分类筛选
            location: 地点筛选
            start_time: 起始时间
            end_time: 结束时间
            sort_by: 排序字段（created_at/lost_time/found_time/view_count/match_count）
            sort_order: 排序方向（ASC/DESC）

        Returns:
            字典 {'lost': [...], 'found': [...]}
        """
        conn = self.connect()
        cursor = conn.cursor()

        # 允许的排序字段白名单，防止SQL注入
        allowed_sort_fields = {
            'created_at', 'lost_time', 'found_time',
            'view_count', 'match_count', 'name'
        }
        if sort_by not in allowed_sort_fields:
            sort_by = 'created_at'
        if sort_order.upper() not in ('ASC', 'DESC'):
            sort_order = 'DESC'

        results = {'lost': [], 'found': []}

        # ---------- 搜索失物 ----------
        if item_type in (None, 'lost'):
            query = 'SELECT * FROM lost_items WHERE 1=1'
            params = []

            if keyword:
                query += ' AND (name LIKE ? OR description LIKE ?)'
                params.extend([f'%{keyword}%', f'%{keyword}%'])
            if category:
                query += ' AND category = ?'
                params.append(category)
            if location:
                query += ' AND location LIKE ?'
                params.append(f'%{location}%')
            if start_time:
                query += ' AND lost_time >= ?'
                params.append(start_time)
            if end_time:
                query += ' AND lost_time <= ?'
                params.append(end_time)

            query += f' ORDER BY {sort_by} {sort_order}'
            cursor.execute(query, params)
            results['lost'] = [dict(row) for row in cursor.fetchall()]

        # ---------- 搜索招领 ----------
        if item_type in (None, 'found'):
            query = 'SELECT * FROM found_items WHERE 1=1'
            params = []

            if keyword:
                query += ' AND (name LIKE ? OR description LIKE ?)'
                params.extend([f'%{keyword}%', f'%{keyword}%'])
            if category:
                query += ' AND category = ?'
                params.append(category)
            if location:
                query += ' AND location LIKE ?'
                params.append(f'%{location}%')
            if start_time:
                query += ' AND found_time >= ?'
                params.append(start_time)
            if end_time:
                query += ' AND found_time <= ?'
                params.append(end_time)

            query += f' ORDER BY {sort_by} {sort_order}'
            cursor.execute(query, params)
            results['found'] = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return results

    # ========================================================================
    #  第三方登录模块（全新）
    # ========================================================================

    def link_oauth_account(self, user_id, provider, provider_uid, access_token=None):
        """绑定第三方账号

        Args:
            user_id: 本系统用户ID
            provider: 第三方平台（wechat/qq/github）
            provider_uid: 第三方平台用户唯一标识
            access_token: 访问令牌（可选）

        Returns:
            绑定记录ID
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO oauth_accounts (user_id, provider, provider_uid, access_token)
            VALUES (?, ?, ?, ?)
        ''', (user_id, provider, provider_uid, access_token))
        conn.commit()
        oauth_id = cursor.lastrowid
        conn.close()
        return oauth_id

    def get_user_by_oauth(self, provider, provider_uid):
        """通过第三方账号查找对应用户

        Args:
            provider: 第三方平台（wechat/qq/github）
            provider_uid: 第三方平台用户唯一标识

        Returns:
            用户字典，未找到则返回None
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.* FROM users u
            INNER JOIN oauth_accounts o ON u.id = o.user_id
            WHERE o.provider = ? AND o.provider_uid = ?
        ''', (provider, provider_uid))
        user = cursor.fetchone()
        conn.close()
        return dict(user) if user else None

    def unlink_oauth_account(self, user_id, provider):
        """解绑第三方账号

        Args:
            user_id: 本系统用户ID
            provider: 第三方平台（wechat/qq/github）
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM oauth_accounts WHERE user_id = ? AND provider = ?
        ''', (user_id, provider))
        conn.commit()
        conn.close()

    # ========================================================================
    #  系统配置操作
    # ========================================================================

    def get_config(self, key):
        """获取系统配置值"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT config_value FROM system_configs WHERE config_key = ?', (key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    def update_config(self, key, value):
        """更新系统配置值"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE system_configs SET config_value = ?, updated_at = ? WHERE config_key = ?
        ''', (value, datetime.now(), key))
        conn.commit()
        conn.close()

    # ========================================================================
    #  分类和地点操作
    # ========================================================================

    def get_categories(self, parent_id=None):
        """获取分类列表，可按父级筛选"""
        conn = self.connect()
        cursor = conn.cursor()

        if parent_id is None:
            cursor.execute('SELECT * FROM categories WHERE parent_id IS NULL AND is_active = 1 ORDER BY sort_order')
        else:
            cursor.execute('SELECT * FROM categories WHERE parent_id = ? AND is_active = 1 ORDER BY sort_order', (parent_id,))

        categories = cursor.fetchall()
        conn.close()
        return [dict(cat) for cat in categories]

    def get_all_categories(self):
        """获取所有活跃分类"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM categories WHERE is_active = 1 ORDER BY sort_order')
        categories = cursor.fetchall()
        conn.close()
        return [dict(cat) for cat in categories]

    def get_locations(self):
        """获取所有活跃地点"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM locations WHERE is_active = 1 ORDER BY name')
        locations = cursor.fetchall()
        conn.close()
        return [dict(loc) for loc in locations]

    # ========================================================================
    #  积分记录操作
    # ========================================================================

    def get_credit_records(self, user_id, limit=20):
        """获取用户积分变动记录"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM credit_records WHERE user_id = ? ORDER BY created_at DESC LIMIT ?
        ''', (user_id, limit))
        records = cursor.fetchall()
        conn.close()
        return [dict(record) for record in records]

    # =======================================================================
    #  社区功能操作
    # =======================================================================

    def add_community_post(self, user_id, content, title=None, images=None, category=None, tags=None):
        """发布社区帖子"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO community_posts (user_id, title, content, images, category, tags)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, title, content, images, category, tags))
        post_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return post_id

    def get_community_posts(self, category=None, search=None, sort='latest', limit=20, offset=0):
        """获取社区帖子列表，支持分类、搜索、排序"""
        conn = self.connect()
        cursor = conn.cursor()
        where_clauses = ["p.status = 'active'"]
        params = []
        if category and category != 'all':
            where_clauses.append("p.category = ?")
            params.append(category)
        if search:
            where_clauses.append("(p.title LIKE ? OR p.content LIKE ? OR p.tags LIKE ?)")
            params.extend(['%' + search + '%', '%' + search + '%', '%' + search + '%'])
        where_sql = ' AND '.join(where_clauses)
        if sort == 'hot':
            order_sql = "p.views_count * 1 + p.likes_count * 3 + p.comments_count * 2 DESC, p.created_at DESC"
        elif sort == 'essence':
            order_sql = "p.is_essence DESC, p.created_at DESC"
        else:
            order_sql = "p.is_pinned DESC, p.created_at DESC"
        params.extend([limit, offset])
        cursor.execute(f'''
            SELECT p.*, u.username, u.real_name, u.avatar
            FROM community_posts p
            JOIN users u ON p.user_id = u.id
            WHERE {where_sql}
            ORDER BY {order_sql}
            LIMIT ? OFFSET ?
        ''', params)
        posts = cursor.fetchall()
        conn.close()
        return [dict(p) for p in posts]

    def get_community_post_by_id(self, post_id):
        """获取帖子详情"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.*, u.username, u.real_name, u.avatar
            FROM community_posts p
            JOIN users u ON p.user_id = u.id
            WHERE p.id = ?
        ''', (post_id,))
        post = cursor.fetchone()
        if post:
            cursor.execute('UPDATE community_posts SET views_count = views_count + 1 WHERE id = ?', (post_id,))
            conn.commit()
        conn.close()
        return dict(post) if post else None

    def get_my_community_posts(self, user_id, limit=50):
        """获取我的帖子"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.*, u.username, u.real_name, u.avatar
            FROM community_posts p
            JOIN users u ON p.user_id = u.id
            WHERE p.user_id = ? AND p.status = 'active'
            ORDER BY p.created_at DESC
            LIMIT ?
        ''', (user_id, limit))
        posts = cursor.fetchall()
        conn.close()
        return [dict(p) for p in posts]

    def delete_community_post(self, post_id, user_id):
        """删除帖子"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM community_posts WHERE id = ? AND user_id = ?', (post_id, user_id))
        conn.commit()
        conn.close()

    def add_comment(self, post_id, user_id, content, parent_id=None):
        """添加评论"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO community_comments (post_id, user_id, content, parent_id)
            VALUES (?, ?, ?, ?)
        ''', (post_id, user_id, content, parent_id))
        comment_id = cursor.lastrowid
        cursor.execute('UPDATE community_posts SET comments_count = comments_count + 1 WHERE id = ?', (post_id,))
        conn.commit()
        conn.close()
        return comment_id

    def get_comments_by_post(self, post_id):
        """获取帖子评论（包含用户信息）"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT c.*, u.username, u.real_name, u.avatar
            FROM community_comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.post_id = ?
            ORDER BY c.parent_id IS NULL DESC, c.created_at ASC
        ''', (post_id,))
        comments = cursor.fetchall()
        conn.close()
        return [dict(c) for c in comments]

    def toggle_like(self, target_type, target_id, user_id):
        """点赞/取消点赞"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id FROM community_likes WHERE target_type = ? AND target_id = ? AND user_id = ?
        ''', (target_type, target_id, user_id))
        existing = cursor.fetchone()
        if existing:
            cursor.execute('DELETE FROM community_likes WHERE id = ?', (existing[0],))
            liked = False
        else:
            cursor.execute('''
                INSERT INTO community_likes (target_type, target_id, user_id) VALUES (?, ?, ?)
            ''', (target_type, target_id, user_id))
            liked = True
        if target_type == 'post':
            cursor.execute('''
                UPDATE community_posts SET likes_count = (
                    SELECT COUNT(*) FROM community_likes WHERE target_type = 'post' AND target_id = ?
                ) WHERE id = ?
            ''', (target_id, target_id))
        elif target_type == 'comment':
            cursor.execute('''
                UPDATE community_comments SET likes_count = (
                    SELECT COUNT(*) FROM community_likes WHERE target_type = 'comment' AND target_id = ?
                ) WHERE id = ?
            ''', (target_id, target_id))
        conn.commit()
        conn.close()
        return liked

    def check_like_status(self, target_type, target_id, user_id):
        """检查是否已点赞"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 1 FROM community_likes WHERE target_type = ? AND target_id = ? AND user_id = ?
        ''', (target_type, target_id, user_id))
        result = cursor.fetchone()
        conn.close()
        return bool(result)

    def add_report(self, target_type, target_id, reporter_user_id, reason):
        """添加举报"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO community_reports (target_type, target_id, reporter_user_id, reason)
            VALUES (?, ?, ?, ?)
        ''', (target_type, target_id, reporter_user_id, reason))
        report_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return report_id

    def get_hot_tags(self, limit=10):
        """获取热门标签"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT tags FROM community_posts WHERE status = 'active' AND tags IS NOT NULL AND tags != ''
        ''')
        rows = cursor.fetchall()
        conn.close()
        from collections import Counter
        tag_counter = Counter()
        for row in rows:
            for tag in row[0].split(','):
                tag_counter[tag.strip()] += 1
        return [{'name': tag, 'count': count} for tag, count in tag_counter.most_common(limit)]

    def add_feedback(self, user_id, content, contact=None, category='general'):
        """添加用户反馈"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                content TEXT NOT NULL,
                contact TEXT,
                category TEXT DEFAULT 'general',
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            INSERT INTO user_feedback (user_id, content, contact, category)
            VALUES (?, ?, ?, ?)
        ''', (user_id, content, contact, category))
        feedback_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return feedback_id

    def get_user_settings(self, user_id):
        """获取用户设置"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                theme TEXT DEFAULT 'light',
                notification_enabled INTEGER DEFAULT 1,
                language TEXT DEFAULT 'zh',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('SELECT * FROM user_settings WHERE user_id = ?', (user_id,))
        settings = cursor.fetchone()
        if not settings:
            cursor.execute('INSERT INTO user_settings (user_id) VALUES (?)', (user_id,))
            conn.commit()
            cursor.execute('SELECT * FROM user_settings WHERE user_id = ?', (user_id,))
            settings = cursor.fetchone()
        conn.close()
        return dict(settings)

    def update_user_settings(self, user_id, **kwargs):
        """更新用户设置"""
        conn = self.connect()
        cursor = conn.cursor()
        allowed = ['theme', 'notification_enabled', 'language']
        updates = []
        values = []
        for field in allowed:
            if field in kwargs:
                updates.append(f"{field} = ?")
                values.append(kwargs[field])
        if updates:
            values.append(datetime.now())
            values.append(user_id)
            cursor.execute(f'''
                INSERT INTO user_settings (user_id) VALUES (?)
                ON CONFLICT(user_id) DO UPDATE SET
                {', '.join(updates)}, updated_at = ?
            ''', [user_id] + values)
            conn.commit()
        conn.close()
