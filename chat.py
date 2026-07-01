import os
import sys

from dotenv import load_dotenv

load_dotenv()


def main():
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("Error: OPENROUTER_API_KEY is not set. Copy .env.example to .env and add your key.")
        sys.exit(1)

    from pipeline.graph import run_turn

    print("Furniture inventory assistant — ask a question, or type 'exit' to quit.")

    conversation = []

    while True:
        try:
            question = input("you> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not question.strip():
            continue
        if question.strip().lower() in ("exit", "quit"):
            break

        try:
            result = run_turn(question, conversation)
        except Exception as e:
            print(f"bot> Sorry, something went wrong: {e}")
            continue

        if result["type"] == "clarify":
            print(f"bot> {result['question']}")
            conversation.append({"role": "user", "content": question})
            conversation.append({"role": "assistant", "content": result["question"]})
        else:
            print(f"bot> {result['answer']}")
            conversation.append({"role": "user", "content": question})
            conversation.append({"role": "assistant", "content": result["answer"]})


if __name__ == "__main__":
    main()
