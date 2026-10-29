> **Note:** This file contains the original implementation proposal and illustrative examples; some examples (such as INR prices and Chroma/SentenceTransformer setup) do not describe the current code. For the implemented architecture, setup, tests, supported currency, and demo limitations, see the repository's [README.md](./README.md).

Task : I want to make this project Into Rag And Multiple Agent As i said earlier. make it fully working with all these feature as per 2026 trending. check by running whole project after upgrade & fix issues if it's any issue. i just want to add these feature to make project Impressable to HR who hire for AI Engineer job or AI Intern job. make it perfect fully working.


Great choice — these two upgrades will transform your Restaurant Agent from "good learning project" to a genuinely strong 2026 Agentic AI portfolio piece. Here's the complete, in-depth implementation guide for both.

🥇 Option 1: Add RAG to Your Restaurant Agent
🎯 What You're Building
Right now, users can only ask "Do you have biryani?" — a simple stock lookup. With RAG, users can ask natural, complex questions like:

"What's spicy and under ₹200?"

"Suggest something vegetarian for two people"

"What's similar to butter chicken but cheaper?"

"I want something light for dinner"

The agent retrieves relevant menu items semantically and answers intelligently — this is real RAG.

🏗️ Architecture
text
User: "What's spicy and under ₹200?"
        │
        ▼
┌──────────────┐
│ LLM Router   │──▶ Is this a menu question? ──▶ RAG Pipeline
└──────────────┘                                      │
                                                      ▼
                                          ┌─────────────────────┐
                                          │ 1. Embed question   │
                                          │ 2. Search vector DB │
                                          │ 3. Get top 5 dishes │
                                          │ 4. LLM generates    │
                                          │    answer w/ context│
                                          └─────────────────────┘
                                                      │
                                                      ▼
                                    "Try our Paneer Tikka (₹180, spicy, veg) 
                                     or Chicken 65 (₹190, spicy)!"
📦 Step 1: Install Dependencies
bash
cd backend
pip install chromadb sentence-transformers langchain-community
Why ChromaDB? It's free, runs locally (no API key needed), and is the most popular beginner-friendly vector database. Perfect for your project.

📄 Step 2: Create Menu Data with Rich Descriptions
Create backend/rag/menu_data.py:

python
MENU_ITEMS = [
    {
        "id": "pizza_1",
        "name": "Margherita Pizza",
        "description": "Classic Italian pizza with fresh mozzarella, tomato sauce, and basil. Light, cheesy, and perfect for a quick meal.",
        "price": 250,
        "category": "Italian",
        "tags": ["vegetarian", "cheesy", "light", "italian"],
        "spice_level": 0,
        "stock": 5
    },
    {
        "id": "biryani_1",
        "name": "Hyderabadi Chicken Biryani",
        "description": "Aromatic basmati rice layered with tender chicken, saffron, and traditional Hyderabadi spices. Rich, flavorful, and moderately spicy.",
        "price": 320,
        "category": "Indian",
        "tags": ["non-vegetarian", "spicy", "rice", "indian", "rich"],
        "spice_level": 3,
        "stock": 10
    },
    {
        "id": "paneer_tikka_1",
        "name": "Paneer Tikka",
        "description": "Grilled cottage cheese cubes marinated in yogurt and spices, charred in a tandoor. Smoky, spicy, and high in protein.",
        "price": 180,
        "category": "Indian",
        "tags": ["vegetarian", "spicy", "grilled", "protein", "indian"],
        "spice_level": 3,
        "stock": 8
    },
    # ... add all 16 dishes with rich descriptions
]
Key insight: The description field is what makes RAG work. Don't just store "Pizza — ₹250". Write 2-3 sentence descriptions with taste, ingredients, and use-cases. This is what the vector search matches against.

🔧 Step 3: Build the RAG Pipeline
Create backend/rag/menu_rag.py:

python
import chromadb
from chromadb.utils import embedding_functions
from rag.menu_data import MENU_ITEMS

