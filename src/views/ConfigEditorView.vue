<template>
  <div class="config-editor-view">
    <h2>AI 配置编辑器</h2>
    
    <div class="config-actions">
      <button @click="loadConfig" :disabled="!isWebSocketConnected">加载当前配置</button>
      <button @click="saveConfig" :disabled="!isWebSocketConnected">保存配置</button>
    </div>

    <div class="settings-section ai-settings">
      <h3>通用 AI 设置</h3>
      <div class="form-group">
        <label for="currentPersona">当前激活角色:</label>
        <select id="currentPersona" v-model="formConfig.ai_settings.current_persona">
          <option v-for="(persona, id) in formConfig.ai_settings.personas" :key="id" :value="id">
            {{ persona.name }} ({{ id }})
          </option>
        </select>
      </div>
    </div>

    <div class="settings-section persona-definitions">
      <h3>
        角色定义 
        <button @click="showPersonaDefinitions = !showPersonaDefinitions" class="toggle-section-button">
          {{ showPersonaDefinitions ? '收起' : '展开' }}
        </button>
      </h3>
      <div v-show="showPersonaDefinitions">
        <div v-for="(persona, id) in formConfig.ai_settings.personas" :key="id" class="persona-item">
          <h4>{{ persona.name }} (ID: {{ id }})</h4>
          <div class="form-group">
            <label :for="'persona-name-' + id">角色名称:</label>
            <input type="text" :id="'persona-name-' + id" v-model="persona.name" />
          </div>
          <div class="form-group">
            <label :for="'responseMode-' + id">响应模式:</label>
            <select :id="'responseMode-' + id" v-model="persona.response_mode">
              <option value="keyword">关键词模式</option>
              <option value="free_qa">自由问答模式</option>
            </select>
          </div>
          <div class="form-group">
            <label :for="'personaPrompt-' + id">角色人设提示:</label>
            <textarea :id="'personaPrompt-' + id" v-model="persona.persona_prompt" rows="5"></textarea>
          </div>
          <div class="form-group">
            <label :for="'filteringEnabled-' + id">启用过滤 (自由问答模式):</label>
            <input type="checkbox" :id="'filteringEnabled-' + id" v-model="persona.filtering_enabled" />
          </div>
          <div class="form-group" v-if="persona.filtering_enabled">
            <label :for="'minMessageLength-' + id">最小消息长度:</label>
            <input type="number" :id="'minMessageLength-' + id" v-model.number="persona.min_message_length" min="1" />
          </div>
          <div class="form-group" v-if="persona.filtering_enabled">
            <label :for="'meaninglessPatterns-' + id">无意义模式 (每行一个):</label>
            <textarea :id="'meaninglessPatterns-' + id" 
                      :value="getMeaninglessPatternsText(id)"
                      @input="setMeaninglessPatternsText(id, ($event.target as HTMLTextAreaElement).value)" 
                      rows="5"></textarea>
          </div>
          <button @click="removePersona(id)" class="remove-button" :disabled="Object.keys(formConfig.ai_settings.personas).length === 1">删除此角色</button>
        </div>
        <button @click="addPersona" class="add-button">添加新角色</button>
      </div>
    </div>

    <div class="settings-section keyword-settings">
      <h3>
        关键词配置
        <button @click="showKeywordSettings = !showKeywordSettings" class="toggle-section-button">
          {{ showKeywordSettings ? '收起' : '展开' }}
        </button>
      </h3>
      <div v-show="showKeywordSettings">
        <div class="keyword-filter-search">
          <div class="filter-group">
            <label for="typeFilter">按类型筛选:</label>
            <select id="typeFilter" v-model="selectedTypeFilter">
              <option value="All">所有类型</option>
              <option value="simple_reply">简单回复</option>
              <option value="contextual_reply">上下文回复</option>
              <option value="product_info">商品信息</option>
            </select>
          </div>
          <div class="search-group">
            <label for="keywordSearch">关键词搜索:</label>
            <input type="text" id="keywordSearch" v-model="searchTerm" placeholder="输入关键词搜索..." />
          </div>
        </div>

        <div class="keyword-list-header">
          <div>关键词</div>
          <div>类型</div>
          <div>AI 上下文摘要</div>
          <div>操作</div>
        </div>
        <div v-for="(keywordConfig, index) in filteredKeywords" :key="getKeywordUniqueId(keywordConfig, index)" class="keyword-item-row">
          <div class="keyword-summary">
            <div>{{ keywordConfig.keyword }}</div>
            <div>{{ keywordConfig.type === 'product_info' ? '商品信息' : (keywordConfig.type === 'simple_reply' ? '简单回复' : '上下文回复') }}</div>
            <div class="context-summary">{{ keywordConfig.ai_context.substring(0, 30) }}{{ keywordConfig.ai_context.length > 30 ? '...' : '' }}</div>
            <div class="actions">
              <button @click="toggleEdit(index)" class="edit-button">{{ editingIndex === index ? '收起' : '编辑' }}</button>
              <button @click="removeKeyword(index)" class="remove-button">删除</button>
            </div>
          </div>
          <div v-if="editingIndex === index" class="keyword-detail-editor">
            <div class="form-group">
              <label :for="'keyword-detail-' + index">关键词文字:</label>
              <input type="text" :id="'keyword-detail-' + index" v-model="keywordConfig.keyword" />
            </div>
            <div class="form-group">
              <label :for="'type-detail-' + index">类型:</label>
              <select :id="'type-detail-' + index" v-model="keywordConfig.type">
                <option value="simple_reply">简单回复</option>
                <option value="contextual_reply">上下文回复</option>
                <option value="product_info">商品信息</option>
              </select>
            </div>
            <div class="form-group">
              <label :for="'ai_context-detail-' + index">AI 上下文指示:</label>
              <textarea :id="'ai_context-detail-' + index" v-model="keywordConfig.ai_context" rows="3"></textarea>
            </div>
            <div class="form-group">
              <label :for="'response_template-detail-' + index">回复模板 (可选):</label>
              <textarea :id="'response_template-detail-' + index" v-model="keywordConfig.response_template" rows="2"></textarea>
            </div>

            <div v-if="keywordConfig.type === 'product_info'" class="product-info-section">
              <h5>商品信息</h5>
              <div class="form-group">
                <label :for="'product_name-detail-' + index">商品名称:</label>
                <input type="text" :id="'product_name-detail-' + index" v-model="keywordConfig.product_name" />
              </div>
              <div class="form-group">
                <label :for="'price-detail-' + index">价格:</label>
                <input type="text" :id="'price-detail-' + index" v-model="keywordConfig.price" />
              </div>
              <div class="form-group">
                <label :for="'selling_method-detail-' + index">购买方式:</label>
                <input type="text" :id="'selling_method-detail-' + index" v-model="keywordConfig.selling_method" />
              </div>
            </div>
          </div>
        </div>
        <button @click="addKeyword" class="add-button">添加新关键词</button>
      </div>
    </div>

    <div v-if="message" class="message">{{ message }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue';
import { CLog } from '@/utils/logUtil';

// Interface definitions to match keywords_config.json structure
interface PersonaSettings {
  name: string;
  response_mode: 'keyword' | 'free_qa';
  persona_prompt: string;
  filtering_enabled: boolean;
  min_message_length: number;
  meaningless_patterns: string[];
}

interface AiSettings {
  current_persona: string;
  personas: { [id: string]: PersonaSettings };
}

interface KeywordConfig {
  keyword: string; // This will be the key in the JSON, but an explicit field here
  type: 'simple_reply' | 'contextual_reply' | 'product_info';
  ai_context: string;
  response_template?: string;
  product_name?: string;
  price?: string;
  selling_method?: string;
}

interface FullConfig {
  ai_settings: AiSettings;
  keywords: KeywordConfig[]; // For easier form binding
}

const aiWebSocket = ref<WebSocket | null>(null);
const message = ref<string>('');
const isWebSocketConnected = ref(false);
const editingIndex = ref<number | null>(null); // Tracks which keyword is being edited

// Filter and search state
const selectedTypeFilter = ref<string>('All');
const searchTerm = ref<string>('');

// Collapsible section state
const showPersonaDefinitions = ref<boolean>(true); // New: State for persona section visibility
const showKeywordSettings = ref<boolean>(true); // New: State for keyword section visibility

// Reactive form data structure
const formConfig = ref<FullConfig>({
  ai_settings: {
    current_persona: 'live_selling_assistant',
    personas: {
      live_selling_assistant: {
        name: '卖货助手',
        response_mode: 'keyword',
        persona_prompt: '你是一个专业的直播带货助手，名字叫弹幕鸭。你的任务是积极、热情地回答用户关于商品的所有问题，引导他们下单，并主动介绍商品亮点和优惠活动。你的语气要充满活力和说服力。',
        filtering_enabled: true,
        min_message_length: 4,
        meaningless_patterns: [],
      },
      friendly_chatter: {
        name: '闲聊伙伴',
        response_mode: 'free_qa',
        persona_prompt: '你是一个直播间的好朋友，名字叫弹幕鸭。请专注于与用户进行轻松愉快的闲聊，分享有趣的故事，或者对他们的评论做出幽默的回应，避免过多推销商品。',
        filtering_enabled: true,
        min_message_length: 4,
        meaningless_patterns: [],
      },
    },
  },
  keywords: [],
});

// Helper for meaningless_patterns (Persona specific)
const getMeaninglessPatternsText = (personaId: string) => {
  return formConfig.value.ai_settings.personas[personaId].meaningless_patterns.join('\n');
};
const setMeaninglessPatternsText = (personaId: string, newValue: string) => {
  formConfig.value.ai_settings.personas[personaId].meaningless_patterns = newValue.split('\n').map(s => s.trim()).filter(s => s.length > 0);
};


// Computed property for filtered and searched keywords
const filteredKeywords = computed(() => {
  let filtered = formConfig.value.keywords;

  // Apply type filter
  if (selectedTypeFilter.value !== 'All') {
    filtered = filtered.filter(kw => kw.type === selectedTypeFilter.value);
  }

  // Apply search term
  if (searchTerm.value.trim() !== '') {
    const lowerCaseSearchTerm = searchTerm.value.trim().toLowerCase();
    filtered = filtered.filter(kw => kw.keyword.toLowerCase().includes(lowerCaseSearchTerm));
  }

  return filtered;
});


const connectWebSocket = () => {
  aiWebSocket.value = new WebSocket('ws://localhost:8080');

  aiWebSocket.value.onopen = () => {
    CLog.info('Config Editor WebSocket connected.');
    message.value = 'WebSocket 连接成功。';
    isWebSocketConnected.value = true;
    loadConfig(); // Load config immediately on connection
  };

  aiWebSocket.value.onmessage = (event) => {
    CLog.info('Config Editor Raw WebSocket message received:', event.data);
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'config_update' && data.data) {
        // Parse incoming data into formConfig
        formConfig.value.ai_settings = data.data.ai_settings || formConfig.value.ai_settings;
        
        // Transform keywords from object to array for form binding
        const loadedKeywords: KeywordConfig[] = [];
        for (const key in data.data) {
          if (key !== 'ai_settings') {
            const keywordConfig = data.data[key];
            loadedKeywords.push({ keyword: key, ...keywordConfig });
          }
        }
        formConfig.value.keywords = loadedKeywords;
        message.value = '配置已成功加载。';
      } else if (data.type === 'config_saved') {
        message.value = data.message;
        // Optionally reload config to ensure frontend is in sync
        loadConfig();
      } else {
        CLog.warn('Config Editor Received WebSocket message not recognized:', data);
      }
    } catch (e) {
      CLog.error('Config Editor Failed to parse WebSocket message:', e, 'Raw data:', event.data);
      message.value = '处理消息时出错。';
    }
  };

  aiWebSocket.value.onclose = () => {
    CLog.warn('Config Editor WebSocket disconnected.');
    message.value = 'WebSocket 连接已断开。';
    isWebSocketConnected.value = false;
  };

  aiWebSocket.value.onerror = (error) => {
    CLog.error('Config Editor WebSocket error:', error);
    message.value = 'WebSocket 连接出错。';
    isWebSocketConnected.value = false;
  };
};

