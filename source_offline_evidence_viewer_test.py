from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_offline_evidence_viewer import generate_offline_backup_viewer


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "screenshots").mkdir()
        (root / "screenshots" / "android_article_MAIN_SINGLE_reference_style.png").write_bytes(b"fakepngarticle")
        (root / "screenshots" / "android_comments_all_expanded_SINGLE_INTERNAL_STITCH.png").write_bytes(b"fakepngcomments")
        comments = {
            "comments": [
                {
                    "human_id": "C0001",
                    "type": "Parent Comment",
                    "author": "A",
                    "text": "Canonical parent text",
                    "likes": "2",
                    "replies": [
                        {
                            "human_id": "R0001",
                            "parent_human_id": "C0001",
                            "type": "Reply",
                            "author": "B",
                            "text": "Canonical reply text",
                            "likes": "1",
                            "replies": [],
                        }
                    ],
                }
            ]
        }
        (root / "comments.json").write_text(json.dumps(comments, ensure_ascii=False), encoding="utf-8")
        profiles = [
            {
                "author": "A",
                "profile_cid": "cid-abc123",
                "canonical_url": "",
                "account_comments": "",
                "account_likes": "",
                "account_followers": "",
                "profile_stats_status": "not_found",
                "profile_stats_method": "not_found",
            },
            {
                "author": "B",
                "profile_cid": "cid-def456",
                "canonical_url": "https://www.msn.com/en-gb/community/profile/cid-def456",
                "account_comments": "10",
                "account_likes": "20",
                "account_followers": "3",
                "profile_stats_status": "found",
                "profile_stats_method": "profile_card_text",
            },
        ]
        (root / "profiles.json").write_text(json.dumps(profiles, ensure_ascii=False), encoding="utf-8")
        (root / "memento_archive_discovery.json").write_text(json.dumps({
            "status": "MEMENTOS_FOUND",
            "memento_count": 1,
            "first_memento": {"timestamp": "20260730140946", "archive_url": "https://web.archive.org/web/20260730140946/example"},
            "latest_memento": {"timestamp": "20260730140946", "archive_url": "https://web.archive.org/web/20260730140946/example"},
        }, ensure_ascii=False), encoding="utf-8")
        (root / "archive_replay_status.json").write_text(json.dumps({
            "WARC_REPLAY_STRUCTURAL_STATUS": "PASS",
            "PYWB_VISUAL_REPLAY_STATUS": "NOT_ACCEPTED",
        }), encoding="utf-8")
        (root / "offline_backup_viewer_input_receipt.json").write_text(
            json.dumps({"accepted_reference_gate": "PASS"}), encoding="utf-8"
        )
        (root / "live_capture").mkdir()
        (root / "live_capture" / "rendered-page.pywb-indexable.warc.gz").write_bytes(b"fakewarc")

        res = generate_offline_backup_viewer(root)
        viewer = Path(res["offline_backup_viewer_html"])
        manifest = Path(res["offline_backup_manifest_json"])
        assert viewer.exists(), viewer
        assert manifest.exists(), manifest

        text = viewer.read_text(encoding="utf-8")
        manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
        assert "MSN Offline Evidence Backup Viewer" in text
        assert "Structured comments backup — canonical text" in text
        assert "Canonical parent text" in text
        assert "Canonical reply text" in text
        assert manifest_data["comment_count_loaded"] == 2
        assert manifest_data["profile_count_loaded"] == 2
        assert manifest_data["profile_stats_found_count"] == 1
        assert "V35-style fields" in text
        assert "<th>Comments</th><th>Likes</th><th>Followers</th>" in text
        assert "https://www.msn.com/en-gb/community/profile/cid-abc123" in text
        assert "URL reconstructed from stored CID" in text
        assert "Not captured" in text
        assert "MEMENTOS_FOUND" in text
        assert "NOT_ACCEPTED" in text
        assert "Partial / experimental archive-replay artifacts" in text
        assert "accepted_reference_gate" in text
    print("source_offline_evidence_viewer_test OK")


if __name__ == "__main__":
    main()
