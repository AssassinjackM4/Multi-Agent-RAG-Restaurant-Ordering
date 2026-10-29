"""
Restaurant order management agent built with LangGraph.

Flow:
    user_input -> llm -> order_confirm -> llm -> cook -> llm -> serve -> llm -> END

The `llm` node is the "brain": every other node reports back to it by writing
`status`, and the llm reads the state (status + retry counters) to decide what
to say to the user and which node runs next.

uv add langgraph langchain-groq python-dotenv
"""

import difflib
import operator
import os
import random
import re
import sys
from threading import RLock
from typing import Annotated, Literal, Optional, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from menu_rag import MenuRecommendation, recommend_menu_items

load_dotenv()

# Windows console defaults to cp1252 and chokes on fancy quotes the model likes to emit
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MODEL = "openai/gpt-oss-120b"
llm = (
    ChatGroq(model=MODEL, api_key=os.environ["GROQ_API_KEY"], temperature=0)
    if os.getenv("GROQ_API_KEY")
    else None
)

# ============================================================
# MENU  (dish -> quantity in stock)
# ============================================================

MENU: dict[str, int] = {
    "red sauce penne pasta": 8,
    "veg burger": 7,
    "veg biryani": 8,
    "white sauce penne pasta": 6,
    "pizza": 5,
    "burger": 3,
    "biryani": 10,
    "dosa": 2,
    "pasta": 0,  # on the menu but sold out
    "tacos": 8,
    "sushi": 4,
    "ramen": 6,
    "butter chicken": 6,
    "pad thai": 7,
    "falafel": 5,
    "cheesecake": 3,
    "lasagna": 5,
    "margherita pizza": 7,
    "chicken tikka masala": 6,
    "chole bhature": 5,
    "green curry": 6,
    "mac and cheese": 6,
    "tiramisu": 5,
    "veg momos": 8,
    "chinese veg dumplings": 8,
    "veg spring rolls": 8,
    "veg fried rice": 8,
    "chilli paneer": 8,
}
INITIAL_MENU = MENU.copy()
inventory_lock = RLock()

ORDER_RETRIES = 3
COOK_RETRIES = 2
SERVE_RETRIES = 2

COOK_SUCCESS_PROB = 0.6
SERVE_SUCCESS_PROB = 0.6


def find_menu_item(name: str) -> str | None:
    """Fuzzy-match a dish name to a MENU key. Returns the key, or None if nothing is close."""
    name = name.strip().lower()
    if not name:
        return None
    if name in MENU:
        return name
    # "margherita pizza" -> "pizza", "biryani rice" -> "biryani"
    for key in MENU:
        if key in name or name in key:
            return key
    # "piza", "burgr" -> closest spelling
    close = difflib.get_close_matches(name, MENU.keys(), n=1, cutoff=0.6)
    return close[0] if close else None


# ============================================================
# STATE
# ============================================================


class OrderDetails(TypedDict):
    dish_name: str
    required_quantity: int
    available_quantity: int  # written by order_confirm; 0 if dish not on menu


# Values `status` can hold. Nodes write the left column, the llm reads it and
# writes the right column to say where the graph goes next.
#
#   written by nodes            written by llm (= routing decision)
#   ---------------------       ----------------------------------
#   new                         awaiting_user   -> user_input
#   confirmed / partial /       placed          -> order_confirm
#     unavailable               cook            -> cook
#   ready / cook_failed         serve           -> serve
#   complete / serve_failed     done / failed   -> END
Status = Literal[
    "new",
    "awaiting_user",
    "placed",
    "confirmed",
    "partial",
    "unavailable",
    "cook",
    "ready",
    "cook_failed",
    "serve",
    "complete",
    "serve_failed",
    "done",
    "failed",
    "menu_recommendation",
]


