import os
import sqlite3
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from aiogram import Bot

# === НАСТРОЙКИ ===
BOT_TOKEN = "8994297709:AAF6-5MaQghke6xdgMxezpr31a2KXT0YwDg"

app = FastAPI()
bot = Bot("8994297709:AAF6-5MaQghke6xdgMxezpr31a2KXT0YwDg")

# Разрешаем CORS, чтобы Web App мог делать запросы к серверу
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === БАЗА ДАННЫХ ===
def init_db():
    conn = sqlite3.connect("bank.db")
    cursor = conn.cursor()
    # Таблица пользователей (колонка coins теперь концептуально хранит VNT)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            tg_id INTEGER PRIMARY KEY,
            username TEXT,
            coins INTEGER DEFAULT 1000,
            stars_spent INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Модели данных для API
class TransferModel(BaseModel):
    sender_id: int
    recipient_username: str
    amount: int

class UserRequest(BaseModel):
    tg_id: int
    username: str

# === API ЭНДПОИНТЫ ===

# Получить или создать профиль пользователя
@app.post("/api/profile")
async def get_profile(data: UserRequest):
    conn = sqlite3.connect("bank.db")
    cursor = conn.cursor()
    cursor.execute("SELECT coins, stars_spent FROM users WHERE tg_id = ?", (data.tg_id,))
    row = cursor.fetchone()
    
    if not row:
        # Если пользователя нет, регистрируем и дарим 0 VNT
        cursor.execute("INSERT INTO users (tg_id, username, coins) VALUES (?, ?, ?)", 
                       (data.tg_id, data.username, 0))
        conn.commit()
        coins, stars_spent = 0, 0
    else:
        coins, stars_spent = row
        cursor.execute("UPDATE users SET username = ? WHERE tg_id = ?", (data.username, data.tg_id))
        conn.commit()
        
    conn.close()
    return {"tg_id": data.tg_id, "username": data.username, "coins": coins, "stars_spent": stars_spent}

# Перевод VNT между пользователями
@app.post("/api/transfer")
async def transfer_coins(data: TransferModel):
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Сумма должна быть больше 0")
        
    conn = sqlite3.connect("bank.db")
    cursor = conn.cursor()
    
    # Проверяем баланс отправителя
    cursor.execute("SELECT coins FROM users WHERE tg_id = ?", (data.sender_id,))
    sender_row = cursor.fetchone()
    if not sender_row or sender_row[0] < data.amount:
        conn.close()
        raise HTTPException(status_code=400, detail="Недостаточно вент (VNT) на балансе")
        
    # Ищем получателя по юзернейму
    target_username = data.recipient_username.replace("@", "").strip()
    cursor.execute("SELECT tg_id FROM users WHERE username = ?", (target_username,))
    recipient_row = cursor.fetchone()
    if not recipient_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Пользователь не найден в системе")
        
    recipient_id = recipient_row[0]
    if recipient_id == data.sender_id:
        conn.close()
        raise HTTPException(status_code=400, detail="Нельзя переводить VNT самому себе")
        
    # Проводим транзакцию
    cursor.execute("UPDATE users SET coins = coins - ? WHERE tg_id = ?", (data.amount, data.sender_id))
    cursor.execute("UPDATE users SET coins = coins + ? WHERE tg_id = ?", (data.amount, recipient_id))
    conn.commit()
    conn.close()
    
    return {"status": "success", "message": f"Переведено {data.amount} VNT пользователю @{target_username}"}

# Инициация покупки VNT за Telegram Stars
@app.post("/api/buy-stars")
async def buy_stars(data: UserRequest):
    try:
        invoice_link = await bot.create_invoice_link(
            title="1000 вент (VNT)",
            description="Покупка внутрибанковской валюты VNT за Telegram Stars",
            payload=f"stars_buy_{data.tg_id}",
            provider_token="", # Для Stars ПУСТО
            currency="XTR",
            prices=[{"label": "1000 VNT", "amount": 10}] # 10 Stars
        )
        return {"invoice_link": invoice_link}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
async def read_index():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return "Файл index.html не найден!"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)