from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Модели для запросов
class UserProfileRequest(BaseModel):
    user_id: int
    username: str = "Без юзернейма"

class BuyStarsRequest(BaseModel):
    user_id: int
    stars: int

# База данных в оперативной памяти сервера
# Структура: { user_id: {"username": "имя", "balance": 0, "history": []} }
USERS_DATA = {}

# 1. Роут для получения или автоматического создания профиля
@app.post("/get_profile")
async def get_profile(data: UserProfileRequest):
    uid = data.user_id
    # Если пользователя еще нет в нашей базе, регистрируем его со стартовым балансом 0
    if uid not in USERS_DATA:
        USERS_DATA[uid] = {
            "username": data.username,
            "balance": 0,
            "history": []
        }
    else:
        # Если зашел под новым ником, обновляем его
        USERS_DATA[uid]["username"] = data.username
        
    return USERS_DATA[uid]

# 2. Роут для обработки платежа (покупки звезд)
@app.post("/buy_stars")
async def buy_stars(data: BuyStarsRequest):
    uid = data.user_id
    stars = data.stars
    
    if stars <= 0:
        raise HTTPException(status_code=400, detail="Количество звезд должно быть больше 0")
        
    # Если пользователя почему-то еще нет в базе, создаем его
    if uid not in USERS_DATA:
        USERS_DATA[uid] = {
            "username": f"User_{uid}",
            "balance": 0,
            "history": []
        }
        
    # Начисляем VNT по курсу 1 к 1
    USERS_DATA[uid]["balance"] += stars
    
    # Добавляем операцию в историю на сервере
    operation = {"type": "Пополнение", "amount": f"+{stars} VNT", "status": "success"}
    USERS_DATA[uid]["history"].append(operation)
    
    return {
        "status": "success", 
        "new_balance": USERS_DATA[uid]["balance"],
        "history": USERS_DATA[uid]["history"]
    }

# Подключаем раздачу статических файлов (index.html)
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    # Render автоматически передает порт в переменную PORT
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
