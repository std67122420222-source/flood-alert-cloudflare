# FloodAlert — Cloudflare Deploy Guide

## A. สร้าง Hyperdrive จาก Supabase

1. เข้า Cloudflare Dashboard → **Workers & Pages** → **Hyperdrive** → **Create Configuration**
2. ใช้ connection string ของ Supabase PostgreSQL ที่คุณมีอยู่แล้ว
3. ตั้งชื่อ เช่น `flood-alert-db`
4. หลังสร้าง ให้คัดลอก **Configuration ID**
5. นำ ID ไปใส่ใน `wrangler.jsonc` ที่ `HYPERDRIVE.id`

หรือใช้ CLI:

```powershell
npx wrangler hyperdrive create flood-alert-db --connection-string="postgres://USER:PASSWORD@HOST:5432/postgres"
```

อย่า commit connection string ลง GitHub.

## B. ใส่ Secrets

```powershell
npx wrangler secret put SECRET_KEY
npx wrangler secret put TMD_ACCESS_TOKEN
```

## C. Deploy

```powershell
uv run pywrangler deploy
```

## D. ตรวจ Cron

Cloudflare → Worker → **Settings → Triggers → Cron Triggers**

ควรเห็น 2 schedules:

```text
*/15 * * * *
*/10 * * * *
```

Cloudflare ระบุว่า Cron ใช้ UTC และการเปลี่ยน Cron Trigger อาจใช้เวลาหลายนาทีกว่าจะกระจายครบ.

## E. Test Cron locally

```powershell
npx wrangler dev --test-scheduled
```

จากนั้น:

```powershell
curl "http://localhost:8787/cdn-cgi/local/scheduled?cron=*/15+*+*+*+*"
```

## F. เปลี่ยน Database เมื่อเปลี่ยน Supabase

ไม่ต้องใส่ `DATABASE_URL` ใน Worker production. ให้ update Hyperdrive configuration ให้ชี้ PostgreSQL ตัวใหม่ แล้ว redeploy/restart ตามขั้นตอน Cloudflare.
