import main
from main import App


class FakeDndWidget:
    def __init__(self) -> None:
        self.registered: list[object] = []
        self.bindings: dict[str, object] = {}
        self.master = None

    def drop_target_register(self, drop_type: object) -> None:
        self.registered.append(drop_type)

    def dnd_bind(self, event_name: str, callback: object) -> None:
        self.bindings[event_name] = callback


class FakePanel:
    def __init__(self) -> None:
        self.grid_calls = 0
        self.grid_remove_calls = 0
        self.mapped = False

    def grid(self) -> None:
        self.grid_calls += 1
        self.mapped = True

    def grid_remove(self) -> None:
        self.grid_remove_calls += 1
        self.mapped = False

    def winfo_ismapped(self) -> bool:
        return self.mapped


class FakeButton:
    def __init__(self) -> None:
        self.configured: list[dict[str, object]] = []

    def configure(self, **kwargs: object) -> None:
        self.configured.append(dict(kwargs))


def _make_app() -> App:
    return App.__new__(App)


def test_final_drop_binding_skips_missing_converter_widgets_on_tkless_stub() -> None:
    app = _make_app()
    app.file_drag_drop_ready = True
    app._file_drag_drop_type = "DND_FILES"
    app.files_header_frame = FakeDndWidget()
    app.files_frame = FakeDndWidget()
    app.files_list_frame = FakeDndWidget()
    app.files_empty_label = FakeDndWidget()
    app.files_drop_status_label = FakeDndWidget()
    app.transcript_card = FakeDndWidget()
    app.transcript_textbox = FakeDndWidget()
    app.transcript_timeline_canvas = FakeDndWidget()
    transcript_text_widget = FakeDndWidget()
    app._get_transcript_text_widget = lambda: transcript_text_widget

    assert App._bind_final_file_drop_targets(app) is True

    assert app.file_drag_drop_ready is True
    assert app.file_drag_drop_status == "ready"
    assert app.file_converter_drag_drop_available is False
    assert app.files_header_frame.registered == ["DND_FILES"]
    assert app.transcript_card.registered == ["DND_FILES"]
    assert transcript_text_widget.registered == ["DND_FILES"]


def test_converter_drop_binding_uses_only_real_instance_widgets() -> None:
    app = _make_app()
    app.file_drag_drop_ready = True
    app._file_drag_drop_type = "DND_FILES"
    app.file_converter_card = FakeDndWidget()
    app.file_converter_drop_frame = FakeDndWidget()
    app.file_converter_drop_list_frame = FakeDndWidget()
    app.file_converter_queue_textbox = FakeDndWidget()

    assert App._bind_file_converter_drop_targets(app) is True

    for widget in (
        app.file_converter_card,
        app.file_converter_drop_frame,
        app.file_converter_drop_list_frame,
        app.file_converter_queue_textbox,
    ):
        assert widget.registered == ["DND_FILES"]
        assert "<<DropEnter>>" in widget.bindings
        assert "<<DropLeave>>" in widget.bindings
        assert "<<Drop>>" in widget.bindings


def test_file_converter_panel_controls_do_not_probe_tk_for_missing_widgets() -> None:
    app = _make_app()

    App._show_file_converter_panel(app)
    App._hide_file_converter_panel(app)
    App._toggle_file_converter_panel(app)

    app.file_converter_card = FakePanel()
    app.show_file_converter_panel_button = FakeButton()
    App._show_file_converter_panel(app)
    assert app.file_converter_card.grid_calls == 1
    assert app.show_file_converter_panel_button.configured[-1]["fg_color"] == main.COLORS["accent"]

    App._toggle_file_converter_panel(app)
    assert app.file_converter_card.grid_remove_calls == 1


def test_session_file_converter_drop_target_match_uses_instance_state_only() -> None:
    app = _make_app()
    converter = FakeDndWidget()
    child = FakeDndWidget()
    child.master = converter
    app.file_converter_card = converter

    assert App._session_file_drop_target_is_converter(app, child) is True
    assert App._session_file_drop_target_is_converter(app, FakeDndWidget()) is False


def run_self_test() -> None:
    test_final_drop_binding_skips_missing_converter_widgets_on_tkless_stub()
    test_converter_drop_binding_uses_only_real_instance_widgets()
    test_file_converter_panel_controls_do_not_probe_tk_for_missing_widgets()
    test_session_file_converter_drop_target_match_uses_instance_state_only()
    print("session_files_drop_target_widget_guard_r42gf_test OK")


if __name__ == "__main__":
    run_self_test()
