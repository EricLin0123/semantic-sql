import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_template_total_quantity():
    from db.seed import main as seed_db

    seed_db()
    from pipeline.graph import run_turn

    result = run_turn("how many pieces of furniture in total?", [])
    assert result["type"] == "answer"
    assert "242" in result["answer"]


def test_template_category_breakdown_includes_current_seed_data():
    from db.seed import main as seed_db

    seed_db()
    from pipeline.graph import run_turn

    result = run_turn("how many tables do we have?", [])
    assert result["type"] == "answer"
    assert "30" in result["answer"]
    assert "12 coffee table" in result["answer"]


def test_ambiguous_question_clarifies_without_llm():
    from db.seed import main as seed_db

    seed_db()
    from pipeline.graph import run_turn

    result = run_turn("tell me about the furniture", [])
    assert result["type"] == "clarify"
    assert "quantity" in result["question"].lower()


def test_price_question_returns_unit_price_not_quantity():
    from db.seed import main as seed_db

    seed_db()
    from pipeline.graph import run_turn

    result = run_turn("How much is a square table?", [])
    assert result["type"] == "answer"
    assert "$120.00" in result["answer"]
    assert "You have 10" not in result["answer"]


def test_location_followup_uses_previous_catalog_item():
    from db.seed import main as seed_db

    seed_db()
    from pipeline.graph import run_turn

    conversation = []
    first = run_turn("How much is a square table?", conversation)
    conversation.append({"role": "user", "content": "How much is a square table?"})
    conversation.append({"role": "assistant", "content": first["answer"]})

    result = run_turn("Where are they?", conversation)
    assert result["type"] == "answer"
    assert "Warehouse A" in result["answer"]
    assert "242 pieces" not in result["answer"]


def test_price_followup_one_uses_previous_catalog_item():
    from db.seed import main as seed_db

    seed_db()
    from pipeline.graph import run_turn

    conversation = []
    first = run_turn("How many recliner?", conversation)
    conversation.append({"role": "user", "content": "How many recliner?"})
    conversation.append({"role": "assistant", "content": first["answer"]})

    result = run_turn("How much is one?", conversation)
    assert result["type"] == "answer"
    assert "$310.00" in result["answer"]


def test_fallback_question_can_answer_from_conversation_history():
    from db.seed import main as seed_db

    seed_db()
    import re

    import pipeline.graph as graph
    import pipeline.nodes as nodes
    from pipeline.prompts import HISTORY_FALLBACK_PROMPT

    original_chat = nodes.chat
    graph._compiled_graph = None

    def fake_chat(system, messages):
        assert system == HISTORY_FALLBACK_PROMPT
        assert [message["role"] for message in messages] == [
            "user",
            "assistant",
            "user",
            "assistant",
            "user",
        ]
        assert messages[-1]["content"] == "what is the total cost?"

        prior_answers = "\n".join(message["content"] for message in messages[:-1] if message["role"] == "assistant")
        quantity = re.search(r"You have (\d+) corner desk", prior_answers)
        unit_price = re.search(r"corner desk costs \$([0-9,.]+)", prior_answers)
        assert quantity is not None
        assert unit_price is not None

        total = int(quantity.group(1)) * float(unit_price.group(1).replace(",", ""))
        return '{"action": "answer", "answer": "The total cost is $' + f'{total:,.2f}' + '."}'

    nodes.chat = fake_chat
    try:
        conversation = []

        first_question = "How many corner desk?"
        first = graph.run_turn(first_question, conversation)
        conversation.append({"role": "user", "content": first_question})
        conversation.append({"role": "assistant", "content": first["answer"]})

        second_question = "How much is one?"
        second = graph.run_turn(second_question, conversation)
        conversation.append({"role": "user", "content": second_question})
        conversation.append({"role": "assistant", "content": second["answer"]})

        result = graph.run_turn("what is the total cost?", conversation)
    finally:
        nodes.chat = original_chat
        graph._compiled_graph = None

    assert first["type"] == "answer"
    assert "4" in first["answer"]
    assert second["type"] == "answer"
    assert "$300.00" in second["answer"]
    assert result["type"] == "answer"
    assert "$1,200.00" in result["answer"]


def test_confirmation_question_uses_short_fallback():
    from db.seed import main as seed_db

    seed_db()
    from pipeline.graph import run_turn

    result = run_turn("Are you sure?", [])
    assert result["type"] == "answer"
    assert "inventory data" in result["answer"].lower()


def test_unrelated_question_uses_short_fallback_without_llm():
    from db.seed import main as seed_db

    seed_db()
    from pipeline.graph import run_turn

    result = run_turn("What is the weather today?", [])
    assert result["type"] == "answer"
    assert "furniture inventory" in result["answer"].lower()


if __name__ == "__main__":
    test_template_total_quantity()
    test_template_category_breakdown_includes_current_seed_data()
    test_ambiguous_question_clarifies_without_llm()
    test_price_question_returns_unit_price_not_quantity()
    test_location_followup_uses_previous_catalog_item()
    test_price_followup_one_uses_previous_catalog_item()
    test_fallback_question_can_answer_from_conversation_history()
    test_confirmation_question_uses_short_fallback()
    test_unrelated_question_uses_short_fallback_without_llm()
    print("All template tests passed.")
