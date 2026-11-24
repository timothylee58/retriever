# Cloudflare Workers Builds settings for Retriever

The dashboard error:

```text
Could not detect a directory containing static files (e.g. html, css and js) for the project
```

means Wrangler ran at the **repo root** and treated the project as a static site. This repo is not a static site. The API Worker lives under `workers/retriever-api`.

## Fix in the Cloudflare dashboard

Open the Worker connected to this GitHub repo → **Settings** → **Build**.

| Setting | Value |
|---|---|
| Root directory | leave empty (`/` of the repo) |
| Build command | `npm install` |
| Deploy command | `npm run deploy:api` |
| Non-production branch deploy command | same: `npm run deploy:api` |

Do **not** leave the Deploy command blank. A blank command makes Wrangler guess, and at the repo root it looks for `index.html` and fails with the static-files error.

Do **not** set Root directory to `web/`. That is the Next.js dashboard, not the API container Worker.

## After the static-files error is gone

A successful build still fails at:

```text
A request to the Cloudflare API (.../containers/me) failed
```

That call is the Containers product. On the **Free** plan Containers are **N/A**. Enable **Workers Paid** ($5/month) on the account, then retry the deploy:

https://dash.cloudflare.com/?to=/:account/workers/plans

The Worker name in `workers/retriever-api/wrangler.jsonc` must match the Cloudflare project name (`retriever`). A mismatch only warns; missing Containers entitlement fails the deploy.

The Neon database in Singapore already has the Retriever schema. It is separate from this error.
