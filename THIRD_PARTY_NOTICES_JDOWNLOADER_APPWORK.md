# Third-party architecture notice: JDownloader / AppWork

V80M adds a Python/Tk runtime foundation for YTCE based on the queue, UI-dispatch,
and slow-UI-detection structure reviewed from the uploaded JDownloader/AppWork source set.

Reviewed source files:

- `org.appwork.utils.event.queue.Queue`
- `org.appwork.utils.event.queue.QueueAction`
- `org.appwork.utils.event.queue.QueueThread`
- `org.appwork.utils.swing.EDT`
- `org.appwork.utils.swing.EDTHelper`
- `org.appwork.utils.swing.EDTRunner`
- `org.appwork.utils.swing.SlowEDTDetector`

The reviewed Java file headers identify the upstream project as AppWork Utilities / JDownloader,
with AppWork GmbH copyright notices and dual commercial / AGPL-style licensing terms. Keep this
notice with the YTCE source when the V80M runtime modules are used, modified, or redistributed.

Python files added by V80M:

- `ytce_app_work_queue.py`
- `ytce_ui_dispatch.py`
- `ytce_slow_tk_detector.py`

Implementation mapping:

- AppWork `Queue`, `QueueAction`, `QueueThread` → `YTCEWorkQueue`, `YTCEWorkItem`, worker loop.
- AppWork `EDTHelper` / `EDTRunner` → `YTCEUiDispatcher` using Tk `after(...)`.
- AppWork `SlowEDTDetector` → `YTCESlowTkDetector` using delayed Tk heartbeats.

This notice is intentionally explicit because the V80M code is not just general inspiration; it is a
source-credited Python implementation of the reviewed runtime design and behaviour.

## V80Q browser-grid FILES dedupe integration

YTCE V80Q wires the side-effect-free FILES/media intake dedupe guard into the browser-native image grid "Add selected to FILES" path.  The implementation keeps JDownloader/AppWork-style identity tracking and repeat-work avoidance labels in project terminology: source URL identity, local path identity, batch duplicate review, existing record reuse, and explicit added/reused/duplicate/failed operator counts.

Reference source areas reviewed:

- JDownloader/AppWork queue and watchdog infrastructure already cited above.
- YTCE V80P `file_intake_dedupe.py`, which implements the Python/Tk FILES/media intake dedupe model from that architecture.

No Java source text is pasted into this Python integration.  The functionality/structure is implemented natively in YTCE with the JDownloader/AppWork source pattern credited here.

## V80R — Persistent FILES/media intake identity store

V80R extends the YTCE FILES/media dedupe guard with a persistent identity-store layer.

JDownloader/AppWork source pattern reviewed:

- `jd.controlling.downloadcontroller.DownloadWatchDog`
- `jd.controlling.downloadcontroller.DownloadWatchDogJob`
- `org.appwork.utils.event.queue.Queue`
- `org.appwork.utils.event.queue.QueueAction`
- `org.appwork.utils.event.queue.QueueThread`

YTCE implementation files:

- `file_intake_identity_store.py`
- `file_intake_identity_store_test.py`
- browser-grid FILES intake integration in `main.py`

Implementation note: this is a Python/Tk-native JSON identity store for already-known
FILES/media intake records.  It preserves the reviewed JDownloader/AppWork method of
operation — explicit identity records, stale-entry filtering, bounded memory, and
reuse before repeated media work — without embedding Java source text.


## V80S — Browser-grid known FILES/media preflight labels

V80S surfaces the existing FILES/media intake identity review before the operator clicks
"Add selected to FILES" in the browser-native image grid.

JDownloader/AppWork source pattern reviewed:

- `jd.controlling.downloadcontroller.DownloadWatchDog`
- `org.appwork.utils.event.queue.Queue`
- `org.appwork.utils.event.queue.QueueAction`
- `org.appwork.utils.event.queue.QueueThread`

YTCE implementation files:

- browser-grid FILES/media card status integration in `main.py`
- source-level UI contract checks in `main_source_resource_ui_test.py`

Implementation note: this is Python/Tk/browser-native UI feedback for the already-ported
identity/dedupe workflow.  It preserves the reviewed method of operation — preflight identity
review, explicit reused/duplicate/failed labels, and no media mutation during review — without
embedding Java source text.

## V80T — Browser-grid already-added FILES/media wording and highlight

V80T refines the V80S browser-native image-grid preflight labels so reused FILES/media
records are shown as already added to FILES before the operator clicks "Add selected to FILES".

JDownloader/AppWork source pattern reviewed:

- `jd.controlling.downloadcontroller.DownloadWatchDog`
- `org.appwork.utils.event.queue.Queue`
- `org.appwork.utils.event.queue.QueueAction`
- `org.appwork.utils.event.queue.QueueThread`

YTCE implementation files:

- browser-grid FILES/media card status wording and highlight in `main.py`
- source-level UI contract checks in `main_source_resource_ui_test.py`

