from openai import OpenAI
from django.conf import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

PERSONA_INSTRUCTIONS = {
    "judge": "You are a strict judge providing formal, precise legal responses.",
    "lawyer": "You are a professional lawyer giving detailed legal advice to clients.",
    "assistant": "You are a friendly assistant explaining legal topics simply for everyone."
}

def ask_ai(question, user_role=None, persona=None, history=None):
    """
    پرسش AI با پشتیبانی از نقش کاربر و Persona
    Persona پیش‌فرض: دستیار (assistant)
    history: لیست آخرین سوالات و پاسخ‌ها برای context
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

        # آماده‌سازی پیام‌ها برای AI
        messages = [{"role": "system", "content": full_instruction}]
        if history:
            for h in history:
                messages.append({"role": "user", "content": h["question"]})
                messages.append({"role": "assistant", "content": h["answer"]})
        messages.append({"role": "user", "content": question})

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )

        answer = response.choices[0].message.content
        return str(answer).encode("utf-8", errors="ignore").decode("utf-8")

    except Exception as e:
        return f"AI service error: {e}"