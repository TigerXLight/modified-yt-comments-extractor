from typing import Any, Dict, List, Optional

from core.constants import SortOption
from core.settings import AppSettings
from core.validators import MaxCommentsValidator
from extractor import YouTubeCommentExtractor


VALID_ID = "aB3_dE-9xYz"
CANONICAL_URL = f"https://www.youtube.com/watch?v={VALID_ID}"


class FakeRequest:
    def __init__(self, response: Dict[str, Any]):
        self.response = response

    def execute(self) -> Dict[str, Any]:
        return self.response


class FakeVideosService:
    def list(self, **_kwargs: Any) -> FakeRequest:
        return FakeRequest({
            "items": [{
                "snippet": {
                    "title": "Test Video",
                    "channelTitle": "Test Channel",
                    "channelId": "channel-owner",
                    "publishedAt": "2026-07-09T10:00:00Z",
                    "description": "",
                },
                "statistics": {
                    "commentCount": "3",
                    "viewCount": "10",
                    "likeCount": "2",
                },
                "liveStreamingDetails": {},
            }]
        })


class FakeCommentThreadsService:
    def __init__(self, pages: List[Dict[str, Any]]):
        self.pages = pages
        self.list_calls: List[Dict[str, Any]] = []
        self.list_next_calls = 0
        self._next_index = 1

    def list(self, **kwargs: Any) -> FakeRequest:
        self.list_calls.append(kwargs)
        self._next_index = 1
        return FakeRequest(self.pages[0])

    def list_next(self, _request: FakeRequest, _response: Dict[str, Any]) -> Optional[FakeRequest]:
        self.list_next_calls += 1
        if self._next_index >= len(self.pages):
            return None
        response = self.pages[self._next_index]
        self._next_index += 1
        return FakeRequest(response)


class FakeCommentsService:
    def __init__(self, replies_by_parent: Dict[str, List[Dict[str, Any]]]):
        self.replies_by_parent = replies_by_parent
        self.list_calls: List[Dict[str, Any]] = []
        self.list_next_calls = 0
        self._active_parent = ""
        self._next_index = 1

    def list(self, **kwargs: Any) -> FakeRequest:
        self.list_calls.append(kwargs)
        self._active_parent = kwargs["parentId"]
        self._next_index = 1
        pages = self.replies_by_parent.get(self._active_parent, [{"items": []}])
        return FakeRequest(pages[0])

    def list_next(self, _request: FakeRequest, _response: Dict[str, Any]) -> Optional[FakeRequest]:
        self.list_next_calls += 1
        pages = self.replies_by_parent.get(self._active_parent, [{"items": []}])
        if self._next_index >= len(pages):
            return None
        response = pages[self._next_index]
        self._next_index += 1
        return FakeRequest(response)


class FakeYouTube:
    def __init__(
        self,
        comment_pages: List[Dict[str, Any]],
        replies_by_parent: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ):
        self.comment_threads_service = FakeCommentThreadsService(comment_pages)
        self.comments_service = FakeCommentsService(replies_by_parent or {})
        self.videos_service = FakeVideosService()

    def commentThreads(self) -> FakeCommentThreadsService:
        return self.comment_threads_service

    def comments(self) -> FakeCommentsService:
        return self.comments_service

    def videos(self) -> FakeVideosService:
        return self.videos_service


def _make_extractor(fake_youtube: FakeYouTube) -> YouTubeCommentExtractor:
    extractor = YouTubeCommentExtractor.__new__(YouTubeCommentExtractor)
    extractor.youtube = fake_youtube
    extractor.spam_threshold = 0.5
    extractor.blacklist_patterns = []
    extractor.whitelist_patterns = []
    extractor._should_stop = False
    return extractor


def _parent_thread(comment_id: str, published_at: str, reply_count: int = 0) -> Dict[str, Any]:
    return {
        "id": f"thread-{comment_id}",
        "snippet": {
            "totalReplyCount": reply_count,
            "topLevelComment": {
                "id": comment_id,
                "snippet": {
                    "authorDisplayName": f"Author {comment_id}",
                    "authorChannelId": {"value": f"author-channel-{comment_id}"},
                    "textDisplay": f"Parent {comment_id}",
                    "likeCount": 0,
                    "publishedAt": published_at,
                    "updatedAt": published_at,
                },
            },
        },
    }


