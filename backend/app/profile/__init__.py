"""Report profile layer.

A lightweight description of a report's structure — business breadth, geographic
scope, industry style, and report type — used as a *hint* (never a hard rule) to
adapt extraction, cleaning, classification and display. A user may set it at
upload; otherwise it is auto-detected from the extracted facts.
"""
from app.profile.model import (
    BUSINESS_STRUCTURES,
    GEO_SCOPES,
    INDUSTRIES,
    ReportProfile,
    infer_profile,
    profile_from_json,
    profile_options,
)
from app.profile.policy import ReportPolicy, policy_for

__all__ = [
    "ReportProfile",
    "infer_profile",
    "profile_from_json",
    "profile_options",
    "BUSINESS_STRUCTURES",
    "GEO_SCOPES",
    "INDUSTRIES",
    "ReportPolicy",
    "policy_for",
]
