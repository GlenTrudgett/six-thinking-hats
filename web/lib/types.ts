export type Hat = "white" | "red" | "green" | "yellow" | "black";

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
  sequence: Hat[];
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
  sequence: Hat[] | null;
}

export type ServerEvent =
  | { event: "start"; data: { run_id: string } }
  | { event: "progress"; data: ProgressEvent }
  | { event: "report"; data: Report }
  | { event: "error"; data: { kind: string; message: string } };
