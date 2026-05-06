export interface Session {
  session_id: string;
  status: "dialogue" | "requirement" | "generating" | "review";
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  options?: string[] | null;
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
  product_name: string;
  three_view_desc: string;
  scene_desc: string;
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
  image_url: string;
  prompt: string;
  status: "complete" | "failed";
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
