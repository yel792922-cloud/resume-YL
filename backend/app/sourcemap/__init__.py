"""Source mapping / highlighting layer.

Given a page's positioned words and a piece of text (a metric's label, a value,
a search query), resolve the bounding box that covers it — so the UI can draw a
highlight and click-to-jump to the exact spot in the original report.
"""

from app.sourcemap.highlight import (
    bbox_from_cell,
    locate_snippet,
    locate_terms,
    union_bbox,
)

__all__ = ["bbox_from_cell", "locate_snippet", "locate_terms", "union_bbox"]
