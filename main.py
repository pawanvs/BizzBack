# main.py - FastAPI server with RQ-based webhook delivery, HTTPS, JWT Auth, and MongoDB

from fastapi import FastAPI, Request, HTTPException, Depends, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from jose import JWTError, jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
import motor.motor_asyncio
import asyncio
import os
import uvicorn
from redis import Redis
from rq import Queue, Retry
from webhook_worker import send_webhook
from fastapi.responses import JSONResponse

# Load environment variables
load_dotenv()

# Configuration
PORT = int(os.getenv("PORT", "18000"))
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
MONGO_URI = os.getenv("MONGO_URI")
SSL_KEYFILE = os.getenv("SSL_KEYFILE", "certs/key.pem")
SSL_CERTFILE = os.getenv("SSL_CERTFILE", "certs/cert.pem")
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

# MongoDB Client
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client["bizzBackend"]
users_collection = db["users"]

# FastAPI app
app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    username: str
    password: str

class CustomerInfo(BaseModel):
    purchaseOrder: str
    company: str
    dispatcher: str
    customerName: str
    customerPhone: str
    vehicleModel: str
    serviceCategory: str
    reason: str
    towSource: str
    towDestination: str
    wheelLiftAvailable: str
    flatBedAvailable: str
    jobEta: str
    customerNeedsRide: str
    serviceType: str
    towReportId: str
    notes: str

async def get_user(username: str):
    return await users_collection.find_one({"username": username})

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(status_code=401, detail="Could not validate credentials")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = await get_user(username)
    if user is None:
        raise credentials_exception
    return user

@app.post("/register")
async def register(user: User):
    existing_user = await users_collection.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    await users_collection.insert_one(user.dict())
    return {"msg": "User registered successfully"}

@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await get_user(form_data.username)
    if not user or user["password"] != form_data.password:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/status")
def status():
    return JSONResponse(content={"status": "ok", "service": "BizBack"})

@app.get("/")
async def root():
    return {"message": "Server is running"}

@app.get("/apiServerHealth")
async def api_server_health():
    return {"status": "healthy"}

@app.post("/verifyCustomerInfo2_simulation")
async def verify_customer_info(payload: CustomerInfo, user: dict = Depends(get_current_user)):
    print(f"[LOG] POST /verifyCustomerInfo - Received payload: {payload.dict()}")
    await asyncio.sleep(10)
    response = {
        "Customer Name": "Martin Briggs",
        "Agent Name": "Jessica",
        "Company": "ABC Towing",
        "Service Requested": "Jumpstart",
        "Vehicle Location": "10692 World Place San Diego 92126",
        "ETA": "30 minutes",
        "Call Outcome": "Confirmed jumpstart service request. Customer was satisfied and engaged positively with the agent.",
        "PurchaseOrder": "88025677bond",
        "outBoundCallNumber": "123456789",
        "gdslt": "GqtMhfVpMllaJ10KLZrSe61b",
        "callDurationMin": "94",
        "userSentiment": "Positive",
        "disconnectReason": "agent_hangup",
        "transcript": "Agent: Hi Martin Briggs, I'm Jessica from ABC Towing. This call is with regards to your Jumpstart request. Are you in a safe place?User: Yes. I am. Thanks for asking. Appreciate it.Agent: I'm glad to hear that, Martin! Now, do you know when was the last time you replaced your battery?User: No clue.Agent: No problem at all! Just a quick question—do you need a jump start, or might you also need a tow?User: Let's start with jump start. If it doesn't work, I might need it to.Agent: Got it! We'll start with the jump start. Just to confirm, will you be at the location of the vehicle?User: Yes, I am.Agent: Perfect! Now, I just need to confirm a couple of details. The address I have for the vehicle's current location is 10692 World Place San Diego 92126. Is that correct?User: You got it.Agent: Thank you for confirming that, Martin! Your ETA for the jump start service is 30 minutes. You should hear from the driver when they are 10 to 15 minutes away from your location.Is there anything else I can help you with?User: No. That's good. Maybe tell me a joke.Agent: I'm glad to hear that, Martin! Here’s a light-hearted joke for you: Why did the bicycle fall over? Because it was two-tired!Take care, and if you need anything else, just let us know. Have a great day!I'll go ahead and wrap up the call now.Agent: Thank you for your time, Martin Briggs. Have a great day!",
        "response": "SUCCESS",
        "Purchase_Order": "88025677",
        "Tow_Destination": "",
        "CallOutcome": "Confirmed jumpstart service request. Customer was satisfied and engaged positively with the agent.",
        "Reason": "Jumpstart",
        "CallScore": "60",
        "CallScoreReview": "Positive",
        "additionalInformation": " --------------------- <br/><br/> --------------------- ",
        "additional_Information": " --------------------- <br/><br/> --------------------- "
    }
    print(f"[LOG] POST /verifyCustomerInfo - Responding with static response")
    return response

async def process_verification_request(data):
    verification_id = data.get("verificationId")
    print(f"[LOG] 🚀 Simulating verification call: {verification_id}")

    await asyncio.sleep(10)

    result = {
        "verificationId": verification_id,
        "Customer Name": data.get("customerName"),
        "Company": data.get("company", "ABC Towing"),
        "Call Outcome": "Confirmed service",
        "PurchaseOrder": data.get("purchaseOrder"),
        "outBoundCallNumber": data.get("customerPhone"),
        "callDurationMin": 94,
        "userSentiment": "Positive",
        "disconnectReason": "agent_hangup",
        "response": "SUCCESS",
        "Reason": data.get("reason"),
        "CallScore": "60",
        "CallScoreReview": "Positive",
        "transcript": "Agent: Hi ... User: Yes ... Agent: Great!",
        "gdslt": verification_id,
        "timestamp": datetime.utcnow().isoformat(),
        "webhookUrl": data.get("webhookUrl")
    }

    redis_conn = Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD
    )
    q = Queue("webhookQueue", connection=redis_conn, serializer=PickleSerializer)
    q.enqueue(send_webhook, result,
        retry=Retry(max=3, interval=[5, 10, 30])
        )
    print("[LOG] 📤 Enqueued webhook job with retry")

@app.post("/verifyCustomerInfo")
async def verify_customer_info(
    request: Request,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    data = await request.json()
    print(f"[LOG] POST /verifyCustomerInfo - Received payload: {data}")
    background_tasks.add_task(process_verification_request, data)
    return {"status": "queued", "verificationId": data.get("verificationId")}

if __name__ == "__main__":
    print(f"[LOG] Starting FastAPI server on HTTPS port {PORT}...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=PORT,
        ssl_keyfile=SSL_KEYFILE,
        ssl_certfile=SSL_CERTFILE
    )
    
