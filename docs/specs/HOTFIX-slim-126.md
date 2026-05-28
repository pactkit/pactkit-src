# HOTFIX-slim-126: Fix pactkit.dev Cloudflare Cache Hit Rate

## Background
pactkit.dev is a pure static docs site (Next.js `output: 'export'`, all pages use `generateStaticParams`).
It was deployed via `@opennextjs/cloudflare` (Workers adapter), which is designed for SSR.
This caused all requests to route through Cloudflare Workers instead of Cloudflare Assets CDN cache,
resulting in ~30% cache hit rate instead of the expected 80%+.

## Target
- `~/workspaces/pactkit.dev/next.config.mjs`
- `~/workspaces/pactkit.dev/wrangler.jsonc`
- `~/workspaces/pactkit.dev/open-next.config.ts`
- `~/workspaces/pactkit.dev/package.json` (deploy scripts)

## Fix
Remove OpenNext/Workers setup. Keep `output: 'export'` in next.config.mjs.
Update deploy scripts to use `wrangler pages deploy out/` (Cloudflare Pages static deploy).
