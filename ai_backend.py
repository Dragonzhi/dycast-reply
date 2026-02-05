
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

async def get_ai_response(user_message: str):
    """
    Calls the DeepSeek API to get an AI response.
    """
    if not API_KEY:
        print("!!! API Key is not set. Cannot call AI API.")
        return None

    print(f"-> Sending to AI: '{user_message}'")
    try:
        # Initialize the OpenAI client with the provided API key and DeepSeek base URL
        client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "你是一个直播间助手，你的名字叫“弹幕鸭”。请用友好、简洁、幽默的风格回答问题。"},
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

# Define your keywords here
KEYWORDS = ["测试", "你好", "AI", "关键词"]

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
            # The connection will be properly closed by the handler's finally block
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
                            for keyword in KEYWORDS:
                                if keyword in content:
                                    print(f"[Backend] !!! Keyword '{keyword}' detected from {user_name}: {content}")
                                    ai_response_content = await get_ai_response(content)
                                    if ai_response_content:
                                        await broadcast_ai_response(ai_response_content)
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

    print("Starting AI WebSocket backend on ws://localhost:8080")
    print(f"Listening for keywords: {KEYWORDS}")
    async with websockets.serve(handler, "localhost", 8080):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
