const STOPWORDS = new Set([
  "a","an","and","are","as","at","be","by","for","from","has","he","i","in","is","it","its",
  "of","on","or","she","that","the","their","this","to","was","were","with","you","your",
  "watch","shorts","youtube","youtu","http","https","www","com","social","media","community",
  "discord","twitter","twitch","instagram","spotify","listen","music","official","video",
  "started","streaming","details","games","wiki","fandom","page","edit","source","category",
  "navigation","comments","livechat","imported","situation","search","api","article",
  "legacy","five","tank","misty","weasel","smokey","lena","josee"
]);

const PRESERVE_TERMS = new Set([
  "kingman",
  "zonex",
  "shadowsmith",
  "nicolas cage",
  "nicolas",
  "cage",
  "zonex",
  "shadowsmith",
  "nicolas cage",
  "nicolas",
  "cage",
  "freckelston",
  "caltheris",
  "nyxara",
  "kowakujō",
  "kowakujo"
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
    .replace(/^[\s.,:;!?()[\]{}<>"'“”‘’]+|[\s.,:;!?()[\]{}<>"'“”‘’]+$/g, "")
    .replace(/[’']s$/i, "");

  if (term.length < 3 || term.length > 80) return "";
  if (/^\d+$/.test(term)) return "";

  if (/^[A-Za-z0-9_-]{11}$/.test(term) && /[_-]/.test(term)) return "";
  if (/\byoutube\b/i.test(term)) return "";

  const lowered = term.toLowerCase();
  if (PRESERVE_TERMS.has(lowered)) return term;
  if (STOPWORDS.has(lowered)) return "";

  if (/^[A-Za-z0-9_-]{8,}$/.test(term) && !/[a-z][A-Z]/.test(term) && !/[^\x00-\x7F]/.test(term)) {
    return "";
  }

  return term;
}

function norm(value) {
  return cleanTerm(value)
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[’']/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function dedupeTerms(items, maxTerms = 80) {
  const out = [];
  const seen = new Set();

  for (const item of items || []) {
    const term = cleanTerm(item);
    if (!term) continue;

    const key = norm(term);
    if (!key || seen.has(key)) continue;

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

function extractCandidateTerms(text, urls = [], maxTerms = 80) {
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

async function fetchJson(url, timeoutMs = 3500) {
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

async function mediaWikiSearch(api, query, limit = 5) {
  const url = new URL(api);
  url.searchParams.set("action", "query");
  url.searchParams.set("list", "search");
  url.searchParams.set("srsearch", `"${query}"`);
  url.searchParams.set("srlimit", String(limit));
  url.searchParams.set("format", "json");
  url.searchParams.set("origin", "*");

  const data = await fetchJson(url.toString());
  return data?.query?.search || [];
}

function titleMatchesSeed(title, seed) {
  const t = norm(title.replace(/\s*\([^)]*\)\s*/g, " "));
  const s = norm(seed);

  if (!t || !s) return false;
  if (t === s) return true;

  if (s.length >= 5 && t.includes(s)) return true;
  if (t.length >= 5 && s.includes(t)) return true;

  return false;
}

function buildSeeds(payload) {
  const context = payload.context || {};
  const urls = [
    ...(Array.isArray(context.urls) ? context.urls : []),
    ...extractUrls(context.url_text || "")
  ];

  const referenceTerms = Array.isArray(context.reference_terms) ? context.reference_terms : [];
  const localTerms = Array.isArray(payload.local_terms) ? payload.local_terms : [];
  const textTerms = extractCandidateTerms(contextText(context), urls, 50);

  const text = contextText(context);

  const defaults = [];
  if (/bo7|codzombies|zombies|call of duty|black ops|kowakuj/i.test(text)) {
    defaults.push("Kowakujō", "Caltheris", "Nyxara", "Shadowsmith");
  }

  return dedupeTerms([
    ...referenceTerms,
    ...localTerms,
    ...defaults,
    ...textTerms
  ], 50);
}

async function resolve(payload, env) {
  const maxTerms = Math.max(10, Math.min(Number(payload.max_terms || env.MAX_TERMS || 80), 120));
  const seeds = buildSeeds(payload);
  const terms = [...seeds];
  const sources = [];
  const errors = [];
  const acceptedTitles = [];

  for (const seed of seeds.slice(0, 24)) {
    for (const wiki of WIKI_APIS) {
      let results = [];

      try {
        results = await mediaWikiSearch(wiki.api, seed, 4);
      } catch (error) {
        errors.push(`Wiki search failed ${wiki.name}/${seed}: ${error.message}`);
        continue;
      }

      for (const item of results) {
        const title = item.title || "";
        if (!title) continue;

        if (!titleMatchesSeed(title, seed)) {
          continue;
        }

        acceptedTitles.push(title);

        sources.push({
          title: `${wiki.name}: ${title}`,
          url: wiki.base + encodeURIComponent(title.replaceAll(" ", "_")),
          matched_seed: seed
        });
      }
    }
  }

  return {
    terms: dedupeTerms(terms, maxTerms),
    sources: sources.slice(0, 20),
    errors: errors.slice(0, 12),
    provider: "free-reference-wiki-strict-v2",
    seed_terms: seeds.slice(0, 50),
    accepted_titles: dedupeTerms(acceptedTitles, 50)
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
        provider: "free-reference-wiki-strict-v2",
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
