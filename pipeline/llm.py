import os

from openai import OpenAI

MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_API_KEY"],
        )
    return _client


def chat(system: str, messages: list[dict]) -> str:
    client = _get_client()
    full_messages = [{"role": "system", "content": system}] + messages
    response = client.chat.completions.create(model=MODEL, messages=full_messages)
    return response.choices[0].message.content
