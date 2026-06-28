from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import hashlib
import os
import sys
import base64
from datetime import datetime
from database import DatabaseManager
from matching_engine import AdvancedMatchingEngine
from ai_service import AIService
import jwt
from functools import wraps
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# ========== 路径解析（兼容PyInstaller打包） ==========
def _get_app_root():
    """获取应用根目录，兼容开发环境和PyInstaller打包"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        # 开发环境: code/的父目录（项目根目录）
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _get_resource_dir():
    """获取资源文件目录（前端等）"""
    if getattr(sys, 'frozen', False):
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass and os.path.isdir(os.path.join(meipass, 'frontend')):
            return meipass
        internal = os.path.join(_get_app_root(), '_internal')
        if os.path.isdir(os.path.join(internal, 'frontend')):
            return internal
        return _get_app_root()
    else:
        # 开发环境: 当前py文件所在目录（code/）
        return os.path.dirname(os.path.abspath(__file__))

APP_ROOT = _get_app_root()
RESOURCE_DIR = _get_resource_dir()
FRONTEND_DIR = os.path.join(RESOURCE_DIR, 'frontend')
DB_PATH = os.path.join(APP_ROOT, 'match_system.db')

# 关键修复：首次运行时，将打包的数据库从临时目录复制到exe同级目录
if not os.path.exists(DB_PATH):
    # 查找打包的数据库文件
    bundled_db = os.path.join(RESOURCE_DIR, 'match_system.db')
    if os.path.exists(bundled_db):
        import shutil
        try:
            shutil.copy2(bundled_db, DB_PATH)
            print(f'数据库已从 {bundled_db} 复制到 {DB_PATH}')
        except Exception as e:
            print(f'数据库复制失败: {e}')
    else:
        print(f'未找到打包的数据库文件（查找路径: {bundled_db}），将自动创建新数据库')
else:
    print(f'使用已有数据库: {DB_PATH}')

app = Flask(__name__, static_folder=FRONTEND_DIR, template_folder=FRONTEND_DIR)
app.config['SECRET_KEY'] = 'campus_lost_found_secret_key_2024'
CORS(app)

# AES加密密钥（32字节，实际项目中应从安全配置中读取）
AES_SECRET_KEY = b'campus_lost_found_aes_key_2024!!'  # 32字节
AES_IV = b'campus_aes_iv_16byte!'  # 16字节初始化向量

# 初始化组件
db = DatabaseManager(db_path=DB_PATH)
matching_engine = AdvancedMatchingEngine()
ai_service = AIService()

# ==================== 工具函数 ====================

def token_required(f):
    """JWT认证装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'code': 401, 'message': '缺少认证令牌'}), 401

        try:
            token = token.replace('Bearer ', '')
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = db.get_user_by_id(data['user_id'])
            if not current_user:
                return jsonify({'code': 401, 'message': '用户不存在'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'code': 401, 'message': '令牌已过期'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'code': 401, 'message': '无效令牌'}), 401

        return f(current_user, *args, **kwargs)
    return decorated


def admin_required(f):
    """管理员权限装饰器"""
    @wraps(f)
    def decorated(current_user, *args, **kwargs):
        if current_user.get('role') != 'admin':
            return jsonify({'code': 403, 'message': '需要管理员权限'}), 403
        return f(current_user, *args, **kwargs)
    return decorated


def hash_password(password):
    """密码哈希"""
    return hashlib.sha256(password.encode()).hexdigest()


