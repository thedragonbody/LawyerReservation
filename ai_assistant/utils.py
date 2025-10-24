import json
import logging
from typing import Optional

from django.conf import settings
from openai import OpenAI

# Logging کامل
logger = logging.getLogger("ai_assistant")
logger.setLevel(logging.INFO)
handler = logging.FileHandler("ai_assistant.log")
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

_client: Optional[OpenAI] = None


def _get_openai_client() -> OpenAI:
    """Lazily create an OpenAI client when the API key is configured."""

    api_key = settings.OPENAI_API_KEY
    if not api_key:
        raise RuntimeError("OpenAI API key is not configured. Set OPENAI_API_KEY to enable AI features.")
    global _client
    if _client is None:
        _client = OpenAI(api_key=api_key)
    return _client

PERSONA_INSTRUCTIONS = {
    "judge": "You are a strict judge providing formal, precise legal responses.",
    "lawyer": "You are a professional lawyer giving detailed legal advice to clients.",
    "assistant": "You are a friendly assistant explaining legal topics simply for everyone."
}

def ask_ai_with_retry(user, question, user_role=None, persona=None, history=None, max_retries=3):
    """
    پرسش AI با:
    - Multi-turn و Persona
    - Memory weighted
    - Retry هوشمند در صورت خطای OpenAI
    """
    for attempt in range(max_retries):
        try:
            return ask_ai(user, question, user_role=user_role, persona=persona, history=history)
        except Exception as e:
            logger.warning(f"Attempt {attempt+1}/{max_retries} failed: {e}")
            if attempt == max_retries - 1:
                logger.error(f"AI service finally failed: {e}")
                return f"AI service error after {max_retries} attempts: {e}"

def ask_ai(user, question, user_role=None, persona=None, history=None):
    """
    Memory پیشرفته با weighted importance
    """
    try:
        if isinstance(question, bytes):
            question = question.decode("utf-8", errors="ignore")
        else:
            question = str(question).encode("utf-8", errors="ignore").decode("utf-8")

        if persona not in PERSONA_INSTRUCTIONS:
            persona = "assistant"
        persona_instruction = PERSONA_INSTRUCTIONS[persona]

        role_instruction = {
            "lawyer": "You are an expert legal assistant helping lawyers respond to clients professionally.",
            "client": "You are a helpful assistant explaining legal topics simply to clients.",
        }.get(user_role, "")

        full_instruction = f"{role_instruction} {persona_instruction}".strip()

        # Weighted history: مرتب‌سازی بر اساس importance و زمان
        messages = [{"role": "system", "content": full_instruction}]
        if history:
            sorted_history = sorted(history, key=lambda h: (-h.get("importance", 1), h.get("created_at")))
            for h in sorted_history:
                messages.append({"role": "user", "content": h.get("question", "")})
                messages.append({"role": "assistant", "content": h.get("answer", "")})

        messages.append({"role": "user", "content": question})

        logger.info(f"Sending question to AI | UserRole: {user_role} | Persona: {persona} | Question: {question}")
        client = _get_openai_client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )
        answer = response.choices[0].message.content
        logger.info(f"Received AI answer: {answer}")
        return str(answer).encode("utf-8", errors="ignore").decode("utf-8")

    except Exception as e:
        logger.error(f"AI service error: {e}")
        raise e  # raise برای اینکه retry عمل کنه

def format_ai_output(answer):
    try:
        data = json.loads(answer)
        if isinstance(data, list):
            return "\n".join([f"- {item}" for item in data])
        elif isinstance(data, dict):
            return "\n".join([f"{k}: {v}" for k, v in data.items()])
    except Exception:
        return answer