class State(TypedDict):
    messages: Annotated[list, add_messages]
    agent_trace: Annotated[list[str], operator.add]
    order: OrderDetails
    status: Status
    pending_partial_confirmation: bool
    order_retries: int  # order attempts left (3)
    cook_retries: int  # cook RE-runs left (2); first cook is free, every re-cook costs one, whoever caused it
    serve_retries: int  # serve RE-runs left (2); first serve is free
    final_result: str
    recommendations: list[MenuRecommendation]
    reserved_quantity: int


def initial_state() -> State:
    return {
        "messages": [],
        "agent_trace": [],
        "order": {"dish_name": "", "required_quantity": 0, "available_quantity": 0},
        "status": "new",
        "pending_partial_confirmation": False,
        "order_retries": ORDER_RETRIES,
        "cook_retries": COOK_RETRIES,
        "serve_retries": SERVE_RETRIES,
        "final_result": "",
        "recommendations": [],
        "reserved_quantity": 0,
    }


def inventory_snapshot() -> dict[str, int]:
    """Return a consistent stock snapshot for API responses and retrieval."""
    with inventory_lock:
        return MENU.copy()


def reset_inventory() -> None:
    """Restore demo inventory to its initial quantities."""
    with inventory_lock:
        MENU.clear()
        MENU.update(INITIAL_MENU)


def release_inventory(dish_name: str, quantity: int) -> None:
    """Return a failed order's reservation without exceeding initial stock."""
    with inventory_lock:
        if dish_name in MENU and quantity > 0:
            MENU[dish_name] = min(INITIAL_MENU[dish_name], MENU[dish_name] + quantity)


def get_llm() -> ChatGroq:
    """Return the configured model or fail clearly when the API key is missing."""
    if llm is None:
        raise RuntimeError("GROQ_API_KEY is not configured. Add it to backend/.env and restart the server.")
    return llm


# ============================================================
# LLM HELPERS
# ============================================================


class OrderIntent(BaseModel):
    """What the LLM extracts from a user message."""

    intent: Literal["new_order", "accept_partial", "availability", "unrelated"] = Field(
        description=(
            "new_order: user is ordering a dish with a quantity. "
            "accept_partial: user agrees to take the smaller available quantity. "
            "availability: user is asking whether a dish is available or how many are in stock. "
            "unrelated: message has nothing to do with ordering food."
        )
    )
    dish_name: Optional[str] = Field(default=None, description="Dish name, lowercase, singular")
    quantity: Optional[int] = Field(default=None, description="Quantity requested (default 1 if omitted)")


EXTRACT_PROMPT = """You are the order-taking assistant of a restaurant. You ONLY handle food orders.
Read the user's latest message and classify it.

- If they order a dish, return intent=new_order with dish_name (lowercase, singular) and quantity (1 if not stated).
- If they are agreeing to go ahead with the smaller available quantity that was offered to them
  (e.g. "yes", "ok go ahead", "fine, give me what you have", "yes, send the available quantity"),
  return intent=accept_partial.
- If they ask whether a dish is available or how many are in stock, return intent=availability
  with the exact menu dish_name. Do not classify a stock question as a new order.
- If they ask what food or dishes are available, what the restaurant has, request the full menu stock,
  or ask a general/category availability question without naming a dish, return intent=availability
  with dish_name=null. This includes requests like "what vegetarian food do you have?".
- If they ask about a dish that is not on the menu, return intent=availability with that dish name
  so the customer can be told it is not listed.
- If the message is not about ordering food (general questions, chit-chat, coding help...), return intent=unrelated.

Menu (dish -> in stock): {menu}
When extracting a dish, use the exact menu item name. Keep modifiers such as "red sauce",
"white sauce", and "veg" because these identify distinct menu items.
Was the user just offered a partial order? {partial_offer}
"""


def latest_human_message(state: State) -> HumanMessage | None:
    """Return the newest human message, or None when a state has no user input yet."""
    for message in reversed(state["messages"]):
        if isinstance(message, HumanMessage):
            return message
    return None


