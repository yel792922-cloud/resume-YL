"""Scenario forecasting layer (v3).

Lightweight, heuristic, period-aware forecasting. For a single report it derives
the observed period-over-period trend of each key metric (from the current and
prior columns already captured in each fact's source snippet) and projects the
**next** period at the report's own cadence (quarter / half-year / year) under
three scenarios: base, bear, bull.

Forecasts are ephemeral (computed on demand, never persisted) and every one
cites the source facts it was built from — analytical estimates, not guarantees.
"""

from app.forecasting.service import forecast_document

__all__ = ["forecast_document"]
