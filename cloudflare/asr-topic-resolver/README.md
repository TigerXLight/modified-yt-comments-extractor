# YTCE ASR Topic Resolver

Cloudflare Worker resolver for background ASR glossary discovery.

Commands:

1. npm install
2. npx wrangler login
3. npx wrangler secret put BRAVE_SEARCH_API_KEY
4. optional: npx wrangler secret put RESOLVER_SHARED_KEY
5. npx wrangler deploy

Desktop app:

set ASR_TOPIC_RESOLVER_URL=https://ytce-asr-topic-resolver.<your-subdomain>.workers.dev/resolve
set ASR_TOPIC_RESOLVER_KEY=<same value as RESOLVER_SHARED_KEY if configured>
python main.py
