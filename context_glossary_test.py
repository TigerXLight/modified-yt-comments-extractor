from context_glossary import (
    GlossaryTerm,
    HINT_SOURCE_SOURCE_URL,
    HINT_SOURCE_TITLE,
    TERM_CATEGORY_PERSON,
    dedupe_glossary_terms,
    glossary_key,
    glossary_terms_from_strings,
    normalize_glossary_text,
    phrase_prompt_terms,
    resolve_context_hints,
)


def run_self_test() -> None:
    assert normalize_glossary_text("  Nicolas   Cage  ") == "Nicolas Cage"
    assert normalize_glossary_text("   ") == ""
    assert glossary_key("  Shadowsmith  ") == "shadowsmith"
    assert glossary_key("  Shadowsmith  ", case_sensitive=True) == "Shadowsmith"

    terms = glossary_terms_from_strings(
        [" Shadowsmith ", "", "shadowsmith", "Caltheris"],
        category=TERM_CATEGORY_PERSON,
    )
    assert [term.text for term in terms] == ["Shadowsmith", "Caltheris"]
    assert all(term.category == TERM_CATEGORY_PERSON for term in terms)

    case_terms = dedupe_glossary_terms(
        [
            GlossaryTerm("ZoneX", case_sensitive=True),
            GlossaryTerm("zonex", case_sensitive=True),
            GlossaryTerm("ZoneX", case_sensitive=True),
        ]
    )
    assert [term.text for term in case_terms] == ["ZoneX", "zonex"]

    alias_terms = dedupe_glossary_terms(
        [
            GlossaryTerm(
                "Caltheris",
                aliases=(" Cal Ferris ", "", "Cal Ferris", "Kalfirisk"),
            )
        ]
    )
    assert alias_terms[0].aliases == ("Cal Ferris", "Kalfirisk")
    assert phrase_prompt_terms(alias_terms) == ("Caltheris", "Cal Ferris", "Kalfirisk")
    assert phrase_prompt_terms(alias_terms, include_aliases=False) == ("Caltheris",)
    assert phrase_prompt_terms(alias_terms, max_terms=2) == ("Caltheris", "Cal Ferris")
    assert phrase_prompt_terms(alias_terms, max_terms=0) == ()

    resolved = resolve_context_hints(
        source_label=" YouTube clip ",
        source_url=" https://www.youtube.com/watch?v=aB3_dE-9xYz ",
        title="  Stream Highlights  ",
        user_terms=["Nyxara", " nyxara ", "Freckelston"],
    )
    assert resolved.source_label == "YouTube clip"
    assert resolved.source_url == "https://www.youtube.com/watch?v=aB3_dE-9xYz"
    assert [hint.label for hint in resolved.context_hints] == [
        "source_label",
        "source_url",
        "title",
    ]
    assert resolved.context_hints[1].source == HINT_SOURCE_SOURCE_URL
    assert resolved.context_hints[2].source == HINT_SOURCE_TITLE
    assert [term.text for term in resolved.glossary_terms] == ["Nyxara", "Freckelston"]
    assert resolved.warnings == ()


if __name__ == "__main__":
    run_self_test()
    print("Context glossary self-test passed.")
