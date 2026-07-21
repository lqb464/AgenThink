export interface ToolCallData {
  tool: string;
  arguments?: Record<string, any>;
  success?: boolean;
  text?: string;
  /** RAG citations from search_documents / summarize / report */
  sources?: CitationSource[];
}

export interface CitationSource {
  filename: string;
  snippet?: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "tool" | "system";
  content: string | any[];
  images?: string[]; // base64 data urls or urls
  tool_calls?: any[];
  tool_call_id?: string;
  created_at?: string;
  // UI helper fields
  isStreaming?: boolean;
  activeTools?: string[]; // tools running during this assistant response
  toolResults?: ToolCallData[]; // completed tool cards for this turn
  planSteps?: string[];
  reflectStatus?: string;
  /** Flattened citations for the Sources panel */
  citations?: CitationSource[];
}

export interface SessionSummary {
  id: string;
  title: string;
  message_count: number;
  updated_at?: string;
}

export interface HealthResponse {
  status: string;
  agent: string;
  version: string;
  llm_provider: string;
  llm_model: string;
  gemini_key_count?: number;
  auth_required?: boolean;
  services: Record<string, boolean>;
  features: {
    streaming: boolean;
    multimodal: boolean;
    planning?: boolean;
    reflection?: boolean;
    artifacts?: boolean;
    i18n?: boolean;
    model_picker?: boolean;
  };
  model_profiles?: Record<string, unknown>;
}

export interface DocsProjectSnapshot {
  ok?: boolean;
  exists?: boolean;
  project_id: string;
  name?: string;
  sources?: string[];
  stats?: { documents?: number; chunks?: number };
  indexed?: boolean;
  studio_url?: string;
}

export interface DocsStatusResponse {
  online: boolean;
  default_project_id: string;
  project_id: string;
  project: DocsProjectSnapshot | null;
  studio_url?: string | null;
  error?: string | null;
}
