from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from .models import RedditComment, RedditThread

AGE_PATTERNS = [
    re.compile(r"\b(?:i am|i'm|im)\s+(\d{1,2})\b", re.IGNORECASE),
    re.compile(r"\b(\d{1,2})\s*(?:years old|yo|y/o)\b", re.IGNORECASE),
    re.compile(r"\bage\s+(\d{1,2})\b", re.IGNORECASE),
]

QUOTE_RELEVANCE_PATTERN = re.compile(
    r"\b(floaters?|vitreous|pvd|posterior vitreous detachment|visual snow|flashes?|retinal|retina|atropine|vitrectomy|vitreolysis)\b",
    re.IGNORECASE,
)
FIRST_PERSON_PATTERN = re.compile(r"\b(i|i'm|i’ve|i've|me|my|mine)\b", re.IGNORECASE)
ADVICE_PATTERN = re.compile(
    r"\b(try|you should|focus on|what helps me|here is what helps|see your doctor|get checked|wishing you|stay strong|live your life)\b",
    re.IGNORECASE,
)
HELP_SEEKING_PATTERN = re.compile(
    r"\b(anyone|has anyone|need advice|looking for advice|found relief|what do you do|does it get better)\b|\?",
    re.IGNORECASE,
)

EMOTIONAL_CUES = {
    "suicidal": 6.0,
    "hopeless": 3.5,
    "isolated": 3.5,
    "alone": 3.0,
    "terrified": 3.0,
    "depressed": 3.0,
    "depression": 3.0,
    "anxiety": 2.5,
    "anxious": 2.5,
    "panic": 2.5,
    "embarrassed": 2.5,
    "ashamed": 2.5,
    "scared": 2.5,
    "suffering": 2.5,
    "struggling": 2.0,
    "ruining": 2.0,
    "exhausting": 2.0,
    "depressing": 2.0,
    "frustrating": 1.5,
    "can't enjoy": 3.0,
    "cannot enjoy": 3.0,
    "quality of life": 3.5,
    "can't live like this": 4.5,
    "cannot live like this": 4.5,
    "feel weird": 1.5,
    "feel less alone": 1.5,
}

SEVERITY_KEYWORDS = {
    "severe": 3,
    "debilitating": 3,
    "crippling": 3,
    "unbearable": 3,
    "constant": 2,
    "worse": 2,
    "terrible": 2,
    "awful": 2,
    "huge": 2,
    "mild": -1,
    "manageable": -1,
    "used to it": -1,
}

LIFESTYLE_PATTERNS = {
    "driving": re.compile(r"\bdrive|driving|car\b", re.IGNORECASE),
    "reading": re.compile(r"\bread|reading|book\b", re.IGNORECASE),
    "screen_time": re.compile(r"\bscreen|computer|monitor|phone|laptop\b", re.IGNORECASE),
    "outdoors": re.compile(r"\boutside|outdoors|sky|sunlight|bright\b", re.IGNORECASE),
    "work": re.compile(r"\bwork|job|office|career\b", re.IGNORECASE),
    "mental_health": re.compile(r"\banxious|anxiety|depressed|depression|suicidal|panic\b", re.IGNORECASE),
    "hobbies": re.compile(r"\bhobby|gaming|art|sports|exercise|run|reading\b", re.IGNORECASE),
    "sleep": re.compile(r"\bsleep|insomnia|night\b", re.IGNORECASE),
}

MEDICAL_TERMS = {
    "flashes": re.compile(r"\bflash|flashes\b", re.IGNORECASE),
    "pvd": re.compile(r"\bpvd|posterior vitreous detachment\b", re.IGNORECASE),
    "retinal_tear": re.compile(r"\bretinal tear|retina tear\b", re.IGNORECASE),
    "retinal_detachment": re.compile(r"\bretinal detachment\b", re.IGNORECASE),
    "vitrectomy": re.compile(r"\bvitrectomy\b", re.IGNORECASE),
    "yag": re.compile(r"\byag\b", re.IGNORECASE),
    "laser": re.compile(r"\blaser\b", re.IGNORECASE),
}


@dataclass(frozen=True)
class TextAnalysis:
    sentiment_compound: float
    sentiment_label: str
    age_mention: int | None
    severity_score: int
    severity_label: str
    emotional_score: float
    quote_category: str
    lifestyle_impacts: list[str]
    medical_flags: list[str]
    quote_score: float


