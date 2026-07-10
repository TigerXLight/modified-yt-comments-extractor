from source_adapters import (
    AVAILABLE_SOURCE_ADAPTERS,
    YOUTUBE_SOURCE_ADAPTER,
    find_source_adapter,
    find_source_adapter_by_name,
    source_adapter_names,
)


def run_self_test() -> None:
    names = source_adapter_names()
    assert names == ("youtube",)

    assert find_source_adapter_by_name("youtube") is YOUTUBE_SOURCE_ADAPTER
    assert find_source_adapter_by_name(" YouTube ") is YOUTUBE_SOURCE_ADAPTER
    assert find_source_adapter_by_name("missing") is None
    assert find_source_adapter_by_name("") is None

    for adapter in AVAILABLE_SOURCE_ADAPTERS:
        assert adapter.source_name
        assert adapter.metadata.display_name
        assert not hasattr(adapter, "name")

    assert find_source_adapter("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is YOUTUBE_SOURCE_ADAPTER
    assert find_source_adapter("https://example.com/not-supported") is None


if __name__ == "__main__":
    run_self_test()
    print("Source adapter registry self-test passed.")