const validateForm = (): boolean => {
  message.value = ''; // Clear previous messages

  // Validate current_persona exists
  if (!formConfig.value.ai_settings.current_persona || !(formConfig.value.ai_settings.current_persona in formConfig.value.ai_settings.personas)) {
    message.value = '请选择一个有效的当前激活角色。';
    return false;
  }

  // Validate each persona
  const personaIds = new Set<string>();
  for (const id in formConfig.value.ai_settings.personas) {
    const persona = formConfig.value.ai_settings.personas[id];
    if (!persona.name || persona.name.trim() === '') {
      message.value = `角色 ID "${id}" 的名称不能为空。`;
      return false;
    }
    if (!persona.persona_prompt || persona.persona_prompt.trim() === '') {
      message.value = `角色 ID "${id}" 的人设提示不能为空。`;
      return false;
    }
    if (persona.filtering_enabled) {
      if (typeof persona.min_message_length !== 'number' || persona.min_message_length < 1) {
        message.value = `角色 ID "${id}" 的最小消息长度必须是大于0的数字。`;
        return false;
      }
    }
    personaIds.add(id); // Using the ID from the loop, not persona.name
  }
  if (personaIds.size === 0) {
      message.value = '至少需要定义一个角色。';
      return false;
  }


  // Validate keywords
  const keywordNames = new Set<string>();
  for (const kw of formConfig.value.keywords) {
    if (!kw.keyword || kw.keyword.trim() === '') {
      message.value = '所有关键词不能为空。';
      return false;
    }
    if (keywordNames.has(kw.keyword)) {
      message.value = `关键词 "${kw.keyword}" 重复，请确保每个关键词唯一。`;
      return false;
    }
    keywordNames.add(kw.keyword);

    if (!kw.ai_context || kw.ai_context.trim() === '') {
      message.value = `关键词 "${kw.keyword}" 的 AI 上下文指示不能为空。`;
      return false;
    }

    if (kw.type === 'product_info') {
      if (!kw.product_name || kw.product_name.trim() === '') {
        message.value = `商品关键词 "${kw.keyword}" 的商品名称不能为空。`;
        return false;
      }
      if (!kw.price || kw.price.trim() === '') {
        message.value = `商品关键词 "${kw.keyword}" 的价格不能为空。`;
        return false;
      }
      if (!kw.selling_method || kw.selling_method.trim() === '') {
        message.value = `商品关键词 "${kw.keyword}" 的购买方式不能为空。`;
        return false;
      }
    }
  }

  return true;
};

