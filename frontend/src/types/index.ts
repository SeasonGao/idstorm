export interface Session {
  session_id: string;
  status: "dialogue" | "requirement" | "generating" | "review";
}

export interface MessageOptions {
  type: "single" | "multi";
  items: string[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  options?: MessageOptions | null;
}

export interface DimensionProgress {
  current: string;
  completed: string[];
  remaining: string[];
}

export interface DialogueResponse {
  message: ChatMessage;
  dimension_progress: DimensionProgress;
  dialogue_complete: boolean;
}

export interface DimensionField {
  key: string;
  label: string;
  value: string;
  editable: boolean;
}

export interface Dimension {
  key: string;
  label: string;
  fields: DimensionField[];
}

export interface DesignRequirement {
  session_id: string;
  dimensions: Record<string, Dimension>;
  version: number;
}

export interface CandidateImage {
  id: string;
  image_type: "orthographic" | "render";
  url: string;
}

export interface Candidate {
  id: string;
  label: string;
  variant_description: string;
  orthographic_url: string;
  render_url: string;
  status: "complete" | "partial";
  failed_views: string[];
}

export interface GenerateResponse {
  candidates: Candidate[];
}

export interface IterateRequest {
  session_id: string;
  candidate_id: string;
  mode: "text_edit" | "image_feedback";
  updates: Record<string, string> | { annotation_text: string };
}

export interface SSETokenEvent {
  delta: string;
}

export interface SSEMetadataEvent {
  dimension_progress: DimensionProgress;
  dialogue_complete: boolean;
}

export interface SSEDoneEvent {
  message: ChatMessage;
}

export interface SSEErrorEvent {
  code: "deepseek_timeout" | "deepseek_api_error" | "internal";
  message: string;
}
