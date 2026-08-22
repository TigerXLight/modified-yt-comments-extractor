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
