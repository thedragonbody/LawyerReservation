from openai import OpenAI
from django.conf import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def ask_ai(question, user_role=None):
    try:
        # اطمینان از اینکه ورودی همیشه UTF-8 است
        if isinstance(question, bytes):
            question = question.decode("utf-8", errors="ignore")
        else:
            question = str(question).encode("utf-8", errors="ignore").decode("utf-8")

        role_instruction = {
            "lawyer": "You are an expert legal assistant helping lawyers respond to clients professionally.",
            "client": "You are a helpful assistant explaining legal topics simply to clients.",
        }.get(user_role, "You are a helpful AI assistant for general and legal questions.")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": role_instruction},
                {"role": "user", "content": question},
            ],
        )

        answer = response.choices[0].message.content

        # همیشه خروجی را هم utf-8 برگردان
        return str(answer).encode("utf-8", errors="ignore").decode("utf-8")

    except Exception as e:
        return f"AI service error: {e}"