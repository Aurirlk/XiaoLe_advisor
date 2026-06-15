/**
 * KnowledgeGraph - Neo4j知识图谱可视化页面
 * 使用Canvas渲染图谱节点和关系
 */
const KnowledgeGraph = {
    name: 'KnowledgeGraph',
    template: `
        <div class="knowledge-graph">
            <!-- 页面标题 -->
            <div class="graph-header">
                <h2>🕸️ 知识图谱可视化</h2>
                <p>探索院校、专业、职业之间的关联关系</p>
            </div>

            <!-- 控制面板 -->
            <div class="graph-controls">
                <div class="control-group">
                    <label>查询类型</label>
                    <select v-model="queryType" @change="loadGraph">
                        <option value="university">按院校查询</option>
                        <option value="major">按专业查询</option>
                        <option value="city">按城市查询</option>
                        <option value="career">按职业查询</option>
                    </select>
                </div>
                <div class="control-group">
                    <label>搜索</label>
                    <input 
                        type="text" 
                        v-model="searchKeyword" 
                        :placeholder="searchPlaceholder"
                        @keyup.enter="loadGraph"
                    />
                </div>
                <div class="control-group">
                    <label>深度</label>
                    <select v-model="depth">
                        <option value="1">1跳</option>
                        <option value="2">2跳</option>
                        <option value="3">3跳</option>
                    </select>
                </div>
                <button class="btn-primary" @click="loadGraph">
                    🔍 查询图谱
                </button>
                <button class="btn-secondary" @click="resetGraph">
                    🔄 重置
                </button>
            </div>

            <!-- 图例 -->
            <div class="graph-legend">
                <div class="legend-item" v-for="item in legendItems" :key="item.type">
                    <span class="legend-dot" :style="{ background: item.color }"></span>
                    <span class="legend-label">{{ item.label }}</span>
                </div>
            </div>

            <!-- 图谱画布 -->
            <div class="graph-canvas-wrapper">
                <canvas 
                    ref="graphCanvas" 
                    :width="canvasWidth" 
                    :height="canvasHeight"
                    @mousedown="onMouseDown"
                    @mousemove="onMouseMove"
                    @mouseup="onMouseUp"
                    @wheel="onWheel"
                ></canvas>
                
                <!-- 节点信息提示 -->
                <div v-if="hoveredNode" class="node-tooltip" :style="tooltipStyle">
                    <h4>{{ hoveredNode.label }}</h4>
                    <p>类型: {{ hoveredNode.type }}</p>
                    <p v-if="hoveredNode.properties">
                        <span v-for="(value, key) in hoveredNode.properties" :key="key">
                            {{ key }}: {{ value }}<br/>
                        </span>
                    </p>
                </div>
            </div>

            <!-- 统计信息 -->
            <div class="graph-stats">
                <div class="stat-item">
                    <span class="stat-value">{{ nodes.length }}</span>
                    <span class="stat-label">节点数</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value">{{ edges.length }}</span>
                    <span class="stat-label">关系数</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value">{{ selectedNode ? selectedNode.label : '-' }}</span>
                    <span class="stat-label">选中节点</span>
                </div>
            </div>

            <!-- 节点详情面板 -->
            <div v-if="selectedNode" class="node-detail-panel">
                <h3>{{ selectedNode.label }}</h3>
                <div class="detail-content">
                    <div class="detail-row">
                        <span class="label">类型:</span>
                        <span class="value">{{ selectedNode.type }}</span>
                    </div>
                    <div v-if="selectedNode.properties" class="detail-row" v-for="(value, key) in selectedNode.properties" :key="key">
                        <span class="label">{{ key }}:</span>
                        <span class="value">{{ value }}</span>
                    </div>
                </div>
                <h4>关联节点</h4>
                <div class="related-nodes">
                    <div 
                        v-for="edge in getRelatedEdges(selectedNode)" 
                        :key="edge.id"
                        class="related-item"
                        @click="focusNode(edge.target)"
                    >
                        <span class="edge-type">{{ edge.label }}</span>
                        <span class="target-node">{{ getNodeLabel(edge.target) }}</span>
                    </div>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            queryType: 'university',
            searchKeyword: '',
            depth: 2,
            canvasWidth: 900,
            canvasHeight: 600,
            nodes: [],
            edges: [],
            selectedNode: null,
            hoveredNode: null,
            tooltipStyle: {},
            isDragging: false,
            dragNode: null,
            offsetX: 0,
            offsetY: 0,
            panX: 0,
            panY: 0,
            scale: 1,
            legendItems: [
                { type: 'University', label: '院校', color: '#4A90D9' },
                { type: 'Major', label: '专业', color: '#67C23A' },
                { type: 'Career', label: '职业', color: '#E6A23C' },
                { type: 'City', label: '城市', color: '#F56C6C' },
                { type: 'IndustryCluster', label: '产业集群', color: '#909399' },
                { type: 'Province', label: '省份', color: '#9B59B6' },
            ],
            // 示例图谱数据
            sampleGraph: {
                nodes: [
                    { id: 'u1', label: '清华大学', type: 'University', x: 400, y: 100, properties: { level: '985', city: '北京' } },
                    { id: 'u2', label: '北京大学', type: 'University', x: 600, y: 150, properties: { level: '985', city: '北京' } },
                    { id: 'u3', label: '中山大学', type: 'University', x: 300, y: 300, properties: { level: '985', city: '广州' } },
                    { id: 'u4', label: '华南理工大学', type: 'University', x: 500, y: 350, properties: { level: '985', city: '广州' } },
                    { id: 'm1', label: '计算机科学', type: 'Major', x: 200, y: 200 },
                    { id: 'm2', label: '人工智能', type: 'Major', x: 350, y: 200 },
                    { id: 'm3', label: '临床医学', type: 'Major', x: 650, y: 250 },
                    { id: 'm4', label: '法学', type: 'Major', x: 750, y: 300 },
                    { id: 'c1', label: '软件工程师', type: 'Career', x: 150, y: 350 },
                    { id: 'c2', label: '算法工程师', type: 'Career', x: 300, y: 400 },
                    { id: 'c3', label: '医生', type: 'Career', x: 600, y: 400 },
                    { id: 'c4', label: '律师', type: 'Career', x: 750, y: 400 },
                    { id: 'city1', label: '北京', type: 'City', x: 500, y: 50, properties: { tier: '一线' } },
                    { id: 'city2', label: '广州', type: 'City', x: 400, y: 450, properties: { tier: '一线' } },
                    { id: 'cl1', label: '中关村科技园', type: 'IndustryCluster', x: 650, y: 100, properties: { industry: '科技' } },
                    { id: 'cl2', label: '天河软件园', type: 'IndustryCluster', x: 250, y: 450, properties: { industry: '软件' } },
                ],
                edges: [
                    { id: 'e1', source: 'u1', target: 'm1', label: '开设' },
                    { id: 'e2', source: 'u1', target: 'm2', label: '开设' },
                    { id: 'e3', source: 'u2', target: 'm3', label: '开设' },
                    { id: 'e4', source: 'u2', target: 'm4', label: '开设' },
                    { id: 'e5', source: 'u3', target: 'm1', label: '开设' },
                    { id: 'e6', source: 'u3', target: 'm3', label: '开设' },
                    { id: 'e7', source: 'u4', target: 'm1', label: '开设' },
                    { id: 'e8', source: 'u4', target: 'm2', label: '开设' },
                    { id: 'e9', source: 'm1', target: 'c1', label: '就业方向' },
                    { id: 'e10', source: 'm2', target: 'c2', label: '就业方向' },
                    { id: 'e11', source: 'm3', target: 'c3', label: '就业方向' },
                    { id: 'e12', source: 'm4', target: 'c4', label: '就业方向' },
                    { id: 'e13', source: 'u1', target: 'city1', label: '位于' },
                    { id: 'e14', source: 'u2', target: 'city1', label: '位于' },
                    { id: 'e15', source: 'u3', target: 'city2', label: '位于' },
                    { id: 'e16', source: 'u4', target: 'city2', label: '位于' },
                    { id: 'e17', source: 'city1', target: 'cl1', label: '拥有' },
                    { id: 'e18', source: 'city2', target: 'cl2', label: '拥有' },
                ],
            },
        };
    },
    computed: {
        searchPlaceholder() {
            const placeholders = {
                university: '输入院校名称，如：清华大学',
                major: '输入专业名称，如：计算机科学',
                city: '输入城市名称，如：北京',
                career: '输入职业名称，如：软件工程师',
            };
            return placeholders[this.queryType] || '输入关键词...';
        },
    },
    mounted() {
        this.loadGraph();
        this.startAnimation();
    },
    methods: {
        loadGraph() {
            // 使用示例数据（实际应从API获取）
            this.nodes = JSON.parse(JSON.stringify(this.sampleGraph.nodes));
            this.edges = JSON.parse(JSON.stringify(this.sampleGraph.edges));
            this.renderGraph();
        },
        resetGraph() {
            this.selectedNode = null;
            this.hoveredNode = null;
            this.panX = 0;
            this.panY = 0;
            this.scale = 1;
            this.loadGraph();
        },
        renderGraph() {
            const canvas = this.$refs.graphCanvas;
            if (!canvas) return;
            
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, this.canvasWidth, this.canvasHeight);
            
            ctx.save();
            ctx.translate(this.panX, this.panY);
            ctx.scale(this.scale, this.scale);
            
            // 绘制边
            this.edges.forEach(edge => {
                const source = this.nodes.find(n => n.id === edge.source);
                const target = this.nodes.find(n => n.id === edge.target);
                if (source && target) {
                    this.drawEdge(ctx, source, target, edge);
                }
            });
            
            // 绘制节点
            this.nodes.forEach(node => {
                this.drawNode(ctx, node);
            });
            
            ctx.restore();
        },
        drawNode(ctx, node) {
            const colors = {
                University: '#4A90D9',
                Major: '#67C23A',
                Career: '#E6A23C',
                City: '#F56C6C',
                IndustryCluster: '#909399',
                Province: '#9B59B6',
            };
            
            const color = colors[node.type] || '#909399';
            const radius = node.type === 'University' ? 25 : 20;
            
            // 绘制节点圆形
            ctx.beginPath();
            ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
            ctx.fillStyle = this.selectedNode?.id === node.id ? '#FFD700' : color;
            ctx.fill();
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 2;
            ctx.stroke();
            
            // 绘制节点标签
            ctx.fillStyle = '#333';
            ctx.font = '12px Microsoft YaHei';
            ctx.textAlign = 'center';
            ctx.fillText(node.label, node.x, node.y + radius + 15);
        },
        drawEdge(ctx, source, target, edge) {
            ctx.beginPath();
            ctx.moveTo(source.x, source.y);
            ctx.lineTo(target.x, target.y);
            ctx.strokeStyle = '#ccc';
            ctx.lineWidth = 1;
            ctx.stroke();
            
            // 绘制关系标签
            const midX = (source.x + target.x) / 2;
            const midY = (source.y + target.y) / 2;
            ctx.fillStyle = '#999';
            ctx.font = '10px Microsoft YaHei';
            ctx.textAlign = 'center';
            ctx.fillText(edge.label, midX, midY - 5);
        },
        onMouseDown(e) {
            const rect = this.$refs.graphCanvas.getBoundingClientRect();
            const x = (e.clientX - rect.left - this.panX) / this.scale;
            const y = (e.clientY - rect.top - this.panY) / this.scale;
            
            const clickedNode = this.nodes.find(node => {
                const dx = node.x - x;
                const dy = node.y - y;
                return Math.sqrt(dx * dx + dy * dy) < 25;
            });
            
            if (clickedNode) {
                this.isDragging = true;
                this.dragNode = clickedNode;
                this.offsetX = x - clickedNode.x;
                this.offsetY = y - clickedNode.y;
                this.selectedNode = clickedNode;
            }
        },
        onMouseMove(e) {
            const rect = this.$refs.graphCanvas.getBoundingClientRect();
            const x = (e.clientX - rect.left - this.panX) / this.scale;
            const y = (e.clientY - rect.top - this.panY) / this.scale;
            
            if (this.isDragging && this.dragNode) {
                this.dragNode.x = x - this.offsetX;
                this.dragNode.y = y - this.offsetY;
                this.renderGraph();
            } else {
                // 检测悬停节点
                const hovered = this.nodes.find(node => {
                    const dx = node.x - x;
                    const dy = node.y - y;
                    return Math.sqrt(dx * dx + dy * dy) < 25;
                });
                
                this.hoveredNode = hovered;
                if (hovered) {
                    this.tooltipStyle = {
                        left: (e.clientX - rect.left + 10) + 'px',
                        top: (e.clientY - rect.top - 30) + 'px',
                    };
                }
            }
        },
        onMouseUp() {
            this.isDragging = false;
            this.dragNode = null;
        },
        onWheel(e) {
            e.preventDefault();
            const delta = e.deltaY > 0 ? 0.9 : 1.1;
            this.scale *= delta;
            this.scale = Math.max(0.5, Math.min(2, this.scale));
            this.renderGraph();
        },
        getRelatedEdges(node) {
            return this.edges.filter(e => e.source === node.id || e.target === node.id);
        },
        getNodeLabel(nodeId) {
            const node = this.nodes.find(n => n.id === nodeId);
            return node ? node.label : '';
        },
        focusNode(nodeId) {
            const node = this.nodes.find(n => n.id === nodeId);
            if (node) {
                this.selectedNode = node;
                this.renderGraph();
            }
        },
        startAnimation() {
            // 简单的动画循环
            const animate = () => {
                this.renderGraph();
                requestAnimationFrame(animate);
            };
            animate();
        },
    },
};
