from redis import Redis
from rq import Queue
from webhook_worker import send_webhook
from datetime import datetime
from dotenv import load_dotenv
import os
from datetime import datetime, timezone

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

print("[DEBUG] Starting webhook test")

redis_conn = Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD
    )

q = Queue("webhookQueue", connection=redis_conn)

result = {
    "verificationId": "test-123",
    "customerName": "Ayed",
    "webhookUrl": "https://localhost:15000/api/verificationResult",
    "timestamp": datetime.now(timezone.utc).isoformat()
}

job = q.enqueue(send_webhook, result)
print(f"[MAIN] Job queued: {job.id}")
