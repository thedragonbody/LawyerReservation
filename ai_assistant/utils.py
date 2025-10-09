import json
import logging
from openai import OpenAI
from django.conf import settings

# تنظیم logging برای ثبت خطاها و فعالیت‌ها
logger = logging.getLogger("ai_assistant")
logger.setLevel(logging.INFO)
handler = logging.FileHandler("ai_assistant.log")
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

client = OpenAI(api_key=settings.OPENAI_API_KEY)

PERSONA_INSTRUCTIONS = {
    "judge": "You are a strict judge providing formal, precise legal responses.",
    "lawyer": "You are a professional lawyer giving detailed legal advice to clients.",
    "assistant": "You are a friendly assistant explaining legal topics simply for everyone."
}

def ask_ai(question, user_role=None, persona=None, history=None):
    """
    پرسش AI با پشتیبانی از:
    - Persona
    - نقش کاربر
    - Multi-turn (با history)
    - Memory پیشرفته با قابلیت weight (در آینده قابل گسترش)
    """
    try:
        # اطمینان از UTF-8 بودن ورودی
        if isinstance(question, bytes):
            question = question.decode("utf-8", errors="ignore")
        else:
            question = str(question).encode("utf-8", errors="ignore").decode("utf-8")

        # تعیین Persona پیش‌فرض
        if persona not in PERSONA_INSTRUCTIONS:
            persona = "assistant"
        persona_instruction = PERSONA_INSTRUCTIONS[persona]

        # دستورالعمل اضافی بر اساس نقش کاربر
        role_instruction = {
            "lawyer": "You are an expert legal assistant helping lawyers respond to clients professionally.",
            "client": "You are a helpful assistant explaining legal topics simply to clients.",
        }.get(user_role, "")

        full_instruction = f"{role_instruction} {persona_instruction}".strip()

        # ساخت history برای Multi-turn
        messages = [{"role": "system", "content": full_instruction}]
        if history:
            # می‌توان weight یا اهمیت را اضافه کرد
            for h in history:
                messages.append({"role": "user", "content": h.get("question", "")})
                messages.append({"role": "assistant", "content": h.get("answer", "")})

        messages.append({"role": "user", "content": question})

        logger.info(f"Sending question to AI: {question}")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )

        answer = response.choices[0].message.content
        logger.info(f"Received answer: {answer}")
        return str(answer).encode("utf-8", errors="ignore").decode("utf-8")

    except Exception as e:
        logger.error(f"AI service error: {e}")
        return f"AI service error: {e}"


def format_ai_output(answer):
    """
    تبدیل پاسخ AI به متن قابل خواندن:
    - اگر JSON باشد، به جدول یا لیست ساده تبدیل می‌کند
    - اگر ساده باشد، همان متن را برمی‌گرداند
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
        # اگر JSON نبود، همان متن را بازگردان
        return answer