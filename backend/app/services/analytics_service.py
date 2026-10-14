"""Exact descriptive analytics used by the dashboard and RAG assistant."""

from typing import Any, Mapping


ANALYSIS_FEATURES = [
    "contract_type",
    "internet_service",
    "payment_method",
    "online_security",
    "tech_support",
    "tenure",
]
FEATURE_LABELS = {
    "contract_type": "contract type",
    "internet_service": "internet service",
    "payment_method": "payment method",
    "online_security": "online security",
    "tech_support": "tech support",
    "tenure": "tenure band",
}
TENURE_LABELS = ["0-12 months", "13-24 months", "25-48 months", "49+ months"]
MIN_SEGMENT_SIZE = 30


def summarize_labeled_customers(dataset) -> dict[str, Any]:
    """Calculate counts and segment rates using only rows with known outcomes."""
    total_customers = int(len(dataset))
    if total_customers == 0:
        return {
            "total_customers": 0,
            "churn_count": 0,
            "retained_count": 0,
            "churn_rate": 0.0,
            "segments": [],
            "known_actual_outcomes": 0,
            "unlabeled_customers": 0,
        }
    churn_count = int(dataset["churn_label"].sum())
    retained_count = total_customers - churn_count
    segments: list[dict[str, Any]] = []

    for feature in ANALYSIS_FEATURES:
        if feature == "tenure":
            values = dataset["tenure"].map(
                lambda tenure: (
                    TENURE_LABELS[0]
                    if tenure <= 12
                    else TENURE_LABELS[1]
                    if tenure <= 24
                    else TENURE_LABELS[2]
                    if tenure <= 48
                    else TENURE_LABELS[3]
                )
            )
        else:
            values = dataset[feature]

        groups = dataset.assign(_segment=values).groupby(
            "_segment", observed=True, sort=False
        )
        for category, group in groups:
            customers = int(len(group))
            if customers < MIN_SEGMENT_SIZE:
                continue
            churned = int(group["churn_label"].sum())
            segments.append(
                {
                    "feature": FEATURE_LABELS[feature],
                    "category": str(category),
                    "customers": customers,
                    "churned": churned,
                    "churn_rate": churned / customers,
                }
            )

    segments.sort(key=lambda item: item["churn_rate"], reverse=True)
    return {
        "total_customers": total_customers,
        "churn_count": churn_count,
        "retained_count": retained_count,
        "churn_rate": churn_count / total_customers if total_customers else 0.0,
        "segments": segments,
        "known_actual_outcomes": total_customers,
        "unlabeled_customers": 0,
    }


def format_dataset_evidence(summary: Mapping[str, Any]) -> str:
    """Format live database outcomes and exact segment statistics for RAG."""
    top_segments = summary["segments"][:12]
    segment_lines = [
        (
            f"- {segment['feature']} = {segment['category']}: "
            f"{segment['churned']} churned of {segment['customers']} customers "
            f"({segment['churn_rate']:.1%} churn rate)"
        )
        for segment in top_segments
    ]
    return "\n".join(
        [
            "Exact calculations from the current PostgreSQL customer database:",
            (
                f"- Customer profiles: {summary['total_customers']}; "
                f"known actual outcomes: {summary['known_actual_outcomes']}; "
                f"outcomes not yet known: {summary['unlabeled_customers']}."
            ),
            (
                f"- Churned: {summary['churn_count']}; "
                f"retained: {summary['retained_count']}; "
                f"churn rate among known outcomes: {summary['churn_rate']:.1%}."
            ),
            "- Highest observed segment churn rates, calculated only from records with known actual outcomes (segments have at least 30 known outcomes):",
            *segment_lines,
            (
                "Segment differences are observational associations, not proof "
                "that a feature caused churn. Recommendations must be framed "
                "as hypotheses to test, not established causal effects."
            ),
        ]
    )