def generate_token(user_id):
    """生成JWT令牌"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow().timestamp() + 86400  # 24小时过期
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')


def aes_encrypt(plaintext):
    """AES加密数据"""
    cipher = AES.new(AES_SECRET_KEY, AES.MODE_CBC, AES_IV)
    padded_data = pad(plaintext.encode('utf-8'), AES.block_size)
    encrypted = cipher.encrypt(padded_data)
    return base64.b64encode(encrypted).decode('utf-8')


def aes_decrypt(ciphertext):
    """AES解密数据"""
    cipher = AES.new(AES_SECRET_KEY, AES.MODE_CBC, AES_IV)
    encrypted_data = base64.b64decode(ciphertext)
    decrypted = unpad(cipher.decrypt(encrypted_data), AES.block_size)
    return decrypted.decode('utf-8')


# ==================== 页面路由 ====================

@app.route('/')
def index():
    """首页"""
    return send_from_directory(FRONTEND_DIR, 'mvp.html')


@app.route('/<path:path>')
def static_files(path):
    """静态文件服务"""
    return send_from_directory(FRONTEND_DIR, path)


# ==================== 认证相关API ====================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.get_json()
    required = ['username', 'password', 'real_name']
    if not all(k in data for k in required):
        return jsonify({'code': 400, 'message': '缺少必填项'}), 400

    # 检查用户名是否已存在
    if db.get_user_by_username(data['username']):
        return jsonify({'code': 409, 'message': '用户名已存在'}), 409

    user_id = db.add_user(
        username=data['username'],
        password_hash=hash_password(data['password']),
        real_name=data['real_name'],
        email=data.get('email'),
        phone=data.get('phone'),
        student_id=data.get('student_id')
    )

    token = generate_token(user_id)

    return jsonify({
        'code': 200,
        'message': '注册成功',
        'token': token,
        'user': {
            'id': user_id,
            'username': data['username'],
            'real_name': data['real_name']
        }
    }), 200


@app.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'code': 400, 'message': '缺少参数'}), 400

    user = db.get_user_by_username(data['username'])

    if user and user['password_hash'] == hash_password(data['password']):
        token = generate_token(user['id'])
        return jsonify({
            'code': 200,
            'message': '登录成功',
            'token': token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'real_name': user['real_name'],
                'email': user.get('email'),
                'phone': user.get('phone'),
                'credit_score': user['credit_score'],
                'role': user['role']
            }
        }), 200
    else:
        return jsonify({'code': 401, 'message': '用户名或密码错误'}), 401


@app.route('/api/auth/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    """获取用户信息"""
    return jsonify({
        'code': 200,
        'data': {
            'id': current_user['id'],
            'username': current_user['username'],
            'real_name': current_user['real_name'],
            'email': current_user.get('email'),
            'phone': current_user.get('phone'),
            'student_id': current_user.get('student_id'),
            'credit_score': current_user['credit_score'],
            'role': current_user['role'],
            'avatar': current_user.get('avatar')
        }
    }), 200


@app.route('/api/auth/profile', methods=['PUT'])
@token_required
def update_profile(current_user):
    """更新用户信息"""
    data = request.get_json()

    allowed_fields = ['email', 'phone', 'real_name', 'avatar']
    update_data = {k: v for k, v in data.items() if k in allowed_fields}

    db.update_user(current_user['id'], **update_data)

    return jsonify({'code': 200, 'message': '更新成功'}), 200


# ========== 个人中心兼容路由（前端使用驼峰命名） ==========

@app.route('/api/users/me', methods=['GET'])
@token_required
def get_users_me(current_user):
    """获取用户信息（驼峰别名，兼容前端）"""
    return jsonify({
        'code': 200,
        'data': {
            'id': current_user['id'],
            'username': current_user['username'],
            'realName': current_user['real_name'],
            'real_name': current_user['real_name'],
            'email': current_user.get('email'),
            'phone': current_user.get('phone'),
            'studentId': current_user.get('student_id'),
            'student_id': current_user.get('student_id'),
            'creditScore': current_user['credit_score'],
            'credit_score': current_user['credit_score'],
            'role': current_user['role'],
            'avatar': current_user.get('avatar')
        }
    }), 200


@app.route('/api/users/me', methods=['PUT'])
@token_required
def update_users_me(current_user):
    """更新用户信息（驼峰别名，兼容前端）"""
    data = request.get_json()
    allowed_fields_mapping = {
        'realName': 'real_name', 'real_name': 'real_name',
        'studentId': 'student_id', 'student_id': 'student_id',
        'email': 'email', 'phone': 'phone', 'avatar': 'avatar'
    }
    update_data = {}
    for front_key, db_key in allowed_fields_mapping.items():
        if front_key in data:
            update_data[db_key] = data[front_key]
    db.update_user(current_user['id'], **update_data)
    return jsonify({'code': 200, 'message': '更新成功'}), 200


@app.route('/api/items/my', methods=['GET'])
@token_required
def get_my_items(current_user):
    """获取当前用户的所有物品"""
    lost = db.get_lost_items(user_id=current_user['id'])
    found = db.get_found_items(user_id=current_user['id'])
    all_items = []
    for item in (lost or []):
        all_items.append({
            'id': item['id'], 'type': 'lost',
            'itemName': item['name'], 'name': item['name'],
            'item_name': item['name'],
            'category': item['category'],
            'description': item['description'],
            'location': item['location'],
            'status': item.get('status', 'pending'),
            'createdAt': item.get('created_at'),
            'created_at': item.get('created_at')
        })
    for item in (found or []):
        all_items.append({
            'id': item['id'], 'type': 'found',
            'itemName': item['name'], 'name': item['name'],
            'item_name': item['name'],
            'category': item['category'],
            'description': item['description'],
            'location': item['location'],
            'status': item.get('status', 'pending'),
            'createdAt': item.get('created_at'),
            'created_at': item.get('created_at')
        })
    # 支持 type 过滤
    req_type = request.args.get('type')
    if req_type:
        all_items = [i for i in all_items if i['type'] == req_type]
    # 按时间排序
    all_items.sort(key=lambda x: x.get('created_at') or '', reverse=True)
    return jsonify({'code': 200, 'data': all_items}), 200


@app.route('/api/notifications/read-all', methods=['POST'])
@token_required
def read_all_notifications(current_user):
    """标记所有通知为已读"""
    db.mark_all_notifications_read(current_user['id'])
    return jsonify({'code': 200, 'message': '已全部标记为已读'}), 200


@app.route('/api/claims/<int:claim_id>/cancel', methods=['POST'])
@token_required
def cancel_claim(current_user, claim_id):
    """取消认领申请（仅限待审核状态）"""
    claim = db.get_claim_by_id(claim_id)
    if not claim:
        return jsonify({'code': 404, 'message': '认领记录不存在'}), 404
    if claim['claimant_user_id'] != current_user['id']:
        return jsonify({'code': 403, 'message': '无权操作此认领'}), 403
    if claim['status'] != 'pending':
        return jsonify({'code': 400, 'message': '仅待审核状态的认领可以取消'}), 400
    db.update_claim_status(claim_id, 'cancelled', current_user['id'])
    return jsonify({'code': 200, 'message': '认领已取消'}), 200


@app.route('/api/credit/rules', methods=['GET'])
def get_credit_rules():
    """获取积分规则"""
    rules = [
        {'action': 'publish_lost', 'name': '发布失物', 'points': 2},
        {'action': 'publish_found', 'name': '发布招领', 'points': 3},
        {'action': 'confirm_match', 'name': '确认匹配', 'points': 10},
        {'action': 'successful_claim', 'name': '成功认领', 'points': 5},
        {'action': 'daily_login', 'name': '每日登录', 'points': 1},
        {'action': 'referral', 'name': '推荐他人使用', 'points': 5},
    ]
    return jsonify({'code': 200, 'data': rules}), 200


# ==================== 社区功能API ====================

@app.route('/api/community/posts', methods=['GET'])
def get_community_posts():
    """获取社区帖子列表，支持分类、搜索、排序"""
    category = request.args.get('category')
    search = request.args.get('search')
    sort = request.args.get('sort', 'latest')
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    posts = db.get_community_posts(category=category, search=search, sort=sort, limit=limit, offset=offset)
    return jsonify({'code': 200, 'data': posts}), 200


@app.route('/api/community/posts', methods=['POST'])
@token_required
def create_community_post(current_user):
    """发布社区帖子"""
    data = request.get_json()
    if not data or not data.get('content'):
        return jsonify({'code': 400, 'message': '内容不能为空'}), 400
    post_id = db.add_community_post(
        user_id=current_user['id'],
        content=data['content'],
        title=data.get('title'),
        images=data.get('images'),
        category=data.get('category', 'general'),
        tags=data.get('tags')
    )
    return jsonify({'code': 200, 'message': '发布成功', 'data': {'id': post_id}}), 200


@app.route('/api/community/posts/my', methods=['GET'])
@token_required
def get_my_community_posts(current_user):
    """获取我的帖子"""
    posts = db.get_my_community_posts(current_user['id'])
    return jsonify({'code': 200, 'data': posts}), 200


@app.route('/api/community/posts/<int:post_id>', methods=['GET'])
def get_community_post_detail(post_id):
    """获取帖子详情"""
    post = db.get_community_post_by_id(post_id)
    if not post:
        return jsonify({'code': 404, 'message': '帖子不存在'}), 404
    comments = db.get_comments_by_post(post_id)
    return jsonify({'code': 200, 'data': {'post': post, 'comments': comments}}), 200


@app.route('/api/community/posts/<int:post_id>', methods=['DELETE'])
@token_required
def delete_community_post(current_user, post_id):
    """删除帖子"""
    db.delete_community_post(post_id, current_user['id'])
    return jsonify({'code': 200, 'message': '已删除'}), 200


@app.route('/api/community/posts/<int:post_id>/comments', methods=['POST'])
@token_required
def add_post_comment(current_user, post_id):
    """发表评论"""
    data = request.get_json()
    if not data or not data.get('content'):
        return jsonify({'code': 400, 'message': '评论内容不能为空'}), 400
    comment_id = db.add_comment(
        post_id=post_id,
        user_id=current_user['id'],
        content=data['content'],
        parent_id=data.get('parent_id')
    )
    # 通知帖子作者
    try:
        post = db.get_community_post_by_id(post_id)
        if post and post['user_id'] != current_user['id']:
            db.add_notification(
                user_id=post['user_id'],
                type='comment',
                title='新评论',
                content=f'{current_user.get("real_name") or current_user.get("username")} 评论了你的帖子',
                related_item_id=post_id,
                related_item_type='community_post'
            )
    except Exception as e:
        print(f'评论通知发送失败: {e}')
    return jsonify({'code': 200, 'message': '评论成功', 'data': {'id': comment_id}}), 200


@app.route('/api/community/posts/<int:post_id>/like', methods=['POST'])
@token_required
def like_post(current_user, post_id):
    """点赞/取消点赞帖子"""
    liked = db.toggle_like('post', post_id, current_user['id'])
    return jsonify({'code': 200, 'message': '已点赞' if liked else '已取消点赞', 'data': {'liked': liked}}), 200


@app.route('/api/community/posts/<int:post_id>/like-status', methods=['GET'])
@token_required
def get_post_like_status(current_user, post_id):
    """获取点赞状态"""
    liked = db.check_like_status('post', post_id, current_user['id'])
    return jsonify({'code': 200, 'data': {'liked': liked}}), 200


@app.route('/api/community/comments/<int:comment_id>/like', methods=['POST'])
@token_required
def like_comment(current_user, comment_id):
    """点赞/取消点赞评论"""
    liked = db.toggle_like('comment', comment_id, current_user['id'])
    return jsonify({'code': 200, 'message': '已点赞' if liked else '已取消点赞', 'data': {'liked': liked}}), 200


@app.route('/api/community/posts/<int:post_id>/report', methods=['POST'])
@token_required
def report_post(current_user, post_id):
    """举报帖子"""
    data = request.get_json()
    if not data or not data.get('reason'):
        return jsonify({'code': 400, 'message': '请填写举报原因'}), 400
    db.add_report('post', post_id, current_user['id'], data['reason'])
    return jsonify({'code': 200, 'message': '举报已提交，我们会尽快处理'}), 200


@app.route('/api/community/tags/hot', methods=['GET'])
def get_hot_tags():
    """获取热门标签"""
    tags = db.get_hot_tags(limit=15)
    return jsonify({'code': 200, 'data': tags}), 200


@app.route('/api/feedback', methods=['POST'])
@token_required
def submit_feedback(current_user):
    """提交用户反馈"""
    data = request.get_json()
    if not data or not data.get('content'):
        return jsonify({'code': 400, 'message': '反馈内容不能为空'}), 400
    feedback_id = db.add_feedback(
        user_id=current_user['id'],
        content=data['content'],
        contact=data.get('contact'),
        category=data.get('category', 'general')
    )
    return jsonify({'code': 200, 'message': '反馈已提交，感谢你的建议', 'data': {'id': feedback_id}}), 200


@app.route('/api/settings', methods=['GET'])
@token_required
def get_settings(current_user):
    """获取用户设置"""
    settings = db.get_user_settings(current_user['id'])
    return jsonify({'code': 200, 'data': settings}), 200


@app.route('/api/settings', methods=['PUT'])
@token_required
def update_settings(current_user):
    """更新用户设置"""
    data = request.get_json()
    db.update_user_settings(current_user['id'], **data)
    return jsonify({'code': 200, 'message': '设置已保存'}), 200


@app.route('/api/items/<int:item_id>', methods=['PUT'])
@token_required
def edit_my_item(current_user, item_id):
    """统一编辑物品（由前端判断类型）"""
    data = request.get_json()
    if not data:
        return jsonify({'code': 400, 'message': '缺少更新数据'}), 400
    # 尝试失物
    item = db.get_lost_item_by_id(item_id)
    if item and item['user_id'] == current_user['id']:
        allowed = ['name', 'category', 'description', 'location', 'location_detail', 'expected_reward', 'brand']
        update = {k: v for k, v in data.items() if k in allowed}
        if update:
            db.update_lost_item(item_id, **update)
        return jsonify({'code': 200, 'message': '更新成功'}), 200
    # 尝试招领
    item = db.get_found_item_by_id(item_id)
    if item and item['user_id'] == current_user['id']:
        allowed = ['name', 'category', 'description', 'location', 'location_detail']
        update = {k: v for k, v in data.items() if k in allowed}
        if update:
            db.update_found_item(item_id, **update)
        return jsonify({'code': 200, 'message': '更新成功'}), 200
    return jsonify({'code': 404, 'message': '物品不存在或无权限'}), 404


@app.route('/api/items/<int:item_id>', methods=['DELETE'])
@token_required
def delete_my_item(current_user, item_id):
    """统一删除物品"""
    item = db.get_lost_item_by_id(item_id)
    if item and item['user_id'] == current_user['id']:
        db.delete_lost_item(item_id)
        return jsonify({'code': 200, 'message': '已删除'}), 200
    item = db.get_found_item_by_id(item_id)
    if item and item['user_id'] == current_user['id']:
        db.delete_found_item(item_id)
        return jsonify({'code': 200, 'message': '已删除'}), 200
    return jsonify({'code': 404, 'message': '物品不存在或无权限'}), 404


@app.route('/api/auth/change-password', methods=['POST'])
@token_required
def change_password(current_user):
    """修改密码"""
    data = request.get_json()
    if not data or 'old_password' not in data or 'new_password' not in data:
        return jsonify({'code': 400, 'message': '缺少参数'}), 400

    # 验证旧密码
    if current_user['password_hash'] != hash_password(data['old_password']):
        return jsonify({'code': 400, 'message': '原密码错误'}), 400

    # 检查新密码长度
    if len(data['new_password']) < 6:
        return jsonify({'code': 400, 'message': '新密码长度不能少于6位'}), 400

    # 更新密码
    db.update_user(
        current_user['id'],
        password_hash=hash_password(data['new_password'])
    )

    return jsonify({'code': 200, 'message': '密码修改成功'}), 200


@app.route('/api/auth/encrypt-data', methods=['POST'])
@token_required
def encrypt_data(current_user):
    """加密数据接口（AES加密演示）"""
    data = request.get_json()
    if not data or 'plaintext' not in data:
        return jsonify({'code': 400, 'message': '缺少待加密数据'}), 400

    plaintext = data['plaintext']
    encrypted = aes_encrypt(plaintext)

    return jsonify({
        'code': 200,
        'message': '加密成功',
        'data': {
            'encrypted': encrypted,
            'algorithm': 'AES-CBC',
            'original_length': len(plaintext)
        }
    }), 200


# ==================== 第三方登录API ====================

@app.route('/api/auth/oauth/login', methods=['POST'])
def oauth_login():
    """第三方登录"""
    data = request.get_json()
    if not data or 'provider' not in data or 'provider_uid' not in data:
        return jsonify({'code': 400, 'message': '缺少第三方登录参数'}), 400

    provider = data['provider']
    provider_uid = data['provider_uid']
    access_token = data.get('access_token', '')

    # 查找已绑定的用户
    user = db.get_user_by_oauth(provider, provider_uid)

    if user:
        # 已绑定，直接登录
        token = generate_token(user['id'])
        return jsonify({
            'code': 200,
            'message': '第三方登录成功',
            'token': token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'real_name': user['real_name'],
                'email': user.get('email'),
                'phone': user.get('phone'),
                'credit_score': user['credit_score'],
                'role': user['role']
            },
            'is_bound': True
        }), 200
    else:
        # 未绑定，返回提示需要绑定已有账号或注册
        return jsonify({
            'code': 200,
            'message': '第三方账号未绑定，请先绑定已有账号或注册新账号',
            'is_bound': False,
            'provider': provider,
            'provider_uid': provider_uid
        }), 200


@app.route('/api/auth/oauth/bind', methods=['POST'])
@token_required
def oauth_bind(current_user):
    """绑定第三方账号"""
    data = request.get_json()
    if not data or 'provider' not in data or 'provider_uid' not in data:
        return jsonify({'code': 400, 'message': '缺少绑定参数'}), 400

    provider = data['provider']
    provider_uid = data['provider_uid']
    access_token = data.get('access_token', '')

    # 检查该第三方账号是否已被其他用户绑定
    existing_user = db.get_user_by_oauth(provider, provider_uid)
    if existing_user:
        return jsonify({'code': 409, 'message': '该第三方账号已被其他用户绑定'}), 409

    # 执行绑定
    db.link_oauth_account(
        user_id=current_user['id'],
        provider=provider,
        provider_uid=provider_uid,
        access_token=access_token
    )

    return jsonify({'code': 200, 'message': '第三方账号绑定成功'}), 200


@app.route('/api/auth/oauth/unbind', methods=['DELETE'])
@token_required
def oauth_unbind(current_user):
    """解绑第三方账号"""
    data = request.get_json() or {}
    provider = data.get('provider')
    if not provider:
        # 也支持从query参数获取
        provider = request.args.get('provider')

    if not provider:
        return jsonify({'code': 400, 'message': '缺少provider参数'}), 400

    db.unlink_oauth_account(current_user['id'], provider)

    return jsonify({'code': 200, 'message': '第三方账号解绑成功'}), 200


# ==================== 失物相关API ====================

@app.route('/api/lost-items', methods=['POST'])
@token_required
def add_lost_item(current_user):
    """添加失物信息"""
    data = request.get_json()
    required = ['name', 'category', 'description', 'lost_time', 'location']
    if not all(k in data for k in required):
        return jsonify({'code': 400, 'message': '缺少必填项'}), 400

    item_id = db.add_lost_item(
        user_id=current_user['id'],
        name=data['name'],
        category=data['category'],
        sub_category=data.get('sub_category'),
        brand=data.get('brand'),
        description=data['description'],
        lost_time=data['lost_time'],
        location=data['location'],
        location_detail=data.get('location_detail'),
        latitude=data.get('latitude'),
        longitude=data.get('longitude'),
        images=data.get('images'),
        expected_reward=min(max(float(data.get('expected_reward') or 0), 0), 500),
        urgency_level=data.get('urgency_level', 'normal')
    )

    # 自动匹配
    found_items = db.get_found_items(status='pending')
    if found_items:
        lost_item = db.get_lost_item_by_id(item_id)
        matches = matching_engine.batch_match(lost_item, found_items)

        for i, match in enumerate(matches[:5]):
            db.add_match(
                lost_item_id=item_id,
                found_item_id=match['found_item']['id'],
                score=match['score'],
                text_score=match['details']['text'],
                time_score=match['details']['time'],
                location_score=match['details']['location'],
                rank=i+1
            )

    # 添加积分
    db.update_credit_score(
        current_user['id'],
        5,
        'publish_lost',
        '发布失物信息',
        item_id
    )

    return jsonify({
        'code': 200,
        'message': '失物登记成功',
        'item_id': item_id
    }), 200


@app.route('/api/lost-items', methods=['GET'])
def get_lost_items():
    """获取失物列表"""
    status = request.args.get('status')
    category = request.args.get('category')
    user_id = request.args.get('user_id', type=int)
    limit = request.args.get('limit', type=int)
    offset = request.args.get('offset', type=int)

    items = db.get_lost_items(
        status=status,
        category=category,
        user_id=user_id,
        limit=limit,
        offset=offset
    )

    return jsonify({'code': 200, 'data': items}), 200


@app.route('/api/lost-items/<int:item_id>', methods=['GET'])
def get_lost_item(item_id):
    """获取失物详情"""
    item = db.get_lost_item_by_id(item_id)
    if not item:
        return jsonify({'code': 404, 'message': '物品不存在'}), 404

    # 增加浏览次数
    db.increment_lost_view_count(item_id)

    # 获取匹配结果
    matches = db.get_matches_for_lost_item(item_id)

    return jsonify({
        'code': 200,
        'data': {
            'item': item,
            'matches': matches
        }
    }), 200


@app.route('/api/lost-items/<int:item_id>', methods=['PUT'])
@token_required
def edit_lost_item(current_user, item_id):
    """编辑失物信息"""
    item = db.get_lost_item_by_id(item_id)
    if not item:
        return jsonify({'code': 404, 'message': '物品不存在'}), 404

    # 只有发布者本人或管理员可以编辑
    if item['user_id'] != current_user['id'] and current_user.get('role') != 'admin':
        return jsonify({'code': 403, 'message': '无权编辑此物品'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'code': 400, 'message': '缺少更新数据'}), 400

    # 允许编辑的字段
    allowed_fields = [
        'name', 'category', 'brand', 'description',
        'lost_time', 'location', 'location_detail',
        'latitude', 'longitude', 'images',
        'expected_reward', 'urgency_level'
    ]
    update_data = {k: v for k, v in data.items() if k in allowed_fields}

    if not update_data:
        return jsonify({'code': 400, 'message': '没有有效的更新字段'}), 400

    db.update_lost_item(item_id, **update_data)

    return jsonify({'code': 200, 'message': '失物信息更新成功'}), 200


@app.route('/api/lost-items/<int:item_id>', methods=['DELETE'])
@token_required
def delete_lost_item(current_user, item_id):
    """删除失物"""
    item = db.get_lost_item_by_id(item_id)
    if not item:
        return jsonify({'code': 404, 'message': '物品不存在'}), 404

    # 只有发布者本人或管理员可以删除
    if item['user_id'] != current_user['id'] and current_user.get('role') != 'admin':
        return jsonify({'code': 403, 'message': '无权删除此物品'}), 403

    db.delete_lost_item(item_id)

    return jsonify({'code': 200, 'message': '失物已删除'}), 200


@app.route('/api/admin/lost-items/<int:item_id>/audit', methods=['POST'])
@token_required
@admin_required
def audit_lost_item(current_user, item_id):
    """审核失物（管理员）"""
    item = db.get_lost_item_by_id(item_id)
    if not item:
        return jsonify({'code': 404, 'message': '物品不存在'}), 404

    data = request.get_json()
    if not data or 'status' not in data:
        return jsonify({'code': 400, 'message': '缺少审核状态参数'}), 400

    status = data['status']
    reason = data.get('reason', '')

    if status not in ('approved', 'rejected'):
        return jsonify({'code': 400, 'message': '审核状态无效，只能是approved或rejected'}), 400

    db.audit_lost_item(item_id, status, reason)

    return jsonify({'code': 200, 'message': f'失物审核{"通过" if status == "approved" else "已拒绝"}'}), 200


# ==================== 招领相关API ====================

@app.route('/api/found-items', methods=['POST'])
@token_required
def add_found_item(current_user):
    """添加招领信息"""
    data = request.get_json()
    required = ['name', 'category', 'description', 'found_time', 'location', 'storage_method', 'contact_methods']
    if not all(k in data for k in required):
        return jsonify({'code': 400, 'message': '缺少必填项'}), 400

    item_id = db.add_found_item(
        user_id=current_user['id'],
        name=data['name'],
        category=data['category'],
        sub_category=data.get('sub_category'),
        description=data['description'],
        found_time=data['found_time'],
        location=data['location'],
        location_detail=data.get('location_detail'),
        latitude=data.get('latitude'),
        longitude=data.get('longitude'),
        images=data.get('images'),
        storage_method=data['storage_method'],
        contact_methods=data['contact_methods']
    )

    # 自动匹配
    lost_items = db.get_lost_items(status='pending')
    if lost_items:
        found_item = db.get_found_item_by_id(item_id)
        for lost_item in lost_items:
            score, details = matching_engine.calculate_comprehensive_score(lost_item, found_item)
            if matching_engine.get_match_level(score) != 'none':
                db.add_match(
                    lost_item_id=lost_item['id'],
                    found_item_id=item_id,
                    score=score,
                    text_score=details['text'],
                    time_score=details['time'],
                    location_score=details['location']
                )

    # 添加积分
    db.update_credit_score(
        current_user['id'],
        10,
        'publish_found',
        '发布招领信息',
        item_id
    )

    return jsonify({
        'code': 200,
        'message': '招领登记成功',
        'item_id': item_id
    }), 200


@app.route('/api/found-items', methods=['GET'])
def get_found_items():
    """获取招领物品列表"""
    status = request.args.get('status')
    category = request.args.get('category')
    user_id = request.args.get('user_id', type=int)
    limit = request.args.get('limit', type=int)
    offset = request.args.get('offset', type=int)

    items = db.get_found_items(
        status=status,
        category=category,
        user_id=user_id,
        limit=limit,
        offset=offset
    )

    return jsonify({'code': 200, 'data': items}), 200


@app.route('/api/found-items/<int:item_id>', methods=['GET'])
def get_found_item(item_id):
    """获取招领详情"""
    item = db.get_found_item_by_id(item_id)
    if not item:
        return jsonify({'code': 404, 'message': '物品不存在'}), 404

    # 增加浏览次数
    db.increment_found_view_count(item_id)

    # 获取匹配结果
    matches = db.get_matches_for_found_item(item_id)

    return jsonify({
        'code': 200,
        'data': {
            'item': item,
            'matches': matches
        }
    }), 200


@app.route('/api/found-items/<int:item_id>', methods=['PUT'])
@token_required
def edit_found_item(current_user, item_id):
    """编辑招领信息"""
    item = db.get_found_item_by_id(item_id)
    if not item:
        return jsonify({'code': 404, 'message': '物品不存在'}), 404

    # 只有发布者本人或管理员可以编辑
    if item['user_id'] != current_user['id'] and current_user.get('role') != 'admin':
        return jsonify({'code': 403, 'message': '无权编辑此物品'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'code': 400, 'message': '缺少更新数据'}), 400

    # 允许编辑的字段
    allowed_fields = [
        'name', 'category', 'description',
        'found_time', 'location', 'location_detail',
        'latitude', 'longitude', 'images',
        'storage_method', 'contact_methods'
    ]
    update_data = {k: v for k, v in data.items() if k in allowed_fields}

    if not update_data:
        return jsonify({'code': 400, 'message': '没有有效的更新字段'}), 400

    db.update_found_item(item_id, **update_data)

    return jsonify({'code': 200, 'message': '招领信息更新成功'}), 200


@app.route('/api/found-items/<int:item_id>', methods=['DELETE'])
@token_required
def delete_found_item(current_user, item_id):
    """删除招领"""
    item = db.get_found_item_by_id(item_id)
    if not item:
        return jsonify({'code': 404, 'message': '物品不存在'}), 404

    # 只有发布者本人或管理员可以删除
    if item['user_id'] != current_user['id'] and current_user.get('role') != 'admin':
        return jsonify({'code': 403, 'message': '无权删除此物品'}), 403

    db.delete_found_item(item_id)

    return jsonify({'code': 200, 'message': '招领已删除'}), 200


@app.route('/api/admin/found-items/<int:item_id>/audit', methods=['POST'])
@token_required
@admin_required
def audit_found_item(current_user, item_id):
    """审核招领（管理员）"""
    item = db.get_found_item_by_id(item_id)
    if not item:
        return jsonify({'code': 404, 'message': '物品不存在'}), 404

    data = request.get_json()
    if not data or 'status' not in data:
        return jsonify({'code': 400, 'message': '缺少审核状态参数'}), 400

    status = data['status']
    reason = data.get('reason', '')

    if status not in ('approved', 'rejected'):
        return jsonify({'code': 400, 'message': '审核状态无效，只能是approved或rejected'}), 400

    db.audit_found_item(item_id, status, reason)

    return jsonify({'code': 200, 'message': f'招领审核{"通过" if status == "approved" else "已拒绝"}'}), 200


# ==================== 统一物品列表API ====================

@app.route('/api/items', methods=['GET'])
def get_items():
    """统一物品列表接口（失物+招领混合）"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('pageSize', 20, type=int)
    keyword = request.args.get('keyword', '')
    item_type = request.args.get('type')        # lost / found / 空=全部
    category = request.args.get('category', '')
    location = request.args.get('location', '')
    sort = request.args.get('sort', 'latest')  # latest / urgency

    offset = (page - 1) * page_size

    # 搜索失物
    lost = []
    if item_type in (None, '', 'lost'):
        if keyword or category or location:
            result = db.search_items_advanced(
                keyword=keyword, item_type='lost', category=category,
                location=location, sort_by='created_at', sort_order='desc'
            )
            lost = result.get('lost', [])
        else:
            lost = db.get_lost_items(
                status='pending', category=category if category else None,
                limit=page_size, offset=0
            )

    # 搜索招领
    found = []
    if item_type in (None, '', 'found'):
        if keyword or category or location:
            result = db.search_items_advanced(
                keyword=keyword, item_type='found', category=category,
                location=location, sort_by='created_at', sort_order='desc'
            )
            found = result.get('found', [])
        else:
            found = db.get_found_items(
                status='pending', category=category if category else None,
                limit=page_size, offset=0
            )

    # 统一格式 - 使用下划线命名规范
    all_items = []
    for item in lost:
        all_items.append({
            'id': item['id'], 'type': 'lost',
            'item_name': item['name'], 'name': item['name'],
            'category': item['category'], 'sub_category': item.get('sub_category'),
            'brand': item.get('brand'),
            'description': item['description'],
            'location': item['location'], 'location_detail': item.get('location_detail'),
            'lost_time': item.get('lost_time'), 'found_time': None,
            'urgency_level': item.get('urgency_level'), 'urgency': item.get('urgency_level'),
            'expected_reward': item.get('expected_reward'), 'reward': item.get('expected_reward'),
            'view_count': item.get('view_count', 0), 'views': item.get('view_count', 0),
            'user_id': item['user_id'], 'userId': item['user_id'],
            'created_at': item.get('created_at'), 'createdAt': item.get('created_at'),
            'status': item.get('status')
        })
    for item in found:
        all_items.append({
            'id': item['id'], 'type': 'found',
            'item_name': item['name'], 'name': item['name'],
            'category': item['category'], 'sub_category': item.get('sub_category'),
            'brand': None,
            'description': item['description'],
            'location': item['location'], 'location_detail': item.get('location_detail'),
            'lost_time': None, 'found_time': item.get('found_time'),
            'urgency_level': None, 'urgency': None,
            'expected_reward': None, 'reward': None,
            'view_count': item.get('view_count', 0), 'views': item.get('view_count', 0),
            'user_id': item['user_id'], 'userId': item['user_id'],
            'created_at': item.get('created_at'), 'createdAt': item.get('created_at'),
            'status': item.get('status')
        })

    # 排序
    if sort == 'urgency':
        urgency_order = {'very_urgent': 0, 'urgent': 1, 'normal': 2}
        all_items.sort(key=lambda x: urgency_order.get(x.get('urgency'), 3))
    else:
        all_items.sort(key=lambda x: x.get('createdAt', ''), reverse=True)

    # 分页
    total = len(all_items)
    paged = all_items[offset:offset + page_size]
    total_pages = (total + page_size - 1) // page_size

    return jsonify({
        'code': 200,
        'items': paged,
        'total': total,
        'page': page,
        'pageSize': page_size,
        'totalPages': total_pages
    }), 200


