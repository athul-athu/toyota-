# Toyota Payroll Admin

Admin dashboard for payroll upload, salary slip PDF generation, Supabase storage, and automated employee emails.

---

## Prerequisites (install once on your PC)

Python 3.12+ | https://www.python.org/downloads/ (tick **Add to PATH**) |
Node.js 20+ | https://nodejs.org/ |

---

## First time setup (do this only once)

Follow these steps **the first time** you set up the project (or when someone new clones the folder).

### Step 1 — Run the setup batch file

Double-click this file in the project folder:

```
setup-first-time.bat
```

It will:
- Create Python virtual environment in `server/`
- Install Python packages (`requirements.txt`)
- Run database migrations
- Install npm packages for `admin-dash/`
- Create `.env` from `.env.example` (if missing)
- Create `admin-dash/.env.local` (if missing)

Wait until it says **Setup complete!**

### Step 2 — Configure `.env`

Open the file **`toyota-\.env`** (in the **same folder** as the `.bat` files, **not** inside `server/`).

Fill in:

```env
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-gmail-app-password
SMTP_FROM=Toyota Payroll <your-email@gmail.com>
```

**Where to get values:**
- **Supabase keys** → [SETUP.md](SETUP.md) section *3.1 Get Supabase keys*
- **Gmail App Password** → [SETUP.md](SETUP.md) section *3.2 Gmail App Password*

### Step 3 — Supabase database

1. Open https://supabase.com → your project → **SQL Editor**
2. Open the file **`server/supabase/schema.sql`** in this project
3. Copy all SQL → paste in Supabase → click **Run**

### Step 4 — First run

Double-click:

```
start-toyota.bat
```

Browser opens → http://localhost:3000/login → **Sign up** → use the app.

---

## Next time (every day after that)

You only need **one** batch file:

```
start-toyota.bat
```

Double-click **`start-toyota.bat`** → wait for two terminal windows → browser opens to login.

| What it starts | URL |
|----------------|-----|
| Django API | http://localhost:8000 |
| Admin dashboard | http://localhost:3000 |

**To stop:** close both terminal windows (or press `Ctrl+C` in each).

You do **not** need to run `setup-first-time.bat` again unless you delete `server/.venv` or reinstall the project.

---

## Batch files summary

| File | When to use |
|------|-------------|
| **`setup-first-time.bat`** | **Once** — first install only |
| **`start-toyota.bat`** | **Every time** you want to run the app |

---

## Using the app (after login)

1. Go to **Upload Portal** tab  
2. Upload Excel/CSV (sample: `admin-dash/public/payroll-template.csv`)  
3. Click **Generate PDFs & Send All Emails**  
4. PDFs are created, saved to Supabase, and emailed to each employee  

---

## More help

- Full setup (keys, app password, troubleshooting): **[SETUP.md](SETUP.md)**
- Supabase SQL migration (month/year): **`server/supabase/migration_month_year_period.sql`**
