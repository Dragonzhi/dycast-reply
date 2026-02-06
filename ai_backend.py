import asyncio
import websockets
import json
import os
import re # Import regex module
from openai import OpenAI

# --- AI Configuration ---
# BASE_URL is for DeepSeek API
BASE_URL = "https://api.deepseek.com/v1"
MODEL = "deepseek-chat"

# Global variable for API key
API_KEY = None
keywords_config = {}
ai_settings = {} # Global for AI specific settings
full_config = {} # Global to store the entire loaded config for frontend management

async def get_ai_response(user_message: str, system_message: str = "你是一个直播间助手，你的名字叫“弹幕鸭”。请用友好、简洁、幽默的风格回答问题。"):
    """
    Calls the DeepSeek API to get an AI response.
    Returns a tuple of (message, mood).
    """
    if not API_KEY:
        print("!!! API Key is not set. Cannot call AI API.")
        return None, None

    # Add instruction for mood tagging to the system prompt
    mood_instruction = "在回答的开头，请务必根据你的回复内容和情绪，在以下标签中选择最合适的一个，并将其作为前缀：[happy], [neutral], [selling], [confused], [thinking]。例如：[happy]你好呀！很高兴为你服务。"
    full_system_prompt = f"{system_message}\n\n{mood_instruction}"

    print(f"-> Sending to AI: '{user_message}' with system prompt: '{full_system_prompt}'")
    try:
        client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
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
        
        # Parse mood tag from the response
        mood = "neutral" # Default mood
        match = re.match(r"\[(\w+)\]", ai_response_text)
        if match:
            mood = match.group(1)
            # Remove the tag from the message
            ai_message = ai_response_text[len(match.group(0)):].strip()
        else:
            ai_message = ai_response_text.strip()
            
        print(f"<- AI Response (Mood: {mood}): {ai_message}")
        return ai_message, mood
        
    except Exception as e:
        print(f"!!! Error calling AI API: {e}")
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

async def broadcast_ai_response(ai_response_content: str, mood: str, original_comment_data: dict = None):
    """
    Broadcasts the AI response to all connected clients.
    """
    if not CONNECTED_CLIENTS:
        print("[Backend] No clients connected to broadcast to.")
        return

    ai_message_for_frontend = {
        "type": "ai_response",
        "content": ai_response_content,
        "mood": mood,
        "original_comment": original_comment_data
    }
    
    message_to_send = json.dumps(ai_message_for_frontend, ensure_ascii=False)
    
    tasks = [client.send(message_to_send) for client in CONNECTED_CLIENTS]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for result, client in zip(results, list(CONNECTED_CLIENTS)):
        if isinstance(result, Exception):
            print(f"[Backend] Error sending to client {client.remote_address}: {result}. Client will be removed.")
        else:
            print(f"[Backend] -> Sent AI response to client {client.remote_address}")

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
                                await broadcast_ai_response(ai_response_content, mood, original_comment_info)

            except json.JSONDecodeError: pass
            except Exception as e: print(f"[Backend] Error processing message: {e}")
    finally:
        CONNECTED_CLIENTS.remove(websocket)
        print(f"[Backend] Client disconnected from {websocket.remote_address}. Total clients: {len(CONNECTED_CLIENTS)}")

async def main():
    global API_KEY
    API_KEY = input("Please enter your DeepSeek API Key: ").strip()
    if not API_KEY:
        print("No API Key provided. Exiting.")
        return

    load_keywords_config()
    print("Starting AI WebSocket backend on ws://localhost:8080")
    print(f"Current response mode: {ai_settings.get('response_mode', 'keyword')}")
    if ai_settings.get("response_mode") == "keyword":
        print(f"Listening for {len(keywords_config)} configured keywords.")
    else:
        print(f"Free Q&A mode enabled with filtering: {ai_settings.get('filtering_enabled', False)}")
        
    async with websockets.serve(handler, "localhost", 8080):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())