Implementation note: this keeps the V80S/V80R preflight identity review and only changes the
operator-facing browser-grid wording/highlight. No Java source text is embedded.

## V80U browser grid same-image variant grouping and lighter already-added labels

V80U continues the JDownloader/AppWork-inspired identity and duplicate-avoidance work by collapsing browser-grid image candidates that appear to be the same image at different webpage/CDN sizes. The Python implementation keeps a single default representative card, prefers already-added variants when present, otherwise prefers the highest-dimension candidate, and marks previously-added cards with a lighter ghosted state rather than a heavy blocking badge.


## V80U visual polish

The browser-grid already-added state now uses a lighter ghosted card and compact badge while retaining the JDownloader/AppWork-inspired identity/reuse flow documented above.


## V80V browser image variant selector

Adds a compact browser-grid variant selector adapted from the JDownloader/AppWork-style grouping/reuse model already documented in this notice. Same-image size variants are represented as one card; the highest-dimension candidate is first/default, and alternate dimensions can be selected from the image-size control without cluttering the bottom metadata row.

## V80W browser-grid controls and variant selector polish

V80W continues the AppWork/JDownloader-style operator-control model by keeping resource
identity, open/download actions, URL copying, and grouped variant selection as explicit
per-item controls instead of hover-only hidden overlays. This is a Python/HTML/CSS/JS
implementation in YTCE; no Java source text is copied.

## V80X browser-grid compact controls

V80X continues the JDownloader/AppWork-style queued media-intake and browser-grid work by keeping explicit per-card URL/Open/Download actions compact and non-blocking. The UI change keeps URL copy as an explicit control and avoids hover overlays interfering with variant-size selection.

## V80Y browser-grid icon control polish

V80Y keeps the browser-native grid architecture and the AppWork/JDownloader-attributed queued-runtime foundations unchanged. It only polishes the in-card browser-grid controls by replacing crowded text buttons with compact icon-labelled URL/Open/Download controls while retaining tooltips and accessible labels.

## V80Z browser-grid download icon control polish

V80Z keeps the text URL and text Open controls from the browser-native image grid while replacing only the compact Download text control with the user-supplied Icons8 download image as an inline data-URI icon. The AppWork/JDownloader-attributed queue, watchdog, and media-intake foundations are unchanged.

## V80Z const fix for download icon data URI

This repair keeps the V80Z text URL/Open controls and supplied download-icon button, and fixes the generated browser-grid page by defining the inline download icon data URI in the source-image browser script before its render path creates image cards.

## V80AA browser-grid direct download icon behavior and hover polish

V80AA keeps the text `URL` and `Open` controls, uses the user's white download icon for the single-image download control, routes that icon through the same FILES intake endpoint instead of browser navigation, marks the card as `Added before` after a successful per-card intake request, applies the same blue hover outline to Open/download controls as the URL button, and hides the `Added before` badge while hover controls are visible.
## 2026-08-22 - V81A browser-native Video & Audio grid

- Added a browser-native Video & Audio window using the same lightweight app-window pattern as the Images grid.
- Added direct media URL copy/open controls, download-icon FILES intake, already-added highlighting, and persistent source identity records for browser-grid video/audio candidates.
- Preserved the existing VDH-length Tk hover preview implementation as the fallback/provider-specific path rather than copying JDownloader source code.

## 2026-08-22 - V81B browser-native Video & Audio quick-open repair

V81B keeps the browser-native Video & Audio card layout from V81A but restores the fast/static-first open behaviour from the prior Tk video dialog. The browser-native window now opens from cached or quick static video/audio candidates instead of waiting for the slower rendered discovery path, gates repeated clicks while discovery is already pending, and lets the source-row rendered prefetch continue in the background. The existing VDH-length hover-preview and JDownloader/AppWork-attributed queued intake foundations remain unchanged.

## 2026-08-22 - V81C browser-native Video & Audio metadata and preview polish

V81C keeps the V81A/V81B browser-native Video & Audio grid and quick-open model, then adds browser-side metadata refinement and manual preview controls. Directly playable video/audio elements now update displayed dimensions after metadata loads, already-added media previews are visibly dimmed, and a per-card play/pause control allows quick media/audio checking without adding a separate LIVE action. URL, Open, and FILES download behavior remains based on the existing YTCE browser-grid and queued intake foundations; no JDownloader/AppWork source text is copied.

## V81D browser-native Video & Audio polish

- Added an explicit information button for video/audio cards so generic candidate labels do not have to cover the preview.
- Kept persistent video/audio identity records as history, but no longer uses them alone to claim a restarted app has a file currently in the visible FILES list.
- Made browser-side media metadata refresh more robust with loadeddata/canplay hooks and kept the direct FILES intake/download icon flow.

## V81D info icon runtime repair

- Fixed the browser-native Video & Audio grid so the Python-side info icon data URI is embedded before the browser HTML is rendered.
- Keeps the uploaded information icon as an inline browser asset; no external runtime dependency is added.

