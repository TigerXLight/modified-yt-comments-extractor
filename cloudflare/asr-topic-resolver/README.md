# YTCE ASR Topic Resolver

Free Cloudflare Worker resolver for background ASR glossary discovery.

This version does not require Brave Search or payment details.

It uses:
- YouTube/page metadata fetch
- MediaWiki/Fandom direct APIs
- Call of Duty Wiki search/parse
- optional RESOLVER_SHARED_KEY secret

Commands:

1. npm install
2. npx wrangler login
3. optional: npx wrangler secret put RESOLVER_SHARED_KEY
4. npx wrangler deploy

Desktop app:

set ASR_TOPIC_RESOLVER_URL=https://ytce-asr-topic-resolver.<your-subdomain>.workers.dev/resolve
set ASR_TOPIC_RESOLVER_KEY=<same value as RESOLVER_SHARED_KEY if configured>
python main.py
