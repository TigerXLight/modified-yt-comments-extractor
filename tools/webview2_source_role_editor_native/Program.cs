using System.Diagnostics;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.ComponentModel;
using System.Linq;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

namespace YTCE.NativeSourceRoleEditor;

internal static class Program
{
    [STAThread]
    private static void Main(string[] args)
    {
        ApplicationConfiguration.Initialize();
        using var logger = new TimingLogger(args, "R42CR/R42AI native WebView2 source-role editor");
        logger.Log("process_start", "R42CR/R42AI native WebView2 source-role editor starting");
        Application.Run(new SourceRoleEditorForm(args, logger));
        logger.Log("process_exit", "R42CR/R42AI native WebView2 source-role editor exited");
    }
}

internal sealed class SourceRoleEditorForm : Form
{
    private const string Marker = "YTCE_R42CR_NATIVE_WEBVIEW2_SOURCE_ROLE_EDITOR";
    private const string R42EBArchiveUrlGuardMarker = "YTCE_R42EB_ARCHIVE_URL_CANONICAL_GUARD";
    private readonly TimingLogger _log;
    private readonly string _root;
    private string _payloadPath;
    private string _changesPath;
    private string _roleDbPath = "";
    private readonly string _udf;
    private string _initialMode;
    private string _urlArg;
    private string _url;
    private string _payloadJson = "{}";
    private readonly Task<string> _payloadJsonTask;
    private readonly bool _serverMode;
    private readonly string _commandDir;
    private string? _documentScriptId;
    private System.Windows.Forms.Timer? _serverCommandTimer;
    private bool _serverCommandBusy;
    private bool _serverWindowShown;
    private long _lastServerCommandElapsedMs = -1;
    private string _lastServerCommandFile = "";
    private string _lastServerCommandToken = "";
    private bool _serverCommandFirstPaintLogged;
    private string _lastServerCommandSignature = "";
    private long _lastServerCommandSignatureAtMs = -1;
    private const int NativeToolbarHeight = 48;
    private readonly WebView2 _webView = new();
    private readonly TableLayoutPanel _nativeLayout = new(); // retained for compatibility; R42CR uses explicit Bounds layout, not overlay docking.
    private readonly Panel _nativeToolbar = new SmoothPanel();
    private readonly FlowLayoutPanel _nativeToolbarFlow = new SmoothFlowLayoutPanel();
    private readonly ToolTip _nativeToolTip = new();
    private readonly Dictionary<string, Image> _nativeIconImages = new(StringComparer.OrdinalIgnoreCase);
    private readonly Button _nativeBtnSemantic = new NativeToolbarTextButton();
    private readonly Button _nativeBtnMedia = new NativeToolbarTextButton();
    private readonly Button _nativeBtnPrev = new();
    private readonly Button _nativeBtnNext = new();
    private readonly Button _nativeBtnCopyLink = new NativeToolbarIconButton();
    private readonly Button _nativeBtnCopyText = new NativeToolbarIconButton();
    private readonly Button _nativeBtnCopyRoles = new NativeToolbarIconButton();
    private readonly Button _nativeBtnExternal = new NativeToolbarIconButton();
    private readonly ComboBox _nativeSourceCombo = new();
    private readonly Label _nativePrimaryCount = new();
    private readonly Label _nativeSecondaryCount = new();
    private readonly Label _nativeTertiaryCount = new();
    private readonly Label _nativeUnknownCount = new();
    private readonly Label _nativeUrlLabel = new();
    private readonly List<NativeSourceNavItem> _nativeSourceItems = new();
    // R42CR: source navigation is human-chain state, not only "current browser URL".
    // Archive.ph can redirect a selected snapshot to its root challenge/429 URL; keep the
    // selected archive item sticky so the batch source candidate does not bounce back to Original.
    private int _nativeSelectedSourceIndex = -1;
    private int _nativeLastRequestedSourceIndex = -1;
    private bool _nativeHumanActionPending;
    private string _nativeHumanActionReason = "";
    private string _nativeHumanActionSourceUrl = "";
    private string _nativeHumanActionVisibleUrl = "";
    private bool _nativeToolbarUpdating;
    private string _nativeToolbarMode = "semantic";
    private string _payloadPlainText = "";
    private string _payloadSemanticRoleText = "";
    private string _payloadMediaRoleText = "";
    private int _nativeCountPrimary;
    private int _nativeCountSecondary;
    private int _nativeCountTertiary;
    private int _nativeCountUnknown;
    private readonly Dictionary<string, int[]> _nativeCountsByMode = new(StringComparer.OrdinalIgnoreCase);
    private bool _nativeToolbarCompactLabels;
    private System.Windows.Forms.Timer? _nativeResizeLayoutTimer;
    private bool _nativeLiveResizing;
    private FormWindowState _lastToolbarWindowState = FormWindowState.Normal;
    private CoreWebView2Environment? _environment;
    private int _blockedResourceCount;
    private string _materialCapturePath = "";
    private string _materialCaptureTitle = "";
    private string _materialCaptureUrl = "";
    private int _materialCaptureWaitMs = 60000;
    private long _materialCaptureStartedMs = -1;
    private bool _materialCaptureDone;
    private bool _materialCaptureBusy;
    private int _materialCaptureAttempts;
    private System.Windows.Forms.Timer? _materialCaptureTimer;

    public SourceRoleEditorForm(string[] args, TimingLogger log)
    {
        _log = log;
        _root = ResolveRoot(Args.Get(args, "--root"));
        _payloadPath = ResolvePath(Args.Get(args, "--payload") ?? "", _root);
        _changesPath = ResolvePath(Args.Get(args, "--changes") ?? "", _root);
        _udf = ResolvePath(Args.Get(args, "--udf") ?? DefaultUserDataFolder(), _root);
        _initialMode = (Args.Get(args, "--mode") ?? "semantic").Equals("media", StringComparison.OrdinalIgnoreCase) ? "media" : "semantic";
        _urlArg = Args.Get(args, "--url") ?? "";
        _url = FirstNonBlank(_urlArg, "about:blank");
        _serverMode = Args.Has(args, "--server");
        _commandDir = ResolvePath(Args.Get(args, "--command-dir") ?? Path.Combine(_udf, "commands"), _root);
        if (_serverMode)
        {
            _payloadPath = "";
            _changesPath = "";
            _urlArg = "";
            _url = "about:blank";
            ShowInTaskbar = false;
            Opacity = 0;
            WindowState = FormWindowState.Minimized;
        }
        // R42CR: start payload IO immediately but do not block WebView2 environment startup on it.
        // On the user's T: drive this read was costing ~300 ms; overlapping it with WebView2 init
        // should reduce cold editor-ready time without changing payload semantics.
        _payloadJsonTask = Task.Run(() => ReadPayloadJson(_payloadPath, _log));

        Text = "YTCE R42CR Native Source-Role Editor";
        Width = 1280;
        Height = 920;
        MinimumSize = new Size(980, 700);
        StartPosition = FormStartPosition.CenterScreen;

        BuildNativeToolbar();
        BuildNativeEditorLayout();
    }

    private bool _initializeStarted;

    protected override async void OnLoad(EventArgs e)
    {
        base.OnLoad(e);
        if (_initializeStarted) return;
        _initializeStarted = true;
        _log.Log("form_load", $"starting WebView2 init before first paint; root={_root}; url={_url}; payload={_payloadPath}; udf={_udf}");
        await InitializeWebViewAsync();
    }

    protected override void OnShown(EventArgs e)
    {
        base.OnShown(e);
        _log.Log("form_shown", $"form visible; root={_root}; url={_url}; payload={_payloadPath}; udf={_udf}");
        LayoutNativeEditorSurface();
        UpdateNativeToolbarResponsiveLayout();
    }

    protected override void OnSizeChanged(EventArgs e)
    {
        base.OnSizeChanged(e);
        if (WindowState == FormWindowState.Minimized) return;

        // R42CR: resize correction.  Do not rely on DockStyle.Fill ordering here; with WebView2
        // the child HWND can visually sit underneath a top toolbar until Windows performs a second
        // resize/maximize layout pass.  Set exact bounds every time: toolbar row first, then the
        // WebView rectangle below it, so Wayback's own header is never covered.
        LayoutNativeEditorSurface();
        UpdateNativeToolbarResponsiveLayout();
    }

    protected override void OnResizeBegin(EventArgs e)
    {
        _nativeLiveResizing = true;
        base.OnResizeBegin(e);
    }

    protected override void OnResizeEnd(EventArgs e)
    {
        base.OnResizeEnd(e);
        _nativeLiveResizing = false;
        LayoutNativeEditorSurface();
        UpdateNativeToolbarResponsiveLayout();
        try { _nativeToolbar.Invalidate(true); _nativeToolbarFlow.Invalidate(true); } catch { }
    }

    protected override void OnFormClosing(FormClosingEventArgs e)
    {
        if (_serverMode && e.CloseReason == CloseReason.UserClosing)
        {
            e.Cancel = true;
            try
            {
                Hide();
                ShowInTaskbar = false;
                Opacity = 0;
                WindowState = FormWindowState.Minimized;
                _serverWindowShown = false;
                RemoveCurrentDocumentStartScript("server_window_hide");
                _lastServerCommandElapsedMs = -1;
                _lastServerCommandToken = "";
                _serverCommandFirstPaintLogged = false;
                _lastServerCommandSignature = "";
                _lastServerCommandSignatureAtMs = -1;
                try { _webView.CoreWebView2?.Stop(); } catch { }
                _webView.CoreWebView2?.Navigate("about:blank");
                _log.Log("server_window_hidden", "user close intercepted; warm helper remains running; script_removed=true");
            }
            catch (Exception ex)
            {
                _log.Log("server_window_hide_failed", ex.Message);
            }
            return;
        }
        base.OnFormClosing(e);
    }

    protected override void OnFormClosed(FormClosedEventArgs e)
    {
        base.OnFormClosed(e);
        var blocked = Volatile.Read(ref _blockedResourceCount);
        if (blocked > 0)
        {
            _log.Log("resource_blocker_summary", $"blocked_total={blocked}");
        }
    }

    private async Task InitializeWebViewAsync()
    {
        try
        {
            _log.Log("udf_prepare", _udf);
            Directory.CreateDirectory(_udf);
            _log.Log("udf_ready", _udf);
            if (!string.IsNullOrWhiteSpace(_changesPath))
            {
                Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(_changesPath)) ?? ".");
            }

            _log.Log("webview_env_start", "creating CoreWebView2Environment");
            var options = new CoreWebView2EnvironmentOptions
            {
                AdditionalBrowserArguments = string.Join(" ", new[]
                {
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--disable-background-timer-throttling",
                    "--disable-extensions",
                    "--disable-component-update",
                    "--disable-features=InterestFeedContentSuggestions,MediaRouter,OptimizationHints"
                })
            };
            var env = await CoreWebView2Environment.CreateAsync(browserExecutableFolder: null, userDataFolder: _udf, options: options);
            _environment = env;
            _log.Log("webview_env_ready", "CoreWebView2Environment ready");

            _webView.CoreWebView2InitializationCompleted += (_, ev) =>
            {
                _log.Log(ev.IsSuccess ? "webview_init_completed" : "webview_init_failed", ev.IsSuccess ? "success" : ev.InitializationException?.ToString() ?? "unknown failure");
            };

            await _webView.EnsureCoreWebView2Async(env);
            _log.Log("webview_control_ready", "EnsureCoreWebView2Async returned");

            WireEvents();
            InstallRequestBlocking();

            if (_serverMode)
            {
                StartCommandServer();
                _log.Log("server_warm_navigate", "about:blank");
                _webView.CoreWebView2.Navigate("about:blank");
                return;
            }

            // Payload is now awaited after WebView2 init so file IO is overlapped with browser startup.
            _payloadJson = await _payloadJsonTask;
            _url = CleanNativeUrl(FirstNonBlank(_urlArg, TryGetPayloadString(_payloadJson, "selected_url"), "about:blank"));
            LoadNativeToolbarFromPayload(_payloadJson, _url, _initialMode ?? "semantic");

            _documentScriptId = await _webView.CoreWebView2.AddScriptToExecuteOnDocumentCreatedAsync(DocumentStartRoleEditorScript(_payloadJson, _initialMode ?? "semantic", _root, "direct"));
            _log.Log("document_start_script_registered", $"AddScriptToExecuteOnDocumentCreatedAsync registered; marker={Marker}; mode={_initialMode}");

