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


if __name__ == "__main__":
    test_template_total_quantity()
    test_template_category_breakdown_includes_current_seed_data()
    test_ambiguous_question_clarifies_without_llm()
    print("All template tests passed.")
