import type { RunOptions, ServerEvent } from "./types";

/** Parse a server-sent event stream into events. Works with POST, unlike EventSource. */
export async function* streamRun(
  options: RunOptions,
  signal: AbortSignal,
): AsyncGenerator<ServerEvent> {
  const res = await fetch("/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question: options.question,
      mode: options.mode,
      preset: options.preset,
      sequence: options.sequence,
    }),
    signal,
  });
  if (!res.ok || !res.body) {
    throw new Error(
      res.status === 422 ? "The request was not valid (check the question length)." : `Server error (${res.status}).`,
    );
  }
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) return;
    buffer += value;
    let split: number;
    while ((split = buffer.indexOf("\n\n")) !== -1) {
      const block = buffer.slice(0, split);
      buffer = buffer.slice(split + 2);
      const event = /^event: (.+)$/m.exec(block)?.[1];
      const data = /^data: (.+)$/m.exec(block)?.[1];
      if (event && data) yield { event, data: JSON.parse(data) } as ServerEvent;
    }
  }
}
