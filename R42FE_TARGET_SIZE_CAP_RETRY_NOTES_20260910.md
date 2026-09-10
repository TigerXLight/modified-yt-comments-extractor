# R42FE Target Size Cap Retry

R42FD correctly exposed that target-size mode was still too loose: a bitrate cap could be planned, encoded, and still miss the requested size cap.

R42FE tightens the real path:

- target-size bitrate planning now applies a stronger safety margin for real encoder overshoot;
- target-size `-maxrate` no longer floats to 1.35x above the planned bitrate;
- target-size encodes get a bounded retry path that lowers bitrate if the first pass is still over cap;
- strict audit continues to fail if a target-size cap is not respected;
- WebM/VP9 benchmark remains Opus-based, not AAC-based;
- Optimised keeps the size/time recommendation behaviour from R42FD.

No network, WebView2, or archive.ph access is performed by the smoke/audit scripts.
