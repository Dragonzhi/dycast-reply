import asyncio
import websockets
import json
import os
from openai import OpenAI

# --- AI Configuration ---
# BASE_URL is for DeepSeek API
BASE_URL = "https://api.deepseek.com/v1"
MODEL = "deepseek-chat"

# Global variable for API key
API_KEY = None
keywords_config = {}

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
    try:
        with open(KEYWORD_CONFIG_FILE, 'r', encoding='utf-8') as f:
            keywords_config = json.load(f)
        print(f"[Backend] Loaded keyword configurations from {KEYWORD_CONFIG_FILE}.")
    except FileNotFoundError:
        print(f"[Backend] !!! Error: {KEYWORD_CONFIG_FILE} not found. Please create it.")
    except json.JSONDecodeError:
        print(f"[Backend] !!! Error: Could not decode {KEYWORD_CONFIG_FILE}. Check JSON format.")
    except Exception as e:
        print(f"[Backend] !!! An unexpected error occurred while loading {KEYWORD_CONFIG_FILE}: {e}")

# --- WebSocket Client Management ---
CONNECTED_CLIENTS = set()

async def broadcast_ai_response(ai_response_content: str):
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
    message_to_send = json.dumps(ai_message_for_frontend)
    
    # Create a list of tasks for sending messages
    tasks = [client.send(message_to_send) for client in CONNECTED_CLIENTS]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for result, client in zip(results, list(CONNECTED_CLIENTS)):
        if isinstance(result, Exception):
            print(f"[Backend] Error sending to client {client.remote_address}: {result}. Client will be removed.")
        else:
            print(f"[Backend] -> Sent AI response to client {client.remote_address}")

async def handler(websocket):
    CONNECTED_CLIENTS.add(websocket)
    print(f"[Backend] Client connected from {websocket.remote_address}. Total clients: {len(CONNECTED_CLIENTS)}")
    try:
        async for message in websocket:
            try:
                messages_data = json.loads(message)
                if not isinstance(messages_data, list):
                    continue

                for dy_message in messages_data:
                    if dy_message.get("method") == "WebcastChatMessage":
                        content = dy_message.get("content")
                        user_name = dy_message.get("user", {}).get("name", "Unknown User")
                        
                        if content:
                            ai_response_content = None
                            for keyword_text, config in keywords_config.items():
                                if keyword_text in content:
                                    print(f"[Backend] !!! Keyword '{keyword_text}' detected from {user_name}: {content}")
                                    
                                    # Construct AI prompt based on config, always involving the AI
                                    system_prompt_parts = ["你是一个直播间助手，你的名字叫“弹幕鸭”。请用友好、简洁、幽默的风格回答问题。"]
                                    
                                    # Add specific AI context from the keyword config
                                    ai_context = config.get("ai_context", "")
                                    if ai_context:
                                        system_prompt_parts.append(f"根据以下额外指示进行回复：{ai_context}")
                                    
                                    # Integrate response_template as a strong guideline or example
                                    response_template = config.get("response_template")
                                    if response_template:
                                        system_prompt_parts.append(f"请特别注意，当用户提到'{keyword_text}'时，可以参考以下内容进行回复，但要根据用户具体语境进行灵活调整：'{response_template}'")
                                    
                                    # Add product info if applicable
                                    if config.get("type") == "product_info":
                                        product_name = config.get("product_name", "商品")
                                        price = config.get("price", "未知价格")
                                        selling_method = config.get("selling_method", "请咨询主播")
                                        system_prompt_parts.append(f"产品信息：{product_name} 价格：{price}, 购买方式：{selling_method}。")

                                    # Combine all parts into the final system prompt
                                    final_system_prompt = "\n".join(system_prompt_parts)
                                    
                                    # The user message should always be the full content for contextual understanding
                                    ai_user_message = f"用户说：'{content}'。"

                                    ai_response_content = await get_ai_response(ai_user_message, final_system_prompt)
                                    
                                    if ai_response_content:
                                        await broadcast_ai_response(ai_response_content)
                                    break # Only respond to the first matched keyword
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
    print(f"Listening for configured keywords.")
    async with websockets.serve(handler, "localhost", 8080):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())