from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from reddit_scrapping.analyze import (
    analyze_text,
    build_themes,
    classify_quote_category,
    extract_age,
    extract_emotional_score,
    extract_lifestyle_impacts,
    extract_medical_flags,
    label_severity,
    score_quote_candidate,
)
from reddit_scrapping.collect import _is_relevant_post


def test_extract_age_detects_common_patterns() -> None:
    assert extract_age("I'm 29 and these floaters are ruining my mornings.") == 29
    assert extract_age("36 years old, sudden flashes and floaters this week.") == 36
    assert extract_age("No age mentioned here.") is None


def test_analysis_extracts_impacts_and_flags() -> None:
    analyzer = SentimentIntensityAnalyzer()
    result = analyze_text(
        "I can't drive comfortably anymore. Bright skies make the floaters unbearable and my anxiety is awful.",
        analyzer,
        engagement=5,
    )
    assert result.severity_label in {"high", "extreme"}
    assert "driving" in result.lifestyle_impacts
    assert "outdoors" in result.lifestyle_impacts
    assert "mental_health" in result.lifestyle_impacts


def test_medical_flags() -> None:
    flags = extract_medical_flags("My ophthalmologist said it might be PVD with flashes, not a retinal detachment.")
    assert "pvd" in flags
    assert "flashes" in flags
    assert "retinal_detachment" in flags


def test_label_severity() -> None:
    assert label_severity(0) == "low"
    assert label_severity(2) == "moderate"
    assert label_severity(4) == "high"
    assert label_severity(7) == "extreme"


def test_build_themes_returns_clusters() -> None:
    themes = build_themes(
        ["a", "b", "c"],
        [
            "large dark floaters in bright sky",
            "reading at work is hard because of floaters",
            "doctor mentioned vitrectomy and posterior vitreous detachment",
        ],
        max_themes=3,
    )
    assert len(themes) >= 2


def test_lifestyle_impacts() -> None:
    impacts = extract_lifestyle_impacts("Reading on my computer at work is harder now.")
    assert "reading" in impacts
    assert "screen_time" in impacts
    assert "work" in impacts


def test_relevance_filter_rejects_generic_mentions() -> None:
    generic_post = {
        "subreddit": "Anxiety",
        "title": "Huge list of anxiety symptoms to hopefully put you at ease",
        "selftext": "Dizziness can include tunnel vision, blurry vision, and floaters.",
    }
    focused_post = {
        "subreddit": "AskDocs",
        "title": "Sudden floaters and flashes in my left eye",
        "selftext": "I am 34 and my vision changed this week. My ophthalmologist mentioned possible PVD.",
    }
    assert _is_relevant_post(generic_post, search_query="floaters vision changes") is False
    assert _is_relevant_post(focused_post, search_query="floaters vision changes") is True


def test_emotional_testimony_outranks_advice() -> None:
    emotional_text = (
        "I feel so isolated and alone. My eye floaters are ruining my life and I don't know how much longer I can live like this."
    )
    advice_text = (
        "What helps me is to focus on what matters, wear sunglasses outside, and ask your doctor about atropine drops."
    )
    emotional_score = extract_emotional_score(emotional_text, compound=-0.8)
    advice_score = extract_emotional_score(advice_text, compound=0.2)
    emotional_category = classify_quote_category(emotional_text, compound=-0.8, emotional_score=emotional_score, medical_flags=[])
    advice_category = classify_quote_category(advice_text, compound=0.2, emotional_score=advice_score, medical_flags=[])

    ranked_emotional = score_quote_candidate(
        text=emotional_text,
        compound=-0.8,
        severity_score=4,
        emotional_score=emotional_score,
        engagement=1,
        quote_category=emotional_category,
    )
    ranked_advice = score_quote_candidate(
        text=advice_text,
        compound=0.2,
        severity_score=1,
        emotional_score=advice_score,
        engagement=5,
        quote_category=advice_category,
    )

    assert emotional_category == "emotional_testimony"
    assert advice_category == "coping_advice"
    assert ranked_emotional > ranked_advice