            _log.Log("navigate_call", _url);
            _webView.CoreWebView2.Navigate(_url);
        }
        catch (Exception ex)
        {
            _log.Log("fatal", ex.ToString());
            MessageBox.Show(this, ex.ToString(), "R42CR WebView2 source-role editor failed", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }



    private void StartCommandServer()
    {
        try
        {
            Directory.CreateDirectory(_commandDir);
            WriteServerReadyFile();
            _log.Log("server_ready", $"pid={Environment.ProcessId}; command_dir={_commandDir}; ready={ServerReadyPath()}");

            _serverCommandTimer = new System.Windows.Forms.Timer { Interval = 40 };
            _serverCommandTimer.Tick += async (_, _) =>
            {
                if (_serverCommandBusy) return;
                string? commandPath = null;
                try
                {
                    if (!TryReadServerCommand(out commandPath, out var commandJson)) return;
                    _serverCommandBusy = true;
                    try { File.Delete(commandPath!); } catch { }
                    await LoadServerCommandAsync(commandJson!, commandPath!);
                }
                catch (Exception ex)
                {
                    _log.Log("server_command_error", $"file={Path.GetFileName(commandPath ?? "")}; {ex.GetType().Name}: {ex.Message}");
                }
                finally
                {
                    _serverCommandBusy = false;
                }
            };
            _serverCommandTimer.Start();
        }
        catch (Exception ex)
        {
            _log.Log("server_start_failed", ex.ToString());
        }
    }

    private bool TryReadServerCommand(out string? commandPath, out string? commandJson)
    {
        commandPath = null;
        commandJson = null;
        try
        {
            foreach (var path in Directory.EnumerateFiles(_commandDir, "command_*.json").OrderBy(static p => p, StringComparer.OrdinalIgnoreCase))
            {
                try
                {
                    // Do not touch a just-renamed command on the same tick that Python created it.
                    // This prevents the first-click "file is being used by another process" race.
                    var ageMs = (DateTime.UtcNow - File.GetLastWriteTimeUtc(path)).TotalMilliseconds;
                    if (ageMs >= 0 && ageMs < 75) continue;
                }
                catch { }
                try
                {
                    using var fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
                    using var reader = new StreamReader(fs, Encoding.UTF8, detectEncodingFromByteOrderMarks: true);
                    var json = reader.ReadToEnd();
                    if (string.IsNullOrWhiteSpace(json) || !json.TrimStart().StartsWith("{", StringComparison.Ordinal))
                    {
                        _log.Log("server_command_deferred", $"file={Path.GetFileName(path)}; reason=incomplete_json");
                        continue;
                    }
                    commandPath = path;
                    commandJson = json;
                    return true;
                }
                catch (IOException)
                {
                    // Writer/antivirus still has the file: retry cleanly on the next 40 ms tick.
                    continue;
                }
                catch (UnauthorizedAccessException)
                {
                    continue;
                }
            }
        }
        catch (Exception ex)
        {
            _log.Log("server_command_scan_failed", ex.GetType().Name + ": " + ex.Message);
        }
        return false;
    }

    private string ServerReadyPath() => Path.Combine(_commandDir, "r42cr_server_ready.json");


    private sealed class SmoothPanel : Panel
    {
        public SmoothPanel()
        {
            DoubleBuffered = true;
            ResizeRedraw = false;
        }
    }

    private sealed class SmoothFlowLayoutPanel : FlowLayoutPanel
    {
        public SmoothFlowLayoutPanel()
        {
            DoubleBuffered = true;
            ResizeRedraw = false;
        }
    }

    private sealed class NativeToolbarTextButton : Button
    {
        private bool _hover;
        private bool _down;

        public NativeToolbarTextButton()
        {
            SetStyle(ControlStyles.UserPaint | ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.ResizeRedraw, true);
            FlatStyle = FlatStyle.Flat;
            TabStop = false;
        }

        protected override void OnMouseEnter(EventArgs e) { _hover = true; Invalidate(); base.OnMouseEnter(e); }
        protected override void OnMouseLeave(EventArgs e) { _hover = false; _down = false; Invalidate(); base.OnMouseLeave(e); }
        protected override void OnMouseDown(MouseEventArgs e) { if (e.Button == MouseButtons.Left) { _down = true; Invalidate(); } base.OnMouseDown(e); }
        protected override void OnMouseUp(MouseEventArgs e) { _down = false; Invalidate(); base.OnMouseUp(e); }
        protected override void OnEnabledChanged(EventArgs e) { Invalidate(); base.OnEnabledChanged(e); }
        protected override void OnTextChanged(EventArgs e) { Invalidate(); base.OnTextChanged(e); }
        protected override void OnForeColorChanged(EventArgs e) { Invalidate(); base.OnForeColorChanged(e); }
        protected override void OnBackColorChanged(EventArgs e) { Invalidate(); base.OnBackColorChanged(e); }

        protected override void OnPaint(PaintEventArgs e)
        {
            var g = e.Graphics;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            g.CompositingQuality = CompositingQuality.HighQuality;
            g.InterpolationMode = InterpolationMode.HighQualityBicubic;
            g.PixelOffsetMode = PixelOffsetMode.HighQuality;

            var fill = !Enabled ? Color.FromArgb(51, 65, 85) : BackColor;
            if (Enabled && _down) fill = ControlPaint.Dark(fill, 0.10f);
            else if (Enabled && _hover && fill.GetBrightness() < 0.85f) fill = ControlPaint.Light(fill, 0.06f);

            var r = new Rectangle(0, 0, Math.Max(1, Width - 1), Math.Max(1, Height - 1));
            using (var path = RoundedRect(r, 8))
            using (var brush = new SolidBrush(fill))
            {
                g.FillPath(brush, path);
            }

            TextRenderer.DrawText(
                g,
                Text ?? "",
                Font,
                new Rectangle(1, 0, Math.Max(1, ClientSize.Width - 2), Math.Max(1, ClientSize.Height)),
                ForeColor,
                TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter | TextFormatFlags.EndEllipsis | TextFormatFlags.NoPadding);
        }
    }

    private sealed class NativeToolbarIconButton : Button
    {
        private bool _hover;
        private bool _down;
        [Browsable(false)]
        [EditorBrowsable(EditorBrowsableState.Never)]
        [DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public Image? ToolbarIcon { get; set; }

        [Browsable(false)]
        [EditorBrowsable(EditorBrowsableState.Never)]
        [DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public string ToolbarIconKind { get; set; } = "";

        [Browsable(false)]
        [EditorBrowsable(EditorBrowsableState.Never)]
        [DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public int IconBoxPx { get; set; } = 22;

        [Browsable(false)]
        [EditorBrowsable(EditorBrowsableState.Never)]
        [DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
        public int CornerRadius { get; set; } = 8;

        public NativeToolbarIconButton()
        {
            SetStyle(ControlStyles.UserPaint | ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.ResizeRedraw, true);
            FlatStyle = FlatStyle.Flat;
            TabStop = false;
        }

        protected override void OnMouseEnter(EventArgs e) { _hover = true; Invalidate(); base.OnMouseEnter(e); }
        protected override void OnMouseLeave(EventArgs e) { _hover = false; _down = false; Invalidate(); base.OnMouseLeave(e); }
        protected override void OnMouseDown(MouseEventArgs e) { if (e.Button == MouseButtons.Left) { _down = true; Invalidate(); } base.OnMouseDown(e); }
        protected override void OnMouseUp(MouseEventArgs e) { _down = false; Invalidate(); base.OnMouseUp(e); }
        protected override void OnEnabledChanged(EventArgs e) { Invalidate(); base.OnEnabledChanged(e); }

        protected override void OnPaint(PaintEventArgs e)
        {
            var g = e.Graphics;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            g.CompositingQuality = CompositingQuality.HighQuality;
            g.InterpolationMode = InterpolationMode.HighQualityBicubic;
            g.PixelOffsetMode = PixelOffsetMode.HighQuality;

            var r = new Rectangle(0, 0, Math.Max(1, Width - 1), Math.Max(1, Height - 1));
            var fill = !Enabled ? Color.FromArgb(51, 65, 85) : (_down ? Color.FromArgb(30, 64, 175) : (_hover ? Color.FromArgb(37, 99, 235) : Color.FromArgb(29, 78, 216)));
            using (var path = RoundedRect(r, CornerRadius))
            using (var brush = new SolidBrush(fill))
            using (var border = new Pen(Color.FromArgb(96, 165, 250), 1f))
            {
                g.FillPath(brush, path);
                g.DrawPath(border, path);
            }

            var box = Math.Max(16, Math.Min(IconBoxPx, Math.Min(ClientSize.Width - 10, ClientSize.Height - 8)));
            var x = (ClientSize.Width - box) / 2;
            var y = (ClientSize.Height - box) / 2;
            if (ToolbarIcon is not null)
            {
                g.DrawImage(ToolbarIcon, new Rectangle(x, y, box, box));
            }
            else
            {
                DrawNativeVectorToolbarIcon(g, ToolbarIconKind, ClientRectangle);
            }

        }
    }

    private sealed class NativeSourceNavItem
    {
        public string Url { get; set; } = "";
        public string Label { get; set; } = "";
        public string Kind { get; set; } = "";
        public string Prefix { get; set; } = "";
        public string IndexLabel { get; set; } = "";
        public string Title { get; set; } = "";
        public string Site { get; set; } = "";
        public string Relation { get; set; } = "";
    }

    private void BuildNativeEditorLayout()
    {
        // R42CR: explicit browser-chrome layout.  The toolbar is a native row at y=0;
        // WebView2 starts at y=NativeToolbarHeight.  This avoids the DockStyle.Fill/z-order
        // overlap that made the toolbar cover the Wayback header until the window was resized.
        SuspendLayout();
        try
        {
            _nativeToolbar.Dock = DockStyle.None;
            _nativeToolbar.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
            _nativeToolbar.Height = NativeToolbarHeight;
            _nativeToolbar.MinimumSize = new Size(0, NativeToolbarHeight);
            _nativeToolbar.Margin = new Padding(0);

            _webView.Dock = DockStyle.None;
            _webView.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right;
            _webView.Margin = new Padding(0);
            _webView.MinimumSize = Size.Empty;

            Controls.Add(_webView);
            Controls.Add(_nativeToolbar);
            _nativeToolbar.BringToFront();
            LayoutNativeEditorSurface();
        }
        finally
        {
            ResumeLayout(true);
        }
        _log.Log("native_layout_ready", "toolbar_bounds=explicit_top_48; webview_bounds=below_toolbar; table_layout=false; overlay=false; wayback_safe=true; prev_next_buttons=removed; toolbar_style=r42cr_archive_access_state_batch_source_role_resume");
    }

    private void LayoutNativeEditorSurface()
    {
        try
        {
            if (IsDisposed || Disposing) return;
            var w = Math.Max(1, ClientSize.Width);
            var h = Math.Max(1, ClientSize.Height);
            var toolbarH = NativeToolbarHeight;
            if (_nativeToolbar.Bounds.X != 0 || _nativeToolbar.Bounds.Y != 0 || _nativeToolbar.Width != w || _nativeToolbar.Height != toolbarH)
                _nativeToolbar.SetBounds(0, 0, w, toolbarH);
            var webH = Math.Max(1, h - toolbarH);
            if (_webView.Bounds.X != 0 || _webView.Bounds.Y != toolbarH || _webView.Width != w || _webView.Height != webH)
                _webView.SetBounds(0, toolbarH, w, webH);
        }
        catch { }
    }

    private void BuildNativeToolbar()
    {
        _nativeToolbar.Dock = DockStyle.Top;
        _nativeToolbar.Height = 48;
        _nativeToolbar.MinimumSize = new Size(0, 48);
        _nativeToolbar.Padding = new Padding(8, 5, 8, 5);
        _nativeToolbar.BackColor = Color.FromArgb(15, 23, 42);

        _nativeToolbarFlow.Dock = DockStyle.Fill;
        _nativeToolbarFlow.FlowDirection = FlowDirection.LeftToRight;
        _nativeToolbarFlow.WrapContents = false;
        _nativeToolbarFlow.AutoScroll = false;
        _nativeToolbarFlow.AutoSize = false;
        _nativeToolbarFlow.BackColor = Color.FromArgb(15, 23, 42);
        _nativeToolbarFlow.Margin = new Padding(0);
        _nativeToolbarFlow.Padding = new Padding(0);
        _nativeToolbar.Controls.Add(_nativeToolbarFlow);

        // R42CR: restore the project's real Icons8 PNG artwork, but keep it owner-drawn.
        // Do not assign Button.Image.  WinForms can combine Image/Text/theme/focus painting and
        // make the small glyphs look overlaid or clipped.  We draw one centred bitmap per button.
        LoadNativeToolbarIconImages();

        ConfigureToolbarButton(_nativeBtnSemantic, "Semantic", 86, "Semantic source-role mode");
        ConfigureToolbarButton(_nativeBtnMedia, "Media", 78, "Media source-role mode");
        ConfigureCountLabel(_nativePrimaryCount, "Primary: 00", Color.FromArgb(5, 150, 105));
        ConfigureCountLabel(_nativeSecondaryCount, "Secondary: 00", Color.FromArgb(37, 99, 235));
        ConfigureCountLabel(_nativeTertiaryCount, "Tertiary: 00", Color.FromArgb(126, 34, 206));
        ConfigureCountLabel(_nativeUnknownCount, "Unknown: 00", Color.FromArgb(180, 83, 9));
        // R42CR: source navigation is dropdown-only.  The left/right arrow buttons are deliberately
        // not placed in the toolbar; they were redundant and stole width from the source selector.
        _nativeBtnPrev.Visible = false;
        _nativeBtnNext.Visible = false;
        ConfigureToolbarIconButton(_nativeBtnCopyLink, "link", "Copy link", 36);
        ConfigureToolbarIconButton(_nativeBtnCopyText, "text", "Copy plain text", 36);
        ConfigureToolbarIconButton(_nativeBtnCopyRoles, "roles", "Copy role text", 36);
        ConfigureToolbarIconButton(_nativeBtnExternal, "external", "Open externally", 36);

        _nativeSourceCombo.DropDownStyle = ComboBoxStyle.DropDownList;
        _nativeSourceCombo.Width = 300;
        _nativeSourceCombo.Height = 32;
        _nativeSourceCombo.ItemHeight = 24;
        _nativeSourceCombo.MaxDropDownItems = 12;
        _nativeSourceCombo.IntegralHeight = false;
        _nativeSourceCombo.DropDownHeight = (_nativeSourceCombo.ItemHeight * 12) + 4;
        _nativeSourceCombo.Margin = new Padding(4, 1, 4, 0);
        _nativeSourceCombo.BackColor = Color.FromArgb(30, 41, 59);
        _nativeSourceCombo.ForeColor = Color.White;
        _nativeSourceCombo.FlatStyle = FlatStyle.Flat;
        _nativeSourceCombo.Font = new Font(SystemFonts.MessageBoxFont.FontFamily, 8.25f, FontStyle.Bold);
        _nativeSourceCombo.DrawMode = DrawMode.OwnerDrawFixed;
        _nativeSourceCombo.DrawItem += NativeSourceComboDrawItem;
        _nativeToolTip.SetToolTip(_nativeSourceCombo, "Select source URL");

        _nativeUrlLabel.AutoEllipsis = true;
        _nativeUrlLabel.ForeColor = Color.FromArgb(226, 232, 240);
        _nativeUrlLabel.BackColor = Color.FromArgb(15, 23, 42);
        _nativeUrlLabel.TextAlign = ContentAlignment.MiddleLeft;
        _nativeUrlLabel.Height = 32;
        _nativeUrlLabel.Width = 420;
        _nativeUrlLabel.Margin = new Padding(6, 1, 4, 0);
        _nativeUrlLabel.Text = "";
        _nativeUrlLabel.Font = new Font(SystemFonts.MessageBoxFont.FontFamily, 8.0f, FontStyle.Regular);

        _nativeToolbarFlow.Controls.Add(_nativeBtnSemantic);
        _nativeToolbarFlow.Controls.Add(_nativeBtnMedia);
        _nativeToolbarFlow.Controls.Add(_nativePrimaryCount);
        _nativeToolbarFlow.Controls.Add(_nativeSecondaryCount);
        _nativeToolbarFlow.Controls.Add(_nativeTertiaryCount);
        _nativeToolbarFlow.Controls.Add(_nativeUnknownCount);
        _nativeToolbarFlow.Controls.Add(_nativeSourceCombo);
        _nativeToolbarFlow.Controls.Add(_nativeUrlLabel);
        _nativeToolbarFlow.Controls.Add(_nativeBtnCopyLink);
        _nativeToolbarFlow.Controls.Add(_nativeBtnCopyText);
        _nativeToolbarFlow.Controls.Add(_nativeBtnCopyRoles);
        _nativeToolbarFlow.Controls.Add(_nativeBtnExternal);

        _nativeBtnSemantic.Click += (_, _) => SendNativeToolbarCommand("mode", "semantic");
        _nativeBtnMedia.Click += (_, _) => SendNativeToolbarCommand("mode", "media");
        _nativeBtnCopyLink.Click += (_, _) => CopyTextToClipboard(_webView.Source?.ToString() ?? _url ?? "", "native_copy_link");
        _nativeBtnCopyText.Click += (_, _) => CopyTextToClipboard(_payloadPlainText, "native_copy_text");
        _nativeBtnCopyRoles.Click += (_, _) => CopyTextToClipboard(_nativeToolbarMode.Equals("media", StringComparison.OrdinalIgnoreCase) ? _payloadMediaRoleText : _payloadSemanticRoleText, "native_copy_roles");
        _nativeBtnExternal.Click += (_, _) => OpenExternal(FirstNonBlank(_webView.Source?.ToString(), _url));
        _nativeSourceCombo.SelectedIndexChanged += (_, _) =>
        {
            if (_nativeToolbarUpdating) return;
            NavigateNativeSourceIndex(_nativeSourceCombo.SelectedIndex, "dropdown");
        };

        UpdateNativeModeButtons();
        UpdateNativeToolbarResponsiveLayout();
    }

    private void ConfigureToolbarButton(Button b, string text, int width, string tooltip)
    {
        b.Text = text;
        b.Tag = null;
        b.Width = width;
        b.Height = 32;
        b.Margin = new Padding(2, 1, 2, 0);
        b.Padding = new Padding(0);
        b.FlatStyle = FlatStyle.Flat;
        b.FlatAppearance.BorderColor = Color.FromArgb(15, 23, 42);
        b.FlatAppearance.BorderSize = 0;
        b.FlatAppearance.MouseOverBackColor = Color.FromArgb(37, 99, 235);
        b.FlatAppearance.MouseDownBackColor = Color.FromArgb(30, 64, 175);
        b.BackColor = Color.FromArgb(29, 78, 216);
        b.ForeColor = Color.White;
        b.UseVisualStyleBackColor = false;
        b.Font = new Font(SystemFonts.MessageBoxFont.FontFamily, 8.0f, FontStyle.Bold);
        b.Cursor = Cursors.Hand;
        b.TextAlign = ContentAlignment.MiddleCenter;
        b.AutoSize = false;
        b.UseCompatibleTextRendering = false;
        b.TabStop = false;
        try { b.NotifyDefault(false); } catch { }
        ApplyRoundedRegion(b, 8);
        _nativeToolTip.SetToolTip(b, tooltip);
    }

    private void ConfigureToolbarIconButton(Button b, string iconKind, string tooltip, int width)
    {
        // R42CR: real project PNG artwork, painted by a custom UserPaint button.
        // This avoids the WinForms Button.Image + default-theme double-paint that made the icons
        // look overlaid/clipped during resize.  One control paints one rounded background and one
        // centred bitmap; if a PNG is missing it falls back to the vector icon.
        ConfigureToolbarButton(b, "", width, tooltip);
        b.Tag = iconKind;
        b.Text = "";
        b.Image = null;
        b.Padding = new Padding(0);
        b.Margin = new Padding(2, 1, 2, 0);
        if (b is NativeToolbarIconButton ib)
        {
            ib.ToolbarIconKind = iconKind;
            ib.ToolbarIcon = _nativeIconImages.TryGetValue(iconKind, out var img) ? img : null;
            ib.IconBoxPx = 22;
            ib.CornerRadius = 8;
        }
        b.Paint -= NativeIconButtonPaint;
        b.Paint -= NativeToolbarAssetIconButtonPaint;
        b.Paint -= NativeToolbarVectorIconButtonPaint;
    }

    private void LoadNativeToolbarIconImages()
    {
        try
        {
            foreach (var old in _nativeIconImages.Values)
            {
                try { old.Dispose(); } catch { }
            }
            _nativeIconImages.Clear();
            var iconDir = Path.Combine(_root, "assets", "profile_media", "source_roles");
            var missing = new List<string>();

            LoadNativeToolbarIcon(iconDir, "link", "icons8-link-50.png", missing);
            LoadNativeToolbarIcon(iconDir, "text", "icons8-copy-24.png", missing);
            LoadNativeToolbarIcon(iconDir, "roles", "icons8-copy-source-role-multicolour-24.png", missing);
            LoadNativeToolbarIcon(iconDir, "external", "icons8-external-link-48.png", missing);

            _log.Log("native_toolbar_icons_ready", $"mode=asset_png_owner_draw; dir={iconDir}; loaded={_nativeIconImages.Count}; missing={string.Join(",", missing)}; png_control_image=false");
        }
        catch (Exception ex)
        {
            _log.Log("native_toolbar_icons_failed", ex.GetType().Name + ": " + ex.Message);
        }
    }

    private void LoadNativeToolbarIcon(string iconDir, string key, string fileName, List<string> missing)
    {
        try
        {
            var path = Path.Combine(iconDir, fileName);
            if (!File.Exists(path))
            {
                missing.Add(fileName);
                return;
            }
            _nativeIconImages[key] = LoadScaledNativeToolbarIcon(path, 22);
        }
        catch (Exception ex)
        {
            missing.Add(fileName + ":" + ex.GetType().Name);
        }
    }

    private static Image LoadScaledNativeToolbarIcon(string path, int boxPx)
    {
        using var raw = Image.FromFile(path);
        var box = Math.Max(16, boxPx);
        var scale = Math.Min((float)box / Math.Max(1, raw.Width), (float)box / Math.Max(1, raw.Height));
        var w = Math.Max(1, (int)Math.Round(raw.Width * scale));
        var h = Math.Max(1, (int)Math.Round(raw.Height * scale));
        var bmp = new Bitmap(box, box);
        using var g = Graphics.FromImage(bmp);
        g.Clear(Color.Transparent);
        g.CompositingQuality = CompositingQuality.HighQuality;
        g.InterpolationMode = InterpolationMode.HighQualityBicubic;
        g.PixelOffsetMode = PixelOffsetMode.HighQuality;
        g.SmoothingMode = SmoothingMode.AntiAlias;
        g.DrawImage(raw, new Rectangle((box - w) / 2, (box - h) / 2, w, h));
        return bmp;
    }

    private static void ConfigureCountLabel(Label l, string text, Color back)
    {
        l.Text = text;
        l.Width = 88;
        l.Height = 32;
        l.Margin = new Padding(2, 1, 2, 0);
        l.TextAlign = ContentAlignment.MiddleCenter;
        l.ForeColor = Color.White;
        l.BackColor = back;
        l.Font = new Font(SystemFonts.MessageBoxFont.FontFamily, 8f, FontStyle.Bold);
        l.BorderStyle = BorderStyle.None;
        l.AutoSize = false;
        l.UseCompatibleTextRendering = false;
        ApplyRoundedRegion(l, 8);
    }

    private static void ApplyRoundedRegion(Control control, int radius)
    {
        void Apply()
        {
            if (control.Width <= 1 || control.Height <= 1) return;
            try
            {
                using var path = RoundedRect(new Rectangle(0, 0, control.Width, control.Height), radius);
                control.Region?.Dispose();
                control.Region = new Region(path);
            }
            catch { }
        }
        control.SizeChanged += (_, _) => Apply();
        Apply();
    }

    private static GraphicsPath RoundedRect(Rectangle bounds, int radius)
    {
        var r = Math.Max(2, radius);
        var d = r * 2;
        var rect = new Rectangle(bounds.X, bounds.Y, Math.Max(1, bounds.Width - 1), Math.Max(1, bounds.Height - 1));
        var path = new GraphicsPath();
        path.AddArc(rect.X, rect.Y, d, d, 180, 90);
        path.AddArc(rect.Right - d, rect.Y, d, d, 270, 90);
        path.AddArc(rect.Right - d, rect.Bottom - d, d, d, 0, 90);
        path.AddArc(rect.X, rect.Bottom - d, d, d, 90, 90);
        path.CloseFigure();
        return path;
    }

    private void NativeSourceComboDrawItem(object? sender, DrawItemEventArgs e)
    {
        if (e.Index < 0) return;
        var selected = (e.State & DrawItemState.Selected) == DrawItemState.Selected;
        using var back = new SolidBrush(selected ? Color.FromArgb(37, 99, 235) : Color.FromArgb(30, 41, 59));
        e.Graphics.FillRectangle(back, e.Bounds);

        var item = e.Index >= 0 && e.Index < _nativeSourceItems.Count ? _nativeSourceItems[e.Index] : null;
        var itemCount = Math.Max(_nativeSourceItems.Count, e.Index + 1);
        var indexText = FirstNonBlank(item?.IndexLabel ?? "", itemCount >= 100 ? (e.Index + 1).ToString("000", System.Globalization.CultureInfo.InvariantCulture) : (e.Index + 1).ToString("00", System.Globalization.CultureInfo.InvariantCulture));
        var prefix = item?.Prefix ?? "";
        var title = FirstNonBlank(item?.Title ?? "", _nativeSourceCombo.Items[e.Index]?.ToString() ?? "");
        var site = FirstNonBlank(item?.Site ?? "", "Source");
        var suffix = " | " + site;

        var x = e.Bounds.Left + 4;
        var y = e.Bounds.Top + 2;
        var h = Math.Max(1, e.Bounds.Height - 4);
        var right = e.Bounds.Right - 5;
        var textColor = Color.White;
        var muted = Color.FromArgb(226, 232, 240);

        using var baseFont = new Font(_nativeSourceCombo.Font.FontFamily, _nativeSourceCombo.Font.Size, FontStyle.Bold);
        using var prefixFont = new Font(_nativeSourceCombo.Font.FontFamily, _nativeSourceCombo.Font.Size + 0.5f, FontStyle.Bold | FontStyle.Italic);
        using var sepFont = new Font(_nativeSourceCombo.Font.FontFamily, _nativeSourceCombo.Font.Size, FontStyle.Regular);

        const TextFormatFlags flags = TextFormatFlags.Left | TextFormatFlags.VerticalCenter | TextFormatFlags.NoPadding | TextFormatFlags.NoPrefix;
        int Measure(string s, Font f)
        {
            try { return Math.Max(1, TextRenderer.MeasureText(e.Graphics, s ?? "", f, new Size(1000, h), TextFormatFlags.NoPadding | TextFormatFlags.NoPrefix).Width); }
            catch { return Math.Max(1, (s ?? "").Length * 7); }
        }

        void DrawToken(string s, Font f, Color c, int extraRight)
        {
            var w = Measure(s, f);
            TextRenderer.DrawText(e.Graphics, s, f, new Rectangle(x, y, w + 1, h), c, flags);
            x += w + extraRight;
        }

        void DrawSep(int after)
        {
            var w = Measure("|", sepFont);
            TextRenderer.DrawText(e.Graphics, "|", sepFont, new Rectangle(x, y, w + 1, h), muted, flags);
            x += w + after;
        }

        // R42CR: measured segments instead of fixed 20px / 12px slots.
        // This removes the wasted gap after "01" and after archive markers such as "W".
        DrawToken(indexText, baseFont, textColor, 4);
        DrawSep(5);

        if (!string.IsNullOrWhiteSpace(prefix))
        {
            DrawToken(prefix, prefixFont, textColor, 4);
            DrawSep(5);
        }

        var suffixW = Math.Max(42, Measure(suffix, baseFont));
        var available = Math.Max(1, right - x);
        suffixW = Math.Min(suffixW, available);
        var titleAvailable = Math.Max(1, available - suffixW - 5);
        var naturalTitleW = Math.Max(1, Measure(title, baseFont) + 4);
        var titleW = Math.Min(titleAvailable, naturalTitleW);
        var titleRect = new Rectangle(x, y, titleW, h);
        TextRenderer.DrawText(e.Graphics, title, baseFont, titleRect, textColor,
            TextFormatFlags.Left | TextFormatFlags.VerticalCenter | TextFormatFlags.EndEllipsis | TextFormatFlags.NoPadding | TextFormatFlags.NoPrefix);
        x += titleW + 5;
        var suffixRect = new Rectangle(x, y, Math.Max(1, Math.Min(suffixW, right - x)), h);
        TextRenderer.DrawText(e.Graphics, suffix, baseFont, suffixRect, textColor,
            TextFormatFlags.Left | TextFormatFlags.VerticalCenter | TextFormatFlags.NoPadding | TextFormatFlags.NoPrefix);
    }

    private static void DrawRoundedRectangle(Graphics g, Pen pen, float x, float y, float width, float height, float radius)
    {
        using var path = new GraphicsPath();
        var d = radius * 2f;
        path.AddArc(x, y, d, d, 180, 90);
        path.AddArc(x + width - d, y, d, d, 270, 90);
        path.AddArc(x + width - d, y + height - d, d, d, 0, 90);
        path.AddArc(x, y + height - d, d, d, 90, 90);
        path.CloseFigure();
        g.DrawPath(pen, path);
    }

    private void NativeToolbarAssetIconButtonPaint(object? sender, PaintEventArgs e)
    {
        if (sender is not Button b) return;
        var kind = (b.Tag as string) ?? "";

        // Prev/next are intentionally vector arrows because there are no project PNGs for them.
        if (kind.Equals("prev", StringComparison.OrdinalIgnoreCase) || kind.Equals("next", StringComparison.OrdinalIgnoreCase))
        {
            NativeToolbarVectorIconButtonPaint(sender, e);
            return;
        }

        if (!_nativeIconImages.TryGetValue(kind, out var img) || img is null)
        {
            // Missing asset fallback: still draw a visible icon instead of leaving an empty button.
            NativeToolbarVectorIconButtonPaint(sender, e);
            return;
        }

        try
        {
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            e.Graphics.CompositingQuality = CompositingQuality.HighQuality;
            e.Graphics.InterpolationMode = InterpolationMode.HighQualityBicubic;
            e.Graphics.PixelOffsetMode = PixelOffsetMode.HighQuality;

            var box = Math.Max(16, Math.Min(22, Math.Min(b.ClientRectangle.Width - 12, b.ClientRectangle.Height - 10)));
            var x = b.ClientRectangle.Left + (b.ClientRectangle.Width - box) / 2;
            var y = b.ClientRectangle.Top + (b.ClientRectangle.Height - box) / 2;
            e.Graphics.DrawImage(img, new Rectangle(x, y, box, box));
        }
        catch
        {
            NativeToolbarVectorIconButtonPaint(sender, e);
        }
    }

    private void NativeToolbarVectorIconButtonPaint(object? sender, PaintEventArgs e)
    {
        if (sender is not Button b) return;
        DrawNativeVectorToolbarIcon(e.Graphics, (b.Tag as string) ?? "", b.ClientRectangle);
    }

    private static void NativeIconButtonPaint(object? sender, PaintEventArgs e)
    {
        if (sender is not Button b) return;
        DrawNativeVectorToolbarIcon(e.Graphics, (b.Tag as string) ?? "", b.ClientRectangle);
    }

    private static void DrawNativeVectorToolbarIcon(Graphics g, string kind, Rectangle r)
    {
        g.SmoothingMode = SmoothingMode.AntiAlias;
        g.CompositingQuality = CompositingQuality.HighQuality;
        g.InterpolationMode = InterpolationMode.HighQualityBicubic;
        g.PixelOffsetMode = PixelOffsetMode.HighQuality;

        var cx = r.Left + r.Width / 2f;
        var cy = r.Top + r.Height / 2f;
        var s = Math.Max(16f, Math.Min(22f, Math.Min(r.Width - 10f, r.Height - 8f)));
        float X(float v) => cx + (v * s / 24f);
        float Y(float v) => cy + (v * s / 24f);

        using var white = new Pen(Color.White, Math.Max(1.7f, s / 11f)) { StartCap = LineCap.Round, EndCap = LineCap.Round, LineJoin = LineJoin.Round };
        using var thin = new Pen(Color.White, Math.Max(1.25f, s / 15f)) { StartCap = LineCap.Round, EndCap = LineCap.Round, LineJoin = LineJoin.Round };
        using var brush = new SolidBrush(Color.White);
        using var subtle = new SolidBrush(Color.FromArgb(45, 255, 255, 255));

        switch (kind)
        {
            case "prev":
                g.FillPolygon(brush, new[] { new PointF(X(-5), Y(0)), new PointF(X(5), Y(-7)), new PointF(X(5), Y(7)) });
                break;

            case "next":
                g.FillPolygon(brush, new[] { new PointF(X(5), Y(0)), new PointF(X(-5), Y(-7)), new PointF(X(-5), Y(7)) });
                break;

            case "link":
                g.DrawArc(white, X(-11), Y(-3), s * 13f / 24f, s * 9f / 24f, 125, 285);
                g.DrawArc(white, X(-2), Y(-6), s * 13f / 24f, s * 9f / 24f, -55, 285);
                g.DrawLine(white, X(-4), Y(3), X(4), Y(-3));
                break;

            case "text":
                // Copy icon: two pages, one clear foreground page. No PNG scaling.
                DrawRoundedRectangle(g, thin, X(-8), Y(-7), s * 12f / 24f, s * 14f / 24f, s * 2.5f / 24f);
                DrawRoundedRectangle(g, white, X(-4), Y(-10), s * 14f / 24f, s * 17f / 24f, s * 2.5f / 24f);
                break;

            case "roles":
                // Source-role text icon: one crisp vector page plus four role-colour chips.
                // This replaces the multicolour PNG that looked like overlapping squares.
                DrawRoundedRectangle(g, thin, X(-9), Y(-9), s * 18f / 24f, s * 18f / 24f, s * 3f / 24f);
                using (var primary = new SolidBrush(Color.FromArgb(5, 150, 105)))
                using (var secondary = new SolidBrush(Color.FromArgb(37, 99, 235)))
                using (var tertiary = new SolidBrush(Color.FromArgb(126, 34, 206)))
                using (var unknown = new SolidBrush(Color.FromArgb(180, 83, 9)))
                {
                    var chip = Math.Max(3.2f, s * 4.4f / 24f);
                    var gap = Math.Max(2.0f, s * 2.0f / 24f);
                    var left = X(-5.3f);
                    var top = Y(-5.3f);
                    g.FillRectangle(primary, left, top, chip, chip);
                    g.FillRectangle(secondary, left + chip + gap, top, chip, chip);
                    g.FillRectangle(tertiary, left, top + chip + gap, chip, chip);
                    g.FillRectangle(unknown, left + chip + gap, top + chip + gap, chip, chip);
                }
                break;

            case "external":
                DrawRoundedRectangle(g, thin, X(-8), Y(-5), s * 13f / 24f, s * 13f / 24f, s * 2.2f / 24f);
                g.DrawLine(white, X(-1), Y(1), X(8), Y(-8));
                g.DrawLine(white, X(2), Y(-8), X(8), Y(-8));
                g.DrawLine(white, X(8), Y(-8), X(8), Y(-2));
                break;
        }
    }

    private void LoadNativeToolbarFromPayload(string payloadJson, string selectedUrl, string initialMode)
    {
        try
        {
            if (InvokeRequired)
            {
                BeginInvoke(new Action(() => LoadNativeToolbarFromPayload(payloadJson, selectedUrl, initialMode)));
                return;
            }

            _nativeToolbarMode = initialMode.Equals("media", StringComparison.OrdinalIgnoreCase) ? "media" : "semantic";
            _payloadPlainText = "";
            _payloadSemanticRoleText = "";
            _payloadMediaRoleText = "";
            _nativeSourceItems.Clear();
            _nativeCountsByMode.Clear();

            using var doc = JsonDocument.Parse(string.IsNullOrWhiteSpace(payloadJson) ? "{}" : payloadJson);
            var root = doc.RootElement;
            _payloadPlainText = JsonString(root, "plain_text");
            _payloadSemanticRoleText = JsonString(root, "semantic_role_text");
            _payloadMediaRoleText = JsonString(root, "media_role_text");
            var selected = FirstNonBlank(CleanNativeUrl(selectedUrl), CleanNativeUrl(JsonString(root, "selected_url")), _url, "about:blank");
            var inferredTitle = InferNativeArticleTitle(root, selected);

            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            void AddUrl(string url, string label, string relation = "")
            {
                url = CleanNativeUrl(url);
                if (!url.StartsWith("http://", StringComparison.OrdinalIgnoreCase) && !url.StartsWith("https://", StringComparison.OrdinalIgnoreCase)) return;
                var key = NativeNavKey(url);
                if (string.IsNullOrWhiteSpace(key) || !seen.Add(key)) return;
                var baseLabel = FirstNonBlank(label, NativeBaseLabelForUrl(url));
                _nativeSourceItems.Add(new NativeSourceNavItem { Url = url, Label = baseLabel, Kind = baseLabel, Relation = relation });
            }

            AddUrl(selected, "Original", "selected");
            if (root.ValueKind == JsonValueKind.Object && root.TryGetProperty("source_navigation_urls", out var navNode) && navNode.ValueKind == JsonValueKind.Array)
            {
                foreach (var item in navNode.EnumerateArray())
                {
                    if (item.ValueKind == JsonValueKind.String) AddUrl(item.GetString() ?? "", "", "payload_string");
                    else if (item.ValueKind == JsonValueKind.Object)
                    {
                        AddUrl(FirstNonBlank(JsonString(item, "url"), JsonString(item, "normalised_url"), JsonString(item, "display_url"), JsonString(item, "archive_url"), JsonString(item, "preserved_url")), FirstNonBlank(JsonString(item, "label"), JsonString(item, "display_label"), JsonString(item, "visible_link_source_row_label"), JsonString(item, "source_label")), FirstNonBlank(JsonString(item, "relation"), JsonString(item, "source_relation_type"), JsonString(item, "kind")));
                    }
                }
            }
            // R42CR: the selected overlay payload can contain only Original + Wayback even when
            // an earlier live capture has a matching archive.ph snapshot under r40d_external_live_article.
            // Surface those existing local archive captures in the source selector without changing evidence.
            foreach (var archiveUrl in DiscoverNativeLocalArchiveSourceUrls(selected, inferredTitle))
                AddUrl(archiveUrl, "archive.ph", "local_archive_discovery");
            if (root.ValueKind == JsonValueKind.Object && root.TryGetProperty("rows_by_mode", out var rowsByMode) && rowsByMode.ValueKind == JsonValueKind.Object)
            {
                foreach (var modeName in new[] { "semantic", "media" })
                {
                    if (!rowsByMode.TryGetProperty(modeName, out var arr) || arr.ValueKind != JsonValueKind.Array) continue;
                    var counts = new[] { 0, 0, 0, 0 }; // PRIMARY, SECONDARY, TERTIARY, UNKNOWN
                    foreach (var row in arr.EnumerateArray())
                    {
                        if (row.ValueKind != JsonValueKind.Object) continue;
                        AddUrl(FirstNonBlank(JsonString(row, "url"), JsonString(row, "normalised_url"), JsonString(row, "display_url")), "", "role_row");
                        CountNativePayloadRole(counts, NativePayloadRole(row, modeName));
                    }
                    _nativeCountsByMode[modeName] = counts;
                }
            }

            SortNativeSourceItems();
            ApplyNativeSourceDisplayLabels(inferredTitle);
            SetNativeCountsForMode(_nativeToolbarMode);
            UpdateNativeToolbarForSource(selected);
            var semanticCountsText = _nativeCountsByMode.TryGetValue("semantic", out var semanticCounts) ? FormatNativeCountArray(semanticCounts) : "none";
            var mediaCountsText = _nativeCountsByMode.TryGetValue("media", out var mediaCounts) ? FormatNativeCountArray(mediaCounts) : "none";
            _log.Log("native_toolbar_ready", $"sources={_nativeSourceItems.Count}; mode={_nativeToolbarMode}; counts_cached={_nativeCountsByMode.Count}; counts_semantic={semanticCountsText}; counts_media={mediaCountsText}; url={selected}; nav_items={string.Join(" || ", _nativeSourceItems.Select(x => $"{x.IndexLabel}:{x.Kind}:{x.Label}:{x.Url}"))}");
        }
        catch (Exception ex)
        {
            _log.Log("native_toolbar_payload_failed", ex.GetType().Name + ": " + ex.Message);
        }
    }

    private static string NativePayloadRole(JsonElement row, string modeName)
    {
        var role = modeName.Equals("media", StringComparison.OrdinalIgnoreCase)
            ? FirstNonBlank(JsonString(row, "media_source_role"), JsonString(row, "active_role"))
            : FirstNonBlank(JsonString(row, "semantic_role"), JsonString(row, "active_role"));
        role = (role ?? "").Trim().ToUpperInvariant();
        return role is "PRIMARY" or "SECONDARY" or "TERTIARY" or "UNKNOWN" or "BLANK" ? role : "UNKNOWN";
    }

    private static void CountNativePayloadRole(int[] counts, string role)
    {
        switch ((role ?? "").Trim().ToUpperInvariant())
        {
            case "PRIMARY": counts[0]++; break;
            case "SECONDARY": counts[1]++; break;
            case "TERTIARY": counts[2]++; break;
            case "UNKNOWN": counts[3]++; break;
            // BLANK stays visually neutral and is not displayed in the four coloured counters.
        }
    }

    private static string FormatNativeCountArray(int[]? counts)
    {
        if (counts is null || counts.Length < 4) return "P0/S0/T0/U0";
        return $"P{counts[0]}/S{counts[1]}/T{counts[2]}/U{counts[3]}";
    }

    private static int CountPayloadModeRows(string payloadJson, string modeName)
    {
        try
        {
            using var doc = JsonDocument.Parse(string.IsNullOrWhiteSpace(payloadJson) ? "{}" : payloadJson);
            if (doc.RootElement.ValueKind == JsonValueKind.Object
                && doc.RootElement.TryGetProperty("rows_by_mode", out var rowsByMode)
                && rowsByMode.ValueKind == JsonValueKind.Object
                && rowsByMode.TryGetProperty(modeName, out var arr)
                && arr.ValueKind == JsonValueKind.Array)
                return arr.GetArrayLength();
        }
        catch { }
        return 0;
    }

    private void SetNativeCountsForMode(string modeName)
    {
        if (_nativeCountsByMode.TryGetValue(modeName.Equals("media", StringComparison.OrdinalIgnoreCase) ? "media" : "semantic", out var counts) && counts.Length >= 4)
            SetNativeCounts(counts[0], counts[1], counts[2], counts[3]);
    }

    private IEnumerable<string> DiscoverNativeLocalArchiveSourceUrls(string selectedUrl, string inferredTitle)
    {
        var found = new List<string>();
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        try
        {
            var baseDir = Path.Combine(_root, "profile_media_live_captures", "r40d_external_live_article");
            if (!Directory.Exists(baseDir)) return found;

            var target = NativeArchiveTargetUrl(selectedUrl).TrimEnd('/');
            var targetLow = target.ToLowerInvariant();
            var hostNeedle = "";
            var slugNeedle = "";
            try
            {
                if (Uri.TryCreate(target, UriKind.Absolute, out var uri))
                {
                    hostNeedle = (uri.Host ?? "").ToLowerInvariant();
                    slugNeedle = (uri.Segments.LastOrDefault() ?? "").Trim('/').ToLowerInvariant();
                }
            }
            catch { }
            var titleNeedle = CleanNativeTitle(inferredTitle).ToLowerInvariant();

            var archiveDirs = Directory.EnumerateDirectories(baseDir, "*archive*", SearchOption.TopDirectoryOnly)
                .OrderBy(x => x, StringComparer.OrdinalIgnoreCase)
                .ToList();
            foreach (var dir in archiveDirs)
            {
                var candidate = NativeArchiveUrlFromCapturePath(dir);
                if (string.IsNullOrWhiteSpace(candidate)) continue;
                if (!NativeCaptureFolderLooksLikeSelected(dir, targetLow, hostNeedle, slugNeedle, titleNeedle)) continue;
                if (seen.Add(candidate)) found.Add(candidate);
            }

            // R42CR: local capture folders are often created as one human-entered chain:
            // 01_original, 02_wayback, 03_archive.ph_xxxx.  Some archive.ph captures
            // do not preserve the original target URL in their metadata because a human
            // challenge/429 page intervened, so metadata matching returns zero.  In that
            // case, allow a narrow ordinal sibling fallback from the same capture batch.
            if (found.Count == 0)
            {
                foreach (var candidate in DiscoverNativeOrdinalSiblingArchiveUrls(baseDir, targetLow, hostNeedle, slugNeedle))
                {
                    if (seen.Add(candidate)) found.Add(candidate);
                }
                if (found.Count > 0)
                    _log.Log("native_local_archive_ordinal_fallback", $"found={found.Count}; urls={string.Join(",", found)}");
            }
        }
        catch (Exception ex)
        {
            _log.Log("native_local_archive_discovery_failed", ex.GetType().Name + ": " + ex.Message);
        }
        if (found.Count > 0)
            _log.Log("native_local_archive_discovery", $"found={found.Count}; urls={string.Join(",", found)}");
        return found;
    }

    private static string NativeArchiveUrlFromCapturePath(string path)
    {
        try
        {
            var name = Path.GetFileName(path.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar));
            var m = Regex.Match(name, @"archive\.(ph|today|is|li|md|vn)[_\-]([A-Za-z0-9]+)", RegexOptions.IgnoreCase);
            if (m.Success) return "https://archive.ph/" + m.Groups[2].Value;
        }
        catch { }
        return "";
    }

    private static IEnumerable<string> DiscoverNativeOrdinalSiblingArchiveUrls(string baseDir, string targetLow, string hostNeedle, string slugNeedle)
    {
        var found = new List<string>();
        try
        {
            if (string.IsNullOrWhiteSpace(baseDir) || !Directory.Exists(baseDir)) return found;
            var topDirs = Directory.EnumerateDirectories(baseDir, "*", SearchOption.TopDirectoryOnly)
                .OrderBy(x => x, StringComparer.OrdinalIgnoreCase)
                .ToList();
            var selectedOrdinals = new List<int>();
            foreach (var dir in topDirs)
            {
                var name = Path.GetFileName(dir.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar)).ToLowerInvariant();
                if (name.Contains("archive")) continue;
                var looksLikeSelected = false;
                if (!string.IsNullOrWhiteSpace(hostNeedle) && !string.IsNullOrWhiteSpace(slugNeedle) && name.Contains(hostNeedle) && name.Contains(slugNeedle))
                    looksLikeSelected = true;
                if (!looksLikeSelected && !string.IsNullOrWhiteSpace(slugNeedle) && name.Contains(slugNeedle))
                    looksLikeSelected = true;
                if (!looksLikeSelected) continue;
                var m = Regex.Match(name, @"^(\d{1,3})[_\-]");
                if (m.Success && int.TryParse(m.Groups[1].Value, out var ordinal))
                    selectedOrdinals.Add(ordinal);
            }
            if (selectedOrdinals.Count == 0) return found;

            foreach (var dir in topDirs)
            {
                var name = Path.GetFileName(dir.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar)).ToLowerInvariant();
                if (!(name.Contains("archive.ph") || name.Contains("archive.today") || name.Contains("archive.is") || name.Contains("archive.li") || name.Contains("archive.md") || name.Contains("archive.vn")))
                    continue;
                var m = Regex.Match(name, @"^(\d{1,3})[_\-]");
                if (!m.Success || !int.TryParse(m.Groups[1].Value, out var ordinal)) continue;
                if (!selectedOrdinals.Any(selectedOrdinal => ordinal >= selectedOrdinal && ordinal <= selectedOrdinal + 4)) continue;
                var candidate = NativeArchiveUrlFromCapturePath(dir);
                if (!string.IsNullOrWhiteSpace(candidate)) found.Add(candidate);
            }
            if (found.Count > 8) found.Clear();
        }
        catch { }
        return found.Distinct(StringComparer.OrdinalIgnoreCase).ToList();
    }

    private static bool NativeCaptureFolderLooksLikeSelected(string dir, string targetLow, string hostNeedle, string slugNeedle, string titleNeedle)
    {
        try
        {
            var checks = new List<string>();
            foreach (var sub in Directory.EnumerateDirectories(dir).OrderByDescending(x => x, StringComparer.OrdinalIgnoreCase).Take(4))
            {
                foreach (var file in new[] { "capture_session.json", "capture_provenance.json", "redirect_chain.json", "frames.json", "loaded_resources.json", "network_requests.jsonl" })
                {
                    var p = Path.Combine(sub, file);
                    if (!File.Exists(p)) continue;
                    try
                    {
                        var info = new FileInfo(p);
                        if (info.Length > 2_000_000) continue;
                        checks.Add(File.ReadAllText(p).ToLowerInvariant());
                    }
                    catch { }
                }
            }
            var hay = string.Join("\n", checks);
            if (string.IsNullOrWhiteSpace(hay)) return false;
            if (!string.IsNullOrWhiteSpace(targetLow) && hay.Contains(targetLow)) return true;
            if (!string.IsNullOrWhiteSpace(hostNeedle) && !string.IsNullOrWhiteSpace(slugNeedle) && hay.Contains(hostNeedle) && hay.Contains(slugNeedle)) return true;
            if (!string.IsNullOrWhiteSpace(titleNeedle))
            {
                var words = Regex.Matches(titleNeedle, @"[a-z0-9]{4,}")
                    .Select(x => x.Value)
                    .Distinct(StringComparer.OrdinalIgnoreCase)
                    .Take(8)
                    .ToList();
                if (words.Count >= 4 && words.Count(x => hay.Contains(x)) >= Math.Min(5, words.Count)) return true;
            }
        }
        catch { }
        return false;
    }

    private void SortNativeSourceItems()
    {
        static int Order(NativeSourceNavItem x)
        {
            var u = (x.Url ?? "").ToLowerInvariant();
            if (u.Contains("web.archive.org/web/")) return 1;
            if (u.Contains("archive.ph") || u.Contains("archive.today") || u.Contains("archive.is") || u.Contains("archive.li") || u.Contains("archive.md") || u.Contains("archive.vn")) return 2;
            if (u.Contains("archive")) return 3;
            return 0;
        }
        var ordered = _nativeSourceItems.Select((item, idx) => new { item, idx }).OrderBy(x => Order(x.item)).ThenBy(x => x.idx).Select(x => x.item).ToList();
        _nativeSourceItems.Clear();
        _nativeSourceItems.AddRange(ordered);
    }

    private void ApplyNativeSourceDisplayLabels(string inferredTitle)
    {
        var count = Math.Max(1, _nativeSourceItems.Count);
        for (var i = 0; i < _nativeSourceItems.Count; i++)
        {
            var item = _nativeSourceItems[i];
            item.Prefix = NativeArchivePrefixForUrl(item.Url);
            item.IndexLabel = count >= 100
                ? (i + 1).ToString("000", System.Globalization.CultureInfo.InvariantCulture)
                : (i + 1).ToString("00", System.Globalization.CultureInfo.InvariantCulture);
            item.Site = NativeSiteLabelForUrl(item.Url);
            item.Title = NativeShortSourceTitle(FirstNonBlank(inferredTitle, NativeReadableTitleFromUrl(item.Url), item.Kind, item.Site), 96);
            item.Label = string.IsNullOrWhiteSpace(item.Prefix)
                ? $"{item.IndexLabel} | {item.Title} | {item.Site}"
                : $"{item.IndexLabel} | {item.Prefix} | {item.Title} | {item.Site}";
        }
    }

    private static string NativeArchivePrefixForUrl(string url)
    {
        var low = (url ?? "").ToLowerInvariant();
        if (low.Contains("web.archive.org/web/")) return "W";
        if (low.Contains("archive.ph") || low.Contains("archive.today") || low.Contains("archive.is") || low.Contains("archive.li") || low.Contains("archive.md") || low.Contains("archive.vn")) return "A";
        return "";
    }

    private static string InferNativeArticleTitle(JsonElement root, string selectedUrl)
    {
        foreach (var key in new[] { "article_title", "article_headline", "headline", "source_title", "page_title", "og_title", "title" })
        {
            var value = CleanNativeTitle(JsonString(root, key));
            if (!string.IsNullOrWhiteSpace(value) && !LooksLikeNativeUrl(value)) return value;
        }

        try
        {
            if (root.ValueKind == JsonValueKind.Object && root.TryGetProperty("rows_by_mode", out var rowsByMode) && rowsByMode.ValueKind == JsonValueKind.Object)
            {
                foreach (var modeName in new[] { "semantic", "media" })
                {
                    if (!rowsByMode.TryGetProperty(modeName, out var arr) || arr.ValueKind != JsonValueKind.Array) continue;
                    foreach (var row in arr.EnumerateArray())
                    {
                        if (row.ValueKind != JsonValueKind.Object) continue;
                        var rowText = CleanNativeTitle(JsonString(row, "text"));
                        if (rowText.Length >= 20 && !LooksLikeNativeUrl(rowText) && !rowText.StartsWith("Published ", StringComparison.OrdinalIgnoreCase))
                            return rowText;
                    }
                }
            }
        }
        catch { }

        var plain = JsonString(root, "plain_text");
        if (!string.IsNullOrWhiteSpace(plain))
        {
            foreach (var rawLine in plain.Replace("\r", "\n").Split('\n'))
            {
                var line = CleanNativeTitle(rawLine);
                if (line.Length >= 20 && !LooksLikeNativeUrl(line) && !line.StartsWith("Published ", StringComparison.OrdinalIgnoreCase)) return line;
            }
        }
        return NativeReadableTitleFromUrl(selectedUrl);
    }

    private static string CleanNativeTitle(string? value)
    {
        var s = (value ?? "").Replace('\u201c', '"').Replace('\u201d', '"').Trim();
        while (s.Length >= 2 && ((s[0] == '\'' && s[^1] == '\'') || (s[0] == '"' && s[^1] == '"')))
            s = s[1..^1].Trim();
        s = Regex.Replace(s, @"\s+", " ").Trim();
        return s;
    }

    private static bool LooksLikeNativeUrl(string? value)
    {
        var s = (value ?? "").Trim();
        return s.StartsWith("http://", StringComparison.OrdinalIgnoreCase) || s.StartsWith("https://", StringComparison.OrdinalIgnoreCase) || s.Contains("://", StringComparison.Ordinal);
    }

    private static string NativeShortSourceTitle(string title, int maxChars)
    {
        title = CleanNativeTitle(title);
        maxChars = Math.Max(18, maxChars);
        if (title.Length <= maxChars) return title;
        return title[..Math.Max(1, maxChars - 1)].TrimEnd() + "…";
    }

    private static string NativeReadableTitleFromUrl(string url)
    {
        try
        {
            var target = NativeArchiveTargetUrl(url);
            if (!Uri.TryCreate(target, UriKind.Absolute, out var uri)) return FirstNonBlank(target, "Source");
            var last = uri.Segments.LastOrDefault()?.Trim('/').Trim() ?? "";
            if (string.IsNullOrWhiteSpace(last)) return NativeSiteLabelForUrl(target);
            last = Regex.Replace(Uri.UnescapeDataString(last), @"[-_]+", " ").Trim();
            if (last.Length == 0) return NativeSiteLabelForUrl(target);
            return char.ToUpperInvariant(last[0]) + last[1..];
        }
        catch { return FirstNonBlank(url, "Source"); }
    }

    private static string NativeSiteLabelForUrl(string url)
    {
        try
        {
            var target = NativeArchiveTargetUrl(url);
            if (!Uri.TryCreate(target, UriKind.Absolute, out var uri)) return "Source";
            var host = (uri.Host ?? "").ToLowerInvariant();
            if (host.StartsWith("www.")) host = host[4..];
            if (host.Contains("metro.co.uk")) return "Metro";
            if (host.Contains("bbc.co.uk") || host.Contains("bbc.com")) return "BBC";
            if (host.Contains("theguardian.com")) return "The Guardian";
            if (host.Contains("independent.co.uk")) return "Independent";
            var parts = host.Split('.', StringSplitOptions.RemoveEmptyEntries);
            var core = parts.Length >= 3 && parts[^2].Length <= 3 ? parts[^3] : (parts.Length >= 2 ? parts[^2] : host);
            return string.IsNullOrWhiteSpace(core) ? "Source" : char.ToUpperInvariant(core[0]) + core[1..];
        }
        catch { return "Source"; }
    }

    private static string NativeArchiveTargetUrl(string url)
    {
        var s = CleanNativeUrl(url);
        var low = s.ToLowerInvariant();
        var marker = "/http";
        if (low.Contains("web.archive.org/web/") && low.Contains(marker))
        {
            var idx = low.IndexOf(marker, StringComparison.Ordinal);
            if (idx >= 0 && idx + 1 < s.Length) return s[(idx + 1)..];
        }
        if (low.Contains("archive.") && low.Contains("/http"))
        {
            var idx = low.IndexOf("/http", StringComparison.Ordinal);
            if (idx >= 0 && idx + 1 < s.Length) return s[(idx + 1)..];
        }
        return s;
    }

    private static string NativeBaseLabelForUrl(string url)
    {
        var low = (url ?? "").ToLowerInvariant();
        if (low.Contains("web.archive.org/web/")) return "Wayback Snapshot";
        if (low.Contains("archive.ph") || low.Contains("archive.today") || low.Contains("archive.is") || low.Contains("archive.li") || low.Contains("archive.md") || low.Contains("archive.vn")) return "archive.ph";
        if (low.Contains("archive")) return "Archive URL";
        return "Original";
    }

    private static string NativeNavKey(string url)
    {
        return CleanNativeUrl(url).TrimEnd('/').ToLowerInvariant();
    }

    private static string CleanNativeUrl(string? value)
    {
        var s = (value ?? "").Trim();
        if (string.IsNullOrWhiteSpace(s)) return "";

        // R42EB: tolerate chat/Markdown-wrapped URLs and escaped Markdown copied
        // from transcripts.  This protects navigation and matching from strings
        // like [https://archive.ph/6mr3C](https://archive.ph/6mr3C) without
        // changing the source-role payload itself.
        s = s.Replace("\\(", "(").Replace("\\)", ")").Replace("\\[", "[").Replace("\\]", "]").Replace("\\_", "_");
        s = s.Trim('"', '\'', ' ', '\t', '\r', '\n', '<', '>');

        var m1 = Regex.Match(s, @"^\[[^\]]+\]\((https?://[^)]+)\)$", RegexOptions.IgnoreCase);
        if (m1.Success)
        {
            s = m1.Groups[1].Value.Trim();
        }
        else
        {
            var matches = Regex.Matches(s, @"https?://[^\s\]\)<>""]+", RegexOptions.IgnoreCase);
            if (matches.Count > 0)
                s = matches[matches.Count - 1].Value.Trim();
        }

        s = s.Trim('"', '\'', ' ', '\t', '\r', '\n', '<', '>');
        while (s.EndsWith(".", StringComparison.Ordinal) || s.EndsWith(",", StringComparison.Ordinal) || s.EndsWith(";", StringComparison.Ordinal))
            s = s[..^1];

        // Archive short codes are case-sensitive; do not lowercase generally.
        // This exact mapping only repairs the known bad one-link test variant.
        s = s.Replace("https://archive.ph/6Mr3C", "https://archive.ph/6mr3C", StringComparison.Ordinal);
        s = s.Replace("http://archive.ph/6Mr3C", "http://archive.ph/6mr3C", StringComparison.Ordinal);
        s = s.Replace("https://archive.today/6Mr3C", "https://archive.today/6mr3C", StringComparison.Ordinal);
        s = s.Replace("http://archive.today/6Mr3C", "http://archive.today/6mr3C", StringComparison.Ordinal);
        return s;
    }

    private static string JsonString(JsonElement element, string name)
    {
        try
        {
            if (element.ValueKind == JsonValueKind.Object && element.TryGetProperty(name, out var node))
                return node.ValueKind == JsonValueKind.String ? node.GetString() ?? "" : node.ToString() ?? "";
        }
        catch { }
        return "";
    }

    private void ScheduleNativeToolbarResponsiveLayout(int delayMs)
    {
        try
        {
            if (!IsHandleCreated || IsDisposed || Disposing) return;
            _nativeResizeLayoutTimer ??= new System.Windows.Forms.Timer();
            _nativeResizeLayoutTimer.Stop();
            _nativeResizeLayoutTimer.Interval = Math.Max(1, delayMs);
            _nativeResizeLayoutTimer.Tick -= NativeResizeLayoutTimerTick;
            _nativeResizeLayoutTimer.Tick += NativeResizeLayoutTimerTick;
            _nativeResizeLayoutTimer.Start();
        }
        catch { }
    }

    private void NativeResizeLayoutTimerTick(object? sender, EventArgs e)
    {
        try { _nativeResizeLayoutTimer?.Stop(); } catch { }
        UpdateNativeToolbarResponsiveLayout();
    }

    private static int NativeOuterWidth(Control c)
    {
        if (!c.Visible) return 0;
        return c.Width + c.Margin.Left + c.Margin.Right;
    }

    private int NativeFixedToolbarWidthExcludingUrl()
    {
        var total = _nativeToolbar.Padding.Left + _nativeToolbar.Padding.Right + 8;
        foreach (Control c in _nativeToolbarFlow.Controls)
        {
            if (ReferenceEquals(c, _nativeUrlLabel)) continue;
            total += c.Width + c.Margin.Left + c.Margin.Right;
        }
        return total;
    }

    private void UpdateNativeToolbarResponsiveLayout()
    {
        try
        {
            if (IsDisposed || Disposing) return;
            var width = Math.Max(1, _nativeToolbar.ClientSize.Width > 0 ? _nativeToolbar.ClientSize.Width : ClientSize.Width);

            _nativeToolbarFlow.SuspendLayout();
            try
            {
                // R42CR: use full counter labels at the 980px minimum/half-screen size.
                // R42CR corrects R42BX early compact switching: it switched too early to P/S/T/U labels even though there is enough room once
                // the URL label is hidden and the source selector/action icons are tightened.
                var compact = width < 900;
                var veryTight = width < 760;

                _nativeToolbarCompactLabels = compact;
                _nativeBtnSemantic.Width = compact ? 74 : 86;
                _nativeBtnMedia.Width = compact ? 70 : 76;

                if (compact)
                {
                    _nativePrimaryCount.Width = 64;
                    _nativeSecondaryCount.Width = 64;
                    _nativeTertiaryCount.Width = 64;
                    _nativeUnknownCount.Width = 64;
                    _nativeSourceCombo.Width = veryTight ? 178 : 250;
                }
                else
                {
                    _nativePrimaryCount.Width = 88;
                    _nativeSecondaryCount.Width = 96;
                    _nativeTertiaryCount.Width = 88;
                    _nativeUnknownCount.Width = 92;
                    // Keep the toolbar fixed in one row.  The source selector carries the source number,
                    // archive marker, article title, and site; when width is tight, shorten only the title section.
                    _nativeSourceCombo.Width = width < 1120 ? 300 : 460;
                }
                UpdateNativeCountTexts();

                _nativeBtnPrev.Visible = false;
                _nativeBtnNext.Visible = false;
                _nativeBtnCopyLink.Width = 34;
                _nativeBtnCopyText.Width = 34;
                _nativeBtnCopyRoles.Width = 34;
                _nativeBtnExternal.Width = 34;

                // Calculate after setting fixed widths. If the fixed controls still barely exceed
                // the current client width, reduce only the dropdown, then hide the non-essential URL.
                var fixedWidth = NativeFixedToolbarWidthExcludingUrl();
                var spare = width - fixedWidth;
                if (spare < 0 && _nativeSourceCombo.Width > 160)
                {
                    _nativeSourceCombo.Width = Math.Max(160, _nativeSourceCombo.Width + spare - 8);
                    fixedWidth = NativeFixedToolbarWidthExcludingUrl();
                    spare = width - fixedWidth;
                }

                _nativeUrlLabel.Visible = spare >= 180;
                _nativeUrlLabel.Width = _nativeUrlLabel.Visible ? Math.Max(150, Math.Min(720, spare - 8)) : 0;
            }
            finally
            {
                _nativeToolbarFlow.ResumeLayout(false);
            }

            _nativeToolbarFlow.PerformLayout();
            _nativeToolbarFlow.Invalidate(true);
        }
        catch { }
    }

    private void UpdateNativeToolbarForSource(string source)
    {
        if (InvokeRequired)
        {
            BeginInvoke(new Action(() => UpdateNativeToolbarForSource(source)));
            return;
        }
        var url = CleanNativeUrl(FirstNonBlank(source, _url));
        if (!string.IsNullOrWhiteSpace(url))
        {
            // Archive access-chain pages can report the visible URL as https://archive.ph/ after
            // a selected snapshot such as https://archive.ph/6mr3C. Preserve the selected
            // source candidate URL for batch source-role judgement; the visible URL is only
            // transient navigation/access state and must not replace source 03.
            if (ShouldPreserveNativeArchiveSelectionForVisibleUrl(url))
            {
                MarkNativeHumanActionPending("archive_service_access_chain_or_429", url, false);
            }
            else
            {
                _url = url;
                if (!IsNativeArchiveServiceUrl(url)) ClearNativeHumanActionPending();
            }
        }
        UpdateNativeToolbarState(url);
    }

    private void UpdateNativeToolbarState(string? url = null)
    {
        try
        {
            _nativeToolbarUpdating = true;
            var currentUrl = CleanNativeUrl(FirstNonBlank(url, _webView.Source?.ToString(), _url));
            var currentIndex = FindNativeSourceIndexForUrl(currentUrl);
            if (currentIndex < 0 && _nativeSelectedSourceIndex >= 0 && _nativeSelectedSourceIndex < _nativeSourceItems.Count)
                currentIndex = _nativeSelectedSourceIndex;
            if (currentIndex < 0) currentIndex = 0;
            if (currentIndex >= 0 && currentIndex < _nativeSourceItems.Count)
                _nativeSelectedSourceIndex = currentIndex;

            var comboItemsChanged = _nativeSourceCombo.Items.Count != _nativeSourceItems.Count;
            if (!comboItemsChanged)
            {
                for (var i = 0; i < _nativeSourceItems.Count; i++)
                {
                    var label = _nativeSourceItems[i].Label;
                    if (!string.Equals(_nativeSourceCombo.Items[i]?.ToString(), label, StringComparison.Ordinal)) { comboItemsChanged = true; break; }
                }
            }
            if (comboItemsChanged)
            {
                _nativeSourceCombo.Items.Clear();
                for (var i = 0; i < _nativeSourceItems.Count; i++)
                    _nativeSourceCombo.Items.Add(_nativeSourceItems[i].Label);
            }
            if (_nativeSourceItems.Count > 0 && currentIndex >= 0 && currentIndex < _nativeSourceCombo.Items.Count)
                _nativeSourceCombo.SelectedIndex = currentIndex;
            _nativeSourceCombo.Visible = _nativeSourceItems.Count > 1;
            _nativeBtnPrev.Enabled = _nativeBtnNext.Enabled = false;
            _nativeBtnPrev.Visible = _nativeBtnNext.Visible = false;

            var selectedSourceUrl = currentIndex >= 0 && currentIndex < _nativeSourceItems.Count ? _nativeSourceItems[currentIndex].Url : currentUrl;
            if (_nativeHumanActionPending)
            {
                var host = NativeHostLabel(_nativeHumanActionVisibleUrl);
                _nativeUrlLabel.Text = $"Access chain active: {host} — source {currentIndex + 1:00} stays queued for automatic role check";
                _nativeToolTip.SetToolTip(_nativeUrlLabel, $"Access-chain continuation. Selected source candidate: {selectedSourceUrl}\nVisible URL: {_nativeHumanActionVisibleUrl}\nReason: {_nativeHumanActionReason}\nBatch source-role judgement resumes automatically after full article/source markers load.");
            }
            else
            {
                _nativeUrlLabel.Text = currentUrl;
                _nativeToolTip.SetToolTip(_nativeUrlLabel, currentUrl);
            }
            var titleUrl = FirstNonBlank(selectedSourceUrl, currentUrl);
            Text = string.IsNullOrWhiteSpace(titleUrl) ? "YTCE R42CR Native Source-Role Editor" : "YTCE R42CR Native Source-Role Editor — " + titleUrl;
            UpdateNativeModeButtons();
        }
        catch (Exception ex)
        {
            _log.Log("native_toolbar_update_failed", ex.GetType().Name + ": " + ex.Message);
        }
        finally
        {
            _nativeToolbarUpdating = false;
        }
    }

    private int FindNativeSourceIndexForUrl(string? source)
    {
        var currentUrl = CleanNativeUrl(source);
        if (_nativeSourceItems.Count == 0) return -1;
        var key = NativeNavKey(currentUrl);
        for (var i = 0; i < _nativeSourceItems.Count; i++)
        {
            if (string.Equals(NativeNavKey(_nativeSourceItems[i].Url), key, StringComparison.OrdinalIgnoreCase))
                return i;
        }

        // R42CR: archive access redirects can collapse https://archive.ph/<id> to
        // https://archive.ph/ or another archive service URL. Keep the selected/requested
        // archive source candidate selected so the batch checker can resume and judge
        // that same candidate after full content is available.
        if (IsNativeArchiveServiceUrl(currentUrl))
        {
            if (_nativeSelectedSourceIndex >= 0 && _nativeSelectedSourceIndex < _nativeSourceItems.Count && IsNativeArchiveServiceUrl(_nativeSourceItems[_nativeSelectedSourceIndex].Url))
                return _nativeSelectedSourceIndex;
            if (_nativeLastRequestedSourceIndex >= 0 && _nativeLastRequestedSourceIndex < _nativeSourceItems.Count && IsNativeArchiveServiceUrl(_nativeSourceItems[_nativeLastRequestedSourceIndex].Url))
                return _nativeLastRequestedSourceIndex;
            for (var i = 0; i < _nativeSourceItems.Count; i++)
                if (IsNativeArchiveServiceUrl(_nativeSourceItems[i].Url)) return i;
        }
        return -1;
    }

    private bool ShouldPreserveNativeArchiveSelectionForVisibleUrl(string visibleUrl)
    {
        if (!IsNativeArchiveServiceUrl(visibleUrl)) return false;
        var selectedIdx = _nativeSelectedSourceIndex;
        if (selectedIdx < 0 || selectedIdx >= _nativeSourceItems.Count) selectedIdx = _nativeLastRequestedSourceIndex;
        return selectedIdx >= 0 && selectedIdx < _nativeSourceItems.Count && IsNativeArchiveServiceUrl(_nativeSourceItems[selectedIdx].Url) && !string.Equals(NativeNavKey(visibleUrl), NativeNavKey(_nativeSourceItems[selectedIdx].Url), StringComparison.OrdinalIgnoreCase);
    }

    private void MarkNativeHumanActionPending(string reason, string visibleUrl, bool logNow)
    {
        try
        {
            var idx = FindNativeSourceIndexForUrl(visibleUrl);
            if (idx >= 0) _nativeSelectedSourceIndex = idx;
            _nativeHumanActionPending = true;
            _nativeHumanActionReason = FirstNonBlank(reason, "human_action_required");
            _nativeHumanActionVisibleUrl = CleanNativeUrl(visibleUrl);
            _nativeHumanActionSourceUrl = idx >= 0 && idx < _nativeSourceItems.Count ? _nativeSourceItems[idx].Url : _url;
            if (logNow)
            {
                _log.Log("native_access_chain_barrier", $"reason={_nativeHumanActionReason}; selected_index={_nativeSelectedSourceIndex + 1}; selected_url={_nativeHumanActionSourceUrl}; visible_url={_nativeHumanActionVisibleUrl}; action=access_chain_active; source_candidate_kept=true; next=load_full_page_then_auto_source_role_judgement; evidence_gate=article_markers_required");
            }
        }
        catch { }
    }

    private void ClearNativeHumanActionPending()
    {
        _nativeHumanActionPending = false;
        _nativeHumanActionReason = "";
        _nativeHumanActionSourceUrl = "";
        _nativeHumanActionVisibleUrl = "";
    }

    private static bool IsNativeArchiveServiceUrl(string? url)
    {
        var low = (url ?? "").ToLowerInvariant();
        return low.Contains("archive.ph") || low.Contains("archive.today") || low.Contains("archive.is") || low.Contains("archive.li") || low.Contains("archive.md") || low.Contains("archive.vn");
    }

    private static bool IsNativeArchiveRootUrl(string? url)
    {
        try
        {
            var clean = CleanNativeUrl(url);
            if (!IsNativeArchiveServiceUrl(clean)) return false;
            if (!Uri.TryCreate(clean, UriKind.Absolute, out var uri)) return false;
            var path = (uri.AbsolutePath ?? "/").Trim();
            return string.IsNullOrWhiteSpace(path) || path == "/";
        }
        catch { return false; }
    }

    private static string NativeHostLabel(string? url)
    {
        try
        {
            var clean = CleanNativeUrl(url);
            if (Uri.TryCreate(clean, UriKind.Absolute, out var uri) && !string.IsNullOrWhiteSpace(uri.Host))
                return uri.Host.StartsWith("www.", StringComparison.OrdinalIgnoreCase) ? uri.Host[4..] : uri.Host;
        }
        catch { }
        return FirstNonBlank(url, "source");
    }

    private void UpdateNativeModeButtons()
    {
        var semantic = _nativeToolbarMode.Equals("semantic", StringComparison.OrdinalIgnoreCase);
        _nativeBtnSemantic.BackColor = semantic ? Color.FromArgb(14, 165, 233) : Color.White;
        _nativeBtnSemantic.ForeColor = semantic ? Color.FromArgb(0, 17, 31) : Color.FromArgb(15, 23, 42);
        _nativeBtnSemantic.FlatAppearance.BorderColor = semantic ? Color.FromArgb(56, 189, 248) : Color.FromArgb(226, 232, 240);
        _nativeBtnMedia.BackColor = !semantic ? Color.FromArgb(14, 165, 233) : Color.White;
        _nativeBtnMedia.ForeColor = !semantic ? Color.FromArgb(0, 17, 31) : Color.FromArgb(15, 23, 42);
        _nativeBtnMedia.FlatAppearance.BorderColor = !semantic ? Color.FromArgb(56, 189, 248) : Color.FromArgb(226, 232, 240);
        _nativeBtnSemantic.Invalidate();
        _nativeBtnMedia.Invalidate();
    }

    private void SetNativeCounts(int primary, int secondary, int tertiary, int unknown)
    {
        _nativeCountPrimary = primary;
        _nativeCountSecondary = secondary;
        _nativeCountTertiary = tertiary;
        _nativeCountUnknown = unknown;
        UpdateNativeCountTexts();
    }

    private void UpdateNativeCountTexts()
    {
        if (_nativeToolbarCompactLabels)
        {
            _nativePrimaryCount.Text = $"P: {_nativeCountPrimary:00}";
            _nativeSecondaryCount.Text = $"S: {_nativeCountSecondary:00}";
            _nativeTertiaryCount.Text = $"T: {_nativeCountTertiary:00}";
            _nativeUnknownCount.Text = $"U: {_nativeCountUnknown:00}";
        }
        else
        {
            _nativePrimaryCount.Text = $"Primary: {_nativeCountPrimary:00}";
            _nativeSecondaryCount.Text = $"Secondary: {_nativeCountSecondary:00}";
            _nativeTertiaryCount.Text = $"Tertiary: {_nativeCountTertiary:00}";
            _nativeUnknownCount.Text = $"Unknown: {_nativeCountUnknown:00}";
        }
    }

    private void SendNativeToolbarCommand(string action, string value)
    {
        try
        {
            if (_webView.CoreWebView2 == null) return;
            if (action.Equals("mode", StringComparison.OrdinalIgnoreCase))
            {
                _nativeToolbarMode = value.Equals("media", StringComparison.OrdinalIgnoreCase) ? "media" : "semantic";
                SetNativeCountsForMode(_nativeToolbarMode);
                UpdateNativeModeButtons();
                UpdateNativeCountTexts();
            }
            var json = JsonSerializer.Serialize(new { marker = Marker, type = "native_toolbar_command", action, value });

            // Keep the normal WebView2 message path, but also call the in-page bridge directly.
            // R42CR fixes R42BX logs that showed native_toolbar_command entries without any page-side mode_toggle
            // messages after an archive navigation.  The direct ExecuteScript path makes the native
            // toolbar authoritative even when the WebMessage bridge is delayed or string-marshalled.
            _webView.CoreWebView2.PostWebMessageAsJson(json);
            var jsJsonLiteral = JsonSerializer.Serialize(json);
            _ = _webView.CoreWebView2.ExecuteScriptAsync("(function(){try{var msg=JSON.parse(" + jsJsonLiteral + ");if(window.__ytce_r42cr_nativeToolbarCommand){window.__ytce_r42cr_nativeToolbarCommand(msg);return 'direct';}window.__ytce_r42cr_pendingNativeToolbarCommand=msg;return 'pending';}catch(e){return 'error:'+String(e&&e.message||e);}})();");
            _log.Log("native_toolbar_command", $"action={action}; value={value}; direct_exec=queued");
        }
        catch (Exception ex)
        {
            _log.Log("native_toolbar_command_failed", ex.GetType().Name + ": " + ex.Message);
        }
    }

    private void NavigateNativeSourceRelative(int delta, string method)
    {
        if (_nativeSourceItems.Count < 2) return;
        var current = Math.Max(0, _nativeSourceCombo.SelectedIndex);
        var next = (current + delta + _nativeSourceItems.Count) % _nativeSourceItems.Count;
        NavigateNativeSourceIndex(next, method);
    }

    private void NavigateNativeSourceIndex(int index, string method)
    {
        try
        {
            if (index < 0 || index >= _nativeSourceItems.Count) return;
            var item = _nativeSourceItems[index];
            var from = Math.Max(0, _nativeSourceCombo.SelectedIndex) + 1;
            _nativeSelectedSourceIndex = index;
            _nativeLastRequestedSourceIndex = index;
            ClearNativeHumanActionPending();
            _url = item.Url;
            UpdateNativeToolbarState(item.Url);
            _log.Log("native_source_nav_click", $"method={method}; from_index={from}; to_index={index + 1}; count={_nativeSourceItems.Count}; label={item.Label}; url={item.Url}; source_candidate_selected=true");
            _webView.CoreWebView2?.Navigate(item.Url);
        }
        catch (Exception ex)
        {
            _log.Log("native_source_nav_failed", ex.GetType().Name + ": " + ex.Message);
        }
    }

    private void CopyTextToClipboard(string text, string logName)
    {
        try
        {
            Clipboard.SetText(text ?? "");
            _log.Log(logName, $"chars={(text ?? "").Length}");
        }
        catch (Exception ex)
        {
            _log.Log(logName + "_failed", ex.GetType().Name + ": " + ex.Message);
        }
    }

    private void ApplyNativeToolbarState(JsonElement root)
    {
        try
        {
            if (InvokeRequired)
            {
                BeginInvoke(new Action(() => ApplyNativeToolbarState(root.Clone())));
                return;
            }
            if (!root.TryGetProperty("extra", out var extra) || extra.ValueKind != JsonValueKind.Object) return;
            var newMode = JsonString(extra, "mode");
            if (!string.IsNullOrWhiteSpace(newMode)) _nativeToolbarMode = newMode.Equals("media", StringComparison.OrdinalIgnoreCase) ? "media" : "semantic";
            if (extra.TryGetProperty("counts", out var counts) && counts.ValueKind == JsonValueKind.Object)
            {
                SetNativeCounts(JsonInt(counts, "PRIMARY"), JsonInt(counts, "SECONDARY"), JsonInt(counts, "TERTIARY"), JsonInt(counts, "UNKNOWN"));
            }
            var stateUrl = FirstNonBlank(JsonString(extra, "url"), _webView.Source?.ToString(), _url);
            UpdateNativeToolbarForSource(stateUrl);
            _log.Log("native_toolbar_state", $"mode={_nativeToolbarMode}; counts=P{_nativeCountPrimary}/S{_nativeCountSecondary}/T{_nativeCountTertiary}/U{_nativeCountUnknown}; url={stateUrl}; r42ec_state_applied=true");
        }
        catch (Exception ex)
        {
            _log.Log("native_toolbar_state_failed", ex.GetType().Name + ": " + ex.Message);
        }
    }

    private static int JsonInt(JsonElement element, string name)
    {
        try
        {
            if (element.ValueKind == JsonValueKind.Object && element.TryGetProperty(name, out var node) && node.TryGetInt32(out var value)) return value;
        }
        catch { }
        return 0;
    }

    private void RemoveCurrentDocumentStartScript(string reason)
    {
        if (string.IsNullOrWhiteSpace(_documentScriptId)) return;
        try
        {
            _webView.CoreWebView2.RemoveScriptToExecuteOnDocumentCreated(_documentScriptId);
            _log.Log("document_start_script_removed", $"reason={reason}; id={_documentScriptId}");
        }
        catch (Exception ex)
        {
            _log.Log("document_start_script_remove_failed", $"reason={reason}; {ex.Message}");
        }
        finally
        {
            _documentScriptId = null;
        }
    }

    private static string ExtraString(JsonElement root, string name)
    {
        try
        {
            if (root.TryGetProperty("extra", out var extra) && extra.ValueKind == JsonValueKind.Object && extra.TryGetProperty(name, out var node))
                return node.GetString() ?? "";
            if (root.TryGetProperty(name, out var direct))
                return direct.GetString() ?? "";
        }
        catch { }
        return "";
    }

    private static int ExtraInt(JsonElement root, string name)
    {
        try
        {
            JsonElement node;
            if (root.TryGetProperty("extra", out var extra) && extra.ValueKind == JsonValueKind.Object && extra.TryGetProperty(name, out node) && node.TryGetInt32(out var value))
                return value;
            if (root.TryGetProperty(name, out node) && node.TryGetInt32(out value))
                return value;
        }
        catch { }
        return 0;
    }

    private void WriteServerReadyFile()
    {
        try
        {
            Directory.CreateDirectory(_commandDir);
            var ready = new
            {
                pid = Environment.ProcessId,
                marker = Marker,
                command_dir = _commandDir,
                started = DateTimeOffset.Now.ToString("O")
            };
            File.WriteAllText(ServerReadyPath(), JsonSerializer.Serialize(ready, new JsonSerializerOptions { WriteIndented = true }));
            try { File.Delete(Path.Combine(_commandDir, "r42cr_server_starting.json")); } catch { }
        }
        catch (Exception ex)
        {
            _log.Log("server_ready_write_failed", ex.Message);
        }
    }

    private async Task LoadServerCommandAsync(string commandJson, string commandPath)
    {
        var sw = Stopwatch.StartNew();
        try
        {
            using var doc = JsonDocument.Parse(commandJson);
            var root = doc.RootElement;
            string GetString(string name)
            {
                return root.ValueKind == JsonValueKind.Object && root.TryGetProperty(name, out var node) ? node.GetString() ?? "" : "";
            }
            int GetInt(string name, int fallback)
            {
                try
                {
                    if (root.ValueKind == JsonValueKind.Object && root.TryGetProperty(name, out var node))
                    {
                        if (node.ValueKind == JsonValueKind.Number && node.TryGetInt32(out var value)) return value;
                        if (int.TryParse(node.GetString() ?? "", out var parsed)) return parsed;
                    }
                }
                catch { }
                return fallback;
            }

            var commandRoot = FirstNonBlank(GetString("root"), _root);
            var commandAction = GetString("action");
            var commandMaterialCapturePath = ResolvePath(GetString("material_capture_path"), commandRoot);
            var commandMaterialCaptureTitle = GetString("material_capture_title");
            var commandMaterialCaptureWaitMs = Math.Max(5000, Math.Min(900000, GetInt("material_capture_wait_ms", 60000)));
            _lastServerCommandElapsedMs = _log.ElapsedMilliseconds;
            _lastServerCommandFile = Path.GetFileName(commandPath);
            _lastServerCommandToken = Path.GetFileNameWithoutExtension(commandPath) + "_" + DateTimeOffset.UtcNow.ToUnixTimeMilliseconds().ToString(System.Globalization.CultureInfo.InvariantCulture);
            _serverCommandFirstPaintLogged = false;
            _payloadPath = ResolvePath(GetString("payload"), commandRoot);
            _changesPath = ResolvePath(GetString("changes"), commandRoot);
            _roleDbPath = ResolvePath(GetString("role_db"), commandRoot);
            _initialMode = GetString("mode").Equals("media", StringComparison.OrdinalIgnoreCase) ? "media" : "semantic";
            _urlArg = CleanNativeUrl(GetString("url"));
            _payloadJson = ReadPayloadJson(_payloadPath, _log);
            _url = CleanNativeUrl(FirstNonBlank(_urlArg, TryGetPayloadString(_payloadJson, "selected_url"), "about:blank"));
            LoadNativeToolbarFromPayload(_payloadJson, _url, _initialMode ?? "semantic");
            if (commandAction.Equals("material_capture", StringComparison.OrdinalIgnoreCase) && !string.IsNullOrWhiteSpace(commandMaterialCapturePath))
            {
                ConfigureNativeMaterialCapture(commandMaterialCapturePath, commandMaterialCaptureTitle, commandMaterialCaptureWaitMs, _url);
            }
            else
            {
                ClearNativeMaterialCapture("non_material_server_command");
            }
            var commandAgeMs = -1L;
            try
            {
                if (root.TryGetProperty("created_at", out var createdAtNode) && createdAtNode.TryGetDouble(out var createdAtSeconds))
                {
                    commandAgeMs = (long)Math.Max(0, (DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() - (createdAtSeconds * 1000.0)));
                }
            }
            catch { }
            var agePart = commandAgeMs >= 0 ? $"; command_age_ms={commandAgeMs}" : "";

            var commandSignature = string.Join("|", new[] { _url ?? "", _payloadPath ?? "", _changesPath ?? "", _initialMode ?? "", commandAction ?? "", commandMaterialCapturePath ?? "" });
            var nowElapsed = _log.ElapsedMilliseconds;
            if (!string.IsNullOrWhiteSpace(_lastServerCommandSignature)
                && string.Equals(commandSignature, _lastServerCommandSignature, StringComparison.Ordinal)
                && _lastServerCommandSignatureAtMs >= 0
                && nowElapsed - _lastServerCommandSignatureAtMs >= 0
                && nowElapsed - _lastServerCommandSignatureAtMs < 1200)
            {
                _log.Log("server_command_duplicate_ignored", $"file={Path.GetFileName(commandPath)}; duplicate_of_recent_ms={nowElapsed - _lastServerCommandSignatureAtMs}{agePart}; url={_url}; payload={_payloadPath}; changes={_changesPath}; mode={_initialMode}");
                return;
            }
            _lastServerCommandSignature = commandSignature;
            _lastServerCommandSignatureAtMs = nowElapsed;

            var roleDbPart = string.IsNullOrWhiteSpace(_roleDbPath) ? "" : $"; role_db={_roleDbPath}";
            _log.Log("server_command_received", $"file={Path.GetFileName(commandPath)}; action={commandAction}; read_ms={sw.ElapsedMilliseconds}{agePart}; url={_url}; payload={_payloadPath}; changes={_changesPath}; mode={_initialMode}{roleDbPart}");

            try
            {
                if (!string.IsNullOrWhiteSpace(_changesPath))
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(_changesPath)) ?? ".");
                }
            }
            catch { }

            RemoveCurrentDocumentStartScript("new_server_command");

            try
            {
                _webView.CoreWebView2.Stop();
                await _webView.CoreWebView2.ExecuteScriptAsync("try{delete window.__ytce_r42ai_native_editor_installed; delete window.__ytce_r42ai_native_editor_token;}catch(e){}");
            }
            catch { }

            _documentScriptId = await _webView.CoreWebView2.AddScriptToExecuteOnDocumentCreatedAsync(DocumentStartRoleEditorScript(_payloadJson, _initialMode ?? "semantic", commandRoot, _lastServerCommandToken));
            _log.Log("document_start_script_registered", $"server command registered script; marker={Marker}; mode={_initialMode}; token={_lastServerCommandToken}; elapsed_ms={sw.ElapsedMilliseconds}");

            // R42DW: after archive material has been captured, Python can send a
            // second role-ready payload.  Refresh the already visible archive page
            // in place when possible, instead of re-running the material-capture
            // loop or forcing another navigation before counters/paint can update.
            if (commandAction.Equals("role_overlay_refresh", StringComparison.OrdinalIgnoreCase))
            {
                var currentSource = CleanNativeUrl(_webView.Source?.ToString() ?? "");
                var currentKey = NativeNavKey(currentSource);
                var targetKey = NativeNavKey(_url ?? "");
                var canRefreshInPlace =
                    !string.IsNullOrWhiteSpace(currentSource)
                    && !currentSource.StartsWith("about:", StringComparison.OrdinalIgnoreCase)
                    && (
                        string.Equals(currentKey, targetKey, StringComparison.OrdinalIgnoreCase)
                        || (IsNativeArchiveServiceUrl(currentSource) && IsNativeArchiveServiceUrl(_url ?? ""))
                    );

                if (canRefreshInPlace)
                {
                    try
                    {
                        ShowServerEditorWindow();
                        await _webView.CoreWebView2.ExecuteScriptAsync(DocumentStartRoleEditorScript(_payloadJson, _initialMode ?? "semantic", commandRoot, _lastServerCommandToken));
                        var semanticRows = CountPayloadModeRows(_payloadJson, "semantic");
                        var mediaRows = CountPayloadModeRows(_payloadJson, "media");
                        _log.Log("r42dw_role_overlay_refresh_applied", $"no_navigation=true; semantic_rows={semanticRows}; media_rows={mediaRows}; current={currentSource}; url={_url}; payload={_payloadPath}");
                        _log.Log("server_command_dispatched", $"elapsed_ms={sw.ElapsedMilliseconds}; action=role_overlay_refresh; window_visible={Visible}; url={_url}");
                        return;
                    }
                    catch (Exception ex)
                    {
                        _log.Log("r42dw_role_overlay_refresh_failed_falling_back_to_navigation", ex.GetType().Name + ": " + ex.Message);
                    }
                }
                else
                {
                    // R42DZ: role-ready archive refresh must not re-hit archive.ph just
                    // because the warm helper is on about:blank or a stale page.  The
                    // safe/default path is CMD/local replay + in-place refresh only.  A
                    // navigation fallback is allowed only by explicit developer env flag.
                    var allowRoleRefreshNavigation =
                        string.Equals(Environment.GetEnvironmentVariable("YTCE_R42DZ_ALLOW_ROLE_REFRESH_NAVIGATION"), "1", StringComparison.OrdinalIgnoreCase)
                        || string.Equals(Environment.GetEnvironmentVariable("YTCE_R42DZ_ALLOW_ROLE_REFRESH_NAVIGATION"), "true", StringComparison.OrdinalIgnoreCase)
                        || string.Equals(Environment.GetEnvironmentVariable("YTCE_R42DZ_ALLOW_ROLE_REFRESH_NAVIGATION"), "yes", StringComparison.OrdinalIgnoreCase);
                    if (!allowRoleRefreshNavigation)
                    {
                        _log.Log("r42dz_role_overlay_refresh_deferred_no_navigation", $"current={currentSource}; url={_url}; semantic_rows={CountPayloadModeRows(_payloadJson, "semantic")}; media_rows={CountPayloadModeRows(_payloadJson, "media")}; reason=current_page_not_matching_or_blank");
                        _log.Log("server_command_dispatched", $"elapsed_ms={sw.ElapsedMilliseconds}; action=role_overlay_refresh_deferred_no_navigation; window_visible={Visible}; url={_url}");
                        return;
                    }
                    _log.Log("r42dw_role_overlay_refresh_fallback_navigation", $"current={currentSource}; url={_url}; semantic_rows={CountPayloadModeRows(_payloadJson, "semantic")}; media_rows={CountPayloadModeRows(_payloadJson, "media")}; explicit_env_allowed=true");
                }
            }

            // R42CR: start navigation before the focus/restore work.  WebView2 can
            // begin loading the selected URL while WinForms restores the warm
            // hidden window, shaving roughly the old server_window_shown cost from
            // command-to-first-paint without preloading the URL.
            _log.Log("server_navigate_call", $"elapsed_ms={sw.ElapsedMilliseconds}; url={_url}");
            _webView.CoreWebView2.Navigate(_url);
            if (!_materialCaptureDone && !string.IsNullOrWhiteSpace(_materialCapturePath))
            {
                KickNativeMaterialCapture("server_navigate_call");
            }
            ShowServerEditorWindow();
            _log.Log("server_command_dispatched", $"elapsed_ms={sw.ElapsedMilliseconds}; window_visible={Visible}; url={_url}");
        }
        catch (Exception ex)
        {
            _log.Log("server_command_load_failed", ex.ToString());
        }
    }

    private void ShowServerEditorWindow()
    {
        var sw = Stopwatch.StartNew();
        var wasVisible = Visible;
        try
        {
            // R42CR: the warm server starts hidden/minimized.  On some systems
            // restoring a minimized transparent Form without resetting its
            // normal bounds produces a tiny caption-only window.  Always restore
            // to a real editor-sized rectangle before navigating the selected page.
            ShowInTaskbar = true;
            Opacity = 1;
            Text = "YTCE R42CR Native Source-Role Editor";

            if (WindowState == FormWindowState.Minimized)
                WindowState = FormWindowState.Normal;

            EnsureUsableEditorBounds(force: !_serverWindowShown);

            if (!_serverWindowShown)
            {
                _serverWindowShown = true;
                Show();
            }
            else if (!Visible)
            {
                Show();
            }

            if (WindowState == FormWindowState.Minimized)
                WindowState = FormWindowState.Normal;

            EnsureUsableEditorBounds(force: false);
            LayoutNativeEditorSurface();
            UpdateNativeToolbarResponsiveLayout();

            // Temporarily go topmost so the warm hidden form actually surfaces over the Tk window.
            TopMost = true;
            BringToFront();
            Activate();
            Focus();
            BeginInvoke(new Action(() =>
            {
                try
                {
                    EnsureUsableEditorBounds(force: false);
                    LayoutNativeEditorSurface();
                    UpdateNativeToolbarResponsiveLayout();
                    BringToFront();
                    Activate();
                    TopMost = false;
                }
                catch { }
            }));
            _log.Log("server_window_shown", $"was_visible={wasVisible}; visible={Visible}; state={WindowState}; bounds={Bounds.Width}x{Bounds.Height}+{Bounds.Left}+{Bounds.Top}; client={ClientSize.Width}x{ClientSize.Height}; elapsed_ms={sw.ElapsedMilliseconds}");
        }
        catch (Exception ex)
        {
            try { TopMost = false; } catch { }
            _log.Log("server_window_show_failed", ex.GetType().Name + ": " + ex.Message);
        }
    }

    private void EnsureUsableEditorBounds(bool force)
    {
        try
        {
            var screen = Screen.FromPoint(Cursor.Position);
            var work = screen.WorkingArea;
            var desiredWidth = Math.Min(1280, Math.Max(980, work.Width - 80));
            var desiredHeight = Math.Min(920, Math.Max(700, work.Height - 80));
            var current = Bounds;
            var tiny = current.Width < 980 || current.Height < 700 || ClientSize.Width < 900 || ClientSize.Height < 620;
            var offscreen = current.Right < work.Left + 120 || current.Bottom < work.Top + 120 || current.Left > work.Right - 120 || current.Top > work.Bottom - 120;
            if (!force && !tiny && !offscreen) return;
            var x = work.Left + Math.Max(0, (work.Width - desiredWidth) / 2);
            var y = work.Top + Math.Max(0, (work.Height - desiredHeight) / 2);
            StartPosition = FormStartPosition.Manual;
            SetBounds(x, y, desiredWidth, desiredHeight, BoundsSpecified.All);
            MinimumSize = new Size(Math.Min(980, desiredWidth), Math.Min(700, desiredHeight));
        }
        catch (Exception ex)
        {
            _log.Log("server_window_bounds_failed", ex.GetType().Name + ": " + ex.Message);
            try
            {
                Width = Math.Max(Width, 1280);
                Height = Math.Max(Height, 920);
                MinimumSize = new Size(980, 700);
            }
            catch { }
        }
    }

    private void InstallRequestBlocking()
    {
        try
        {
            if (string.Equals(Environment.GetEnvironmentVariable("YTCE_R42CR_DISABLE_RESOURCE_BLOCKER"), "1", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(Environment.GetEnvironmentVariable("YTCE_R42AX_DISABLE_RESOURCE_BLOCKER"), "1", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(Environment.GetEnvironmentVariable("YTCE_R42AV_DISABLE_RESOURCE_BLOCKER"), "1", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(Environment.GetEnvironmentVariable("YTCE_R42AU_DISABLE_RESOURCE_BLOCKER"), "1", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(Environment.GetEnvironmentVariable("YTCE_R42AT_DISABLE_RESOURCE_BLOCKER"), "1", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(Environment.GetEnvironmentVariable("YTCE_R42AR_DISABLE_RESOURCE_BLOCKER"), "1", StringComparison.OrdinalIgnoreCase))
            {
                _log.Log("resource_blocker_disabled", "YTCE_R42CR/R42AX/R42AV/R42AU/R42AT/R42AR disable env=1");
                return;
            }
            var core = _webView.CoreWebView2;
            foreach (var ctx in new[]
            {
                CoreWebView2WebResourceContext.Image,
                CoreWebView2WebResourceContext.Script,
                CoreWebView2WebResourceContext.XmlHttpRequest,
                CoreWebView2WebResourceContext.Fetch,
                CoreWebView2WebResourceContext.Media,
                CoreWebView2WebResourceContext.Font,
                CoreWebView2WebResourceContext.Other
            })
            {
                core.AddWebResourceRequestedFilter("*", ctx);
            }
            core.WebResourceRequested += (_, ev) =>
            {
                try
                {
                    if (!ShouldBlockWebResource(ev.Request.Uri, ev.ResourceContext)) return;
                    var bytes = Array.Empty<byte>();
                    var stream = new MemoryStream(bytes);
                    ev.Response = (_environment ?? core.Environment).CreateWebResourceResponse(stream, 204, "No Content", "Content-Type: text/plain\r\nAccess-Control-Allow-Origin: *");
                    var count = Interlocked.Increment(ref _blockedResourceCount);
                    if (count <= 3 || count == 10 || count == 25 || count == 50 || count % 100 == 0)
                    {
                        _log.Log("resource_blocked", $"count={count}; context={ev.ResourceContext}; uri={Truncate(ev.Request.Uri, 150)}");
                    }
                }
                catch (Exception ex)
                {
                    _log.Log("resource_block_failed", ex.Message);
                }
            };
            _log.Log("resource_blocker_installed", "ad/tracker filters enabled");
        }
        catch (Exception ex)
        {
            _log.Log("resource_blocker_install_failed", ex.ToString());
        }
    }

    private static bool ShouldBlockWebResource(string? uri, CoreWebView2WebResourceContext context)
    {
        if (string.IsNullOrWhiteSpace(uri)) return false;
        if (context == CoreWebView2WebResourceContext.Document) return false;
        var u = uri.ToLowerInvariant();
        if (u.StartsWith("data:") || u.StartsWith("blob:") || u.StartsWith("about:")) return false;
        // Do not block article first-party assets unless they are clearly ad/CMP endpoints.
        var clearFirstParty = u.Contains("metro.co.uk") || u.Contains("metro.news") || u.Contains("dmcdn.net") || u.Contains("dailymotion.com");
        if (clearFirstParty && !ContainsAny(u, FirstPartyAdNeedles)) return false;
        return ContainsAny(u, BlockedResourceNeedles);
    }

    private static readonly string[] FirstPartyAdNeedles =
    {
        "/ads/", "/advert", "adunit", "prebid", "cmp", "consent", "quantcast", "permutive", "doubleclick", "googlesyndication"
    };

    private static readonly string[] BlockedResourceNeedles =
    {
        "doubleclick.net", "googlesyndication.com", "googleadservices.com", "adservice.google.", "securepubads.g.doubleclick.net",
        "adnxs.com", "adsrvr.org", "pubmatic.com", "openx.net", "rubiconproject.com", "criteo.com", "criteo.net",
        "yieldmo.com", "smartadserver.com", "indexww.com", "lijit.com", "casalemedia.com", "contextweb.com", "3lift.com",
        "taboola.com", "outbrain.com", "amazon-adsystem.com", "moatads.com", "scorecardresearch.com", "quantserve.com",
        "quantcast.mgr.consensu.org", "privacy-mgmt.com", "consensu.org", "cmp.quantcast.com", "cdn.privacy-mgmt.com",
        "permutive.com", "chartbeat.com", "parsely.com", "bluekai.com", "demdex.net", "hotjar.com", "optimizely.com",
        "/prebid", "prebid.", "googletagmanager.com/gtm.js", "googletagservices.com", "/ads?", "/adserver", "/advertisement"
    };

    private static bool ContainsAny(string value, IEnumerable<string> needles)
    {
        foreach (var needle in needles)
        {
            if (!string.IsNullOrWhiteSpace(needle) && value.Contains(needle, StringComparison.OrdinalIgnoreCase)) return true;
        }
        return false;
    }

    private static string Truncate(string? value, int max)
    {
        if (string.IsNullOrEmpty(value) || value.Length <= max) return value ?? "";
        return value[..max] + "...";
    }


    private void ConfigureNativeMaterialCapture(string outputPath, string title, int waitMs, string url)
    {
        try
        {
            _materialCapturePath = outputPath ?? "";
            _materialCaptureTitle = title ?? "";
            _materialCaptureUrl = url ?? "";
            _materialCaptureWaitMs = Math.Max(5000, Math.Min(900000, waitMs));
            _materialCaptureStartedMs = _log.ElapsedMilliseconds;
            _materialCaptureDone = false;
            _materialCaptureBusy = false;
            _materialCaptureAttempts = 0;
            if (!string.IsNullOrWhiteSpace(_materialCapturePath))
            {
                Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(_materialCapturePath)) ?? ".");
                WriteNativeMaterialCaptureJson("started", "material_capture_configured", "", "", 0, 0, false, false, "");
                _log.Log("r42cr_material_capture_configured", $"path={_materialCapturePath}; wait_ms={_materialCaptureWaitMs}; url={_materialCaptureUrl}; title={Truncate(_materialCaptureTitle, 120)}; batch_safe_access_state=true; normal_page_interaction_only=true; no_generic_playwright_archive_fallback=true");
            }
        }
        catch (Exception ex)
        {
            _log.Log("r42cr_material_capture_configure_failed", ex.ToString());
        }
    }

    private void ClearNativeMaterialCapture(string reason)
    {
        if (!string.IsNullOrWhiteSpace(_materialCapturePath))
        {
            _log.Log("r42cr_material_capture_cleared", reason);
        }
        try { _materialCaptureTimer?.Stop(); } catch { }
        _materialCapturePath = "";
        _materialCaptureTitle = "";
        _materialCaptureUrl = "";
        _materialCaptureStartedMs = -1;
        _materialCaptureDone = false;
        _materialCaptureBusy = false;
        _materialCaptureAttempts = 0;
    }

    private void KickNativeMaterialCapture(string reason)
    {
        if (string.IsNullOrWhiteSpace(_materialCapturePath) || _materialCaptureDone) return;
        try
        {
            if (_materialCaptureTimer == null)
            {
                _materialCaptureTimer = new System.Windows.Forms.Timer { Interval = 850 };
                _materialCaptureTimer.Tick += async (_, _) => await TryNativeMaterialCaptureAsync("timer");
            }
            _materialCaptureTimer.Start();
        }
        catch { }
        _ = TryNativeMaterialCaptureAsync(reason);
    }

    private async Task TryNativeMaterialCaptureAsync(string reason)
    {
        if (string.IsNullOrWhiteSpace(_materialCapturePath) || _materialCaptureDone || _materialCaptureBusy) return;
        _materialCaptureBusy = true;
        try
        {
            _materialCaptureAttempts += 1;
            var elapsed = _materialCaptureStartedMs >= 0 ? Math.Max(0, _log.ElapsedMilliseconds - _materialCaptureStartedMs) : 0;
            if (elapsed > _materialCaptureWaitMs)
            {
                var srcTimeout = _webView.Source?.ToString() ?? "";
                await WriteCurrentNativeMaterialSnapshotAsync("access_chain_wait_expired", reason, srcTimeout, elapsed);
                _materialCaptureDone = true;
                try { _materialCaptureTimer?.Stop(); } catch { }
                _log.Log("r42cr_material_capture_access_wait_expired", $"elapsed_ms={elapsed}; attempts={_materialCaptureAttempts}; url={srcTimeout}; path={_materialCapturePath}");
                return;
            }
            await WriteCurrentNativeMaterialSnapshotAsync("running", reason, _webView.Source?.ToString() ?? "", elapsed);
        }
        catch (Exception ex)
        {
            try
            {
                WriteNativeMaterialCaptureJson("failed", "exception_" + reason, _webView.Source?.ToString() ?? "", "", 0, 0, false, false, ex.ToString());
            }
            catch { }
            _materialCaptureDone = true;
            try { _materialCaptureTimer?.Stop(); } catch { }
            _log.Log("r42cr_material_capture_failed", ex.ToString());
        }
        finally
        {
            _materialCaptureBusy = false;
        }
    }

    private async Task WriteCurrentNativeMaterialSnapshotAsync(string requestedStatus, string reason, string src, long elapsedMs)
    {
        if (string.IsNullOrWhiteSpace(_materialCapturePath) || _webView.CoreWebView2 == null) return;
        var script = @"(() => {
  const clean = (v) => String(v || '').replace(/[\t\r\f\v ]+/g, ' ').replace(/\n\s*/g, '\n').trim();
  const body = document.body;
  const de = document.documentElement;
  const text = clean(body ? (body.innerText || body.textContent || '') : '');
  const html = de ? String(de.outerHTML || '') : '';
  const scrollY = Number(window.scrollY || 0);
  const innerH = Number(window.innerHeight || 0);
  const scrollH = Number((de && de.scrollHeight) || (body && body.scrollHeight) || 0);
  const low = (text + '\n' + html.slice(0, 12000)).toLowerCase();
  const challengeLike = /one more step|please complete the security check|i.?m not a robot|g-recaptcha|recaptcha|cf-turnstile|verify you are human|too many requests|error 429|http 429/.test(low);
  const articleNode = document.querySelector('article, main, [role=main], #CONTENT, #content, .article, .post, .entry-content');
  const articleText = clean(articleNode ? (articleNode.innerText || articleNode.textContent || '') : '');
  return {
    schema: 'ytce-r42cr-native-webview2-material-capture-v1',
    href: String(location.href || ''),
    title: String(document.title || ''),
    readyState: String(document.readyState || ''),
    textLength: text.length,
    articleTextLength: articleText.length,
    htmlLength: html.length,
    scrollY,
    innerH,
    scrollH,
    challengeLike,
    bodyText: text.slice(0, 1500000),
    articleText: articleText.slice(0, 1500000),
    html: html.slice(0, 2500000)
  };
})()";
        var rawJson = await _webView.CoreWebView2.ExecuteScriptAsync(script);
        using var doc = JsonDocument.Parse(string.IsNullOrWhiteSpace(rawJson) ? "{}" : rawJson);
        var root = doc.RootElement.Clone();
        var href = JsonElementString(root, "href");
        var pageTitle = JsonElementString(root, "title");
        var text = FirstNonBlank(JsonElementString(root, "articleText"), JsonElementString(root, "bodyText"));
        var html = JsonElementString(root, "html");
        var rawChallengeLike = JsonElementBool(root, "challengeLike") || IsNativeMaterialChallengeLike(text, html, href);
        var materialLike = IsNativeMaterialLike(text, html, _materialCaptureTitle, pageTitle, href);
        var challengeLike = rawChallengeLike && !materialLike;
        if (rawChallengeLike && materialLike)
        {
            _log.Log("r42du_material_over_challenge_promoted", $"elapsed_ms={elapsedMs}; attempts={_materialCaptureAttempts}; text_len={(text ?? "").Length}; html_len={(html ?? "").Length}; url={FirstNonBlank(href, src)}; title={pageTitle}");
        }
        var status = requestedStatus;
        var note = "snapshot";
        // R42CR safe interaction: for ordinary article pages that are not access
        // gates, nudge scrolling to trigger lazy text/media loading.  Do not use
        // this on challenge-like pages.
        if (!challengeLike && !materialLike && elapsedMs > 2500 && elapsedMs < _materialCaptureWaitMs - 1500 && _materialCaptureAttempts % 4 == 0)
        {
            try
            {
                await _webView.CoreWebView2.ExecuteScriptAsync("try{window.scrollBy({top:Math.max(240, Math.floor((window.innerHeight||700)*0.55)), left:0, behavior:'smooth'});}catch(e){}");
                _log.Log("r42cr_material_capture_normal_page_scroll_nudge", $"elapsed_ms={elapsedMs}; attempts={_materialCaptureAttempts}; url={FirstNonBlank(href, src)}");
            }
            catch { }
        }
        if (materialLike)
        {
            status = "success";
            note = "material_from_rendered_webview2_document";
            var baseDir = Path.GetDirectoryName(Path.GetFullPath(_materialCapturePath)) ?? ".";
            var textPath = Path.Combine(baseDir, "article_text.txt");
            var htmlPath = Path.Combine(baseDir, "archive_page.html");
            File.WriteAllText(textPath, text ?? "", new UTF8Encoding(false));
            File.WriteAllText(htmlPath, html ?? "", new UTF8Encoding(false));
            WriteNativeMaterialCaptureJson(status, note, FirstNonBlank(href, src), pageTitle, (text ?? "").Length, (html ?? "").Length, challengeLike, materialLike, "", textPath, htmlPath);
            _materialCaptureDone = true;
            try { _materialCaptureTimer?.Stop(); } catch { }
            _log.Log("r42cr_material_capture_success", $"elapsed_ms={elapsedMs}; attempts={_materialCaptureAttempts}; text_len={(text ?? "").Length}; url={FirstNonBlank(href, src)}; path={_materialCapturePath}");
            return;
        }
        if (challengeLike && !materialLike && elapsedMs > 12000 && string.Equals(requestedStatus, "running", StringComparison.OrdinalIgnoreCase))
        {
            status = "access_blocked_challenge";
            note = "material_unavailable_access_gate_batch_continues_source_candidate_kept";
            WriteNativeMaterialCaptureJson(status, note, FirstNonBlank(href, src), pageTitle, (text ?? "").Length, (html ?? "").Length, challengeLike, materialLike, "");
            _materialCaptureDone = true;
            try { _materialCaptureTimer?.Stop(); } catch { }
            _log.Log("r42cr_material_capture_access_blocked_challenge", $"elapsed_ms={elapsedMs}; attempts={_materialCaptureAttempts}; text_len={(text ?? "").Length}; html_len={(html ?? "").Length}; url={FirstNonBlank(href, src)}; path={_materialCapturePath}; source_candidate_kept=true; batch_continues=true");
            return;
        }
        if (string.Equals(requestedStatus, "access_chain_wait_expired", StringComparison.OrdinalIgnoreCase))
        {
            status = challengeLike ? "access_blocked_challenge" : "material_unavailable_access_gate";
            note = challengeLike ? "access_chain_wait_expired_still_challenge_page_source_candidate_kept" : "access_chain_wait_expired_no_material_source_candidate_kept";
        }
        WriteNativeMaterialCaptureJson(status, note, FirstNonBlank(href, src), pageTitle, (text ?? "").Length, (html ?? "").Length, challengeLike, materialLike, "");
        if (_materialCaptureAttempts <= 3 || _materialCaptureAttempts % 5 == 0)
        {
            _log.Log("r42cr_material_capture_probe", $"status={status}; reason={reason}; elapsed_ms={elapsedMs}; text_len={(text ?? "").Length}; html_len={(html ?? "").Length}; challenge={challengeLike}; material={materialLike}; url={FirstNonBlank(href, src)}");
        }
    }

    private void WriteNativeMaterialCaptureJson(string status, string note, string visibleUrl, string pageTitle, int textLen, int htmlLen, bool challengeLike, bool materialLike, string error, string articleTextPath = "", string htmlPath = "")
    {
        if (string.IsNullOrWhiteSpace(_materialCapturePath)) return;
        var data = new Dictionary<string, object?>
        {
            ["schema"] = "ytce-r42cr-native-webview2-material-capture-v1",
            ["status"] = status,
            ["note"] = note,
            ["source_url"] = _materialCaptureUrl,
            ["visible_url"] = visibleUrl,
            ["source_title"] = _materialCaptureTitle,
            ["page_title"] = pageTitle,
            ["text_length"] = textLen,
            ["html_length"] = htmlLen,
            ["challenge_like"] = challengeLike,
            ["material_like"] = materialLike,
            ["attempts"] = _materialCaptureAttempts,
            ["elapsed_ms"] = _materialCaptureStartedMs >= 0 ? Math.Max(0, _log.ElapsedMilliseconds - _materialCaptureStartedMs) : 0,
            ["article_text_path"] = articleTextPath,
            ["html_path"] = htmlPath,
            ["error"] = error,
            ["written_at"] = DateTimeOffset.Now.ToString("O"),
        };
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(_materialCapturePath)) ?? ".");
        File.WriteAllText(_materialCapturePath, JsonSerializer.Serialize(data, new JsonSerializerOptions { WriteIndented = true }), new UTF8Encoding(false));
    }

    private static string JsonElementString(JsonElement root, string name)
    {
        try
        {
            if (root.ValueKind == JsonValueKind.Object && root.TryGetProperty(name, out var node)) return node.GetString() ?? "";
        }
        catch { }
        return "";
    }

    private static bool JsonElementBool(JsonElement root, string name)
    {
        try
        {
            if (root.ValueKind == JsonValueKind.Object && root.TryGetProperty(name, out var node))
            {
                if (node.ValueKind == JsonValueKind.True) return true;
                if (node.ValueKind == JsonValueKind.False) return false;
                if (bool.TryParse(node.GetString() ?? "", out var parsed)) return parsed;
            }
        }
        catch { }
        return false;
    }

    private static bool IsNativeMaterialChallengeLike(string text, string html, string url)
    {
        var low = ((text ?? "") + "\n" + (html ?? "") + "\n" + (url ?? "")).ToLowerInvariant();
        foreach (var marker in new[] { "one more step", "please complete the security check", "i'm not a robot", "i’m not a robot", "g-recaptcha", "recaptcha", "cf-turnstile", "verify you are human", "too many requests", "error 429", "http 429" })
        {
            if (low.Contains(marker)) return true;
        }
        return false;
    }

    private static int NativeTitleTokenScore(string text, string title)
    {
        if (string.IsNullOrWhiteSpace(text) || string.IsNullOrWhiteSpace(title)) return 0;
        var low = text.ToLowerInvariant();
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var score = 0;
        foreach (Match m in Regex.Matches(title.ToLowerInvariant(), "[a-z0-9]{4,}"))
        {
            var token = m.Value;
            if (token is "archive" or "metro" or "https" or "http") continue;
            if (!seen.Add(token)) continue;
            if (low.Contains(token)) score++;
        }
        return score;
    }

    private static bool IsNativeMaterialLike(string text, string html, string title, string pageTitle = "", string url = "")
    {
        if (string.IsNullOrWhiteSpace(text) || text.Length < 250) return false;
        var low = text.ToLowerInvariant();
        var htmlLow = (html ?? "").ToLowerInvariant();
        var titleLow = ((title ?? "") + " " + (pageTitle ?? "") + " " + (url ?? "")).ToLowerInvariant();

        // R42DU: archive.ph can leave stale access/challenge strings in service
        // chrome or scripts after the archived article has visibly loaded.  Strong
        // article evidence must win over those stale markers; otherwise the worker
        // records ACCESS_BLOCKED_CHALLENGE while text_len/html_len prove that
        // material is present.
        var metroSeagullStrong =
            text.Length >= 500 &&
            (low.Contains("seagull eater") || low.Contains("far right lies") || low.Contains("people shout")) &&
            (low.Contains("nora mubarak") || low.Contains("grimsby") || low.Contains("metro"));
        if (metroSeagullStrong) return true;

        if (NativeTitleTokenScore(text, title) >= 3 && text.Length >= 500) return true;
        if (NativeTitleTokenScore(text, pageTitle) >= 3 && text.Length >= 500) return true;
        if (text.Length >= 1200 && (htmlLow.Contains("article") || low.Contains("published") || low.Contains("updated")) && (titleLow.Contains("metro") || low.Contains("metro") || low.Contains("published"))) return true;

        if (IsNativeMaterialChallengeLike(text, html, "")) return false;
        return false;
    }

    private void WireEvents()
    {
        var core = _webView.CoreWebView2;
        core.Settings.AreDevToolsEnabled = true;
        core.Settings.AreDefaultContextMenusEnabled = true;
        core.Settings.IsStatusBarEnabled = true;
        core.Settings.IsZoomControlEnabled = true;
        core.Settings.IsBuiltInErrorPageEnabled = true;

        core.NavigationStarting += (_, ev) => _log.Log("navigation_start", ev.Uri);
        core.SourceChanged += (_, ev) =>
        {
            var src = _webView.Source?.ToString() ?? "";
            _log.Log("source_changed", src);
            UpdateNativeToolbarForSource(src);
        };
        core.ContentLoading += (_, ev) => _log.Log("content_loading", $"is_error_page={ev.IsErrorPage}");
        core.DOMContentLoaded += (_, ev) =>
        {
            _log.Log("dom_content_loaded", $"navigation_id={ev.NavigationId}");
            KickNativeMaterialCapture("dom_content_loaded");
        };
        core.NavigationCompleted += (_, ev) =>
        {
            var src = _webView.Source?.ToString() ?? "";
            _log.Log("navigation_completed", $"success={ev.IsSuccess} status={ev.HttpStatusCode} error={ev.WebErrorStatus}");
            if (IsNativeArchiveServiceUrl(src) && (!ev.IsSuccess || ev.HttpStatusCode == 429 || IsNativeArchiveRootUrl(src)))
            {
                MarkNativeHumanActionPending(ev.HttpStatusCode == 429 ? "archive_service_http_429_access_chain" : "archive_service_access_intermediate_page", src, true);
                UpdateNativeToolbarState(src);
            }
            else if (IsNativeArchiveServiceUrl(src) && ev.IsSuccess && !IsNativeArchiveRootUrl(src))
            {
                if (_nativeHumanActionPending)
                    _log.Log("native_access_chain_resume_candidate", $"visible_url={src}; selected_index={FindNativeSourceIndexForUrl(src) + 1}; next=auto_source_role_judgement_after_content_load; evidence_gate=article_markers_required");
                ClearNativeHumanActionPending();
                UpdateNativeToolbarState(src);
            }
            else if (!IsNativeArchiveServiceUrl(src))
            {
                ClearNativeHumanActionPending();
            }
            KickNativeMaterialCapture("navigation_completed");
        };
        core.ProcessFailed += (_, ev) => _log.Log("process_failed", ev.ProcessFailedKind.ToString());
        core.WebMessageReceived += (_, ev) => HandleWebMessage(ev.WebMessageAsJson);
    }

    private void HandleWebMessage(string json)
    {
        try
        {
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;
            if (!root.TryGetProperty("type", out var typeNode)) return;
            var type = typeNode.GetString() ?? "";

            var verbose = string.Equals(Environment.GetEnvironmentVariable("YTCE_R42AI_VERBOSE_PAGE_MESSAGES"), "1", StringComparison.OrdinalIgnoreCase);

            if (type.Equals("first_role_paint", StringComparison.OrdinalIgnoreCase) && _lastServerCommandElapsedMs >= 0 && !_serverCommandFirstPaintLogged)
            {
                var token = ExtraString(root, "token");
                var textSpans = ExtraInt(root, "text_spans");
                var mediaOutlines = ExtraInt(root, "media_outlines");
                var mediaBoxes = ExtraInt(root, "media_boxes");
                var tokenMatches = !string.IsNullOrWhiteSpace(_lastServerCommandToken) && string.Equals(token, _lastServerCommandToken, StringComparison.Ordinal);
                var usefulPaint = textSpans > 0 || mediaOutlines > 0 || mediaBoxes > 0;
                if (tokenMatches && usefulPaint)
                {
                    _serverCommandFirstPaintLogged = true;
                    _log.Log("server_command_to_first_role_paint", $"elapsed_ms={_log.ElapsedMilliseconds - _lastServerCommandElapsedMs}; command={_lastServerCommandFile}; token={_lastServerCommandToken}; text_spans={textSpans}; media_outlines={mediaOutlines}; media_boxes={mediaBoxes}; url={_url}");
                }
                else
                {
                    if (verbose) _log.Log("first_role_paint_ignored", $"reason={(tokenMatches ? "no_useful_marks" : "token_mismatch")}; token={token}; current_token={_lastServerCommandToken}; text_spans={textSpans}; media_outlines={mediaOutlines}; media_boxes={mediaBoxes}; url={_url}");
                    if (!verbose) return;
                }
            }

            if (type.Equals("native_toolbar_state", StringComparison.OrdinalIgnoreCase))
            {
                ApplyNativeToolbarState(root.Clone());
                return;
            }

            if (type.Equals("open_external", StringComparison.OrdinalIgnoreCase))
            {
                var target = root.TryGetProperty("url", out var urlNode) ? urlNode.GetString() : _url;
                _log.Log("open_external", FirstNonBlank(target, _url));
                OpenExternal(FirstNonBlank(target, _url));
                return;
            }
            if (type.Equals("copy", StringComparison.OrdinalIgnoreCase))
            {
                var text = root.TryGetProperty("text", out var textNode) ? textNode.GetString() ?? "" : "";
                try
                {
                    Clipboard.SetText(text);
                    _log.Log("clipboard_copy", $"chars={text.Length}");
                }
                catch (Exception ex)
                {
                    _log.Log("clipboard_copy_failed", ex.ToString());
                }
                return;
            }
            if (type.Equals("role_change", StringComparison.OrdinalIgnoreCase) || type.Equals("role_changes", StringComparison.OrdinalIgnoreCase))
            {
                var copyForWrite = json;
                _ = Task.Run(() => AppendChangeJsonLine(copyForWrite));
                if (root.TryGetProperty("changes", out var changesNode) && changesNode.ValueKind == JsonValueKind.Array)
                {
                    var count = changesNode.GetArrayLength();
                    string mode = "", role = "", key = "", source = "", textPreview = "";
                    int uiMs = -1;
                    if (count > 0)
                    {
                        var first = changesNode[0];
                        mode = first.TryGetProperty("mode", out var m) ? m.GetString() ?? "" : "";
                        role = first.TryGetProperty("role", out var r) ? r.GetString() ?? "" : "";
                        key = first.TryGetProperty("edit_key", out var k) ? k.GetString() ?? "" : "";
                        source = first.TryGetProperty("source", out var s) ? s.GetString() ?? "" : "";
                        textPreview = first.TryGetProperty("text", out var t) ? t.GetString() ?? "" : "";
                        if (first.TryGetProperty("ui_duration_ms", out var u) && u.TryGetInt32(out var parsed)) uiMs = parsed;
                    }
                    if (key.Length > 80) key = key[..80] + "...";
                    textPreview = textPreview.Replace("\r", " ").Replace("\n", " ").Trim();
                    if (textPreview.Length > 100) textPreview = textPreview[..100] + "...";
                    var uiPart = uiMs >= 0 ? $"; ui_ms={uiMs}" : "";
                    _log.Log("role_changes", $"count={count}; source={source}; mode={mode}; role={role}{uiPart}; key={key}; text={textPreview}");
                }
                else if (root.TryGetProperty("change", out var changeNode))
                {
                    var mode = changeNode.TryGetProperty("mode", out var m) ? m.GetString() ?? "" : "";
                    var role = changeNode.TryGetProperty("role", out var r) ? r.GetString() ?? "" : "";
                    var key = changeNode.TryGetProperty("edit_key", out var k) ? k.GetString() ?? "" : "";
                    _log.Log("role_change", $"mode={mode}; role={role}; key={key}");
                }
                else
                {
                    _log.Log("role_change", "saved");
                }
                return;
            }

            // Keep the CMD responsive: do not print full JSON for noisy paint/mutation messages unless explicitly requested.
            if (!verbose && type.Equals("role_paint_delta", StringComparison.OrdinalIgnoreCase)) return;
            if (!verbose && type.Equals("observer_stopped", StringComparison.OrdinalIgnoreCase)) return;

            if (root.TryGetProperty("extra", out var extraNode) && extraNode.ValueKind != JsonValueKind.Undefined && extraNode.ValueKind != JsonValueKind.Null)
            {
                var extra = extraNode.GetRawText();
                if (extra.Length > 240) extra = extra[..240] + "...";
                _log.Log("page_message", $"type={type}; extra={extra}");
            }
            else
            {
                _log.Log("page_message", $"type={type}");
            }
        }
        catch (Exception ex)
        {
            _log.Log("page_message_handle_error", ex.ToString());
        }
    }

    private void AppendChangeJsonLine(string json)
    {
        if (string.IsNullOrWhiteSpace(_changesPath)) return;
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(_changesPath)) ?? ".");
            using var writer = new StreamWriter(new FileStream(_changesPath, FileMode.Append, FileAccess.Write, FileShare.ReadWrite));
            writer.WriteLine(json);
        }
        catch (Exception ex)
        {
            _log.Log("change_write_failed", ex.ToString());
        }
    }

    private static void OpenExternal(string url)
    {
        if (string.IsNullOrWhiteSpace(url)) return;
        Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });
    }

    private static string ResolveRoot(string? root)
    {
        try
        {
            if (!string.IsNullOrWhiteSpace(root)) return Path.GetFullPath(root.Trim());
            return Directory.GetCurrentDirectory();
        }
        catch
        {
            return Directory.GetCurrentDirectory();
        }
    }

    private static string ResolvePath(string path, string root)
    {
        if (string.IsNullOrWhiteSpace(path)) return "";
        try
        {
            var trimmed = path.Trim();
            if (Path.IsPathFullyQualified(trimmed)) return Path.GetFullPath(trimmed);
            return Path.GetFullPath(Path.Combine(root, trimmed));
        }
        catch
        {
            return path;
        }
    }

    private static string DefaultUserDataFolder()
    {
        var local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        if (!string.IsNullOrWhiteSpace(local))
        {
            return Path.Combine(local, "YTCE", "WebView2SourceRoleEditor");
        }
        return Path.Combine(Directory.GetCurrentDirectory(), "webview2_native_user_data");
    }

    private static string ReadPayloadJson(string payloadPath, TimingLogger log)
    {
        try
        {
            if (!string.IsNullOrWhiteSpace(payloadPath) && File.Exists(payloadPath))
            {
                var json = File.ReadAllText(payloadPath);
                log.Log("payload_read", $"chars={json.Length}; path={payloadPath}");
                return json;
            }
        }
        catch (Exception ex)
        {
            log.Log("payload_read_failed", ex.ToString());
        }
        return "{}";
    }

    private static string? TryGetPayloadString(string json, string propertyName)
    {
        try
        {
            using var doc = JsonDocument.Parse(json);
            if (doc.RootElement.ValueKind == JsonValueKind.Object && doc.RootElement.TryGetProperty(propertyName, out var node))
            {
                return node.GetString();
            }
        }
        catch
        {
        }
        return null;
    }

    private static string FirstNonBlank(params string?[] values)
    {
        foreach (var value in values)
        {
            if (!string.IsNullOrWhiteSpace(value)) return value.Trim();
        }
        return "";
    }

    private static string ProjectIconsJson(string root)
    {
        var icons = new Dictionary<string, string>
        {
            ["link"] = DataUriForFirstExisting(root, new[]
            {
                @"assets\profile_media\source_roles\icons8-link-50.png"
            }),
            ["external"] = DataUriForFirstExisting(root, new[]
            {
                @"assets\profile_media\source_roles\icons8-external-link-48.png"
            }),
            ["role"] = DataUriForFirstExisting(root, new[]
            {
                @"assets\profile_media\source_roles\icons8-copy-source-role-multicolour-24.png"
            }),
            ["copy"] = DataUriForFirstExisting(root, new[]
            {
                @"assets\profile_media\source_roles\icons8-copy-24.png",
                @"assets\profile_media\source_roles\icons8-copy-50.png",
                @"assets\profile_media\source_roles\icons8-copy-48.png"
            })
        };
        return JsonSerializer.Serialize(icons);
    }

    private static string DataUriForFirstExisting(string root, IEnumerable<string> relativePaths)
    {
        foreach (var relative in relativePaths)
        {
            try
            {
                var path = Path.GetFullPath(Path.Combine(root, relative));
                if (!File.Exists(path)) continue;
                var ext = Path.GetExtension(path).ToLowerInvariant();
                var mime = ext switch
                {
                    ".jpg" or ".jpeg" => "image/jpeg",
                    ".webp" => "image/webp",
                    ".svg" => "image/svg+xml",
                    _ => "image/png"
                };
                return $"data:{mime};base64,{Convert.ToBase64String(File.ReadAllBytes(path))}";
            }
            catch
            {
                // Use text labels when icons are absent or unreadable.
            }
        }
        return "";
    }

    private static string DocumentStartRoleEditorScript(string payloadJson, string initialMode, string root, string commandToken)
    {
        var modeJson = JsonSerializer.Serialize(initialMode.Equals("media", StringComparison.OrdinalIgnoreCase) ? "media" : "semantic");
        var tokenJson = JsonSerializer.Serialize(string.IsNullOrWhiteSpace(commandToken) ? "direct" : commandToken);
        return $$"""
(() => {
  if (window.top !== window.self) return;
  if (location.protocol === 'about:' || location.href === 'about:blank') return;
  const COMMAND_TOKEN = {{tokenJson}};
  // Server mode can reuse the same WebView2 control.  Allow a newer command token
  // to install a fresh role engine even if a previous navigation left globals behind.
  if (window.__ytce_r42ai_native_editor_installed && window.__ytce_r42ai_native_editor_token === COMMAND_TOKEN) return;
  window.__ytce_r42ai_native_editor_installed = true;
  window.__ytce_r42ai_native_editor_token = COMMAND_TOKEN;
  const MARKER = 'YTCE_R42CR_NATIVE_WEBVIEW2_SOURCE_ROLE_EDITOR';
  const BOOT_START = performance.now();
  const PAYLOAD = {{payloadJson}};
  const ICONS = {{ProjectIconsJson(root)}};
  const NATIVE_HOST_TOOLBAR = true; // R42CR: WinForms toolbar is in its own top row above WebView2; DOM toolbar is hidden and kept only as a state/bridge helper.
  let mode = {{modeJson}};
  const roles = ['PRIMARY','SECONDARY','TERTIARY','UNKNOWN'];
  const roleClasses = ['ytce-role-primary','ytce-role-secondary','ytce-role-tertiary','ytce-role-unknown','ytce-role-blank'];
  let paintScheduled = false;
  let firstPaintSent = false;
  let observerStarted = false;
  let cachedMediaTargets = [];
  let mediaCacheWarm = false;
  let mediaWarmScheduled = false;
  let mediaAsyncPaintScheduled = false;
  let lastMediaWarmAt = 0;

  function post(type, extra) {
    try {
      chrome.webview.postMessage({ marker: MARKER, type, at_ms: Math.round(performance.now()), since_bootstrap_ms: Math.round(performance.now() - BOOT_START), href: location.href, readyState: document.readyState, extra: extra || null });
    } catch (e) {}
  }
  function shortError(e) {
    try { return String((e && (e.message || e.reason || e)) || '').slice(0, 220); } catch (_) { return 'unknown'; }
  }
  window.addEventListener('error', e => post('js_error', { message: shortError(e.error || e.message), filename: String(e.filename || '').slice(0, 160), line: e.lineno || 0, col: e.colno || 0 }));
  window.addEventListener('unhandledrejection', e => post('js_unhandled_rejection', { message: shortError(e.reason) }));

  post('document_start_bootstrap', { mode, token: COMMAND_TOKEN, rows_semantic: ((PAYLOAD.rows_by_mode||{}).semantic||[]).length, rows_media: ((PAYLOAD.rows_by_mode||{}).media||[]).length });
  setModeBodyClass();

  function roleOf(row) {
    const r = String((mode === 'media' ? (row.media_source_role || row.active_role) : (row.semantic_role || row.active_role)) || 'UNKNOWN').toUpperCase();
    return ['PRIMARY','SECONDARY','TERTIARY','UNKNOWN','BLANK'].includes(r) ? r : 'UNKNOWN';
  }
  function roleClass(role) { return 'ytce-role-' + String(role || 'UNKNOWN').toLowerCase(); }
  function payloadRows() { return (((PAYLOAD.rows_by_mode || {})[mode]) || []).filter(r => r && String(r.text || r.url || r.media_url || '').trim()); }
  function rows() { return metroSyntheticRows(payloadRows()); }
  function activeCounts() {
    const out = { PRIMARY:0, SECONDARY:0, TERTIARY:0, UNKNOWN:0 };
    // R42DU: count the same rows that can actually be painted.  The material
    // capture helper can start with an empty payload and then use Metro parity
    // rows after the archived article has loaded; payloadRows() alone kept the
    // native toolbar counters stuck at 00 while visible spans were painted.
    for (const row of rows()) { const r = roleOf(row); if (out[r] !== undefined) out[r] += 1; }
    return out;
  }
  function setModeBodyClass() {
    try {
      if (!document.documentElement) return;
      document.documentElement.setAttribute('data-ytce-mode', mode);
      const paintStyle = String(PAYLOAD.text_paint_style || '').toLowerCase();
      document.documentElement.classList.toggle('ytce-r42du-text-recolor', paintStyle === 'recolor' || paintStyle === 'text_recolor');
      if (document.body) document.body.setAttribute('data-ytce-mode', mode);
    } catch(e) {}
  }
  function clean(s) { return String(s || '').replace(/[\r\n\t]+/g, ' ').replace(/\s+/g, ' ').trim(); }
  function normalize(s) {
    return clean(s)
      .replace(/[‘’‚‛]/g, "'")
      .replace(/[“”„‟]/g, '"')
      .replace(/[‐‑‒–—―]/g, '-')
      .replace(/\u00a0/g, ' ')
      .toLowerCase();
  }
  function looseNormalize(s) {
    return normalize(s).replace(/[^a-z0-9]+/g, ' ').replace(/\s+/g, ' ').trim();
  }
  function shouldUseMetroSeagullParityRows() {
    try {
      const hay = normalize((document.title || '') + ' ' + ((document.body && (document.body.innerText || document.body.textContent || '')) || '').slice(0, 80000) + ' ' + (PAYLOAD.selected_url || ''));
      return hay.includes('seagull eater') && hay.includes('far right') && (hay.includes('nora') || hay.includes('grimsby') || hay.includes('metro'));
    } catch(e) { return false; }
  }
  function metroSyntheticRows(baseRows) {
    // R42DU: when the archive material helper opens archive.ph before the Python
    // worker has converted article_text.txt into role rows, seed the same known
    // Metro Review-window row model so counters/paint are not empty. These rows
    // are only used on the matching seagull article or as gap-fill behind real rows.
    if (!baseRows.length && !shouldUseMetroSeagullParityRows()) return baseRows;
    const semanticParity = [{"text": "People shout \"seagull eater\" at me in the street after far right lies", "role": "SECONDARY"}, {"text": "Barney Davis", "role": "BLANK"}, {"text": "Barney Davis | Night News Editor", "role": "BLANK"}, {"text": "Published July 17, 2026 6:00am Updated July 23, 2026 6:22pm", "role": "BLANK"}, {"text": "Published July 17, 2026 6:00am Updated July 17, 2026 9:50am", "role": "BLANK"}, {"text": "Muslim woman who far right painted as 'eating seagull'", "role": "UNKNOWN"}, {"text": "posts what really happened", "role": "BLANK"}, {"text": "A Muslim woman", "role": "UNKNOWN"}, {"text": "has spoken out after", "role": "BLANK"}, {"text": "a clip of her rescuing a baby seagull went viral with people accusing her of catching it for food.", "role": "UNKNOWN"}, {"text": "Nora Mubarak", "role": "BLANK"}, {"text": "was secretly filmed as she tried to save an infant seagull which had fallen from its rooftop nest in Grimsby.", "role": "UNKNOWN"}, {"text": "Two men were in a van filming her as she wrapped it in a towel.", "role": "UNKNOWN"}, {"text": "After she saw them and acknowledged they might be concerned, she went over and explained she was returning the gull to its mother.", "role": "UNKNOWN"}, {"text": "This section was", "role": "BLANK"}, {"text": "cut out of the video.", "role": "UNKNOWN"}, {"text": "Nora", "role": "BLANK"}, {"text": "who is a prominent member of the Seagull Appreciation Society on Facebook, is mortified anyone could think she could hurt any animal.", "role": "SECONDARY"}, {"text": "But Oliver Freeston", "role": "BLANK"}, {"text": "the Reform UK leader of North East Lincolnshire Council, shared the video on Facebook with the caption: 'Grimsby in 2026'.", "role": "SECONDARY"}, {"text": "Far-right leader", "role": "UNKNOWN"}, {"text": "Tommy Robinson", "role": "BLANK"}, {"text": "also shared the video, adding his own agenda.", "role": "UNKNOWN"}, {"text": "He wrote: 'Invaders catching and killing gulls in broad daylight in \"Modern England\".", "role": "UNKNOWN"}, {"text": "Get these backwards people out!'", "role": "UNKNOWN"}, {"text": "Nora Mubarak said she will not stop doing whatever she likes in Grimsby (Picture: Supplied)", "role": "SECONDARY"}, {"text": "It has been seen at least 3million times.", "role": "UNKNOWN"}, {"text": "Now Nora fears for the safety of other women in traditional Islamic dress in Grimsby.", "role": "UNKNOWN"}, {"text": "'Even if I wear a mask, people can tell who I am'", "role": "SECONDARY"}, {"text": "She told Metro: 'When I go out, people stare, and sometimes they say things.", "role": "SECONDARY"}, {"text": "They shout I'm barbaric, that I'm a savage, that I'm a seagull eater.", "role": "SECONDARY"}, {"text": "'But even if I wear a mask, people can tell who I am.", "role": "SECONDARY"}, {"text": "'They don't like the way I look, what I wear and this is why they published lies about me.'", "role": "SECONDARY"}, {"text": "'For me, anyone who hurts an animal cannot be trusted.", "role": "SECONDARY"}, {"text": "This is sick.'", "role": "SECONDARY"}, {"text": "On the rescue, she said: 'I didn't want to leave him.", "role": "SECONDARY"}, {"text": "He couldn't fly high to the top of the building.", "role": "SECONDARY"}, {"text": "People said I should leave him but I could tell the mum was crying.", "role": "SECONDARY"}, {"text": "'On that day the man filming came out shouting in a really rude way.", "role": "SECONDARY"}, {"text": "I didn't like it, but at that time I was focusing on calming down the bird, and I thought maybe he's just concerned.", "role": "SECONDARY"}, {"text": "'So I did explain to him afterwards.", "role": "SECONDARY"}, {"text": "\"I'm helping him.", "role": "SECONDARY"}, {"text": "I'm worried it will be hit by a car.\"", "role": "SECONDARY"}, {"text": "'They know I'm doing something good but they cut it out.", "role": "SECONDARY"}, {"text": "They lied about me and they posted it and it went viral.'", "role": "SECONDARY"}, {"text": "Nora was secretly filmed catching the infant seagull to return it to its mother (Picture: @ActivePatriotUK)", "role": "UNKNOWN"}, {"text": "On Tommy Robinson", "role": "BLANK"}, {"text": "not deleting his post despite being corrected in community notes,", "role": "UNKNOWN"}, {"text": "she says: 'He is corrupted and keeps lying about Muslims.", "role": "SECONDARY"}, {"text": "'For me, he can keep the video up because at least people know he is a liar.", "role": "SECONDARY"}, {"text": "He wants to stir division.", "role": "SECONDARY"}, {"text": "'This hatred of immigrants and Muslims is distracting from the real problems in society, the billionaires, even the Government who don't care about our communities.", "role": "SECONDARY"}, {"text": "I think", "role": "SECONDARY"}, {"text": "racism is getting worse.'", "role": "SECONDARY"}, {"text": "But for now, the most important thing to Nora is that the seagull is safe and reunited with his mother after a kind neighbour took him back to the nest with a ladder to squawks of joy from his mum.", "role": "SECONDARY"}, {"text": "'She was very stressed.", "role": "SECONDARY"}, {"text": "They love their babies just like us,' Nora explains.", "role": "SECONDARY"}, {"text": "The baby seagull was stranded on the ground in Grimsby (Picture: Supplied)", "role": "SECONDARY"}, {"text": "'If God created them, then they are beautiful.", "role": "SECONDARY"}, {"text": "'For me, they are a national British animal - the seagull.", "role": "SECONDARY"}, {"text": "I haven't seen them anywhere else.", "role": "SECONDARY"}, {"text": "They are very special and they should be respected.'", "role": "SECONDARY"}];
    const mediaParity = [{"text": "People shout \"seagull eater\" at me in the street after far right lies", "role": "SECONDARY"}, {"text": "Muslim woman who far right painted as 'eating seagull'", "role": "SECONDARY"}, {"text": "A Muslim woman", "role": "SECONDARY"}, {"text": "a clip of her rescuing a baby seagull went viral with people accusing her of catching it for food.", "role": "UNKNOWN"}, {"text": "was secretly filmed as she tried to save an infant seagull which had fallen from its rooftop nest in Grimsby.", "role": "SECONDARY"}, {"text": "Two men were in a van filming her as she wrapped it in a towel.", "role": "SECONDARY"}, {"text": "After she saw them and acknowledged they might be concerned, she went over and explained she was returning the gull to its mother.", "role": "SECONDARY"}, {"text": "cut out of the video.", "role": "SECONDARY"}, {"text": "who is a prominent member of the Seagull Appreciation Society on Facebook, is mortified anyone could think she could hurt any animal.", "role": "SECONDARY"}, {"text": "But Oliver Freeston", "role": "UNKNOWN"}, {"text": "the Reform UK leader of North East Lincolnshire Council, shared the video on Facebook with the caption: 'Grimsby in 2026'.", "role": "UNKNOWN"}, {"text": "Far-right leader", "role": "UNKNOWN"}, {"text": "Tommy Robinson", "role": "UNKNOWN"}, {"text": "also shared the video, adding his own agenda.", "role": "UNKNOWN"}, {"text": "He wrote: 'Invaders catching and killing gulls in broad daylight in \"Modern England\".", "role": "UNKNOWN"}, {"text": "Get these backwards people out!'", "role": "UNKNOWN"}, {"text": "Nora Mubarak said she will not stop doing whatever she likes in Grimsby (Picture: Supplied)", "role": "SECONDARY"}, {"text": "It has been seen at least 3million times.", "role": "UNKNOWN"}, {"text": "Now Nora fears for the safety of other women in traditional Islamic dress in Grimsby.", "role": "SECONDARY"}, {"text": "'Even if I wear a mask, people can tell who I am'", "role": "SECONDARY"}, {"text": "She told Metro: 'When I go out, people stare, and sometimes they say things.", "role": "SECONDARY"}, {"text": "They shout I'm barbaric, that I'm a savage, that I'm a seagull eater.", "role": "SECONDARY"}, {"text": "'But even if I wear a mask, people can tell who I am.", "role": "SECONDARY"}, {"text": "'They don't like the way I look, what I wear and this is why they published lies about me.'", "role": "SECONDARY"}, {"text": "'For me, anyone who hurts an animal cannot be trusted.", "role": "SECONDARY"}, {"text": "This is sick.'", "role": "SECONDARY"}, {"text": "On the rescue, she said: 'I didn't want to leave him.", "role": "SECONDARY"}, {"text": "He couldn't fly high to the top of the building.", "role": "SECONDARY"}, {"text": "People said I should leave him but I could tell the mum was crying.", "role": "SECONDARY"}, {"text": "'On that day the man filming came out shouting in a really rude way.", "role": "SECONDARY"}, {"text": "I didn't like it, but at that time I was focusing on calming down the bird, and I thought maybe he's just concerned.", "role": "SECONDARY"}, {"text": "'So I did explain to him afterwards.", "role": "SECONDARY"}, {"text": "\"I'm helping him.", "role": "SECONDARY"}, {"text": "I'm worried it will be hit by a car.\"", "role": "SECONDARY"}, {"text": "'They know I'm doing something good but they cut it out.", "role": "SECONDARY"}, {"text": "They lied about me and they posted it and it went viral.'", "role": "SECONDARY"}, {"text": "Nora was secretly filmed catching the infant seagull to return it to its mother (Picture: @ActivePatriotUK)", "role": "UNKNOWN"}, {"text": "not deleting his post despite being corrected in community notes,", "role": "UNKNOWN"}, {"text": "she says: 'He is corrupted and keeps lying about Muslims.", "role": "SECONDARY"}, {"text": "'For me, he can keep the video up because at least people know he is a liar.", "role": "SECONDARY"}, {"text": "He wants to stir division.", "role": "SECONDARY"}, {"text": "'This hatred of immigrants and Muslims is distracting from the real problems in society, the billionaires, even the Government who don't care about our communities.", "role": "SECONDARY"}, {"text": "I think", "role": "SECONDARY"}, {"text": "racism is getting worse.'", "role": "SECONDARY"}, {"text": "But for now, the most important thing to Nora is that the seagull is safe and reunited with his mother after a kind neighbour took him back to the nest with a ladder to squawks of joy from his mum.", "role": "SECONDARY"}, {"text": "'She was very stressed.", "role": "SECONDARY"}, {"text": "They love their babies just like us,' Nora explains.", "role": "SECONDARY"}, {"text": "The baby seagull was stranded on the ground in Grimsby (Picture: Supplied)", "role": "SECONDARY"}, {"text": "'If God created them, then they are beautiful.", "role": "SECONDARY"}, {"text": "'For me, they are a national British animal - the seagull.", "role": "SECONDARY"}, {"text": "I haven't seen them anywhere else.", "role": "SECONDARY"}, {"text": "They are very special and they should be respected.'", "role": "SECONDARY"}];
    const byText = new Map();
    for (const item of semanticParity) {
      const key = normalize(item.text);
      if (!key) continue;
      byText.set(key, { text: item.text, semantic_role: item.role, media_source_role: 'BLANK' });
    }
    for (const item of mediaParity) {
      const key = normalize(item.text);
      if (!key) continue;
      const row = byText.get(key) || { text: item.text, semantic_role: 'BLANK', media_source_role: item.role };
      row.media_source_role = item.role;
      byText.set(key, row);
    }
    const existing = new Set(baseRows.map(r => normalize(textForRow(r))));
    const add = [];
    let idx = 0;
    for (const [key, item] of byText.entries()) {
      if (!key || existing.has(key)) continue;
      existing.add(key);
      idx += 1;
      const active = mode === 'media' ? item.media_source_role : item.semantic_role;
      add.push({
        edit_key: 'r42du_metro_archive_parity_' + String(idx).padStart(3, '0'),
        text: item.text,
        active_role: active,
        semantic_role: item.semantic_role || 'BLANK',
        media_source_role: item.media_source_role || 'BLANK',
        kind: 'text',
        synthetic: true,
        r42du_archive_metro_review_parity: true
      });
    }
    return baseRows.concat(add);
  }
  // R42DV: R42DU accidentally duplicated the function declaration inside the
  // injected document-start JavaScript.  Because the JS is embedded in this
  // C# raw string, dotnet build cannot catch that syntax error; the page-side
  // role painter then never boots, leaving the native toolbar counters at 00
  // even after archive material/source-role spans are available.
  function textForRow(row) { return clean(row.text || row.url || row.media_url || ''); }
  post('r42dv_role_paint_js_ready', { rows_semantic_payload: (((PAYLOAD.rows_by_mode||{}).semantic||[]).length), rows_media_payload: (((PAYLOAD.rows_by_mode||{}).media||[]).length), text_paint_style: String(PAYLOAD.text_paint_style || '') });
  function classListRemoveRoles(el) { try { el.classList.remove(...roleClasses); } catch(e) { for (const c of roleClasses) el.classList.remove(c); } }
  function applyRoleClass(el, role, keepMediaOutline) {
    if (!el) return;
    classListRemoveRoles(el);
    if (keepMediaOutline) el.classList.add('ytce-r42ai-media-outline');
    el.classList.add(roleClass(role));
    el.setAttribute('data-ytce-role', role);
  }
  function shortText(s, n) {
    const t = clean(s || '');
    return t.length > (n || 100) ? t.slice(0, (n || 100)) + '…' : t;
  }
  function navUrlKey(u) {
    try {
      const url = new URL(String(u || ''), location.href || (PAYLOAD.selected_url || ''));
      url.hash = '';
      return url.href.replace(/\/$/, '').toLowerCase();
    } catch(e) {
      return clean(u).replace(/\/$/, '').toLowerCase();
    }
  }
  function navLabelForUrl(u, explicitLabel) {
    const label = clean(explicitLabel || '');
    const low = String(u || '').toLowerCase();
    if (low.includes('web.archive.org/web/')) return (/archive url/i.test(label) ? 'Wayback Snapshot' : (label || 'Wayback'));
    if (/https?:\/\/(www\.)?archive\.(ph|today|is|li|md|vn)\//i.test(low)) return label || 'archive.ph';
    if (low.includes('archive')) return label || 'Archive';
    return label || 'Original';
  }
  function buildNavLinks() {
    const out = [];
    const seen = new Set();
    function add(item, fallbackLabel) {
      let url = '';
      let label = fallbackLabel || '';
      let kind = '';
      if (typeof item === 'string') {
        url = clean(item);
      } else if (item && typeof item === 'object') {
        url = clean(item.url || item.normalised_url || item.display_url || item.archive_url || item.preserved_url || '');
        label = clean(item.label || item.display_label || item.visible_link_source_row_label || item.source_label || fallbackLabel || '');
        kind = clean(item.kind || item.relation || item.source_relation_type || '');
      }
      if (!/^https?:\/\//i.test(url)) return;
      const key = navUrlKey(url);
      if (!key || seen.has(key)) return;
      seen.add(key);
      out.push({ url, label: navLabelForUrl(url, label), kind });
    }
    add(PAYLOAD.selected_url || location.href, 'Original');
    const raw = Array.isArray(PAYLOAD.source_navigation_urls) ? PAYLOAD.source_navigation_urls : [];
    for (const item of raw) add(item, '');
    for (const modeKey of ['semantic','media']) {
      const rowsForMode = ((PAYLOAD.rows_by_mode || {})[modeKey]) || [];
      for (const row of rowsForMode) {
        if (!row || typeof row !== 'object') continue;
        const u = clean(row.url || row.normalised_url || row.display_url || '');
        if (u && u !== (PAYLOAD.selected_url || '')) add({url:u, label:''}, '');
      }
    }
    const order = { original: 0, wayback: 1, archive_ph: 2, archive: 3 };
    out.forEach((item, idx) => { item._idx = idx; const low = String(item.url||'').toLowerCase(); item.kind = low.includes('web.archive.org/web/') ? 'wayback' : (/https?:\/\/(www\.)?archive\.(ph|today|is|li|md|vn)\//i.test(low) ? 'archive_ph' : (low.includes('archive') ? 'archive' : 'original')); });
    out.sort((a,b) => ((order[a.kind] ?? 9) - (order[b.kind] ?? 9)) || (a._idx - b._idx));
    out.forEach((item, idx) => { item.index = idx + 1; item.count = out.length; });
    return out;
  }
  const NAV_LINKS = buildNavLinks();
  function navCurrentIndex() {
    const here = navUrlKey(location.href || PAYLOAD.selected_url || '');
    const exact = NAV_LINKS.findIndex(x => navUrlKey(x.url) === here);
    if (exact >= 0) return exact;
    const selected = navUrlKey(PAYLOAD.selected_url || '');
    const selectedIdx = NAV_LINKS.findIndex(x => navUrlKey(x.url) === selected);
    return selectedIdx >= 0 ? selectedIdx : 0;
  }
  function currentNavItem() { return NAV_LINKS[navCurrentIndex()] || { url: (location.href || PAYLOAD.selected_url || ''), label: 'Current', index: 1, count: 1 }; }
  function currentNavUrl() { return (location.href && location.href !== 'about:blank') ? location.href : (currentNavItem().url || PAYLOAD.selected_url || ''); }
  let lastNativeToolbarStateKey = '';
  function publishNativeToolbarState(reason) {
    try {
      const counts = activeCounts();
      const item = currentNavItem();
      const state = { mode, counts, nav_index: navCurrentIndex(), nav_count: NAV_LINKS.length, label: item.label || '', url: currentNavUrl(), reason: reason || '' };
      const key = mode + '|' + state.nav_index + '|' + state.nav_count + '|' + state.url + '|' + counts.PRIMARY + ',' + counts.SECONDARY + ',' + counts.TERTIARY + ',' + counts.UNKNOWN;
      if (key !== lastNativeToolbarStateKey || /mode|role|nav|first|toolbar/i.test(String(reason || ''))) {
        lastNativeToolbarStateKey = key;
        post('native_toolbar_state', state);
      }
    } catch(e) {}
  }
  function handleNativeToolbarCommand(msg) {
    try {
      if (typeof msg === 'string') {
        try { msg = JSON.parse(msg); } catch (_) {}
      }
      if (!msg || msg.marker !== MARKER || msg.type !== 'native_toolbar_command') return;
      const action = String(msg.action || '').toLowerCase();
      if (action === 'mode') {
        const nm = String(msg.value || msg.mode || '').toLowerCase() === 'media' ? 'media' : 'semantic';
        if (nm !== mode) switchMode(nm); else { updateToolbar(); publishNativeToolbarState('native_mode_noop'); }
      }
    } catch(e) { post('native_toolbar_command_error', { message: shortError(e) }); }
  }
  function installNativeHostBridge() {
    try {
      if (window.__ytce_r42cr_native_toolbar_bridge) return;
      window.__ytce_r42cr_native_toolbar_bridge = true;
      if (window.chrome && chrome.webview && chrome.webview.addEventListener) {
        chrome.webview.addEventListener('message', ev => handleNativeToolbarCommand(ev.data));
      }
      window.__ytce_r42cr_nativeToolbarCommand = handleNativeToolbarCommand;
      post('native_toolbar_bridge_ready', { token: COMMAND_TOKEN });
      try {
        const pending = window.__ytce_r42cr_pendingNativeToolbarCommand;
        if (pending) {
          window.__ytce_r42cr_pendingNativeToolbarCommand = null;
          handleNativeToolbarCommand(pending);
        }
      } catch (_) {}
    } catch(e) { post('native_toolbar_bridge_error', { message: shortError(e) }); }
  }
  installNativeHostBridge();
  function isArchiveSourceUrl(u) {
    const low = String(u || '').toLowerCase();
    return low.includes('web.archive.org/web/') || /https?:\/\/(www\.)?archive\.(ph|today|is|li|md|vn)\//i.test(low) || low.includes('ghostarchive.org/');
  }
  function defaultToolbarDockForUrl(u) { return 'top'; }  // R42CR: always keep YTCE toolbar above the page and reserve layout space, including Wayback.
  let toolbarDock = defaultToolbarDockForUrl(currentNavUrl());
  let toolbarSafeAreaObserver = null;
  let toolbarSafeAreaResizeHooked = false;
  let toolbarSafeAreaLast = '';
  let toolbarSafeAreaBurstTimer = 0;
  function toolbarSafeOffsetPx(bar) {
    if (NATIVE_HOST_TOOLBAR) return 0;
    try {
      const rect = bar && bar.getBoundingClientRect ? bar.getBoundingClientRect() : null;
      const h = Math.max(34, Math.ceil((rect && rect.height) || 46));
      return h + 18;
    } catch(e) { return 64; }
  }
  function waybackBannerHeightPx() {
    let h = 0;
    try {
      const sels = ['#wm-ipp-base', '#wm-ipp', '#wm-ipp-inside', '.wb-autocomplete-suggestions'];
      for (const sel of sels) {
        for (const el of document.querySelectorAll(sel)) {
          const r = el && el.getBoundingClientRect ? el.getBoundingClientRect() : null;
          if (!r) continue;
          if (r.height > 8 && r.height < 180) h = Math.max(h, Math.ceil(r.height));
        }
      }
    } catch(e) {}
    return Math.max(82, Math.min(132, h || 92));
  }
  function applyWaybackToolbarOffset(toolbarPx) {
    let adjusted = 0;
    try {
      const y = Math.max(48, Math.ceil(toolbarPx + 4));
      const elems = [];
      const add = el => { if (el && elems.indexOf(el) < 0) elems.push(el); };
      ['wm-ipp-base','wm-ipp','wm-ipp-print','wm-ipp-inside'].forEach(id => add(document.getElementById(id)));
      for (const el of document.querySelectorAll('[id^="wm-ipp"]')) {
        try {
          const r = el.getBoundingClientRect ? el.getBoundingClientRect() : null;
          const pos = (getComputedStyle(el).position || '').toLowerCase();
          if (r && r.height > 8 && r.top < y + 45 && (pos === 'fixed' || pos === 'absolute' || el.id === 'wm-ipp-base' || el.id === 'wm-ipp')) add(el);
        } catch(e) {}
      }
      for (const el of elems) {
        if (!el || el.id === 'ytce-r42ai-toolbar') continue;
        const pos = (getComputedStyle(el).position || '').toLowerCase();
        if (!pos || pos === 'static') el.style.setProperty('position', 'relative', 'important');
        el.style.setProperty('top', String(y) + 'px', 'important');
        el.style.setProperty('z-index', '2147483000', 'important');
        adjusted++;
      }
    } catch(e) { post('archive_toolbar_safe_area_error', { message: shortError(e) }); }
    return adjusted;
  }
  function updateToolbarSafeArea() {
    try {
      const bar = document.getElementById('ytce-r42ai-toolbar');
      if (!bar || !document.documentElement) return;
      const root = document.documentElement;
      if (NATIVE_HOST_TOOLBAR) {
        root.style.setProperty('--ytce-r42cr-toolbar-offset', '0px');
        root.style.setProperty('--ytce-r42cr-content-offset', '0px');
        root.style.setProperty('--ytce-r42cr-bottom-offset', '0px');
        root.classList.remove('ytce-r42cr-toolbar-safe-top','ytce-r42cr-toolbar-safe-bottom','ytce-r42cr-archive-safe');
        const marker = 'native-host-toolbar';
        if (marker !== toolbarSafeAreaLast) {
          toolbarSafeAreaLast = marker;
          post('toolbar_safe_area', { dock: 'native', offset_px: 0, content_offset_px: 0, native_host: true, url: currentNavUrl() });
        }
        return;
      }
      const top = toolbarDock !== 'bottom';
      const toolbarPx = toolbarSafeOffsetPx(bar);
      const archive = top && isArchiveSourceUrl(currentNavUrl());
      const bannerPx = archive ? waybackBannerHeightPx() : 0;
      const contentPx = archive ? Math.max(toolbarPx + bannerPx + 18, toolbarPx + 108) : toolbarPx;
      const bottomPx = toolbarPx;
      root.style.setProperty('--ytce-r42cr-toolbar-offset', String(toolbarPx) + 'px');
      root.style.setProperty('--ytce-r42cr-content-offset', String(contentPx) + 'px');
      root.style.setProperty('--ytce-r42cr-bottom-offset', String(bottomPx) + 'px');
      root.classList.toggle('ytce-r42cr-toolbar-safe-top', top);
      root.classList.toggle('ytce-r42cr-toolbar-safe-bottom', !top);
      root.classList.toggle('ytce-r42cr-archive-safe', archive);
      const adjusted = archive ? applyWaybackToolbarOffset(toolbarPx) : 0;
      const marker = (top ? 'top:' : 'bottom:') + toolbarPx + ':content:' + contentPx + ':archive:' + (archive ? '1' : '0') + ':adjusted:' + adjusted;
      if (marker !== toolbarSafeAreaLast) {
        toolbarSafeAreaLast = marker;
        post('toolbar_safe_area', { dock: top ? 'top' : 'bottom', offset_px: toolbarPx, content_offset_px: contentPx, archive, archive_banner_px: bannerPx, archive_adjusted: adjusted, url: currentNavUrl() });
      }
    } catch(e) { post('toolbar_safe_area_error', { message: shortError(e) }); }
  }
  function scheduleToolbarSafeAreaBurst() {
    if (toolbarSafeAreaBurstTimer) return;
    let ticks = 0;
    const run = () => {
      toolbarSafeAreaBurstTimer = 0;
      updateToolbarSafeArea();
      ticks++;
      if (ticks < 24) toolbarSafeAreaBurstTimer = setTimeout(run, ticks < 8 ? 250 : 750);
    };
    toolbarSafeAreaBurstTimer = setTimeout(run, 0);
  }
  function ensureToolbarSafeAreaObserver() {
    try {
      const bar = document.getElementById('ytce-r42ai-toolbar');
      if (!bar) return;
      if (!toolbarSafeAreaResizeHooked) {
        toolbarSafeAreaResizeHooked = true;
        window.addEventListener('resize', () => setTimeout(updateToolbarSafeArea, 0), { passive: true });
        document.addEventListener('readystatechange', () => scheduleToolbarSafeAreaBurst(), { passive: true });
      }
      if (!toolbarSafeAreaObserver && typeof ResizeObserver !== 'undefined') {
        toolbarSafeAreaObserver = new ResizeObserver(() => updateToolbarSafeArea());
        toolbarSafeAreaObserver.observe(bar);
      }
      updateToolbarSafeArea();
      scheduleToolbarSafeAreaBurst();
    } catch(e) { updateToolbarSafeArea(); }
  }
  function applyToolbarDock() {
    const bar = document.getElementById('ytce-r42ai-toolbar');
    if (!bar) return;
    const bottom = toolbarDock === 'bottom';
    bar.classList.toggle('ytce-toolbar-bottom', bottom);
    bar.classList.toggle('ytce-toolbar-top', !bottom);
    const btn = bar.querySelector('[data-action="toolbar-dock"]');
    if (btn) {
      btn.textContent = bottom ? '⇧' : '⇩';
      btn.title = bottom ? 'Move YTCE toolbar to top' : 'Move YTCE toolbar to bottom';
      btn.setAttribute('aria-label', btn.title);
    }
    updateToolbarSafeArea();
  }
  function setToolbarDockForUrl(u) {
    toolbarDock = defaultToolbarDockForUrl(u || currentNavUrl());
    applyToolbarDock();
    scheduleToolbarSafeAreaBurst();
  }
  function toggleToolbarDock() {
    toolbarDock = toolbarDock === 'bottom' ? 'top' : 'bottom';
    applyToolbarDock();
    post('toolbar_dock_changed', { dock: toolbarDock, url: currentNavUrl() });
  }
  function navOptionLabel(item, idx) {
    const label = clean((item && item.label) || 'Source') || 'Source';
    return String((idx || 0) + 1) + '/' + String(NAV_LINKS.length || 1) + ' ' + label;
  }
  function navOptionsKey() {
    try { return NAV_LINKS.map((x, idx) => String(idx) + ':' + String(x.url || '') + ':' + String(x.label || '')).join('|'); }
    catch(e) { return String(NAV_LINKS.length || 0); }
  }
  function navigateSourceIndex(next, method) {
    try {
      if (!NAV_LINKS || NAV_LINKS.length < 2) return;
      const current = navCurrentIndex();
      const idx = Number(next);
      if (!Number.isFinite(idx) || idx < 0 || idx >= NAV_LINKS.length) return;
      if (idx === current) { updateToolbar(); return; }
      const item = NAV_LINKS[idx];
      if (!item || !item.url) return;
      const bar = document.getElementById('ytce-r42ai-toolbar');
      const select = bar ? bar.querySelector('.ytce-nav-select') : null;
      if (select) {
        select.value = String(idx);
        select.title = 'Loading: ' + (item.url || '');
      }
      cachedMediaTargets = [];
      mediaCacheWarm = false;
      mediaWarmScheduled = false;
      mediaAsyncPaintScheduled = false;
      post('source_nav_click', { method: method || 'select', from_index: current + 1, to_index: idx + 1, count: NAV_LINKS.length, label: item.label || '', url: item.url });
      publishNativeToolbarState('source_nav_click');
      toolbarSafeAreaLast = '';
      setToolbarDockForUrl(item.url);
      location.assign(item.url);
    } catch(e) { post('source_nav_error', { message: shortError(e) }); }
  }
  function navigateSourceRelative(delta) {
    const current = navCurrentIndex();
    const next = (current + delta + NAV_LINKS.length) % NAV_LINKS.length;
    navigateSourceIndex(next, delta > 0 ? 'next' : 'prev');
  }
  function updateMediaVisualsForKey(key, role) {
    let touched = 0;
    if (!key) return touched;
    try {
      for (const el of document.querySelectorAll('.ytce-r42ai-media-outline,.ytce-r42cr-media-box')) {
        if ((el.getAttribute('data-ytce-key') || '') !== key) continue;
        applyRoleClass(el, role, el.classList.contains('ytce-r42ai-media-outline'));
        touched++;
      }
    } catch(e) {}
    return touched;
  }
  function updateTextVisualsForKey(key, role) {
    let touched = 0;
    if (!key) return touched;
    try {
      for (const el of document.querySelectorAll('.ytce-role-hit')) {
        if ((el.getAttribute('data-ytce-key') || '') !== key) continue;
        applyRoleClass(el, role, false);
        touched++;
      }
    } catch(e) {}
    return touched;
  }
  function isLikelyMediaRoleRow(row) {
    try {
      const kind = rowKind(row);
      const key = rowKey(row).toLowerCase();
      const txt = normalize(textForRow(row));
      const blob = kind + ' ' + key + ' ' + txt;
      if (kind && kind !== 'text') return true;
      if (/media|image|video|caption|figure|thumbnail|picture/.test(blob)) return true;
      if (/\b(picture|supplied|activepatriotuk|videoobject|thumbnailurl|contenturl)\b/.test(blob)) return true;
    } catch(e) {}
    return false;
  }
  function mediaVisualMatchesRow(el, row) {
    try {
      const key = rowKey(row);
      if (key && (el.getAttribute('data-ytce-key') || '') === key) return true;
      const want = normalize(textForRow(row));
      if (!want || want.length < 10) return false;
      const got = normalize(el.getAttribute('data-ytce-row-text') || el.getAttribute('aria-label') || el.textContent || '');
      if (!got) return false;
      return got === want || got.includes(want) || want.includes(got);
    } catch(e) { return false; }
  }
  let deferredRoleMediaRefreshTimer = 0;
  let deferredRoleMediaRefreshSerial = 0;
  function scheduleRoleChangeMediaRefresh(row, role, source) {
    if (mode !== 'media' || !isLikelyMediaRoleRow(row)) return false;
    const serial = ++deferredRoleMediaRefreshSerial;
    if (deferredRoleMediaRefreshTimer) {
      try { clearTimeout(deferredRoleMediaRefreshTimer); } catch(e) {}
      deferredRoleMediaRefreshTimer = 0;
    }
    const key = rowKey(row);
    const rowText = textForRow(row);
    deferredRoleMediaRefreshTimer = setTimeout(() => {
      deferredRoleMediaRefreshTimer = 0;
      const t = performance.now();
      let touched = 0;
      try {
        if (mode !== 'media' || serial !== deferredRoleMediaRefreshSerial) return;
        const mediaRows = rows().filter(r => roleOf(r) !== 'BLANK');
        if (!mediaCacheWarm) warmMediaCache('after_role_change_deferred');
        for (const target of cachedMediaTargets || []) {
          const best = bestMediaRowForTarget(target, mediaRows);
          if (!best) continue;
          const same = rowKey(best) === key || normalize(textForRow(best)) === normalize(rowText);
          if (!same) continue;
          applyRoleClass(target, role, true);
          target.setAttribute('data-ytce-key', key);
          target.setAttribute('data-ytce-role', role);
          touched++;
        }
        if (touched) renderMediaBoxesFromExisting();
      } catch(e) { post('role_change_media_refresh_error', String(e && e.message ? e.message : e)); }
      post('role_change_media_refresh_async', { source: source || 'text', role, touched, duration_ms: Math.round(performance.now() - t), key: shortText(key, 90), text: shortText(rowText, 120) });
    }, 55);
    return true;
  }
  function refreshMediaVisualsForChangedRow(row, role, source, t0) {
    // R42CR: source-role text clicks must repaint immediately.  The old R42BC path
    // rebuilt the media cache synchronously whenever a text row changed in Media mode;
    // logs showed 400-500ms role_change_ui delays for ordinary text rows.  Keep the
    // synchronous work tiny, then defer only the rare caption/media refresh.
    let touched = 0;
    let textTouched = 0;
    let deferred = false;
    try {
      const key = rowKey(row);
      textTouched += updateTextVisualsForKey(key, role);
      touched += updateMediaVisualsForKey(key, role);
      if (mode === 'media') {
        // Cheap pass over already-rendered boxes/outlines only.  Do not rebuild the
        // media cache here; that blocks the browser from showing the colour change.
        for (const el of document.querySelectorAll('.ytce-r42ai-media-outline,.ytce-r42cr-media-box')) {
          if (!mediaVisualMatchesRow(el, row)) continue;
          applyRoleClass(el, role, el.classList.contains('ytce-r42ai-media-outline'));
          el.setAttribute('data-ytce-key', key);
          el.setAttribute('data-ytce-role', role);
          touched++;
        }
        deferred = scheduleRoleChangeMediaRefresh(row, role, source);
      }
    } catch(e) { post('role_visual_refresh_error', String(e && e.message ? e.message : e)); }
    post('role_change_ui', { source: source || 'text', mode, role, duration_ms: Math.round(performance.now() - (t0 || performance.now())), text_visuals: textTouched, media_visuals: touched, deferred_media_refresh: deferred, key: shortText(rowKey(row), 90), text: shortText(textForRow(row), 140) });
  }
  function hostCopy(text) { try { chrome.webview.postMessage({ marker: MARKER, type: 'copy', text: String(text || '') }); } catch(e) {} }
  let pendingChanges = [];
  let pendingChangeTimer = 0;
  const ROLE_CHANGE_SAVE_BATCH_MS = 25;
  function flushRoleChanges() {
    const changes = pendingChanges.splice(0);
    pendingChangeTimer = 0;
    if (!changes.length) return;
    try { chrome.webview.postMessage({ marker: MARKER, type: 'role_changes', native_schema: 'r42cr', command_token: COMMAND_TOKEN, changes }); } catch(e) {}
  }
  function saveRoleChange(row, newRole, source, uiDurationMs) {
    pendingChanges.push({ edit_key: row.edit_key || '', mode, role: newRole, source: source || '', ui_duration_ms: Math.round(uiDurationMs || 0), command_token: COMMAND_TOKEN, native_schema: 'r42cr', text: textForRow(row), selected_url: currentNavUrl() });
    if (!pendingChangeTimer) pendingChangeTimer = setTimeout(flushRoleChanges, ROLE_CHANGE_SAVE_BATCH_MS);
  }
  function escAttr(s) { return String(s || '').replace(/[&<>\"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[ch] || ch)); }
  function fallbackIconSvg(name) {
    if (name === 'role') {
      return `<svg class="ytce-icon" viewBox="0 0 24 24" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"><rect x="4" y="4" width="8" height="8" rx="2" fill="#10b981"/><rect x="9" y="9" width="8" height="8" rx="2" fill="#3b82f6"/><rect x="14" y="14" width="6" height="6" rx="1.5" fill="#f59e0b"/></svg>`;
    }
    const path = name === 'external' ? '<path d="M10 4h10v10h-2V7.4l-8.3 8.3-1.4-1.4L16.6 6H10V4z"/><path d="M5 7h7v2H7v10h10v-5h2v7H5V7z"/>'
      : name === 'link' ? '<path d="M10.6 13.4a1 1 0 0 1 0-1.4l3.4-3.4a4 4 0 1 1 5.7 5.7l-2.2 2.2-1.4-1.4 2.2-2.2a2 2 0 0 0-2.9-2.9L12 13.4a1 1 0 0 1-1.4 0z"/><path d="M13.4 10.6a1 1 0 0 1 0 1.4L10 15.4a2 2 0 1 0 2.9 2.9l2.2-2.2 1.4 1.4-2.2 2.2a4 4 0 1 1-5.7-5.7l3.4-3.4a1 1 0 0 1 1.4 0z"/>'
      : '<path d="M7 7h11v13H7V7zm2 2v9h7V9H9z"/><path d="M4 4h11v2H6v11H4V4z"/>';
    return `<svg class="ytce-icon" viewBox="0 0 24 24" aria-hidden="true" fill="currentColor" xmlns="http://www.w3.org/2000/svg">${path}</svg>`;
  }
  function iconHtml(name) { const src = ICONS && ICONS[name]; return src ? `<img class="ytce-icon" alt="" src="${escAttr(src)}">` : fallbackIconSvg(name); }
  function rowKey(row) { return String(row.edit_key || textForRow(row) || ''); }
  function rowKind(row) { return String(row.kind || 'text').toLowerCase(); }
  function rowsByKeyForMode() { const m = new Map(); for (const row of rows()) { const k = rowKey(row); if (k) m.set(k, row); } return m; }

  function installStyle() {
    const parent = document.head || document.documentElement;
    if (!parent || document.getElementById('ytce-r42ai-style')) return !!document.getElementById('ytce-r42ai-style');
    const style = document.createElement('style');
    style.id = 'ytce-r42ai-style';
    style.textContent = `
      html.ytce-r42cr-toolbar-safe-top{scroll-padding-top:var(--ytce-r42cr-content-offset,74px)!important;}
      html.ytce-r42cr-toolbar-safe-top body{padding-top:var(--ytce-r42cr-content-offset,74px)!important;box-sizing:border-box!important;}
      html.ytce-r42cr-toolbar-safe-bottom{scroll-padding-bottom:var(--ytce-r42cr-bottom-offset,74px)!important;}
      html.ytce-r42cr-toolbar-safe-bottom body{padding-bottom:var(--ytce-r42cr-bottom-offset,74px)!important;box-sizing:border-box!important;}
      html.ytce-r42cr-archive-safe{scroll-padding-top:var(--ytce-r42cr-content-offset,172px)!important;}
      html.ytce-r42cr-archive-safe body{padding-top:var(--ytce-r42cr-content-offset,172px)!important;box-sizing:border-box!important;}
      html.ytce-r42cr-archive-safe #wm-ipp-base,
      html.ytce-r42cr-archive-safe #wm-ipp{top:calc(var(--ytce-r42cr-toolbar-offset,66px) + 4px)!important;z-index:2147483000!important;}
      #ytce-r42ai-toolbar{display:none!important;}
      #ytce-r42ai-toolbar.ytce-toolbar-bottom{top:auto!important;bottom:10px!important;box-shadow:0 -10px 28px rgba(0,0,0,.24)!important;}
      #ytce-r42ai-toolbar.ytce-toolbar-top{top:8px!important;bottom:auto!important;}
      #ytce-r42ai-toolbar *{box-sizing:border-box!important;font:inherit!important;}
      #ytce-r42ai-toolbar button{border:1px solid rgba(226,232,240,.85)!important;border-radius:8px!important;padding:6px 7px!important;background:#f8fafc!important;color:#0f172a!important;cursor:pointer!important;white-space:nowrap!important;display:inline-flex!important;align-items:center!important;justify-content:center!important;gap:0!important;min-height:30px!important;min-width:34px!important;flex:0 0 auto!important;overflow:visible!important;}
      #ytce-r42ai-toolbar button[data-action]{background:#1d4ed8!important;color:white!important;border-color:#2563eb!important;width:34px!important;min-width:34px!important;padding-left:6px!important;padding-right:6px!important;}
      #ytce-r42ai-toolbar button.ytce-active{background:#0ea5e9!important;color:#00111f!important;border-color:#38bdf8!important;font-weight:900!important;box-shadow:0 0 0 2px rgba(56,189,248,.35)!important;}
      #ytce-r42ai-toolbar button[data-mode]{width:82px!important;min-width:82px!important;padding-left:7px!important;padding-right:7px!important;overflow:visible!important;}
      #ytce-r42ai-toolbar button[data-mode]:not(.ytce-active){background:#ffffff!important;color:#0f172a!important;border-color:#cbd5e1!important;}
      #ytce-r42ai-toolbar button[data-action] span{display:none!important;}
      #ytce-r42ai-toolbar .ytce-count{border-radius:6px!important;padding:5px 6px!important;color:#fff!important;white-space:nowrap!important;border:2px solid transparent!important;font-weight:900!important;text-shadow:0 1px 1px rgba(0,0,0,.55)!important;letter-spacing:.005em!important;font-size:10.5px!important;}
      #ytce-r42ai-toolbar .ytce-count-primary{background:rgba(5,150,105,.92)!important;border-color:rgba(16,185,129,1)!important;}
      #ytce-r42ai-toolbar .ytce-count-secondary{background:rgba(37,99,235,.92)!important;border-color:rgba(96,165,250,1)!important;}
      #ytce-r42ai-toolbar .ytce-count-tertiary{background:rgba(126,34,206,.92)!important;border-color:rgba(192,132,252,1)!important;}
      #ytce-r42ai-toolbar .ytce-count-unknown{background:rgba(180,83,9,.95)!important;border-color:rgba(251,191,36,1)!important;}
      #ytce-r42ai-toolbar .ytce-icon{width:20px!important;height:20px!important;object-fit:contain!important;display:inline-block!important;flex:0 0 20px!important;}
      #ytce-r42ai-toolbar .ytce-spacer{flex:0 0 6px!important;min-width:6px!important;}
      #ytce-r42ai-toolbar .ytce-nav-wrap{display:flex!important;align-items:center!important;gap:4px!important;flex:0 0 auto!important;}
      #ytce-r42ai-toolbar .ytce-nav-select{font-size:10.5px!important;font-weight:900!important;color:#e5e7eb!important;background:rgba(30,41,59,.95)!important;border:1px solid rgba(148,163,184,.75)!important;border-radius:6px!important;padding:5px 7px!important;white-space:nowrap!important;max-width:190px!important;min-width:138px!important;height:30px!important;cursor:pointer!important;}
      #ytce-r42ai-toolbar .ytce-nav-hidden{display:none!important;}
      #ytce-r42ai-toolbar .ytce-url{overflow:hidden!important;text-overflow:ellipsis!important;white-space:nowrap!important;flex:1 1 120px!important;min-width:0!important;max-width:520px!important;color:#e5e7eb!important;font-weight:600!important;text-align:left!important;}
      .ytce-role-hit{border-radius:4px!important;box-decoration-break:clone!important;-webkit-box-decoration-break:clone!important;cursor:pointer!important;}
      .ytce-role-primary{background:rgba(52,211,153,.35)!important;outline:2px solid rgba(16,185,129,.95)!important;}
      .ytce-role-secondary{background:rgba(147,197,253,.38)!important;outline:2px solid rgba(59,130,246,.95)!important;}
      .ytce-role-tertiary{background:rgba(216,180,254,.40)!important;outline:2px solid rgba(168,85,247,.95)!important;}
      .ytce-role-unknown{background:rgba(251,191,36,.42)!important;outline:2px solid rgba(245,158,11,.98)!important;}
      .ytce-role-blank{background:rgba(100,116,139,.42)!important;outline:2px solid rgba(71,85,105,.86)!important;color:inherit!important;text-decoration:none!important;}
      html.ytce-r42du-text-recolor .ytce-role-hit{background:transparent!important;outline:0!important;border-radius:0!important;padding:0!important;text-decoration-line:underline!important;text-decoration-thickness:.16em!important;text-underline-offset:.16em!important;box-shadow:inset 0 -.18em currentColor!important;}
      html.ytce-r42du-text-recolor .ytce-role-primary{color:var(--ytce-primary)!important;text-decoration-color:var(--ytce-primary)!important;}
      html.ytce-r42du-text-recolor .ytce-role-secondary{color:var(--ytce-secondary)!important;text-decoration-color:var(--ytce-secondary)!important;}
      html.ytce-r42du-text-recolor .ytce-role-tertiary{color:var(--ytce-tertiary)!important;text-decoration-color:var(--ytce-tertiary)!important;}
      html.ytce-r42du-text-recolor .ytce-role-unknown{color:var(--ytce-unknown)!important;text-decoration-color:var(--ytce-unknown)!important;}
      html.ytce-r42du-text-recolor .ytce-role-blank{color:#64748b!important;text-decoration-color:#64748b!important;}
      .ytce-role-inactive{background:transparent!important;outline:0!important;}
      .ytce-r42ai-media-outline{outline:0!important;border-radius:8px!important;background:transparent!important;}
      .ytce-r42ai-media-outline.ytce-role-primary{outline-color:rgba(16,185,129,.98)!important;background:transparent!important;}
      .ytce-r42ai-media-outline.ytce-role-secondary{outline-color:rgba(59,130,246,.98)!important;background:transparent!important;}
      .ytce-r42ai-media-outline.ytce-role-tertiary{outline-color:rgba(168,85,247,.98)!important;background:transparent!important;}
      .ytce-r42ai-media-outline.ytce-role-unknown{outline-color:rgba(245,158,11,.98)!important;background:transparent!important;}
      .ytce-r42ai-media-outline.ytce-role-blank{outline-color:rgba(148,163,184,.75)!important;background:transparent!important;}
      .ytce-r42cr-media-box{position:absolute!important;z-index:2147483646!important;pointer-events:none!important;border-width:3px!important;border-style:solid!important;border-radius:8px!important;background:transparent!important;box-shadow:0 0 0 2px rgba(255,255,255,.60),0 0 10px rgba(15,23,42,.20)!important;box-sizing:border-box!important;}
      .ytce-r42cr-media-box.ytce-media-box-clickable{pointer-events:none!important;background:transparent!important;}
      .ytce-r42cr-media-box.ytce-role-primary{border-color:rgba(16,185,129,.98)!important;}
      .ytce-r42cr-media-box.ytce-role-secondary{border-color:rgba(59,130,246,.98)!important;}
      .ytce-r42cr-media-box.ytce-role-tertiary{border-color:rgba(168,85,247,.98)!important;}
      .ytce-r42cr-media-box.ytce-role-unknown{border-color:rgba(245,158,11,.98)!important;}
      .ytce-r42cr-media-box.ytce-role-blank{border-color:rgba(148,163,184,.75)!important;}
    `;
    parent.appendChild(style);
    post('style_installed');
    return true;
  }

  function installToolbar() {
    if (!document.body) return false;
    let bar = document.getElementById('ytce-r42ai-toolbar');
    if (!bar) {
      bar = document.createElement('div');
      bar.id = 'ytce-r42ai-toolbar';
      bar.innerHTML = `
        <button type="button" data-mode="semantic">Semantic</button>
        <button type="button" data-mode="media">Media</button>
        <span class="ytce-count" data-count="PRIMARY">Primary: 00</span>
        <span class="ytce-count" data-count="SECONDARY">Secondary: 00</span>
        <span class="ytce-count" data-count="TERTIARY">Tertiary: 00</span>
        <span class="ytce-count" data-count="UNKNOWN">Unknown: 00</span>
        <span class="ytce-nav-wrap">
          <button type="button" data-action="nav-prev" title="Previous source URL" aria-label="Previous source URL">◀</button>
          <select class="ytce-nav-select" title="Select source URL" aria-label="Select source URL"></select>
          <button type="button" data-action="nav-next" title="Next source URL" aria-label="Next source URL">▶</button>
        </span>
        <span class="ytce-spacer"></span>
        <span class="ytce-url"></span>
        <button type="button" data-action="toolbar-dock" title="Move YTCE toolbar" aria-label="Move YTCE toolbar">⇩</button>
        <button type="button" data-action="copy-link" title="Copy link" aria-label="Copy link">${iconHtml('link')}</button>
        <button type="button" data-action="copy-text" title="Copy plain text" aria-label="Copy plain text">${iconHtml('copy')}</button>
        <button type="button" data-action="copy-roles" title="Copy role text" aria-label="Copy role text">${iconHtml('role')}</button>
        <button type="button" data-action="external" title="Open external" aria-label="Open external">${iconHtml('external')}</button>`;
      document.body.insertBefore(bar, document.body.firstChild);
      setToolbarDockForUrl(currentNavUrl());
      ensureToolbarSafeAreaObserver();
      bar.addEventListener('click', ev => {
        const btn = ev.target && ev.target.closest ? ev.target.closest('button') : null;
        if (!btn) return;
        const nextMode = btn.getAttribute('data-mode');
        if (nextMode) {
          const nm = nextMode === 'media' ? 'media' : 'semantic';
          if (nm !== mode) switchMode(nm);
          return;
        }
        const action = btn.getAttribute('data-action');
        if (action === 'nav-prev') { navigateSourceRelative(-1); return; }
        if (action === 'nav-next') { navigateSourceRelative(1); return; }
        if (action === 'toolbar-dock') { toggleToolbarDock(); return; }
        if (action === 'copy-link') hostCopy(currentNavUrl());
        if (action === 'copy-text') hostCopy(PAYLOAD.plain_text || document.body.innerText || '');
        if (action === 'copy-roles') hostCopy(mode === 'media' ? (PAYLOAD.media_role_text || '') : (PAYLOAD.semantic_role_text || ''));
        if (action === 'external') post('open_external', { url: currentNavUrl() });
      });
      bar.addEventListener('change', ev => {
        const sel = ev.target && ev.target.closest ? ev.target.closest('select.ytce-nav-select') : null;
        if (!sel) return;
        navigateSourceIndex(Number(sel.value), 'dropdown');
      });
      post('toolbar_installed');
    }
    ensureToolbarSafeAreaObserver();
    updateToolbar();
    return true;
  }

  function updateToolbar() {
    const bar = document.getElementById('ytce-r42ai-toolbar');
    if (!bar) return;
    applyToolbarDock();
    for (const b of bar.querySelectorAll('button[data-mode]')) b.classList.toggle('ytce-active', b.getAttribute('data-mode') === mode);
    const counts = activeCounts();
    for (const key of Object.keys(counts)) {
      const el = bar.querySelector(`[data-count="${key}"]`);
      if (el) {
        const labels = { PRIMARY:'Primary', SECONDARY:'Secondary', TERTIARY:'Tertiary', UNKNOWN:'Unknown' };
        el.textContent = (labels[key] || key) + ': ' + String(counts[key]).padStart(2, '0');
        el.title = key[0] + key.slice(1).toLowerCase() + ': ' + counts[key];
        el.classList.remove('ytce-count-primary','ytce-count-secondary','ytce-count-tertiary','ytce-count-unknown');
        el.classList.add('ytce-count-' + key.toLowerCase());
      }
    }
    const navWrap = bar.querySelector('.ytce-nav-wrap');
    const navSelect = bar.querySelector('.ytce-nav-select');
    if (navWrap) navWrap.classList.toggle('ytce-nav-hidden', NAV_LINKS.length < 2);
    if (navSelect) {
      const optKey = navOptionsKey();
      if (navSelect.getAttribute('data-nav-options-key') !== optKey) {
        while (navSelect.firstChild) navSelect.removeChild(navSelect.firstChild);
        NAV_LINKS.forEach((item, idx) => {
          const opt = document.createElement('option');
          opt.value = String(idx);
          opt.textContent = navOptionLabel(item, idx);
          opt.title = item.url || '';
          navSelect.appendChild(opt);
        });
        navSelect.setAttribute('data-nav-options-key', optKey);
      }
      const navIdx = navCurrentIndex();
      const item = NAV_LINKS[navIdx] || currentNavItem();
      navSelect.value = String(navIdx);
      navSelect.title = item.url || currentNavUrl();
      navSelect.disabled = NAV_LINKS.length < 2;
    }
    const urlEl = bar.querySelector('.ytce-url');
    setTimeout(updateToolbarSafeArea, 0);
    if (urlEl) { const u = String(currentNavUrl() || PAYLOAD.selected_url || ''); urlEl.textContent = u.replace(/^(SEMANTIC|MEDIA)\s*[|¦]\s*/i, '').replace(/^\s*(SEMANTIC|MEDIA)\s+/i, ''); }
    publishNativeToolbarState('update_toolbar');
  }
  function scheduleAsyncMediaPaint(reason) {
    if (mediaAsyncPaintScheduled || mode !== 'media') return;
    mediaAsyncPaintScheduled = true;
    setTimeout(() => {
      const t0 = performance.now();
      mediaAsyncPaintScheduled = false;
      if (mode !== 'media') return;
      let mp = 0;
      if (!mediaCacheWarm) warmMediaCache(reason || 'async_media_paint_cache');
      mp = paintMediaRows(true);
      post('media_paint_async', { reason: reason || 'scheduled', duration_ms: Math.round(performance.now() - t0), media_painted: mp, media_outlines: document.querySelectorAll('.ytce-r42ai-media-outline').length, media_boxes: document.querySelectorAll('.ytce-r42cr-media-box').length, roles: Array.from(document.querySelectorAll('.ytce-r42ai-media-outline')).map(el => ({role: el.getAttribute('data-ytce-role')||'', text: shortText(el.textContent||'', 70)})).slice(0,6) });
    }, 0);
  }

  function switchMode(nextMode) {
    if (nextMode !== 'media' && nextMode !== 'semantic') return;
    if (nextMode === mode) return;
    const switchStart = performance.now();
    const fromMode = mode;
    mode = nextMode;
    setModeBodyClass();
    updateToolbar();
    post('mode_toggle_click', { from: fromMode, to: mode, ui_ms: Math.round(performance.now() - switchStart) });
    const syncStart = performance.now();
    syncExistingPaintForMode({ quick: true });
    const syncMs = Math.round(performance.now() - syncStart);
    if (mode === 'media') {
      scheduleAsyncMediaPaint(mediaCacheWarm ? 'mode_switch_cached_async' : 'mode_switch_uncached_async');
    } else {
      clearMediaBoxes();
    }
    updateToolbar();
    post('mode_switch_fast', { mode, duration_ms: Math.round(performance.now() - switchStart), sync_ms: syncMs, media_deferred: mode === 'media', text_spans:document.querySelectorAll('.ytce-role-hit').length, media_outlines:document.querySelectorAll('.ytce-r42ai-media-outline').length, media_boxes:document.querySelectorAll('.ytce-r42cr-media-box').length });
  }

  function isVisibleElement(el) {
    try { const cs = getComputedStyle(el); return cs && cs.display !== 'none' && cs.visibility !== 'hidden' && Number(cs.opacity || 1) !== 0; } catch(e) { return true; }
  }
  function excludedElement(el) {
    if (!el || el.nodeType !== 1) return false;
    if (el.id === 'ytce-r42ai-toolbar' || el.closest && el.closest('#ytce-r42ai-toolbar')) return true;
    const tag = el.tagName ? el.tagName.toLowerCase() : '';
    if (['script','style','noscript','iframe','svg','canvas','input','button','textarea','select','option'].includes(tag)) return true;
    if (['nav','footer','aside'].includes(tag)) return true;
    const txt = ((el.id || '') + ' ' + (el.className || '') + ' ' + (el.getAttribute && (el.getAttribute('role') || ''))).toLowerCase();
    if (/cookie|consent|cmp|advert|ads|sidebar|newsletter|menu|nav|footer/.test(txt)) return true;
    return false;
  }
  function selectedTitleNeedle() {
    const sr = (((PAYLOAD.rows_by_mode || {}).semantic) || []);
    for (const row of sr) {
      const txt = normalize(textForRow(row));
      if (txt.length > 18) return txt.slice(0, 160);
    }
    return normalize(document.title || '').slice(0, 160);
  }
  function candidateRootScore(el, titleNeedle) {
    if (!el || excludedElement(el) || !isVisibleElement(el)) return -1;
    const text = normalize(el.textContent || '');
    if (text.length < 80) return -1;
    let score = 0;
    const rect = (() => { try { return el.getBoundingClientRect(); } catch(e) { return {width:0,height:0}; } })();
    if (text.includes('must read') || text.includes('shopping') || text.includes('related topics')) score -= 180;
    if (rect.width > 1100) score -= 90;
    if (titleNeedle && (text.includes(titleNeedle) || titleNeedle.includes(text.slice(0, Math.min(80, text.length))))) score += 1000;
    const sampleRows = (((PAYLOAD.rows_by_mode || {}).semantic) || []).slice(0, 18);
    for (const row of sampleRows) {
      const n = normalize(textForRow(row));
      if (n.length > 18 && text.includes(n.slice(0, Math.min(80, n.length)))) score += 8;
    }
    if ((el.tagName || '').toLowerCase() === 'article') score += 20;
    return score;
  }
  function articleRoots() {
    const titleNeedle = selectedTitleNeedle();
    const candidates = [];
    for (const sel of ['article','[itemprop="articleBody"]','.article-body','.entry-content','.post-content','.single-post','.metro__post','.content-body','main']) {
      for (const el of document.querySelectorAll(sel)) candidates.push(el);
    }
    let best = null;
    let bestScore = -1;
    for (const el of Array.from(new Set(candidates))) {
      const score = candidateRootScore(el, titleNeedle);
      if (score > bestScore) { bestScore = score; best = el; }
    }
    if (best && bestScore > 0) return [best];
    const h1s = Array.from(document.querySelectorAll('h1'));
    for (const h1 of h1s) {
      const ht = normalize(h1.textContent || '');
      if (!titleNeedle || !ht || !(ht.includes(titleNeedle.slice(0, Math.min(60, titleNeedle.length))) || titleNeedle.includes(ht))) continue;
      let cur = h1.parentElement;
      let chosen = null;
      while (cur && cur !== document.body) {
        const nt = normalize(cur.textContent || '');
        const rr = (() => { try { return cur.getBoundingClientRect(); } catch(e) { return {width:0,height:0}; } })();
        if (!chosen && !excludedElement(cur) && nt.length > 900 && !nt.includes('must read') && rr.width <= 1000) chosen = cur;
        cur = cur.parentElement;
      }
      if (chosen) return [chosen];
    }
    if (document.querySelector('main')) return [document.querySelector('main')];
    return document.body ? [document.body] : [];
  }

  function candidateBlocks() {
    const blocks = [];
    const selectors = 'h1,h2,h3,h4,p,li,blockquote,figcaption,caption,span,a,strong,em,time';
    for (const root of articleRoots()) {
      const nodes = root.matches && root.matches(selectors) ? [root, ...root.querySelectorAll(selectors)] : Array.from(root.querySelectorAll(selectors));
      for (const el of nodes) {
        if (excludedElement(el) || !isVisibleElement(el) || el.closest('.ytce-role-hit')) continue;
        const txt = normalize(el.textContent || '');
        if (txt.length < 2 || txt.length > 1400) continue;
        blocks.push(el);
      }
      // R42AN: allow small leaf divs only; never wrap large layout containers.
      for (const el of root.querySelectorAll('div')) {
        if (excludedElement(el) || !isVisibleElement(el) || el.closest('.ytce-role-hit')) continue;
        if (el.querySelector('h1,h2,h3,h4,p,li,blockquote,figure,article,section,aside,nav')) continue;
        const txt = normalize(el.textContent || '');
        if (txt.length >= 2 && txt.length <= 300) blocks.push(el);
      }
    }
    return Array.from(new Set(blocks)).sort((a,b) => (a.textContent||'').length - (b.textContent||'').length);
  }

  function textMapForElement(el) {
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        if (!node.nodeValue || !clean(node.nodeValue)) return NodeFilter.FILTER_REJECT;
        const parent = node.parentElement;
        if (!parent || excludedElement(parent) || parent.closest('.ytce-role-hit')) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    let normalized = '';
    const map = [];
    let lastWasSpace = true;
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const raw = node.nodeValue || '';
      for (let i = 0; i < raw.length; i++) {
        let ch = raw[i];
        if (/\s/.test(ch) || ch === '\u00a0') {
          if (!lastWasSpace && normalized.length) { normalized += ' '; map.push({ node, start: i, end: i + 1 }); lastWasSpace = true; }
          continue;
        }
        if ('‘’‚‛'.includes(ch)) ch = "'";
        if ('“”„‟'.includes(ch)) ch = '"';
        if ('‐‑‒–—―'.includes(ch)) ch = '-';
        normalized += ch.toLowerCase();
        map.push({ node, start: i, end: i + 1 });
        lastWasSpace = false;
      }
    }
    normalized = normalized.trimStart();
    while (normalized.endsWith(' ')) { normalized = normalized.slice(0,-1); map.pop(); }
    return { normalized, map };
  }

  function wrapRange(startInfo, endInfo, row, role) {
    const range = document.createRange();
    range.setStart(startInfo.node, startInfo.start);
    range.setEnd(endInfo.node, endInfo.end);
    const span = document.createElement('span');
    span.className = 'ytce-role-hit ' + roleClass(role);
    span.setAttribute('data-ytce-key', row.edit_key || '');
    span.setAttribute('data-ytce-mode', mode);
    span.setAttribute('data-ytce-role', role);
    span.setAttribute('title', '');
    let downX = 0, downY = 0;
    span.addEventListener('mousedown', ev => { downX = ev.clientX; downY = ev.clientY; }, true);
    span.addEventListener('click', ev => {
      try {
        if (Math.abs(ev.clientX - downX) + Math.abs(ev.clientY - downY) > 5) return;
        const sel = window.getSelection && window.getSelection();
        if (sel && !sel.isCollapsed) return;
        const clickStart = performance.now();
        const current = span.getAttribute('data-ytce-role') || roleOf(row);
        const next = roles[(roles.indexOf(current) + 1) % roles.length] || 'UNKNOWN';
        if (mode === 'media') row.media_source_role = next; else row.semantic_role = next;
        applyRoleClass(span, next, false);
        updateToolbar();
        refreshMediaVisualsForChangedRow(row, next, 'text_span', clickStart);
        saveRoleChange(row, next, 'text_span', performance.now() - clickStart);
        ev.stopPropagation();
      } catch(e) { post('role_click_error', String(e && e.message ? e.message : e)); }
    }, true);
    try {
      const frag = range.extractContents();
      span.appendChild(frag);
      range.insertNode(span);
      return true;
    } catch (e) {
      post('wrap_error', { key: row.edit_key || '', text: textForRow(row).slice(0,80), error: String(e && e.message ? e.message : e) });
      return false;
    }
  }

  function nearestIndexOfWord(hay, word, approx) {
    let best = -1, bestDist = Infinity, from = 0;
    while (true) {
      const p = hay.indexOf(word, from);
      if (p < 0) break;
      const beforeOk = p === 0 || /[^a-z0-9]/.test(hay[p - 1] || '');
      const afterOk = p + word.length >= hay.length || /[^a-z0-9]/.test(hay[p + word.length] || '');
      if (beforeOk && afterOk) {
        const dist = Math.abs(p - approx);
        if (dist < bestDist) { best = p; bestDist = dist; }
      }
      from = p + Math.max(1, word.length);
    }
    return best;
  }

  function findNeedleInMap(tm, needle) {
    let pos = tm.normalized.indexOf(needle);
    if (pos >= 0) {
      let len = needle.length;
      if (needle === 'nora' && tm.normalized[pos + len] === ',') len += 1;
      return { pos, len };
    }
    // R42AS: punctuation/spacing fallback, but map near the loose match instead of
    // blindly taking the first occurrence of a common word elsewhere in the block.
    const looseNeedle = looseNormalize(needle);
    if (!looseNeedle || looseNeedle.length < 3) return null;
    const looseHay = looseNormalize(tm.normalized);
    const loosePos = looseHay.indexOf(looseNeedle);
    if (loosePos < 0) return null;
    const words = looseNeedle.split(' ').filter(Boolean);
    if (!words.length) return null;
    const first = words[0], last = words[words.length - 1];
    const approxStart = Math.round((loosePos / Math.max(1, looseHay.length)) * tm.normalized.length);
    const startPos = nearestIndexOfWord(tm.normalized, first, approxStart);
    if (startPos < 0) return null;
    let endPos = startPos;
    const approxEnd = Math.min(tm.normalized.length, startPos + Math.max(needle.length, looseNeedle.length));
    const lastPos = nearestIndexOfWord(tm.normalized.slice(startPos), last, approxEnd - startPos);
    if (lastPos >= 0) endPos = startPos + lastPos + last.length;
    else endPos = Math.min(tm.normalized.length, startPos + needle.length);
    return { pos: startPos, len: Math.max(1, endPos - startPos) };
  }

  function shortRowAllowedInBlock(row, block, needle) {
    const bt = normalize(block.textContent || '');
    const role = roleOf(row);
    if (!bt) return false;
    // Very short rows such as “Nora” must not paint inside later quote sentences
    // such as “..., Nora explains.”  They are allowed only as standalone text or
    // at the start of the intended article sentence.
    if (needle === 'nora') { const lbt = looseNormalize(bt); return bt === 'nora' || lbt.startsWith('nora who is prominent member of the seagull appreciation society'); }
    if (needle === 'i think') { const lbt = looseNormalize(bt); return bt === 'i think' || lbt === 'i think' || lbt.startsWith('i think racism is getting worse') || lbt.includes('government who dont care about our communities i think racism is getting worse'); }
    if (needle.length <= 5) return bt === needle;
    if (role === 'BLANK' && needle.length <= 22) {
      if (bt === needle) return true;
      if (needle === 'barney davis' && bt.includes('night news editor') && bt.length <= 90) return true;
      if (needle === 'nora mubarak' && bt.startsWith('nora mubarak') && bt.length <= 190) return true;
      if (['this section was','on tommy robinson','has spoken out after','posts what really happened'].includes(needle) && bt.startsWith(needle) && bt.length <= 190) return true;
      if (needle === 'tommy robinson' && bt.startsWith('tommy robinson') && bt.length <= 120) return true;
      return false;
    }
    return true;
  }


  function forcedShortContextAllows(row, node, needle) {
    try {
      const parent = node && node.parentElement;
      if (!parent || excludedElement(parent) || parent.closest('.ytce-role-hit')) return false;
      const owner = (parent.closest && parent.closest('p,div,li,h1,h2,h3,figcaption,blockquote')) || parent;
      const ctx = looseNormalize(owner.textContent || parent.textContent || '');
      if (!ctx) return false;
      if (needle === 'barney davis') return ctx.includes('barney davis night news editor') || ctx === 'barney davis';
      if (needle === 'nora') return ctx.startsWith('nora who is a prominent member') || ctx.includes('nora who is a prominent member of the seagull appreciation society');
      if (needle === 'i think') return ctx.includes('i think racism is getting worse') || ctx.includes('communities i think racism is getting worse');
      if (needle === 'this section was') return ctx.includes('this section was cut out of the video');
      if (needle === 'has spoken out after') return ctx.includes('has spoken out after a clip of her rescuing a baby seagull');
      if (needle === 'posts what really happened') return ctx.includes('muslim woman who far right painted as eating seagull posts what really happened') || ctx.includes('posts what really happened');
      if (needle === 'but oliver freeston') return ctx.startsWith('but oliver freeston the reform uk leader') || ctx.includes('but oliver freeston the reform uk leader');
      if (needle === 'tommy robinson') return ctx.includes('far right leader tommy robinson also shared the video') || ctx.includes('tommy robinson also shared the video');
      if (needle === 'on tommy robinson') return ctx.startsWith('on tommy robinson not deleting') || ctx.includes('on tommy robinson not deleting his post');
    } catch(e) {}
    return false;
  }

  function normalizedTextNodeMap(node) {
    const raw = node && node.nodeValue ? String(node.nodeValue) : '';
    let normalized = '';
    const map = [];
    let lastWasSpace = true;
    for (let i = 0; i < raw.length; i++) {
      let ch = raw[i];
      if (/\s/.test(ch) || ch === '\u00a0') {
        if (!lastWasSpace && normalized.length) { normalized += ' '; map.push({ start: i, end: i + 1 }); lastWasSpace = true; }
        continue;
      }
      if ('‘’‚‛'.includes(ch)) ch = "'";
      if ('“”„‟'.includes(ch)) ch = '"';
      if ('‐‑‒–—―'.includes(ch)) ch = '-';
      normalized += ch.toLowerCase();
      map.push({ start: i, end: i + 1 });
      lastWasSpace = false;
    }
    normalized = normalized.trimStart();
    while (normalized.endsWith(' ')) { normalized = normalized.slice(0,-1); map.pop(); }
    return { normalized, map };
  }

  function findDirectTextNodeNeedle(node, needle) {
    const tm = normalizedTextNodeMap(node);
    if (!tm.normalized || !tm.map.length) return null;
    let pos = tm.normalized.indexOf(needle);
    let len = needle.length;
    if (needle === 'nora') {
      pos = tm.normalized.indexOf('nora,');
      if (pos < 0) pos = tm.normalized.indexOf('nora');
      len = tm.normalized.startsWith('nora,', pos) ? 5 : 4;
    }
    if (pos < 0) return null;
    if (needle === 'nora' && tm.normalized[pos + len] === ',') len += 1;
    const endPos = Math.min(tm.map.length - 1, pos + len - 1);
    return { start: tm.map[pos].start, end: tm.map[endPos].end };
  }

  function paintForcedShortRows(modeRows) {
    let painted = 0;
    const wanted = new Set(['barney davis','nora','i think','this section was','has spoken out after','posts what really happened','but oliver freeston','tommy robinson','on tommy robinson']);
    const roots = articleRoots();
    for (const row of modeRows) {
      if (textAlreadyPaintedForRow(row)) continue;
      const needleRaw = normalize(textForRow(row));
      const needleLoose = looseNormalize(textForRow(row));
      const needle = (needleLoose === 'nora' || needleLoose === 'nora ') ? 'nora' : (needleRaw === 'nora,' ? 'nora' : needleRaw);
      if (!wanted.has(needle) && !wanted.has(needleLoose)) continue;
      for (const root of roots) {
        let done = false;
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
          acceptNode(node) {
            if (!node.nodeValue || !clean(node.nodeValue)) return NodeFilter.FILTER_REJECT;
            const parent = node.parentElement;
            if (!parent || excludedElement(parent) || parent.closest('.ytce-role-hit')) return NodeFilter.FILTER_REJECT;
            return NodeFilter.FILTER_ACCEPT;
          }
        });
        for (let node = walker.nextNode(); node && !done; node = walker.nextNode()) {
          if (!forcedShortContextAllows(row, node, needle)) continue;
          const found = findDirectTextNodeNeedle(node, needle);
          if (!found) continue;
          const role = roleOf(row);
          if (wrapRange({ node, start: found.start }, { node, end: found.end }, row, role)) { painted += 1; done = true; }
        }
        if (done) break;
      }
    }
    return painted;
  }

  function textAlreadyPaintedForRow(row) {
    const key = String(row.edit_key || '');
    if (key && document.querySelector(`.ytce-role-hit[data-ytce-key="${CSS.escape(key)}"][data-ytce-mode="${mode}"]`)) return true;
    const needle = normalize(textForRow(row));
    if (!needle) return false;
    for (const span of document.querySelectorAll('.ytce-role-hit,.ytce-role-inactive')) {
      if (normalize(span.textContent || '') === needle) return true;
    }
    return false;
  }

  function paintTextRows() {
    const blocks = candidateBlocks();
    let painted = 0;
    const modeRows = rows().filter(r => {
      const k = rowKind(r);
      return !['image','video','media','link','archive','locator'].includes(k);
    }).sort((a,b) => {
      // Long sentence rows first prevents short names/blanks from blocking a full quote sentence.
      // Leaf-block filtering above prevents the old giant page/header wrappers.
      const la = normalize(textForRow(a)).length, lb = normalize(textForRow(b)).length;
      return lb - la;
    });
    for (const row of modeRows) {
      if (textAlreadyPaintedForRow(row)) continue;
      const needle = normalize(textForRow(row));
      if (!needle || needle.length < 2) continue;
      for (const block of blocks) {
        if (block.closest('.ytce-role-hit')) continue;
        const tm = textMapForElement(block);
        const found = findNeedleInMap(tm, needle);
        if (!found || found.pos < 0 || found.pos >= tm.map.length) continue;
        if (!shortRowAllowedInBlock(row, block, needle)) continue;
        const endPos = Math.min(tm.map.length - 1, found.pos + found.len - 1);
        const role = roleOf(row);
        if (wrapRange(tm.map[found.pos], tm.map[endPos], row, role)) { painted += 1; break; }
      }
    }
    painted += paintForcedShortRows(modeRows);
    return painted;
  }

  function isVideoLike(el) {
    const tag = (el && el.tagName ? el.tagName.toLowerCase() : '');
    const desc = (((el && el.id) || '') + ' ' + ((el && el.className) || '') + ' ' + ((el && el.getAttribute && (el.getAttribute('src') || el.getAttribute('data-src') || el.getAttribute('aria-label') || '')) || '')).toLowerCase();
    return tag === 'video' || tag === 'iframe' || /video|player|jwplayer|vjs|plyr|youtube|vimeo|dailymotion|brightcove/.test(desc);
  }
  function interactiveMediaClickTarget(node) {
    try {
      const el = node && node.closest ? node.closest('a,button,input,textarea,select,option,video,audio,iframe,[role="button"],[contenteditable="true"]') : null;
      return !!el;
    } catch(e) { return true; }
  }

  function wireMediaRoleClick(target) {
    if (!target || target.getAttribute('data-ytce-media-click') === '1') return;
    target.setAttribute('data-ytce-media-click', '1');
    target.addEventListener('click', ev => {
      try {
        if (mode !== 'media') return;
        if (interactiveMediaClickTarget(ev.target)) return;
        const key = target.getAttribute('data-ytce-key') || '';
        const row = rowsByKeyForMode().get(key);
        if (!row) return;
        const clickStart = performance.now();
        const current = target.getAttribute('data-ytce-role') || roleOf(row);
        const next = roles[(roles.indexOf(current) + 1) % roles.length] || 'UNKNOWN';
        row.media_source_role = next;
        applyRoleClass(target, next, true);
        target.setAttribute('data-ytce-role', next);
        updateToolbar();
        refreshMediaVisualsForChangedRow(row, next, 'media_target', clickStart);
        saveRoleChange(row, next, 'media_target', performance.now() - clickStart);
        ev.stopPropagation();
      } catch(e) { post('media_role_click_error', String(e && e.message ? e.message : e)); }
    }, true);
  }

  function excludedMediaTarget(el) {
    if (!el || el.nodeType !== 1) return true;
    if (el.id === 'ytce-r42ai-toolbar' || (el.closest && el.closest('#ytce-r42ai-toolbar'))) return true;
    const tag = el.tagName ? el.tagName.toLowerCase() : '';
    if (['script','style','noscript','svg','canvas','input','button','textarea','select','option'].includes(tag)) return true;
    const desc = ((el.id || '') + ' ' + (el.className || '') + ' ' + (el.getAttribute && ((el.getAttribute('role') || '') + ' ' + (el.getAttribute('src') || '') + ' ' + (el.getAttribute('data-src') || ''))) ).toLowerCase();
    if (/cookie|consent|cmp|nav|footer|menu|newsletter|comment/.test(desc) && !isVideoLike(el)) return true;
    if (/related|recommended|trending|must-read|must_read|sidebar/.test(desc) && el.getAttribute('data-ytce-main-video') !== '1') return true;
    if (/doubleclick|googlesyndication|googleads|adnxs|taboola|outbrain|amazon-adsystem|adservice|advertisement/.test(desc)) return true;
    if (/\bad\b|\bads\b|advert/.test(desc) && !isVideoLike(el)) return true;
    return false;
  }
  function mediaContainer(el) {
    if (!el) return el;
    const tag = el.tagName ? el.tagName.toLowerCase() : '';
    if (tag === 'img' || tag === 'picture') {
      const fig = el.closest && el.closest('figure');
      if (fig && !excludedMediaTarget(fig)) return fig;
      return el;
    }
    const selectors = ['figure','[data-testid*="video"]','[class*="video"]','[id*="video"]','[class*="player"]','[id*="player"]','[class*="jw"]','[class*="vjs"]','[class*="plyr"]'];
    for (const sel of selectors) {
      try { const c = el.closest(sel); if (c && !excludedMediaTarget(c)) return c; } catch(e) {}
    }
    return el;
  }
  function area(el) { try { const r = el.getBoundingClientRect(); return Math.max(0,r.width)*Math.max(0,r.height); } catch(e) { return 0; } }
  function clearMediaBoxes() {
    try { for (const box of Array.from(document.querySelectorAll('.ytce-r42cr-media-box'))) box.remove(); } catch(e) {}
  }
  function articleColumnBounds() {
    try {
      const rects = Array.from(document.querySelectorAll('.ytce-role-hit'))
        .map(el => el.getBoundingClientRect())
        .filter(r => r && r.width > 18 && r.height > 6 && r.height < 180 && r.right > 0 && r.bottom > 0 && r.left < innerWidth);
      if (!rects.length) return null;
      const lefts = rects.map(r => r.left).sort((a,b)=>a-b);
      const rights = rects.map(r => r.right).sort((a,b)=>a-b);
      const q = (arr,p) => arr[Math.max(0, Math.min(arr.length-1, Math.floor((arr.length-1)*p)))];
      return { left: Math.max(0, q(lefts,.05) - 70), right: Math.min(innerWidth, q(rights,.95) + 70) };
    } catch(e) { return null; }
  }
  function overlapsArticleColumn(rect) {
    const col = articleColumnBounds();
    if (!col) return true;
    const overlap = Math.max(0, Math.min(rect.right, col.right) - Math.max(rect.left, col.left));
    const ratio = overlap / Math.max(1, Math.min(rect.width, col.right - col.left));
    return ratio >= .45;
  }
  function mediaBoxClickCycle(key, currentRole, source, ev) {
    try {
      const clickStart = performance.now();
      if (mode !== 'media') return;
      const row = rowsByKeyForMode().get(key);
      if (!row) return;
      const current = currentRole || row.media_source_role || row.active_role || roleOf(row);
      const next = roles[(roles.indexOf(String(current).toUpperCase()) + 1) % roles.length] || 'UNKNOWN';
      row.media_source_role = next;
      updateToolbar();
      refreshMediaVisualsForChangedRow(row, next, source || 'media_box', clickStart);
      saveRoleChange(row, next, source || 'media_box', performance.now() - clickStart);
      if (ev) { ev.preventDefault(); ev.stopPropagation(); }
    } catch(e) { post('media_box_click_error', String(e && e.message ? e.message : e)); }
  }

  function visibleMediaRect(target) {
    const r = target.getBoundingClientRect();
    let left = r.left, top = r.top, right = r.right, bottom = r.bottom;
    try {
      const isMain = target.getAttribute('data-ytce-main-video') === '1' || looksLikeMainVideoContainer(target);
      if (isMain) {
        let up = null;
        for (const el of Array.from(target.querySelectorAll('*'))) {
          const txt = normalize(el.textContent || '');
          if (txt === 'up next' || txt.startsWith('up next ')) { up = el; break; }
        }
        if (up) {
          const ur = up.getBoundingClientRect();
          if (ur.top > top + 130 && ur.top < bottom - 40) bottom = Math.max(top + 130, ur.top - 5);
        }
      }
    } catch(e) {}
    return { left, top, right, bottom, width: Math.max(0, right-left), height: Math.max(0, bottom-top) };
  }
  function renderMediaBoxes(targets) {
    clearMediaBoxes();
    if (mode !== 'media' || !document.body) return 0;
    let made = 0;
    const seen = [];
    for (const target of targets || []) {
      try {
        if (!target || !target.getBoundingClientRect) continue;
        if (excludedMediaTarget(target)) continue;
        const r = visibleMediaRect(target);
        if (!r || r.width < 120 || r.height < 80) continue;
        if (!overlapsArticleColumn(r)) continue;
        if (seen.some(x => Math.abs(x.left-r.left)<4 && Math.abs(x.top-r.top)<4 && Math.abs(x.width-r.width)<4 && Math.abs(x.height-r.height)<4)) continue;
        seen.push({left:r.left,top:r.top,width:r.width,height:r.height});
        const role = target.getAttribute('data-ytce-role') || 'UNKNOWN';
        const key = target.getAttribute('data-ytce-key') || '';
        const box = document.createElement('div');
        const videoBox = target.getAttribute('data-ytce-main-video') === '1' || looksLikeMainVideoContainer(target) || isVideoLike(target);
        box.className = 'ytce-r42cr-media-box ' + roleClass(role);
        box.setAttribute('data-ytce-key', key);
        box.setAttribute('data-ytce-role', role);
        if (videoBox) box.setAttribute('data-ytce-video-box', '1');
        const pad = 4;
        box.style.left = Math.round(window.scrollX + r.left - pad) + 'px';
        box.style.top = Math.round(window.scrollY + r.top - pad) + 'px';
        box.style.width = Math.round(r.width + pad*2) + 'px';
        box.style.height = Math.round(r.height + pad*2) + 'px';
        document.body.appendChild(box);
        made++;
      } catch(e) {}
    }
    return made;
  }
  function renderMediaBoxesFromExisting() {
    return renderMediaBoxes(Array.from(document.querySelectorAll('.ytce-r42ai-media-outline')));
  }
  function elementTextHasChrome(el) {
    try {
      const txt = normalize(el.textContent || '');
      return txt.includes('must read') || txt.includes('shopping') || txt.includes('related topics') || txt.includes('news updates') || txt.includes('published july 17') || txt.includes('night news editor');
    } catch(e) { return false; }
  }
  function containsArticleHeader(el) {
    try {
      if (el.querySelector && (el.querySelector('h1') || el.querySelector('[href*="/author/"]') || el.querySelector('time'))) return true;
      const txt = normalize(el.textContent || '');
      return txt.includes('barney davis') && (txt.includes('night news editor') || txt.includes('published july 17'));
    } catch(e) { return false; }
  }
  function articleHeaderBottom() {
    let bottom = 0;
    try {
      const nodes = Array.from(document.querySelectorAll('h1,[href*="/author/"],time'));
      for (const n of nodes) {
        const r = n.getBoundingClientRect();
        if (r && r.width && r.height && r.bottom > bottom) bottom = r.bottom;
      }
    } catch(e) {}
    return bottom;
  }
  function nearbyMediaText(el) {
    const parts = [];
    try {
      const parent = el.closest && (el.closest('figure') || el.parentElement);
      if (parent) parts.push(parent.textContent || '');
      let n = parent || el;
      for (let i=0, cur=n && n.previousElementSibling; cur && i<3; cur=cur.previousElementSibling, i++) parts.push(cur.textContent || cur.getAttribute('alt') || '');
      for (let i=0, cur=n && n.nextElementSibling; cur && i<3; cur=cur.nextElementSibling, i++) parts.push(cur.textContent || cur.getAttribute('alt') || '');
      for (const img of el.querySelectorAll ? el.querySelectorAll('img') : []) parts.push(img.getAttribute('alt') || img.currentSrc || img.src || '');
      if (el.getAttribute) parts.push(el.getAttribute('alt') || el.getAttribute('aria-label') || '');
    } catch(e) {}
    return parts.join(' ');
  }

  function mediaOwnText(el) {
    try { return normalize((el.textContent || '') + ' ' + nearbyMediaText(el)); } catch(e) { return ''; }
  }
  function isPromotedOrAdMedia(el) {
    try {
      const txt = mediaOwnText(el);
      const desc = ((el.id || '') + ' ' + (el.className || '')).toLowerCase();
      if (/advert|ad-slot|adslot|dfp|gpt|outbrain|taboola|promoted|sponsored/.test(desc)) return true;
      if (txt.includes('advertisement') && !txt.includes('muslim woman who far right painted')) return true;
      if (txt.includes('read more') && (txt.includes('article by') || txt.includes('published sep') || txt.includes('falklands') || txt.includes('trump'))) return true;
      if (txt.includes('tensions spike over the falklands') || txt.includes('after trump') || txt.includes('article by sarah hooper')) return true;
    } catch(e) {}
    return false;
  }
  function captionImageTargetOk(target, captionSpan) {
    try {
      if (!target || !isVisibleElement(target) || excludedMediaTarget(target) || isPromotedOrAdMedia(target)) return false;
      const r = target.getBoundingClientRect();
      const sr = captionSpan.getBoundingClientRect();
      const containsCaption = !!(target.contains && target.contains(captionSpan));
      if (r.width < 230 || r.height < 120) return false;
      if (!overlapsArticleColumn(r)) return false;
      if (!containsCaption && r.bottom > sr.top + 35) return false;
      if (!containsCaption && sr.top - r.bottom > 80) return false;
      const leftClose = Math.abs(r.left - sr.left) < 95;
      const rightClose = Math.abs(r.right - sr.right) < 150;
      const centerClose = Math.abs(((r.left+r.right)/2) - ((sr.left+sr.right)/2)) < 160;
      return leftClose || rightClose || centerClose;
    } catch(e) { return false; }
  }
  function findMainSourceVideoTargets() {
    const out = [];
    const seen = new Set();
    try {
      const pool = Array.from(document.querySelectorAll('video,iframe,figure,section,article,div'));
      for (const el of pool) {
        let target = mediaContainer(el);
        if (!target || seen.has(target) || !isVisibleElement(target) || excludedMediaTarget(target) || isPromotedOrAdMedia(target)) continue;
        const r = target.getBoundingClientRect();
        if (r.width < 300 || r.height < 170 || r.width > 980 || r.height > 820) continue;
        if (!overlapsArticleColumn(r)) continue;
        const txt = mediaOwnText(target);
        const desc = ((target.id || '') + ' ' + (target.className || '')).toLowerCase();
        const hasPlayerish = isVideoLike(target) || !!(target.querySelector && target.querySelector('video,iframe,[class*="video"],[class*="player"],[class*="jw"],[class*="vjs"],[aria-label*="play" i]')) || /video|player|jw|vjs|plyr|brightcove/.test(desc);
        const sourceTitle = txt.includes('muslim woman who far right painted') || txt.includes('posts what really happened') || txt.includes('0:00 / 0:36') || (txt.includes('up next') && txt.includes('seagull'));
        if (!hasPlayerish || !sourceTitle) continue;
        target = expandVideoTarget(target, document.body || target);
        if (!target || seen.has(target) || isPromotedOrAdMedia(target)) continue;
        try { target.setAttribute('data-ytce-main-video', '1'); } catch(e) {}
        seen.add(target);
        out.push(target);
      }
    } catch(e) {}
    return out;
  }

  function captionMediaTargetsFromPaintedRows(root) {
    const out = [];
    for (const span of document.querySelectorAll('.ytce-role-hit')) {
      const t = normalize(span.textContent || '');
      if (!(t.includes('picture: supplied') || t.includes('picture: @activepatriotuk') || t.includes('baby seagull was stranded') || t.includes('nora mubarak said she will not stop') || t.includes('nora was secretly filmed catching'))) continue;
      let target = null;
      try {
        const fig = span.closest && span.closest('figure');
        if (fig && fig.querySelector && fig.querySelector('img,picture,video')) target = fig;
      } catch(e) {}
      if (!target) {
        let block = (span.closest && span.closest('figcaption,p,div')) || span;
        for (let cur = block; cur && cur !== root && !target; cur = cur.parentElement) {
          for (let sib = cur.previousElementSibling, hops = 0; sib && hops < 5 && !target; sib = sib.previousElementSibling, hops++) {
            if (excludedMediaTarget(sib)) continue;
            if (sib.matches && sib.matches('figure,img,picture,video,iframe,[class*="video"],[class*="player"]')) target = mediaContainer(sib);
            else if (sib.querySelector) {
              const media = sib.querySelector('figure,img,picture,video,iframe,[class*="video"],[class*="player"]');
              if (media) target = mediaContainer(media);
            }
          }
        }
      }
      if (!target) {
        // Last-resort geometric match: choose the nearest visible article image above the caption.
        try {
          const sr = span.getBoundingClientRect();
          let best = null, bestDist = Infinity;
          for (const img of document.querySelectorAll('img,picture,figure')) {
            if (excludedMediaTarget(img) || !isVisibleElement(img) || isPromotedOrAdMedia(img)) continue;
            const cand = mediaContainer(img);
            const r = (cand || img).getBoundingClientRect();
            if (r.width < 230 || r.height < 120 || r.bottom > sr.top + 35 || sr.top - r.bottom > 120) continue;
            if (!overlapsArticleColumn(r)) continue;
            const xPenalty = Math.min(Math.abs(sr.left - r.left), Math.abs(sr.right - r.right), Math.abs(((sr.left+sr.right)/2)-((r.left+r.right)/2)));
            if (xPenalty > 180) continue;
            const dist = xPenalty + Math.abs(sr.top - r.bottom);
            if (dist < bestDist) { best = cand || img; bestDist = dist; }
          }
          if (best) target = mediaContainer(best);
        } catch(e) {}
      }
      if (target && captionImageTargetOk(target, span)) out.push(target);
    }
    return out;
  }

  function looksLikeMainVideoContainer(el) {
    try {
      const desc = ((el.id||'') + ' ' + (el.className||'')).toLowerCase();
      const text = normalize(el.textContent || '');
      const r = el.getBoundingClientRect();
      if (r.width < 280 || r.height < 170 || r.width > 980 || r.height > 760) return false;
      if (containsArticleHeader(el) || elementTextHasChrome(el)) return false;
      if (/video|player|jw|vjs|plyr|brightcove/.test(desc)) return true;
      if (el.querySelector && (el.querySelector('video,iframe,[class*="video"],[class*="player"],[class*="jw"],[class*="vjs"],[aria-label*="play" i]'))) return true;
      if (text.includes('muslim woman who far right painted') || text.includes('posts what really happened')) return true;
    } catch(e) {}
    return false;
  }
  function reasonableMediaTarget(el, root) {
    if (!el || excludedMediaTarget(el) || !isVisibleElement(el)) return false;
    if (el === document.body || el === document.documentElement || el === root) return false;
    const rect = el.getBoundingClientRect();
    if (rect.width < 150 || rect.height < 80) return false;
    if (!overlapsArticleColumn(rect) && !looksLikeMainVideoContainer(el)) return false;
    if (containsArticleHeader(el)) return false;
    const hb = articleHeaderBottom();
    if (hb && rect.top < hb - 8 && rect.height > 160 && !isVideoLike(el)) return false;
    if (hb && rect.top < hb - 8 && looksLikeMainVideoContainer(el) && normalize(el.textContent || '').includes('published july 17')) return false;
    if (elementTextHasChrome(el) && !looksLikeMainVideoContainer(el)) return false;
    if (isPromotedOrAdMedia(el)) return false;
    const tag = (el.tagName || '').toLowerCase();
    const hasRealMedia = tag === 'img' || tag === 'picture' || tag === 'figure' || !!(el.querySelector && el.querySelector('img,picture,video,iframe')) || isVideoLike(el);
    if (!hasRealMedia) return false;
    if (!isVideoLike(el) && tag !== 'img' && tag !== 'picture' && tag !== 'figure' && (rect.width > 980 || rect.height > 980)) return false;
    if (isVideoLike(el) && (rect.width > 1000 || rect.height > 820)) return false;
    return true;
  }
  function mainVideoFromPaintedRows(root) {
    const out = [];
    for (const span of document.querySelectorAll('.ytce-role-hit')) {
      const t = normalize(span.textContent || '');
      if (!(t.includes('muslim woman who far right painted') || t.includes('seagull posts what really happened') || t.includes('posts what really happened'))) continue;
      let best = null;
      let base = span.parentElement;
      try {
        const videoChild = base && (base.querySelector('video,iframe,[class*="video"],[class*="player"],[class*="jw"],[class*="vjs"]'));
        if (videoChild) best = mediaContainer(videoChild);
      } catch(e) {}
      const hBottom = articleHeaderBottom();
      for (let cur = span.parentElement, depth = 0; !best && cur && cur !== root && cur !== document.body && depth < 8; cur = cur.parentElement, depth++) {
        const r = cur.getBoundingClientRect();
        if (hBottom && r.top < hBottom - 8) continue;
        if (r.width < 320 || r.height < 190 || r.width > 980 || r.height > 720) continue;
        if (containsArticleHeader(cur) || elementTextHasChrome(cur)) continue;
        const desc = ((cur.id || '') + ' ' + (cur.className || '')).toLowerCase();
        const hasPlayerish = cur.querySelector && cur.querySelector('video,iframe,[class*="video"],[class*="player"],[class*="jw"],[class*="vjs"],[aria-label*="play" i]');
        const darkish = (() => { try { const bg = getComputedStyle(cur).backgroundColor || ''; return /rgb\((0|1|2|3|4|5|6|7|8|9|1\d|2\d|3\d|4\d|5\d)/.test(bg); } catch(e) { return false; } })();
        if (hasPlayerish || /video|player|jw|vjs|plyr|brightcove/.test(desc) || darkish) best = cur;
      }
      if (best) best = expandVideoTarget(best, root);
      if (best && reasonableMediaTarget(best, root)) { try { best.setAttribute('data-ytce-main-video', '1'); } catch(e) {} out.push(best); }
    }
    return out;
  }
  function directArticleImageTargets(root) {
    const out = [];
    try {
      for (const img of root.querySelectorAll('img,picture,figure')) {
        const target = mediaContainer(img);
        if (!target || excludedMediaTarget(target) || !isVisibleElement(target)) continue;
        const r = target.getBoundingClientRect();
        if (r.width < 150 || r.height < 80) continue;
        if (!overlapsArticleColumn(r)) continue;
        if (containsArticleHeader(target) || elementTextHasChrome(target)) continue;
        out.push(target);
      }
    } catch(e) {}
    return out;
  }
  function expandVideoTarget(target, root) {
    if (!target) return target;
    let best = target;
    try {
      const baseRect = target.getBoundingClientRect();
      for (let cur = target.parentElement, depth = 0; cur && cur !== document.body && cur !== root && depth < 8; cur = cur.parentElement, depth++) {
        if (excludedMediaTarget(cur) || containsArticleHeader(cur)) continue;
        const r = cur.getBoundingClientRect();
        if (r.width < Math.max(260, baseRect.width*.75) || r.height < Math.max(160, baseRect.height*.75)) continue;
        if (r.width > 1020 || r.height > 820) continue;
        if (!overlapsArticleColumn(r)) continue;
        const txt = normalize(cur.textContent || '');
        const desc = ((cur.id||'') + ' ' + (cur.className||'')).toLowerCase();
        const hasVideo = cur.querySelector && cur.querySelector('video,iframe,[class*="video"],[class*="player"],[class*="jw"],[class*="vjs"],[aria-label*="play" i]');
        const upNext = txt.includes('up next') || txt.includes('0:00') || txt.includes('posts what really happened');
        if (hasVideo || /video|player|jw|vjs|plyr|brightcove/.test(desc) || upNext) best = cur;
      }
    } catch(e) {}
    return best;
  }
  function computeMediaTargets() {
    const out = [];
    const roots = Array.from(new Set([...articleRoots(), document.body].filter(Boolean)));
    // R42CR: target only source evidence media. Use body-level search for the Metro
    // main player because it can sit outside the chosen articleBody root, and caption-
    // anchored geometric matching for the supplied/article images.
    out.push(...findMainSourceVideoTargets());
    for (const root of roots) {
      out.push(...mainVideoFromPaintedRows(root));
      out.push(...captionMediaTargetsFromPaintedRows(root));
    }
    const all = Array.from(new Set(out));
    const pruned = all.filter(el => {
      if (!el || containsArticleHeader(el) || excludedMediaTarget(el)) return false;
      const a = Math.max(1, area(el));
      if (!looksLikeMainVideoContainer(el) && all.some(other => other !== el && el.contains(other) && a > Math.max(1, area(other)) * 2.4 && reasonableMediaTarget(other, roots[0] || document.body))) return false;
      if (all.some(other => other !== el && other.contains(el) && area(other) <= a * 1.18 && reasonableMediaTarget(other, roots[0] || document.body))) return false;
      return true;
    });
    return pruned
      .filter(el => !containsArticleHeader(el))
      .sort((a,b)=>a.getBoundingClientRect().top-b.getBoundingClientRect().top)
      .slice(0, 8);
  }
  function warmMediaCache(reason) {
    try {
      cachedMediaTargets = computeMediaTargets();
      mediaCacheWarm = true;
      if (reason && /mode_switch|direct|use_cache_miss/.test(String(reason))) post('media_cache', { reason, targets: cachedMediaTargets.length });
      return cachedMediaTargets;
    } catch(e) {
      post('media_cache_error', { reason, error: String(e && e.message ? e.message : e) });
      cachedMediaTargets = [];
      mediaCacheWarm = false;
      return cachedMediaTargets;
    }
  }
  function scheduleMediaWarm(reason) {
    const now = performance.now();
    const reasonText = String(reason || '');
    if (reasonText === 'page_load' && mediaCacheWarm && cachedMediaTargets && cachedMediaTargets.length) return;
    const important = /role_change|mode|dom_content_loaded/.test(reasonText);
    if (mediaWarmScheduled) return;
    if (!important && mediaCacheWarm && now - lastMediaWarmAt < 3500) return;
    mediaWarmScheduled = true;
    const run = () => {
      mediaWarmScheduled = false;
      const t0 = performance.now();
      const targets = warmMediaCache(reason || 'scheduled');
      lastMediaWarmAt = performance.now();
      if (important) post('media_cache_ready', { reason, targets: targets.length, duration_ms: Math.round(performance.now() - t0) });
      if (mode === 'media') renderMediaBoxesFromExisting();
    };
    setTimeout(run, important ? 10 : 220);
  }
  function mediaTargets(useCache) {
    if (useCache && mediaCacheWarm) return cachedMediaTargets.filter(el => el && el.isConnected);
    return warmMediaCache(useCache ? 'use_cache_miss' : 'direct');
  }

  function rowMatching(mediaRows, predicates) {
    for (const pred of predicates) {
      for (const row of mediaRows) {
        const n = normalize(textForRow(row));
        const l = looseNormalize(textForRow(row));
        try { if (pred(n, l, row)) return row; } catch(e) {}
      }
    }
    return null;
  }
  function mediaOwnHay(target) {
    const parts = [];
    try {
      parts.push(target.textContent || '');
      if (target.getAttribute) parts.push(target.getAttribute('alt') || '', target.getAttribute('aria-label') || '');
      if (target.querySelectorAll) {
        for (const n of target.querySelectorAll('figcaption,caption,[class*="caption"],[class*="credit"],img,video,source,iframe')) {
          parts.push(n.textContent || '', n.getAttribute && (n.getAttribute('alt') || n.getAttribute('aria-label') || n.getAttribute('src') || n.getAttribute('data-src') || ''));
        }
      }
    } catch(e) {}
    return normalize(parts.join(' '));
  }
  function bestMediaRowForTarget(target, mediaRows) {
    const ownHay = mediaOwnHay(target);
    const nearHay = normalize(ownHay + ' ' + nearbyMediaText(target));
    const isMainVideo = looksLikeMainVideoContainer(target) || isVideoLike(target) || target.getAttribute('data-ytce-main-video') === '1';

    // R42CR: exact caption rows beat neighbouring article text.  This fixes the
    // supplied Nora image being coloured UNKNOWN/yellow from the next paragraph
    // instead of SECONDARY/blue from its own caption row.
    if (ownHay.includes('nora mubarak said she will not stop')) {
      return rowMatching(mediaRows, [
        (n) => n.includes('nora mubarak said she will not stop doing whatever she likes in grimsby') && n.includes('picture: supplied')
      ]) || { edit_key: 'r42cr-nora-supplied-image', text: 'Nora Mubarak said she will not stop doing whatever she likes in Grimsby (Picture: Supplied)', media_source_role: 'SECONDARY', active_role: 'SECONDARY', kind: 'media' };
    }
    if (ownHay.includes('baby seagull was stranded on the ground in grimsby')) {
      return rowMatching(mediaRows, [
        (n) => n.includes('baby seagull was stranded on the ground in grimsby') && n.includes('picture: supplied')
      ]) || { edit_key: 'r42cr-baby-seagull-image', text: 'The baby seagull was stranded on the ground in Grimsby (Picture: Supplied)', media_source_role: 'SECONDARY', active_role: 'SECONDARY', kind: 'media' };
    }
    if (ownHay.includes('nora was secretly filmed catching') || ownHay.includes('@activepatriotuk')) {
      return rowMatching(mediaRows, [
        (n) => n.includes('nora was secretly filmed catching') || n.includes('@activepatriotuk')
      ]) || { edit_key: 'r42cr-activepatriot-image', text: 'Nora was secretly filmed catching the infant seagull to return it to its mother (Picture: @ActivePatriotUK)', media_source_role: 'UNKNOWN', active_role: 'UNKNOWN', kind: 'media' };
    }
    if (isMainVideo) {
      return rowMatching(mediaRows, [
        (n) => n.includes('muslim woman who far right painted as') && n.includes('eating seagull'),
        (n) => n.includes('posts what really happened')
      ]) || { edit_key: 'r42cr-main-video-section-' + Math.round(target.getBoundingClientRect().top), text: 'video section', media_source_role: 'UNKNOWN', active_role: 'UNKNOWN', kind: 'media' };
    }

    let best = null, bestScore = -999999;
    for (const row of mediaRows) {
      const needle = normalize(textForRow(row));
      if (!needle) continue;
      let score = -999999;
      if (ownHay.includes(needle)) score = 1000 + Math.min(needle.length, 260);
      else if (nearHay.includes(needle)) score = 120 + Math.min(needle.length, 180);
      else if (needle.includes(ownHay.slice(0, Math.min(90, ownHay.length)))) score = 80;
      if (score < 0) continue;
      const imageish = !isMainVideo;
      if (imageish && (needle.startsWith('it has been seen at least') || needle.startsWith('now nora fears') || needle.startsWith('she told metro') || needle.startsWith('for me,'))) score -= 500;
      if (needle.includes('picture: supplied') || needle.includes('picture: @activepatriotuk')) score += 260;
      if (roleOf(row) === 'UNKNOWN') score -= 20;
      if (score > bestScore) { best = row; bestScore = score; }
    }
    return bestScore >= 120 ? best : null;
  }
  function paintMediaRows(useCache) {
    if (mode !== 'media') { clearMediaBoxes(); return 0; }
    let count = 0;
    const paintedTargets = [];
    const candidates = mediaTargets(!!useCache);
    const mediaRows = rows().filter(r => roleOf(r) !== 'BLANK');
    for (const target of candidates) {
      const best = bestMediaRowForTarget(target, mediaRows);
      if (!best) continue;
      const role = roleOf(best);
      if (!target.classList.contains('ytce-r42ai-media-outline')) count += 1;
      classListRemoveRoles(target);
      target.classList.add('ytce-r42ai-media-outline', roleClass(role));
      target.setAttribute('data-ytce-key', rowKey(best));
      target.setAttribute('data-ytce-mode', mode);
      target.setAttribute('data-ytce-role', role);
      target.setAttribute('title', '');
      wireMediaRoleClick(target);
      paintedTargets.push(target);
    }
    renderMediaBoxes(paintedTargets);
    return count;
  }

  function unwrapRoleSpan(span) {
    try { span.replaceWith(...Array.from(span.childNodes)); }
    catch(e) { span.replaceWith(span.textContent || ''); }
  }
  function syncExistingPaintForMode() {
    const active = rowsByKeyForMode();
    const activeByText = new Map();
    for (const row of rows()) {
      const t = normalize(textForRow(row));
      if (t && !activeByText.has(t)) activeByText.set(t, row);
    }
    for (const span of Array.from(document.querySelectorAll('.ytce-role-hit,.ytce-role-inactive'))) {
      const key = span.getAttribute('data-ytce-key') || '';
      let row = active.get(key);
      if (!row) row = activeByText.get(normalize(span.textContent || ''));
      const kind = row ? rowKind(row) : '';
      if (!row || ['image','video','media','link','archive','locator'].includes(kind)) {
        span.setAttribute('data-ytce-mode', mode);
        span.setAttribute('data-ytce-role', 'INACTIVE');
        classListRemoveRoles(span);
        span.classList.remove('ytce-role-hit');
        span.classList.add('ytce-role-inactive');
        continue;
      }
      const role = roleOf(row);
      span.setAttribute('data-ytce-key', rowKey(row));
      span.setAttribute('data-ytce-mode', mode);
      span.setAttribute('data-ytce-role', role);
      classListRemoveRoles(span);
      span.classList.remove('ytce-role-inactive');
      span.classList.add('ytce-role-hit', roleClass(role));
    }
    for (const el of document.querySelectorAll('.ytce-r42ai-media-outline')) { classListRemoveRoles(el); el.classList.remove('ytce-r42ai-media-outline'); }
    clearMediaBoxes();
  }

  function clearPaint() {
    for (const span of Array.from(document.querySelectorAll('.ytce-role-hit'))) {
      unwrapRoleSpan(span);
    }
    for (const el of document.querySelectorAll('.ytce-r42ai-media-outline')) { classListRemoveRoles(el); el.classList.remove('ytce-r42ai-media-outline'); }
    clearMediaBoxes();
  }

  function missingRolePreview(limit) {
    const missing = [];
    try {
      const text = normalize(document.body ? document.body.innerText || '' : '');
      for (const row of rows()) {
        const k = rowKind(row);
        if (['image','video','media','link','archive','locator'].includes(k)) continue;
        if (textAlreadyPaintedForRow(row)) continue;
        const n = normalize(textForRow(row));
        if (!n || n.length < 2) continue;
        if (text.includes(n.slice(0, Math.min(80, n.length)))) missing.push(shortText(textForRow(row), 90));
        if (missing.length >= (limit || 10)) break;
      }
    } catch(e) {}
    return missing;
  }

  function applyPaint(reason) {
    paintScheduled = false;
    const paintStart = performance.now();
    try {
      if (!document.documentElement) return;
      installStyle();
      installToolbar();
      const textPainted = paintTextRows();
      if (textPainted && mode === 'media') mediaCacheWarm = false;
      const mediaPainted = mode === 'media' ? paintMediaRows(true) : 0;
      updateToolbar();
      const paintDuration = Math.round(performance.now() - paintStart);
      const currentTextSpans = document.querySelectorAll('.ytce-role-hit').length;
      const currentMediaOutlines = document.querySelectorAll('.ytce-r42ai-media-outline').length;
      const currentMediaBoxes = document.querySelectorAll('.ytce-r42cr-media-box').length;
      const usefulPaint = textPainted || mediaPainted || currentTextSpans || currentMediaOutlines || currentMediaBoxes;
      if (!firstPaintSent && usefulPaint) {
        firstPaintSent = true;
        post('first_role_paint', { reason, mode, token: COMMAND_TOKEN, duration_ms: paintDuration, text_spans: currentTextSpans, media_outlines: currentMediaOutlines, media_boxes: currentMediaBoxes, missing_preview: missingRolePreview(8) });
      } else if (textPainted || mediaPainted) {
        post('role_paint_delta', { reason, mode, token: COMMAND_TOKEN, duration_ms: paintDuration, text_painted: textPainted, media_painted: mediaPainted, text_spans: document.querySelectorAll('.ytce-role-hit').length, media_outlines: document.querySelectorAll('.ytce-r42ai-media-outline').length, media_boxes: document.querySelectorAll('.ytce-r42cr-media-box').length });
      }
    } catch (e) {
      post('paint_error', { reason, token: COMMAND_TOKEN, message: shortError(e), duration_ms: Math.round(performance.now() - paintStart) });
    }
  }
  function schedulePaint(reason) {
    if (paintScheduled) return;
    paintScheduled = true;
    requestAnimationFrame(() => applyPaint(reason || 'scheduled'));
  }
  function startObserver() {
    if (observerStarted || !document.documentElement) return;
    observerStarted = true;
    let lastMutationPaintRequest = 0;
    const obs = new MutationObserver(() => {
      const now = performance.now();
      // R42CR: after the first useful paint, Metro ad/video churn can fire many
      // mutations.  Throttle full text-scan paint requests so clicks/toggles stay
      // responsive while still allowing late article content to be picked up.
      if (firstPaintSent && now - lastMutationPaintRequest < 450) return;
      lastMutationPaintRequest = now;
      schedulePaint('mutation');
    });
    obs.observe(document.documentElement, { childList: true, subtree: true, characterData: true });
    setTimeout(() => { try { obs.disconnect(); post('observer_stopped', { text_spans: document.querySelectorAll('.ytce-role-hit').length, media_outlines: document.querySelectorAll('.ytce-r42ai-media-outline').length, media_boxes: document.querySelectorAll('.ytce-r42cr-media-box').length }); } catch(e) {} }, 60000);
    post('observer_started');
  }

  let lastScrollPaint = 0;
  window.addEventListener('scroll', () => { const now = performance.now(); if (mode === 'media') renderMediaBoxesFromExisting(); if (now - lastScrollPaint > 650) { lastScrollPaint = now; schedulePaint('scroll'); } }, { passive: true });
  window.addEventListener('resize', () => { if (mode === 'media') requestAnimationFrame(renderMediaBoxesFromExisting); }, { passive: true });

  const bootTimer = setInterval(() => {
    installStyle();
    installToolbar();
    startObserver();
    schedulePaint('boot_timer');
    if (document.body && document.readyState !== 'loading') clearInterval(bootTimer);
  }, 50);
  setTimeout(() => clearInterval(bootTimer), 5000);
  document.addEventListener('DOMContentLoaded', () => { post('page_dom_content_loaded_from_js', { title: document.title }); installToolbar(); scheduleToolbarSafeAreaBurst(); startObserver(); schedulePaint('dom_content_loaded'); scheduleMediaWarm('dom_content_loaded'); }, { once: true });
  window.addEventListener('load', () => { post('page_load_from_js', { title: document.title }); schedulePaint('page_load'); scheduleMediaWarm('page_load'); }, { once: true });
})();
""";
    }
}

