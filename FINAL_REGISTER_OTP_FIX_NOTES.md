# Lexara Final Register + OTP Fix

این نسخه شامل آخرین تغییرات UI قبلی + اصلاح ثبت‌نام است.

## بک‌اند
در `backend/apps/accounts/views.py` داخل تابع `register`:
- OTP بعد از ساخته‌شدن در ترمینال بک‌اند چاپ می‌شود:
  `LEXARA DEV OTP for <phone>: <code>`
- مقدار `_dev_otp` هم در Response ثبت‌نام برگشت داده می‌شود، تا تا زمان اتصال SMS، فرانت بتواند کد را نمایش دهد.
- شرط شماره تکراری دست‌نخورده و امن باقی مانده است.

## فرانت
در `frontend/src/app/(auth)/register/page.tsx`:
- Response ثبت‌نام در Console چاپ می‌شود.
- فرانت این نام‌ها را برای OTP پشتیبانی می‌کند:
  `_dev_otp`, `dev_otp`, `otp`, `code`
- خطای واقعی بک‌اند روی صفحه نمایش داده می‌شود.

## اجرا
ترمینال ۱:
`cd backend`
`python manage.py runserver 8000`

ترمینال ۲:
`cd frontend`
`npm run dev`

قبل از تست ثبت‌نام:
`python manage.py makemigrations`
`python manage.py migrate`
