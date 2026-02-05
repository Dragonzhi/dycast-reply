
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

async def handler(websocket):
    print(f"Client connected from {websocket.remote_address}")
    try:
        async for message in websocket:
            # print(f"Received message: {message[:200]}...") # Uncomment for debugging raw messages
            try:
                # Messages are expected to be JSON strings of a list of DyMessage objects
                messages_data = json.loads(message)
                if not isinstance(messages_data, list):
                    # print("Warning: Received message is not a list. Skipping.")
                    continue

                for dy_message in messages_data:
                    if dy_message.get("method") == "WebcastChatMessage":
                        content = dy_message.get("content")
                        user_name = dy_message.get("user", {}).get("name", "Unknown User")
                        if content:
                            for keyword in KEYWORDS:
                                if keyword in content:
                                    print(f"!!! Keyword '{keyword}' detected from {user_name}: {content}")
                                    await get_ai_response(content)
            except json.JSONDecodeError:
                print("Error: Received message is not a valid JSON string.")
            except Exception as e:
                print(f"Error processing message: {e}")
    except websockets.exceptions.ConnectionClosedOK:
        print(f"Client from {websocket.remote_address} disconnected normally.")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"Client from {websocket.remote_address} disconnected with error: {e}.")
    except Exception as e:
        print(f"An unexpected error occurred with client {websocket.remote_address}: {e}")

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
