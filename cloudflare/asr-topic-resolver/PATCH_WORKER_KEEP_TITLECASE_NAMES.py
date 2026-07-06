from pathlib import Path

p = Path("src/index.js")
s = p.read_text(encoding="utf-8")

old = '''  if (/^[A-Za-z0-9_-]{8,}$/.test(term) && !/[a-z][A-Z]/.test(term) && !/[^\\x00-\\x7F]/.test(term)) {
    return "";
  }
'''

new = '''  const looksLikeVideoId = /^[A-Za-z0-9_-]{8,}$/.test(term) && /[_-]/.test(term);
  const looksLikePlainLowerId = /^[a-z0-9_-]{10,}$/.test(term);
  const isNormalTitleCaseName = /^[A-Z][a-z][A-Za-z'’_-]{2,}$/.test(term);

  if ((looksLikeVideoId || looksLikePlainLowerId) && !isNormalTitleCaseName && !/[^\\x00-\\x7F]/.test(term)) {
    return "";
  }
'''

if old);

  if ((looksLikeVideoId || looksLikePlainLowerId) && !isNormalTitleCaseName && !/[^\\x not in s:
    raise RuntimeError("Could not find old video-id filter block in src/index.js")

s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("Worker now keeps normal TitleCase names like Shadowsmith, Freckelston, Caltheris.")