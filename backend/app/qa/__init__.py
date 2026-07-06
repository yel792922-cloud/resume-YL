"""Evidence-based single-report Q&A (v4).

Answers questions about one financial report using **only** the report's own
extracted/cleaned facts and source snippets — grounded, cited, and conservative
when the evidence is weak. No LLM and no general-knowledge answers: every
sentence maps to a retrieved fact/snippet with a jump-back source reference.

Flow:  question → intent (classify) → retrieval (rank evidence) → compose answer.
Reuses the existing search, cleaning, normalization and forecasting primitives.
Ephemeral — nothing is persisted.
"""

from app.qa.service import answer_question

__all__ = ["answer_question"]
