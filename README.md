# GymPulse

GymPulse is a WhatsApp-first gym tracking app:
- WhatsApp bot for natural language workout logging
- FastAPI backend on Render free tier
- Open-source parser path via Ollama (`qwen2.5:1.5b`)
- Supabase PostgreSQL (free tier)
- React + Vite dashboard on Vercel (dark, animated, pro-gated)
- Razorpay subscriptions (`₹99/month`)
- Admin panel at `/admin` with password-gated analytics and broadcast tools

## Project Structure

```text
gymflow/
├── backend/
│   ├── main.py
│   ├── schema.sql
│   ├── requirements.txt
│   ├── .env.example
│   ├── routers/
│   │   ├── webhook.py
│   │   ├── api.py
│   │   ├── payments.py
│   │   └── admin.py
│   └── services/
│       ├── parser.py
│       ├── db.py
│       ├── whatsapp.py
│       ├── payments.py
│       └── image_gen.py
├── frontend/
│   ├── .env.example
│   ├── package.json
│   ├── tailwind.config.js
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       ├── index.css
│       ├── pages/
│       │   ├── Dashboard.jsx
│       │   └── Admin.jsx
│       └── components/
│           ├── OverviewCards.jsx
│           ├── ProgressChart.jsx
│           ├── VolumeChart.jsx
│           ├── RadarChart.jsx
│           ├── HeatmapCalendar.jsx
│           ├── MedalsGrid.jsx
│           ├── SessionsFeed.jsx
│           └── StoryCard.jsx
└── README.md
```

## 1. Prerequisites

Install:
- Python 3.11+
- Node.js 20+
- Git
- A Supabase account (free)
- A Razorpay account (for subscriptions)
- A Meta Developer account + WhatsApp Cloud API access
- Ollama (for free open-source parsing)

## 2. Supabase Setup

1. Create a new project in Supabase.
2. Open `SQL Editor`.
3. Run `backend/schema.sql`.
4. Go to `Project Settings -> API` and copy:
   - Project URL
   - `service_role` key (legacy key section)

## 3. Open-Source LLM Parser Setup (Ollama)

1. Install Ollama: https://ollama.com/download
2. Pull a lightweight model:
   - `ollama pull qwen2.5:1.5b`
3. Start Ollama (default API: `http://127.0.0.1:11434`)

The backend uses this model for parsing workout text. If Ollama is unavailable, a regex fallback is used.

## 4. Razorpay Setup (Pro Paywall)

1. Create a monthly plan in Razorpay dashboard for `₹99`.
2. Copy your:
   - `Key ID`
   - `Key Secret`
   - `Plan ID`
3. Configure a webhook endpoint:
   - URL: `https://<your-backend-domain>/payments/webhook`
   - Events:
     - `subscription.activated`
     - `subscription.cancelled`
     - `payment.failed`
4. Copy webhook secret.

## 5. Meta WhatsApp Cloud API Setup

1. Go to Meta Developers and create an app.
2. Add **WhatsApp** product.
3. Copy:
   - Temporary/permanent access token
   - Phone Number ID
4. Add webhook callback URL:
   - `https://<your-backend-domain>/webhook`
5. Set verify token (any string you choose, must match backend env).
6. Subscribe to message webhooks.
7. Add your phone as a test recipient in WhatsApp Cloud API.

## 6. Backend Local Setup (CMD / PowerShell)

```bat
cd /d D:\gym-project\gymflow\backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Set `backend/.env`:

```env
WHATSAPP_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_VERIFY_TOKEN=
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_KEY=YOUR_SUPABASE_SERVICE_ROLE_KEY
FRONTEND_URL=http://localhost:5173

OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:1.5b

RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
RAZORPAY_WEBHOOK_SECRET=
RAZORPAY_PLAN_ID=

ADMIN_PASSWORD=
```

Run backend:

```bat
python -m uvicorn main:app --reload --port 8000
```

Health check:
- `http://127.0.0.1:8000/`

## 7. Frontend Local Setup

```bat
cd /d D:\gym-project\gymflow\frontend
copy .env.example .env
npm install
npm run dev
```

Set `frontend/.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Open:
- User dashboard: `http://localhost:5173/dashboard/demo`
- Admin panel: `http://localhost:5173/admin`

## 8. Admin Panel Auth

Admin routes require:
- Header: `Authorization: Bearer <ADMIN_PASSWORD>`

Frontend admin login keeps password in memory only (not localStorage), per requirement.

## 9. Deploy Backend to Render (Free Tier)

1. Push repo to GitHub.
2. Create new Web Service on Render pointing to `gymflow/backend`.
3. Build command:
   - `pip install -r requirements.txt`
4. Start command:
   - `uvicorn main:app --host 0.0.0.0 --port 10000`
5. Add all backend env vars in Render dashboard.
6. Update `FRONTEND_URL` to your Vercel URL after frontend deploy.

## 10. Deploy Frontend to Vercel (Free Tier)

1. Import repo in Vercel.
2. Set project root to `gymflow/frontend`.
3. Set env var:
   - `VITE_API_BASE_URL=https://<your-render-url>`
4. Deploy.

## 11. End-to-End Testing Checklist

1. Backend health:
   - `curl http://127.0.0.1:8000/`
2. Dashboard token check:
   - `curl http://127.0.0.1:8000/api/dashboard/demo`
3. WhatsApp webhook verify:
   - configure Meta webhook and confirm verification succeeds.
4. Send WhatsApp message:
   - `bench 80kg 4x8, incline db 22.5kg 3x10`
5. Test command flows:
   - `stats`
   - `medals`
   - `dashboard` (free -> pay link)
   - `story` (free -> pay link)
6. Complete Razorpay payment:
   - confirm `subscription.activated` webhook triggers
   - bot sends Pro confirmation message
7. Open dashboard token URL:
   - free user sees paywall
   - pro user sees full analytics and charts
8. Admin panel:
   - `/admin` login with `ADMIN_PASSWORD`
   - verify overview/users/revenue/live feed/broadcast functions

## 12. Main API Routes

User + bot:
- `GET /webhook`
- `POST /webhook`
- `GET /api/dashboard/{token}`
- `GET /api/exercises/{token}`
- `GET /api/medals/{token}`
- `GET /api/story/{token}`
- `POST /payments/webhook`

Admin:
- `GET /api/admin/overview`
- `GET /api/admin/users`
- `GET /api/admin/users/{user_id}`
- `GET /api/admin/revenue`
- `GET /api/admin/live-sessions`
- `POST /api/admin/message`
- `POST /api/admin/broadcast`

## Notes

- Dashboard is fully Pro-gated.
- Workout logs are always saved, even for free users.
- If Razorpay or WhatsApp env vars are missing, related features return graceful errors.