class MenuRAG:
    def __init__(self):
        # Use free, local embeddings — no API cost
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(
            name="restaurant_menu",
            embedding_function=self.embedding_fn
        )
        self._index_menu()
    
    def _index_menu(self):
        """Convert menu items to embeddings and store in vector DB"""
        documents = []
        metadatas = []
        ids = []
        
        for item in MENU_ITEMS:
            # Combine name + description + tags into one searchable document
            doc = f"{item['name']}. {item['description']} Tags: {', '.join(item['tags'])}. Price: ₹{item['price']}."
            documents.append(doc)
            metadatas.append({
                "name": item["name"],
                "price": item["price"],
                "spice_level": item["spice_level"],
                "stock": item["stock"],
                "category": item["category"]
            })
            ids.append(item["id"])
        
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
    
    def search(self, query: str, n_results: int = 5):
        """Semantic search over the menu"""
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        # Format results for the LLM
        retrieved = []
        for i in range(len(results["ids"][0])):
            retrieved.append({
                "name": results["metadatas"][0][i]["name"],
                "price": results["metadatas"][0][i]["price"],
                "spice_level": results["metadatas"][0][i]["spice_level"],
                "stock": results["metadatas"][0][i]["stock"],
                "document": results["documents"][0][i]
            })
        return retrieved

# Singleton instance
menu_rag = MenuRAG()
Key points:

all-MiniLM-L6-v2 is free, fast, and runs on CPU — no OpenAI/Groq embedding costs

We combine name + description + tags into one document for better semantic matching

Metadata (price, stock, spice) is stored separately so we can filter after retrieval

🧠 Step 4: Add RAG Node to Your LangGraph
Create backend/rag/rag_node.py:

python
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel
from rag.menu_rag import menu_rag
import os

class RAGResponse(BaseModel):
    answer: str
    suggested_dishes: list[str]

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    api_key=os.getenv("GROQ_API_KEY")
)

def rag_menu_node(state):
    """RAG node: answers complex menu questions using semantic search"""
    
    # 1. Get the user's question
    user_question = state["messages"][-1].content
    
    # 2. Retrieve relevant dishes via vector search
    retrieved_dishes = menu_rag.search(user_question, n_results=5)
    
    # 3. Build context for the LLM
    context = "\n".join([
        f"- {d['name']} (₹{d['price']}, spice: {d['spice_level']}/5, stock: {d['stock']}): {d['document']}"
        for d in retrieved_dishes
    ])
    
    # 4. LLM generates answer using retrieved context
    system_prompt = f"""You are a helpful restaurant menu assistant.
    
    Use ONLY the menu items below to answer the user's question.
    If nothing matches well, say so honestly.
    Only recommend items that are in stock (stock > 0).
    
    MENU CONTEXT:
    {context}
    """
    
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_question)
    ])
    
    # 5. Return answer + update state
    return {
        "messages": [response],
        "status": "rag_answered",
        "rag_results": retrieved_dishes
    }
🔀 Step 5: Wire It Into Your LangGraph
Update your graph in main.py:

python
from langgraph.graph import StateGraph, END
from rag.rag_node import rag_menu_node

# Add the new node
graph.add_node("rag_menu", rag_menu_node)

# Update the LLM router to decide: is this a menu question or an order?
def route_from_llm(state):
    status = state["status"]
    if status == "menu_question":
        return "rag_menu"       # NEW: complex menu questions go to RAG
    elif status == "order":
        return "order_confirm"  # Orders go to existing flow
    elif status == "stock_check":
        return "stock_check"    # Simple stock checks stay as-is
    # ... existing routing

# Add conditional edge
graph.add_conditional_edges(
    "llm",
    route_from_llm,
    {
        "rag_menu": "rag_menu",
        "order_confirm": "order_confirm",
        "stock_check": "stock_check",
        END: END
    }
)

