"""Report-period-aware horizons, negative growth, configurable factors, and the
Custom scenario + impact summary."""
from __future__ import annotations

from app.forecasting.factors import (
    contributions,
    external_growth_adjustment_pp,
    factor_catalog,
    normalize_weights,
)
from app.forecasting.periods import next_period_label
from app.models.document import ReportType


# ---------------------------- period-aware horizon ----------------------------

def test_horizon_follows_report_type():
    assert next_period_label("2024 Q2", ReportType.QUARTERLY) == "2024 Q3"
    assert next_period_label("2024 H1", ReportType.INTERIM) == "2024 H2"
    assert next_period_label("2024 FY", ReportType.ANNUAL) == "2025 FY"


# ---------------------------- factor model ----------------------------

def test_factor_catalog_has_expected_drivers():
    ids = {f.id for f in factor_catalog()}
    for wanted in ("market_expansion", "macro", "interest_rates", "exchange_rate",
                   "regulatory", "competition", "sentiment", "input_cost",
                   "supply_chain", "consumer_demand"):
        assert wanted in ids


def test_weights_clamped_and_zeros_dropped():
    w = normalize_weights({"macro": 5, "competition": -9, "sentiment": 0, "bogus": 2})
    assert w == {"macro": 2, "competition": -2}   # clamped to ±2, zero + unknown dropped


def test_external_adjustment_and_contributions_sign():
    w = normalize_weights({"consumer_demand": 2, "regulatory": -1})
    adj = external_growth_adjustment_pp(w)
    assert adj > 0   # +2 demand outweighs -1 regulatory
    contribs = contributions(w)
    # Largest absolute impact first, signs preserved.
    assert contribs[0].id == "consumer_demand" and contribs[0].contribution_pp > 0
    assert any(c.id == "regulatory" and c.contribution_pp < 0 for c in contribs)


# ---------------------------- API: negative growth ----------------------------

def test_negative_growth_override_supported(client, seeded):
    did, headers = seeded
    r = client.post(f"/api/documents/{did}/forecast/custom", headers=headers,
                    json={"growth_override_pct": -30})
    assert r.status_code == 200, r.text
    body = r.json()
    rev = next(m for m in body["metrics"] if m["concept_id"] == "revenue")
    custom = next(s for s in rev["scenarios"] if s["scenario"] == "custom")
    assert custom["growth_pct"] < 0           # negative growth honored
    assert custom["predicted_value"] < rev["current_value"]


# ---------------------------- API: custom scenario + impact -------------------

def test_custom_scenario_and_impact_summary(client, seeded):
    did, headers = seeded
    r = client.post(f"/api/documents/{did}/forecast/custom", headers=headers, json={
        "growth_override_pct": 10,
        "factor_weights": {"consumer_demand": 2, "regulatory": -1, "unknown": 3},
        "notes": "bullish on demand",
    })
    assert r.status_code == 200, r.text
    body = r.json()

    # Custom scenario present alongside base/bull/bear.
    rev = next(m for m in body["metrics"] if m["concept_id"] == "revenue")
    names = {s["scenario"] for s in rev["scenarios"]}
    assert {"base", "bull", "bear", "custom"} <= names

    # Weights echoed & sanitized (unknown dropped, kept ones clamped).
    assert body["factor_weights"] == {"consumer_demand": 2, "regulatory": -1}
    assert body["factors"]                      # catalog present for the UI

    # Impact summary explains the drivers.
    imp = body["impact_summary"]
    assert imp["headline"]
    assert imp["internal_drivers"]              # ranked report metrics
    assert imp["external_drivers"]              # weighted factors
    assert imp["notes"] == "bullish on demand"
    # Custom growth = base override (+10) + external factors (+2*1.2 -1*1.2 = +1.2) = +11.2
    custom = next(s for s in rev["scenarios"] if s["scenario"] == "custom")
    assert abs(custom["growth_pct"] - 11.2) < 0.01


def test_plain_forecast_has_no_custom_scenario(client, seeded):
    did, headers = seeded
    body = client.get(f"/api/documents/{did}/forecast", headers=headers).json()
    rev = next(m for m in body["metrics"] if m["concept_id"] == "revenue")
    assert "custom" not in {s["scenario"] for s in rev["scenarios"]}
    assert body["annualized"] is False or body["annualized_note"]  # annualized is optional-view


def test_custom_forecast_owner_scoped(client, seeded):
    from tests.conftest import register
    did, _ = seeded
    bob = register(client, "bob-forecast@example.com")
    r = client.post(f"/api/documents/{did}/forecast/custom", headers=bob["headers"], json={})
    assert r.status_code == 404
