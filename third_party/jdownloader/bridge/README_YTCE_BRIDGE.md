# YTCE JDownloader bridge

`ytce.jdbridge.YtceJDownloaderEngine` is a small project-owned Java CLI bridge.
It compiles independently before the heavier JDownloader integration.

Current behaviour:

- parses command-line arguments
- supports probe mode
- writes JSON manifests
- reports project-local vendor/source/runtime paths
- never calls the external installed JDownloader GUI

Next integration layer can load or launch project-local JDownloader runtime
components from `third_party/jdownloader/runtime/JDownloader 2/`.
