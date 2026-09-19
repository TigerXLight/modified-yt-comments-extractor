#!/usr/bin/env python3
from pathlib import Path
import tempfile
import profile_media_facebook_print_clean_evidence_screenshot_r45i as r45i


def test_self_test_passes():
    with tempfile.TemporaryDirectory() as td:
        class Args:
            output_root = td
        report = r45i.run_self_test(Args())
        assert report['status'] == r45i.STATUS_PASS
        assert report['sample_result']['comment_count'] == 3
        assert Path(report['sample_result']['html_path']).exists()


def test_extract_blocks_from_inner_text():
    text = 'Tony Bentley\nMohhamed etc is the first name\nDan Melin\nLook I am all for Restore\n'
    blocks = r45i.extract_blocks_from_inner_text(text)
    assert blocks
    assert blocks[0]['author_candidate'] == 'Tony Bentley'


if __name__ == '__main__':
    test_self_test_passes()
    test_extract_blocks_from_inner_text()
    print('profile_media_facebook_print_clean_evidence_screenshot_r45i_test: PASS')
