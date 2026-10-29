"""Deterministic tests for the conversation and retry scenarios in prompt.md."""

import re
from concurrent.futures import ThreadPoolExecutor

import main
import pytest


class FakeStructuredOutput:
    def invoke(self, messages):
        text = str(messages[-1].content).strip().lower()
        partial_offer = "was the user just offered a partial order? yes" in str(messages[0].content).lower()

        if partial_offer and (
            text in {"yes", "yes please", "ok", "okay", "go ahead"}
            or "send the available quantity" in text
        ):
            return main.OrderIntent(intent="accept_partial")

        if any(
            term in text
            for term in (
                "available",
                "in stock",
                "how many",
                "stock of",
                "what foods",
                "what vegetarian",
                "what do you have",
            )
        ):
            for dish in main.MENU:
                if dish in text or f"{dish}s" in text:
                    return main.OrderIntent(intent="availability", dish_name=dish)
            if "paella" in text:
                return main.OrderIntent(intent="availability", dish_name="paella")
            return main.OrderIntent(intent="availability")

        quantity_match = re.search(r"\b(\d+)\b", text)
        quantity = int(quantity_match.group(1)) if quantity_match else 1
        for dish in main.MENU:
            if dish in text or f"{dish}s" in text:
                return main.OrderIntent(intent="new_order", dish_name=dish, quantity=quantity)
        return main.OrderIntent(intent="unrelated")


class FakeLLM:
    def with_structured_output(self, _schema):
        return FakeStructuredOutput()

    def invoke(self, _messages):
        return type("ModelResponse", (), {"content": "Thanks, I have the latest update for your order."})()


main.llm = FakeLLM()


@pytest.fixture(autouse=True)
def reset_inventory():
    main.reset_inventory()
    yield
    main.reset_inventory()


def test_tc1():
    state = main.simulate(
        ["what is the weather today?", "I want 5 burgers", "no, give me 2 pasta instead"]
    )
    assert state["order_retries"] == 0
    assert state["final_result"] == "NOT COMPLETED: order attempts exhausted"


def test_tc2():
    state = main.simulate(
        ["2 pizzas"],
        cook_outcomes=[False, True, True],
        serve_outcomes=[False, True],
    )
    assert state["final_result"] == "COMPLETED"
    assert state["cook_retries"] == 0
    assert state["serve_retries"] == 1


def test_tc3():
    state = main.simulate(
        ["5 burgers", "no, give me 1 dosa"],
        cook_outcomes=[False, True, True],
        serve_outcomes=[False, False],
    )
    assert state["final_result"] == "NOT COMPLETED: serve failed and cook retries exhausted"
    assert state["cook_retries"] == 0


def test_order_confirmation_marks_unknown_dish_unavailable():
    state = main.initial_state()
    state["order"] = {
        "dish_name": "mystery dish",
        "required_quantity": 1,
        "available_quantity": 0,
    }
    result = main.order_confirm(state)
    assert result["status"] == "unavailable"
    assert result["order"]["available_quantity"] == 0


def test_menu_item_lookup_rejects_blank_names():
    assert main.find_menu_item("") is None


def test_llm_node_handles_missing_human_messages_gracefully():
    state = main.initial_state()
    answer = main.llm_node(state)

    assert answer["status"] == "awaiting_user"
    assert "order" in answer["messages"][0].content.lower()


def test_menu_requests_with_menu_phrases_are_identified_without_llm():
    state = main.initial_state()
    state["messages"] = [main.HumanMessage("Show me the menu")]

    answer = main.llm_node(state)

    assert answer["status"] == "awaiting_user"
    assert "Current menu stock:" in answer["messages"][0].content


def test_availability_questions_report_exact_menu_stock_without_llm(monkeypatch):
    def fail_if_llm_extracts(_state):
        raise AssertionError("Menu availability should be answered from the restaurant inventory.")

    monkeypatch.setattr(main, "extract_order", fail_if_llm_extracts)

    specific_state = main.initial_state()
    specific_state["messages"] = [main.HumanMessage("Is pasta available?")]
    specific_answer = main.llm_node(specific_state)
    assert specific_answer["order"]["dish_name"] == "pasta"
    assert specific_answer["order"]["available_quantity"] == 0
    assert "sold out" in specific_answer["messages"][0].content

    menu_state = main.initial_state()
    menu_state["messages"] = [main.HumanMessage("What foods are available?")]
    menu_answer = main.llm_node(menu_state)
    for dish, quantity in main.MENU.items():
        assert f"{dish}: {quantity}" in menu_answer["messages"][0].content


def test_new_front_page_dishes_have_inventory():
    for dish in (
        "red sauce penne pasta",
        "veg burger",
        "veg biryani",
        "white sauce penne pasta",
    ):
        state = main.initial_state()
        state["order"] = {
            "dish_name": dish,
            "required_quantity": 1,
            "available_quantity": 0,
        }
        result = main.order_confirm(state)
        assert result["status"] == "confirmed"
        assert result["order"]["dish_name"] == dish
        assert result["order"]["available_quantity"] > 0


