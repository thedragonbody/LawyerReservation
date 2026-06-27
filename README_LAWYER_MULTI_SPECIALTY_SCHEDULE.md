# Lawyer dashboard multi-specialty + day schedule patch

Changes included:
- `/dashboard/lawyer` now has a landing-style top header that hides on scroll.
- Lawyer can select multiple practice areas/specialties.
- Lawyer can upload/change profile image.
- Clicking a calendar day opens a bottom sheet.
- The bottom sheet shows bookings for the selected date.
- The lawyer can mark that day closed/open.
- The lawyer can add one or more working-hour ranges for that day.
- `footer.lawyer-logout-footer` width is smaller.

Backend changes:
- `Availability` supports exact `date` and `is_closed`.
- New endpoint: `GET/POST /api/lawyers/me/availability/day/`
- Lawyer profile update accepts repeated `areas` values and `avatar` file.

After replacing files run:

```powershell
cd "C:\Users\MB-KING\Desktop\vakil app\lexara\backend"
python manage.py makemigrations lawyers
python manage.py migrate
python manage.py runserver 8000
```

Frontend:

```powershell
cd "C:\Users\MB-KING\Desktop\vakil app\lexara\frontend"
npm run dev
```
