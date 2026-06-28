const API_BASE_URL = 'http://localhost:8080/api/v1';

class App {
    constructor() {
        this.currentUser = null;
        this.lostItems = [];
        this.foundItems = [];
        this.recommendations = [];
        this.init();
    }

    init() {
        this.loadUserInfo();
        this.bindEvents();
        this.checkAuth();
    }

    bindEvents() {
        document.querySelectorAll('.nav a').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = e.target.getAttribute('data-page');
                this.navigateTo(page);
            });
        });

        document.getElementById('lostItemForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitLostItem();
        });

        document.getElementById('foundItemForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitFoundItem();
        });

        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const target = e.target.getAttribute('data-tab');
                this.switchTab(target);
            });
        });
    }

    checkAuth() {
        const token = localStorage.getItem('token');
        if (!token) {
            this.showLoginModal();
        }
    }

    loadUserInfo() {
        const userInfo = localStorage.getItem('userInfo');
        if (userInfo) {
            this.currentUser = JSON.parse(userInfo);
            this.updateUserUI();
        }
    }

    updateUserUI() {
        const userAvatar = document.querySelector('.user-avatar');
        const userName = document.querySelector('.user-name');
        if (userAvatar && this.currentUser) {
            userAvatar.textContent = this.currentUser.username?.charAt(0).toUpperCase() || 'U';
        }
        if (userName) {
            userName.textContent = this.currentUser?.username || '未登录';
        }
    }

    navigateTo(page) {
        document.querySelectorAll('.nav a').forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('data-page') === page) {
                link.classList.add('active');
            }
        });

        document.querySelectorAll('.page').forEach(p => {
            p.style.display = 'none';
        });

        const targetPage = document.getElementById(`${page}Page`);
        if (targetPage) {
            targetPage.style.display = 'block';
        }

        switch(page) {
            case 'home':
                this.loadHomePage();
                break;
            case 'lost':
                this.loadLostItems();
                break;
            case 'found':
                this.loadFoundItems();
                break;
            case 'match':
                this.loadRecommendations();
                break;
            case 'profile':
                this.loadProfile();
                break;
        }
    }

    loadHomePage() {
        this.loadStats();
        this.loadRecentItems();
    }

    async loadStats() {
        const stats = {
            totalLost: 156,
            totalFound: 89,
            matched: 67,
            pending: 23
        };

        document.querySelectorAll('.stat-value').forEach((el, index) => {
            const values = [stats.totalLost, stats.totalFound, stats.matched, stats.pending];
            el.textContent = values[index] || 0;
        });
    }

    async loadRecentItems() {
        const mockItems = [
            {
                id: '1',
                name: '蓝色钱包',
                category: '证件卡片',
                description: '蓝色皮革钱包，内有身份证和银行卡',
                time: '2026-04-25 14:30',
                location: '图书馆二楼',
                type: 'lost',
                image: null
            },
            {
                id: '2',
                name: '黑色笔记本电脑',
                category: '电子设备',
                description: '黑色联想笔记本电脑，有红色贴纸',
                time: '2026-04-25 10:00',
                location: '教学楼302室',
                type: 'found',
                image: null
            },
            {
                id: '3',
                name: '红色手机',
                category: '电子设备',
                description: '红色智能手机，屏幕有保护膜',
                time: '2026-04-24 16:00',
                location: '操场',
                type: 'lost',
                image: null
            },
            {
                id: '4',
                name: '绿色背包',
                category: '箱包',
                description: '绿色双肩背包，有学校标志',
                time: '2026-04-24 15:30',
                location: '食堂',
                type: 'found',
                image: null
            }
        ];

        const container = document.getElementById('recentItemsGrid');
        if (container) {
            container.innerHTML = mockItems.map(item => this.renderItemCard(item)).join('');
        }
    }

    renderItemCard(item) {
        const icon = this.getCategoryIcon(item.category);
        return `
            <div class="item-card" data-id="${item.id}">
                <div class="item-image">
                    ${icon}
                    <span class="item-badge ${item.type}">${item.type === 'lost' ? '寻物' : '招领'}</span>
                </div>
                <div class="item-content">
                    <h3 class="item-title">
                        ${item.name}
                        <span class="item-category">${item.category}</span>
                    </h3>
                    <p class="item-desc">${item.description}</p>
                    <div class="item-meta">
                        <span>📍 ${item.location}</span>
                        <span>🕐 ${item.time}</span>
                    </div>
                </div>
                <div class="item-actions">
                    <button class="btn btn-primary" onclick="app.viewItemDetail('${item.id}')">查看详情</button>
                    ${item.type === 'lost' ? 
                        '<button class="btn btn-secondary" onclick="app.findMatch(\'' + item.id + '\')">寻找匹配</button>' : 
                        '<button class="btn btn-secondary" onclick="app.viewMatches(\'' + item.id + '\')">查看匹配</button>'}
                </div>
            </div>
        `;
    }

    getCategoryIcon(category) {
        const icons = {
            '电子设备': '📱',
            '证件卡片': '🪪',
            '箱包': '🎒',
            '书籍文具': '📚',
            '服饰': '👕',
            '钥匙': '🔑',
            '其他': '📦'
        };
        return icons[category] || '📦';
    }

    viewItemDetail(id) {
        const item = [...this.lostItems, ...this.foundItems].find(i => i.id === id);
        if (item) {
            this.showModal('itemDetailModal', {
                title: item.name,
                content: `
                    <div class="item-detail">
                        <p><strong>类别：</strong>${item.category}</p>
                        <p><strong>描述：</strong>${item.description}</p>
                        <p><strong>${item.type === 'lost' ? '丢失' : '捡到'}时间：</strong>${item.time}</p>
                        <p><strong>${item.type === 'lost' ? '丢失' : '捡到'}地点：</strong>${item.location}</p>
                    </div>
                `
            });
        }
    }

    async loadLostItems() {
        const container = document.getElementById('lostItemsGrid');
        if (container) {
            container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
            
            setTimeout(() => {
                const mockLostItems = [
                    {
                        id: 'lost1',
                        name: '蓝色钱包',
                        category: '证件卡片',
                        description: '蓝色皮革钱包，内有身份证和银行卡',
                        time: '2026-04-25 14:30',
                        location: '图书馆二楼',
                        image: null
                    },
                    {
                        id: 'lost2',
                        name: '红色手机',
                        category: '电子设备',
                        description: '红色智能手机，屏幕有保护膜',
                        time: '2026-04-24 16:00',
                        location: '操场',
                        image: null
                    }
                ];
                
                this.lostItems = mockLostItems;
                container.innerHTML = mockLostItems.map(item => {
                    item.type = 'lost';
                    return this.renderItemCard(item);
                }).join('');
            }, 500);
        }
    }

    async loadFoundItems() {
        const container = document.getElementById('foundItemsGrid');
        if (container) {
            container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
            
            setTimeout(() => {
                const mockFoundItems = [
                    {
                        id: 'found1',
                        name: '黑色笔记本电脑',
                        category: '电子设备',
                        description: '黑色联想笔记本电脑，有红色贴纸',
                        time: '2026-04-25 10:00',
                        location: '教学楼302室',
                        image: null
                    },
                    {
                        id: 'found2',
                        name: '绿色背包',
                        category: '箱包',
                        description: '绿色双肩背包，有学校标志',
                        time: '2026-04-24 15:30',
                        location: '食堂',
                        image: null
                    }
                ];
                
                this.foundItems = mockFoundItems;
                container.innerHTML = mockFoundItems.map(item => {
                    item.type = 'found';
                    return this.renderItemCard(item);
                }).join('');
            }, 500);
        }
    }

    async loadRecommendations() {
        const container = document.getElementById('recommendationsGrid');
        if (container) {
            container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
            
            setTimeout(() => {
                const mockRecommendations = [
                    {
                        id: 'rec1',
                        score: 92,
                        lostItem: {
                            name: '蓝色钱包',
                            category: '证件卡片',
                            description: '蓝色皮革钱包，内有身份证和银行卡',
                            time: '2026-04-25 14:30',
                            location: '图书馆二楼'
                        },
                        foundItem: {
                            name: '蓝色钱包',
                            category: '证件卡片',
                            description: '蓝色钱包，内有身份证',
                            time: '2026-04-25 15:00',
                            location: '图书馆三楼'
                        }
                    },
                    {
                        id: 'rec2',
                        score: 85,
                        lostItem: {
                            name: '红色手机',
                            category: '电子设备',
                            description: '红色智能手机，屏幕有保护膜',
                            time: '2026-04-24 16:00',
                            location: '操场'
                        },
                        foundItem: {
                            name: '红色手机',
                            category: '电子设备',
                            description: '红色手机，屏幕有保护膜',
                            time: '2026-04-24 16:30',
                            location: '操场'
                        }
                    }
                ];
                
                this.recommendations = mockRecommendations;
                container.innerHTML = mockRecommendations.map(rec => this.renderMatchCard(rec)).join('');
            }, 500);
        }
    }

    renderMatchCard(rec) {
        return `
            <div class="match-card">
                <div class="match-header">
                    <div class="match-score">${rec.score}%</div>
                    <div class="match-label">匹配度</div>
                </div>
                <div class="match-body">
                    <div class="match-item">
                        <div class="match-item-title">失物信息</div>
                        <div class="match-item-content">
                            <div class="match-item-image">${this.getCategoryIcon(rec.lostItem.category)}</div>
                            <div class="match-item-name">${rec.lostItem.name}</div>
                            <div class="match-item-desc">${rec.lostItem.description}</div>
                        </div>
                    </div>
                    <div class="match-vs">≈</div>
                    <div class="match-item">
                        <div class="match-item-title">招领信息</div>
                        <div class="match-item-content">
                            <div class="match-item-image">${this.getCategoryIcon(rec.foundItem.category)}</div>
                            <div class="match-item-name">${rec.foundItem.name}</div>
                            <div class="match-item-desc">${rec.foundItem.description}</div>
                        </div>
                    </div>
                </div>
                <div class="match-footer">
                    <button class="btn btn-primary" onclick="app.confirmMatch('${rec.id}', true)">确认匹配</button>
                    <button class="btn btn-secondary" onclick="app.confirmMatch('${rec.id}', false)">不是我的</button>
                </div>
            </div>
        `;
    }

    confirmMatch(id, isMatch) {
        if (isMatch) {
            this.showToast('匹配成功！请等待对方确认。', 'success');
        } else {
            this.showToast('已记录，感谢反馈。', 'info');
            const rec = this.recommendations.find(r => r.id === id);
            if (rec) {
                rec.status = 'skipped';
                this.loadRecommendations();
            }
        }
    }

    findMatch(id) {
        this.navigateTo('match');
    }

    viewMatches(id) {
        this.navigateTo('match');
    }

    async submitLostItem() {
        const form = document.getElementById('lostItemForm');
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        if (!this.validateForm(data, ['name', 'category', 'description', 'lostTime', 'lostLocation'])) {
            return;
        }

        try {
            this.showToast('失物登记成功！正在为您匹配...', 'success');
            this.navigateTo('match');
        } catch (error) {
            this.showToast('提交失败，请重试', 'error');
        }
    }

    async submitFoundItem() {
        const form = document.getElementById('foundItemForm');
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        if (!this.validateForm(data, ['name', 'category', 'description', 'foundTime', 'foundLocation', 'storageMethod'])) {
            return;
        }

        try {
            this.showToast('招领登记成功！正在为您匹配...', 'success');
            this.navigateTo('match');
        } catch (error) {
            this.showToast('提交失败，请重试', 'error');
        }
    }

    validateForm(data, requiredFields) {
        for (const field of requiredFields) {
            if (!data[field] || data[field].trim() === '') {
                this.showToast(`请填写必填项：${field}`, 'error');
                return false;
            }
        }
        return true;
    }

    loadProfile() {
        const container = document.getElementById('profileContent');
        if (container && this.currentUser) {
            container.innerHTML = `
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">个人信息</h3>
                    </div>
                    <div class="card-body">
                        <div style="text-align: center; margin-bottom: 2rem;">
                            <div class="user-avatar" style="width: 80px; height: 80px; font-size: 2rem; margin: 0 auto 1rem;">
                                ${this.currentUser.username?.charAt(0).toUpperCase() || 'U'}
                            </div>
                            <h3>${this.currentUser.username || '用户'}</h3>
                            <p style="color: #888;">${this.currentUser.email || '未设置邮箱'}</p>
                        </div>
                        <div style="display: grid; gap: 1rem;">
                            <div><strong>学号/工号：</strong>${this.currentUser.studentId || '未设置'}</div>
                            <div><strong>手机号：</strong>${this.currentUser.phone || '未设置'}</div>
                            <div><strong>诚信积分：</strong>${this.currentUser.creditScore || 100}</div>
                        </div>
                    </div>
                </div>
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">我的记录</h3>
                    </div>
                    <div class="card-body">
                        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; text-align: center;">
                            <div>
                                <div style="font-size: 2rem; font-weight: bold; color: var(--danger-color);">3</div>
                                <div style="color: #888;">失物登记</div>
                            </div>
                            <div>
                                <div style="font-size: 2rem; font-weight: bold; color: var(--secondary-color);">2</div>
                                <div style="color: #888;">招领登记</div>
                            </div>
                            <div>
                                <div style="font-size: 2rem; font-weight: bold; color: var(--primary-color);">2</div>
                                <div style="color: #888;">成功匹配</div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
    }

    switchTab(tab) {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        document.querySelector(`[data-tab="${tab}"]`)?.classList.add('active');
        document.getElementById(`${tab}Tab`)?.classList.add('active');
    }

    showLoginModal() {
        const modal = document.getElementById('loginModal');
        if (modal) {
            modal.classList.add('show');
        }
    }

    hideLoginModal() {
        const modal = document.getElementById('loginModal');
        if (modal) {
            modal.classList.remove('show');
        }
    }

    showModal(modalId, options = {}) {
        const modal = document.getElementById(modalId);
        if (modal) {
            if (options.title) {
                modal.querySelector('.modal-title').textContent = options.title;
            }
            if (options.content) {
                modal.querySelector('.modal-body').innerHTML = options.content;
            }
            modal.classList.add('show');
        }
    }

    hideModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('show');
        }
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }

    logout() {
        localStorage.removeItem('token');
        localStorage.removeItem('userInfo');
        this.currentUser = null;
        this.showLoginModal();
    }

    login(username, password) {
        localStorage.setItem('token', 'mock_token');
        localStorage.setItem('userInfo', JSON.stringify({
            username: username,
            email: username + '@school.edu.cn',
            studentId: '2408090602043',
            phone: '138****8888',
            creditScore: 100
        }));
        this.loadUserInfo();
        this.hideLoginModal();
        this.showToast('登录成功！', 'success');
        this.navigateTo('home');
    }
}

const app = new App();

window.addEventListener('DOMContentLoaded', () => {
    app.navigateTo('home');
});

function handleImageUpload(input, previewId) {
    const preview = document.getElementById(previewId);
    if (preview && input.files) {
        preview.innerHTML = '';
        for (let i = 0; i < Math.min(input.files.length, 4); i++) {
            const file = input.files[i];
            const reader = new FileReader();
            reader.onload = (e) => {
                preview.innerHTML += `
                    <div class="image-preview-item">
                        <img src="${e.target.result}" alt="预览">
                        <button type="button" class="image-preview-remove" onclick="removeImage(this)">×</button>
                    </div>
                `;
            };
            reader.readAsDataURL(file);
        }
    }
}

function removeImage(btn) {
    btn.parentElement.remove();
}

document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-close')) {
        e.target.closest('.modal').classList.remove('show');
    }
});

document.querySelectorAll('.modal').forEach(modal => {
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.remove('show');
        }
    });
});