@app.route('/api/items', methods=['POST'])
@token_required
def create_item(current_user):
    """统一物品发布接口（根据type自动分发到失物/招领）"""
    data = request.get_json()
    item_type = data.get('type')

    if item_type == 'lost':
        required = ['name', 'category', 'description', 'lost_time', 'location']
        if not all(k in data for k in required):
            return jsonify({'code': 400, 'message': '缺少必填项'}), 400

        item_id = db.add_lost_item(
            user_id=current_user['id'],
            name=data['name'],
            category=data['category'],
            sub_category=data.get('sub_category'),
            brand=data.get('brand'),
            description=data['description'],
            lost_time=data['lost_time'],
            location=data['location'],
            location_detail=data.get('location_detail'),
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            images=data.get('images'),
            expected_reward=min(max(float(data.get('expected_reward') or 0), 0), 500),
            urgency_level=data.get('urgency_level', 'normal')
        )
        # 自动匹配
        found_items = db.get_found_items(status='pending')
        if found_items:
            lost_item = db.get_lost_item_by_id(item_id)
            matches = matching_engine.batch_match(lost_item, found_items)
            for i, match in enumerate(matches[:5]):
                db.add_match(
                    lost_item_id=item_id,
                    found_item_id=match['found_item']['id'],
                    score=match['score'],
                    text_score=match['details']['text'],
                    time_score=match['details']['time'],
                    location_score=match['details']['location'],
                    rank=i+1
                )
        db.update_credit_score(current_user['id'], 5, 'publish_lost', f'发布失物：{data["name"]}')

    elif item_type == 'found':
        required = ['name', 'category', 'description', 'found_time', 'location', 'storage_method', 'contact_methods']
        if not all(k in data for k in required):
            return jsonify({'code': 400, 'message': '缺少必填项'}), 400

        item_id = db.add_found_item(
            user_id=current_user['id'],
            name=data['name'],
            category=data['category'],
            sub_category=data.get('sub_category'),
            description=data['description'],
            found_time=data['found_time'],
            location=data['location'],
            location_detail=data.get('location_detail'),
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            images=data.get('images'),
            storage_method=data['storage_method'],
            contact_methods=data['contact_methods']
        )
        # 自动匹配
        lost_items = db.get_lost_items(status='pending')
        if lost_items:
            found_item = db.get_found_item_by_id(item_id)
            for lost_item in lost_items:
                score, details = matching_engine.calculate_comprehensive_score(lost_item, found_item)
                if score >= 30:
                    db.add_match(
                        lost_item_id=lost_item['id'],
                        found_item_id=item_id,
                        score=score,
                        text_score=details['text'],
                        time_score=details['time'],
                        location_score=details['location'],
                        rank=1
                    )
        db.update_credit_score(current_user['id'], 5, 'publish_found', f'发布招领：{data["name"]}')

    else:
        return jsonify({'code': 400, 'message': '类型错误，type只能是lost或found'}), 400

    return jsonify({
        'code': 200,
        'message': '发布成功',
        'data': {'id': item_id, 'type': item_type}
    }), 200


