const STOPWORDS = new Set([
  "a","an","and","are","as","at","be","by","for","from","has","he","i","in","is","it","its",
  "of","on","or","she","that","the","their","this","to","was","were","with","you","your",
  "watch","shorts","youtube","youtu","http","https","www","com","social","media","community",
  "discord","twitter","twitch","instagram","spotify","listen","music","official","video",
  "started","streaming","details","games","wiki","fandom","page","edit","source","category",
  "navigation","comments","livechat","imported","situation"
]);

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

  // Drop likely random YouTube/video IDs unless they have obvious word casing.
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

function extractMeta(htmlText) {
  const text = String(htmlText || "");
  const parts = [];

  const title = text.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
  if (title) parts.push(stripHtml(title[1]));

  const metaPatterns = [
    /<meta[^>]+name=["']description["'][^>]+content=["']([\s\S]*?)["']/i,
    /<meta[^>]+property=["']og:title["'][^>]+content=["']([\s\S]*?)["']/i,
    /<meta[^>]+property=["']og:description["'][^>]+content=["']([\s\S]*?)["']/i
  ];

  for (const pattern of metaPatterns) {
    const match = text.match(pattern);
    if (match && match[1]) parts.push(stripHtml(match[1]));
  }

  return parts.join("\\n");
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

  for (const key of ["title","video_title","description","channel_title","channel","author","tags","keywords","category"]) {
    const value = info[key];

    if (Array.isArray(value)) {
      parts.push(`${key}: ${value.join(", ")}`);
    } else if (value) {
      parts.push(`${key}: ${value}`);
    }
  }

  return parts.join("\\n");
}

async function braveSearch(query, env) {
  if (!env.BRAVE_SEARCH_API_KEY) {
    throw new Error("BRAVE_SEARCH_API_KEY is not configured");
  }

  const endpoint = new URL("https://api.search.brave.com/res/v1/web/search");
  endpoint.searchParams.set("q", query);
  endpoint.searchParams.set("count", "10");
  endpoint.searchParams.set("text_decorations", "false");
  endpoint.searchParams.set("safesearch", "moderate");

  const response = await fetch(endpoint.toString(), {
    headers: {
      "Accept": "application/json",
      "X-Subscription-Token": env.BRAVE_SEARCH_API_KEY
    }
  });

  if (!response.ok) {
    throw new Error(`Brave Search failed: ${response.status} ${response.statusText}`);
  }

  return await response.json();
}

function buildQueries(context, localTerms) {
  const text = contextText(context);
  const terms = dedupeTerms(localTerms, 20);
  const seed = terms.slice(0, 8).join(" ");

  const queries = [];

  if (seed) {
    queries.push(`${seed} glossary`);
    queries.push(`${seed} wiki`);
    queries.push(`${seed} fandom`);
  }

  if (/codzombies|bo7|zombies|call of duty/i.test(text)) {
    queries.push(`${seed} Call of Duty Zombies wiki`);
    queries.push(`site:callofduty.fandom.com ${seed}`);
  }

  if (!queries.length) {
    queries.push(`${text.slice(0, 120)} glossary`);
  }

  return [...new Set(queries.map((q) => q.trim()).filter(Boolean))].slice(0, 6);
}

function resultSource(result) {
  return {
    title: result.title || "",
    url: result.url || "",
    description: result.description || ""
  };
}

function shouldFetchPage(url) {
  try {
    const host = new URL(url).hostname.toLowerCase();
    return host.includes("fandom.com") || host.includes("wikipedia.org") || host.includes("wiki");
  } catch (_) {
    return false;
  }
}

async function fetchText(url) {
  const response = await fetch(url, {
    headers: {
      "User-Agent": "YTCE-ASR-TopicResolver/1.0",
      "Accept": "text/html,application/xhtml+xml,application/json;q=0.8,*/*;q=0.5"
    }
  });

  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }

  return await response.text();
}

async function resolve(payload, env) {
  const context = payload.context || {};
  const maxTerms = Math.max(10, Math.min(Number(payload.max_terms || env.MAX_TERMS || 80), 120));

  const urls = [
    ...(Array.isArray(context.urls) ? context.urls : []),
    ...extractUrls(context.url_text || "")
  ];

  const uniqueUrls = [...new Set(urls)];
  const corpus = [];
  const sources = [];
  const errors = [];

  corpus.push(contextText(context));

  for (const url of uniqueUrls.slice(0, 3)) {
    try {
      const page = await fetchText(url);
      const meta = extractMeta(page);
      if (meta) {
        corpus.push(meta);
        sources.push({ title: "Source metadata", url, description: meta.slice(0, 500) });
      }
    } catch (error) {
      errors.push(`Source fetch failed for ${url}: ${error.message}`);
    }
  }

  const firstPassTerms = dedupeTerms([
    ...(payload.local_terms || []),
    ...extractTerms(corpus.join("\\n"), uniqueUrls, maxTerms)
  ], maxTerms);

  const queries = buildQueries(context, firstPassTerms);

  if (env.BRAVE_SEARCH_API_KEY) {
    for (const query of queries) {
      try {
        const data = await braveSearch(query, env);
        const results = data?.web?.results || [];

        for (const result of results.slice(0, 8)) {
          const source = resultSource(result);
          if (source.url) sources.push(source);
          corpus.push(`${source.title}\\n${source.description}\\n${source.url}`);

          if (source.url && shouldFetchPage(source.url)) {
            try {
              const page = await fetchText(source.url);
              corpus.push(extractMeta(page));
              corpus.push(stripHtml(page).slice(0, 25000));
            } catch (error) {
              errors.push(`Result page fetch failed for ${source.url}: ${error.message}`);
            }
          }
        }
      } catch (error) {
        errors.push(`Brave query failed "${query}": ${error.message}`);
      }
    }
  } else {
    errors.push("BRAVE_SEARCH_API_KEY is not configured");
  }

  const terms = dedupeTerms([
    ...extractTerms(corpus.join("\\n"), uniqueUrls, maxTerms),
    ...firstPassTerms
  ], maxTerms);

  return {
    terms,
    sources: sources.slice(0, 20),
    queries,
    errors,
    provider: env.BRAVE_SEARCH_API_KEY ? "brave-search" : "local-only"
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
        brave_configured: Boolean(env.BRAVE_SEARCH_API_KEY),
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
