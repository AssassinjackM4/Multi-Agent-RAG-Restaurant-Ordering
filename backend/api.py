"""FastAPI endpoints for the restaurant ordering agent."""

from __future__ import annotations

import os
from threading import Lock
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from main import State, get_llm, initial_state, inventory_snapshot, run_turn

app = FastAPI(title="Restaurant Order Agent API", version="1.0.0")
allowed_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv("FRONTEND_ORIGINS", "").split(",")
    if origin.strip()
]
allowed_origins = list(dict.fromkeys([
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://ai-restaurant-order-agent.vercel.app",
    *allowed_origins,
]))
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class CartItem(BaseModel):
    dish_name: str = Field(min_length=1, max_length=80)
    quantity: int = Field(ge=1, le=99)

    @field_validator("dish_name")
    @classmethod
    def normalize_dish_name(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("Dish name cannot be blank.")
        return normalized


class CheckoutRequest(BaseModel):
    items: list[CartItem] = Field(min_length=1, max_length=20)


class MessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Message cannot be blank.")
        return normalized


class OrderSession:
    def __init__(self, state: State) -> None:
        self.state = state
        self.lock = Lock()


sessions: dict[str, OrderSession] = {}
sessions_lock = Lock()


def state_payload(state: State) -> dict:
    return {
        "messages": [
            {
                "role": "assistant" if getattr(message, "type", "") == "ai" else "user",
                "content": message.content if isinstance(message.content, str) else str(message.content),
            }
            for message in state["messages"]
        ],
        "agent_trace": state["agent_trace"],
        "recommendations": state["recommendations"],
        "order": state["order"],
        "status": state["status"],
        "pending_partial_confirmation": state["pending_partial_confirmation"],
        "order_retries": state["order_retries"],
        "cook_retries": state["cook_retries"],
        "serve_retries": state["serve_retries"],
        "final_result": state["final_result"],
        "reserved_quantity": state["reserved_quantity"],
    }


def _require_llm() -> None:
    try:
        get_llm()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _process_message(state: State, message: str) -> State:
    return run_turn(state, message)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/menu")
def menu() -> dict[str, dict[str, int]]:
    return {"items": inventory_snapshot()}


@app.post("/api/chat/sessions")
def create_chat_session() -> dict:
    """Create a LangGraph-backed session for the floating restaurant assistant."""
    session_id = str(uuid4())
    record = OrderSession(initial_state())
    with sessions_lock:
        sessions[session_id] = record
    return {"session_id": session_id, "state": state_payload(record.state)}


@app.post("/api/checkout")
def checkout(request: CheckoutRequest) -> dict:
    """Start one LangGraph conversation for each item in the submitted cart."""
    _require_llm()
    results = []
    for item in request.items:
        session_id = str(uuid4())
        record = OrderSession(initial_state())
        with sessions_lock:
            sessions[session_id] = record
        state = _process_message(
            record.state,
            f"I would like {item.quantity} {item.dish_name}.",
        )
        record.state = state
        results.append(
            {
                "session_id": session_id,
                "dish_name": item.dish_name,
                "state": state_payload(state),
            }
        )
    return {"orders": results}


@app.post("/api/sessions/{session_id}/messages")
def send_message(session_id: str, request: MessageRequest) -> dict:
    _require_llm()
    with sessions_lock:
        record = sessions.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Order session not found.")

    with record.lock:
        if record.state["status"] in ("done", "failed"):
            raise HTTPException(status_code=409, detail="This order session has already ended.")
        state = _process_message(record.state, request.message.strip())
        record.state = state
        return {"session_id": session_id, "state": state_payload(state)}
