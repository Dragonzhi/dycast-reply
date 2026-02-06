<template>
  <div class="ai-assistant-view">
    <div class="ai-main-interaction-area">
      <div class="ai-avatar-section" :class="[isSpeaking ? 'speaking' : '', currentMood]">
        <img src="@/assets/duck_avatar.svg" alt="AI Assistant" class="ai-avatar" />
        <div v-if="currentAiResponse" class="ai-bubble speaking-bubble">
          <div v-if="currentOriginalComment" class="original-comment-context">
            <span class="user-name">{{ currentOriginalComment.user_name }}:</span> {{ currentOriginalComment.text }}
          </div>
          {{ currentAiResponse }}
        </div>
      </div>
      <button @click="testSpeech" class="speech-test-button">测试语音</button>
    </div>

    <div class="ai-history-area">
      <h3>聊天记录</h3>
      <div class="ai-history-list">
        <div v-for="(entry, index) in aiResponseHistory" :key="index" class="ai-bubble history-bubble">
          <div v-if="entry.original_comment" class="original-comment-context history">
            <span class="user-name">{{ entry.original_comment.user_name }}:</span> {{ entry.original_comment.text }}
          </div>
          <div class="ai-response-text">
            <span v-if="entry.mood" class="mood-indicator">[{{ entry.mood }}]</span>
            {{ entry.ai_response }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { CLog } from '@/utils/logUtil';

// Interface definitions for history entries
interface OriginalCommentData {
  user_name: string;
  text: string;
}

interface AiResponseHistoryEntry {
  ai_response: string;
  original_comment?: OriginalCommentData;
  mood?: string;
}

const aiWebSocket = ref<WebSocket | null>(null);
const isSpeaking = ref(false);
const currentAiResponse = ref<string | null>(null);
const currentOriginalComment = ref<OriginalCommentData | null>(null);
const currentMood = ref<string>('neutral'); // New: To store the current mood
const aiResponseHistory = ref<AiResponseHistoryEntry[]>([]);

const speechQueue: { text: string; originalComment?: OriginalCommentData; mood?: string }[] = [];
let speechSynth: SpeechSynthesis | null = null;
let utterance: SpeechSynthesisUtterance | null = null;
let selectedVoice: SpeechSynthesisVoice | null = null;

const initializeSpeechSynthesis = () => {
  speechSynth = window.speechSynthesis;
  speechSynth.onvoiceschanged = () => {
    const voices = speechSynth!.getVoices();
    selectedVoice = voices.find(voice => voice.lang === 'zh-CN') || voices[0];
    if (selectedVoice) CLog.info('Selected voice:', selectedVoice.name, selectedVoice.lang);
    else CLog.warn('No Chinese voice found, using default or first available.');
  };
  if (speechSynth.getVoices().length > 0) {
    const voices = speechSynth.getVoices();
    selectedVoice = voices.find(voice => voice.lang === 'zh-CN') || voices[0];
    if (selectedVoice) CLog.info('Selected voice (on init):', selectedVoice.name, selectedVoice.lang);
    else CLog.warn('No Chinese voice found on init, using default or first available.');
  }

  speechSynth.onend = () => {
    CLog.info('Speech ended.');
    isSpeaking.value = false;
    currentAiResponse.value = null;
    currentOriginalComment.value = null;
    currentMood.value = 'neutral';
    processSpeechQueue();
  };
  speechSynth.onerror = (event) => {
    CLog.error('Speech synthesis error:', event.error);
    isSpeaking.value = false;
    currentAiResponse.value = null;
    currentOriginalComment.value = null;
    currentMood.value = 'neutral';
    processSpeechQueue();
  };
};

const speakAiResponse = (text: string, originalComment?: OriginalCommentData, mood: string = 'neutral') => {
  if (!speechSynth) {
    initializeSpeechSynthesis();
    if (!speechSynth) {
      CLog.error('SpeechSynthesis not available.');
      return;
    }
  }

  if (speechSynth.speaking) {
    speechQueue.push({ text, originalComment, mood });
    CLog.info('Added to speech queue:', { text, originalComment, mood });
  } else {
    currentAiResponse.value = text;
    currentOriginalComment.value = originalComment || null;
    currentMood.value = mood;
    aiResponseHistory.value.unshift({ ai_response: text, original_comment: originalComment, mood });
    isSpeaking.value = true;
    utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'zh-CN';
    if (selectedVoice) utterance.voice = selectedVoice;
    CLog.info('Speaking:', text);
    speechSynth.speak(utterance);
  }
};

const processSpeechQueue = () => {
  if (speechQueue.length > 0 && speechSynth && !speechSynth.speaking) {
    const nextItem = speechQueue.shift();
    if (nextItem) {
      currentAiResponse.value = nextItem.text;
      currentOriginalComment.value = nextItem.originalComment || null;
      currentMood.value = nextItem.mood || 'neutral';
      aiResponseHistory.value.unshift({ ai_response: nextItem.text, original_comment: nextItem.originalComment, mood: nextItem.mood });
      isSpeaking.value = true;
      utterance = new SpeechSynthesisUtterance(nextItem.text);
      utterance.lang = 'zh-CN';
      if (selectedVoice) utterance.voice = selectedVoice;
      CLog.info('Speaking from queue:', nextItem.text);
      speechSynth.speak(utterance);
    }
  }
};

const testSpeech = () => {
  speakAiResponse('你好，这是一个语音测试。如果听到声音，说明语音合成功能正常。', { user_name: '测试用户', text: '你好鸭鸭，测试一下语音功能。' }, 'happy');
};

onMounted(() => {
  initializeSpeechSynthesis();

  aiWebSocket.value = new WebSocket('ws://localhost:8080');

  aiWebSocket.value.onopen = () => CLog.info('AI WebSocket connected.');

  aiWebSocket.value.onmessage = (event) => {
    CLog.info('Raw WebSocket message received:', event.data);
    try {
      const data = JSON.parse(event.data);
      CLog.info('Parsed WebSocket message data:', data);
      if (data.type === 'ai_response' && data.content) {
        CLog.info('Received valid AI response type:', data.content);
        speakAiResponse(data.content, data.original_comment, data.mood);
      } else {
        CLog.warn('Received WebSocket message not an AI response or missing content:', data);
      }
    } catch (e) {
      CLog.error('Failed to parse AI WebSocket message:', e, 'Raw data:', event.data);
    }
  };

  aiWebSocket.value.onclose = () => CLog.warn('AI WebSocket disconnected.');
  aiWebSocket.value.onerror = (error) => CLog.error('AI WebSocket error:', error);
});

onUnmounted(() => {
  if (aiWebSocket.value) aiWebSocket.value.close();
  if (speechSynth && speechSynth.speaking) speechSynth.cancel();
});
</script>

<style lang="scss" scoped>
$theme: #68be8d;

.ai-assistant-view {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f0f2f5;
  gap: 20px;
}

.ai-main-interaction-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
  background-color: #fff;
  border-radius: 15px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.1);
  max-width: 400px;
  width: 90%;
}

