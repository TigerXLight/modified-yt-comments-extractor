# R43R Twitter/X Live Evidence To Account Ledger Notes

R43R materializes the live evidence already captured by the R43Q normal workbench route into the existing R43A account/date-folder ledger. It does not add a new control plane and it does not replace the R43L -> R43J -> R43I -> R43H -> R43G -> R43F -> R43E -> R43D route.

The materializer consumes the R43N/R43O/R43P live smoke outputs, especially the R42GZ runner directory, rendered DOM snapshot, session screenshot, R42GV visible-browser observation store, and R42GT media index outputs. It extracts visible Twitter/X tweet articles in DOM order and feeds the resulting records into `write_twitter_x_account_media_ledger_r43a(...)`.

R43R keeps remote Twitter/X media metadata-only. It filters obvious site chrome and account/profile assets such as `abs.twimg.com`, default profile images, profile avatars, and banners so those are not attached as post media. If only the session screenshot exists, each post folder receives a `static_screenshot.png` copy marked as `session_visible_page_fallback`, not an article crop.

R43R records date-source provenance for each post. ISO visible datetimes use the visible date, relative visible times use the capture date with a warning, and ambiguous month/day text such as `Sep 14` is kept in `dates/unknown_date/` with `date_source=unknown_ambiguous_month_day_visible_time`; it must not silently fall back to the capture date.

The R43D explicit-live branch now runs R43R after R43N/R43O/R43P prove real non-fixture promoted evidence. The normal surface receipt now includes ledger paths and counts through `account_ledger_summary` and the extended `live_evidence_summary`.

R43R performs no browser launch, network access, remote media download, hidden API scraping, login automation, cookie/token extraction, challenge bypass, source-role work, review-window rewrite, or YouTube capture engine change.
