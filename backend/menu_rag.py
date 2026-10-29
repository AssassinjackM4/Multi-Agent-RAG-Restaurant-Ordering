"""Lightweight, local TF-IDF retrieval for grounded menu recommendations."""

from __future__ import annotations

import math
import re
from typing import TypedDict


class MenuRecommendation(TypedDict):
    id: str
    name: str
    description: str
    price: float
    category: str
    tags: list[str]
    stock: int
    score: float


CATALOG: tuple[dict[str, object], ...] = (
    {"id": "red sauce penne pasta", "name": "Red sauce penne pasta", "description": "Penne tossed in slow-simmered tomato sauce with fresh basil. Bright, savory Italian comfort food.", "price": 17, "category": "Italian", "tags": ["vegetarian", "tomato", "pasta", "light"]},
    {"id": "veg burger", "name": "Veg burger", "description": "Crispy garden patty with ripe tomato and tangy house sauce. A hearty plant-powered classic.", "price": 14, "category": "American", "tags": ["vegetarian", "plant based", "savory"]},
    {"id": "veg biryani", "name": "Veg biryani", "description": "Fragrant dum-cooked basmati rice with garden vegetables and warming Indian herbs and spices.", "price": 16, "category": "Indian", "tags": ["vegetarian", "rice", "spicy", "aromatic"]},
    {"id": "white sauce penne pasta", "name": "White sauce penne pasta", "description": "Penne in a silky parmesan cream sauce with cracked pepper. Rich, creamy Italian comfort food.", "price": 17, "category": "Italian", "tags": ["vegetarian", "cheesy", "creamy", "pasta"]},
    {"id": "pizza", "name": "Pizza", "description": "A shareable oven-baked pizza with tomato, melted cheese and herbs. Familiar, savory and satisfying.", "price": 16, "category": "Italian", "tags": ["vegetarian", "cheesy", "tomato", "shareable"]},
    {"id": "burger", "name": "Burger", "description": "A classic juicy beef burger layered with fresh vegetables and savory sauce.", "price": 15, "category": "American", "tags": ["beef", "savory", "hearty"]},
    {"id": "biryani", "name": "Biryani", "description": "Aromatic basmati rice layered with tender chicken and traditional spices. Rich and moderately spicy.", "price": 19, "category": "Indian", "tags": ["chicken", "rice", "spicy", "rich"]},
    {"id": "dosa", "name": "Masala dosa", "description": "A golden-crisp fermented rice crepe filled with potato masala and served with chutneys.", "price": 12, "category": "Indian", "tags": ["vegetarian", "crispy", "light", "potato"]},
    {"id": "pasta", "name": "Creamy truffle pasta", "description": "Silky parmesan cream, mushrooms and a touch of truffle. A rich and earthy Italian pasta.", "price": 17, "category": "Italian", "tags": ["vegetarian", "creamy", "mushroom", "rich"]},
    {"id": "tacos", "name": "Tacos", "description": "Soft tortillas with seasoned filling, crisp vegetables and a bright, zesty salsa.", "price": 15, "category": "American", "tags": ["savory", "fresh", "zesty"]},
    {"id": "sushi", "name": "Salmon sushi set", "description": "Hand-rolled salmon maki served with ginger and wasabi. Fresh, delicate and balanced.", "price": 21, "category": "Japanese", "tags": ["fish", "fresh", "light", "rice"]},
    {"id": "ramen", "name": "Miso butter ramen", "description": "A slow-simmered miso broth with springy noodles and a jammy egg. Warm, savory Japanese comfort food.", "price": 19, "category": "Japanese", "tags": ["noodles", "soup", "savory", "comfort"]},
    {"id": "butter chicken", "name": "Butter chicken", "description": "Tandoor-kissed chicken in a velvety tomato and butter sauce with fragrant Indian spices.", "price": 18, "category": "Indian", "tags": ["chicken", "tomato", "creamy", "spicy"]},
    {"id": "pad thai", "name": "Bangkok pad thai", "description": "Tamarind rice noodles with roasted peanuts and lime. Sweet, savory and tangy Thai street-food favorite.", "price": 16, "category": "Thai", "tags": ["noodles", "peanut", "tangy", "savory"]},
    {"id": "falafel", "name": "Green garden falafel", "description": "Herby chickpea falafel with crisp greens and whipped tahini. A fresh, plant-based Mediterranean meal.", "price": 13, "category": "Mediterranean", "tags": ["vegan", "vegetarian", "plant based", "light", "protein"]},
    {"id": "cheesecake", "name": "Vanilla bean cheesecake", "description": "Slow-baked vanilla bean cheesecake with berry compote. A creamy, lightly sweet dessert.", "price": 9, "category": "Dessert", "tags": ["vegetarian", "sweet", "dessert", "creamy"]},
    {"id": "lasagna", "name": "Classic beef lasagna", "description": "Slow-baked layers of pasta, rich ragù, béchamel and golden parmesan.", "price": 19, "category": "Italian", "tags": ["beef", "pasta", "cheesy", "oven baked"]},
    {"id": "margherita pizza", "name": "Margherita pizza", "description": "Wood-fired style pizza with tomato, creamy mozzarella and fresh basil.", "price": 16, "category": "Italian", "tags": ["vegetarian", "cheesy", "tomato", "basil"]},
    {"id": "chicken tikka masala", "name": "Chicken tikka masala", "description": "Tandoor-charred chicken in a velvety tomato curry with warm spices.", "price": 18, "category": "Indian", "tags": ["chicken", "spicy", "creamy", "curry"]},
    {"id": "chole bhature", "name": "Chole bhature", "description": "Punjabi spiced chickpeas served with fluffy, deep-fried bhature.", "price": 15, "category": "Indian", "tags": ["vegetarian", "chickpea", "spicy", "street food"]},
    {"id": "green curry", "name": "Thai green curry", "description": "Fragrant green curry with coconut milk, Thai basil and seasonal vegetables.", "price": 17, "category": "Thai", "tags": ["vegetarian", "coconut", "spicy", "curry"]},
    {"id": "mac and cheese", "name": "Baked mac and cheese", "description": "Tender macaroni in a rich cheddar cheese sauce with a crisp baked top.", "price": 15, "category": "American", "tags": ["vegetarian", "pasta", "cheesy", "comfort"]},
    {"id": "tiramisu", "name": "Classic tiramisu", "description": "Espresso-soaked ladyfingers layered with mascarpone and cocoa.", "price": 10, "category": "Dessert", "tags": ["vegetarian", "coffee", "sweet", "dessert"]},
    {"id": "veg momos", "name": "Steamed veg momos", "description": "Steamed vegetable dumplings served with bright tomato chutney.", "price": 12, "category": "Veg Chinese", "tags": ["vegetarian", "vegan", "momos", "dumplings", "steamed", "tomato chutney"]},
    {"id": "chinese veg dumplings", "name": "Chinese vegetable dumplings", "description": "Golden pan-seared vegetable potstickers with a savory dipping sauce.", "price": 13, "category": "Veg Chinese", "tags": ["vegetarian", "vegan", "dumplings", "potstickers", "pan seared", "savory"]},
    {"id": "veg spring rolls", "name": "Crispy veg spring rolls", "description": "Golden rolls filled with cabbage, carrots and sweet peppers, with chili dip.", "price": 10, "category": "Veg Chinese", "tags": ["vegetarian", "vegan", "spring rolls", "crispy", "cabbage", "carrot"]},
    {"id": "veg fried rice", "name": "Vegetable fried rice", "description": "Wok-tossed rice with crisp seasonal vegetables and fragrant scallions.", "price": 13, "category": "Veg Chinese", "tags": ["vegetarian", "vegan", "rice", "wok", "vegetables", "savory"]},
    {"id": "chilli paneer", "name": "Chilli paneer", "description": "Crisp paneer cubes with scallions in a tangy Indo-Chinese sauce.", "price": 14, "category": "Veg Chinese", "tags": ["vegetarian", "paneer", "Indo Chinese", "scallion", "savory"]},
)

