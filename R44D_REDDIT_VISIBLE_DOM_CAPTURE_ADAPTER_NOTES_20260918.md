# R44D Reddit Visible DOM Capture Adapter

R44D starts the Reddit adapter after the completed Twitter/X and Bluesky account capture stacks.

It maps visible Reddit records into the same universal local ledger:

- Reddit submissions -> `post`
- Reddit crossposts -> `repost_or_reshare`
- Reddit comments -> `reply`
- `i.redd.it`, `preview.redd.it`, `v.redd.it`, and Reddit media/card URLs -> metadata-only media receipts
- caller-supplied or fixture screenshots -> screenshot receipts

Navigation parity:

- Twitter/X posts and retweets -> Reddit submissions plus crossposts: `/user/<handle>/submitted/`
- Twitter/X posts and replies -> Reddit submissions plus comments: `/user/<handle>/comments/`
- Reddit thread/comment URLs are preserved exactly.

R44D does not start a browser by itself, read or copy browser profile files, extract cookies or tokens, automate login, bypass challenges, scrape hidden APIs, or download remote media bytes.
