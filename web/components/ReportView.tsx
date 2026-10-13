import { HatChip } from "@/components/HatIcon";
import { formatMoney } from "@/lib/money";
import type { Hat, Report } from "@/lib/types";

function List({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <>
      <h2>{title}</h2>
      <ul className="plain">
        {items.map((i, n) => (
          <li key={n}>{i}</li>
        ))}
      </ul>
    </>
  );
}

export function ReportView({ report }: { report: Report }) {
  const t = report.token_usage;
  return (
    <article className="card" aria-label="Report">
      {report.degraded && (
        <div className="warn" role="status">
          <strong>Degraded run.</strong> Missing: {report.missing_perspectives.join(", ") || "unknown"}.
          {report.failures.map((f, n) => (
            <div key={n} className="hint">
              {f.node}
              {f.hat ? ` / ${f.hat}` : ""}: {f.error_type}
              {f.message ? ` (${f.message})` : ""}
            </div>
          ))}
        </div>
      )}
      <div className="chips" aria-label="Hat order">
        <HatChip hat="blue" label="Blue" />
        {(report.mode === "sequential" ? report.sequence : ["white", "red", "green", "yellow", "black"]).map(
          (h, n) => (
            <HatChip key={n} hat={h as Hat} />
          ),
        )}
        <HatChip hat="blue" label="Blue" />
        <span className="hint">{report.mode}{report.preset ? ` · ${report.preset}` : ""}</span>
      </div>
      <h2>Framing</h2>
      <p>{report.framing_summary}</p>
      <h2>What each hat said</h2>
      {report.hat_summaries.map((h, n) => (
        <div key={n} className={`hatcard ${h.hat}`}>
          <strong>{h.hat}</strong>: {h.summary}
        </div>
      ))}
      <List title="Conclusions" items={report.conclusions} />
      <List title="Agreements" items={report.agreements} />
      <List title="Tensions" items={report.tensions} />
      <List title="Recommended next steps" items={report.recommended_next_steps} />
      <List title="Open questions" items={report.open_questions} />
      <p className="meta">
        {report.models_used.join(", ") || "model n/a"} · {t.input_tokens ?? 0} in / {t.output_tokens ?? 0} out
        tokens
        {report.elapsed_seconds != null ? ` · ${report.elapsed_seconds}s` : ""}
        {report.estimated_cost != null && report.cost_currency
          ? ` · est. cost ${formatMoney(report.estimated_cost, report.cost_currency)}`
          : ""}
      </p>
    </article>
  );
}