@app.route('/api/items/recent', methods=['GET'])
def get_recent_items():
    """获取最近物品动态"""
    limit = request.args.get('limit', 10, type=int)
    lost_items = db.get_lost_items(limit=limit)
    found_items = db.get_found_items(limit=limit)

    combined = []
    for item in (lost_items or []):
        item['type'] = 'lost'
        item['item_name'] = item['name']
        combined.append(item)
    for item in (found_items or []):
        item['type'] = 'found'
        item['item_name'] = item['name']
        combined.append(item)

    combined.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    return jsonify({
        'code': 200,
        'data': combined[:limit]
    }), 200


def _normalize_item(item, item_type):
    """统一物品字段格式"""
    item['type'] = item_type
    item['item_name'] = item['name']
    item['itemName'] = item['name']
    item['sub_category'] = item.get('sub_category')
    item['location_detail'] = item.get('location_detail')
    item['lost_time'] = item.get('lost_time')
    item['found_time'] = item.get('found_time')
    item['urgency_level'] = item.get('urgency_level')
    item['urgency'] = item.get('urgency_level')
    item['expected_reward'] = item.get('expected_reward')
    item['reward'] = item.get('expected_reward')
    item['view_count'] = item.get('view_count', 0)
    item['views'] = item.get('view_count', 0)
    item['user_id'] = item.get('user_id')
    item['userId'] = item.get('user_id')
    item['created_at'] = item.get('created_at')
    item['createdAt'] = item.get('created_at')
    item['updated_at'] = item.get('updated_at')
    item['updatedAt'] = item.get('updated_at')
    return item


