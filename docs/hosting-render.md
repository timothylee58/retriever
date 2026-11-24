# Hosting: Render + Neon (no Cloudflare Containers)

Cloudflare Workers Paid is not required for this setup.

| Piece | Where |
|---|---|
| API | Render free web service `retriever-api` (Docker, Singapore) |
| Dashboard | Render free web service `retriever-web` (Node/Next.js, Singapore) |
| Database | Neon `icy-bar-03631492` (ap-southeast-1) |

## URLs

- API: https://retriever-api-mifm.onrender.com
- Web: https://retriever-web.onrender.com
- Health: https://retriever-api-mifm.onrender.com/health

## Notes

- Free Render services sleep after idle; the first request can take ~30–60s.
- `HITPAY_WEBHOOK_URL` should be `https://retriever-api-mifm.onrender.com/webhooks/hitpay`.
- Vercel was tried for the dashboard; the account returned `402 resource_creation_blocked` (billing/payment method). Render hosts both services instead.
- Set secrets in the Render dashboard; do not commit `.env` or `.render-env.local.json`.
