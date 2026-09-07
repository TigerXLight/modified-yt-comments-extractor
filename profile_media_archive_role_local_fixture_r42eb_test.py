from __future__ import annotations

from profile_media_archive_role_local_fixture_r42eb import clean_source_url, run_self_test, _log_has_count_format

def test_clean_source_url_markdown_and_known_archive_case():
    run_self_test()
    assert clean_source_url("[https://archive.ph/6mr3C](https://archive.ph/6mr3C)") == "https://archive.ph/6mr3C"
    assert clean_source_url("https://archive.ph/6Mr3C") == "https://archive.ph/6mr3C"
    assert clean_source_url("https://archive.ph/AbCdE") == "https://archive.ph/AbCdE"
    expected_sem = {"PRIMARY": 0, "SECONDARY": 35, "TERTIARY": 0, "UNKNOWN": 15, "BLANK": 11}
    expected_med = {"PRIMARY": 0, "SECONDARY": 41, "TERTIARY": 0, "UNKNOWN": 11, "BLANK": 0}
    assert _log_has_count_format("native_toolbar_ready: counts_semantic=P0/S35/T0/U15", "counts_semantic", expected_sem)
    assert _log_has_count_format("native_toolbar_ready: counts_media=P0/S41/T0/U11", "counts_media", expected_med)
    assert _log_has_count_format("native_toolbar_ready: counts_semantic=0,35,0,15", "counts_semantic", expected_sem)

if __name__ == "__main__":
    test_clean_source_url_markdown_and_known_archive_case()
    print("R42EB tests passed.")