@app.route('/api/items/<int:item_id>', methods=['GET'])
def get_item_detail(item_id):
    """统一物品详情接口"""
    # 先查失物
    item = db.get_lost_item_by_id(item_id)
    if item:
        item = _normalize_item(item, 'lost')
        matches = db.get_matches_for_lost_item(item_id)
        return jsonify({'code': 200, 'data': {**item, 'matches': matches}}), 200

    # 再查招领
    item = db.get_found_item_by_id(item_id)
    if item:
        item = _normalize_item(item, 'found')
        matches = db.get_matches_for_found_item(item_id)
        return jsonify({'code': 200, 'data': {**item, 'matches': matches}}), 200

    return jsonify({'code': 404, 'message': '物品不存在'}), 404


# ==================== 认领管理API ====================

@app.route('/api/claims', methods=['POST'])
@token_required
def submit_claim(current_user):
    """提交认领申请"""
    data = request.get_json()
    required = ['item_type', 'item_id', 'description']
    if not all(k in data for k in required):
        return jsonify({'code': 400, 'message': '缺少必填项（item_type, item_id, description）'}), 400

    if data['item_type'] not in ('lost', 'found'):
        return jsonify({'code': 400, 'message': 'item_type只能是lost或found'}), 400

    claim_id = db.add_claim(
        claimant_user_id=current_user['id'],
        item_type=data['item_type'],
        item_id=data['item_id'],
        description=data['description'],
        proof_images=data.get('proof_images')
    )

    return jsonify({
        'code': 200,
        'message': '认领申请提交成功',
        'claim_id': claim_id
    }), 200