const loadConfig = () => {
  if (aiWebSocket.value && isWebSocketConnected.value) {
    aiWebSocket.value.send(JSON.stringify({ action: 'get_config' }));
    message.value = '正在加载配置...';
    editingIndex.value = null; // Collapse any open editors on load
  } else {
    message.value = 'WebSocket 未连接，请稍后再试。';
    CLog.warn('Attempted to load config while WebSocket was not open.');
  }
};

const saveConfig = () => {
  if (!validateForm()) {
    return;
  }

  if (aiWebSocket.value && isWebSocketConnected.value) {
    try {
      // Transform formConfig back into the keywords_config.json structure
      const configToSave: { [key: string]: any } = {
        ai_settings: formConfig.value.ai_settings,
      };
      formConfig.value.keywords.forEach(kw => {
        const { keyword, ...rest } = kw;
        configToSave[keyword] = rest;
      });
      aiWebSocket.value.send(JSON.stringify({ action: 'save_config', data: configToSave }));
      message.value = '正在保存配置...';
      editingIndex.value = null; // Collapse editors after save
    } catch (e) {
      message.value = '保存配置失败，请检查数据格式。';
      CLog.error('Failed to prepare config for saving:', e);
    }
  } else {
    message.value = 'WebSocket 未连接，请稍后再试。';
    CLog.warn('Attempted to save config while WebSocket was not open.');
  }
};