def _reply(comment_id: str, published_at: str) -> Dict[str, Any]:
    return {
        "id": comment_id,
        "snippet": {
            "authorDisplayName": f"Reply Author {comment_id}",
            "authorChannelId": {"value": f"reply-channel-{comment_id}"},
            "textDisplay": f"Reply {comment_id}",
            "likeCount": 0,
            "publishedAt": published_at,
            "updatedAt": published_at,
        },
    }


def test_sort_order_helpers() -> None:
    assert YouTubeCommentExtractor.api_comment_order("Date (Newest)") == "time"
    assert YouTubeCommentExtractor.api_comment_order("newest") == "time"
    assert YouTubeCommentExtractor.api_comment_order(SortOption.DATE_NEWEST.value) == "time"
    assert YouTubeCommentExtractor.api_comment_order(SortOption.DATE_OLDEST.value) == "time"
    assert YouTubeCommentExtractor.api_comment_order("time") == "time"
    assert YouTubeCommentExtractor.api_comment_order("Likes") == "relevance"
    assert YouTubeCommentExtractor.api_comment_order("relevance") == "relevance"

    assert SortOption.from_display_name("Date (Newest)") is SortOption.DATE_NEWEST
    assert SortOption.from_display_name("Newest") is SortOption.DATE_NEWEST
    assert SortOption.from_display_name("unknown display") is SortOption.DATE_NEWEST
    assert AppSettings().sort_by == SortOption.DATE_NEWEST.value


def test_max_comments_validator() -> None:
    assert MaxCommentsValidator.parse("") == (None, None)
    assert MaxCommentsValidator.parse("   ") == (None, None)
    assert MaxCommentsValidator.parse("25") == (25, None)

    parsed, warning = MaxCommentsValidator.parse("0")
    assert parsed is None
    assert warning is not None

    parsed, warning = MaxCommentsValidator.parse("not-a-number")
    assert parsed is None
    assert warning is not None


def test_process_video_default_uses_time_order() -> None:
    fake_youtube = FakeYouTube([
        {"items": [_parent_thread("parent-1", "2026-07-09T10:00:00Z")]}
    ])
    extractor = _make_extractor(fake_youtube)

    metadata, comments, spam = extractor.process_video(CANONICAL_URL, max_results=1)

    assert metadata["items_fetched"] == 1
    assert len(comments) == 1
    assert spam == []
    assert fake_youtube.comment_threads_service.list_calls[0]["order"] == "time"


def test_max_results_counts_parent_comments_and_replies() -> None:
    parent_id = "parent-with-replies"
    fake_youtube = FakeYouTube(
        [{"items": [_parent_thread(parent_id, "2026-07-09T10:00:00Z", reply_count=2)]}],
        replies_by_parent={
            parent_id: [{
                "items": [
                    _reply("reply-1", "2026-07-09T10:01:00Z"),
                    _reply("reply-2", "2026-07-09T10:02:00Z"),
                ]
            }]
        },
    )
    extractor = _make_extractor(fake_youtube)

    comments = extractor.fetch_comments_and_replies(
        video_id=VALID_ID,
        metadata={"video_id": VALID_ID, "title": "Test", "channel_title": "Channel"},
        sort_by=SortOption.DATE_NEWEST.value,
        max_results=2,
        min_likes=0,
        exclude_creator=False,
        date_from=None,
        date_to=None,
        filter_words=None,
        cancel_event=None,
        progress_callback=None,
    )

    assert [row["type"] for row in comments] == ["Parent Comment", "Reply"]
    assert [row["id"] for row in comments] == [parent_id, "reply-1"]
    assert fake_youtube.comment_threads_service.list_calls[0]["order"] == "time"


def run_self_test() -> None:
    test_sort_order_helpers()
    test_max_comments_validator()
    test_process_video_default_uses_time_order()
    test_max_results_counts_parent_comments_and_replies()


if __name__ == "__main__":
    run_self_test()
    print("Extractor sort/max-comments self-test passed.")
