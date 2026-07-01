import os
import sys

from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

console = Console()


def main():
    if not os.environ.get("OPENROUTER_API_KEY"):
        console.print(
            "[bold red]Error:[/bold red] OPENROUTER_API_KEY is not set. "
            "Copy .env.example to .env and add your key."
        )
        sys.exit(1)

    from pipeline.graph import run_turn

    console.print(
        "[bold cyan]Furniture inventory assistant[/bold cyan] — "
        "ask a question, or type 'exit' to quit."
    )

    conversation = []

    while True:
        try:
            question = console.input("[bold green]you>[/bold green] ")
        except (EOFError, KeyboardInterrupt):
            console.print()
            break

        if not question.strip():
            continue
        if question.strip().lower() in ("exit", "quit"):
            break

        with console.status("[dim]thinking…[/dim]", spinner="dots"):
            try:
                result = run_turn(question, conversation)
            except Exception as e:
                result = None
                console.print(f"[bold red]bot>[/bold red] Sorry, something went wrong: {e}")

        if result is None:
            continue

        if result["type"] == "clarify":
            console.print(f"[bold magenta]bot>[/bold magenta] {result['question']}")
            conversation.append({"role": "user", "content": question})
            conversation.append({"role": "assistant", "content": result["question"]})
        else:
            console.print(f"[bold magenta]bot>[/bold magenta] {result['answer']}")
            conversation.append({"role": "user", "content": question})
            conversation.append({"role": "assistant", "content": result["answer"]})


if __name__ == "__main__":
    main()
