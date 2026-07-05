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
    weight: 3
  },
  {
    name: "Zombies Wiki",
    api: "https://callofduty.fandom.com/api.php",
    weight: 2
  },
  {
    name: "Wikipedia",
    api: "https://en.wikipedia.org/w/api.php",
    weight: 1
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

function extractMeta(htmlText) {
  const text = String(htmlText || "");
  const parts = [];

  const title = text.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
  if (title) parts.push(stripHtml(title[1]));

  const metaPatterns = [
    /<meta[^>]+name=["']description["'][^>]+content=["']([\s\S]*?)["']/i,
    /<meta[^>]+property=["']og:title["'][^>]+content=["']([\s\S]*?)["']/i,
    /<meta[^>]+property=["']og:description["'][^>]+content=["']([\s\S]*?)["']/i,
    /"shortDescription"\s*:\s*"((?:\\"|[^"])*)"/i,
    /"title"\s*:\s*\{"runs"\s*:\s*\[\{"text"\s*:\s*"((?:\\"|[^"])*)"/i
  ];

  for (const pattern of metaPatterns) {
    const match = text.match(pattern);
    if (match && match[1]) {
      try {
        parts.push(JSON.parse(`"${match[1]}"`));
      } catch (_) {
        parts.push(stripHtml(match[1]));
      }
    }
  }

  return parts.join("\n");
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

  return parts.join("\n");
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

async function fetchJson(url) {
  const response = await fetch(url, {
    headers: {
      "User-Agent": "YTCE-ASR-TopicResolver/1.0",
      "Accept": "application/json"
    }
  });

  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }

  return await response.json();
}

function buildWikiQueries(context, localTerms) {
  const text = contextText(context);
  const terms = dedupeTerms(localTerms, 30);

  const quoted = [...text.matchAll(/["'“‘]([^"'”’]{3,80})["'”’]/gu)].map((m) => m[1]);
  const hashtags = [...text.matchAll(/#([\p{L}\p{N}_-]{3,60})/gu)].map((m) => m[1]);

  const topicSeeds = dedupeTerms([
    ...quoted,
    ...hashtags,
    ...terms,
    "Black Ops 7 Zombies",
    "Call of Duty Zombies",
    "Kowakujō"
  ], 40);

  const queries = [];

  for (const seed of topicSeeds.slice(0, 12)) {
    queries.push(seed);
  }

  if (/bo7|codzombies|zombies|call of duty|black ops/i.test(text)) {
    queries.push("Black Ops 7 Zombies");
    queries.push("BO7 Zombies");
    queries.push("Kowakujō");
    queries.push("Caltheris");
    queries.push("Nyxara");
    queries.push("Shadowsmith");
  }

  return [...new Set(queries.map((q) => q.trim()).filter(Boolean))].slice(0, 24);
}

async function mediaWikiSearch(api, query, limit = 8) {
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

async function mediaWikiParse(api, title) {
  const url = new URL(api);
  url.searchParams.set("action", "parse");
  url.searchParams.set("page", title);
  url.searchParams.set("prop", "text|links|displaytitle");
  url.searchParams.set("format", "json");
  url.searchParams.set("origin", "*");

  const data = await fetchJson(url.toString());
  const parse = data?.parse || {};
  const htmlText = parse?.text?.["*"] || "";
  const links = Array.isArray(parse.links) ? parse.links : [];

  return {
    title: parse.title || title,
    displaytitle: stripHtml(parse.displaytitle || ""),
    text: stripHtml(htmlText).slice(0, 40000),
    links: links.map((item) => item["*"]).filter(Boolean).slice(0, 200)
  };
}

async function resolveWikiDatabases(context, localTerms, maxTerms) {
  const queries = buildWikiQueries(context, localTerms);
  const corpus = [];
  const sources = [];
  const errors = [];
  const foundTitles = new Set();

  for (const wiki of WIKI_APIS) {
    for (const query of queries.slice(0, 12)) {
      try {
        const results = await mediaWikiSearch(wiki.api, query, 6);

        for (const item of results) {
          const title = item.title || "";
          if (!title) continue;

          const key = `${wiki.name}:${title}`;
          if (foundTitles.has(key)) continue;
          foundTitles.add(key);

          sources.push({
            title: `${wiki.name}: ${title}`,
            url: item.url || "",
            description: stripHtml(item.snippet || "").slice(0, 300)
          });

          corpus.push(`${title}\n${stripHtml(item.snippet || "")}`);

          if (foundTitles.size <= 14) {
            try {
              const page = await mediaWikiParse(wiki.api, title);
              corpus.push(`${page.title}\n${page.displaytitle}\n${page.links.join("\n")}\n${page.text}`);
              sources.push({
                title: `${wiki.name}: ${page.title}`,
                url: wiki.api.replace("/api.php", `/wiki/${encodeURIComponent(page.title.replaceAll(" ", "_"))}`),
                description: page.text.slice(0, 300)
              });
            } catch (error) {
              errors.push(`Wiki parse failed ${wiki.name}/${title}: ${error.message}`);
            }
          }
        }
      } catch (error) {
        errors.push(`Wiki search failed ${wiki.name}/${query}: ${error.message}`);
      }
    }
  }

  return {
    terms: extractTerms(corpus.join("\n"), [], maxTerms),
    sources,
    errors,
    queries
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
  const corpus = [];
  const sources = [];
  const errors = [];

  corpus.push(contextText(context));

  for (const url of uniqueUrls.slice(0, 4)) {
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
    ...extractTerms(corpus.join("\n"), uniqueUrls, maxTerms)
  ], maxTerms);

  const wiki = await resolveWikiDatabases(context, firstPassTerms, maxTerms);

  const terms = dedupeTerms([
    ...wiki.terms,
    ...firstPassTerms
  ], maxTerms);

  return {
    terms,
    sources: [...sources, ...wiki.sources].slice(0, 30),
    queries: wiki.queries,
    errors: [...errors, ...wiki.errors].slice(0, 20),
    provider: "free-mediawiki-direct"
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
        provider: "free-mediawiki-direct",
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
