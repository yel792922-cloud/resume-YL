"""Data-cleaning layer (v3).

A **read-time, non-destructive** pass over already-extracted facts. It removes
low-value noise, de-duplicates, and normalizes units/labels while preserving
full source traceability for every retained fact and keeping an audit trail of
everything it changed or dropped.

Nothing here mutates the database or the extraction pipeline — cleaning is
computed on demand, so existing endpoints and stored data are unaffected. The
cleaned view is exposed via the API and reused as the input to forecasting.
"""

from app.cleaning.pipeline import CleanResult, clean_facts
from app.cleaning.rules import CleaningConfig, active_rule_ids

__all__ = ["clean_facts", "CleanResult", "CleaningConfig", "active_rule_ids"]
