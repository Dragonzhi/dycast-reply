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

// Interface definitions
interface OriginalCommentData {
  user_name: string;
  text: string;
}

interface AiResponseHistoryEntry {
  ai_response: string;
  original_comment?: OriginalCommentData;
  mood?: string;
}

// State variables
const aiWebSocket = ref<WebSocket | null>(null);
const isSpeaking = ref(false);
const currentAiResponse = ref<string | null>(null);
const currentOriginalComment = ref<OriginalCommentData | null>(null);
const currentMood = ref<string>('neutral');
const aiResponseHistory = ref<AiResponseHistoryEntry[]>([]);

// Web Audio API variables
let audioContext: AudioContext | null = null;
let currentSourceNode: AudioBufferSourceNode | null = null;
const audioQueue = ref<any[]>([]);

const initializeAudio = () => {
  if (!audioContext) {
    audioContext = new AudioContext();
    CLog.info('AudioContext initialized.');
  }
};

const playAudioFromBase64 = (base64: string, samplingRate: number) => {
  if (!audioContext) {
    CLog.error('AudioContext is not initialized.');
    return;
  }
  
  const binaryString = window.atob(base64);
  const len = binaryString.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  
  audioContext.decodeAudioData(bytes.buffer)
    .then(audioBuffer => {
      // Stop any currently playing audio
      if (currentSourceNode) {
        currentSourceNode.stop();
      }

      const source = audioContext!.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContext!.destination);
      source.onended = () => {
        CLog.info('Audio playback ended.');
        resetSpeakingState();
        processAudioQueue();
      };
      source.start(0);
      currentSourceNode = source;
    })
    .catch(e => {
      CLog.error('Error decoding audio data:', e);
      resetSpeakingState();
    });
};

const handleNewResponse = (data: any) => {
  if (isSpeaking.value) {
    audioQueue.value.push(data);
    CLog.info('Response added to queue.', data);
  } else {
    currentAiResponse.value = data.content;
    currentOriginalComment.value = data.original_comment || null;
    currentMood.value = data.mood || 'neutral';
    aiResponseHistory.value.unshift({ 
      ai_response: data.content, 
      original_comment: data.original_comment, 
      mood: data.mood 
    });
    isSpeaking.value = true;
    playAudioFromBase64(data.audio_base64, data.sampling_rate);
  }
};

const processAudioQueue = () => {
  if (audioQueue.value.length > 0) {
    const nextData = audioQueue.value.shift();
    handleNewResponse(nextData);
  }
};

const resetSpeakingState = () => {
  isSpeaking.value = false;
  currentAiResponse.value = null;
  currentOriginalComment.value = null;
  currentMood.value = 'neutral';
  currentSourceNode = null;
};

const testSpeech = () => {
  const testText = '你好，这是一个语音测试。如果听到声音，说明语音合成功能正常。';
  const testMood = 'happy';
  if (aiWebSocket.value && aiWebSocket.value.readyState === WebSocket.OPEN) {
    aiWebSocket.value.send(JSON.stringify({
      action: 'test_speech', 
      text: testText, 
      mood: testMood 
    }));
    CLog.info('Sent test speech request to backend.');
  } else {
    CLog.warn('WebSocket not connected. Cannot send test speech request.');
  }
};

onMounted(() => {
  initializeAudio();

  aiWebSocket.value = new WebSocket('ws://localhost:8080');

  aiWebSocket.value.onopen = () => CLog.info('AI WebSocket connected.');

  aiWebSocket.value.onmessage = (event) => {
    CLog.info('Raw WebSocket message received:', event.data);
    try {
      const data = JSON.parse(event.data);
      CLog.info('Parsed WebSocket message data:', data);
      if (data.type === 'ai_response' && data.content && data.audio_base64) {
        CLog.info('Received valid AI response with audio:', data.content);
        handleNewResponse(data);
      } else {
        CLog.warn('Received WebSocket message not an AI response or missing content/audio:', data);
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
  if (currentSourceNode) currentSourceNode.stop();
  if (audioContext) audioContext.close();
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
    border-radius: 50%; /* Reintroducing border-radius for circular shape */
    border: 4px solid transparent; /* Keep border for speaking highlight */
    transition: border-color 0.3s ease-in-out;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    display: block;
    object-fit: contain;
    transform-origin: center center; /* Animation origin for overall avatar */
  }
  
  /* Overall speaking animation for the avatar image */
  &.speaking .ai-avatar {
    border-color: $theme;
    animation: avatar-speaking-pulse-strong 1.5s infinite alternate ease-in-out, avatar-speaking-bounce 0.8s infinite alternate ease-in-out;
  }

  /* Mood specific overall avatar animations */
  &.happy .ai-avatar {
    animation: avatar-happy-wobble 0.8s infinite ease-in-out;
  }
  &.selling .ai-avatar {
    border-color: #ffc107;
    animation: avatar-selling-enthusiasm 1.2s infinite alternate ease-in-out;
  }
  &.thinking .ai-avatar {
    filter: brightness(0.9);
    animation: avatar-thinking-subtle 2s infinite alternate ease-in-out;
  }
  &.confused .ai-avatar {
    filter: hue-rotate(10deg);
    animation: avatar-confused-tilt 1.5s infinite alternate ease-in-out;
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

/* --- Keyframe Animations for overall avatar --- */
@keyframes avatar-speaking-pulse-strong {
  0% { transform: scale(1); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
  100% { transform: scale(1.1); box-shadow: 0 8px 20px rgba(0,0,0,0.25); }
}
@keyframes avatar-speaking-bounce {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  50% { transform: translateY(-8px) rotate(-2deg); }
}

@keyframes avatar-happy-wobble {
  0%, 100% { transform: rotate(0deg) scale(1); }
  25% { transform: rotate(3deg) scale(1.02); }
  75% { transform: rotate(-3deg) scale(1.02); }
}

@keyframes avatar-selling-enthusiasm {
  0% { transform: translateY(0) scale(1); box-shadow: 0 4px 12px rgba(255, 193, 7, 0.2); }
  50% { transform: translateY(-10px) scale(1.05); box-shadow: 0 8px 25px rgba(255, 193, 7, 0.4); }
  100% { transform: translateY(0) scale(1); box-shadow: 0 4px 12px rgba(255, 193, 7, 0.2); }
}

@keyframes avatar-thinking-subtle {
  0%, 100% { transform: translateY(0) translateX(0); }
  25% { transform: translateY(-2px) translateX(2px); }
  75% { transform: translateY(2px) translateX(-2px); }
}

@keyframes avatar-confused-tilt {
  0%, 100% { transform: rotate(0deg) translateY(0); }
  50% { transform: rotate(-8deg) translateY(-5px); }
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