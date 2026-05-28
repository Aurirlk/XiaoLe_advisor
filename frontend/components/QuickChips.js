export default {
  name: 'QuickChips',
  emits: ['send-query'],
  template: `
    <div class="quick-chips">
      <span 
        class="chip" 
        v-for="chip in chips" 
        :key="chip.query"
        @click="$emit('send-query', chip.query)"
      >
        <i :class="chip.icon"></i>
        {{ chip.label }}
      </span>
    </div>
  `,
  data() {
    return {
      chips: [
        { 
          query: '我位次32000，推荐广东可冲稳保院校', 
          label: '位次选校', 
          icon: 'fas fa-bullseye' 
        },
        { 
          query: '计算机科学与技术就业前景怎么样', 
          label: '就业分析', 
          icon: 'fas fa-briefcase' 
        },
        { 
          query: '帮我搜一下2026年最新招生政策', 
          label: '政策查询', 
          icon: 'fas fa-search' 
        },
        { 
          query: '临床医学和电子信息哪个更有前途', 
          label: '专业对比', 
          icon: 'fas fa-balance-scale' 
        },
        { 
          query: '理科580分，想去江苏读计算机', 
          label: '分数匹配', 
          icon: 'fas fa-chart-bar' 
        },
        { 
          query: '家里条件不好该不该考研', 
          label: '人生规划', 
          icon: 'fas fa-road' 
        }
      ]
    }
  }
}