from __future__ import annotations

from dataclasses import dataclass

from webpage_video_variant_grouping import (
    group_video_rendition_items,
    normalize_video_rendition_content_key,
    video_variant_quality_label,
    video_variant_quality_option_labels,
    video_variant_url_dimensions,
)


@dataclass(frozen=True)
class FakeVideoItem:
    resource_id: str
    reference_url: str
    display_name: str = "People shout seagull eater at me in the street after far right l"
    extension: str = ".mp4"
    mime_type: str = "video/mp4"
    width: int = 0
    height: int = 0


def _media_url(item: FakeVideoItem) -> str:
    return item.reference_url


def test_metro_quality_renditions_share_content_key() -> None:
    low = "https://videos.metro.co.uk/video/met/2026/07/16/7351137571375236737/480x270_MP4_7351137571375236737.mp4"
    high = "https://videos.metro.co.uk/video/met/2026/07/16/7351137571375236737/1024x576_MP4_7351137571375236737.mp4"
    assert normalize_video_rendition_content_key(low, title="same title")
    assert normalize_video_rendition_content_key(low, title="article title") == normalize_video_rendition_content_key(high, title="file MP4 from source")


def test_group_video_renditions_prefers_highest_resolution() -> None:
    low = FakeVideoItem(
        resource_id="low",
        reference_url="https://videos.metro.co.uk/video/met/2026/07/16/7351137571375236737/480x270_MP4_7351137571375236737.mp4",
        width=270,
        height=480,
    )
    high = FakeVideoItem(
        resource_id="high",
        reference_url="https://videos.metro.co.uk/video/met/2026/07/16/7351137571375236737/1024x576_MP4_7351137571375236737.mp4",
        width=576,
        height=1024,
    )
    other = FakeVideoItem(
        resource_id="other",
        reference_url="https://videos.metro.co.uk/video/met/2026/07/16/1111111111111111111/1024x576_MP4_1111111111111111111.mp4",
        display_name="different clip",
        width=576,
        height=1024,
    )

    display, groups, rep_by_variant = group_video_rendition_items((low, high, other), media_url_getter=_media_url)

    assert [item.resource_id for item in display] == ["high", "other"]
    assert tuple(item.resource_id for item in groups["high"]) == ("high", "low")
    assert rep_by_variant == {"high": "high", "low": "high"}
    assert video_variant_quality_label(groups["high"][0]).startswith("1024x576")


def test_variant_labels_prefer_url_dimensions_when_metadata_is_poster_sized() -> None:
    low = FakeVideoItem(
        resource_id="low",
        reference_url="https://videos.metro.co.uk/video/met/2026/07/16/7351137571375236737/480x270_MP4_7351137571375236737.mp4",
        width=576,
        height=1024,
    )
    high = FakeVideoItem(
        resource_id="high",
        reference_url="https://videos.metro.co.uk/video/met/2026/07/16/7351137571375236737/1024x576_MP4_7351137571375236737.mp4",
        width=576,
        height=1024,
    )

    display, groups, rep_by_variant = group_video_rendition_items((low, high), media_url_getter=_media_url)
    labels = video_variant_quality_option_labels(groups["high"])

    assert [item.resource_id for item in display] == ["high"]
    assert rep_by_variant == {"high": "high", "low": "high"}
    assert video_variant_url_dimensions(high) == (1024, 576)
    assert video_variant_url_dimensions(low) == (480, 270)
    assert labels == ("1024x576 MP4 / high", "480x270 MP4 / low")
    selected_by_label = dict(zip(labels, groups["high"]))
    assert selected_by_label["1024x576 MP4 / high"].reference_url.endswith("1024x576_MP4_7351137571375236737.mp4")
    assert selected_by_label["480x270 MP4 / low"].reference_url.endswith("480x270_MP4_7351137571375236737.mp4")


def run_tests() -> None:
    test_metro_quality_renditions_share_content_key()
    test_group_video_renditions_prefers_highest_resolution()
    test_variant_labels_prefer_url_dimensions_when_metadata_is_poster_sized()
    print("webpage_video_variant_grouping_test OK")


if __name__ == "__main__":
    run_tests()
