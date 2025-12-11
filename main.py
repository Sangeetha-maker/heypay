from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List

app = FastAPI(title="HeyPay Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VoiceCommand(BaseModel):
    text: str
    language: str = "en"

class ParsedCommand(BaseModel):
    action: str
    amount: float | None = None
    payee: str | None = None
    language: str

class ConfirmRequest(BaseModel):
    action: str
    amount: float
    payee: str
    user_id: str = "demo-user"

class Transaction(BaseModel):
    payee: str
    amount: float

BALANCES = {"demo-user": 10000.0}
TX_HISTORY: dict[str, List[Transaction]] = {"demo-user": []}

@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "HeyPay backend running"}

@app.post("/api/parse-command", response_model=ParsedCommand)
def parse_command(cmd: VoiceCommand):
    text = cmd.text.lower()

    action = "unknown"
    if "send" in text or "pay" in text:
        action = "pay"
    elif "balance" in text or "check balance" in text:
        action = "check_balance"

    amount = None
    clean = text.replace("rupees", "").replace("rs", "").replace("rs.", "")
    words = clean.split()
    for w in words:
        if w.replace(".", "", 1).isdigit():
            amount = float(w)
            break

    payee = None
    if " to " in text:
        payee = text.split(" to ", 1)[1].strip().title()

    return ParsedCommand(
        action=action,
        amount=amount,
        payee=payee,
        language=cmd.language,
    )

@app.post("/api/confirm-transaction")
def confirm_transaction(req: ConfirmRequest):
    balance = BALANCES.get(req.user_id, 0.0)
    if req.amount > balance:
        return {
            "status": "failed",
            "reason": "insufficient_balance",
            "balance": balance,
        }

    BALANCES[req.user_id] = balance - req.amount
    TX_HISTORY.setdefault(req.user_id, []).append(
        Transaction(payee=req.payee, amount=req.amount)
    )
    return {
        "status": "success",
        "balance": BALANCES[req.user_id],
        "payee": req.payee,
        "amount": req.amount,
    }

@app.get("/api/transactions")
def get_transactions(user_id: str = "demo-user"):
    return {
        "balance": BALANCES.get(user_id, 10000.0),
        "transactions": TX_HISTORY.get(user_id, []),
    }

# Serve Flutter web build from build/web
app.mount("/", StaticFiles(directory="build/web", html=True), name="static")

@app.get("/")
async def serve_spa():
    return FileResponse("build/web/index.html")