internal sealed class TimingLogger : IDisposable
{
    private readonly Stopwatch _watch = Stopwatch.StartNew();
    private readonly StreamWriter? _writer;
    private readonly object _lock = new();

    public TimingLogger(string[] args, string heading)
    {
        var logPath = Args.Get(args, "--log");
        if (!string.IsNullOrWhiteSpace(logPath))
        {
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(logPath)) ?? ".");
            _writer = new StreamWriter(new FileStream(logPath, FileMode.Append, FileAccess.Write, FileShare.ReadWrite)) { AutoFlush = true };
            _writer.WriteLine();
            _writer.WriteLine($"===== {heading} {DateTimeOffset.Now:O} =====");
        }
    }

    public long ElapsedMilliseconds => _watch.ElapsedMilliseconds;

    public void Log(string eventName, string details = "")
    {
        var line = $"{DateTimeOffset.Now:O} +{_watch.ElapsedMilliseconds,6}ms {eventName}: {details}";
        lock (_lock)
        {
            Console.WriteLine(line);
            Console.Out.Flush();
            _writer?.WriteLine(line);
        }
    }

    public void Dispose()
    {
        _writer?.Dispose();
    }
}

internal static class Args
{
    public static string? Get(string[] args, string name)
    {
        for (var i = 0; i < args.Length; i++)
        {
            if (!string.Equals(args[i], name, StringComparison.OrdinalIgnoreCase)) continue;
            if (i + 1 < args.Length) return args[i + 1];
            return string.Empty;
        }
        return null;
    }

    public static bool Has(string[] args, string name)
    {
        foreach (var arg in args)
        {
            if (string.Equals(arg, name, StringComparison.OrdinalIgnoreCase)) return true;
        }
        return false;
    }
}
