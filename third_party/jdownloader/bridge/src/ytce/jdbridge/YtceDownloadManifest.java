package ytce.jdbridge;

public class YtceDownloadManifest {
    public String url = "";
    public String outputDir = "";
    public String packageName = "";
    public int maxHeight = 0;
    public boolean video = false;
    public boolean audio = false;
    public boolean image = false;
    public boolean description = false;
    public boolean probeOnly = false;
    public boolean startRuntime = false;
    public boolean submitJob = false;
    public boolean wait = false;
    public int timeoutSeconds = 0;
    public String vendorRoot = "";
    public String runtimeDir = "";

    public String toJson() {
        StringBuilder sb = new StringBuilder();
        sb.append("{\n");
        append(sb, "backend_id", "jdownloader_internal", true);
        append(sb, "url", url, true);
        append(sb, "output_dir", outputDir, true);
        append(sb, "package_name", packageName, true);
        append(sb, "max_height", String.valueOf(maxHeight), false);
        append(sb, "video", String.valueOf(video), false);
        append(sb, "audio", String.valueOf(audio), false);
        append(sb, "image", String.valueOf(image), false);
        append(sb, "description", String.valueOf(description), false);
        append(sb, "probe_only", String.valueOf(probeOnly), false);
        append(sb, "start_runtime", String.valueOf(startRuntime), false);
        append(sb, "submit_job", String.valueOf(submitJob), false);
        append(sb, "wait", String.valueOf(wait), false);
        append(sb, "timeout_seconds", String.valueOf(timeoutSeconds), false);
        append(sb, "vendor_root", vendorRoot, true);
        append(sb, "runtime_dir", runtimeDir, true);
        append(sb, "status", status(), true);
        append(sb, "job_execution_note", jobExecutionNote(), true);
        sb.append("  \"external_installed_jdownloader_used_as_primary\": false\n");
        sb.append("}\n");
        return sb.toString();
    }

    private String status() {
        if (probeOnly) {
            return "JD_BRIDGE_PROBE_READY";
        }
        if (submitJob || startRuntime) {
            return "JD_BRIDGE_JOB_PATH_UNAVAILABLE";
        }
        return "JD_BRIDGE_MANIFEST_READY";
    }

    private String jobExecutionNote() {
        if (probeOnly) {
            return "Probe only; no runtime start or download job was attempted.";
        }
        if (submitJob || startRuntime) {
            return "Java bridge parsed the V28 job command shape, but Python owns runtime startup, CNL submission, and output monitoring in this pass.";
        }
        return "Manifest command shape only; no download success is claimed.";
    }

    private static void append(StringBuilder sb, String key, String value, boolean quote) {
        sb.append("  \"").append(escape(key)).append("\": ");
        if (quote) {
            sb.append("\"").append(escape(value)).append("\"");
        } else {
            sb.append(value);
        }
        sb.append(",\n");
    }

    private static String escape(String value) {
        String text = value == null ? "" : value;
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < text.length(); i++) {
            char ch = text.charAt(i);
            if (ch == '\\' || ch == '"') {
                sb.append('\\');
            }
            if (ch == '\n') {
                sb.append("\\n");
            } else if (ch == '\r') {
                sb.append("\\r");
            } else {
                sb.append(ch);
            }
        }
        return sb.toString();
    }
}
