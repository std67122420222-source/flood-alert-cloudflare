# FloodAlert — Cloudflare Python Workers + Hyperdrive + Supabase

ชุดนี้นำ FloodAlert Flask ตัวปัจจุบันไปรันบน **Cloudflare Python Workers** โดยใช้ **Cloudflare Hyperdrive** เป็นทางเชื่อมไปยัง PostgreSQL (Supabase) และใช้ Cron Triggers แทน APScheduler สำหรับงาน refresh เบื้องหลัง

Cloudflare รองรับ Flask ผ่าน WSGI ใน Python Workers และมี `wsgi.entrypoint/fetch` สำหรับเชื่อม Flask เข้ากับ Worker runtime. Hyperdrive รองรับ PostgreSQL จาก Python Workers และเอกสาร Cloudflare ระบุว่ารองรับ synchronous SQLAlchemy สำหรับงานลักษณะนี้.

## โครงสร้าง

```text
flood-alert-cloudflare/
├── src/
│   ├── worker.py
│   └── floodalert/
├── pyproject.toml
├── wrangler.jsonc
├── run.py
└── .env.example
```

## สิ่งที่ต้องมี

1. Cloudflare account ที่เปิดใช้งาน Workers
2. Supabase PostgreSQL ที่ใช้อยู่เดิม
3. Node.js 16.17+ และ `uv`
4. Cloudflare Hyperdrive configuration ที่ชี้ไปยัง Supabase PostgreSQL

## Deploy แบบเร็ว

### 1) Login

```powershell
npx wrangler login
```

### 2) สร้าง Hyperdrive จาก Connection String ของ Supabase

เก็บ Connection String ไว้เป็นข้อมูลลับ และอย่า commit ลง GitHub. ตัวอย่าง:

```powershell
npx wrangler hyperdrive create flood-alert-db --connection-string="postgres://USER:PASSWORD@HOST:5432/postgres"
```

คำสั่งจะคืน **Hyperdrive configuration ID**.

### 3) ใส่ Hyperdrive ID ใน `wrangler.jsonc`

เปลี่ยน:

```json
"id": "YOUR_HYPERDRIVE_CONFIG_ID"
```

เป็น ID ที่ได้จากข้อ 2

### 4) ใส่ Secrets

```powershell
npx wrangler secret put SECRET_KEY
npx wrangler secret put TMD_ACCESS_TOKEN
```

เมื่อ CLI ถาม ให้กรอกค่าจริงในเครื่องของคุณ

### 5) Deploy

```powershell
uv run pywrangler deploy
```

หรือ:

```powershell
uvx --from workers-py pywrangler deploy
```

Cloudflare จะสร้าง URL ประมาณ:

```text
https://flood-alert.<your-subdomain>.workers.dev
```

## Local development

```powershell
uv run pywrangler dev
```

ถ้าจะทดสอบ Hyperdrive ใน local ให้ดูเอกสาร `CLOUDFLARE_DEPLOY.md` เรื่อง `localConnectionString` หรือใช้ `pywrangler dev --remote` เพื่อทดสอบผ่าน Hyperdrive ที่ deploy แล้ว

## Environment / Secrets

Secrets:

- `SECRET_KEY`
- `TMD_ACCESS_TOKEN`

Config vars ใน `wrangler.jsonc`:

- `TMD_FORECAST_URL`
- `TMD_WARNING_URL`
- `TMD_TIMEOUT`
- `TMD_FORECAST_HOURS`
- `TMD_MAX_RETRIES`
- `TMD_RETRY_BASE_SECONDS`
- `TMD_REQUEST_DELAY_SECONDS`
- `TMD_FORECAST_FIELDS`
- `TMD_WARNING_TIMEOUT`
- `TMD_WARNING_CACHE_MINUTES`

ไม่ต้องใส่ `DATABASE_URL` บน production Worker เพราะ database connection ถูกส่งผ่าน `HYPERDRIVE` binding.

## Cron

Worker มี 2 schedule:

- `*/15 * * * *` → refresh Forecast ของพื้นที่ที่ติดตาม
- `*/10 * * * *` → refresh Warning

Cron ของ Cloudflare ใช้เวลา UTC. งาน refresh ถูกย้ายออกจาก APScheduler เพราะ Workers เป็น request/event driven.

## หมายเหตุสำคัญ

Python Workers ใช้ Pyodide/WebAssembly. Package ต้องมี build ที่เข้ากันได้กับ Workers. โปรเจกต์นี้จึงใช้ `pg8000` กับ Hyperdrive และ `bcrypt` โดยตรง แทน `psycopg[binary]` และ `Flask-Bcrypt` ที่ผูกกับ native server environment มากกว่า.

สำหรับ Worker Free plan Cloudflare ระบุ request, CPU, memory และ subrequest limits ไว้ชัดเจน หากมีการใช้งานหนักหรือ refresh หลายจังหวัดพร้อมกัน อาจต้องปรับความถี่ Cron/upgrade plan.


## Cloudflare Workers runtime note
This build uses the built-in Workers Python SDK (`disable_python_external_sdk`) so Workers Builds with `npx wrangler deploy` do not require bundling the external `workers` package.
