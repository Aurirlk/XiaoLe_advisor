/**
 * QuestionnairePage - 调查问卷页面组件
 * 支持多种题型：选择题、填空题、论述题
 * 用户填写问卷后自动填充画像，减少对话轮次
 */
const QuestionnairePage = {
    name: 'QuestionnairePage',
    template: `
        <div class="questionnaire-page">
            <!-- 问卷类型选择 -->
            <div v-if="currentStep === 'select'" class="questionnaire-select">
                <div class="select-header">
                    <h2>📋 快速完成你的志愿画像</h2>
                    <p>填写问卷可以减少与AI的对话轮次，获得更精准的建议</p>
                </div>
                
                <div class="questionnaire-cards">
                    <div 
                        v-for="type in questionnaireTypes" 
                        :key="type.id"
                        class="questionnaire-card"
                        :class="{ 'required': type.required }"
                        @click="selectQuestionnaire(type.id)"
                    >
                        <div class="card-badge" v-if="type.required">必填</div>
                        <h3>{{ type.name }}</h3>
                        <p>{{ type.description }}</p>
                        <div class="card-meta">
                            <span>📝 {{ type.question_count }}题</span>
                            <span>⏱️ {{ type.estimated_time }}</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 问卷填写 -->
            <div v-else-if="currentStep === 'fill'" class="questionnaire-fill">
                <div class="fill-header">
                    <button class="back-btn" @click="currentStep = 'select'">
                        ← 返回选择
                    </button>
                    <h3>{{ currentQuestionnaire?.name }}</h3>
                    <div class="progress-bar">
                        <div class="progress" :style="{ width: progressPercent + '%' }"></div>
                    </div>
                    <span class="progress-text">{{ answeredCount }}/{{ currentQuestionnaire?.questions?.length || 0 }}</span>
                </div>
                
                <div class="questions-container">
                    <div 
                        v-for="(question, index) in currentQuestionnaire?.questions" 
                        :key="question.id"
                        class="question-item"
                        :class="{ 'active': index === currentIndex }"
                        v-show="index === currentIndex"
                    >
                        <div class="question-number">第 {{ index + 1 }} 题</div>
                        <div class="question-text">{{ question.question }}</div>
                        
                        <!-- 单选题 -->
                        <div v-if="question.type === 'single_choice'" class="options-list">
                            <label 
                                v-for="option in question.options" 
                                :key="option"
                                class="option-item"
                                :class="{ 'selected': answers[question.id] === option }"
                            >
                                <input 
                                    type="radio" 
                                    :name="question.id" 
                                    :value="option"
                                    v-model="answers[question.id]"
                                    @change="onAnswer(question.id, option)"
                                />
                                <span class="option-text">{{ option }}</span>
                            </label>
                        </div>
                        
                        <!-- 多选题 -->
                        <div v-else-if="question.type === 'multiple_choice'" class="options-list multiple">
                            <label 
                                v-for="option in question.options" 
                                :key="option"
                                class="option-item"
                                :class="{ 'selected': (answers[question.id] || []).includes(option) }"
                            >
                                <input 
                                    type="checkbox" 
                                    :value="option"
                                    :checked="(answers[question.id] || []).includes(option)"
                                    @change="onMultiAnswer(question.id, option, question.max_select)"
                                />
                                <span class="option-text">{{ option }}</span>
                            </label>
                            <div v-if="question.max_select" class="max-hint">
                                最多选择 {{ question.max_select }} 项
                            </div>
                        </div>
                        
                        <!-- 填空题 -->
                        <div v-else-if="question.type === 'fill_blank'" class="fill-blank">
                            <input 
                                :type="question.input_type === 'number' ? 'number' : 'text'"
                                :placeholder="question.placeholder"
                                v-model="answers[question.id]"
                                :min="question.min"
                                :max="question.max"
                                @input="onAnswer(question.id, answers[question.id])"
                            />
                        </div>
                        
                        <!-- 论述题 -->
                        <div v-else-if="question.type === 'textarea'" class="textarea-wrapper">
                            <textarea 
                                :placeholder="question.placeholder"
                                v-model="answers[question.id]"
                                rows="4"
                                @input="onAnswer(question.id, answers[question.id])"
                            ></textarea>
                        </div>
                    </div>
                </div>
                
                <div class="navigation-buttons">
                    <button 
                        class="btn" 
                        @click="prevQuestion"
                        :disabled="currentIndex === 0"
                    >
                        上一题
                    </button>
                    <button 
                        v-if="currentIndex < totalQuestions - 1"
                        class="btn btn-primary" 
                        @click="nextQuestion"
                    >
                        下一题
                    </button>
                    <button 
                        v-else
                        class="btn btn-success" 
                        @click="submitQuestionnaire"
                        :disabled="submitting"
                    >
                        {{ submitting ? '提交中...' : '完成提交' }}
                    </button>
                </div>
            </div>
            
            <!-- 结果展示 -->
            <div v-else-if="currentStep === 'result'" class="questionnaire-result">
                <div class="result-icon">✅</div>
                <h2>问卷填写完成！</h2>
                <p>你的画像已自动填充，可以开始与AI对话了</p>
                
                <div class="result-summary">
                    <h4>你的画像摘要：</h4>
                    <div class="profile-tags">
                        <span v-if="resultProfile.province" class="tag">{{ resultProfile.province }}</span>
                        <span v-if="resultProfile.subject_type" class="tag">{{ resultProfile.subject_type }}</span>
                        <span v-if="resultProfile.score" class="tag">{{ resultProfile.score }}分</span>
                        <span v-if="resultProfile.gender" class="tag">{{ resultProfile.gender === 'male' ? '男' : '女' }}</span>
                        <span v-if="resultProfile.mbti_type" class="tag">MBTI: {{ resultProfile.mbti_type }}</span>
                    </div>
                    
                    <div v-if="resultProfile.preferred_cities?.length" class="tag-group">
                        <span class="label">偏好城市：</span>
                        <span v-for="city in resultProfile.preferred_cities" :key="city" class="tag small">{{ city }}</span>
                    </div>
                    
                    <div v-if="resultProfile.preferred_majors?.length" class="tag-group">
                        <span class="label">偏好专业：</span>
                        <span v-for="major in resultProfile.preferred_majors" :key="major" class="tag small">{{ major }}</span>
                    </div>
                </div>
                
                <button class="btn btn-primary" @click="startChat">
                    开始AI对话 →
                </button>
            </div>
        </div>
    `,
    data() {
        return {
            currentStep: 'select',
            questionnaireTypes: [],
            currentQuestionnaire: null,
            currentIndex: 0,
            answers: {},
            submitting: false,
            resultProfile: {},
        };
    },
    computed: {
        totalQuestions() {
            return this.currentQuestionnaire?.questions?.length || 0;
        },
        answeredCount() {
            if (!this.currentQuestionnaire?.questions) return 0;
            return this.currentQuestionnaire.questions.filter(q => {
                const answer = this.answers[q.id];
                return answer !== null && answer !== undefined && answer !== '' && 
                       (!Array.isArray(answer) || answer.length > 0);
            }).length;
        },
        progressPercent() {
            return this.totalQuestions > 0 ? (this.answeredCount / this.totalQuestions) * 100 : 0;
        },
    },
    mounted() {
        this.loadQuestionnaireTypes();
    },
    methods: {
        async loadQuestionnaireTypes() {
            try {
                const response = await fetch('/questionnaire/types');
                this.questionnaireTypes = await response.json();
            } catch (error) {
                console.error('加载问卷类型失败:', error);
            }
        },
        async selectQuestionnaire(typeId) {
            try {
                const response = await fetch(`/questionnaire/${typeId}`);
                this.currentQuestionnaire = await response.json();
                this.currentIndex = 0;
                this.answers = {};
                this.currentStep = 'fill';
            } catch (error) {
                console.error('加载问卷失败:', error);
            }
        },
        onAnswer(questionId, value) {
            this.answers[questionId] = value;
        },
        onMultiAnswer(questionId, value, maxSelect) {
            if (!this.answers[questionId]) {
                this.answers[questionId] = [];
            }
            
            const index = this.answers[questionId].indexOf(value);
            if (index > -1) {
                this.answers[questionId].splice(index, 1);
            } else {
                if (!maxSelect || this.answers[questionId].length < maxSelect) {
                    this.answers[questionId].push(value);
                }
            }
        },
        prevQuestion() {
            if (this.currentIndex > 0) {
                this.currentIndex--;
            }
        },
        nextQuestion() {
            if (this.currentIndex < this.totalQuestions - 1) {
                this.currentIndex++;
            }
        },
        async submitQuestionnaire() {
            this.submitting = true;
            try {
                const response = await fetch('/questionnaire/submit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        questionnaire_type: this.currentQuestionnaire.id,
                        answers: this.answers,
                        phone_number: localStorage.getItem('user_phone') || '',
                    }),
                });
                
                const result = await response.json();
                
                if (result.ok) {
                    this.resultProfile = result.profile;
                    // 保存到localStorage供后续使用
                    localStorage.setItem('questionnaire_profile', JSON.stringify(result.profile));
                    if (result.parent_constraints) {
                        localStorage.setItem('parent_constraints', JSON.stringify(result.parent_constraints));
                    }
                    if (result.student_preferences) {
                        localStorage.setItem('student_preferences', JSON.stringify(result.student_preferences));
                    }
                    this.currentStep = 'result';
                } else {
                    alert('提交失败: ' + result.message);
                }
            } catch (error) {
                console.error('提交问卷失败:', error);
                alert('提交失败，请重试');
            } finally {
                this.submitting = false;
            }
        },
        startChat() {
            this.$emit('questionnaire-complete', this.resultProfile);
        },
    },
};