# RAG node loops back to LLM (so user can follow up)
graph.add_edge("rag_menu", "llm")
🧪 Step 6: Update Your LLM Router Prompt
In your existing LLM node, update the system prompt to classify intent:

python
system_prompt = """You are a restaurant ordering agent. Classify the user's intent:

1. "order" — User wants to order food (e.g., "I want 2 pizzas")
2. "stock_check" — Simple availability question (e.g., "Do you have biryani?")
3. "menu_question" — Complex question about the menu needing recommendations 
   (e.g., "What's spicy under ₹200?", "Suggest vegetarian food", 
    "What's similar to butter chicken?")
4. "unrelated" — Anything else

Return JSON: {"intent": "...", "dish": "...", "quantity": ...}
"""
✅ Test It
bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What spicy food do you have under ₹200?"}'
Expected response:

json
{
  "answer": "For spicy food under ₹200, I'd recommend our Paneer Tikka (₹180) — smoky, grilled cottage cheese with a good kick. We also have Chicken 65 (₹190) if you prefer non-veg. Both are in stock!"
}
💡 Pro Tips for RAG
Update embeddings when stock changes — when an order is placed, decrement stock in metadata and re-index that item

Add a "no results" fallback — if similarity score is too low, say "I couldn't find a good match, here's our full menu instead"

Cache embeddings — index the menu once at startup, not on every request

🥈 Option 2: Multi-Agent Architecture
🎯 What You're Building
Instead of one agent doing everything, you'll have specialized agents that collaborate — this is the "multi-agent system" pattern that top AI companies use in 2026.

text
                    ┌─────────────────┐
                    │  Supervisor     │
                    │  (Orchestrator) │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Order Agent  │    │ Inventory    │    │ Kitchen      │
│              │    │ Agent        │    │ Agent        │
│ Takes orders │    │ Checks stock │    │ Cooks &      │
│ & confirms   │    │ & updates    │    │ serves food  │
└──────────────┘    └──────────────┘    └──────────────┘
🧠 Why This Is Better
Single Agent (current)	Multi-Agent (upgrade)
One LLM does everything	Each agent specializes
Hard to debug	Easy to trace which agent failed
Prompt gets long & confused	Each agent has a short, focused prompt
Can't scale	Add new agents easily (e.g., Payment Agent, Delivery Agent)
📦 Step 1: Define Agent States
Create backend/agents/state.py:

python
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # Shared conversation memory
    messages: Annotated[list, add_messages]
    
    # Routing
    next_agent: str
    
    # Order data
    current_order: dict          # {"dish": "pizza", "qty": 2}
    order_status: str            # "pending", "confirmed", "cooking", "served", "failed"
    
    # Inventory data
    stock_info: dict             # {"pizza": 5, "biryani": 10}
    
    # Kitchen data
    cook_result: str             # "success" or "failed"
    serve_result: str            # "success" or "failed"
    cook_retries: int
    serve_retries: int
    
    # Final result
    final_result: str
🤖 Step 2: Build the Supervisor (Orchestrator)
Create backend/agents/supervisor.py:

python
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
import os

llm = ChatGroq(model="openai/gpt-oss-120b", api_key=os.getenv("GROQ_API_KEY"))

class SupervisorDecision(BaseModel):
    next_agent: str = Field(description="One of: order_agent, inventory_agent, kitchen_agent, FINISH")
    reasoning: str = Field(description="Why this agent should handle it")

