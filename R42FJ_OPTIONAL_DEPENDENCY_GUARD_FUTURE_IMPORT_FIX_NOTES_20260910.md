# R42FJ optional dependency guard future-import fix

Repairs the failed R42FI insertion by placing optional dependency SkipTest guards after any from __future__ imports.

Guards optional ASR tests on faster_whisper and optional WARC/archive tests on warcio. If the dependency is installed, tests run normally. If absent, unittest reports SKIPPED instead of ERROR.

No production runtime code changed.
