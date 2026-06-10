from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BOT_TOKEN = "8994297709:AAF6-5MAqghke6xdgMxezpr31a2KXT0YWdg"

USERS_DATA = {}

class UserProfileRequest(BaseModel):
    user_id: int
    username: str = "Без юзернейма"

class BuyStarsRequest(BaseModel):
    user_id: int
    stars: int

def init_user(user_id: int, username: str = "Без юзернейма"):
    if user_id not in USERS_DATA:
        USERS_DATA[user_id] = {
            "id": user_id,
            "username": username,
            "balance": 0,
            "history": []
        }

@app.post("/api/profile")
async def get_profile(request: UserProfileRequest):
    init_user(request.user_id, request.username)
    return USERS_DATA[request.user_id]

@app.post("/api/buy-stars")
async def buy_stars(request: BuyStarsRequest):
    if request.stars <= 0:
        raise HTTPException(status_code=400, detail="Неверное количество звёзд")
    
    user_id = request.user_id
    init_user(user_id)
    
    vnt_to_add = request.stars
    USERS_DATA[user_id]["balance"] += vnt_to_add
    
    purchase_entry = {
        "stars": request.stars,
        "vnt": vnt_to_add,
        "timestamp": int(time.time())
    }
    USERS_DATA[user_id]["history"].append(purchase_entry)
    
    return {
        "status": "success",
        "new_balance": USERS_DATA[user_id]["balance"],
        "history": USERS_DATA[user_id]["history"]
    }