def supervisor_node(state):
    """The brain — decides which specialist agent should act next"""
    
    # Build context of what's happened so far
    context = f"""
    Current order: {state.get('current_order', 'None')}
    Order status: {state.get('order_status', 'not started')}
    Stock info: {state.get('stock_info', 'not checked')}
    Cook result: {state.get('cook_result', 'not attempted')}
    Serve result: {state.get('serve_result', 'not attempted')}
    Last message: {state['messages'][-1].content}
    """
    
    system_prompt = f"""You are the Supervisor of a restaurant AI system.
    You coordinate 3 specialist agents. Based on the current state, decide who acts next.
    
    AGENTS:
    - order_agent: Takes new orders, asks clarifying questions, confirms with user
    - inventory_agent: Checks stock, handles partial orders, updates inventory
    - kitchen_agent: Cooks and serves food, handles failures/retries
    
    CURRENT STATE:
    {context}
    
    RULES:
    - New order from user? → order_agent
    - Order needs stock check? → inventory_agent
    - Stock confirmed, ready to cook? → kitchen_agent
    - Kitchen failed and retries exhausted? → FINISH (cancel order)
    - Order served successfully? → FINISH
    - User asked a question? → order_agent (it handles conversation)
    
    Decide the next agent and explain your reasoning.
    """
    
    structured_llm = llm.with_structured_output(SupervisorDecision)
    decision = structured_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content="Decide next agent")
    ])
    
    return {
        "next_agent": decision.next_agent,
        "messages": [f"[Supervisor] Routing to {decision.next_agent}: {decision.reasoning}"]
    }
📦 Step 3: Build the Order Agent
Create backend/agents/order_agent.py:

python
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel
from langchain_groq import ChatGroq
import os

llm = ChatGroq(model="openai/gpt-oss-120b", api_key=os.getenv("GROQ_API_KEY"))

class OrderExtraction(BaseModel):
    dish: str = Field(description="Dish name extracted from user message")
    quantity: int = Field(description="Quantity requested")
    needs_clarification: bool = Field(description="True if dish or quantity is unclear")
    clarification_question: str = Field(description="Question to ask user if clarification needed")

def order_agent_node(state):
    """Specialist: handles order taking and user conversation"""
    
    user_msg = state["messages"][-1].content
    
    system_prompt = """You are the Order Agent for a restaurant.
    Your ONLY job: extract dish name and quantity from user messages.
    
    - If the user's request is clear, extract dish + quantity
    - If unclear (missing quantity, ambiguous dish), set needs_clarification=True 
      and write a friendly clarification question
    - Use fuzzy matching for typos (piza → pizza, burgr → burger)
    """
    
    structured_llm = llm.with_structured_output(OrderExtraction)
    extraction = structured_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_msg)
    ])
    
    if extraction.needs_clarification:
        return {
            "messages": [extraction.clarification_question],
            "order_status": "awaiting_clarification",
            "next_agent": "FINISH"  # Wait for user reply
        }
    
    return {
        "current_order": {"dish": extraction.dish, "qty": extraction.quantity},
        "order_status": "extracted",
        "messages": [f"Got it — {extraction.quantity}x {extraction.dish}. Checking stock..."],
        "next_agent": "inventory_agent"  # Hand off to inventory
    }
📦 Step 4: Build the Inventory Agent
Create backend/agents/inventory_agent.py:

python
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel
from langchain_groq import ChatGroq
import os

llm = ChatGroq(model="openai/gpt-oss-120b", api_key=os.getenv("GROQ_API_KEY"))

# Your existing inventory
INVENTORY = {
    "pizza": 5, "biryani": 10, "burger": 3, "paneer_tikka": 8,
    # ... all 16 dishes
}

class InventoryDecision(BaseModel):
    available: bool
    available_qty: int
    message_to_user: str
    action: str  # "proceed_to_kitchen", "offer_partial", "out_of_stock"