// Persona management
const addPersona = () => {
  let newId = 'new_persona_' + Date.now();
  formConfig.value.ai_settings.personas[newId] = {
    name: '新角色',
    response_mode: 'free_qa',
    persona_prompt: '你是一个新角色，请友好地回应。',
    filtering_enabled: true,
    min_message_length: 4,
    meaningless_patterns: [],
  };
};

const removePersona = (id: string) => {
  if (Object.keys(formConfig.value.ai_settings.personas).length === 1) {
    message.value = '至少需要保留一个角色。';
    return;
  }
  if (formConfig.value.ai_settings.current_persona === id) {
    // If removing the active persona, switch to another one
    const otherPersonaId = Object.keys(formConfig.value.ai_settings.personas).find(pid => pid !== id);
    if (otherPersonaId) {
      formConfig.value.ai_settings.current_persona = otherPersonaId;
    }
  }
  delete formConfig.value.ai_settings.personas[id];
};


const addKeyword = () => {
  formConfig.value.keywords.push({
    keyword: '新关键词',
    type: 'contextual_reply',
    ai_context: '请根据新关键词的含义进行回复。',
    response_template: ''
  });
  // editingIndex.value = formConfig.value.keywords.length - 1; // Auto-expand new keyword for editing - doing this interferes with filtering
};