def extract_order(state: State) -> OrderIntent:
    """Ask the LLM to pull dish + quantity (or intent) out of the latest user message."""
    partial_offer = "yes" if state["pending_partial_confirmation"] else "no"
    system = EXTRACT_PROMPT.format(menu=inventory_snapshot(), partial_offer=partial_offer)
    structured = get_llm().with_structured_output(OrderIntent)
    last_user = latest_human_message(state)
    if last_user is None:
        return OrderIntent(intent="unrelated")
    return structured.invoke([SystemMessage(system), last_user])


def check_menu_availability(message: str) -> tuple[str, OrderDetails] | None:
    """Answer clear stock questions from authoritative menu data without guessing."""
    normalized = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", message.lower())).strip()
    availability_cues = (
        "available",
        "availability",
        "in stock",
        "stock",
        "what do you have",
        "do you have",
        "what dishes",
        "which dishes",
        "what foods",
        "what food",
        "show me the menu",
        "what is on the menu",
        "what's on the menu",
        "menu",
        "how many",
        "vegetarian",
    )
    if not any(cue in normalized for cue in availability_cues):
        return None
    inventory = inventory_snapshot()

    # Keep explicit quantity orders on the normal LLM extraction path.
    if re.search(r"\b(?:order|want|like|give me|send|buy|place)\b", normalized) and re.search(r"\b\d+\b", normalized):
        return None

    for dish in sorted(inventory, key=len, reverse=True):
        dish_pattern = re.escape(dish).replace(r"\ ", r"\s+") + r"s?"
        if re.search(rf"\b{dish_pattern}\b", normalized):
            quantity = inventory[dish]
            detail = {
                "dish_name": dish,
                "required_quantity": 0,
                "available_quantity": quantity,
            }
            if quantity:
                answer = f"We have {quantity} {dish} available right now. Tell me how many you would like to order."
            else:
                answer = f"{dish.capitalize()} is currently sold out (0 available). Would you like to check another dish?"
            return answer, detail

    broad_menu_question = (
        "what do you have",
        "what dishes",
        "which dishes",
        "what foods",
        "what food",
        "what is available",
        "what s available",
        "what s in stock",
        "show me the menu",
        "what is on the menu",
        "what s on the menu",
        "what's on the menu",
        "all dishes",
        "full menu",
        "menu",
        "vegetarian",
    )
    if not any(phrase in normalized for phrase in broad_menu_question):
        return None

    inventory = [
        f"{dish}: {quantity}" + (" (sold out)" if quantity == 0 else "")
        for dish, quantity in inventory.items()
    ]
    answer = "Current menu stock: " + "; ".join(inventory) + ". Tell me a dish and quantity to place an order."
    return answer, {"dish_name": "", "required_quantity": 0, "available_quantity": 0}


def is_menu_recommendation(message: str) -> bool:
    """Identify discovery requests that need retrieval rather than a stock lookup."""
    normalized = message.lower()
    cues = (
        "recommend",
        "suggest",
        "similar to",
        "like but",
        "cheaper",
        "spicy",
        "light meal",
        "high protein",
        "protein",
        "healthy",
        "plant based",
        "plant-based",
        "vegan",
        "vegetarian",
        "italian",
        "indian",
        "american",
        "japanese",
        "chinese",
        "korean",
        "mexican",
        "thai",
        "vietnamese",
        "greek",
        "mediterranean",
        "middle eastern",
        "french",
        "british",
    )
    price_filter = re.search(
        r"\b(?:under|below|less than|cheaper than)\s*(?:₹|\$|rs\.?\s*|inr\s*|rupees?\s*)?\d+(?:\.\d{1,2})?",
        normalized,
    )
    return bool(price_filter) or any(cue in normalized for cue in cues)


def uses_inr_currency(message: str) -> bool:
    """INR cannot be compared to this catalog's USD prices without conversion data."""
    return bool(re.search(r"₹|\b(?:inr|rupees?)\b|\brs\.?\s*\d", message.lower()))


