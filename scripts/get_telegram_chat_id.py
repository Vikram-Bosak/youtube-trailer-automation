"""
Get Telegram Chat ID Helper Script
Run this after adding the bot to your group and sending a message.
"""

import requests
import sys
import time

BOT_TOKEN = "8221183632:AAGPdTvUlY2w2zUpGPXzAfucOi-1Hze9PaA"

def get_chat_id():
    """Get chat IDs from bot updates."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    
    print("🔍 Checking for messages...")
    print("⚠️  If no chat ID found, please:")
    print("   1. Add @yttrailerautobot to your group")
    print("   2. Send any message in the group")
    print("   3. Run this script again")
    print()
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if not data.get("ok"):
            print(f"❌ API Error: {data}")
            return
        
        results = data.get("result", [])
        
        if not results:
            print("❌ No messages found. Please send a message in the group first!")
            return
        
        seen_chats = set()
        for update in results:
            # Check for message
            if "message" in update:
                chat = update["message"]["chat"]
            elif "my_chat_member" in update:
                chat = update["my_chat_member"]["chat"]
            else:
                continue
            
            chat_id = chat.get("id")
            if chat_id and chat_id not in seen_chats:
                seen_chats.add(chat_id)
                chat_type = chat.get("type", "unknown")
                chat_title = chat.get("title", chat.get("username", "Private"))
                print(f"✅ Found Chat ID: {chat_id}")
                print(f"   Type: {chat_type}")
                print(f"   Name: {chat_title}")
                print()
        
        if seen_chats:
            print(f"📋 Add this to your .env file:")
            print(f"   TELEGRAM_CHAT_ID={list(seen_chats)[0]}")
        else:
            print("❌ No chat IDs found")
    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    get_chat_id()
