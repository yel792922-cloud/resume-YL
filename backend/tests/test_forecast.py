"""Scenario forecasting: engine math, period cadence, API, ownership."""
from __future__ import annotations

import pytest

from app.forecasting.engine import (
    MetricInput,
    parse_prior_from_snippet,
    project_metric,
)
from app.forecasting.periods import cadence_label, next_period_label
from app.models.document import ReportType


def test_prior_parsed_from_row_snippet():
    prior = parse_prior_from_snippet("营业收入 Revenue | 6,096.9 | 5,626.5", 6096.9, False)
    assert prior == pytest.approx(5626.5)


def test_prior_absent_returns_none():
    assert parse_prior_from_snippet("Revenue was 6,096.9 this year", 6096.9, False) is None


def test_value_metric_scenarios_ordered():
    m = MetricInput("revenue", "Revenue", "营收", "亿元", 6096.9, 5626.5, is_percent=False, source_confidence=0.9)
    base, bull, bear = project_metric(m)
    assert bear.predicted_value < base.predicted_value < bull.predicted_value
    assert base.direction == "up" and base.confidence == "high"
    assert {s.scenario for s in (base, bull, bear)} == {"base", "bull", "bear"}


def test_margin_metric_is_additive_and_clamped():
    m = MetricInput("gross_margin", "Gross Margin", "毛利率", "%", 53.0, 51.5, is_percent=True, source_confidence=0.9)
    base, bull, bear = project_metric(m)
    assert base.predicted_value == pytest.approx(54.5)     # 53.0 + 1.5pp observed
    assert 0 <= bear.predicted_value <= 100 and 0 <= bull.predicted_value <= 100


def test_flat_when_no_prior():
    m = MetricInput("revenue", "Revenue", None, "亿元", 100.0, None, is_percent=False, source_confidence=0.9)
    base, _, _ = project_metric(m)
    assert base.predicted_value == pytest.approx(100.0)     # flat assumption
    assert base.confidence == "low"


def test_loss_making_base_is_flat_not_sign_flipped():
    # Current loss vs smaller prior loss: multiplicative growth would flip signs;
    # guard falls back to flat instead of projecting nonsense.
    m = MetricInput("operating_profit", "Operating Profit", None, "亿元", -100.0, -50.0, is_percent=False, source_confidence=0.9)
    base, bull, bear = project_metric(m)
    assert base.predicted_value == pytest.approx(-100.0)    # flat, not -200 etc.
    assert base.confidence == "low"


def test_growth_override_applied():
    m = MetricInput("revenue", "Revenue", None, "亿元", 100.0, 90.0, is_percent=False, source_confidence=0.9)
    base, _, _ = project_metric(m, growth_override_pct=20.0)
    assert base.predicted_value == pytest.approx(120.0)


def test_period_cadence_labels():
    assert cadence_label(ReportType.ANNUAL) == "year"
    assert cadence_label(ReportType.QUARTERLY) == "quarter"
    assert cadence_label(ReportType.INTERIM) == "half-year"
    assert next_period_label("2024 FY", ReportType.ANNUAL) == "2025 FY"
    assert next_period_label("2024 Q3", ReportType.QUARTERLY) == "2024 Q4"
    assert next_period_label("2024 Q4", ReportType.QUARTERLY) == "2025 Q1"
    assert next_period_label("2024 H1", ReportType.INTERIM) == "2024 H2"


def test_api_forecast_on_sample(client, seeded):
    did, headers = seeded
    fc = client.get(f"/api/documents/{did}/forecast", headers=headers).json()
    assert fc["report_type"] == "annual"
    assert fc["forecast_period"] == "2025 FY"
    assert fc["cadence"] == "year"
    assert fc["disclaimer"]
    concepts = {m["concept_id"] for m in fc["metrics"]}
    assert {"revenue", "net_profit", "gross_margin"} <= concepts
    revenue = next(m for m in fc["metrics"] if m["concept_id"] == "revenue")
    assert revenue["prior_value"] == pytest.approx(5626.5)   # from the row snippet
    assert len(revenue["scenarios"]) == 3
    assert revenue["source"]["page_number"]                  # source-referenced


def test_forecast_override_via_api(client, seeded):
    did, headers = seeded
    fc = client.get(
        f"/api/documents/{did}/forecast", headers=headers, params={"growth_override_pct": 10}
    ).json()
    revenue = next(m for m in fc["metrics"] if m["concept_id"] == "revenue")
    base = next(s for s in revenue["scenarios"] if s["scenario"] == "base")
    assert base["predicted_value"] == pytest.approx(6096.9 * 1.10, rel=1e-4)


def test_forecast_owner_scoped(client, seeded):
    from tests.conftest import register

    did, _ = seeded
    bob = register(client, "bob-fc@example.com")
    assert client.get(f"/api/documents/{did}/forecast", headers=bob["headers"]).status_code == 404


def test_forecast_override_out_of_bounds_rejected(client, seeded):
    # Extreme override is rejected (422) rather than producing inf / a 500.
    did, headers = seeded
    r = client.get(f"/api/documents/{did}/forecast", headers=headers, params={"growth_override_pct": 1e9})
    assert r.status_code == 422
