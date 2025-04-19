import os
import httpx
import jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv

print("[DEBUG] jwt module location:", jwt.__file__)

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

def send_webhook(data):
    token = jwt.encode(
        {"sub": "bizBackWebhook", "exp": datetime.utcnow() + timedelta(minutes=5)},
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    url = data["webhookUrl"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        with httpx.Client(verify=False) as client:
            response = client.post(url, json=data, headers=headers)
            print(f"[WORKER] ✅ Webhook sent to {url} → {response.status_code}")
            response.raise_for_status()
    except Exception as e:
        print(f"[WORKER ERROR] ❌ {e}")
        raise e  # RQ will retry