def say(instruction: str, state: State) -> str:
    """Ask the LLM to phrase a short message to the customer given the current state."""
    system = (
        "You are the friendly assistant of a restaurant's order system. "
        "Write ONE or TWO short sentences to the customer. No markdown.\n"
        f"Current order: {state['order']}\n"
        f"Retries left -> order: {state['order_retries']}, cook: {state['cook_retries']}, serve: {state['serve_retries']}\n"
        f"What to tell the customer: {instruction}"
    )
    return get_llm().invoke([SystemMessage(system)]).content.strip()


# ============================================================
# NODES
# ============================================================


def user_input(state: State, config: RunnableConfig) -> dict:
    """Read the next order from the user. Tests can inject `input_fn` via config."""
    read = config.get("configurable", {}).get("input_fn", input)
    text = read("\nYou: ")
    return {"messages": [HumanMessage(text)]}


def llm_node(state: State) -> dict:
    """The brain. Reads status + counters, talks to the user, and decides the next status."""
    status = state["status"]
    order = dict(state["order"])

    # ---- waiting on the user: parse what they typed ----------------------
    if status in ("new", "awaiting_user"):
        last_user = latest_human_message(state)
        if last_user is None:
            message = "Tell me what you'd like to order (dish + quantity) or ask about the menu."
            return {
                "messages": [AIMessage(message)],
                "order": {"dish_name": "", "required_quantity": 0, "available_quantity": 0},
                "status": "awaiting_user",
                "pending_partial_confirmation": False,
            }
        if is_menu_recommendation(last_user.content):
            return {"status": "menu_recommendation", "recommendations": []}

        availability = check_menu_availability(last_user.content)
        if availability:
            message, inventory_order = availability
            return {
                "messages": [AIMessage(message)],
                "order": inventory_order,
                "status": "awaiting_user",
                "pending_partial_confirmation": False,
            }

        parsed = extract_order(state)

        if parsed.intent == "accept_partial" and state["pending_partial_confirmation"] and order["available_quantity"] > 0:
            order["required_quantity"] = order["available_quantity"]
            return {
                "messages": [AIMessage("Thanks. I’m checking the latest stock before confirming the available quantity.")],
                "order": order,
                "status": "placed",
                "pending_partial_confirmation": False,
            }

        if parsed.intent == "new_order" and parsed.dish_name:
            order = {
                "dish_name": parsed.dish_name.strip().lower(),
                "required_quantity": max(1, parsed.quantity or 1),
                "available_quantity": 0,
            }
            return {"order": order, "status": "placed", "pending_partial_confirmation": False}

        if parsed.intent == "availability":
            if not parsed.dish_name:
                inventory = [
                    f"{dish}: {quantity}" + (" (sold out)" if quantity == 0 else "")
                    for dish, quantity in inventory_snapshot().items()
                ]
                message = "Current menu stock: " + "; ".join(inventory) + ". Tell me a dish and quantity to place an order."
                order = {"dish_name": "", "required_quantity": 0, "available_quantity": 0}
                return {
                    "messages": [AIMessage(message)],
                    "order": order,
                    "status": "awaiting_user",
                    "pending_partial_confirmation": False,
                }
            match = find_menu_item(parsed.dish_name)
            if match is None:
                message = f"{parsed.dish_name.capitalize()} isn't listed on our menu. Ask me about one of our listed dishes."
                return {
                    "messages": [AIMessage(message)],
                    "order": {"dish_name": parsed.dish_name.strip().lower(), "required_quantity": 0, "available_quantity": 0},
                    "status": "awaiting_user",
                    "pending_partial_confirmation": False,
                }
            available = inventory_snapshot()[match]
            order = {"dish_name": match, "required_quantity": 0, "available_quantity": available}
            message = (
                f"We have {available} {match} available right now. Tell me how many you would like to order."
                if available
                else f"{match.capitalize()} is currently sold out (0 available). Would you like to check another dish?"
            )
            return {
                "messages": [AIMessage(message)],
                "order": order,
                "status": "awaiting_user",
                "pending_partial_confirmation": False,
            }

        # unrelated / could not extract -> costs one order attempt
        retries = state["order_retries"] - 1
        if retries <= 0:
            msg = say("Politely say you are a food-ordering assistant only, and since no valid order was placed after 3 attempts you are closing the session.", state)
            return {"messages": [AIMessage(msg)], "order_retries": 0, "status": "failed", "final_result": "NOT COMPLETED: no valid order after 3 attempts", "pending_partial_confirmation": False}
        msg = say("Politely say you are an AI agent for food ordering only, not a general-purpose assistant, and ask them to place a food order (dish + quantity).", state)
        return {"messages": [AIMessage(msg)], "order_retries": retries, "status": "awaiting_user", "pending_partial_confirmation": False}

    # ---- order_confirm reported back ------------------------------------
    if status == "confirmed":
        msg = (
            f"Confirmed {order['required_quantity']} {order['dish_name']}. "
            "The demo kitchen is preparing your order."
        )
        return {"messages": [AIMessage(msg)], "status": "cook", "pending_partial_confirmation": False}

    if status in ("partial", "unavailable"):
        retries = state["order_retries"] - 1
        if retries <= 0:
            msg = say("Apologize: the order could not be fulfilled and all 3 order attempts are used up, so the session is closing.", state)
            return {"messages": [AIMessage(msg)], "order_retries": 0, "status": "failed", "final_result": "NOT COMPLETED: order attempts exhausted"}
        if status == "partial":
            instruction = (
                f"Only {order['available_quantity']} of the {order['required_quantity']} {order['dish_name']} requested are available. "
                f"Ask if they want to go ahead with {order['available_quantity']} or place a different order. Mention {retries} attempt(s) left."
            )
        else:
            instruction = f"'{order['dish_name']}' is not available at all. Ask them to place a different order. Mention the menu and {retries} attempt(s) left."
        msg = say(instruction, state)
        return {"messages": [AIMessage(msg)], "order_retries": retries, "status": "awaiting_user", "pending_partial_confirmation": status == "partial"}

    # ---- cook reported back ---------------------------------------------
    if status == "ready":
        msg = "The simulated kitchen finished cooking. The demo service step is underway."
        return {"messages": [AIMessage(msg)], "status": "serve"}

    if status == "cook_failed":
        if state["cook_retries"] > 0:
            print(f"[llm] cook failed -> retry cook (cook retries left: {state['cook_retries'] - 1})")
            msg = "The simulated kitchen hit a retryable issue and is preparing your order again."
            return {"messages": [AIMessage(msg)], "status": "cook", "cook_retries": state["cook_retries"] - 1}
        msg = "The simulated kitchen could not prepare this order after its retries. The reservation has been released."
        return {"messages": [AIMessage(msg)], "status": "failed", "final_result": "NOT COMPLETED: cook failed"}

    # ---- serve reported back --------------------------------------------
    if status == "complete":
        msg = "The simulated kitchen and service steps are complete. Enjoy your meal!"
        return {"messages": [AIMessage(msg)], "status": "done", "final_result": "COMPLETED"}

    if status == "serve_failed":
        # a re-serve needs a re-cook first, so this spends one retry of each
        if state["serve_retries"] > 0 and state["cook_retries"] > 0:
            print(f"[llm] serve failed -> retry cook+serve (cook retries left: {state['cook_retries'] - 1}, serve retries left: {state['serve_retries'] - 1})")
            msg = "The simulated service step hit an issue. The kitchen is preparing the order again for another attempt."
            return {"messages": [AIMessage(msg)], "status": "cook", "cook_retries": state["cook_retries"] - 1, "serve_retries": state["serve_retries"] - 1}
        reason = "serve failed" if state["serve_retries"] <= 0 else "serve failed and cook retries exhausted"
        msg = f"The simulated service could not complete the order ({reason}). The reservation has been released."
        return {"messages": [AIMessage(msg)], "status": "failed", "final_result": f"NOT COMPLETED: {reason}"}

    raise ValueError(f"llm node got unexpected status {status!r}")


