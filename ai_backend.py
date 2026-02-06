
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
    """
    if not API_KEY:
        print("!!! API Key is not set. Cannot call AI API.")
        return None

    print(f"-> Sending to AI: '{user_message}' with system prompt: '{system_message}'")
    try:
        # Initialize the OpenAI client with the provided API key and DeepSeek base URL
        client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            temperature=0.7,
            max_tokens=100
        )
        ai_message = response.choices[0].message.content
        print(f"<- AI Response: {ai_message}")
        return ai_message
    except Exception as e:
        print(f"!!! Error calling AI API: {e}")
        return None


KEYWORD_CONFIG_FILE = "keywords_config.json"

def load_keywords_config():
    global keywords_config
    global ai_settings
    global full_config
    try:
        with open(KEYWORD_CONFIG_FILE, 'r', encoding='utf-8') as f:
            full_config = json.load(f)
            keywords_config = {k: v for k, v in full_config.items() if k != "ai_settings"}
            ai_settings = full_config.get("ai_settings", {})
        print(f"[Backend] Loaded keyword configurations from {KEYWORD_CONFIG_FILE}.")
        print(f"[Backend] AI Settings: {ai_settings}")
    except FileNotFoundError:
        print(f"[Backend] !!! Error: {KEYWORD_CONFIG_FILE} not found. Please create it.")
        # Initialize with default structure if not found
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
        save_keywords_config(full_config) # Save the default config
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

async def broadcast_ai_response(ai_response_content: str, original_comment_data: dict = None):
    """
    Broadcasts the AI response to all connected clients.
    """
    if not CONNECTED_CLIENTS:
        print("[Backend] No clients connected to broadcast to.")
        return

    ai_message_for_frontend = {
        "type": "ai_response",
        "content": ai_response_content
    }
    if original_comment_data:
        ai_message_for_frontend["original_comment"] = original_comment_data

    message_to_send = json.dumps(ai_message_for_frontend)
    
    # Create a list of tasks for sending messages
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
    if len(message) < min_length:
        return True
    
    meaningless_patterns = ai_settings.get("meaningless_patterns", [])
    for pattern in meaningless_patterns:
        # Simple check for exact match or if pattern is substantially the message
        if pattern == message.strip() or (len(message.strip()) <= len(pattern) + 2 and pattern in message):
             return True
        # More robust regex check if pattern is complex, assuming simple patterns for now
        # You might want to compile these regexes once for performance
        try:
            # Using re.escape to handle special regex characters in user-defined patterns
            if re.search(re.escape(pattern), message, re.IGNORECASE):
                # If the pattern is a significant part of the message, consider it meaningless
                if len(message.strip()) / len(pattern) < 2: 
                    return True
        except re.error:
            # Handle invalid regex patterns if they somehow get into config
            pass
            
    # Check for messages that are mostly repetition of a character (e.g., "aaaaa" or ".........")
    if len(message) > 2 and len(set(message.lower())) <= 2: # e.g., "666" or "。。。。。"
        return True
            
    return False

async def handler(websocket):
    CONNECTED_CLIENTS.add(websocket)
    print(f"[Backend] Client connected from {websocket.remote_address}. Total clients: {len(CONNECTED_CLIENTS)}")
    try:
        async for message in websocket:
            try:
                message_obj = json.loads(message)

                # --- Handle Config Management Messages ---
                if isinstance(message_obj, dict) and message_obj.get("action"):
                    action = message_obj["action"]
                    if action == "get_config":
                        await websocket.send(json.dumps({"type": "config_update", "data": full_config}, ensure_ascii=False))
                        print("[Backend] Sent config to client.")
                        continue # Process next message

                    elif action == "save_config" and "data" in message_obj:
                        new_config_data = message_obj["data"]
                        save_keywords_config(new_config_data)
                        load_keywords_config() # Reload for backend to use new settings
                        # Optionally, broadcast new config to all clients or send confirmation
                        print("[Backend] Received and saved new config from client.")
                        await websocket.send(json.dumps({"type": "config_saved", "message": "Configuration saved and reloaded."}, ensure_ascii=False))
                        continue # Process next message
                
                # --- Handle Dycast Chat Messages ---
                if not isinstance(message_obj, list): # Check if it's a list of dycast messages
                    continue

                for dy_message in message_obj: # Iterate through dycast messages
                    if dy_message.get("method") == "WebcastChatMessage":
                        content = dy_message.get("content")
                        user_name = dy_message.get("user", {}).get("name", "Unknown User")
                        
                        if content:
                            ai_response_content = None
                            original_comment_info = {
                                "user_name": user_name,
                                "text": content
                            }
                            response_mode = ai_settings.get("response_mode", "keyword")

                            if response_mode == "free_qa":
                                if is_meaningless(content):
                                    print(f"[Backend] Skipped meaningless message from {user_name}: {content}")
                                    continue # Skip this message
                                
                                print(f"[Backend] Free Q&A mode: Processing message from {user_name}: {content}")
                                # Use free_qa_persona_prompt if available, otherwise fallback to default
                                persona_prompt = ai_settings.get("free_qa_persona_prompt", "你是一个直播间助手，你的名字叫“弹幕鸭”。请用友好、简洁、幽默的风格回答问题。")
                                system_prompt_parts = [persona_prompt]
                                final_system_prompt = "\n".join(system_prompt_parts)
                                ai_user_message = f"用户说：'{content}'。"
                                ai_response_content = await get_ai_response(ai_user_message, final_system_prompt)

                            else: # Default or "keyword" mode
                                matched_configs = []
                                for keyword_text, config in keywords_config.items():
                                    if keyword_text in content:
                                        matched_configs.append((keyword_text, config))

                                if matched_configs:
                                    # Construct AI prompt based on all matched configs
                                    system_prompt_parts = ["你是一个直播间助手，你的名字叫“弹幕鸭”。请用友好、简洁、幽默的风格回答问题。"]
                                    
                                    # Collect and synthesize information from all matched keywords
                                    all_ai_contexts = []
                                    all_response_templates = []
                                    all_product_infos = []

                                    for keyword_text, config in matched_configs:
                                        print(f"[Backend] !!! Keyword '{keyword_text}' detected from {user_name}: {content}")
                                        
                                        ai_context = config.get("ai_context", "")
                                        if ai_context:
                                            all_ai_contexts.append(ai_context)
                                        
                                        response_template = config.get("response_template")
                                        if response_template:
                                            all_response_templates.append(f"当用户提到'{keyword_text}'时，可以参考以下内容：'{response_template}'")
                                        
                                        if config.get("type") == "product_info":
                                            product_name = config.get("product_name", "商品")
                                            price = config.get("price", "未知价格")
                                            selling_method = config.get("selling_method", "请咨询主播")
                                            all_product_infos.append(f"{product_name} 价格: {price}, 购买方式: {selling_method}")
                                    
                                    if all_ai_contexts:
                                        system_prompt_parts.append(f"根据以下额外指示进行回复：{' '.join(all_ai_contexts)}")
                                    
                                    if all_response_templates:
                                        system_prompt_parts.append(f"请特别注意，综合参考以下内容进行回复，并根据用户具体语境进行灵活调整：{' '.join(all_response_templates)}")
                                    
                                    if all_product_infos:
                                        system_prompt_parts.append(f"以下是用户可能感兴趣的产品信息：{' '.join(all_product_infos)}。请根据用户提问，结合这些信息进行回答。")

                                    final_system_prompt = "\n".join(system_prompt_parts)
                                    ai_user_message = f"用户说：'{content}'。"

                                    ai_response_content = await get_ai_response(ai_user_message, final_system_prompt)
                            
                            if ai_response_content:
                                await broadcast_ai_response(ai_response_content, original_comment_info)

            except json.JSONDecodeError:
                # This message is not from dycast, maybe from AI assistant page itself, ignore.
                pass
            except Exception as e:
                print(f"[Backend] Error processing message: {e}")
    finally:
        CONNECTED_CLIENTS.remove(websocket)
        print(f"[Backend] Client disconnected from {websocket.remote_address}. Total clients: {len(CONNECTED_CLIENTS)}")


async def main():
    global API_KEY
    API_KEY = input("Please enter your DeepSeek API Key: ").strip()
    if not API_KEY:
        print("No API Key provided. Exiting.")
        return

    load_keywords_config() # Load configurations before starting

    print("Starting AI WebSocket backend on ws://localhost:8080")
    print(f"Current response mode: {ai_settings.get('response_mode', 'keyword')}")
    if ai_settings.get("response_mode") == "keyword":
        print(f"Listening for {len(keywords_config)} configured keywords.")
    else:
        print(f"Free Q&A mode enabled with filtering: {ai_settings.get('filtering_enabled', False)}")
        
    async with websockets.serve(handler, "localhost", 8080):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
