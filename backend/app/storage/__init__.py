"""Storage & retention layer.

Free-tier disk is small and unreliable, so raw PDFs are treated as a *cache*,
not a system of record. Retention keeps only the newest N originals per user;
all structured data (pages, facts, snapshots) is preserved regardless.
"""

from app.storage.retention import delete_raw_file, enforce_retention

__all__ = ["enforce_retention", "delete_raw_file"]