def order_confirm(state: State) -> dict:
    """Atomically check and reserve stock for a complete order."""
    order = dict(state["order"])
    match = find_menu_item(order["dish_name"])
    if match:
        order["dish_name"] = match
    with inventory_lock:
        available = MENU[match] if match else 0
        order["available_quantity"] = available
        reserved_quantity = 0
        if available == 0:
            status = "unavailable"
        elif available < order["required_quantity"]:
            status = "partial"
        else:
            status = "confirmed"
            reserved_quantity = order["required_quantity"]
            MENU[match] -= reserved_quantity

    print(f"[order_confirm] {order['dish_name']}: need {order['required_quantity']}, have {available} -> {status}")
    return {
        "order": order,
        "status": status,
        "reserved_quantity": reserved_quantity,
        "agent_trace": ["inventory_agent"],
    }


def _outcome(config: RunnableConfig, key: str, prob: float) -> bool:
    """60/40 coin flip. Tests can pre-script results with config['configurable'][key] = [True, False, ...]."""
    scripted = config.get("configurable", {}).get(key)
    if scripted:
        return bool(scripted.pop(0))
    return random.random() < prob


def cook(state: State, config: RunnableConfig) -> dict:
    """60/40 coin flip. The llm decides (and pays for) any retry."""
    if _outcome(config, "cook_outcomes", COOK_SUCCESS_PROB):
        print("[cook] success -> ready")
        return {"status": "ready", "agent_trace": ["kitchen_agent"]}
    print("[cook] FAILED")
    return {"status": "cook_failed", "agent_trace": ["kitchen_agent"]}


