import asyncio
import websockets
import json
import os
import re
import base64
import requests # For Aliyun DashScope API calls and downloading audio from URL
import dashscope # Aliyun DashScope SDK
from http import HTTPStatus # For checking API response status
import wave # To read WAV header for sampling rate

from openai import OpenAI

# --- AI Configuration ---
# BASE_URL is for DeepSeek API
BASE_URL = "https://api.deepseek.com/v1"
MODEL = "deepseek-chat"

# --- DashScope TTS Configuration ---
DASHSCOPE_API_KEY = None
QWEN_TTS_MODEL_NAME = "qwen3-tts-flash" # Use the recommended flash model
QWEN_TTS_VOICE_NAME = "Cherry" # Default voice, can be changed. Examples: "Cherry", "Ryan", "Tina", "Xiaoice"
QWEN_TTS_LANGUAGE = "Chinese" # Default language, "Chinese", "English"

# Global variable for DeepSeek API key
DEEPSEEK_API_KEY = None # Renamed from API_KEY for clarity

keywords_config = {}
ai_settings = {} # Global for AI specific settings
full_config = {} # Global to store the entire loaded config for frontend management

async def get_ai_response(user_message: str, system_message: str = "你是一个直播间助手，你的名字叫“弹幕鸭”。请用友好、简洁、幽默的风格回答问题。"):
    """
    Calls the DeepSeek API to get an AI response.
    Returns a tuple of (message, mood).
    """
    if not DEEPSEEK_API_KEY:
        print("!!! DeepSeek API Key is not set. Cannot call AI API.")
        return None, None

    mood_instruction = "在回答的开头，请务必根据你的回复内容和情绪，在以下标签中选择最合适的一个，并将其作为前缀：[happy], [neutral], [selling], [confused], [thinking]。例如：[happy]你好呀！很高兴为你服务。"
    full_system_prompt = f"{system_message}\n\n{mood_instruction}"

    print(f"-> Sending to AI: '{user_message}' with system prompt: '{full_system_prompt}'")
    try:
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=BASE_URL)
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": full_system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.7,
            max_tokens=100
        )
        ai_response_text = response.choices[0].message.content
        
        mood = "neutral"
        match = re.match(r"\[(\w+)\]", ai_response_text)
        if match:
            mood = match.group(1)
            ai_message = ai_response_text[len(match.group(0)):].strip()
        else:
            ai_message = ai_response_text.strip()
            
        print(f"<- AI Response (Mood: {mood}): {ai_message}")
        return ai_message, mood
        
    except Exception as e:
        print(f"!!! Error calling AI API: {e}")
        return None, None


def synthesize_dashscope_tts(text: str):
    """
    Synthesizes speech from text using Aliyun DashScope Qwen-TTS API.
    Downloads the audio from the provided URL in the response.
    Returns a tuple of (WAV audio bytes, sampling rate).
    """
    if not DASHSCOPE_API_KEY:
        print("!!! DashScope API Key is not set. Cannot synthesize speech.")
        return None, None
    
    dashscope.api_key = DASHSCOPE_API_KEY
    # Assuming DashScope base_http_api_url is set in main() for China region

    print(f"[DashScope TTS] Synthesizing speech for: '{text}' (Voice: {QWEN_TTS_VOICE_NAME}, Lang: {QWEN_TTS_LANGUAGE})")
    try:
        response = dashscope.MultiModalConversation.call(
            model=QWEN_TTS_MODEL_NAME,
            text=text,
            voice=QWEN_TTS_VOICE_NAME,
            language_type=QWEN_TTS_LANGUAGE,
        )

        if response.status_code == HTTPStatus.OK:
            if hasattr(response.output, 'audio') and hasattr(response.output.audio, 'url') and response.output.audio.url:
                audio_url = response.output.audio.url
                print(f"[DashScope TTS] Audio URL received: {audio_url}")
                
                # Download audio from the URL
                audio_download_response = requests.get(audio_url, stream=True)
                if audio_download_response.status_code == HTTPStatus.OK:
                    wav_bytes = audio_download_response.content
                    
                    # Try to get sampling rate from WAV header
                    sampling_rate = 16000 # Default assumption
                    try:
                        with wave.open(io.BytesIO(wav_bytes), 'rb') as wf:
                            sampling_rate = wf.getframerate()
                    except Exception as e:
                        print(f"[DashScope TTS] Could not read sampling rate from WAV header, using default 16000Hz: {e}")

                    print(f"[DashScope TTS] Speech synthesized and downloaded successfully. (Sampling Rate: {sampling_rate})")
                    return wav_bytes, sampling_rate
                else:
                    print(f"[DashScope TTS] Failed to download audio from URL. Status: {audio_download_response.status_code}")
                    return None, None
            else:
                print(f"[DashScope TTS] API call successful, but no audio URL found in response: {response.output}")
                return None, None
        else:
            print(f"[DashScope TTS] API call failed, status: {response.status_code}, message: {response.message}")
            return None, None

    except Exception as e:
        print(f"[DashScope TTS] Error during speech synthesis: {e}")
        return None, None