const removeKeyword = (index: number) => {
  formConfig.value.keywords.splice(index, 1);
  if (editingIndex.value === index) {
    editingIndex.value = null; // Close editor if the edited item is removed
  } else if (editingIndex.value !== null && editingIndex.value > index) {
    editingIndex.value--; // Adjust editing index if an item before it is removed
  }
};

const toggleEdit = (index: number) => {
  if (editingIndex.value === index) {
    editingIndex.value = null; // Collapse
  } else {
    editingIndex.value = index; // Expand
  }
};

// Helper to generate a unique key for v-for loop, especially useful when items are filtered/sorted
const getKeywordUniqueId = (keywordConfig: KeywordConfig, index: number): string => {
  return `${keywordConfig.keyword}-${index}`;
};


onMounted(() => {
  connectWebSocket();
});

onUnmounted(() => {
  if (aiWebSocket.value) {
    aiWebSocket.value.close();
  }
});
</script>

<style scoped>
.config-editor-view {
  max-width: 900px;
  margin: 20px auto;
  padding: 20px;
  background-color: #fff;
  border-radius: 15px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.1);
  font-family: 'Helvetica Neue', Arial, sans-serif;
  color: #333;
}

h2 {
  text-align: center;
  color: #68be8d;
  margin-bottom: 30px;
}

h3 {
  color: #555;
  border-bottom: 2px solid #eee;
  padding-bottom: 10px;
  margin-top: 30px;
  margin-bottom: 20px;
}

h4 {
  color: #68be8d;
  margin-top: 20px;
  margin-bottom: 15px;
}

.config-actions {
  text-align: center;
  margin-bottom: 30px;
}

.config-actions button {
  padding: 10px 20px;
  margin: 0 10px;
  background-color: #68be8d;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 16px;
  transition: background-color 0.3s ease;
}

