import json
import logging
import time
import traceback
from openai import OpenAI
from django.conf import settings
from .models import AIErrorLog

logger = logging.getLogger("ai_assistant")
handler = logging.FileHandler("ai_assistant.log")
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

client = OpenAI(api_key=settings.OPENAI_API_KEY)

PERSONA_INSTRUCTIONS = {
    "judge": "You are a strict judge providing formal, precise legal responses.",
    "lawyer": "You are a professional lawyer giving detailed legal advice to clients.",
    "assistant": "You are a friendly assistant explaining legal topics simply for everyone."
}


def ask_ai_raw(question, user_role=None, persona=None, history=None):
    """
    نسخه پایه‌ای که یک درخواست مستقیم به API می‌فرستد.
    """
    question = str(question).encode("utf-8", errors="ignore").decode("utf-8")

    if persona not in PERSONA_INSTRUCTIONS:
        persona = "assistant"
    persona_instruction = PERSONA_INSTRUCTIONS[persona]

    role_instruction = {
        "lawyer": "You are an expert legal assistant helping lawyers respond professionally.",
        "client": "You are a helpful assistant explaining legal concepts simply to clients.",
    }.get(user_role, "")

    system_message = f"{role_instruction} {persona_instruction}".strip()
    messages = [{"role": "system", "content": system_message}]

    if history:
        sorted_history = sorted(history, key=lambda h: (-h.get("importance", 0), h.get("created_at")))
        for h in sorted_history:
            messages.append({"role": "user", "content": h.get("question", "")})
            messages.append({"role": "assistant", "content": h.get("answer", "")})

    messages.append({"role": "user", "content": question})

    response = client.chat.completions.create(
        model=getattr(settings, "AI_MODEL_NAME", "gpt-4o-mini"),
        messages=messages,
    )
    return response.choices[0].message.content


def ask_ai_with_retry(user, question, user_role=None, persona=None, history=None):
    """
    اجرای هوشمند: چند تلاش با افزایش backoff و ثبت خطاها.
    """
    max_retries = getattr(settings, "AI_MAX_RETRIES", 3)
    base_backoff = getattr(settings, "AI_RETRY_BACKOFF_SECONDS", 1)
    last_error = None

    for attempt in range(max_retries):
        try:
            answer = ask_ai_raw(question, user_role, persona, history)
            logger.info(f"AI answered successfully on attempt {attempt + 1}")
            return answer
        except Exception as e:
            last_error = e
            wait = base_backoff * (2 ** attempt)
            logger.warning(f"[AI Retry] attempt {attempt + 1} failed: {e} — waiting {wait}s")
            time.sleep(wait)

    # ثبت خطا در دیتابیس
    trace_str = traceback.format_exc()
    AIErrorLog.objects.create(
        user=user,
        question=question,
        error=str(last_error),
        traceback=trace_str
    )
    logger.error(f"AI failed after {max_retries} attempts: {last_error}")

    # پاسخ خطایی که در AIQuestion هم ذخیره می‌شود
    return f"[AI Error] Unable to process your question at the moment.\n\nDetails: {str(last_error)}"


def format_ai_output(answer):
    """
    اگر پاسخ JSON باشد، زیبا و خوانا تبدیلش می‌کنیم.
    """
    try:
        data = json.loads(answer)
        if isinstance(data, list):
            return "\n".join([f"- {item}" for item in data])
        elif isinstance(data, dict):
            formatted = ""
            for key, value in data.items():
                formatted += f"{key}: {value}\n"
            return formatted.strip()
    except Exception:
        return answer