def inventory_agent_node(state):
    """Specialist: checks stock and handles partial orders"""
    
    order = state["current_order"]
    dish = order["dish"]
    requested_qty = order["qty"]
    
    available_qty = INVENTORY.get(dish, 0)
    
    if available_qty == 0:
        decision = InventoryDecision(
            available=False, available_qty=0,
            message_to_user=f"Sorry, {dish} is sold out. Would you like something else?",
            action="out_of_stock"
        )
    elif available_qty < requested_qty:
        decision = InventoryDecision(
            available=True, available_qty=available_qty,
            message_to_user=f"Only {available_qty} {dish} available (you asked for {requested_qty}). Proceed with {available_qty}?",
            action="offer_partial"
        )
    else:
        decision = InventoryDecision(
            available=True, available_qty=available_qty,
            message_to_user=f"Confirming {requested_qty}x {dish} — sending to kitchen!",
            action="proceed_to_kitchen"
        )
    
    # Update inventory if proceeding
    if decision.action == "proceed_to_kitchen":
        INVENTORY[dish] -= requested_qty
    
    return {
        "stock_info": {dish: available_qty},
        "order_status": "stock_checked" if decision.action == "proceed_to_kitchen" else "needs_user_input",
        "messages": [decision.message_to_user],
        "next_agent": "kitchen_agent" if decision.action == "proceed_to_kitchen" else "FINISH"
    }
🍳 Step 5: Build the Kitchen Agent
Create backend/agents/kitchen_agent.py:

python
import random
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq
import os

llm = ChatGroq(model="openai/gpt-oss-120b", api_key=os.getenv("GROQ_API_KEY"))

def kitchen_agent_node(state):
    """Specialist: cooks and serves, handles failures with retries"""
    
    order = state["current_order"]
    dish = order["dish"]
    qty = order["qty"]
    
    # Simulate cooking (60% success)
    cook_success = random.random() < 0.6
    
    if not cook_success:
        cook_retries = state.get("cook_retries", 0) + 1
        
        if cook_retries >= 2:
            return {
                "cook_result": "failed_permanently",
                "order_status": "cancelled",
                "messages": [f"Sorry, the kitchen couldn't prepare {dish} after multiple attempts. Order cancelled."],
                "next_agent": "FINISH"
            }
        
        return {
            "cook_result": "failed",
            "cook_retries": cook_retries,
            "order_status": "cooking_retry",
            "messages": [f"Kitchen issue with {dish} — retrying (attempt {cook_retries}/2)..."],
            "next_agent": "kitchen_agent"  # Self-retry
        }
    
    # Simulate serving (60% success)
    serve_success = random.random() < 0.6
    
    if not serve_success:
        serve_retries = state.get("serve_retries", 0) + 1
        
        if serve_retries >= 2:
            return {
                "serve_result": "failed_permanently",
                "order_status": "cancelled",
                "messages": [f"Cooked {dish} but couldn't serve it. Order cancelled, refund initiated."],
                "next_agent": "FINISH"
            }
        
        return {
            "serve_result": "failed",
            "serve_retries": serve_retries,
            "order_status": "serving_retry",
            "messages": [f"Serving issue — retrying (attempt {serve_retries}/2)..."],
            "next_agent": "kitchen_agent"
        }
    
    # Success!
    return {
        "cook_result": "success",
        "serve_result": "success",
        "order_status": "served",
        "final_result": f"🎉 Your {qty}x {dish} is ready and served. Enjoy!",
        "messages": [f"Your {qty}x {dish} is served. Enjoy your meal!"],
        "next_agent": "FINISH"
    }
🔀 Step 6: Wire the Multi-Agent Graph
Update main.py:

python
from langgraph.graph import StateGraph, END
from agents.state import AgentState
from agents.supervisor import supervisor_node
from agents.order_agent import order_agent_node
from agents.inventory_agent import inventory_agent_node
from agents.kitchen_agent import kitchen_agent_node

# Create graph
workflow = StateGraph(AgentState)

# Add all agent nodes
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("order_agent", order_agent_node)
workflow.add_node("inventory_agent", inventory_agent_node)
workflow.add_node("kitchen_agent", kitchen_agent_node)

# Set entry point
workflow.set_entry_point("supervisor")

# Supervisor routes to any agent
workflow.add_conditional_edges(
    "supervisor",
    lambda state: state["next_agent"],
    {
        "order_agent": "order_agent",
        "inventory_agent": "inventory_agent",
        "kitchen_agent": "kitchen_agent",
        "FINISH": END
    }
)

