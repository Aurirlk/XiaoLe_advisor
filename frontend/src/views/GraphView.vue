<template>
  <div style="flex:1;overflow:hidden;display:flex;flex-direction:column">
    <div style="padding:12px 20px;display:flex;gap:12px;align-items:center;border-bottom:1px solid var(--border,#e2e8f0);background:var(--card,#fff)">
      <h3 style="margin:0;font-size:16px">知识图谱</h3>
      <el-select v-model="queryType" style="width:120px;margin-left:auto">
        <el-option value="university_info" label="院校" />
        <el-option value="major_info" label="专业" />
        <el-option value="city_info" label="城市" />
        <el-option value="industry_info" label="行业" />
      </el-select>
      <el-input v-model="keyword" placeholder="搜索..." style="width:180px" clearable @keyup.enter="search" />
      <el-button type="primary" @click="search">查询</el-button>
    </div>
    <div style="flex:1;overflow:hidden;position:relative;background:#f8fafc">
      <canvas ref="canvas" style="width:100%;height:100%;display:block"
        @mousedown="onMouseDown" @mousemove="onMouseMove"
        @mouseup="onMouseUp" @wheel.prevent="onWheel"></canvas>
    </div>
    <el-card v-if="selectedNode" shadow="never" style="border-top:1px solid var(--border,#e2e8f0);border-radius:0">
      <div style="display:flex;gap:20px;flex-wrap:wrap">
        <div v-for="(v,k) in selectedNode.props" :key="k" style="font-size:13px">
          <span style="color:#718096">{{ k }}:</span> <strong>{{ v }}</strong>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script>
export default {
  name: 'GraphView',
  data() {
    return { queryType:'university_info', keyword:'', nodes:[], edges:[], selectedNode:null, pan:{x:0,y:0}, dragging:false, lastMouse:{x:0,y:0}, scale:1, nodeRadius:30 }
  },
  methods: {
    async search() {
      try {
        const q = new URLSearchParams({query_type:this.queryType, keyword:this.keyword||'计算机'})
        const r = await fetch((window.API_BASE||'')+'/api/graph/query?'+q)
        if (!r.ok) throw Error()
        const d = await r.json()
        this.nodes = d.nodes||[]
        this.edges = d.edges||d.relationships||[]
        this.draw()
      } catch {
        this.nodes = [
          {id:'1', name:this.keyword||'计算机科学与技术', type:'Major', props:{code:'080901',category:'工学'}},
          {id:'2', name:'清华大学', type:'University', props:{province:'北京',level:'985/211'}},
          {id:'3', name:'北京', type:'City', props:{tier:'一线'}},
          {id:'4', name:'互联网/IT', type:'Industry', props:{avg_salary:'25万/年'}}
        ]
        this.edges = [{from:'1',to:'2'},{from:'2',to:'3'},{from:'1',to:'4'}]
        this.draw()
      }
    },
    draw() {
      const c = this.$refs.canvas
      if (!c) return
      c.width = c.offsetWidth
      c.height = c.offsetHeight
      const ctx = c.getContext('2d')
      ctx.clearRect(0, 0, c.width, c.height)
      ctx.save()
      ctx.translate(this.pan.x, this.pan.y)
      ctx.scale(this.scale, this.scale)
      const n = this.nodes.length
      const positions = this.nodes.map((_,i) => ({
        x: c.width/2 + Math.cos(2*Math.PI*i/n)*200 - this.pan.x,
        y: c.height/2 + Math.sin(2*Math.PI*i/n)*200 - this.pan.y
      }))
      const colors = { University:'#1e3a5f', Major:'#f0a500', City:'#27ae60', Industry:'#e74c3c' }
      for (const e of this.edges) {
        const fi = this.nodes.findIndex(n => n.id===e.from || n.id===e.source)
        const ti = this.nodes.findIndex(n => n.id===e.to || n.id===e.target)
        if (fi<0 || ti<0) continue
        ctx.beginPath()
        ctx.moveTo(positions[fi].x, positions[fi].y)
        ctx.lineTo(positions[ti].x, positions[ti].y)
        ctx.strokeStyle = 'rgba(30,58,95,0.3)'
        ctx.lineWidth = 2
        ctx.stroke()
      }
      for (let i = 0; i < n; i++) {
        const p = positions[i]
        ctx.beginPath()
        ctx.arc(p.x, p.y, this.nodeRadius, 0, 2*Math.PI)
        ctx.fillStyle = colors[this.nodes[i].type] || '#718096'
        ctx.fill()
        ctx.strokeStyle = '#fff'
        ctx.lineWidth = 2
        ctx.stroke()
        ctx.fillStyle = '#fff'
        ctx.font = '11px sans-serif'
        ctx.textAlign = 'center'
        ctx.fillText(this.nodes[i].name.substring(0,6), p.x, p.y+4)
      }
      ctx.restore()
    },
    onMouseDown(e) { this.dragging=true; this.lastMouse={x:e.clientX,y:e.clientY} },
    onMouseMove(e) { if (!this.dragging) return; this.pan.x+=e.clientX-this.lastMouse.x; this.pan.y+=e.clientY-this.lastMouse.y; this.lastMouse={x:e.clientX,y:e.clientY}; this.draw() },
    onMouseUp() { this.dragging=false },
    onWheel(e) { e.preventDefault(); this.scale=Math.max(0.3, Math.min(3, this.scale-e.deltaY*0.001)); this.draw() }
  },
  mounted() { this.search(); window.addEventListener('resize', ()=>this.draw()) }
}
</script>