@app.route('/api/claims/item/<item_type>/<int:item_id>', methods=['GET'])
@token_required
def get_item_claims(current_user, item_type, item_id):
    """获取物品的认领记录"""
    if item_type not in ('lost', 'found'):
        return jsonify({'code': 400, 'message': 'item_type只能是lost或found'}), 400

    claims = db.get_claims_by_item(item_type, item_id)

    return jsonify({'code': 200, 'data': claims}), 200


@app.route('/api/claims/my', methods=['GET'])
@token_required
def get_my_claims(current_user):
    """获取我的认领记录"""
    claims = db.get_claims_by_user(current_user['id'])

    return jsonify({'code': 200, 'data': claims}), 200


@app.route('/api/admin/claims', methods=['GET'])
@token_required
@admin_required
def get_all_claims(current_user):
    """获取所有认领记录（管理员）"""
    status = request.args.get('status')
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)

    claims = db.get_all_claims(status=status, limit=limit, offset=offset)

    return jsonify({'code': 200, 'data': claims}), 200


@app.route('/api/admin/claims/<int:claim_id>/review', methods=['POST'])
@token_required
@admin_required
def review_claim(current_user, claim_id):
    """审核认领（管理员）"""
    claim = db.get_claim_by_id(claim_id)
    if not claim:
        return jsonify({'code': 404, 'message': '认领记录不存在'}), 404

    data = request.get_json()
    if not data or 'status' not in data:
        return jsonify({'code': 400, 'message': '缺少审核状态参数'}), 400

    status = data['status']
    note = data.get('note', '')

    if status not in ('approved', 'rejected'):
        return jsonify({'code': 400, 'message': '审核状态无效，只能是approved或rejected'}), 400

    db.review_claim(claim_id, status, current_user['id'], note)

    # 审核通过时加积分并通知
    if status == 'approved':
        try:
            claim_info = db.get_claim_by_id(claim_id)
            if claim_info:
                db.update_credit_score(
                    claim_info['claimant_user_id'], 5, 'successful_claim',
                    '认领审核通过奖励', claim_id
                )
                db.add_notification(
                    user_id=claim_info['claimant_user_id'],
                    type='claim',
                    title='认领申请已通过',
                    content='你的认领申请已通过审核，积分+5',
                    related_item_id=claim_id,
                    related_item_type='claim'
                )
        except Exception as e:
            print(f'认领审核通知失败: {e}')
    elif status == 'rejected':
        try:
            claim_info = db.get_claim_by_id(claim_id)
            if claim_info:
                db.add_notification(
                    user_id=claim_info['claimant_user_id'],
                    type='claim',
                    title='认领申请被拒绝',
                    content=f'你的认领申请未通过审核。原因：{note or "无"}',
                    related_item_id=claim_id,
                    related_item_type='claim'
                )
        except Exception as e:
            print(f'认领拒绝通知失败: {e}')

    return jsonify({'code': 200, 'message': f'认领审核{"通过" if status == "approved" else "已拒绝"}'}), 200


@app.route('/api/claims/<int:claim_id>', methods=['GET'])
@token_required
def get_claim_detail(current_user, claim_id):
    """获取认领详情"""
    claim = db.get_claim_by_id(claim_id)
    if not claim:
        return jsonify({'code': 404, 'message': '认领记录不存在'}), 404

    return jsonify({'code': 200, 'data': claim}), 200


# ==================== 匹配相关API ====================

@app.route('/api/matches/find', methods=['POST'])
def find_matches():
    """查找匹配"""
    data = request.get_json()
    if not data or 'lost_item' not in data:
        return jsonify({'code': 400, 'message': '缺少参数'}), 400

    lost_item = data['lost_item']

    # 获取招领物品
    found_items = db.get_found_items(status='pending')

    # 执行匹配
    matches = matching_engine.get_top_matches(lost_item, found_items, top_n=5)

    result = []
    for match in matches:
        explanation = matching_engine.get_match_explanation(
            lost_item, match['found_item'], match['score'], match['details']
        )
        result.append({
            'found_item': match['found_item'],
            'score': match['score'],
            'match_level': match['match_level'],
            'match_level_text': match['match_level_text'],
            'explanation': explanation
        })

    return jsonify({'code': 200, 'data': result}), 200


