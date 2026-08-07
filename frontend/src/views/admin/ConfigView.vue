<template>
  <div class="admin-page"><h3>系统配置</h3>
    <el-card v-loading="loading">
      <el-form label-position="top" v-if="config.selected_module">
        <el-form-item label="LLM 模型">
          <el-select v-model="config.selected_module.LLM">
            <el-option v-for="m in llmOptions" :key="m" :label="m" :value="m"/>
          </el-select>
        </el-form-item>
        <el-form-item label="ASR 引擎">
          <el-select v-model="config.selected_module.ASR">
            <el-option v-for="m in asrOptions" :key="m" :label="m" :value="m"/>
          </el-select>
        </el-form-item>
        <el-form-item label="TTS 引擎">
          <el-select v-model="config.selected_module.TTS">
            <el-option v-for="m in ttsOptions" :key="m" :label="m" :value="m"/>
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="save" :loading="saving">保存配置</el-button>
          <el-alert v-if="saveResult" :title="saveResult" :type="saveResult.includes('成功')?'success':'error'" show-icon style="margin-top:12px"/>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>
<script>
export default {
  name:'AdminConfig', data(){return{loading:false,saving:false,saveResult:'',config:{selected_module:{LLM:'',ASR:'',TTS:''}},llmOptions:['deepseek-v4-flash','deepseek-v4-pro','qwen3.7-plus','qwen3.7-max','glm-5.1-flash'],asrOptions:['FunASR','Qwen3ASR'],ttsOptions:['EdgeTTS','CosyVoice']}},
  methods:{
    async loadConfig(){this.loading=true;try{const r=await fetch('/api/admin/config');const d=await r.json();if(d.ok)this.config=d.data}catch{}finally{this.loading=false}},
    async save(){this.saving=true;this.saveResult='';try{const r=await fetch('/api/admin/config',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(this.config)});const d=await r.json();this.saveResult=d.ok?'配置已保存':'保存失败'}catch(e){this.saveResult='请求失败'}finally{this.saving=false}}
  },
  mounted(){this.loadConfig()}
}
</script>