def serve(state: State, config: RunnableConfig) -> dict:
    """60/40 coin flip. The llm decides (and pays for) any retry."""
    if _outcome(config, "serve_outcomes", SERVE_SUCCESS_PROB):
        print("[serve] success -> complete")
        return {"status": "complete", "agent_trace": ["service_agent"]}
    print("[serve] FAILED")
    return {"status": "serve_failed", "agent_trace": ["service_agent"]}


def menu_rag_agent(state: State) -> dict:
    """Retrieve grounded menu matches and generate a concise, evidence-based answer."""
    last_user = latest_human_message(state)
    if last_user is None:
        answer = "Tell me what you would like to recommend or order."
        recommendations: list[MenuRecommendation] = []
    else:
        inr_budget = uses_inr_currency(last_user.content)
        if inr_budget:
            recommendations = []
            answer = "Menu prices are listed in USD. Please ask again with a USD budget so I can filter the menu accurately."
        else:
            recommendations = recommend_menu_items(last_user.content, inventory_snapshot())
        if not inr_budget and not recommendations:
            answer = "I couldn't find an in-stock match for that request. Tell me a dish name and I can check its availability."
        elif recommendations:
            context = "\n".join(
                f"- {item['name']} (${item['price']:.2f}; stock: {item['stock']}): "
                f"{item['description']} Tags: {', '.join(item['tags'])}."
                for item in recommendations
            )
            response = get_llm().invoke(
                [
                    SystemMessage(
                        content=(
                            "You are the restaurant's menu recommendation agent. Recommend only dishes in the "
                            "provided context and only when stock is above zero. Use the actual listed price and "
                            "do not invent ingredients, dietary properties, stock, or alternatives. If no item "
                            "fits, say so. Keep the response concise and friendly.\n\n"
                            f"Retrieved menu context:\n{context}"
                        )
                    ),
                    last_user,
                ]
            )
            answer = response.content.strip()

    return {
        "messages": [AIMessage(content=answer)],
        "recommendations": recommendations,
        "status": "awaiting_user",
        "agent_trace": ["menu_rag_agent"],
    }


