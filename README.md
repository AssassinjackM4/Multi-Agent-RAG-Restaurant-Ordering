<div align="center">

# 🍕 Multi-Agent RAG Restaurant Ordering System

### *AI Chef Agent That Takes, Cooks & Serves Orders — Powered by Multi-Agent RAG!* 🤖🍽️

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2-1C3C3C?logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![Groq AI](https://img.shields.io/badge/Groq_AI-F5C542?logo=groq&logoColor=white)](https://groq.com/)
[![RAG](https://img.shields.io/badge/RAG-Vector_Search-4285F4?logo=google&logoColor=white)](https://www.trychroma.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white)](https://reactjs.org/)
[![Vite](https://img.shields.io/badge/Vite-5-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-FF6F00?logo=chroma&logoColor=white)](https://www.trychroma.com/)

</div>

> 💬 **"I'd like to order 2 Margherita pizzas and a Coke"**  
> 🎯 *Chef Agent: "Order received — checking live inventory..."*  
> 🔍 *RAG: Retrieving menu items and stock data...*  
> 🍕 *All items available! Confirming your order...*  
> 👨‍🍳 *Cooking in progress... Order served! Enjoy your meal!* 🎉

**I've built this Restaurant Ordering Agent — an AI-powered Multi-Agent RAG system that manages the complete order lifecycle. An AI Chef agent routes every customer request through specialized agents: Order Intake, Inventory Check, Order Confirmation, Cooking, and Serving. A ChromaDB-powered RAG pipeline grounds every response in live menu and stock data. Customers can order, check availability, and track their meal through natural conversation — instantly.**

<div align="center">

[![🚀 Live Demo](https://img.shields.io/badge/🚀_Try_The_AI_Chef-Click_Here-2ea44f?style=for-the-badge&logo=vercel&logoColor=white)](https://multi-agent-rag-restaurant-ordering1.vercel.app/)

</div>

---
## 🧠 Why This Is a TRUE Multi-Agent RAG System

Most ordering apps use hardcoded forms. This system uses **specialized agents + RAG-powered menu intelligence** to handle the entire order lifecycle through conversation:

| 🧠 Agent Capability | 🍕 How This System Uses It |
|---------------------|---------------------------|
| 👨‍🍳 **AI Chef Agent (Supervisor)** | Routes each customer request through the order workflow |
| 📦 **Inventory Check Agent** | Verifies live stock availability for every ordered item |
| ✅ **Order Confirmation Agent** | Confirms availability and locks in the order |
| 🔥 **Cooking Agent** | Processes the order through the cooking stage |
| 🍽️ **Serving Agent** | Completes the order and serves it to the customer |
| 🔍 **RAG Menu Intelligence** | ChromaDB vector search grounds responses in live menu and stock data |
| 💬 **Natural Conversation** | Customers order in plain language — no forms, no buttons |
| 🚦 **LangGraph Workflow** | Stateful agent graph manages the full order lifecycle |

---
## ✨ Features

- 🤖 **Multi-Agent Architecture** — AI Chef agent orchestrates the complete order workflow
- 🔍 **RAG-Powered Menu Intelligence** — ChromaDB vector search over menu and stock data
- 📦 **Live Inventory Checks** — Real-time stock verification before confirming orders
- ✅ **Order Confirmation** — Availability confirmed before cooking begins
- 🔥 **Full Order Lifecycle** — Order → Confirm → Cook → Serve, managed by LangGraph
- 💬 **Natural Language Ordering** — Customers order conversationally, no forms needed
- 🚫 **Smart Stock Handling** — Gracefully handles unavailable items
- ⚡ **Groq LLM Speed** — Lightning-fast conversational responses
- 🌐 **Full-Stack Experience** — FastAPI + LangGraph backend, React Vite chat frontend
- 🔒 **Structured Outputs** — Reliable, parseable agent responses

---
## 🛠️ Tech Stack

| Category | Technology |
|----------|------------|
| 🤖 **AI Agents** | LangGraph, LangChain Core |
| 🧠 **LLM** | Groq AI |
| 🔍 **RAG** | ChromaDB, Vector Search |
| ⚙️ **Backend** | Python, FastAPI, Uvicorn |
| 💻 **Frontend** | React 18, Vite, Tailwind CSS |
| 🔌 **API** | RESTful APIs, Axios |
| 🚀 **Deployment** | Vercel (Frontend), Render (Backend) |

---
## 🔄 Multi-Agent Order Workflow

```text
                    ┌─────────────────┐
                    │   AI Chef Agent │◀──────────────┐
                    │  (Supervisor)   │               │
                    └────────┬────────┘               │
                             │                        │
        ┌────────────────────┼────────────────────┐   │
        ▼                    ▼                    ▼   │
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│    Order     │───▶│  Inventory   │───▶│    Order     │
│   Intake     │    │    Check     │    │ Confirmation │
└──────────────┘    └──────────────┘    └──────┬───────┘
                                                │
                                                ▼
                                       ┌──────────────┐
                                       │    Cooking   │
                                       │    Agent     │
                                       └──────┬───────┘
                                              │
                                              ▼
                                       ┌──────────────┐
                                       │    Serving   │
                                       │    Agent     │
                                       └──────┬───────┘
                                              │
                                              ▼
                                            END 🎉
```

### 👨‍🍳 **The AI Chef Agent is the Brain**

Every customer message hits the AI Chef Agent first. It manages the flow:

> *"New order? → Take the order. Items requested? → Check live inventory. All available? → Confirm the order. Confirmed? → Cook it. Cooked? → Serve it."*

**That's what makes it a multi-agent system, not a chatbot.**

---
## 🔍 How RAG Works Here

```text
Customer: "Do you have Margherita pizza?"
        │
        ▼
┌──────────────┐
│  AI Chef     │──▶ RAG Menu Intelligence
│    Agent     │        │
└──────────────┘        ▼
            ┌─────────────────────────┐
            │ 1. Embed the query      │
            │ 2. Search ChromaDB for  │
            │    matching menu items  │
            │ 3. Retrieve live stock  │
            │    data                 │
            │ 4. Chef agent answers   │
            │    with grounded info   │
            └─────────────────────────┘
```

**No hallucinated menus. No stale stock data. Just accurate, source-backed answers.**

---
## 🎬 See the Agents in Action

### 🍕 **Ordering**
```text
🧑 "I want 2 Margherita pizzas and a Coke"
🤖 "Great choice! Let me check availability... Both items are in stock. Shall I confirm your order?"
```

### 📦 **Live Inventory Check**
```text
🧑 "Do you have Paneer Tikka?"
🤖 "Yes! Paneer Tikka is available — 8 portions in stock. Would you like to order?"
```

### 🚫 **Smart Stock Handling**
```text
🧑 "One Butter Chicken please"
🤖 "Sorry, Butter Chicken is currently out of stock. Would you like to try our Chicken Tikka instead?"
```

### 🍽️ **Order Completion**
```text
🧑 "Yes, confirm my order"
🤖 "Order confirmed! 👨‍🍳 Cooking in progress... Your order is ready and served. Enjoy your meal! 🎉"
```

---
## 🧪 Test the Workflow

Try these conversation flows:
```text
1. "I want to order a Margherita pizza"         → Order Intake
2. "Do you have Paneer Tikka?"                   → Inventory Check
3. "Confirm my order"                            → Order Confirmation
4. "What's available today?"                     → RAG Menu Intelligence
5. "Cancel my order"                             → Order Handling
```

---
## 🧠 Key Concepts Demonstrated
- **LangGraph Multi-Agent Systems** — AI Chef agent orchestrating a complete order workflow
- **RAG Pipeline** — ChromaDB vector search for menu and stock intelligence
- **Stateful Workflows** — LangGraph manages the order lifecycle across multiple stages
- **Structured Outputs** — Reliable, parseable agent responses
- **Real-Time Inventory** — Live stock checks before order confirmation
- **Full-Stack Integration** — FastAPI + React connected via RESTful APIs

---
## 🚀 Deployment

### **Backend (Render)**
| Setting | Value |
|---------|-------|
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn api:app --host 0.0.0.0 --port $PORT` |
| Environment Variable | `GROQ_API_KEY` |

### **Frontend (Vercel)**
| Setting | Value |
|---------|-------|
| Root Directory | `frontend` |
| Build Command | `npm run build` |
| Environment Variable | `VITE_API_URL=https://your-backend.onrender.com` |

---
## 🤝 Contributing
Contributions are welcome! 🎉

1. 🍴 Fork the repository
2. 🌿 Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. 💾 Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. 📤 Push to the branch (`git push origin feature/AmazingFeature`)
5. 🔃 Open a Pull Request

---
## 👨‍💻 Author
**AssassinjackM4**  
🤖 AI Agent Full-Stack Developer

- 💼 [LinkedIn](https://www.linkedin.com/in/aniket-meshram-0515a3223)
- 💻 [GitHub](https://github.com/AssassinjackM4)
- 🌐 [Live Demo](https://multi-agent-rag-restaurant-ordering1.vercel.app/)

---
<div align="center">

### 🍕 *Order. Cook. Serve. — Powered by Multi-Agent RAG.* 🤖

**⭐ Star this repo if you found it helpful!**

Built with ❤️ using LangGraph, Groq AI, ChromaDB, FastAPI & React

</div>