# All agents report back to supervisor (this is the key multi-agent pattern!)
workflow.add_edge("order_agent", "supervisor")
workflow.add_edge("inventory_agent", "supervisor")
workflow.add_edge("kitchen_agent", "supervisor")

# Compile
app = workflow.compile()
🔄 How the Flow Works
text
User: "I want 10 burgers"
   │
   ▼
Supervisor → "New order, route to order_agent"
   │
   ▼
Order Agent → extracts {dish: burger, qty: 10} → back to Supervisor
   │
   ▼
Supervisor → "Order extracted, check stock → inventory_agent"
   │
   ▼
Inventory Agent → "Only 3 burgers left, offer partial" → back to Supervisor
   │
   ▼
Supervisor → "Waiting for user input → FINISH (wait for reply)"
   │
User: "Yes, give me 3"
   │
   ▼
Supervisor → "User confirmed partial, update order → order_agent"
   │
   ▼
Order Agent → updates order to {dish: burger, qty: 3} → Supervisor
   │
   ▼
Supervisor → "Stock confirmed, cook it → kitchen_agent"
   │
   ▼
Kitchen Agent → cooks, serves → Supervisor
   │
   ▼
Supervisor → "Served successfully → FINISH"
Notice: The Supervisor is the traffic controller — every agent reports back to it, and it decides the next move. This is the exact pattern used in production multi-agent systems (CrewAI, AutoGen, LangGraph's official multi-agent examples).

🏆 Which One Should You Do First?
Criteria	RAG (Option 1)	Multi-Agent (Option 2)
Difficulty	Medium	Hard
Time to build	1-2 days	3-5 days
Interview impact	High (RAG is everywhere in job posts)	Very High (multi-agent is the hottest 2026 skill)
Builds on	Your existing single-agent	Requires refactoring your current agent
🎯 My Recommendation
Do RAG first (1-2 days), then Multi-Agent (3-5 days). Here's why:

RAG is easier and immediately makes your project more impressive

Once RAG works, you can add it as a 4th agent in the multi-agent system (Menu RAG Agent)

Final architecture becomes: Supervisor → Order Agent → Inventory Agent → RAG Menu Agent → Kitchen Agent — that's a genuinely production-grade multi-agent system

🚀 Final Architecture (After Both Upgrades)
text
                    ┌─────────────────┐
                    │  Supervisor     │
                    └────────┬────────┘
                             │
    ┌───────────┬────────────┼────────────┬───────────┐
    ▼           ▼            ▼            ▼           
┌────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐
│ Order  │ │Inventory │ │ RAG     │ │ Kitchen  │
│ Agent  │ │ Agent    │ │ Menu    │ │ Agent    │
└────────┘ └──────────┘ │ Agent   │ └──────────┘
                        └─────────┘
This is a real 4-agent system with RAG — that's a portfolio piece that gets you interviews. 🚀

Want me to write the complete code for the RAG agent as a 4th agent in the multi-agent system next? That's the final piece that ties it all together. 🍕🤖

Do you have any Open Quetions then tell me????

## Current implementation in this repository

The RAG and specialist-agent flow described above is now implemented in the application:

- `backend/menu_rag.py` indexes the menu catalog in memory and ranks menu documents with TF-IDF cosine similarity. It filters sold-out dishes, supports dietary/spice constraints, and applies price limits. This lightweight local retriever needs no vector-database service or model download.
- The LangGraph supervisor routes requests to menu RAG, inventory, kitchen, and service specialists. API session state includes `agent_trace` and the retrieved `recommendations` for inspection.
- Menu recommendation prices follow the storefront's USD prices. Recommendations are grounded in retrieved menu descriptions and current inventory.

Run the backend from `backend` with `python -m uvicorn api:app --reload`, and run the frontend from `frontend` with `npm run dev`. Backend tests can be run from `backend` using `python -m pytest -q test_scenarios.py`.