"use client";

import { useEffect, useRef, useState } from "react";
import { HatChip, HatIcon } from "@/components/HatIcon";
import { ReportView } from "@/components/ReportView";
import { reportToMarkdown } from "@/lib/markdown";
import { streamRun } from "@/lib/stream";
import type { Hat, PresetInfo, ProgressEvent, Report } from "@/lib/types";

const MAX_QUESTION = 8000;
type Choice = "auto" | "parallel" | "preset" | "custom";

export default function Home() {
  const [question, setQuestion] = useState("");
  const [choice, setChoice] = useState<Choice>("auto");
  const [presets, setPresets] = useState<PresetInfo[]>([]);
  const [hats, setHats] = useState<Hat[]>(["white", "red", "green", "yellow", "black"]);
  const [presetId, setPresetId] = useState("");
  const [custom, setCustom] = useState<Hat[]>([]);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<(ProgressEvent & { at: number })[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abort = useRef<AbortController | null>(null);

  useEffect(() => {
    fetch("/api/presets")
      .then((r) => r.json())
      .then((d: { hats: Hat[]; presets: PresetInfo[] }) => {
        setHats(d.hats);
        setPresets(d.presets);
        setPresetId(d.presets[0]?.id ?? "");
      })
      .catch(() => setError("Cannot reach the API. Is `sixhats serve` running?"));
  }, []);

  const preset = presets.find((p) => p.id === presetId);
  const canRun =
    !busy && question.trim().length > 0 && question.length <= MAX_QUESTION &&
    (choice !== "custom" || custom.length > 0) && (choice !== "preset" || !!preset);

  async function run() {
    setBusy(true); setError(null); setReport(null); setProgress([]);
    const started = performance.now();
    abort.current = new AbortController();
    try {
      const events = streamRun(
        {
          question,
          mode: choice === "parallel" ? "parallel" : "auto",
          preset: choice === "preset" ? presetId : null,
          sequence: choice === "custom" ? custom : null,
        },
        abort.current.signal,
      );
      for await (const ev of events) {
        if (ev.event === "progress") {
          setProgress((p) => [...p, { ...ev.data, at: (performance.now() - started) / 1000 }]);
        } else if (ev.event === "report") setReport(ev.data);
        else if (ev.event === "error") setError(`${ev.data.kind}: ${ev.data.message}`);
      }
    } catch (e) {
      if ((e as Error).name !== "AbortError") setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function download() {
    if (!report) return;
    const url = URL.createObjectURL(new Blob([reportToMarkdown(report)], { type: "text/markdown" }));
    const a = Object.assign(document.createElement("a"), { href: url, download: `sixhats-${report.run_id}.md` });
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <>
    <main>
      <header>
        <p className="eyebrow">After Edward de Bono</p>
        <h1>Six Thinking Hats</h1>
        <div className="hatrow" aria-hidden="true">
          {(["blue", "white", "green", "red", "black", "yellow"] as const).map((h) => <HatIcon key={h} hat={h} size={34} />)}
        </div>
        <p className="sub">Put a question or idea in. Blue frames it, the coloured hats think, Blue sums up.</p>
      </header>

      <section className="card">
        <label htmlFor="q">Your question</label>
        <textarea id="q" value={question} maxLength={MAX_QUESTION} onChange={(e) => setQuestion(e.target.value)}
          placeholder="Should we adopt a four-day work week?" />
        <div className="hint">{question.length} / {MAX_QUESTION}</div>

        <label htmlFor="how">How should the hats work?</label>
        <select id="how" value={choice} onChange={(e) => setChoice(e.target.value as Choice)}>
          <option value="auto">Let Blue decide</option>
          <option value="parallel">All five hats at once</option>
          <option value="preset">A preset order</option>
          <option value="custom">My own order</option>
        </select>

        {choice === "preset" && (
          <>
            <select aria-label="Preset" value={presetId} onChange={(e) => setPresetId(e.target.value)}>
              {presets.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
            </select>
            {preset && (
              <p className="hint">
                {preset.use_when}
                <span className="chips">
                  {preset.sequence.map((h, n) => <HatChip key={n} hat={h} />)}
                </span>
                Source: {preset.source} (a secondary source, not the book text).
              </p>
            )}
          </>
        )}

        {choice === "custom" && (
          <>
            <div className="row" role="group" aria-label="Add a hat">
              {hats.map((h) => (
                <button key={h} className={`chip hatbtn ${h}`} disabled={custom.length >= 8}
                  onClick={() => setCustom((c) => [...c, h])}><HatIcon hat={h} size={22} /> + {h}</button>
              ))}
              <button onClick={() => setCustom((c) => c.slice(0, -1))} disabled={!custom.length}>Undo</button>
              <button onClick={() => setCustom([])} disabled={!custom.length}>Clear</button>
            </div>
            <div className="chips" aria-live="polite">
              {custom.length ? custom.map((h, n) => <HatChip key={n} hat={h} />)
                : <span className="hint">Pick 1 to 8 steps. A hat may repeat.</span>}
            </div>
          </>
        )}

        <div className="row" style={{ marginTop: "1rem" }}>
          <button className="primary" onClick={run} disabled={!canRun}>{busy ? "Thinking…" : "Run"}</button>
          {busy && <button onClick={() => abort.current?.abort()}>Cancel</button>}
        </div>
      </section>

      {error && <p className="card error" role="alert">{error}</p>}

      {progress.length > 0 && (
        <section aria-live="polite">
          <h2>Progress</h2>
          <ul className="progress">
            {progress.map((p, n) => <li key={n}>[{p.at.toFixed(1)}s] {p.node}: {p.message}</li>)}
          </ul>
        </section>
      )}

      {report && (
        <>
          <div className="row" style={{ margin: "1rem 0 .5rem" }}>
            <button onClick={() => navigator.clipboard.writeText(reportToMarkdown(report))}>Copy as Markdown</button>
            <button onClick={download}>Download .md</button>
          </div>
          <ReportView report={report} />
        </>
      )}
    </main>
    <footer><div className="rule">Blue opens · five hats think · Blue closes</div></footer>
    </>
  );
}