KEYWORD_CONFIG_FILE = "keywords_config.json"

def load_keywords_config():
    global keywords_config, ai_settings, full_config
    try:
        with open(KEYWORD_CONFIG_FILE, 'r', encoding='utf-8') as f:
            full_config = json.load(f)
            keywords_config = {k: v for k, v in full_config.items() if k != "ai_settings"}
            ai_settings = full_config.get("ai_settings", {})
        print(f"[Backend] Loaded keyword configurations from {KEYWORD_CONFIG_FILE}.")
        print(f"[Backend] AI Settings: {ai_settings}")
    except FileNotFoundError:
        print(f"[Backend] !!! Error: {KEYWORD_CONFIG_FILE} not found. Please create it.")
        full_config = {
            "ai_settings": {
                "response_mode": "keyword",
                "filtering_enabled": True,
                "min_message_length": 4,
                "meaningless_patterns": [],
                "free_qa_persona_prompt": "你是一个直播间助手，名字叫弹幕鸭。请用友好、简洁、幽默的风格回答问题。"
            }
        }
        keywords_config = {}
        ai_settings = full_config["ai_settings"]
        save_keywords_config(full_config)
    except json.JSONDecodeError:
        print(f"[Backend] !!! Error: Could not decode {KEYWORD_CONFIG_FILE}. Check JSON format.")
    except Exception as e:
        print(f"[Backend] !!! An unexpected error occurred while loading {KEYWORD_CONFIG_FILE}: {e}")

def save_keywords_config(config_data: dict):
    try:
        with open(KEYWORD_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)
        print(f"[Backend] Saved keyword configurations to {KEYWORD_CONFIG_FILE}.")
    except Exception as e:
        print(f"[Backend] !!! Error saving keyword configurations: {e}")


# --- WebSocket Client Management ---
CONNECTED_CLIENTS = set()

async def broadcast_ai_response(ai_response_content: str, mood: str, audio_data_raw: bytes, sampling_rate: int, original_comment_data: dict = None):
    """
    Broadcasts the AI response to all connected clients.
    `audio_data_raw` is expected to be raw WAV bytes.
    """
    if not CONNECTED_CLIENTS:
        print("[Backend] No clients connected to broadcast to.")
        return

    # Base64 encode the audio data here, just before sending
    audio_base64 = base64.b64encode(audio_data_raw).decode('utf-8')

    ai_message_for_frontend = {
        "type": "ai_response",
        "content": ai_response_content,
        "mood": mood,
        "original_comment": original_comment_data,
        "audio_base64": audio_base64,
        "sampling_rate": sampling_rate
    }
    
    message_to_send = json.dumps(ai_message_for_frontend, ensure_ascii=False)
    
    tasks = [client.send(message_to_send) for client in CONNECTED_CLIENTS]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for result, client in zip(results, list(CONNECTED_CLIENTS)):
        if isinstance(result, Exception):
            print(f"[Backend] Error sending to client {client.remote_address}: {result}. Client will be removed.")
        else:
            print(f"[Backend] -> Sent AI response with audio to client {client.remote_address}")

# Helper to check if a message is considered "meaningless"
def is_meaningless(message: str) -> bool:
    if not ai_settings.get("filtering_enabled", False):
        return False
    min_length = ai_settings.get("min_message_length", 4)
    if len(message) < min_length: return True
    meaningless_patterns = ai_settings.get("meaningless_patterns", [])
    for pattern in meaningless_patterns:
        if pattern == message.strip() or (len(message.strip()) <= len(pattern) + 2 and pattern in message): return True
        try:
            if re.search(re.escape(pattern), message, re.IGNORECASE):
                if len(message.strip()) / len(pattern) < 2: return True
        except re.error: pass
    if len(message) > 2 and len(set(message.lower())) <= 2: return True
    return False

