# R42FX universal source/API3128 deep route patch

Purpose:

- Do not rebuild the existing source-adapter framework.
- Treat MSN as the proven reusable news-site model.
- Add Metro as a known news-site row with article text and screenshot marked tested true, while comments remain not tested.
- Add a side-effect-free Metro archive/source-adapter availability scan for the supplied live URL, Wayback URL, and archive.ph URL.
- Make selected public webpage Video & Audio candidates try the API3128-backed JDownloader internal bridge before direct file fallback or yt-dlp fallback/reference paths.

Boundaries:

- No CAPTCHA or access-control bypass is added.
- No archive submission is performed by the scan.
- No network fetch/media download is performed by the scan.
- yt-dlp is retained only as fallback/reference plan language where existing code needs compatibility.
- Twitter/X is not marked closed by this patch.
- Metro comments are not marked tested until a real comments capture/review run exercises them.