# ============================================================
# EDGES
# ============================================================


def route_after_llm(state: State) -> str:
    status = state["status"]
    if status == "awaiting_user":
        return END
    if status == "menu_recommendation":
        return "menu_rag_agent"
    if status == "placed":
        return "inventory_agent"
    if status == "cook":
        return "kitchen_agent"
    if status == "serve":
        return "service_agent"
    return END  # done / failed


def supervisor(state: State) -> dict:
    """Coordinate specialist agents while keeping conversation decisions centralized."""
    update = {**llm_node(state), "agent_trace": ["supervisor"]}
    if update.get("status") == "failed" and state["reserved_quantity"] > 0:
        release_inventory(state["order"]["dish_name"], state["reserved_quantity"])
        update["reserved_quantity"] = 0
    return update


# ============================================================
# GRAPH
# ============================================================

builder = StateGraph(State)
builder.add_node("user_input", user_input)
builder.add_node("supervisor", supervisor)
builder.add_node("inventory_agent", order_confirm)
builder.add_node("kitchen_agent", cook)
builder.add_node("service_agent", serve)
builder.add_node("menu_rag_agent", menu_rag_agent)

builder.add_edge(START, "user_input")
builder.add_edge("user_input", "supervisor")
builder.add_edge("inventory_agent", "supervisor")
builder.add_edge("kitchen_agent", "supervisor")
builder.add_edge("service_agent", "supervisor")
builder.add_conditional_edges(
    "supervisor",
    route_after_llm,
    {
        "menu_rag_agent": "menu_rag_agent",
        "inventory_agent": "inventory_agent",
        "kitchen_agent": "kitchen_agent",
        "service_agent": "service_agent",
        END: END,
    },
)
builder.add_edge("menu_rag_agent", END)

graph = builder.compile()


# ============================================================
# RUN
# ============================================================


def run_turn(
    state: State,
    user_text: str,
    config: RunnableConfig | None = None,
) -> State:
    """Process one user message and return when the agent needs another reply or is done."""
    options = dict(config or {})
    configurable = dict(options.get("configurable", {}))
    configurable["input_fn"] = lambda _prompt: user_text
    options["configurable"] = configurable
    options.setdefault("recursion_limit", 100)
    return graph.invoke(state, config=options)


def run(config: RunnableConfig | None = None) -> State:
    """Run one interactive ordering session in the terminal."""
    options = {"recursion_limit": 100, **(config or {})}
    configurable = options.get("configurable", {})
    read = configurable.get("input_fn", input)
    state = initial_state()
    seen = 0

    while state["status"] not in ("done", "failed"):
        options["configurable"] = {**configurable, "input_fn": read}
        state = graph.invoke(state, config=options)
        for m in state["messages"][seen:]:
            if isinstance(m, AIMessage):
                print(f"Agent: {m.content}")
        seen = len(state["messages"])

    print(f"\nFINAL RESULT: {state['final_result']}")
    return state


def simulate(user_inputs: list[str], cook_outcomes: list[bool] | None = None, serve_outcomes: list[bool] | None = None) -> State:
    """Run a scripted scenario: canned user replies and pre-decided cook/serve results."""
    inputs = list(user_inputs)

    def fake_input(prompt: str) -> str:
        text = inputs.pop(0) if inputs else "bye"
        print(f"{prompt}{text}")
        return text

    return run({"configurable": {"input_fn": fake_input, "cook_outcomes": list(cook_outcomes or []), "serve_outcomes": list(serve_outcomes or [])}})


if __name__ == "__main__":
    print(f"Welcome! Menu: {MENU}")
    print("Tell me what you'd like to order (one dish + quantity).")
    run()
