# V76L Article Extraction Adapter

V76L is the first real article-extraction adapter after the V76K2 HOME/source-criticism rebase.

It uses the downloaded GitHub references as optional extractor baselines:

- `metadata_parser` for page/OpenGraph/canonical metadata
- `trafilatura` for article body and metadata extraction
- `newspaper4k` for article title/text/byline/date fallback

The adapter is offline by default. It parses supplied HTML text or a local HTML file. It does not fetch a URL, crawl a website, download media, copy files, or decide final Primary/Secondary/Tertiary source roles.

## Important source-criticism rule

Extraction is not classification. A newspaper article can contain direct interview language, police/court language, family/authority claims, or agency/publisher chain language. The adapter records these structural markings and sends the record to review rather than declaring the source role as final.

## Image/person affiliation rule

If an article exposes image URLs, V76L records them as URLs only. It does not download them and it does not treat the pictured person as affiliated with the evaluated claim. The result includes `claim_subject_affiliation_review` when image material requires review.

## Guarded write

The source-preview JSON writer requires:

```text
WRITE_ARTICLE_EXTRACTION_SOURCE_PREVIEW
```

The preview is a standalone metadata file and does not alter the HOME repository.