@app.route('/api/matches/confirm', methods=['POST'])
@token_required
def confirm_match(current_user):
    """确认匹配"""
    data = request.get_json()
    if not data or 'match_id' not in data:
        return jsonify({'code': 400, 'message': '缺少参数'}), 400

    match_id = data['match_id']

    # 更新匹配状态
    db.update_match_status(match_id, 'confirmed')

    # 添加积分
    db.update_credit_score(
        current_user['id'],
        20,
        'confirm_match',
        '确认匹配成功'
    )

    # 发送通知给双方
    try:
        match_info = db.get_match_by_id(match_id)
        if match_info:
            lost_item = db.get_lost_item_by_id(match_info['lost_item_id'])
            found_item = db.get_found_item_by_id(match_info['found_item_id'])
            if lost_item and found_item:
                # 通知失物发布者
                db.add_notification(
                    user_id=lost_item['user_id'],
                    type='match',
                    title='匹配成功',
                    content=f'你的失物「{lost_item["name"]}」找到了匹配的招领信息',
                    related_item_id=match_id,
                    related_item_type='match'
                )
                # 通知招领发布者
                db.add_notification(
                    user_id=found_item['user_id'],
                    type='match',
                    title='匹配成功',
                    content=f'你发布的招领「{found_item["name"]}」找到了匹配的失物信息',
                    related_item_id=match_id,
                    related_item_type='match'
                )
    except Exception as e:
        print(f'通知发送失败: {e}')

    return jsonify({'code': 200, 'message': '匹配成功'}), 200


@app.route('/api/matches/reject', methods=['POST'])
@token_required
def reject_match(current_user):
    """拒绝匹配"""
    data = request.get_json()
    if not data or 'match_id' not in data:
        return jsonify({'code': 400, 'message': '缺少参数'}), 400

    match_id = data['match_id']
    reason = data.get('reason', '')

    # 更新匹配状态
    db.update_match_status(match_id, 'rejected')

    return jsonify({'code': 200, 'message': '已拒绝匹配'}), 200


# ==================== 搜索相关API ====================

@app.route('/api/search', methods=['GET'])
def search_items():
    """搜索物品（简单搜索）"""
    keyword = request.args.get('keyword', '')
    item_type = request.args.get('type')
    category = request.args.get('category')

    if not keyword:
        return jsonify({'code': 400, 'message': '缺少搜索关键词'}), 400

    results = db.search_items(keyword, item_type, category)

    return jsonify({'code': 200, 'data': results}), 200


@app.route('/api/search/advanced', methods=['GET'])
def search_items_advanced():
    """高级搜索（支持多条件组合、排序）"""
    keyword = request.args.get('keyword', '')
    item_type = request.args.get('type')
    category = request.args.get('category')
    location = request.args.get('location')
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')

    if not keyword:
        return jsonify({'code': 400, 'message': '缺少搜索关键词'}), 400

    results = db.search_items_advanced(
        keyword=keyword,
        item_type=item_type,
        category=category,
        location=location,
        start_time=start_time,
        end_time=end_time,
        sort_by=sort_by,
        sort_order=sort_order
    )

    return jsonify({'code': 200, 'data': results}), 200


