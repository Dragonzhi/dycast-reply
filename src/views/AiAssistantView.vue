<template>
  <div class="ai-assistant-view">
    <div class="ai-assistant-panel" :class="{ 'speaking': isSpeaking }">
      <img src="@/assets/1.png" alt="AI Assistant" class="ai-avatar" />
      <div v-if="currentAiResponse" class="ai-bubble">
        {{ currentAiResponse }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { CLog } from '@/utils/logUtil';

const aiWebSocket = ref<WebSocket | null>(null);
const isSpeaking = ref(false);
const currentAiResponse = ref<string | null>(null);
const speechQueue: string[] = [];
let speechSynth: SpeechSynthesis | null = null;
let utterance: SpeechSynthesisUtterance | null = null;

const speakAiResponse = (text: string) => {
  if (!speechSynth) {
    speechSynth = window.speechSynthesis;
    speechSynth.onend = () => {
      isSpeaking.value = false;
      currentAiResponse.value = null;
      processSpeechQueue();
    };
    speechSynth.onerror = (event) => {
      CLog.error('Speech synthesis error:', event.error);
      isSpeaking.value = false;
      currentAiResponse.value = null;
      processSpeechQueue();
    };
  }

  if (speechSynth.speaking) {
    speechQueue.push(text);
  } else {
    currentAiResponse.value = text;
    isSpeaking.value = true;
    utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'zh-CN'; // Set language to Chinese
    speechSynth.speak(utterance);
  }
};

const processSpeechQueue = () => {
  if (speechQueue.length > 0 && speechSynth && !speechSynth.speaking) {
    const nextText = speechQueue.shift();
    if (nextText) {
      currentAiResponse.value = nextText;
      isSpeaking.value = true;
      utterance = new SpeechSynthesisUtterance(nextText);
      utterance.lang = 'zh-CN';
      speechSynth.speak(utterance);
    }
  }
};

onMounted(() => {
  aiWebSocket.value = new WebSocket('ws://localhost:8080');

  aiWebSocket.value.onopen = () => {
    CLog.info('AI WebSocket connected.');
  };

  aiWebSocket.value.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'ai_response' && data.content) {
        CLog.info('Received AI response:', data.content);
        speakAiResponse(data.content);
      }
    } catch (e) {
      CLog.error('Failed to parse AI WebSocket message:', e);
    }
  };

  aiWebSocket.value.onclose = () => {
    CLog.warn('AI WebSocket disconnected.');
  };

  aiWebSocket.value.onerror = (error) => {
    CLog.error('AI WebSocket error:', error);
  };
});

onUnmounted(() => {
  if (aiWebSocket.value) {
    aiWebSocket.value.close();
  }
  if (speechSynth && speechSynth.speaking) {
    speechSynth.cancel();
  }
});
</script>

<style lang="scss" scoped>
$theme: #68be8d;

.ai-assistant-view {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f0f2f5;
}

.ai-assistant-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
  .ai-avatar {
    width: 150px;
    height: 150px;
    border-radius: 50%;
    border: 4px solid transparent;
    transition: border-color 0.3s ease-in-out;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  }
  &.speaking .ai-avatar {
    border-color: $theme; /* Highlight when speaking */
  }
  .ai-bubble {
    background-color: #ffffff;
    border-radius: 20px;
    padding: 15px 20px;
    margin-top: 20px;
    max-width: 300px;
    text-align: center;
    color: #333;
    font-size: 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    position: relative;
    
    &::after {
      content: '';
      position: absolute;
      top: -10px;
      left: 50%;
      transform: translateX(-50%);
      border-width: 0 10px 10px 10px;
      border-style: solid;
      border-color: transparent transparent #ffffff transparent;
    }
  }
}
</style>
