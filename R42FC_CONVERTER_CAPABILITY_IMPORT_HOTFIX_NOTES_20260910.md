# R42FC - Converter capability import hotfix

Fixes the R42FB smoke failure caused by loading `profile_media_file_converter_r42eh.py` with `importlib.util.module_from_spec(...)` without inserting the module into `sys.modules` before `exec_module(...)`.

That import style breaks dataclass initialisation on Python 3.11 with `AttributeError("'NoneType' object has no attribute '__dict__'")`.

R42FC keeps the R42FB end-to-end capability matrix goal:

- structure/functionality no-network audit
- CPU/RAM/GPU capability profile
- compiled encoder vs runnable encoder separation
- optional synthetic benchmark
- text/image/audio/video pipeline checks
- remux/copy vs compression/transcode checks
- target-size behaviour checks
- selected encoder vs actual `-c:v` command alignment checks

The implementation change is deliberately narrow: fix the test/audit loader and keep the R42FB backend/UI code intact.
