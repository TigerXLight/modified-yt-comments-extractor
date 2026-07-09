import threading

import main
from main import App, FetchState, is_export_allowed


class MessageBoxRecorder:
    def __init__(self) -> None:
        self.warnings = []

    def showwarning(self, title: str, message: str) -> None:
        self.warnings.append((title, message))


class DialogRecorder:
    def __init__(self) -> None:
        self.save_called = False

    def asksaveasfilename(self, **_kwargs: object) -> str:
        self.save_called = True
        raise AssertionError("Save dialog should not open while export is blocked")


def _make_app(fetch_state: FetchState, comments: list[dict[str, object]]) -> App:
    app = App.__new__(App)
    app.fetch_state = fetch_state
    app._data_lock = threading.Lock()
    app.all_metadata = [{"video_id": "aB3_dE-9xYz"}] if comments else []
    app.all_comments = comments
    app.all_spam = []
    app.log_messages = []
    app.log_message = lambda message, level="info": app.log_messages.append((message, level))
    return app


def test_export_allowed_helper() -> None:
    idle_with_data = FetchState(is_fetching=False)
    assert is_export_allowed(idle_with_data, 1)

    idle_without_data = FetchState(is_fetching=False)
    assert not is_export_allowed(idle_without_data, 0)

    fetching = FetchState(is_fetching=True)
    assert not is_export_allowed(fetching, 1)

    cancelling = FetchState(is_fetching=False)
    cancelling.request_cancel()
    assert not is_export_allowed(cancelling, 1)


def test_direct_export_blocks_save_dialog_while_fetching() -> None:
    messagebox = MessageBoxRecorder()
    filedialog = DialogRecorder()
    original_messagebox = main.messagebox
    original_filedialog = main.filedialog
    main.messagebox = messagebox
    main.filedialog = filedialog
    try:
        app = _make_app(
            FetchState(is_fetching=True),
            [{"id": "comment-1", "text": "Exportable comment"}],
        )

        app.export_csv()

        assert not filedialog.save_called
        assert messagebox.warnings
        assert messagebox.warnings[0][0] == "Fetch In Progress"
        assert app.log_messages[-1][1] == "warning"
    finally:
        main.messagebox = original_messagebox
        main.filedialog = original_filedialog


def test_direct_export_blocks_save_dialog_without_data() -> None:
    messagebox = MessageBoxRecorder()
    filedialog = DialogRecorder()
    original_messagebox = main.messagebox
    original_filedialog = main.filedialog
    main.messagebox = messagebox
    main.filedialog = filedialog
    try:
        app = _make_app(FetchState(is_fetching=False), [])

        app.export_txt()

        assert not filedialog.save_called
        assert messagebox.warnings
        assert messagebox.warnings[0][0] == "No Data"
    finally:
        main.messagebox = original_messagebox
        main.filedialog = original_filedialog


def run_self_test() -> None:
    test_export_allowed_helper()
    test_direct_export_blocks_save_dialog_while_fetching()
    test_direct_export_blocks_save_dialog_without_data()


if __name__ == "__main__":
    run_self_test()
    print("Main export state self-test passed.")
