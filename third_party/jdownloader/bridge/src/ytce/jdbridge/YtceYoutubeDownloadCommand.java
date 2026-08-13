package ytce.jdbridge;

public class YtceYoutubeDownloadCommand {
    public String url = "";
    public String outputDir = "";
    public String packageName = "";
    public int maxHeight = 1080;
    public boolean video = false;
    public boolean audio = false;
    public boolean image = false;
    public boolean description = false;
    public boolean probeOnly = false;
    public boolean startRuntime = false;
    public boolean submitJob = false;
    public boolean wait = false;
    public int timeoutSeconds = 0;
    public String manifestPath = "";

    public static YtceYoutubeDownloadCommand parse(String[] args) {
        YtceYoutubeDownloadCommand cmd = new YtceYoutubeDownloadCommand();
        for (int i = 0; i < args.length; i++) {
            String arg = args[i];
            if ("--url".equals(arg) && i + 1 < args.length) {
                cmd.url = args[++i];
            } else if ("--output-dir".equals(arg) && i + 1 < args.length) {
                cmd.outputDir = args[++i];
            } else if ("--package-name".equals(arg) && i + 1 < args.length) {
                cmd.packageName = args[++i];
            } else if ("--max-height".equals(arg) && i + 1 < args.length) {
                cmd.maxHeight = parseInt(args[++i], 1080);
            } else if ("--manifest".equals(arg) && i + 1 < args.length) {
                cmd.manifestPath = args[++i];
            } else if ("--video".equals(arg)) {
                cmd.video = true;
            } else if ("--audio".equals(arg)) {
                cmd.audio = true;
            } else if ("--image".equals(arg)) {
                cmd.image = true;
            } else if ("--description".equals(arg)) {
                cmd.description = true;
            } else if ("--probe-only".equals(arg)) {
                cmd.probeOnly = true;
            } else if ("--start-runtime".equals(arg)) {
                cmd.startRuntime = true;
            } else if ("--submit-job".equals(arg)) {
                cmd.submitJob = true;
            } else if ("--wait".equals(arg)) {
                cmd.wait = true;
            } else if ("--timeout-seconds".equals(arg) && i + 1 < args.length) {
                cmd.timeoutSeconds = parseInt(args[++i], 0);
            }
        }
        return cmd;
    }

    private static int parseInt(String value, int fallback) {
        try {
            return Integer.parseInt(value);
        } catch (Throwable ignored) {
            return fallback;
        }
    }
}
