import type { PageOut } from "../types";

const PAGE_WIDTH = 560; // px; height derived from the page aspect ratio

/**
 * Render a parsed page as positioned words with an optional highlight box.
 * Coordinates are normalized 0..1, so this faithfully reproduces the original
 * layout (and the highlight location) without needing a PDF renderer.
 */
export function PagePreview({ page, highlight }: { page: PageOut; highlight?: number[] | null }) {
  const aspect = page.height && page.width ? page.height / page.width : 1.414;
  const W = PAGE_WIDTH;
  const H = W * aspect;

  return (
    <div className="page-preview" style={{ width: W, height: H }}>
      {page.words.map((w, i) => {
        const fontPx = Math.max(6, (w.bottom - w.top) * H * 0.86);
        return (
          <span
            key={i}
            className="page-word"
            style={{
              left: w.x0 * W,
              top: w.top * H,
              fontSize: `${fontPx}px`,
            }}
          >
            {w.text}
          </span>
        );
      })}
      {highlight && highlight.length === 4 && (
        <div
          className="page-highlight"
          style={{
            left: highlight[0] * W,
            top: highlight[1] * H,
            width: (highlight[2] - highlight[0]) * W,
            height: (highlight[3] - highlight[1]) * H,
          }}
        />
      )}
      {page.words.length === 0 && (
        <div className="center" style={{ position: "absolute", inset: 0 }}>
          <span className="muted">扫描页 · scanned page (OCR unavailable)</span>
        </div>
      )}
    </div>
  );
}
