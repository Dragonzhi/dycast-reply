
import asyncio
import websockets
import json

# Define your keywords here
KEYWORDS = ["测试", "你好", "AI", "关键词"]

async def handler(websocket):
    print(f"Client connected from {websocket.remote_address}")
    try:
        async for message in websocket:
            print(f"Received message: {message[:200]}...") # Print first 200 chars to avoid flooding
            try:
                # Messages are expected to be JSON strings of a list of DyMessage objects
                messages_data = json.loads(message)
                if not isinstance(messages_data, list):
                    print("Warning: Received message is not a list. Skipping.")
                    continue

                for dy_message in messages_data:
                    if dy_message.get("method") == "WebcastChatMessage":
                        content = dy_message.get("content")
                        user_name = dy_message.get("user", {}).get("name", "Unknown User")
                        if content:
                            for keyword in KEYWORDS:
                                if keyword in content:
                                    print(f"!!! Keyword '{keyword}' detected from {user_name}: {content}")
                                    # Here you would integrate with your AI model
                                    # For now, just print a response
                                    # Example: await websocket.send(f"AI received '{content}' and detected '{keyword}'")
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
    print("Starting WebSocket server on ws://localhost:8080")
    async with websockets.serve(handler, "localhost", 8080):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
