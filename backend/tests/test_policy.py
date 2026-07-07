"""Report policy — deriving an active analysis policy from the profile and
verifying it actually changes cleaning, classification and forecasting."""
from __future__ import annotations

from app.profile import ReportProfile, policy_for


def _profile(**kw):
    base = dict(business_structure="single", geo_scope="single_region",
                industry="auto", complexity="simple")
    base.update(kw)
    return ReportProfile(**base)


# ---------------------------- derivation ----------------------------

def test_simple_profile_is_aggressive_and_strict():
    p = policy_for(_profile())
    assert p.merge_aggressiveness == "aggressive"
    assert p.scope_preservation == "low"
    assert p.cleaning_strictness == "strict"
    assert p.conservative_classification is False
    cfg = p.cleaning_config()
    assert cfg.merge_strength == "standard"
    assert cfg.min_informative_word_chars == 8         # trims more


def test_complex_profile_is_conservative_and_lenient():
    p = policy_for(_profile(business_structure="conglomerate", complexity="complex"))
    assert p.merge_aggressiveness == "conservative"
    assert p.scope_preservation == "high"
    assert p.cleaning_strictness == "lenient"
    assert p.conservative_classification is True
    cfg = p.cleaning_config()
    assert cfg.merge_strength == "preserve"
    assert cfg.min_informative_word_chars == 5         # keeps more context


def test_industry_shapes_families_and_driver_weights():
    bank = policy_for(_profile(industry="bank"))
    assert "regulatory" in bank.preferred_metric_families
    assert "interest_rates" in bank.forecast_driver_weights

    internet = policy_for(_profile(industry="internet", business_structure="multi", complexity="complex"))
    assert "segment_total" in internet.preferred_metric_families
    assert "user" in internet.preferred_metric_families
    assert internet.forecast_driver_weights   # non-empty suggestions

    hotel = policy_for(_profile(industry="hospitality"))
    assert "occupancy" in hotel.preferred_metric_families


def test_none_profile_defaults_to_simple_policy():
    p = policy_for(None)
    assert p.merge_aggressiveness == "aggressive"
    assert p.notes


# ---------------------------- end-to-end via API ----------------------------

def test_forecast_exposes_policy_emphasis(client, seeded):
    did, headers = seeded
    body = client.get(f"/api/documents/{did}/forecast", headers=headers).json()
    emph = body["policy_emphasis"]
    assert emph is not None
    # Sample is multi-business internet → segment/user families emphasized.
    assert emph["preferred_metric_families"]
    assert "segment_total" in emph["preferred_metric_families"]


def test_document_exposes_active_policy(client, seeded):
    did, headers = seeded
    doc = client.get(f"/api/documents/{did}", headers=headers).json()
    pol = doc["profile"]["policy"]
    assert pol is not None
    # Sample is complex → conservative / scope-preserving.
    assert pol["merge_aggressiveness"] == "conservative"
    assert pol["scope_preservation"] == "high"
    assert pol["notes"]


def test_cleaned_view_uses_policy_rules(client, seeded):
    did, headers = seeded
    res = client.get(f"/api/documents/{did}/cleaned", headers=headers).json()
    assert res["stats"]["retained"] > 10
    assert "dedup" in res["rules"]
