<template>
  <div class="file-uploader" style="padding:16px;border:2px dashed var(--border);border-radius:12px;text-align:center">
    <input type="file" @change="handleFile" :accept="accept" style="display:none" ref="fileInput" />
    <button @click="$refs.fileInput.click()" style="padding:12px 24px;border:none;border-radius:8px;background:var(--primary);color:#fff;font-size:14px;cursor:pointer">
      <i class="fas fa-upload"></i> 上传{{ scenario==='score_segment'?'一分一段表':scenario==='admission_score'?'录取分数线':'数据' }}
    </button>
    <p v-if="error" style="color:var(--danger);font-size:12px;margin-top:8px">{{ error }}</p>
    <p v-if="success" style="color:var(--success);font-size:12px;margin-top:8px">{{ success }}</p>
  </div>
</template>
<script>export default { name: 'FileUploader', props: { scenario: String, province: String, year: Number, subjectType: String }, emits: ['upload-success','upload-error'], data() { return { error: '', success: '', accept: '.csv,.xlsx,.xls,.pdf,.png,.jpg' } }, methods: { async handleFile(e) { this.error='';this.success=''; const f=e.target.files[0]; if(!f)return; try{ const fd=new FormData(); fd.append('file',f); if(this.scenario)fd.append('scenario',this.scenario); const r=await fetch(`${window.API_BASE||''}/harness/upload`,{method:'POST',body:fd}); if(!r.ok)throw Error('上传失败'); const d=await r.json(); this.success=`成功解析 ${d.parsed_count||0} 条记录`; this.$emit('upload-success',d) }catch(e){ this.error=e.message; this.$emit('upload-error',{error:e.message}) } } } }</script>