.config-actions button:hover:not(:disabled) {
  background-color: darken(#68be8d, 10%);
}

.config-actions button:active:not(:disabled) {
  background-color: darken(#68be8d, 15%);
}

.config-actions button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.settings-section {
  background-color: #f9f9f9;
  border: 1px solid #eee;
  border-radius: 10px;
  padding: 20px;
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
  color: #444;
}

.form-group input[type="text"],
.form-group input[type="number"],
.form-group select,
.form-group textarea {
  width: calc(100% - 22px); /* Account for padding and border */
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 5px;
  font-size: 14px;
  box-sizing: border-box; /* Include padding in width */
}

.form-group input[type="checkbox"] {
  margin-top: 8px;
  width: auto;
}

textarea {
  resize: vertical;
}

/* Persona Item Styling */
.persona-item {
  border: 1px solid #a8dadc;
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 15px;
  background-color: #f1f8f9;
  position: relative;
}

.persona-item h4 {
  color: #1d3557;
  border-bottom: 1px dashed #a8dadc;
  padding-bottom: 10px;
  margin-bottom: 15px;
  margin-top: 0;
}


/* Keyword Filter and Search Styling */
.keyword-filter-search {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
  padding: 10px 0;
  border-bottom: 1px solid #eee;
}

.filter-group, .search-group {
  flex: 1;
  padding: 0 10px;
}

.filter-group label, .search-group label {
  margin-right: 10px;
  font-weight: bold;
  color: #555;
}

.filter-group select, .search-group input {
  width: auto;
  min-width: 150px;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 5px;
}


/* Keyword List Styling */
.keyword-list-header {
  display: grid;
  grid-template-columns: 1.5fr 1fr 2fr 1fr; /* Keyword, Type, Context, Actions */
  gap: 10px;
  padding: 10px 15px;
  background-color: #e0f2e8;
  font-weight: bold;
  border-radius: 8px 8px 0 0;
  margin-top: 20px;
  border-bottom: 1px solid #cfe7d6;
}

.keyword-item-row {
  border: 1px solid #d3e0d8;
  border-top: none;
  border-radius: 0 0 8px 8px; /* Rounded bottom for the last item */
  margin-bottom: 10px; /* Space between rows */
  background-color: #f9fffb;
}

.keyword-summary {
  display: grid;
  grid-template-columns: 1.5fr 1fr 2fr 1fr;
  gap: 10px;
  align-items: center;
  padding: 10px 15px;
  min-height: 40px;
}

.context-summary {
  font-size: 0.9em;
  color: #666;
  white-space: nowrap; /* Prevent text wrapping */
  overflow: hidden; /* Hide overflow content */
  text-overflow: ellipsis; /* Show ellipsis for truncated text */
}

.keyword-item-row .actions button {
  padding: 5px 10px;
  margin-left: 5px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 13px;
}

.edit-button {
  background-color: #68be8d;
  color: white;
}

.edit-button:hover {
  background-color: darken(#68be8d, 10%);
}

.remove-button {
  background-color: #ff4d4f;
  color: white;
}

.remove-button:hover {
  background-color: darken(#ff4d4f, 10%);
}

.keyword-detail-editor {
  padding: 15px;
  background-color: #f0fcf3;
  border-top: 1px dashed #cfe7d6;
}

.product-info-section {
  border-top: 1px dashed #cfe7d6;
  margin-top: 15px;
  padding-top: 15px;
}

.add-button {
  background-color: #68be8d;
  color: white;
  border: none;
  border-radius: 5px;
  padding: 10px 20px;
  cursor: pointer;
  margin-top: 20px;
  display: block;
  width: fit-content;
  margin-left: auto;
  margin-right: auto;
}

.add-button:hover {
  background-color: darken(#68be8d, 10%);
}

.message {
  margin-top: 20px;
  padding: 10px 15px;
  border-radius: 8px;
  background-color: #e0f7fa;
  color: #00796b;
  font-weight: bold;
  text-align: center;
  width: 100%;
  max-width: 800px;
}

.toggle-section-button {
  background: none;
  border: none;
  color: #68be8d;
  font-size: 1em;
  font-weight: bold;
  cursor: pointer;
  margin-left: 10px;
  padding: 0;
}
.toggle-section-button:hover {
  text-decoration: underline;
}
</style>