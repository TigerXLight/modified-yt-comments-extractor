from main import App


class FakeWidget:
    def __init__(self) -> None:
        self.configure_calls = []
        self.delete_calls = []
        self.insert_calls = []
        self.grid_calls = 0
        self.grid_remove_calls = 0
        self.lift_calls = 0
        self.mapped = False

    def configure(self, **kwargs: object) -> None:
        self.configure_calls.append(dict(kwargs))

    def delete(self, *args: object) -> None:
        self.delete_calls.append(tuple(args))

    def insert(self, *args: object) -> None:
        self.insert_calls.append(tuple(args))

    def grid(self) -> None:
        self.grid_calls += 1
        self.mapped = True

    def grid_remove(self) -> None:
        self.grid_remove_calls += 1
        self.mapped = False

    def lift(self) -> None:
        self.lift_calls += 1

    def winfo_ismapped(self) -> bool:
        return self.mapped


def test_editor_panel_methods_do_not_probe_tk_on_stub_app() -> None:
    app = App.__new__(App)
    assert "tk" not in getattr(app, "__dict__", {})

    App._show_text_editor_panel(app)
    App._hide_text_editor_panel(app)
    App._toggle_text_editor_panel(app)
    App._reset_editor_panels_after_file_intake(app)

    assert app.active_text_editor_file_path == ""


def test_editor_panel_methods_use_instance_dictionary_widgets() -> None:
    app = App.__new__(App)
    card = FakeWidget()
    button = FakeWidget()
    app.text_editor_card = card
    app.show_text_editor_panel_button = button
    app._hide_text_editor_spell_popup = lambda: setattr(app, "spell_popup_hidden", True)

    App._show_text_editor_panel(app)
    assert card.grid_calls == 1
    assert card.lift_calls == 1
    assert button.configure_calls

    App._toggle_text_editor_panel(app)
    assert card.grid_remove_calls == 1
    assert getattr(app, "spell_popup_hidden") is True


def test_reset_editor_panels_updates_optional_widgets_without_tk_probe() -> None:
    app = App.__new__(App)
    status = FakeWidget()
    textbox = FakeWidget()
    save = FakeWidget()
    external = FakeWidget()
    app.text_editor_status_label = status
    app.text_editor_textbox = textbox
    app.text_editor_save_button = save
    app.text_editor_external_open_button = external
    app._hide_text_editor_panel = lambda: setattr(app, "text_editor_hidden", True)
    app._hide_transcript_panel = lambda: setattr(app, "transcript_hidden", True)

    App._reset_editor_panels_after_file_intake(app)

    assert app.active_text_editor_file_path == ""
    assert status.configure_calls[-1]["text"] == "No text file loaded"
    assert textbox.delete_calls == [("1.0", "end")]
    assert textbox.insert_calls
    assert save.configure_calls[-1]["state"] == "disabled"
    assert external.configure_calls[-1]["state"] == "disabled"
    assert app.text_editor_hidden is True
    assert app.transcript_hidden is True


def run_self_test() -> None:
    test_editor_panel_methods_do_not_probe_tk_on_stub_app()
    test_editor_panel_methods_use_instance_dictionary_widgets()
    test_reset_editor_panels_updates_optional_widgets_without_tk_probe()
    print("session_files_editor_reset_guard_r42gf_test OK")


if __name__ == "__main__":
    run_self_test()
