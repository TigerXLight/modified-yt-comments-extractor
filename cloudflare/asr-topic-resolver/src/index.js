const STOPWORDS = new Set([
  "a","an","and","are","as","at","be","by","for","from","has","he","i","in","is","it","its",
  "of","on","or","she","that","the","their","this","to","was","were","with","you","your",
  "watch","shorts","youtube","youtu","http","https","www","com","social","media","community",
  "discord","twitter","twitch","instagram","spotify","listen","music","official","video",
  "started","streaming","details","games","wiki","fandom","page","edit","source","category",
  "navigation","comments","livechat","imported","situation","search","api","article"
]);

const WIKI_APIS = [
  {
    name: "Call of Duty Wiki",
    api: "https://callofduty.fandom.com/api.php",
    base: "https://callofduty.fandom.com/wiki/"
  },
  {
    name: "Wikipedia",
    api: "https://en.wikipedia.org/w/api.php",
    base: "https://en.wikipedia.org/wiki/"
  }
];

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-ASR-Resolver-Key",
    "Access-Control-Max-Age": "86400"
  };
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      ...corsHeaders()
    }
  });
}

function cleanTerm(raw) {
  let term = String(raw || "")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^[\s.,:;!?()[\]{}<>"'“”‘’]+|[\s.,:;!?()[\]{}<>"'“”‘’]+$/g, "");

  if (term.length < 3 || term.length > 80) return "";
  if (/^\d+$/.test(term)) return "";

  const lowered = term.toLowerCase();

  if (STOPWORDS.has(lowered)) return "";

  if (/^[A-Za-z0-9_-]{8,}$/.test(term) && !/[a-z][A-Z]/.test(term) && !/[^\x00-\x7F]/.test(term)) {
    return "";
  }

  return term;
}

function dedupeTerms(items, maxTerms = 80) {
  const out = [];
  const seen = new Set();

  for (const item of items || []) {
    const term = cleanTerm(item);
    if (!term) continue;

    const key = term.toLowerCase();
    if (seen.has(key)) continue;

    seen.add(key);
    out.push(term);

    if (out.length >= maxTerms) break;
  }

  return out;
}

function extractUrls(text) {
  const urls = [];
  const seen = new Set();

  for (const match of String(text || "").matchAll(/https?:\/\/[^\s<>"']+/gi)) {
    const url = match[0].replace(/[).,;\]]+$/g, "");

    if (!seen.has(url)) {
      seen.add(url);
      urls.push(url);
    }
  }

  return urls;
}

function urlPathTerms(url) {
  const terms = [];

  try {
    const parsed = new URL(url);
    const combined = decodeURIComponent(`${parsed.hostname} ${parsed.pathname}`);

    for (const piece of combined.split(/[./_\-#?=&+]+/g)) {
      if (piece && piece.length >= 3) terms.push(piece);
    }
  } catch (_) {}

  return terms;
}

function stripHtml(value) {
  return String(value || "")
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<noscript[\s\S]*?<\/noscript>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&quot;/g, "\"")
    .replace(/&#39;/g, "'")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/\s+/g, " ")
    .trim();
}

function extractTerms(text, urls = [], maxTerms = 80) {
  const terms = [];

  for (const url of urls) {
    terms.push(...urlPathTerms(url));
  }

  const value = String(text || "");

  for (const match of value.matchAll(/#([\p{L}\p{N}_-]{3,60})/gu)) {
    terms.push(match[1]);
  }

  for (const match of value.matchAll(/["'“‘]([^"'”’]{3,80})["'”’]/gu)) {
    terms.push(match[1]);
  }

  for (const match of value.matchAll(/\b(?:[A-Z][A-Za-z0-9'’-]{2,}\s+){1,4}[A-Z][A-Za-z0-9'’-]{2,}\b/g)) {
    terms.push(match[0]);
  }

  for (const match of value.matchAll(/\b[\p{L}][\p{L}\p{N}'’_-]{2,50}\b/gu)) {
    const token = match[0];
    const hasUnicode = /[^\x00-\x7F]/.test(token);
    const hasInternalUpper = /[a-z][A-Z]/.test(token) || /[A-Z].*[A-Z]/.test(token.slice(1));
    const startsUpper = /^[A-Z]/.test(token);
    const hasDigit = /\d/.test(token);

    if (hasUnicode || hasInternalUpper || startsUpper || hasDigit) {
      terms.push(token);
    }
  }

  return dedupeTerms(terms, maxTerms);
}

function contextText(context) {
  const parts = [];
  const info = context.video_info || {};

  if (context.url_text) parts.push(context.url_text);
  if (context.transcript_source) parts.push(context.transcript_source);
  if (context.language) parts.push(`language: ${context.language}`);

  if (Array.isArray(context.reference_terms)) {
    parts.push(`reference terms: ${context.reference_terms.join(", ")}`);
  }

  for (const key of ["title","video_title","description","channel_title","channel","author","tags","keywords","category"]) {
    const value = info[key];

    if (Array.isArray(value)) {
      parts.push(`${key}: ${value.join(", ")}`);
    } else if (value) {
      parts.push(`${key}: ${value}`);
    }
  }

  return parts.join("\n");
}

async function fetchJson(url, timeoutMs = 4500) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      signal: controller.signal,
      headers: {
        "User-Agent": "YTCE-ASR-TopicResolver/1.0",
        "Accept": "application/json"
      }
    });

    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`);
    }

    return await response.json();

  } finally {
    clearTimeout(timer);
  }
}

async function mediaWikiSearch(api, query, limit = 4) {
  const url = new URL(api);
  url.searchParams.set("action", "query");
  url.searchParams.set("list", "search");
  url.searchParams.set("srsearch", query);
  url.searchParams.set("srlimit", String(limit));
  url.searchParams.set("format", "json");
  url.searchParams.set("origin", "*");

  const data = await fetchJson(url.toString());
  return data?.query?.search || [];
}

async function mediaWikiExtract(api, title) {
  const url = new URL(api);
  url.searchParams.set("action", "query");
  url.searchParams.set("prop", "extracts|links");
  url.searchParams.set("titles", title);
  url.searchParams.set("explaintext", "1");
  url.searchParams.set("exintro", "0");
  url.searchParams.set("pllimit", "100");
  url.searchParams.set("format", "json");
  url.searchParams.set("origin", "*");

  const data = await fetchJson(url.toString());
  const pages = data?.query?.pages || {};
  const firstPage = Object.values(pages)[0] || {};

  const links = Array.isArray(firstPage.links)
    ? firstPage.links.map((item) => item.title).filter(Boolean)
    : [];

  return {
    title: firstPage.title || title,
    text: String(firstPage.extract || "").slice(0, 25000),
    links
  };
}

function buildQueries(context, localTerms) {
  const text = contextText(context);
  const terms = dedupeTerms(localTerms, 30);

  const queries = [];

  for (const term of terms.slice(0, 10)) {
    queries.push(term);
  }

  if (/bo7|codzombies|zombies|call of duty|black ops|kowakuj/i.test(text)) {
    queries.push("Caltheris");
    queries.push("Nyxara");
    queries.push("Shadowsmith");
    queries.push("Kowakujō");
    queries.push("Black Ops 7 Zombies");
    queries.push("BO7 Zombies");
  }

  return [...new Set(queries.map((q) => q.trim()).filter(Boolean))].slice(0, 14);
}

async function resolveWikiFast(context, localTerms, maxTerms) {
  const queries = buildQueries(context, localTerms);
  const corpus = [];
  const sources = [];
  const errors = [];
  const seenTitles = new Set();
  let parsedPages = 0;

  for (const wiki of WIKI_APIS) {
    for (const query of queries.slice(0, 10)) {
      let results = [];

      try {
        results = await mediaWikiSearch(wiki.api, query, 3);
      } catch (error) {
        errors.push(`Wiki search failed ${wiki.name}/${query}: ${error.message}`);
        continue;
      }

      for (const item of results.slice(0, 3)) {
        const title = item.title || "";
        if (!title) continue;

        const key = `${wiki.name}:${title}`;
        if (seenTitles.has(key)) continue;
        seenTitles.add(key);

        const snippet = stripHtml(item.snippet || "");

        corpus.push(`${title}\n${snippet}`);

        sources.push({
          title: `${wiki.name}: ${title}`,
          url: wiki.base + encodeURIComponent(title.replaceAll(" ", "_")),
          description: snippet.slice(0, 300)
        });

        if (parsedPages < 8) {
          try {
            const page = await mediaWikiExtract(wiki.api, title);
            parsedPages += 1;
            corpus.push(`${page.title}\n${page.links.join("\n")}\n${page.text}`);

            sources.push({
              title: `${wiki.name}: ${page.title}`,
              url: wiki.base + encodeURIComponent(page.title.replaceAll(" ", "_")),
              description: page.text.slice(0, 300)
            });

          } catch (error) {
            errors.push(`Wiki page fetch failed ${wiki.name}/${title}: ${error.message}`);
          }
        }
      }
    }
  }

  return {
    terms: extractTerms(corpus.join("\n"), [], maxTerms),
    sources,
    errors,
    queries,
    parsed_pages: parsedPages
  };
}

async function resolve(payload, env) {
  const context = payload.context || {};
  const maxTerms = Math.max(10, Math.min(Number(payload.max_terms || env.MAX_TERMS || 80), 120));

  const urls = [
    ...(Array.isArray(context.urls) ? context.urls : []),
    ...extractUrls(context.url_text || "")
  ];

  const uniqueUrls = [...new Set(urls)];

  const localText = contextText(context);

  const localTerms = dedupeTerms([
    ...(payload.local_terms || []),
    ...extractTerms(localText, uniqueUrls, maxTerms)
  ], maxTerms);

  const wiki = await resolveWikiFast(context, localTerms, maxTerms);

  const terms = dedupeTerms([
    ...wiki.terms,
    ...localTerms
  ], maxTerms);

  return {
    terms,
    sources: wiki.sources.slice(0, 24),
    queries: wiki.queries,
    errors: wiki.errors.slice(0, 12),
    provider: "free-mediawiki-fast",
    parsed_pages: wiki.parsed_pages
  };
}

async function handleResolve(request, env) {
  const configuredKey = env.RESOLVER_SHARED_KEY || "";

  if (configuredKey) {
    const auth = request.headers.get("Authorization") || "";
    const direct = request.headers.get("X-ASR-Resolver-Key") || "";
    const token = auth.startsWith("Bearer ") ? auth.slice("Bearer ".length) : "";

    if (token !== configuredKey && direct !== configuredKey) {
      return json({ error: "Unauthorized" }, 401);
    }
  }

  let payload;

  try {
    payload = await request.json();
  } catch (_) {
    return json({ error: "Invalid JSON body" }, 400);
  }

  const data = await resolve(payload, env);
  return json(data);
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders() });
    }

    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/health") {
      return json({
        ok: true,
        service: "ytce-asr-topic-resolver",
        provider: "free-mediawiki-fast",
        auth_required: Boolean(env.RESOLVER_SHARED_KEY)
      });
    }

    if (request.method === "POST" && url.pathname === "/resolve") {
      return handleResolve(request, env);
    }

    return json({
      ok: true,
      endpoints: ["/health", "/resolve"]
    });
  }
};
