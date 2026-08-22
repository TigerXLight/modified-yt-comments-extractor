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

## V80N Profile/Media Database runtime queue bridge

V80N adds `profile_media_database_runtime_queue.py`, a Python/Tk-native queued
operation bridge for Profile/Media Database file-management work.

Source patterns reviewed from the uploaded JDownloader/AppWork reference set:

- `org.appwork.utils.event.queue.Queue`
- `org.appwork.utils.event.queue.QueueAction`
- `org.appwork.utils.event.queue.QueueThread`
- `jd.controlling.downloadcontroller.DownloadWatchDogJob`
- `jd.controlling.downloadcontroller.DownloadWatchDog`

The implementation uses the V80M YTCE runtime queue foundation and does not copy
Java source text directly. It preserves the source-pattern labels and maps the
same queue/job/watchdog semantics into Python-native code.

## V80O: Media operation watchdog

V80O adds `media_operation_watchdog.py`, a Python/Tk media/probe/download watchdog based on
JDownloader/AppWork runtime patterns reviewed from:

- `jd.controlling.downloadcontroller.DownloadWatchDog`
- `jd.controlling.downloadcontroller.DownloadWatchDogJob`
- `org.appwork.utils.event.queue.Queue`
- `org.appwork.utils.event.queue.QueueAction`
- `org.appwork.utils.event.queue.QueueThread`

Implementation mapping:

- JDownloader `DownloadWatchDog` / watchdog job lifecycle → `MediaOperationWatchdog` operation registry, heartbeats, stall detection, timeout detection, and isolated cancel callbacks.
- AppWork queue job execution → optional `YTCEWorkQueue` integration for watched off-UI-thread media operations.

This is a source-credited Python implementation of the reviewed watchdog/job/control-flow behaviour.
