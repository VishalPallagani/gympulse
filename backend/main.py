import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from routers.admin import router as admin_router
from routers.api import router as api_router
from routers.payments import router as payments_router
from routers.webhook import router as webhook_router
from services.db import SupabaseConfigError
from services.payments import PaymentsConfigError

load_dotenv()

app = FastAPI(title="GymPulse API", version="1.0.0")

frontend_url = os.getenv("FRONTEND_URL") or "http://localhost:5173"

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def health_check() -> dict:
    return {"status": "ok", "service": "GymPulse backend"}


@app.exception_handler(SupabaseConfigError)
async def handle_supabase_config_error(request: Request, exc: SupabaseConfigError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(PaymentsConfigError)
async def handle_payments_config_error(request: Request, exc: PaymentsConfigError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


app.include_router(webhook_router)
app.include_router(api_router)
app.include_router(payments_router)
app.include_router(admin_router)
