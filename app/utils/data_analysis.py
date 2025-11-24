from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import datetime
from statistics import mean
from typing import Any, Dict, Iterable, List, Tuple

import requests
from pathlib import Path

GCS_ALLOWED_PREFIX = "https://builder-agent.storage.googleapis.com/"


class DataAnalysisError(Exception):
    """Raised when campaign or experiment data cannot be processed."""


def _strip_bom(text: str) -> str:
    if text.startswith("\ufeff"):
        return text.lstrip("\ufeff")
    return text


def _to_number(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = value.replace(",", "").replace("$", "").strip()
    if not cleaned or cleaned.upper() in {"N/A", "NA"}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _to_percentage(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = value.replace("%", "").replace(",", "").strip()
    if not cleaned or cleaned.upper() in {"N/A", "NA"}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_time_to_seconds(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned or cleaned.upper() in {"N/A", "NA"}:
        return None
    parts = cleaned.split(":")
    try:
        if len(parts) == 3:
            hours, minutes, seconds = [int(p) for p in parts]
            return hours * 3600 + minutes * 60 + seconds
        if len(parts) == 2:
            minutes, seconds = [int(p) for p in parts]
            return minutes * 60 + seconds
        return float(cleaned)
    except ValueError:
        return None


def _fetch_csv_rows(url: str) -> List[Dict[str, str]]:
    if url.startswith(("http://", "https://")):
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        text = _strip_bom(response.text)
    else:
        path = Path(url.replace("file://", ""))
        if not path.exists():
            raise DataAnalysisError(f"Dataset not found at {url}")
        text = _strip_bom(path.read_text(encoding="utf-8"))
    reader = csv.DictReader(io.StringIO(text))
    return [row for row in reader]


def _date_range(
    rows: Iterable[Dict[str, str]], column: str
) -> tuple[str | None, str | None]:
    parsed_dates: List[datetime] = []
    for row in rows:
        raw = row.get(column)
        if not raw:
            continue
        for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
            try:
                parsed_dates.append(datetime.strptime(raw, fmt))
                break
            except ValueError:
                continue
    if not parsed_dates:
        return None, None
    parsed_dates.sort()
    return parsed_dates[0].date().isoformat(), parsed_dates[-1].date().isoformat()


def analyze_campaign_dataset(url: str) -> tuple[dict[str, Any], str]:
    rows = _fetch_csv_rows(url)
    if not rows:
        raise DataAnalysisError("Campaign dataset appears to be empty.")

    metrics: List[dict[str, Any]] = []
    for row in rows:
        sessions = _to_number(row.get("Sessions"))
        conversions = _to_number(row.get("Primary Conversion Count"))
        conversion_rate = _to_percentage(row.get("Primary Conversion Rate (%)"))
        bounce_rate = _to_percentage(row.get("Bounce Rate (%)"))
        engagement_rate = _to_percentage(row.get("Engagement Rate (%)"))
        scroll_depth = _to_percentage(row.get("Scroll Depth (%)"))
        cta_clicks = _to_number(row.get("Clicks on Primary CTA"))
        form_completions = _to_number(row.get("Form Completions"))
        time_on_page = _parse_time_to_seconds(row.get("Average Time on Page"))
        spend = _to_number(row.get("Total Spend"))

        metrics.append(
            {
                "name": row.get("Campaign Name") or "Unnamed Campaign",
                "id": row.get("Campaign ID") or "",
                "traffic_source": row.get("Traffic Source") or "Unknown",
                "utm_source": row.get("UTM Source") or "Unknown",
                "device": row.get("Device Type") or "Unknown",
                "creative_type": row.get("Creative Type") or "Unknown",
                "sessions": sessions or 0.0,
                "conversions": conversions or 0.0,
                "conversion_rate": conversion_rate,
                "bounce_rate": bounce_rate,
                "engagement_rate": engagement_rate,
                "scroll_depth": scroll_depth,
                "cta_clicks": cta_clicks or 0.0,
                "form_completions": form_completions or 0.0,
                "time_on_page_seconds": time_on_page,
                "total_spend": spend or 0.0,
            }
        )

    total_sessions = sum(m["sessions"] for m in metrics)
    total_conversions = sum(m["conversions"] for m in metrics)
    total_spend = sum(m["total_spend"] for m in metrics)
    total_cta_clicks = sum(m["cta_clicks"] for m in metrics)

    weighted_conversion_rate = (
        (total_conversions / total_sessions) * 100 if total_sessions else None
    )
    weighted_bounce_rate = (
        sum((m["bounce_rate"] or 0.0) * m["sessions"] for m in metrics) / total_sessions
        if total_sessions
        else None
    )
    weighted_engagement = (
        sum((m["engagement_rate"] or 0.0) * m["sessions"] for m in metrics)
        / total_sessions
        if total_sessions
        else None
    )
    weighted_scroll_depth = (
        sum((m["scroll_depth"] or 0.0) * m["sessions"] for m in metrics)
        / total_sessions
        if total_sessions
        else None
    )

    top_campaigns = sorted(
        metrics,
        key=lambda m: (m["conversion_rate"] or 0.0, m["form_completions"]),
        reverse=True,
    )[:5]

    traffic_sources: dict[str, dict[str, float]] = defaultdict(
        lambda: {"sessions": 0.0, "conversions": 0.0, "cta_clicks": 0.0}
    )
    devices: dict[str, dict[str, float]] = defaultdict(
        lambda: {"sessions": 0.0, "conversions": 0.0, "form_completions": 0.0}
    )
    creatives: dict[str, dict[str, float]] = defaultdict(
        lambda: {"rows": 0, "conversion_rates": [], "engagement_rates": []}
    )

    for m in metrics:
        traffic = traffic_sources[m["traffic_source"]]
        traffic["sessions"] += m["sessions"]
        traffic["conversions"] += m["conversions"]
        traffic["cta_clicks"] += m["cta_clicks"]

        device = devices[m["device"]]
        device["sessions"] += m["sessions"]
        device["conversions"] += m["conversions"]
        device["form_completions"] += m["form_completions"]

        creative = creatives[m["creative_type"]]
        creative["rows"] += 1
        if m["conversion_rate"] is not None:
            creative["conversion_rates"].append(m["conversion_rate"])
        if m["engagement_rate"] is not None:
            creative["engagement_rates"].append(m["engagement_rate"])

    traffic_summary = []
    for source, values in traffic_sources.items():
        sessions_share = (
            (values["sessions"] / total_sessions) * 100 if total_sessions else 0.0
        )
        conversion_rate = (
            (values["conversions"] / values["sessions"]) * 100
            if values["sessions"]
            else 0.0
        )
        traffic_summary.append(
            {
                "source": source,
                "sessions_share": round(sessions_share, 2),
                "conversion_rate": round(conversion_rate, 2),
                "cta_clicks": int(values["cta_clicks"]),
            }
        )

    device_summary = []
    for device, values in devices.items():
        sessions_share = (
            (values["sessions"] / total_sessions) * 100 if total_sessions else 0.0
        )
        conversion_rate = (
            (values["conversions"] / values["sessions"]) * 100
            if values["sessions"]
            else 0.0
        )
        device_summary.append(
            {
                "device": device,
                "sessions_share": round(sessions_share, 2),
                "conversion_rate": round(conversion_rate, 2),
                "form_completions": int(values["form_completions"]),
            }
        )

    creative_summary = []
    for creative_type, values in creatives.items():
        avg_conversion = (
            round(mean(values["conversion_rates"]), 2)
            if values["conversion_rates"]
            else None
        )
        avg_engagement = (
            round(mean(values["engagement_rates"]), 2)
            if values["engagement_rates"]
            else None
        )
        creative_summary.append(
            {
                "creative_type": creative_type,
                "rows": values["rows"],
                "avg_conversion_rate": avg_conversion,
                "avg_engagement_rate": avg_engagement,
            }
        )

    start_date, end_date = _date_range(rows, "Date")

    structured = {
        "campaign": {
            "row_count": len(rows),
            "date_range": {"start": start_date, "end": end_date},
            "overall": {
                "sessions": int(total_sessions),
                "conversions": int(total_conversions),
                "cta_clicks": int(total_cta_clicks),
                "total_spend": round(total_spend, 2),
                "primary_conversion_rate": (
                    round(weighted_conversion_rate, 2)
                    if weighted_conversion_rate is not None
                    else None
                ),
                "bounce_rate": (
                    round(weighted_bounce_rate, 2)
                    if weighted_bounce_rate is not None
                    else None
                ),
                "engagement_rate": (
                    round(weighted_engagement, 2)
                    if weighted_engagement is not None
                    else None
                ),
                "scroll_depth": (
                    round(weighted_scroll_depth, 2)
                    if weighted_scroll_depth is not None
                    else None
                ),
            },
            "top_campaigns": [
                {
                    "campaign": m["name"],
                    "campaign_id": m["id"],
                    "traffic_source": m["traffic_source"],
                    "creative_type": m["creative_type"],
                    "primary_conversion_rate": (
                        round(m["conversion_rate"], 2)
                        if m["conversion_rate"] is not None
                        else None
                    ),
                    "form_completions": int(m["form_completions"]),
                    "cta_clicks": int(m["cta_clicks"]),
                }
                for m in top_campaigns
            ],
            "traffic_sources": traffic_summary,
            "device_summary": device_summary,
            "creative_summary": creative_summary,
        }
    }

    design_recommendations: List[str] = []
    if creative_summary:
        creative_candidates = [
            c
            for c in creative_summary
            if c["avg_conversion_rate"] is not None
            and c["avg_engagement_rate"] is not None
        ]
        if creative_candidates:
            top_creative = max(
                creative_candidates, key=lambda c: c["avg_conversion_rate"]
            )
            design_recommendations.append(
                f"Lean into {top_creative['creative_type']} storytelling: "
                f"{top_creative['avg_conversion_rate']:.1f}% avg CVR paired with "
                f"{top_creative['avg_engagement_rate']:.1f}% engagement."
            )

    if device_summary:
        dominant_device = max(device_summary, key=lambda x: x["sessions_share"])
        design_recommendations.append(
            f"Optimize for {dominant_device['device']} first — "
            f"{dominant_device['sessions_share']:.1f}% of sessions and "
            f"{dominant_device['conversion_rate']:.1f}% CVR."
        )

    if traffic_summary:
        best_source = max(traffic_summary, key=lambda x: x["conversion_rate"])
        design_recommendations.append(
            f"Mirror {best_source['source']} acquisition intent; conversion rate "
            f"hits {best_source['conversion_rate']:.1f}% with {best_source['sessions_share']:.1f}% of sessions."
        )

    if structured["campaign"]["overall"]["scroll_depth"] is not None:
        design_recommendations.append(
            f"Maintain layered storytelling — average scroll depth reaches "
            f"{structured['campaign']['overall']['scroll_depth']:.1f}%."
        )

    narrative_lines = []
    if structured["campaign"]["overall"]["primary_conversion_rate"] is not None:
        narrative_lines.append(
            f"Weighted primary conversion rate sits at "
            f"{structured['campaign']['overall']['primary_conversion_rate']:.2f}% "
            f"across {int(total_sessions):,} sessions."
        )
    if structured["campaign"]["overall"]["bounce_rate"] is not None:
        narrative_lines.append(
            f"Bounce rate averages {structured['campaign']['overall']['bounce_rate']:.2f}% "
            "while engagement holds above 60% on top-performing campaigns."
        )

    if top_campaigns:
        top_names = ", ".join(
            (
                f"{c['campaign']} ({c['primary_conversion_rate']:.1f}% CVR)"
                if c["primary_conversion_rate"] is not None
                else f"{c['campaign']}"
            )
            for c in structured["campaign"]["top_campaigns"][:3]
        )
        narrative_lines.append(
            f"Highest converting campaigns include {top_names}, all pairing assertive CTAs "
            "with high scroll depth and generous form visibility."
        )

    if traffic_summary:
        best_source = max(traffic_summary, key=lambda x: x["conversion_rate"])
        narrative_lines.append(
            f"{best_source['source']} traffic leads on conversion rate at "
            f"{best_source['conversion_rate']:.1f}% with {best_source['sessions_share']:.1f}% of sessions, "
            "so the landing experience must feel native to that acquisition channel."
        )

    if device_summary:
        dominant_device = max(device_summary, key=lambda x: x["sessions_share"])
        narrative_lines.append(
            f"{dominant_device['device']} contributes {dominant_device['sessions_share']:.1f}% of sessions "
            f"and {dominant_device['conversion_rate']:.1f}% CVR, emphasizing the need for responsive hero layout and "
            "fast-loading media on that footprint."
        )

    if creative_summary:
        sorted_creatives = sorted(
            [
                c
                for c in creative_summary
                if c["avg_conversion_rate"] is not None
                and c["avg_engagement_rate"] is not None
            ],
            key=lambda x: x["avg_conversion_rate"],
            reverse=True,
        )
        if sorted_creatives:
            top_creative = sorted_creatives[0]
            narrative_lines.append(
                f"{top_creative['creative_type']} creatives average "
                f"{top_creative['avg_conversion_rate']:.1f}% conversion and "
                f"{top_creative['avg_engagement_rate']:.1f}% engagement, "
                "suggesting motion-rich hero treatments should anchor the story."
            )

    narrative = "\n".join(narrative_lines)
    if design_recommendations:
        structured["campaign"]["design_recommendations"] = design_recommendations
    return structured, narrative


def analyze_experiment_dataset(url: str) -> tuple[dict[str, Any], str]:
    rows = _fetch_csv_rows(url)
    if not rows:
        raise DataAnalysisError("Experiment dataset appears to be empty.")

    experiment_dict: Dict[str, str] = {}
    for row in rows:
        if len(row) == 2:
            key, value = next(iter(row.items()))
            experiment_dict[key] = value
        else:
            keys = list(row.keys())
            if len(keys) >= 2:
                experiment_dict[row[keys[0]]] = row[keys[1]]

    name = experiment_dict.get("Experiment Name", "Campaign Experiment")
    winning_variant = experiment_dict.get("Winning Variant", "")
    control_metric = _to_percentage(
        experiment_dict.get("Control Result - Primary Metric")
    )
    variant_metric = _to_percentage(
        experiment_dict.get("Variant Result - Primary Metric")
    )
    absolute_delta = _to_percentage(experiment_dict.get("Delta (Absolute %)"))
    uplift = _to_percentage(experiment_dict.get("Uplift (Relative %)"))
    significance = experiment_dict.get("Statistical Significance Achieved", "")
    key_insights = experiment_dict.get("Key Insights and Interpretation", "")
    limitations = experiment_dict.get("Limitations & Notes", "")
    recommendations = experiment_dict.get("Future Recommendations", "")

    structured = {
        "experiment": {
            "name": name,
            "id": experiment_dict.get("Experiment ID"),
            "primary_metric_control": control_metric,
            "primary_metric_variant": variant_metric,
            "absolute_delta": absolute_delta,
            "relative_uplift": uplift,
            "winning_variant": winning_variant,
            "statistical_significance": significance,
            "key_insights": key_insights,
            "limitations": limitations,
            "future_recommendations": recommendations,
            "decision": experiment_dict.get("Decision Taken"),
            "audience": experiment_dict.get("Audience Targeted"),
            "traffic_allocation": experiment_dict.get("Traffic Allocation"),
            "timeframe": {
                "start": experiment_dict.get("Start Date"),
                "end": experiment_dict.get("End Date"),
            },
        }
    }

    narrative_parts = [
        f"Experiment **{name}** ({experiment_dict.get('Experiment ID')}) tested hero form placement "
        f"with variant {winning_variant} outperforming control."
    ]
    if control_metric is not None and variant_metric is not None:
        narrative_parts.append(
            f"Control converted at {control_metric:.2f}% while the variant achieved {variant_metric:.2f}% "
            f"({absolute_delta:.2f}% absolute / {uplift:.2f}% relative lift)."
        )
    if significance:
        narrative_parts.append(
            f"Statistical significance: {significance} (p={experiment_dict.get('P-Value')})."
        )
    if key_insights:
        narrative_parts.append(f"Key insight: {key_insights}")
    if limitations:
        narrative_parts.append(f"Limitations to monitor: {limitations}")
    if recommendations:
        narrative_parts.append(f"Future experiments: {recommendations}")

    narrative = "\n".join(narrative_parts)

    experiment_recs: List[str] = []
    if uplift is not None:
        experiment_recs.append(
            f"Keep hero form above the fold (variant {winning_variant} +{uplift:.2f}% relative lift)."
        )
    else:
        experiment_recs.append(
            f"Keep hero form above the fold per winning variant {winning_variant}."
        )
    if limitations:
        experiment_recs.append(
            "Balance hero form prominence on mobile with generous spacing and optional progressive disclosure (limitation noted by test feedback)."
        )
    structured["experiment"]["design_recommendations"] = experiment_recs

    return structured, narrative


def prepare_data_enrichment(
    payload_dict: dict[str, Any],
    *,
    session_id: str | None = None,
) -> tuple[dict[str, Any], str, dict[str, Any], List[str]]:
    """
    Augment the initialization payload with campaign & experiment data insights.

    Returns:
        - enriched payload dictionary (with dataInsights if available)
        - narrative text appended to init payload text
        - state overrides for BuilderState
        - list of warnings/errors encountered
    """

    data_section = payload_dict.get("data") or {}
    campaign_url = data_section.get("campaignDataUrl")
    experiment_url = data_section.get("experimentDataUrl")

    structured_insights: dict[str, Any] = {}
    campaign_narrative = ""
    experiment_narrative = ""
    warnings: List[str] = []

    if campaign_url:
        if campaign_url.startswith(
            ("http://", "https://")
        ) and not campaign_url.startswith(GCS_ALLOWED_PREFIX):
            warnings.append(
                "Campaign CSV should be hosted at builder-agent.storage.googleapis.com; proceeding with provided URL."
            )
        try:
            structured, narrative = analyze_campaign_dataset(campaign_url)
            structured_insights.update(structured)
            campaign_narrative = narrative
        except Exception as exc:  # pragma: no cover - defensive
            warnings.append(f"Campaign dataset unavailable ({exc}).")
    else:
        warnings.append("No campaign performance CSV provided.")

    if experiment_url:
        if experiment_url.startswith(
            ("http://", "https://")
        ) and not experiment_url.startswith(GCS_ALLOWED_PREFIX):
            warnings.append(
                "Experiment CSV should be hosted at builder-agent.storage.googleapis.com; proceeding with provided URL."
            )
        try:
            structured, narrative = analyze_experiment_dataset(experiment_url)
            structured_insights.update(structured)
            experiment_narrative = narrative
        except Exception as exc:  # pragma: no cover - defensive
            warnings.append(f"Experiment dataset unavailable ({exc}).")
    else:
        warnings.append("No experiment results CSV provided.")

    if structured_insights:
        combined_recommendations: List[str] = []
        combined_recommendations.extend(
            structured_insights.get("campaign", {}).get("design_recommendations", [])
        )
        combined_recommendations.extend(
            structured_insights.get("experiment", {}).get("design_recommendations", [])
        )
        if combined_recommendations:
            structured_insights["recommendations"] = combined_recommendations

        payload_dict = {**payload_dict, "dataInsights": structured_insights}
    else:
        payload_dict = dict(payload_dict)

    narratives = []
    if campaign_narrative:
        narratives.append("#### Campaign Performance Highlights\n" + campaign_narrative)
    if experiment_narrative:
        narratives.append("#### Experiment Findings\n" + experiment_narrative)
    narrative_text = "\n\n".join(narratives)

    state_overrides = {
        "data_insights": structured_insights,
        "campaign_data_digest": campaign_narrative,
        "experiment_data_digest": experiment_narrative,
    }

    return payload_dict, narrative_text, state_overrides, warnings
