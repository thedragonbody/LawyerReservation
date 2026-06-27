# Lexara — Legal Counsel Booking Platform

A full-stack web application connecting clients with verified lawyers.  
**Django REST API** backend + **Next.js 14** frontend.

---

## ✨ Features

### For Clients (Customers)
- Browse and search verified lawyers by practice area, rating, rate, experience
- View full lawyer profiles: bio, education, availability, reviews
- **Book consultations** — select date, choose available time slot
- **Upload case documents** (PDF, JPG, PNG, DOC) during booking
- Track bookings: pending / confirmed / completed / cancelled
- Manage all documents in one place
- Private customer dashboard

### For Lawyers
- Private lawyer dashboard with booking management
- Confirm, reject, or mark bookings as completed
- Add meeting links (Zoom, Google Meet) to confirmed bookings
- Set weekly availability with custom time slots
- Manage practice areas, education, bio, rates
- Toggle "accepting clients" status instantly

### Authentication
- **OTP-based, no email required** — phone number only
- 6-digit OTP with 10-minute expiry & 5-attempt limit
- JWT access tokens (24h) + refresh tokens (30 days)
- Auto-refresh on 401

---

## 🚀 Quick Start

### Backend (Django)
```bash
cd lexara/backend

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env            # fill in your settings

python manage.py migrate
python manage.py createsuperuser

python manage.py runserver      # runs at http://localhost:8000
```

### Frontend (Next.js)
```bash
cd lexara/frontend

npm install

cp .env.local.example .env.local

npm run dev                     # runs at http://localhost:3000
```

---

## 📁 Project Structure

```
lexara/
├── backend/                        Django REST API
│   ├── core/
│   │   ├── settings.py             All configuration
│   │   └── urls.py                 Root URL routing
│   ├── apps/
│   │   ├── accounts/               Custom phone-based User model + JWT auth
│   │   ├── otp/                    OTP generation, verification, expiry
│   │   ├── lawyers/                Lawyer profiles, practice areas, availability, reviews
│   │   ├── bookings/               Booking creation, status management, file uploads
│   │   └── customers/              Customer dashboard stats
│   ├── requirements.txt
│   └── manage.py
│
└── frontend/                       Next.js 14 App Router
    └── src/
        ├── app/
        │   ├── page.tsx            Landing page (hero, search, featured lawyers)
        │   ├── (auth)/
        │   │   ├── login/          Phone + OTP login
        │   │   └── register/       Role selection + registration + OTP verify
        │   ├── lawyers/
        │   │   ├── page.tsx        Lawyer directory with filters
        │   │   └── [id]/page.tsx   Full lawyer profile + booking modal
        │   └── dashboard/
        │       ├── customer/       Client dashboard (bookings, documents)
        │       └── lawyer/         Lawyer dashboard (requests, profile, availability)
        ├── lib/
        │   ├── api.ts              Axios client + all API helpers
        │   └── store.ts            Zustand auth state
        └── app/globals.css         Design system (navy + gold luxury theme)
```

---

## 🔌 API Reference

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register/` | Register new user → sends OTP |
| POST | `/api/auth/request-otp/` | Send OTP to existing user |
| POST | `/api/auth/verify-otp/` | Verify OTP → returns JWT tokens |
| POST | `/api/otp/resend/` | Resend OTP |
| GET | `/api/auth/me/` | Get current user |
| PATCH | `/api/auth/me/update/` | Update profile |
| POST | `/api/auth/logout/` | Blacklist refresh token |

### Lawyers
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/lawyers/` | List lawyers (with filters) |
| GET | `/api/lawyers/{id}/` | Lawyer detail |
| GET/PUT | `/api/lawyers/me/profile/` | Lawyer manages own profile |
| GET | `/api/lawyers/me/dashboard/` | Lawyer dashboard stats |
| POST | `/api/lawyers/{id}/reviews/` | Customer adds review |

### Bookings
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/bookings/` | Customer list + create bookings |
| GET | `/api/bookings/lawyer/` | Lawyer views their bookings |
| GET/PATCH | `/api/bookings/{id}/` | Booking detail + update |
| GET/POST | `/api/bookings/{id}/documents/` | List + upload documents |
| DELETE | `/api/bookings/{id}/documents/{doc_id}/` | Delete document |
| GET | `/api/bookings/slots/{lawyer_id}/?date=YYYY-MM-DD` | Available time slots |

### Filters (GET /api/lawyers/)
| Param | Description |
|-------|-------------|
| `search` | Name, bio keyword |
| `area` | Practice area key (e.g. `corporate`) |
| `min_rate` / `max_rate` | Hourly rate range |
| `min_experience` | Minimum years |
| `min_rating` | Minimum star rating |
| `accepting` | `true` / `false` |
| `ordering` | `-average_rating`, `hourly_rate`, etc. |

---

## 📱 OTP Integration (SMS)

The platform uses **phone-number OTP** with no email required.  
In development, the OTP is returned in the API response (`_dev_otp` field).

For production, integrate an SMS gateway:

```python
# backend/core/settings.py
# Twilio:
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN  = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_FROM  = os.environ.get('TWILIO_PHONE_FROM')
```

Then in `apps/accounts/views.py`, replace the comment with:
```python
from twilio.rest import Client
client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
client.messages.create(body=f"Your Lexara code: {otp_code}", from_=settings.TWILIO_PHONE_FROM, to=phone)
```

Other options: **Vonage**, **AWS SNS**, **Plivo**, **MSG91**

---

## 🚢 Production Checklist

- [ ] Set strong `DJANGO_SECRET_KEY` in `.env`
- [ ] Set `DEBUG=False`
- [ ] Switch to **PostgreSQL**
- [ ] Configure **S3 / Cloudflare R2** for file storage (`django-storages`)
- [ ] Integrate real **SMS gateway** for OTP
- [ ] Add **Redis** for caching
- [ ] Deploy backend with **Gunicorn + Nginx**
- [ ] Deploy frontend to **Vercel** (or similar)
- [ ] Set CORS allowed origins to production domains

---

## ⚠️ Legal Notice

Lexara is a connection platform. It is not a law firm and does not provide legal advice. Consult with a licensed attorney for legal guidance.