def analyze_threads(threads: list[RedditThread], max_themes: int) -> dict[str, object]:
    analyzer = SentimentIntensityAnalyzer()

    post_rows: list[dict[str, object]] = []
    comment_rows: list[dict[str, object]] = []

    post_documents: list[str] = []
    post_ids: list[str] = []

    for thread in threads:
        post_text = " ".join(part for part in [thread.title, thread.selftext] if part).strip()
        post_analysis = analyze_text(post_text, analyzer, engagement=thread.score)
        post_rows.append(
            {
                "post_id": thread.id,
                "subreddit": thread.subreddit,
                "author": thread.author,
                "title": thread.title,
                "created_utc": thread.created_utc,
                "score": thread.score,
                "num_comments": thread.num_comments,
                "source": thread.source,
                "query": thread.query,
                "sentiment_compound": post_analysis.sentiment_compound,
                "sentiment_label": post_analysis.sentiment_label,
                "age_mention": post_analysis.age_mention,
                "severity_score": post_analysis.severity_score,
                "severity_label": post_analysis.severity_label,
                "emotional_score": post_analysis.emotional_score,
                "quote_category": post_analysis.quote_category,
                "lifestyle_impacts": "|".join(post_analysis.lifestyle_impacts),
                "medical_flags": "|".join(post_analysis.medical_flags),
                "quote_score": round(post_analysis.quote_score, 3),
                "permalink": thread.permalink,
                "text": post_text,
            }
        )
        post_documents.append(post_text)
        post_ids.append(thread.id)

        for comment in thread.comments:
            analysis = analyze_text(comment.body, analyzer, engagement=comment.score)
            comment_rows.append(
                {
                    "post_id": thread.id,
                    "comment_id": comment.id,
                    "author": comment.author,
                    "created_utc": comment.created_utc,
                    "score": comment.score,
                    "depth": comment.depth,
                    "sentiment_compound": analysis.sentiment_compound,
                    "sentiment_label": analysis.sentiment_label,
                    "age_mention": analysis.age_mention,
                    "severity_score": analysis.severity_score,
                    "severity_label": analysis.severity_label,
                    "emotional_score": analysis.emotional_score,
                    "quote_category": analysis.quote_category,
                    "lifestyle_impacts": "|".join(analysis.lifestyle_impacts),
                    "medical_flags": "|".join(analysis.medical_flags),
                    "quote_score": round(analysis.quote_score, 3),
                    "permalink": comment.permalink,
                    "body": comment.body,
                }
            )

    themes = build_themes(post_ids, post_documents, max_themes=max_themes)
    quotes = select_quotes(post_rows, comment_rows)
    summary = build_summary(post_rows, comment_rows, themes, quotes)

    return {
        "post_rows": post_rows,
        "comment_rows": comment_rows,
        "themes": themes,
        "quotes": quotes,
        "summary": summary,
    }


def analyze_text(text: str, analyzer: SentimentIntensityAnalyzer, engagement: int = 0) -> TextAnalysis:
    sentiment = analyzer.polarity_scores(text or "")
    compound = round(float(sentiment["compound"]), 4)
    if compound >= 0.35:
        sentiment_label = "positive"
    elif compound <= -0.35:
        sentiment_label = "negative"
    else:
        sentiment_label = "mixed"

    age_mention = extract_age(text)
    severity_score = extract_severity(text)
    severity_label = label_severity(severity_score)
    emotional_score = extract_emotional_score(text, compound)
    lifestyle_impacts = extract_lifestyle_impacts(text)
    medical_flags = extract_medical_flags(text)
    quote_category = classify_quote_category(
        text=text,
        compound=compound,
        emotional_score=emotional_score,
        medical_flags=medical_flags,
    )
    quote_score = score_quote_candidate(
        text=text,
        compound=compound,
        severity_score=severity_score,
        emotional_score=emotional_score,
        engagement=engagement,
        quote_category=quote_category,
    )
    return TextAnalysis(
        sentiment_compound=compound,
        sentiment_label=sentiment_label,
        age_mention=age_mention,
        severity_score=severity_score,
        severity_label=severity_label,
        emotional_score=emotional_score,
        quote_category=quote_category,
        lifestyle_impacts=lifestyle_impacts,
        medical_flags=medical_flags,
        quote_score=quote_score,
    )


