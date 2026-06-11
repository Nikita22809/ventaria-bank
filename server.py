```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
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

BOT_TOKEN = os.environ.get("8994297709:AAF6-5MaQghke6xdgMxezpr31a2KXT0YwDg")

class CreateInvoiceRequest(BaseModel):
    user_id: int
    stars: int

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

@app.post("/create_invoice")
async def create_invoice(data: CreateInvoiceRequest):
    if data.stars <= 0:
        raise HTTPException(status_code=400, detail="Количество звёзд должно быть больше 0")

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/createInvoiceLink"
    payload = {
        "title": "Пополнение баланса VNT",
        "description": f"Покупка {data.stars} VNT через Telegram Stars",
        "payload": f"user_deposit_{data.user_id}_{data.stars}",
        "provider_token": "", 
        "currency": "XTR",
        "prices": [{"label": "Telegram Stars", "amount": data.stars}]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        res_json = response.json()
        
        if res_json.get("ok"):
            return {"status": "success", "invoice_link": res_json["result"]}
        else:
            raise HTTPException(status_code=500, detail=res_json.get("description", "Ошибка Telegram API"))

app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

```
