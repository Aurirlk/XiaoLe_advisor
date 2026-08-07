<template>
  <div style="flex:1;overflow:auto;padding:24px">
    <h2 style="margin-bottom:24px">学生信息问卷</h2>
    <div v-if="submitted" style="text-align:center;padding:40px">
      <el-icon :size="48" color="var(--el-color-success)"><Check /></el-icon>
      <p style="margin-top:12px">提交成功！返回对话获取个性化建议</p>
    </div>
    <el-form v-else label-position="top" style="max-width:600px">
      <el-form-item label="省份">
        <el-select v-model="form.province" style="width:100%">
          <el-option v-for="p in provinces" :key="p" :label="p" :value="p" />
        </el-select>
      </el-form-item>
      <el-form-item label="选科类型">
        <el-select v-model="form.subject_type" style="width:100%">
          <el-option label="物理类" value="物理类" /><el-option label="历史类" value="历史类" />
        </el-select>
      </el-form-item>
      <el-form-item label="预估/实际分数">
        <el-input-number v-model="form.score" :min="0" :max="750" style="width:100%" />
      </el-form-item>
      <el-form-item label="MBTI 性格类型">
        <el-select v-model="form.mbti" style="width:100%" clearable placeholder="不确定">
          <el-option v-for="t in mbtiTypes" :key="t" :label="t" :value="t" />
        </el-select>
      </el-form-item>
      <el-form-item label="兴趣方向（多选）">
        <el-checkbox-group v-model="form.interests">
          <el-checkbox v-for="iv in interests" :key="iv" :label="iv" border />
        </el-checkbox-group>
      </el-form-item>
      <el-form-item label="目标城市">
        <el-input v-model="form.target_cities" placeholder="如：北京、上海、深圳" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" size="large" @click="submit" :loading="submitting">{{ submitting?'提交中...':'提交' }}</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>
<script>
import { Check } from '@element-plus/icons-vue'
export default {
  name:'QuestionnaireView',
  data(){return{submitted:false,submitting:false,form:{province:'广东',subject_type:'物理类',score:null,mbti:'',interests:[],target_cities:''},
    provinces:['北京','上海','广东','江苏','浙江','湖北','湖南','四川','山东','河南','河北','安徽','福建','陕西','辽宁','吉林','黑龙江','重庆','天津'],
    mbtiTypes:['INTJ','INTP','ENTJ','ENTP','INFJ','INFP','ENFJ','ENFP','ISTJ','ISFJ','ESTJ','ESFJ','ISTP','ISFP','ESTP','ESFP'],
    interests:['计算机/人工智能','金融/经济','医学/药学','法学','教育/师范','土木/建筑','机械/电子','化学/生物','文学/新闻','艺术/设计']
  }},
  methods:{
    async submit(){this.submitting=true;try{const r=await fetch((window.API_BASE||'')+'/questionnaire/submit',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+localStorage.getItem('auth_token')},body:JSON.stringify(this.form)});if(r.ok)this.submitted=true;else throw Error()}catch{try{const r=await fetch((window.API_BASE||'')+'/api/profile/update',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+localStorage.getItem('auth_token')},body:JSON.stringify(this.form)});if(r.ok)this.submitted=true}catch{}}finally{this.submitting=false}}
  }
}
</script>
