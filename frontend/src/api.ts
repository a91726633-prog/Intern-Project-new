import type { JobListItem, JobRead, JobStatus } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function uploadDocuments(files: FileList): Promise<{ jobs: JobListItem[] }> {
  const formData = new FormData();
  Array.from(files).forEach((file) => formData.append("files", file));
  return request("/api/documents", { method: "POST", body: formData });
}

export async function fetchJobs(params: { status?: JobStatus | "all"; search?: string; sort?: string }): Promise<JobListItem[]> {
  const searchParams = new URLSearchParams();
  if (params.status && params.status !== "all") searchParams.set("status", params.status);
  if (params.search) searchParams.set("search", params.search);
  if (params.sort) searchParams.set("sort", params.sort);
  return request(`/api/jobs?${searchParams.toString()}`);
}

export async function fetchJob(jobId: string): Promise<JobRead> {
  return request(`/api/jobs/${jobId}`);
}

export async function retryJob(jobId: string): Promise<JobRead> {
  return request(`/api/jobs/${jobId}/retry`, { method: "POST" });
}

export async function saveReview(jobId: string, reviewedJson: Record<string, unknown>): Promise<JobRead> {
  return request(`/api/jobs/${jobId}/review`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reviewed_json: reviewedJson }),
  });
}

export async function finalizeJob(jobId: string): Promise<JobRead> {
  return request(`/api/jobs/${jobId}/finalize`, { method: "POST" });
}

export function exportUrl(jobId: string, format: "json" | "csv"): string {
  return `${API_BASE_URL}/api/jobs/${jobId}/export?format=${format}`;
}

export function eventUrl(jobId: string): string {
  return `${API_BASE_URL}/api/jobs/${jobId}/events`;
}