SYNONYMS = {
    "veg": ("vegetarian", "vegetable", "plant"),
    "vegetarian": ("veg", "vegetable", "plant"),
    "vegan": ("plant", "falafel", "vegetarian"),
    "spicy": ("heat", "chili", "pepper", "spice"),
    "hot": ("heat", "chili", "spicy"),
    "light": ("fresh", "crisp", "balanced"),
    "healthy": ("fresh", "vegetable", "protein", "light"),
    "cheap": ("affordable", "budget"),
    "cheaper": ("affordable", "budget"),
    "similar": ("like", "same"),
}
TOKEN_RE = re.compile(r"[a-z]+")


def _tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def _maximum_price(query: str) -> float | None:
    match = re.search(r"\b(?:under|below|less than|cheaper than)\s*\$?\s*(\d+(?:\.\d{1,2})?)", query.lower())
    return float(match.group(1)) if match else None


def recommend_menu_items(
    query: str,
    inventory: dict[str, int],
    top_k: int = 5,
) -> list[MenuRecommendation]:
    """Rank in-stock menu documents with sparse TF-IDF cosine similarity."""
    documents: list[tuple[dict[str, object], str, list[str]]] = []
    for item in CATALOG:
        document = " ".join(
            [str(item["name"]), str(item["description"]), str(item["category"]), *item["tags"]]
        )
        documents.append((item, document, _tokens(document)))

    document_frequency: dict[str, int] = {}
    for _, _, terms in documents:
        for term in set(terms):
            document_frequency[term] = document_frequency.get(term, 0) + 1

    query_terms = _tokens(query)
    expanded_terms = query_terms + [
        synonym
        for term in query_terms
        for synonym in SYNONYMS.get(term, ())
    ]
    query_counts: dict[str, int] = {}
    for term in expanded_terms:
        query_counts[term] = query_counts.get(term, 0) + 1

    maximum_price = _maximum_price(query)
    vegetarian = "vegetarian" in query_terms or "vegan" in query_terms
    vegan = "vegan" in query_terms
    spicy = "spicy" in query_terms
    similar_query = "similar" in query_terms or "like" in query_terms
    similar_anchor = next(
        (
            item
            for item in sorted(CATALOG, key=lambda catalog_item: len(str(catalog_item["id"])), reverse=True)
            if str(item["id"]) in query.lower()
            or str(item["name"]).lower() in query.lower()
        ),
        None,
    ) if similar_query else None
    ranked: list[MenuRecommendation] = []

    for item, document, terms in documents:
        dish_id = str(item["id"])
        stock = inventory.get(dish_id, 0)
        price = float(item["price"])
        tags = list(item["tags"])
        if similar_anchor and dish_id == similar_anchor["id"]:
            continue
        if stock <= 0 or (maximum_price is not None and price >= maximum_price):
            continue
        if vegetarian and "vegetarian" not in tags:
            continue
        if vegan and "vegan" not in tags:
            continue
        if spicy and not {"spicy", "chili", "heat"}.intersection(tags):
            continue

        term_counts: dict[str, int] = {}
        for term in terms:
            term_counts[term] = term_counts.get(term, 0) + 1
        weights = {
            term: (1 + math.log(count)) * (math.log((len(documents) + 1) / (document_frequency[term] + 1)) + 1)
            for term, count in term_counts.items()
        }
        query_weights = {
            term: (1 + math.log(count))
            * (math.log((len(documents) + 1) / (document_frequency.get(term, 0) + 1)) + 1)
            for term, count in query_counts.items()
        }
        dot = sum(weight * query_weights.get(term, 0.0) for term, weight in weights.items())
        norm = math.sqrt(sum(weight * weight for weight in weights.values()))
        query_norm = math.sqrt(sum(weight * weight for weight in query_weights.values()))
        score = dot / (norm * query_norm) if norm and query_norm else 0.0
        if similar_anchor:
            anchor_tags = set(similar_anchor["tags"])
            shared_tags = anchor_tags.intersection(tags)
            score += len(shared_tags) / max(len(anchor_tags), 1)
        if score <= 0:
            continue

        ranked.append(
            {
                "id": dish_id,
                "name": str(item["name"]),
                "description": str(item["description"]),
                "price": price,
                "category": str(item["category"]),
                "tags": tags,
                "stock": stock,
                "score": score,
            }
        )

    ranked.sort(key=lambda result: (-result["score"], result["price"], result["name"]))
    return ranked[:top_k]
