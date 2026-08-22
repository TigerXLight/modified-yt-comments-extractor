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
