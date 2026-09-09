# R42EX real capability/process and cog fix

- Treat FFmpeg encoder list as compiled capability only, not proof that current GPU can run it.
- Add tiny runnable encoder probes and cache them for Optimised video selection.
- Prevent selected encoder metadata from disagreeing with the actual `-c:v` command.
- Add hardware AV1 command handling so `av1_amf`/NVENC/QSV/MF/Vulkan do not silently fall back to `libx264` while reporting AV1.
- Strengthen File Converter cog first-paint visibility by using the darker cog colour immediately.
- Add a fuller no-network audit that runs text/image/audio, video remux, and one video compression path when a runnable encoder exists.
