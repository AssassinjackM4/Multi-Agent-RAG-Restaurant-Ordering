<div align="center">

# 🍽️ Multi Agent RAG Restaurant Ordering

### *From "I'm Hungry" to "Enjoy Your Meal" — Fully Autonomous!* 🤖🍳

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2-1C3C3C?logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![Groq AI](https://img.shields.io/badge/Groq_AI-F5C542?logo=groq&logoColor=white)](https://groq.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white)](https://reactjs.org/)
[![Vite](https://img.shields.io/badge/Vite-5-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

> 💬 **"I want 2 pizzas, but make it quick!"**  
> 🤖 **"Great choice! Checking stock... 5 pizzas available. Sending 2 to the kitchen — they'll be ready shortly!"**  
> 🍳 *Kitchen is cooking...*  
> 🍕 **"Your 2 pizzas are ready and served. Enjoy your meal!"**

**This isn't just a chatbot — it's a complete AI Agent that thinks, plans, checks inventory, manages a simulated kitchen, handles failures gracefully, and completes your entire food order autonomously.**

<div align="center">

[![🚀 Live Demo](https://img.shields.io/badge/🚀_Try_The_AI_Chef-Click_Here-2ea44f?style=for-the-badge&logo=vercel&logoColor=white)](https://ai-restaurant-order-agent.vercel.app/)

</div>

---

## 🧠 Why This Is a TRUE AI Agent

Most "AI chatbots" just answer questions. This agent **thinks, plans, acts, and adapts** — powered by LangGraph's state machine architecture:

| 🧠 Agent Capability | 🍽️ How This Agent Uses It |
|---------------------|---------------------------|
| 🧠 **Autonomous Decisions** | The LLM node reads order status + retry counters and decides: *take order, confirm, cook, serve, retry, or end?* |
| 🔁 **Multi-Step Workflows** | Full journey: `user_input → llm → order_confirm → cook → serve → END` |
| 🛠️ **Tool Usage** | Checks live menu inventory, validates dishes, manages kitchen operations |
| 🔄 **Self-Correction** | Cook failed? Serve failed? The agent intelligently retries — up to 2 cook retries & 2 serve retries |
| 💬 **Context Memory** | Remembers the conversation, pending offers, and guides users across multiple turns |
| 🚦 **Smart Routing** | Conditional edges route the flow based on what the LLM decides — not hardcoded logic |

---

## ✨ Features

- 🤖 **AI Chef Agent** — Natural language food ordering, powered by Groq's lightning-fast LLM
- 📦 **Live Inventory System** — 16 dishes with real-time stock tracking (sold-out items included!)
- 🔍 **Fuzzy Dish Matching** — "piza" → pizza, "burgr" → burger, "biryani rice" → biryani
- ⚖️ **Partial Order Intelligence** — Want 10 burgers but only 3 left? The agent offers what's available!
- 🍳 **Simulated Kitchen Engine** — Cook & serve nodes with realistic 60% success rates
- 🔄 **Smart Retry System** — 3 order attempts, 2 cook retries, 2 serve retries — all LLM-managed
- 🚫 **Intent Classification** — Orders vs. stock questions vs. chit-chat — the agent knows the difference
- 🌐 **Full-Stack Experience** — FastAPI + LangGraph backend, React Vite glassy chat frontend
- 🧪 **Built-in Simulation Mode** — Test scripted scenarios with pre-decided cook/serve outcomes

---

## 🛠️ Tech Stack

| Category | Technology |
|----------|------------|
| 🤖 **AI Agent** | LangGraph, LangChain Core |
| 🧠 **LLM** | Groq AI (GPT-OSS-120B) |
| ⚙️ **Backend** | Python, FastAPI, Uvicorn |
| 💻 **Frontend** | React 18, Vite, Tailwind CSS |
| 🔌 **API** | RESTful APIs, Axios |
| 🚀 **Deployment** | Vercel (Frontend), Render (Backend) |
| ✅ **Validation** | Pydantic, Structured Outputs |
| 🔍 **Matching** | difflib Fuzzy Matching |

---

## 🔄 Agent Workflow

```text
                    ┌─────────────┐
                    │ user_input  │◀──────────────┐
                    └──────┬──────┘               │
                           ▼                      │
                    ┌─────────────┐               │
             ┌─────▶│     llm     │───────────────┤
             │      └──────┬──────┘               │
             │             │                      │
             │             ▼                      │
             │      ┌───────────────┐            │
             │      │ order_confirm │────────────┤
             │      └───────────────┘            │
             │                                    │
             │             ┌───────┐             │
             └─────────────│ cook  │─────────────┤
                           └───────┘             │
                                                 │
                           ┌───────┐             │
                           │ serve │─────────────┘
                           └───────┘
                                 │
                                 ▼
                               END
```

### 🧠 **The LLM is the Brain**

Every node reports back to the `llm` node by writing a `status`. The LLM reads the state — status, retry counters, pending offers — and decides:

> *"Should I ask the user something? Confirm the order? Send it to the kitchen? Retry a failed cook? Or end the session?"*

**That's what makes it an agent, not a chatbot.**

---
## 🎬 See the Agent in Action

### 📦 **Live Stock Checking**
```text
🧑 "Do you have biryani?"
🤖 "We have 10 biryani available right now. Tell me how many you would like to order."
```

### ⚖️ **Partial Order Intelligence**
```text
🧑 "I want 10 burgers"
🤖 "Only 3 burgers are available. Would you like to go ahead with 3?"
🧑 "Yes, give me what you have"
🤖 "Confirming your order of 3 burgers — sending it to the kitchen!"
```

### 🔍 **Typo? No Problem!**
```text
🧑 "I want 1 piza"
🤖 "We have 5 pizza available right now. How many would you like?"
```

### 🚫 **Knows Its Job**
```text
🧑 "What's the capital of France?"
🤖 "I'm an AI agent for food ordering only. Please place a food order (dish + quantity)!"
```

### 🔄 **Handles Kitchen Failures**
```text
🍳 *Cook fails...*
🤖 "There was a problem in the kitchen — the dish is being cooked again!"
🍳 *Cook fails again...*
🤖 "We sincerely apologize — the kitchen couldn't prepare your dish. Your order has been cancelled."
---
## 🧪 Test the Agent
Try these conversation flows:
```text
1. "I want 2 pizzas"                    → Full order flow
2. "Do you have biryani?"               → Live stock check
3. "I want 10 burgers"                  → Partial order offer
4. "Yes, give me what you have"         → Partial confirmation
5. "I want 1 piza"                      → Fuzzy matching
6. "What vegetarian food do you have?"  → Full menu inventory
7. "What's the weather?"                → Polite boundary
```
---
## 🧠 Key Concepts Demonstrated

- **LangGraph StateGraph** — Finite state machine powering agent workflows
- **Conditional Edges** — Dynamic routing driven by LLM decisions
- **Structured Outputs** — Pydantic models for reliable intent extraction
- **Message Memory** — `add_messages` annotation for multi-turn conversations
- **Intelligent Retries** — LLM-managed retry counters for cook & serve failures
- **Fuzzy Matching** — `difflib` for typo-tolerant dish recognition
- **Full-Stack Integration** — FastAPI + React connected via RESTful APIs

---
## 🚀 Deployment

### **Backend (Render)**
| Setting | Value |
|---------|-------|
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
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
<div align="center">

### 🍕 *Hungry? Let the AI Chef take your order!* 🤖

**⭐ Star this repo if you found it helpful!**

Built with ❤️ using LangGraph, Groq AI, FastAPI & React

</div>
