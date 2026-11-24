from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config import get_settings
from app.db import apply_schema, make_engine
from app.ledger import (
    accept_webhook,
    churn_sweep,
    create_invoice,
    decide_approval,
    list_events,
    list_queue,
    list_rescues,
    mcp_call,
    metrics,
    process_jobs,
    request_refund,
    run_forecast,
)

settings = get_settings()
engine = make_engine(settings.database_url)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    apply_schema(engine)
    yield


app = FastAPI(title="Retriever", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.web_origin.split(",") if origin.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


class InvoiceIn(BaseModel):
    customer_name: str
    email: str | None = None
    ref: str
    amount_minor: int = Field(gt=0)
    currency: str = "SGD"
    due_at: datetime


class DecisionIn(BaseModel):
    actor: str
    note: str = ""


class RefundIn(BaseModel):
    payment_id: UUID
    amount_minor: int = Field(gt=0)
    reason: str


class ToolIn(BaseModel):
    name: str
    arguments: dict = Field(default_factory=dict)


@app.get("/health")
def health():
    return {"ok": True, "dry_run": settings.dry_run}


@app.post("/api/invoices")
def post_invoice(body: InvoiceIn):
    try:
        return create_invoice(engine, settings, **body.model_dump())
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, str(exc)) from exc


@app.post("/webhooks/hitpay")
async def hitpay_webhook(request: Request, hitpay_signature: str | None = Header(default=None, alias="Hitpay-Signature")):
    raw = await request.body()
    status, detail = accept_webhook(engine, settings, "hitpay", raw, hitpay_signature)
    if status == 200:
        process_jobs(engine, settings)
    if status != 200:
        raise HTTPException(status, detail)
    return {"status": detail}


@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request, stripe_signature: str | None = Header(default=None, alias="Stripe-Signature")):
    raw = await request.body()
    status, detail = accept_webhook(engine, settings, "stripe", raw, stripe_signature)
    if status == 200:
        process_jobs(engine, settings)
    if status != 200:
        raise HTTPException(status, detail)
    return {"status": detail}


@app.post("/api/approvals/{approval_id}/approve")
def approve(approval_id: UUID, body: DecisionIn):
    return decide_approval(engine, str(approval_id), True, body.actor, body.note)


@app.post("/api/approvals/{approval_id}/reject")
def reject(approval_id: UUID, body: DecisionIn):
    return decide_approval(engine, str(approval_id), False, body.actor, body.note)


@app.post("/api/refunds")
def post_refund(body: RefundIn):
    try:
        return request_refund(engine, str(body.payment_id), body.amount_minor, body.reason)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/churn/sweep")
def sweep():
    return churn_sweep(engine, settings.churn_after_days)


@app.post("/api/forecast")
def forecast():
    return run_forecast(engine, settings)


@app.get("/api/metrics")
def get_metrics():
    return metrics(engine)


@app.get("/api/queue")
def get_queue():
    return list_queue(engine)


@app.get("/api/rescues")
def get_rescues():
    return list_rescues(engine)


@app.get("/api/events")
def get_events():
    return list_events(engine)


@app.post("/mcp")
def mcp(body: ToolIn):
    try:
        return mcp_call(engine, settings, body.name, body.arguments)
    except KeyError as exc:
        raise HTTPException(404, f"unknown tool {exc}") from exc