# ==================== 统计相关API ====================

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取统计数据"""
    stats = db.get_statistics()
    stats['claim_rate'] = round(db.get_claim_success_rate() * 100, 1)

    return jsonify({
        'code': 200,
        'data': stats
    }), 200


@app.route('/api/stats/dashboard', methods=['GET'])
def get_dashboard_stats():
    """获取仪表盘统计数据"""
    stats = db.get_statistics()

    # 获取最近活动
    recent_lost = db.get_lost_items(limit=5)
    recent_found = db.get_found_items(limit=5)

    return jsonify({
        'code': 200,
        'data': {
            'overview': stats,
            'recent_lost': recent_lost,
            'recent_found': recent_found
        }
    }), 200


@app.route('/api/stats/claim-rate', methods=['GET'])
def get_claim_rate():
    """认领成功率统计（返回丰富格式）"""
    rate_data = db.get_claim_success_rate()
    total, success, pending = db.get_claim_counts()

    return jsonify({
        'code': 200,
        'data': {
            'rate': round(rate_data * 100, 1),
            'claim_rate': round(rate_data * 100, 1),
            'total': total,
            'claimed': success,
            'success': success,
            'pending': pending
        }
    }), 200


@app.route('/api/stats/high-frequency', methods=['GET'])
def get_high_frequency_items():
    """高频丢失物品统计"""
    limit = request.args.get('limit', 10, type=int)
    items = db.get_high_frequency_items(limit)

    return jsonify({
        'code': 200,
        'data': items
    }), 200


@app.route('/api/stats/hotspots', methods=['GET'])
def get_hotspot_locations():
    """丢失高发地点统计"""
    limit = request.args.get('limit', 10, type=int)
    locations = db.get_hotspot_locations(limit)

    return jsonify({
        'code': 200,
        'data': locations
    }), 200


@app.route('/api/stats/hourly', methods=['GET'])
def get_hourly_stats():
    """时段分布统计（24小时）"""
    hourly = db.get_hourly_distribution()

    return jsonify({
        'code': 200,
        'data': hourly
    }), 200


@app.route('/api/stats/recovery-time', methods=['GET'])
def get_recovery_time_stats():
    """找回时间分析"""
    recovery = db.get_recovery_time_distribution()

    return jsonify({
        'code': 200,
        'data': recovery
    }), 200


@app.route('/api/stats/trend', methods=['GET'])
def get_trend_data():
    """趋势数据统计"""
    days = request.args.get('days', 30, type=int)
    trend = db.get_trend_data(days)

    return jsonify({
        'code': 200,
        'data': trend
    }), 200


@app.route('/api/stats/monthly', methods=['GET'])
def get_monthly_stats():
    """月度统计"""
    monthly = db.get_monthly_stats()

    return jsonify({
        'code': 200,
        'data': monthly
    }), 200


# ==================== 分类和地点API ====================

@app.route('/api/categories', methods=['GET'])
def get_categories():
    """获取物品分类"""
    parent_id = request.args.get('parent_id', type=int)
    categories = db.get_categories(parent_id)

    return jsonify({'code': 200, 'data': categories}), 200


@app.route('/api/locations', methods=['GET'])
def get_locations():
    """获取地点列表"""
    locations = db.get_locations()

    return jsonify({'code': 200, 'data': locations}), 200


# ==================== 通知相关API ====================

@app.route('/api/notifications', methods=['GET'])
@token_required
def get_notifications(current_user):
    """获取用户通知"""
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'

    notifications = db.get_user_notifications(current_user['id'], unread_only)

    return jsonify({'code': 200, 'data': notifications}), 200


@app.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@token_required
def mark_notification_read(current_user, notification_id):
    """标记通知已读"""
    db.mark_notification_read(notification_id)

    return jsonify({'code': 200, 'message': '已标记为已读'}), 200


# ==================== 积分相关API ====================

@app.route('/api/credit/records', methods=['GET'])
@token_required
def get_credit_records(current_user):
    """获取积分记录"""
    limit = request.args.get('limit', 20, type=int)

    records = db.get_credit_records(current_user['id'], limit)

    return jsonify({
        'code': 200,
        'data': {
            'current_score': current_user['credit_score'],
            'records': records
        }
    }), 200


# ==================== 系统配置API ====================

@app.route('/api/configs', methods=['GET'])
def get_configs():
    """获取系统配置"""
    # 返回公开的配置项
    configs = {
        'site_name': db.get_config('site_name'),
        'reward_enabled': db.get_config('reward_enabled') == '1'
    }

    return jsonify({'code': 200, 'data': configs}), 200


# ==================== AI服务API ====================

@app.route('/api/ai/enhance-description', methods=['POST'])
def enhance_description():
    """增强物品描述"""
    data = request.get_json()
    if not data or 'description' not in data:
        return jsonify({'code': 400, 'message': '缺少描述'}), 400

    enhanced = ai_service.enhance_description(data['description'])

    return jsonify({
        'code': 200,
        'data': {
            'original': data['description'],
            'enhanced': enhanced
        }
    }), 200


@app.route('/api/ai/predict-category', methods=['POST'])
def predict_category():
    """预测物品类别"""
    data = request.get_json()
    if not data:
        return jsonify({'code': 400, 'message': '缺少参数'}), 400

    result = ai_service.predict_item_category(
        image=data.get('image'),
        text=data.get('description') or data.get('text')
    )

    return jsonify({
        'code': 200,
        'data': result
    }), 200


# ==================== AI助手对话API ====================

@app.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    """AI助手对话"""
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'code': 400, 'message': '缺少消息参数'}), 400

    message = data['message']
    context = data.get('context', {})
    user_id = context.get('user_id') if context else None

    try:
        result = ai_service.chat(message, user_id=user_id, context=context)

        return jsonify({
            'code': 200,
            'data': {
                'reply': result.get('reply', ''),
                'intent': result.get('intent', 'unknown'),
                'matched_pattern': result.get('matched_pattern'),
                'suggestions': result.get('suggestions', []),
                'actions': result.get('actions', [])
            }
        }), 200
    except Exception as e:
        return jsonify({'code': 500, 'message': f'AI对话失败：{str(e)}'}), 500


@app.route('/api/ai/smart-description', methods=['POST'])
def smart_description():
    """智能描述生成"""
    data = request.get_json()
    if not data or 'name' not in data or 'category' not in data:
        return jsonify({'code': 400, 'message': '缺少必填参数（name, category）'}), 400

    name = data['name']
    category = data['category']
    brand = data.get('brand')
    color = data.get('color')
    features = data.get('features')

    try:
        description = ai_service.generate_smart_description(
            item_name=name,
            category=category,
            brand=brand,
            color=color,
            features=features
        )
        keywords = ai_service.suggest_search_keywords(description)

        return jsonify({
            'code': 200,
            'data': {
                'description': description,
                'keywords': keywords
            }
        }), 200
    except Exception as e:
        return jsonify({'code': 500, 'message': f'智能描述生成失败：{str(e)}'}), 500


@app.route('/api/ai/match-reason', methods=['POST'])
def match_reason():
    """匹配原因分析"""
    data = request.get_json()
    if not data or 'lost_item' not in data or 'found_item' not in data or 'scores' not in data:
        return jsonify({'code': 400, 'message': '缺少必填参数（lost_item, found_item, scores）'}), 400

    lost_item = data['lost_item']
    found_item = data['found_item']
    scores = data['scores']

    try:
        reason_result = ai_service.generate_match_reason(lost_item, found_item, scores)
        reason = reason_result if isinstance(reason_result, str) else reason_result.get('reason', '')
        highlights = reason_result.get('highlights', []) if isinstance(reason_result, dict) else []

        return jsonify({
            'code': 200,
            'data': {
                'reason': reason,
                'highlights': highlights
            }
        }), 200
    except Exception as e:
        return jsonify({'code': 500, 'message': f'匹配原因分析失败：{str(e)}'}), 500


@app.route('/api/ai/trend-analysis', methods=['GET'])
def trend_analysis():
    """丢失趋势分析"""
    try:
        items = db.get_lost_items()
        trend_data = ai_service.analyze_lost_trends(items)

        return jsonify({
            'code': 200,
            'data': {
                'peak_hours': trend_data.get('peak_hours', []),
                'hot_locations': trend_data.get('hot_locations', []),
                'frequent_categories': trend_data.get('frequent_categories', [])
            }
        }), 200
    except Exception as e:
        return jsonify({'code': 500, 'message': f'趋势分析失败：{str(e)}'}), 500


@app.route('/api/ai/suggestions', methods=['GET'])
def ai_suggestions():
    """智能建议"""
    suggestion_type = request.args.get('type', 'claim')

    try:
        if suggestion_type == 'claim':
            item_type = request.args.get('item_type', '其他')
            item_category = request.args.get('item_category')
            suggestions = ai_service.get_claim_advice(
                item_type=item_type,
                item_category=item_category
            )
        elif suggestion_type == 'storage':
            item_type = request.args.get('item_type', '其他')
            item_category = request.args.get('item_category')
            suggestions = ai_service.recommend_storage_method(
                item_type=item_type,
                item_category=item_category
            )
        elif suggestion_type == 'keywords':
            description = request.args.get('description', '')
            if not description:
                return jsonify({'code': 400, 'message': 'keywords类型需要description参数'}), 400
            suggestions = ai_service.suggest_search_keywords(description)
        else:
            return jsonify({'code': 400, 'message': '无效的建议类型，支持：claim, storage, keywords'}), 400

        return jsonify({
            'code': 200,
            'data': {
                'type': suggestion_type,
                'suggestions': suggestions
            }
        }), 200
    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取建议失败：{str(e)}'}), 500


# ==================== 管理员API ====================

@app.route('/api/admin/users', methods=['GET'])
@token_required
@admin_required
def get_all_users(current_user):
    """获取所有用户（管理员，支持搜索和分页）"""
    search = request.args.get('search', '')
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)

    users = db.get_all_users(keyword=search, limit=limit, offset=offset)
    total = db.get_user_count()

    return jsonify({
        'code': 200,
        'data': {
            'users': users,
            'total': total,
            'limit': limit,
            'offset': offset
        }
    }), 200


@app.route('/api/admin/users/<int:user_id>/role', methods=['PUT'])
@token_required
@admin_required
def set_user_role(current_user, user_id):
    """设置用户角色（管理员）"""
    data = request.get_json()
    if not data or 'role' not in data:
        return jsonify({'code': 400, 'message': '缺少角色参数'}), 400

    role = data['role']
    if role not in ('user', 'admin', 'moderator'):
        return jsonify({'code': 400, 'message': '无效的角色，只能是user、admin或moderator'}), 400

    # 不能修改自己的角色
    if user_id == current_user['id']:
        return jsonify({'code': 400, 'message': '不能修改自己的角色'}), 400

    target_user = db.get_user_by_id(user_id)
    if not target_user:
        return jsonify({'code': 404, 'message': '目标用户不存在'}), 404

    db.set_user_role(user_id, role)

    return jsonify({'code': 200, 'message': f'用户角色已设置为{role}'}), 200


@app.route('/api/admin/users/<int:user_id>/ban', methods=['POST'])
@token_required
@admin_required
def ban_user(current_user, user_id):
    """封禁用户（管理员）"""
    target_user = db.get_user_by_id(user_id)
    if not target_user:
        return jsonify({'code': 404, 'message': '用户不存在'}), 404

    if user_id == current_user['id']:
        return jsonify({'code': 400, 'message': '不能封禁自己'}), 400

    if target_user.get('status') == 'banned':
        return jsonify({'code': 400, 'message': '用户已被封禁'}), 400

    db.ban_user(user_id)

    return jsonify({'code': 200, 'message': '用户已封禁'}), 200


@app.route('/api/admin/users/<int:user_id>/unban', methods=['POST'])
@token_required
@admin_required
def unban_user(current_user, user_id):
    """解封用户（管理员）"""
    target_user = db.get_user_by_id(user_id)
    if not target_user:
        return jsonify({'code': 404, 'message': '用户不存在'}), 404

    if target_user.get('status') != 'banned':
        return jsonify({'code': 400, 'message': '用户未被封禁'}), 400

    db.unban_user(user_id)

    return jsonify({'code': 200, 'message': '用户已解封'}), 200


@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_user(current_user, user_id):
    """删除用户（管理员）"""
    target_user = db.get_user_by_id(user_id)
    if not target_user:
        return jsonify({'code': 404, 'message': '用户不存在'}), 404

    if user_id == current_user['id']:
        return jsonify({'code': 400, 'message': '不能删除自己'}), 400

    db.delete_user(user_id)

    return jsonify({'code': 200, 'message': '用户已删除'}), 200


@app.route('/api/admin/stats', methods=['GET'])
@token_required
@admin_required
def get_admin_stats(current_user):
    """获取管理员统计数据"""
    stats = db.get_statistics()

    return jsonify({
        'code': 200,
        'data': stats
    }), 200


# ==================== 错误处理 ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'code': 404, 'message': '未找到'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'code': 500, 'message': '服务器内部错误'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
