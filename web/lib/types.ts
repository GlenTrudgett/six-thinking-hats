export type Hat = "white" | "red" | "green" | "yellow" | "black";
/** A step in a sequence: a coloured hat, or "blue" for a Blue checkpoint between hats. */
export type Step = Hat | "blue";

export interface BlueCheckpoint {
  progress: string[];
  gaps: string[];
  next_focus: string;
}

export interface CheckpointRecord {
  after: Hat;
  checkpoint: BlueCheckpoint;
}

/** Why a custom order is not allowed, or null. Mirrors the server rule. */
export function blueProblem(steps: Step[]): string | null {
  if (!steps.includes("blue")) return null;
  if (steps[0] === "blue" || steps[steps.length - 1] === "blue")
    return "A Blue checkpoint sits between hats, not first or last.";
  if (steps.some((s, i) => s === "blue" && steps[i + 1] === "blue"))
    return "Two Blue checkpoints cannot be next to each other.";
  return null;
}

export interface PresetInfo {
  id: string;
  title: string;
  use_when: string;
  sequence: Hat[];
  source: string;
}

export interface HatSummary {
  hat: Hat;
  summary: string;
}

export interface Failure {
  node: string;
  hat: Hat | null;
  error_type: string;
  message: string;
}

export interface Report {
  run_id: string;
  framing_summary: string;
  hat_summaries: HatSummary[];
  conclusions: string[];
  agreements: string[];
  tensions: string[];
  recommended_next_steps: string[];
  open_questions: string[];
  missing_perspectives: Hat[];
  mode: "parallel" | "sequential";
  sequence: Step[];
  checkpoints: CheckpointRecord[];
  preset: string | null;
  preset_source: string | null;
  degraded: boolean;
  failures: Failure[];
  models_used: string[];
  token_usage: Record<string, number>;
  elapsed_seconds: number | null;
  estimated_cost: number | null;
  cost_currency: string | null;
}

export interface ProgressEvent {
  node: string;
  message: string;
}

export interface RunOptions {
  question: string;
  mode: "auto" | "parallel";
  preset: string | null;
  sequence: Step[] | null;
}

export type ServerEvent =
  | { event: "start"; data: { run_id: string } }
  | { event: "progress"; data: ProgressEvent }
  | { event: "report"; data: Report }
  | { event: "error"; data: { kind: string; message: string } };
