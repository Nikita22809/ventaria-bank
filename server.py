import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import httpx
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Токен бота из настроек Render (Environment Variables)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8994297709:AAF6-5MaQghke6xdgMxezpr31a2KXT0YwDg")

class CreateInvoiceRequest(BaseModel):
    user_id: int
    stars: int

# Временная база данных в памяти (для сохранения баланса после успешной оплаты)
USERS_DATA = {}

@app.post("/get_profile")
async def get_profile(data: dict):
    uid = data.get("user_id")
    if not uid:
        raise HTTPException(status_code=400, detail="Не указан user_id")
        
    if uid not in USERS_DATA:
        USERS_DATA[uid] = {
            "balance": 0,
            "history": []
        }
    return USERS_DATA[uid]

# Роут для создания ссылки на оплату Звёздами
@app.post("/create_invoice")
async def create_invoice(data: CreateInvoiceRequest):
    if data.stars <= 0:
        raise HTTPException(status_code=400, detail="Количество звёзд должно быть больше 0")

    # Ссылка на метод создания инвойса в Telegram Bot API
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/createInvoiceLink"
    
    # Параметры платежа для Telegram Stars
    payload = {
        "title": "Пополнение баланса VNT",
        "description": f"Покупка {data.stars} VNT через Telegram Stars",
        "payload": f"user_deposit_{data.user_id}_{data.stars}", # Внутренний ID платежа
        "provider_token": "", # Для звёзд это поле ВСЕГДА должно быть пустым
        "currency": "XTR",     # XTR — это международный код Telegram Stars
        "prices": [{"label": "Telegram Stars", "amount": data.stars}]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        res_json = response.json()
        
        if res_json.get("ok"):
            # Возвращаем готовую ссылку на оплату обратно во фронтенд
            return {"status": "success", "invoice_link": res_json["result"]}
        else:
            print("Ошибка Telegram API:", res_json)
            raise HTTPException(status_code=500, detail=res_json.get("description", "Ошибка Telegram API"))

# Webhook для отлавливания успешной оплаты (Pre-checkout и Successful Payment)
# Когда пользователь оплатит, Telegram отправит сюда уведомление, и мы начислим баланс.
@app.post("/telegram_webhook")
async def telegram_webhook(update: dict):
    # Логика обработки вебхука для зачисления баланса на сервере.
    # Чтобы баланс сохранялся "намертво" при реальной оплате, боту нужно включить вебхуки на этот адрес.
    if "pre_checkout_query" in update:
        # Автоматически одобряем pre_checkout
        pq_id = update["pre_checkout_query"]["id"]
        async with httpx.AsyncClient() as client:
            await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerPreCheckoutQuery", json={
                "pre_checkout_query_id": pq_id,
                "ok": True
            })
    
    if "message" in update and "successful_payment" in update["message"]:
        payment = update["message"]["successful_payment"]
        payload = payment["invoice_payload"]
        
        # Разбираем payload (user_deposit_ЮЗЕРID_ЗВЕЗДЫ)
        if payload.startswith("user_deposit_"):
            parts = payload.split("_")
            uid = int(parts[2])
            stars = int(parts[3])
            
            if uid not in USERS_DATA:
                USERS_DATA[uid] = {"balance": 0, "history": []}
                
            USERS_DATA[uid]["balance"] += stars
            USERS_DATA[uid]["history"].append({
                "type": "Реальное пополнение",
                "amount": f"+{stars} VNT"
            })
            
    return {"ok": True}

app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
