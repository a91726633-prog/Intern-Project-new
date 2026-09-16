export type JobStatus = "queued" | "processing" | "completed" | "failed" | "finalized";

export interface DocumentRead {
  id: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
}

export interface ProgressEventRead {
  id: string;
  event_type: string;
  message: string;
  progress_percent: number;
  attempt_number: number;
  created_at: string;
}

export interface ExtractedResultRead {
  extracted_json: Record<string, unknown>;
  reviewed_json?: Record<string, unknown> | null;
  finalized_json?: Record<string, unknown> | null;
}

export interface JobRead {
  id: string;
  status: JobStatus;
  progress_percent: number;
  error_message?: string | null;
  attempt_count: number;
  created_at: string;
  updated_at: string;
  document: DocumentRead;
  result?: ExtractedResultRead | null;
  events: ProgressEventRead[];
}

export type JobListItem = Omit<JobRead, "result" | "events">;
