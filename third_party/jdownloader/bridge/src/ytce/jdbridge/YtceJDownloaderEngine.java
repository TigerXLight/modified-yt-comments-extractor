package ytce.jdbridge;

import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.io.Writer;

public class YtceJDownloaderEngine {
    public static void main(String[] args) throws Exception {
        YtceYoutubeDownloadCommand command = YtceYoutubeDownloadCommand.parse(args);
        YtceDownloadManifest manifest = new YtceDownloadManifest();
        manifest.url = command.url;
        manifest.outputDir = command.outputDir;
        manifest.packageName = command.packageName;
        manifest.maxHeight = command.maxHeight;
        manifest.video = command.video;
        manifest.audio = command.audio;
        manifest.image = command.image;
        manifest.description = command.description;
        manifest.probeOnly = command.probeOnly;
        manifest.startRuntime = command.startRuntime;
        manifest.submitJob = command.submitJob;
        manifest.wait = command.wait;
        manifest.timeoutSeconds = command.timeoutSeconds;
        File cwd = new File(".").getCanonicalFile();
        manifest.vendorRoot = new File(cwd, "third_party/jdownloader").getPath();
        manifest.runtimeDir = new File(cwd, "third_party/jdownloader/runtime/JDownloader 2").getPath();

        String json = manifest.toJson();
        if (command.manifestPath != null && command.manifestPath.length() > 0) {
            File target = new File(command.manifestPath);
            File parent = target.getParentFile();
            if (parent != null) {
                parent.mkdirs();
            }
            Writer writer = new OutputStreamWriter(new FileOutputStream(target), "UTF-8");
            try {
                writer.write(json);
            } finally {
                writer.close();
            }
        }
        System.out.print(json);
    }
}