.ai-avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  .ai-avatar {
    width: 150px;
    height: 150px;
    border-radius: 50%;
    border: 4px solid transparent;
    transition: border-color 0.3s ease-in-out, transform 0.3s ease-in-out;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    display: block;
  }
  &.speaking .ai-avatar {
    border-color: $theme;
    animation: speaking-pulse 1.5s infinite alternate ease-in-out, speaking-bounce 0.8s infinite alternate ease-in-out;
  }
  &.happy .ai-avatar {
    animation: happy-jiggle 0.5s ease-in-out;
  }
  &.selling .ai-avatar {
    border-color: #ffc107;
    animation: selling-pulse 1s infinite alternate ease-in-out;
  }
  .speaking-bubble {
    margin-top: 20px;
    background-color: #ffffff;
    border-radius: 20px;
    padding: 15px 20px;
    max-width: 300px;
    text-align: center;
    color: #333;
    font-size: 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    position: relative;
    word-wrap: break-word;
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

/* Define keyframe animations */
@keyframes speaking-pulse {
  0% { transform: scale(1); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
  100% { transform: scale(1.08); box-shadow: 0 8px 20px rgba(0,0,0,0.25); }
}
@keyframes speaking-bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-5px); }
}
@keyframes happy-jiggle {
  0%, 100% { transform: rotate(0deg); }
  25% { transform: rotate(5deg); }
  75% { transform: rotate(-5deg); }
}
@keyframes selling-pulse {
  0% { transform: scale(1); box-shadow: 0 4px 12px rgba(255, 193, 7, 0.2); }
  100% { transform: scale(1.1); box-shadow: 0 8px 25px rgba(255, 193, 7, 0.4); }
}

.speech-test-button {
  margin-top: 20px;
  padding: 10px 20px;
  background-color: $theme;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 16px;
  transition: background-color 0.3s ease;
  &:hover { background-color: darken($theme, 10%); }
  &:active { background-color: darken($theme, 15%); }
}

.ai-history-area {
  display: flex;
  flex-direction: column;
  background-color: #f8f8f8;
  border-radius: 15px;
  padding: 15px;
  max-width: 400px;
  width: 90%;
  height: 30vh;
  box-shadow: 0 2px 10px rgba(0,0,0,0.08);
  h3 {
    margin-top: 0;
    color: #555;
    text-align: center;
    margin-bottom: 10px;
  }
}

.ai-history-list {
  flex-grow: 1;
  overflow-y: auto;
  padding-right: 10px;
  display: flex;
  flex-direction: column-reverse;
  gap: 8px;
  &::-webkit-scrollbar { width: 8px; }
  &::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 10px; }
  &::-webkit-scrollbar-thumb { background: #888; border-radius: 10px; }
  &::-webkit-scrollbar-thumb:hover { background: #555; }
}

.ai-bubble.history-bubble {
  opacity: 0.8;
  font-size: 14px;
  background-color: #e9e9e9;
  text-align: left;
  align-self: flex-start;
  max-width: 90%;
  padding: 10px 15px;
  border-radius: 15px;
  box-shadow: none;
}

.original-comment-context {
  font-size: 0.8em;
  color: #777;
  margin-bottom: 5px;
  padding-bottom: 5px;
  border-bottom: 1px solid #e0e0e0;
  &.history {
    font-size: 0.75em;
    color: #888;
    border-bottom: none;
  }
}

.user-name {
  font-weight: bold;
  color: #555;
}

.ai-response-text {
  .mood-indicator {
    font-weight: bold;
    color: $theme;
    margin-right: 5px;
  }
}
</style>