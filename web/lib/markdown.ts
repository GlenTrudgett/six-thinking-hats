import type { Report } from "./types";

const list = (items: string[]) => (items.length ? items.map((i) => `- ${i}`).join("\n") : "_None._");

/** Plain-text export of a report, for the Copy and Download buttons. */
export function reportToMarkdown(r: Report): string {
  const parts = [
    "# Six Thinking Hats report",
    r.degraded ? `> Degraded run. Missing perspectives: ${r.missing_perspectives.join(", ") || "unknown"}.` : "",
    "## Framing\n" + r.framing_summary,
    "## What each hat said\n" + r.hat_summaries.map((h) => `- **${h.hat}**: ${h.summary}`).join("\n"),
    "## Conclusions\n" + list(r.conclusions),
    "## Agreements\n" + list(r.agreements),
    "## Tensions\n" + list(r.tensions),
    "## Recommended next steps\n" + list(r.recommended_next_steps),
    "## Open questions\n" + list(r.open_questions),
  ];
  return parts.filter(Boolean).join("\n\n") + "\n";
}
