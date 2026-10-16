import websocket
import sys

def on_message(ws, message):
    print(f"Received: {message}")

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("Connection closed")

def on_open(ws):
    print("Connection opened")
    # Optionally send a message or just wait
    # ws.send('{"action": "list"}')  # Example, but we don't know the exact format

if __name__ == "__main__":
    ws_url = "ws://localhost:8000/ws/comments/"
    print(f"Connecting to {ws_url}")
    ws = websocket.WebSocketApp(ws_url,
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.run_forever()