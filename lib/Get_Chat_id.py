#### Sc para recuperar el id de un chat. Solo se usa para la configuración inicial, o debug. No forma parte del flujo normal de la aplicación.

import httpx
from config import get_settings

s = get_settings()
base = f"https://api.telegram.org/bot{s.telegram_bot_token}"
print("Base URL:", base)
print ("Chat ID:", s.telegram_chat_id)
print("------------------------------")
with httpx.Client(timeout=30.0) as client:
    r = client.get(f"{base}/getMe")
    print("getMe:", r.json())

    r2 = client.get(f"{base}/getUpdates")
    print("getUpdates:", r2.json())