def extract_age(text: str) -> int | None:
    for pattern in AGE_PATTERNS:
        match = pattern.search(text or "")
        if not match:
            continue
        age = int(match.group(1))
        if 10 <= age <= 99:
            return age
    return None


def extract_severity(text: str) -> int:
    normalized = (text or "").lower()
    score = 0
    for keyword, value in SEVERITY_KEYWORDS.items():
        if keyword in normalized:
            score += value
    if "can't" in normalized or "cannot" in normalized:
        score += 1
    if "suicidal" in normalized:
        score += 4
    return score


def label_severity(score: int) -> str:
    if score >= 6:
        return "extreme"
    if score >= 3:
        return "high"
    if score >= 1:
        return "moderate"
    return "low"


def extract_lifestyle_impacts(text: str) -> list[str]:
    return [label for label, pattern in LIFESTYLE_PATTERNS.items() if pattern.search(text or "")]


def extract_medical_flags(text: str) -> list[str]:
    return [label for label, pattern in MEDICAL_TERMS.items() if pattern.search(text or "")]


def extract_emotional_score(text: str, compound: float) -> float:
    normalized = (text or "").lower()
    score = 0.0
    for cue, weight in EMOTIONAL_CUES.items():
        if cue in normalized:
            score += weight

    if FIRST_PERSON_PATTERN.search(normalized):
        score += 1.0
    if "i feel" in normalized or "i've been feeling" in normalized:
        score += 1.5
    if "can't" in normalized or "cannot" in normalized:
        score += 0.8
    if compound <= -0.4:
        score += abs(compound) * 2.0
    return round(score, 4)


def classify_quote_category(
    text: str,
    compound: float,
    emotional_score: float,
    medical_flags: list[str],
) -> str:
    normalized = text or ""
    has_first_person = bool(FIRST_PERSON_PATTERN.search(normalized))
    has_advice = bool(ADVICE_PATTERN.search(normalized))
    is_help_seeking = bool(HELP_SEEKING_PATTERN.search(normalized))

    if has_first_person and emotional_score >= 4.0 and not has_advice:
        return "emotional_testimony"
    if has_advice:
        return "coping_advice"
    if len(medical_flags) >= 2:
        return "medical_experience"
    if is_help_seeking or compound < 0:
        return "help_seeking"
    return "general_experience"


def score_quote_candidate(
    text: str,
    compound: float,
    severity_score: int,
    emotional_score: float,
    engagement: int,
    quote_category: str,
) -> float:
    word_count = len((text or "").split())
    length_bonus = min(word_count / 80.0, 1.0)
    engagement_bonus = min(math.log1p(max(engagement, 0)), 1.0)
    advice_penalty = 2.5 if quote_category == "coping_advice" else 0.0
    category_bonus = {
        "emotional_testimony": 4.0,
        "help_seeking": 1.2,
        "medical_experience": 0.6,
        "general_experience": 0.0,
        "coping_advice": -1.0,
    }.get(quote_category, 0.0)
    return round(
        emotional_score * 1.6
        + abs(min(compound, 0.0)) * 2.5
        + max(severity_score, 0) * 0.7
        + length_bonus
        + engagement_bonus
        + category_bonus
        - advice_penalty,
        4,
    )


def build_themes(post_ids: list[str], documents: list[str], max_themes: int) -> list[dict[str, object]]:
    usable_docs = [doc for doc in documents if doc.strip()]
    if len(usable_docs) < 2:
        return []

    cluster_count = min(max_themes, len(usable_docs))
    if cluster_count < 2:
        return []

    vectorizer = TfidfVectorizer(stop_words="english", max_features=1000, ngram_range=(1, 2))
    matrix = vectorizer.fit_transform(documents)
    model = KMeans(n_clusters=cluster_count, random_state=42, n_init=10)
    labels = model.fit_predict(matrix)
    feature_names = vectorizer.get_feature_names_out()

    themes: list[dict[str, object]] = []
    for cluster_id in range(cluster_count):
        member_indexes = [idx for idx, label in enumerate(labels) if label == cluster_id]
        if not member_indexes:
            continue
        centroid = model.cluster_centers_[cluster_id]
        top_term_indexes = centroid.argsort()[-6:][::-1]
        top_terms = [str(feature_names[idx]) for idx in top_term_indexes]
        themes.append(
            {
                "theme_id": cluster_id,
                "top_terms": top_terms,
                "post_ids": [post_ids[idx] for idx in member_indexes],
                "size": len(member_indexes),
            }
        )
    return sorted(themes, key=lambda item: int(item["size"]), reverse=True)