def test_menu_inventory_and_rag_catalog_stay_in_sync():
    from menu_rag import CATALOG

    veg_chinese_ids = {
        "veg momos",
        "chinese veg dumplings",
        "veg spring rolls",
        "veg fried rice",
        "chilli paneer",
    }

    assert set(main.MENU) == {item["id"] for item in CATALOG}
    assert all(main.MENU[item["id"]] >= 0 for item in CATALOG)
    assert all(item["price"] > 0 and item["description"] and item["tags"] for item in CATALOG)
    assert {"sushi", "ramen"}.issubset(main.MENU)
    assert veg_chinese_ids.issubset(main.MENU)
    veg_chinese_items = [item for item in CATALOG if item["id"] in veg_chinese_ids]
    assert len(veg_chinese_items) == len(veg_chinese_ids)
    assert all(item["category"] == "Veg Chinese" for item in veg_chinese_items)
    assert all("vegetarian" in item["tags"] for item in veg_chinese_items)


@pytest.mark.parametrize(
    ("cuisine", "expected_dish"),
    (
        ("Italian", "lasagna"),
        ("Indian", "chicken tikka masala"),
        ("Thai", "green curry"),
        ("American", "mac and cheese"),
        ("Veg Chinese", "veg momos"),
    ),
)
def test_rag_can_recommend_added_dishes_from_cuisines(cuisine, expected_dish):
    state = main.run_turn(main.initial_state(), f"Recommend a famous {cuisine} dish")

    assert state["status"] == "awaiting_user"
    assert expected_dish in {item["id"] for item in state["recommendations"]}
    assert "menu_rag_agent" in state["agent_trace"]


def test_menu_rag_recommendations_respect_dietary_price_and_stock_filters():
    from menu_rag import recommend_menu_items

    results = recommend_menu_items(
        "Suggest a spicy vegetarian dish under $18",
        main.MENU,
    )

    assert results
    assert all(result["stock"] > 0 for result in results)
    assert all(result["price"] < 18 for result in results)
    assert all("vegetarian" in result["tags"] for result in results)
    assert all("spicy" in result["tags"] for result in results)
    assert results[0]["id"] == "veg biryani"


def test_menu_rag_finds_related_dish_without_recommending_the_anchor():
    from menu_rag import recommend_menu_items

    results = recommend_menu_items("Something similar to butter chicken but cheaper than $20", main.MENU)

    assert results
    assert all(result["id"] != "butter chicken" for result in results)
    assert all(result["price"] < 20 for result in results)
    assert results[0]["id"] == "chicken tikka masala"


@pytest.mark.parametrize(
    "query",
    (
        "Suggest something spicy under ₹200",
        "Suggest something spicy under INR 200",
        "Suggest something spicy under Rs. 200",
    ),
)
def test_inr_budget_is_not_compared_to_usd_menu_prices(query):
    state = main.run_turn(main.initial_state(), query)

    assert state["recommendations"] == []
    assert "listed in USD" in state["messages"][-1].content
    assert state["agent_trace"] == ["supervisor", "menu_rag_agent"]


def test_menu_rag_runs_as_a_specialist_and_records_agent_trace():
    state = main.run_turn(main.initial_state(), "Recommend a spicy vegetarian dish under $18")

    assert state["status"] == "awaiting_user"
    assert state["recommendations"][0]["id"] == "veg biryani"
    assert state["agent_trace"] == ["supervisor", "menu_rag_agent"]
    assert "latest update" in state["messages"][-1].content


def test_inventory_reservation_prevents_concurrent_overselling():
    def reserve_two_pizzas(_):
        state = main.initial_state()
        state["order"] = {
            "dish_name": "pizza",
            "required_quantity": 2,
            "available_quantity": 0,
        }
        return main.order_confirm(state)

    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(reserve_two_pizzas, range(5)))

    assert sum(result["status"] == "confirmed" for result in results) == 2
    assert sum(result["reserved_quantity"] for result in results) == 4
    assert main.inventory_snapshot()["pizza"] == 1


def test_partial_order_confirmation_rechecks_and_reserves_stock():
    state = main.run_turn(main.initial_state(), "I want 5 burgers")
    assert state["status"] == "awaiting_user"
    assert state["pending_partial_confirmation"] is True
    assert main.inventory_snapshot()["burger"] == 3

    state = main.run_turn(
        state,
        "Yes, please send the available quantity.",
        config={"configurable": {"cook_outcomes": [True], "serve_outcomes": [True]}},
    )

    assert state["status"] == "done"
    assert state["reserved_quantity"] == 3
    assert main.inventory_snapshot()["burger"] == 0


def test_failed_simulated_kitchen_releases_inventory_reservation():
    state = main.run_turn(
        main.initial_state(),
        "I want 2 pizzas",
        config={"configurable": {"cook_outcomes": [False, False, False]}},
    )

    assert state["status"] == "failed"
    assert state["final_result"] == "NOT COMPLETED: cook failed"
    assert state["reserved_quantity"] == 0
    assert main.inventory_snapshot()["pizza"] == main.INITIAL_MENU["pizza"]


