/**
 * KnowledgeManagement - 知识库管理组件
 * 支持查看、添加、删除知识条目
 */
const KnowledgeManagement = {
    name: 'KnowledgeManagement',
    template: `
        <div class="knowledge-management">
            <div class="section-header">
                <h4>知识库管理</h4>
                <button class="btn btn-primary" @click="showAddModal = true">
                    <i class="fas fa-plus"></i> 添加知识
                </button>
            </div>

            <div class="stats-bar">
                <span>共 {{ total }} 条知识</span>
            </div>

            <div class="knowledge-list">
                <div v-if="loading" class="loading">加载中...</div>
                <div v-else-if="items.length === 0" class="empty">暂无数据</div>
                <div v-else class="knowledge-table">
                    <div class="table-header">
                        <span class="col-index">#</span>
                        <span class="col-source">来源</span>
                        <span class="col-text">内容</span>
                        <span class="col-actions">操作</span>
                    </div>
                    <div 
                        v-for="(item, index) in items" 
                        :key="index" 
                        class="table-row"
                    >
                        <span class="col-index">{{ offset + index + 1 }}</span>
                        <span class="col-source">{{ item.source }}</span>
                        <span class="col-text">{{ truncate(item.text, 80) }}</span>
                        <span class="col-actions">
                            <button class="btn-icon" @click="deleteItem(offset + index)" title="删除">
                                <i class="fas fa-trash"></i>
                            </button>
                        </span>
                    </div>
                </div>
            </div>

            <div class="pagination" v-if="total > pageSize">
                <button 
                    class="btn" 
                    :disabled="offset === 0"
                    @click="prevPage"
                >
                    上一页
                </button>
                <span>{{ Math.floor(offset / pageSize) + 1 }} / {{ totalPages }}</span>
                <button 
                    class="btn" 
                    :disabled="offset + pageSize >= total"
                    @click="nextPage"
                >
                    下一页
                </button>
            </div>

            <!-- 添加知识弹窗 -->
            <div v-if="showAddModal" class="modal-overlay" @click.self="showAddModal = false">
                <div class="modal">
                    <h4>添加知识</h4>
                    <form @submit.prevent="addItem">
                        <div class="form-group">
                            <label>来源</label>
                            <input v-model="newItem.source" required placeholder="例如：2024年高考政策解读" />
                        </div>
                        <div class="form-group">
                            <label>内容</label>
                            <textarea v-model="newItem.text" required rows="4" placeholder="知识内容..."></textarea>
                        </div>
                        <div class="modal-actions">
                            <button type="button" class="btn" @click="showAddModal = false">取消</button>
                            <button type="submit" class="btn btn-primary" :disabled="submitting">
                                {{ submitting ? '添加中...' : '添加' }}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            items: [],
            total: 0,
            offset: 0,
            pageSize: 20,
            loading: false,
            showAddModal: false,
            submitting: false,
            newItem: { source: '', text: '' },
        };
    },
    computed: {
        totalPages() {
            return Math.ceil(this.total / this.pageSize);
        },
    },
    mounted() {
        this.loadItems();
    },
    methods: {
        async loadItems() {
            this.loading = true;
            try {
                const response = await fetch(
                    `/admin/knowledge/list?limit=${this.pageSize}&offset=${this.offset}`,
                    {
                        headers: {
                            'X-Admin-Key': localStorage.getItem('admin_key') || '',
                        },
                    }
                );
                const data = await response.json();
                if (data.ok) {
                    this.items = data.items;
                    this.total = data.total;
                }
            } catch (error) {
                console.error('加载知识库失败:', error);
            } finally {
                this.loading = false;
            }
        },
        async addItem() {
            this.submitting = true;
            try {
                const response = await fetch('/admin/knowledge/upload', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Admin-Key': localStorage.getItem('admin_key') || '',
                    },
                    body: JSON.stringify(this.newItem),
                });
                const data = await response.json();
                if (data.ok) {
                    this.showAddModal = false;
                    this.newItem = { source: '', text: '' };
                    this.loadItems();
                }
            } catch (error) {
                console.error('添加知识失败:', error);
            } finally {
                this.submitting = false;
            }
        },
        async deleteItem(index) {
            if (!confirm('确定要删除这条知识吗？')) return;
            try {
                const response = await fetch(`/admin/knowledge/${index}`, {
                    method: 'DELETE',
                    headers: {
                        'X-Admin-Key': localStorage.getItem('admin_key') || '',
                    },
                });
                const data = await response.json();
                if (data.ok) {
                    this.loadItems();
                }
            } catch (error) {
                console.error('删除失败:', error);
            }
        },
        prevPage() {
            this.offset = Math.max(0, this.offset - this.pageSize);
            this.loadItems();
        },
        nextPage() {
            this.offset += this.pageSize;
            this.loadItems();
        },
        truncate(text, length) {
            return text.length > length ? text.substring(0, length) + '...' : text;
        },
    },
};
