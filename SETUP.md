# Toyota Payroll — Local Setup Guide

Run the **Admin Dashboard** + **Django API** on your machine. One-click start: double-click **`start-toyota.bat`** (after first-time setup).

---

## 1. Prerequisites

Install these once:

| Tool | Download |
|------|----------|
| **Python 3.12+** | https://www.python.org/downloads/ (check “Add to PATH”) |
| **Node.js 20+** | https://nodejs.org/ |
| **Git** (optional) | https://git-scm.com/ |

Verify in PowerShell:

```powershell
python --version
node --version
npm --version
```

---

## 2. First-time setup (one time)

Double-click **`setup-first-time.bat`** or run:

```powershell
cd C:\path\to\toyota-
.\setup-first-time.bat
```

This creates the Python virtualenv, installs packages, runs database migrations, and installs npm dependencies.

---

## 3. Environment file (`.env` at repo root)

Copy the template and fill in your values:

```powershell
copy .env.example .env
```

Edit **`toyota-\.env`** (same folder as this README):

```env
# ─── Supabase (database + file storage) ───
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_JWT_SECRET=your-jwt-secret
SUPABASE_SALARY_BUCKET=salary-slips

# ─── Gmail SMTP (salary slip emails) ───
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
SMTP_FROM=Toyota Payroll <your-email@gmail.com>
```

### 3.1 Get Supabase keys

1. Go to https://supabase.com → **New project**
2. Open **Project Settings** → **API**
3. Copy:
   - **Project URL** → `SUPABASE_URL`
   - **anon public** → `SUPABASE_ANON_KEY` (also used in Next.js)
   - **service_role** → `SUPABASE_SERVICE_ROLE_KEY` (keep secret, server only)
4. **JWT Secret** → Project Settings → **API** → JWT Settings → `SUPABASE_JWT_SECRET`
5. Run SQL: open **SQL Editor**, paste and run the script from **`server/supabase/schema.sql`**
6. Confirm bucket **Storage** → `salary-slips` exists (created by SQL)

### 3.2 Gmail App Password (SMTP)

Gmail does **not** allow your normal password for apps.

1. Use a Google account with **2-Step Verification** enabled:  
   https://myaccount.google.com/security
2. Open **App passwords**: https://myaccount.google.com/apppasswords  
   (Google Account → Security → 2-Step Verification → App passwords)
3. Create app: name it `Toyota Payroll`, device **Windows**
4. Google shows a **16-character password** (e.g. `abcd efgh ijkl mnop`)
5. Put it in `.env` as `SMTP_PASSWORD` (spaces optional)

```env
SMTP_USER=you@gmail.com
SMTP_PASSWORD=abcdefghijklmnop
SMTP_FROM=Toyota Payroll <you@gmail.com>
```

### 3.3 Admin dashboard env (optional)

Create **`admin-dash/.env.local`**:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Supabase keys are **not** needed in the browser; only Django uses them.

---

## 4. Run the app (every day)

Double-click **`start-toyota.bat`**.

| Service | URL |
|---------|-----|
| Admin dashboard | http://localhost:3000 |
| Django API | http://localhost:8000 |
| Login | http://localhost:3000/login |

Two terminal windows open (API + dashboard). Your browser opens the dashboard.

**Stop:** close both terminal windows or press `Ctrl+C` in each.

---

## 5. Manual commands (if you prefer)

**Terminal 1 — Django**

```powershell
cd server
.\.venv\Scripts\activate
python manage.py runserver 8000
```

**Terminal 2 — Admin dashboard**

```powershell
cd admin-dash
npm run dev
```

---

## 6. Using the payroll flow

1. Sign up / sign in at http://localhost:3000/login  
2. Open **Upload Portal** tab  
3. Upload Excel/CSV (`admin-dash/public/payroll-template.csv` is a sample)  
4. Columns: `Employee ID`, `Name`, `Email`, `Designation`, `Base Salary`, `HRA`, `Allowances`, `Deductions`, `Month/Year` (e.g. `5/2026`)  
5. Click **Generate PDFs & Send All Emails**  
   - Imports data  
   - Creates PDF slips (Toyota branding)  
   - Uploads to Supabase Storage  
   - Emails each employee with PDF attached  

---

## 7. Logo image

Place your Toyota logo at:

- `admin-dash/public/toyota-logo.png`

Copy the same file to `server/payroll/assets/toyota-logo.png` for PDFs (or restart after updating `public` only).

---

## 8. Troubleshooting

| Problem | Fix |
|---------|-----|
| Login 401 | Create user via Sign up; check Supabase Auth is enabled |
| SMTP / email fails | Verify App Password in root `.env`; restart Django |
| `SMTP not configured` | Fill all `SMTP_*` in **root** `.env`, not `server/.env` |
| Supabase upload error | Run `server/supabase/schema.sql` in SQL Editor |
| Port in use | Stop other apps on 3000 / 8000 or change ports |
| `python` not found | Reinstall Python with “Add to PATH” |

---

## 9. Project structure

```
toyota-/
  .env                 ← all secrets (Supabase + SMTP)
  start-toyota.bat     ← run app
  setup-first-time.bat ← first-time install
  server/              ← Django API
  admin-dash/          ← Next.js UI
```