def test_api_menu_and_multi_item_checkout():
    from fastapi.testclient import TestClient

    import api

    client = TestClient(api.app)
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/api/menu").json()["items"]["pasta"] == 0
    assert client.get("/api/menu").json()["items"]["red sauce penne pasta"] > 0

    session_id = client.post("/api/chat/sessions").json()["session_id"]
    recommendation = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"message": "Recommend a spicy vegetarian dish under $18"},
    )
    assert recommendation.status_code == 200, recommendation.text
    recommendation_state = recommendation.json()["state"]
    assert recommendation_state["recommendations"][0]["id"] == "veg biryani"
    assert recommendation_state["agent_trace"] == ["supervisor", "menu_rag_agent"]

    response = client.post(
        "/api/checkout",
        json={
            "items": [
                {"dish_name": "pizza", "quantity": 2},
                {"dish_name": "burger", "quantity": 5},
            ]
        },
    )
    assert response.status_code == 200, response.text
    orders = response.json()["orders"]
    assert len(orders) == 2
    assert orders[0]["state"]["order"]["dish_name"] == "pizza"
    first_order_completed = orders[0]["state"]["status"] == "done"
    assert orders[0]["state"]["status"] in {"done", "failed"}
    assert orders[0]["state"]["reserved_quantity"] == (2 if first_order_completed else 0)
    assert orders[1]["state"]["status"] == "awaiting_user"
    assert orders[1]["state"]["order"]["available_quantity"] == 3
    assert client.get("/api/menu").json()["items"]["pizza"] == (
        main.INITIAL_MENU["pizza"] - 2 if first_order_completed else main.INITIAL_MENU["pizza"]
    )

    response = client.post(
        f"/api/sessions/{orders[1]['session_id']}/messages",
        json={"message": "Yes, please send the available quantity."},
    )
    assert response.status_code == 200, response.text
    next_state = response.json()["state"]
    assert next_state["order"]["required_quantity"] == 3
    assert next_state["status"] in {"done", "failed"}
    assert next_state["reserved_quantity"] == (3 if next_state["status"] == "done" else 0)
    assert client.get("/api/menu").json()["items"]["burger"] == (
        0 if next_state["status"] == "done" else main.INITIAL_MENU["burger"]
    )


def test_api_allows_deployed_vercel_frontend_origin():
    from fastapi.testclient import TestClient

    import api

    client = TestClient(api.app)
    response = client.options(
        "/api/menu",
        headers={
            "Origin": "https://ai-restaurant-order-agent.vercel.app",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://ai-restaurant-order-agent.vercel.app"


def test_api_chat_can_check_stock_then_place_order():
    from fastapi.testclient import TestClient

    import api

    client = TestClient(api.app)
    session = client.post("/api/chat/sessions")
    assert session.status_code == 200, session.text
    session_id = session.json()["session_id"]

    response = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"message": "How many pizzas are in stock?"},
    )
    assert response.status_code == 200, response.text
    state = response.json()["state"]
    assert state["status"] == "awaiting_user"
    assert state["order"]["dish_name"] == "pizza"
    assert state["order"]["available_quantity"] == main.MENU["pizza"]
    assert state["order"]["required_quantity"] == 0
    assert state["pending_partial_confirmation"] is False
    assert str(main.MENU["pizza"]) in state["messages"][-1]["content"]

    response = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"message": "I would like 2 pizzas."},
    )
    assert response.status_code == 200, response.text
    state = response.json()["state"]
    assert state["order"]["required_quantity"] == 2
    assert state["status"] in {"done", "failed"}

    second_session = client.post("/api/chat/sessions").json()["session_id"]
    response = client.post(
        f"/api/sessions/{second_session}/messages",
        json={"message": "What's available?"},
    )
    assert response.status_code == 200, response.text
    state = response.json()["state"]
    assert state["status"] == "awaiting_user"
    assert state["order"]["dish_name"] == ""
    answer = state["messages"][-1]["content"]
    for dish, quantity in main.MENU.items():
        assert f"{dish}: {quantity}" in answer

    response = client.post(
        f"/api/sessions/{second_session}/messages",
        json={"message": "What vegetarian foods do you have?"},
    )
    assert response.status_code == 200, response.text
    state = response.json()["state"]
    assert state["status"] == "awaiting_user"
    assert state["recommendations"]
    assert all("vegetarian" in item["tags"] for item in state["recommendations"])


def test_api_chat_reports_unknown_dish_not_on_menu():
    from fastapi.testclient import TestClient

    import api

    client = TestClient(api.app)
    session_id = client.post("/api/chat/sessions").json()["session_id"]
    response = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"message": "Is paella available?"},
    )
    assert response.status_code == 200, response.text
    state = response.json()["state"]
    assert state["order"]["dish_name"] == "paella"
    assert "isn't listed on our menu" in state["messages"][-1]["content"]


def test_api_explains_missing_groq_key(monkeypatch):
    from fastapi.testclient import TestClient

    import api

    monkeypatch.setattr(main, "llm", None)
    response = TestClient(api.app).post(
        "/api/checkout",
        json={"items": [{"dish_name": "pizza", "quantity": 1}]},
    )
    assert response.status_code == 503
    assert "GROQ_API_KEY" in response.json()["detail"]
