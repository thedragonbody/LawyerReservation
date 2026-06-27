# Lexara lawyers license/specialty/search/reviews patch

فایل‌های مهم تغییر کرده:
- backend/apps/lawyers/models.py
- backend/apps/lawyers/serializers.py
- backend/apps/lawyers/views.py
- frontend/src/lib/api.ts
- frontend/src/app/dashboard/lawyer/page.tsx
- frontend/src/app/lawyers/page.tsx
- frontend/src/app/lawyers/[id]/page.tsx
- frontend/src/app/globals.css

بعد از جایگزینی فایل‌ها حتماً اجرا کن:

cd backend
python manage.py makemigrations lawyers
python manage.py migrate
python manage.py runserver 8000

cd frontend
npm run dev