async def handler(websocket):
    CONNECTED_CLIENTS.add(websocket)
    print(f"[Backend] Client connected from {websocket.remote_address}. Total clients: {len(CONNECTED_CLIENTS)}")
    try:
        async for message in websocket:
            try:
                message_obj = json.loads(message)

                if isinstance(message_obj, dict) and message_obj.get("action"):
                    action = message_obj["action"]
                    if action == "get_config":
                        await websocket.send(json.dumps({"type": "config_update", "data": full_config}, ensure_ascii=False))
                        print("[Backend] Sent config to client.")
                        continue
                    elif action == "save_config" and "data" in message_obj:
                        save_keywords_config(message_obj["data"])
                        load_keywords_config()
                        await websocket.send(json.dumps({"type": "config_saved", "message": "Configuration saved and reloaded."}, ensure_ascii=False))
                        print("[Backend] Received and saved new config from client.")
                        continue
                    elif action == "test_speech" and "text" in message_obj:
                        # Handle test speech request
                        test_text = message_obj["text"]
                        test_mood = message_obj.get("mood", "neutral")
                        # Use new DashScope TTS function
                        wav_bytes, sampling_rate = synthesize_dashscope_tts(test_text)
                        if wav_bytes and sampling_rate:
                            await broadcast_ai_response(test_text, test_mood, wav_bytes, sampling_rate, {"user_name": "测试用户", "text": "语音测试"})
                        continue

                
                if not isinstance(message_obj, list): continue

                for dy_message in message_obj:
                    if dy_message.get("method") == "WebcastChatMessage":
                        content = dy_message.get("content")
                        user_name = dy_message.get("user", {}).get("name", "Unknown User")
                        
                        if content:
                            ai_response_content, mood = None, "neutral"
                            original_comment_info = {"user_name": user_name, "text": content}
                            response_mode = ai_settings.get("response_mode", "keyword")

                            if response_mode == "free_qa":
                                if is_meaningless(content):
                                    print(f"[Backend] Skipped meaningless message from {user_name}: {content}")
                                    continue
                                print(f"[Backend] Free Q&A mode: Processing message from {user_name}: {content}")
                                persona_prompt = ai_settings.get("free_qa_persona_prompt", "你是一个直播间助手，你的名字叫“弹幕鸭”。请用友好、简洁、幽默的风格回答问题。")
                                ai_response_content, mood = await get_ai_response(f"用户说：'{content}'。", persona_prompt)

                            else: # Keyword mode
                                matched_configs = [(kw, cfg) for kw, cfg in keywords_config.items() if kw in content]
                                if matched_configs:
                                    system_prompt_parts = ["你是一个直播间助手，你的名字叫“弹幕鸭”。请用友好、简洁、幽默的风格回答问题。"]
                                    all_ai_contexts, all_response_templates, all_product_infos = [], [], []
                                    for kw, cfg in matched_configs:
                                        print(f"[Backend] !!! Keyword '{kw}' detected from {user_name}: {content}")
                                        if cfg.get("ai_context"): all_ai_contexts.append(cfg["ai_context"])
                                        if cfg.get("response_template"): all_response_templates.append(f"当用户提到'{kw}'时，可以参考以下内容：'{cfg['response_template']}'")
                                        if cfg.get("type") == "product_info":
                                            all_product_infos.append(f"{cfg.get('product_name', '商品')} 价格: {cfg.get('price', '未知价格')}, 购买方式: {cfg.get('selling_method', '请咨询主播')}")
                                    if all_ai_contexts: system_prompt_parts.append(f"根据以下额外指示进行回复：{' '.join(all_ai_contexts)}")
                                    if all_response_templates: system_prompt_parts.append(f"请特别注意，综合参考以下内容进行回复，并根据用户具体语境进行灵活调整：{' '.join(all_response_templates)}")
                                    if all_product_infos: system_prompt_parts.append(f"以下是用户可能感兴趣的产品信息：{' '.join(all_product_infos)}。请根据用户提问，结合这些信息进行回答。")
                                    
                                    final_system_prompt = "\n".join(system_prompt_parts)
                                    ai_response_content, mood = await get_ai_response(f"用户说：'{content}'。", final_system_prompt)
                            
                            if ai_response_content:
                                # Synthesize speech with DashScope Qwen-TTS API
                                wav_bytes, sampling_rate = synthesize_dashscope_tts(ai_response_content)
                                if wav_bytes is not None and sampling_rate is not None:
                                    await broadcast_ai_response(ai_response_content, mood, wav_bytes, sampling_rate, original_comment_info)

            except json.JSONDecodeError: pass
            except Exception as e: print(f"[Backend] Error processing message: {e}")
    finally:
        CONNECTED_CLIENTS.remove(websocket)
        print(f"[Backend] Client disconnected from {websocket.remote_address}. Total clients: {len(CONNECTED_CLIENTS)}")

async def main():
    global DEEPSEEK_API_KEY, DASHSCOPE_API_KEY
    
    DEEPSEEK_API_KEY = input("请A输入 DeepSeek API Key: ").strip()
    if not DEEPSEEK_API_KEY:
        print("未提供 DeepSeek API Key。退出。")
        return

    DASHSCOPE_API_KEY = input("请B输入 DashScope API Key: ").strip()
    if not DASHSCOPE_API_KEY:
        print("未提供 DashScope API Key。退出。")
        return

    # Set DashScope API key globally for the SDK
    dashscope.api_key = DASHSCOPE_API_KEY
    # For models in China (Beijing) region, it's 'https://dashscope.aliyuncs.com/api/v1'
    # Ensure this is set correctly based on the model's region
    dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'


    load_keywords_config()
    
    print("启动 AI WebSocket 后端在 ws://localhost:8080")
    print(f"当前响应模式: {ai_settings.get('response_mode', 'keyword')}")
    if ai_settings.get("response_mode") == "keyword":
        print(f"监听 {len(keywords_config)} 个已配置的关键词。")
    else:
        print(f"自由问答模式已启用，过滤: {ai_settings.get('filtering_enabled', False)}")
        
    async with websockets.serve(handler, "localhost", 8080):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())