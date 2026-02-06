<template>
  <div class="config-editor-view">
    <h2>AI 配置编辑器</h2>
    <div class="config-actions">
      <button @click="loadConfig">加载当前配置</button>
      <button @click="saveConfig" :disabled="!configContent">保存配置</button>
    </div>
    <textarea v-model="configContent" rows="30" cols="80" placeholder="加载配置后在此编辑 JSON..."></textarea>
    <div v-if="message" class="message">{{ message }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { CLog } from '@/utils/logUtil'; // Assuming CLog is available for logging

const aiWebSocket = ref<WebSocket | null>(null);
const configContent = ref<string>('');
const message = ref<string>(''); // For displaying feedback messages to the user

const connectWebSocket = () => {
  aiWebSocket.value = new WebSocket('ws://localhost:8080');

  aiWebSocket.value.onopen = () => {
    CLog.info('Config Editor WebSocket connected.');
    message.value = 'WebSocket 连接成功。';
    loadConfig(); // Load config immediately on connection
  };

  aiWebSocket.value.onmessage = (event) => {
    CLog.info('Config Editor Raw WebSocket message received:', event.data);
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'config_update' && data.data) {
        configContent.value = JSON.stringify(data.data, null, 4);
        message.value = '配置已成功加载。';
      } else if (data.type === 'config_saved') {
        message.value = data.message;
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
  };

  aiWebSocket.value.onerror = (error) => {
    CLog.error('Config Editor WebSocket error:', error);
    message.value = 'WebSocket 连接出错。';
  };
};

const loadConfig = () => {
  if (aiWebSocket.value && aiWebSocket.value.readyState === WebSocket.OPEN) {
    aiWebSocket.value.send(JSON.stringify({ action: 'get_config' }));
    message.value = '正在加载配置...';
  } else {
    message.value = 'WebSocket 未连接，请稍后再试。';
    CLog.warn('Attempted to load config while WebSocket was not open.');
  }
};

const saveConfig = () => {
  if (aiWebSocket.value && aiWebSocket.value.readyState === WebSocket.OPEN) {
    try {
      const parsedConfig = JSON.parse(configContent.value);
      aiWebSocket.value.send(JSON.stringify({ action: 'save_config', data: parsedConfig }));
      message.value = '正在保存配置...';
    } catch (e) {
      message.value = '配置格式错误，请检查 JSON。';
      CLog.error('Failed to parse config JSON before saving:', e);
    }
  } else {
    message.value = 'WebSocket 未连接，请稍后再试。';
    CLog.warn('Attempted to save config while WebSocket was not open.');
  }
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
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
  background-color: #f0f2f5;
  min-height: 100vh;
}

h2 {
  color: #333;
  margin-bottom: 20px;
}

.config-actions {
  margin-bottom: 20px;
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

textarea {
  width: 90%;
  max-width: 800px;
  padding: 15px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 14px;
  line-height: 1.5;
  box-shadow: inset 0 1px 3px rgba(0,0,0,0.05);
  resize: vertical;
}

.message {
  margin-top: 20px;
  padding: 10px 15px;
  border-radius: 8px;
  background-color: #e0f7fa;
  color: #00796b;
  font-weight: bold;
}
</style>