def select_quotes(
    post_rows: list[dict[str, object]],
    comment_rows: list[dict[str, object]],
    max_quotes: int = 12,
) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []

    for row in post_rows:
        text = str(row["text"]).strip()
        if len(text.split()) < 10 or not QUOTE_RELEVANCE_PATTERN.search(text):
            continue
        candidates.append(
            {
                "kind": "post",
                "post_id": row["post_id"],
                "author": row["author"],
                "quote": text,
                "quote_score": row["quote_score"],
                "emotional_score": row["emotional_score"],
                "quote_category": row["quote_category"],
                "severity_label": row["severity_label"],
                "sentiment_label": row["sentiment_label"],
                "lifestyle_impacts": row["lifestyle_impacts"],
                "medical_flags": row["medical_flags"],
                "permalink": row["permalink"],
            }
        )

    for row in comment_rows:
        text = str(row["body"]).strip()
        if len(text.split()) < 10 or not QUOTE_RELEVANCE_PATTERN.search(text):
            continue
        candidates.append(
            {
                "kind": "comment",
                "post_id": row["post_id"],
                "comment_id": row["comment_id"],
                "author": row["author"],
                "quote": text,
                "quote_score": row["quote_score"],
                "emotional_score": row["emotional_score"],
                "quote_category": row["quote_category"],
                "severity_label": row["severity_label"],
                "sentiment_label": row["sentiment_label"],
                "lifestyle_impacts": row["lifestyle_impacts"],
                "medical_flags": row["medical_flags"],
                "permalink": row["permalink"],
            }
        )

    emotional = [item for item in candidates if item["quote_category"] == "emotional_testimony"]
    emotional_ranked = sorted(
        emotional,
        key=lambda item: (float(item["emotional_score"]), float(item["quote_score"])),
        reverse=True,
    )

    if len(emotional_ranked) >= max_quotes:
        return emotional_ranked[:max_quotes]

    remainder = [item for item in candidates if item["quote_category"] != "emotional_testimony"]
    remainder_ranked = sorted(remainder, key=lambda item: float(item["quote_score"]), reverse=True)
    return emotional_ranked + remainder_ranked[: max_quotes - len(emotional_ranked)]


def build_summary(
    post_rows: list[dict[str, object]],
    comment_rows: list[dict[str, object]],
    themes: list[dict[str, object]],
    quotes: list[dict[str, object]],
) -> dict[str, object]:
    severity_counts = Counter(str(row["severity_label"]) for row in post_rows + comment_rows)
    sentiment_counts = Counter(str(row["sentiment_label"]) for row in post_rows + comment_rows)
    lifestyle_counts = Counter()
    medical_flag_counts = Counter()
    quote_category_counts = Counter(str(row["quote_category"]) for row in post_rows + comment_rows)
    ages = []

    for row in post_rows + comment_rows:
        impacts = [item for item in str(row["lifestyle_impacts"]).split("|") if item]
        flags = [item for item in str(row["medical_flags"]).split("|") if item]
        lifestyle_counts.update(impacts)
        medical_flag_counts.update(flags)
        age_mention = row.get("age_mention")
        if isinstance(age_mention, int):
            ages.append(age_mention)

    return {
        "thread_count": len(post_rows),
        "comment_count": len(comment_rows),
        "severity_counts": dict(severity_counts),
        "sentiment_counts": dict(sentiment_counts),
        "top_lifestyle_impacts": lifestyle_counts.most_common(8),
        "top_medical_flags": medical_flag_counts.most_common(8),
        "quote_category_counts": dict(quote_category_counts),
        "age_mentions_count": len(ages),
        "average_age_mention": round(sum(ages) / len(ages), 2) if ages else None,
        "theme_count": len(themes),
        "quote_count": len(quotes),
    }
