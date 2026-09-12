from main import App


class FakeCard:
    def __init__(self) -> None:
        self.grid_calls = 0
        self.grid_remove_calls = 0
        self.configure_calls = []
        self.mapped = False

    def grid(self) -> None:
        self.grid_calls += 1
        self.mapped = True

    def grid_remove(self) -> None:
        self.grid_remove_calls += 1
        self.mapped = False

    def configure(self, **kwargs: object) -> None:
        self.configure_calls.append(dict(kwargs))

    def winfo_ismapped(self) -> bool:
        return self.mapped


class FakeButton:
    def __init__(self) -> None:
        self.configure_calls = []

    def configure(self, **kwargs: object) -> None:
        self.configure_calls.append(dict(kwargs))


def test_transcript_panel_methods_do_not_probe_tk_on_stub_app() -> None:
    app = App.__new__(App)
    assert "tk" not in getattr(app, "__dict__", {})

    App._show_transcript_panel(app)
    App._hide_transcript_panel(app)
    App._toggle_transcript_panel(app)


def test_transcript_panel_methods_use_instance_dictionary_widgets() -> None:
    app = App.__new__(App)
    card = FakeCard()
    button = FakeButton()
    app.transcript_card = card
    app.show_transcript_panel_button = button

    App._show_transcript_panel(app)
    assert card.grid_calls == 1
    assert button.configure_calls

    App._toggle_transcript_panel(app)
    assert card.grid_remove_calls == 1


def test_transcript_drop_highlight_does_not_probe_tk_on_stub_app() -> None:
    app = App.__new__(App)
    app.transcript_segments = []
    app._transcript_empty_state_text = lambda: "empty"

    App._set_transcript_drop_highlight(app, True)
    App._set_transcript_drop_highlight(app, False)


def run_self_test() -> None:
    test_transcript_panel_methods_do_not_probe_tk_on_stub_app()
    test_transcript_panel_methods_use_instance_dictionary_widgets()
    test_transcript_drop_highlight_does_not_probe_tk_on_stub_app()
    print("session_files_transcript_panel_guard_r42gf_test OK")


if __name__ == "__main__":
    run_self_test()