## V81E browser-native Video & Audio rich discovery refresh and info polish
- Keeps the V81B quick/static-first browser-native Video & Audio opening path, while the open browser window now polls the app for richer rendered/prefetched media candidates and grouped rendition variants.
- Keeps the image-window-style URL/Open/download-icon control layout, brightens the info icon, hides the title overlay while hover controls are visible, and uses the source/page title instead of generic labels such as “file MP4 from source.”
- Source-labelled implementation in `main.py` and `main_source_resource_ui_test.py`.
- 2026-08-22 V81E test fix: updated Video & Audio browser-grid self-test to assert generic media labels fall back to the page/source title instead of requiring the removed `file MP4` label.

## V81F browser-native Video & Audio eager preview buffering and refresh guard

V81F keeps the instant/static-first browser-native Video & Audio window while making the
preview media elements more eager for hover playback.  Browser video/audio preview elements
now use eager preload/load hints, pointer-enter hover playback handlers, and a rendered-refresh
guard so background candidate enrichment does not rebuild cards while a user is hovering or
manually playing a preview.  This preserves the image-window-style responsive feel while still
allowing richer rendered variants to appear once discovery finishes.

## V81G browser-native Video & Audio LinkGrabber-style source precheck

V81G moves generic webpage video/audio discovery closer to JDownloader's LinkGrabber model.  When a source URL is added, YTCE now performs a quick static video/audio precheck first, caches any immediately available candidates for instant browser-native Video & Audio opening, and then continues the slower rendered/richer discovery in the background so dimensions and grouped variants can refresh later.  This preserves the V81B/V81E instant window-open behaviour while making later clicks more likely to open from already-prepared candidates.  This implementation is source-labelled and does not copy JDownloader/AppWork source code.

## V81G source-add self-test wording repair

V81G changes the source-add success message from the older generic metadata-probe wording to mention metadata/media LinkGrabber prechecks.  The self-test now accepts both the older wording and the new V81G wording so the behaviour change is covered without failing on stale log text.
- V81H keeps the browser-native Video & Audio info control visible by removing whole-card reused opacity and boosting the white info icon contrast.
- V81I renders the browser-native Video & Audio info control as a deterministic pure-white CSS icon so reused-card dimming and raster filters cannot dull it.
- V81J restores the browser-native Video & Audio information control to the stable raster icon layout while preserving boosted contrast and non-dimmed controls.
- V81K restores the browser-native Video & Audio top-left control layout by separating the URL text button from the smaller raster information icon button.

- V81L adds browser-native Video & Audio readiness status text for quick/static candidate display and rendered-variant refresh completion.
### YTCE V81L test repair — Video & Audio readiness status assertion

- Repairs a stale self-test assertion left from the earlier Video & Audio browser-grid marker wording.
- The runtime status behaviour remains unchanged; the test now checks the active `YTCEVideoAudioGrid/1.0` browser-grid handler marker.
### YTCE V81L repair 2 — Video & Audio readiness status variable scope

- Moves the V81L initial readiness status variables from the Images browser-grid setup into the Video & Audio browser-grid setup.
- Keeps the runtime Video & Audio status wording unchanged: quick media ready while rendered variants load, then rendered variants loaded after refresh.
- Leaves hover/playback, LinkGrabber precheck, and the top-left Video & Audio controls untouched.

## YTCE V81M Video & Audio rendered refresh active-window guard

- Adds a per-row active browser-window token and source/cache-key signature for the browser-native Video & Audio grid.
- The `/media-items` refresh endpoint now marks older or source-mismatched windows as stale so the browser ignores late rendered refreshes instead of replacing a newer active window/source state.
- Keeps V81L readiness status wording, instant quick-open, hover playback, LinkGrabber precheck, and top-left controls unchanged.

## YTCE V81N Video & Audio stale rendered-refresh trace visibility

- Keeps V81M's stale rendered-refresh guard behaviour unchanged while recording a small diagnostic trace when an older Video & Audio browser window/source refresh is ignored.
- Adds browser-side test/devtools visibility for ignored stale refresh payloads without changing quick-open, rendered refresh handling, hover playback, or the top-left controls.

## YTCE V81O media byte-size display

- Adds a separate browser-grid byte-size label for Images and Video & Audio without blocking window opening or hover playback.
- Keeps dimension probing separate by changing the old pending wording from `Detecting size` to `Detecting dimensions`.
- Uses already-known candidate metadata first, then allows the browser grid to request a local asynchronous HEAD-based byte-size probe after the window has opened.
- Keeps JDownloader/LinkGrabber routing, quick-open behaviour, rendered refresh handling, and card controls unchanged.

V81O repair 2: Browser-grid byte-size probes are signature-safe label-only updates; they do not advance media render signatures after local video dimension metadata changes, preventing Video & Audio card rebuild loops during variant/dimension selection.

V81O repair 3: Video & Audio byte-size results are cached by resource id and URL, reused across MP4 dimension/variant changes, and excluded from media render signatures so size labels do not rebuild video cards or disappear after switching variants.
