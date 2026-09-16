import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  CheckCircle2,
  Download,
  FileText,
  RefreshCcw,
  RotateCcw,
  Save,
  Search,
  Send,
  UploadCloud,
} from "lucide-react";

import {
  eventUrl,
  exportUrl,
  fetchJob,
  fetchJobs,
  finalizeJob,
  retryJob,
  saveReview,
  uploadDocuments,
} from "./api";
import type { JobListItem, JobRead, JobStatus } from "./types";
import "./styles.css";

const statusOptions: Array<JobStatus | "all"> = ["all", "queued", "processing", "completed", "failed", "finalized"];

function App() {
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [selectedJob, setSelectedJob] = useState<JobRead | null>(null);
  const [status, setStatus] = useState<JobStatus | "all">("all");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("newest");
  const [reviewText, setReviewText] = useState("{}");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(false);

  async function loadJobs() {
    const data = await fetchJobs({ status, search, sort });
    setJobs(data);
    if (!selectedJobId && data[0]) setSelectedJobId(data[0].id);
  }

  async function loadSelectedJob(id: string) {
    const data = await fetchJob(id);
    setSelectedJob(data);
    const result = data.result?.reviewed_json ?? data.result?.extracted_json ?? {};
    setReviewText(JSON.stringify(result, null, 2));
  }

  useEffect(() => {
    loadJobs().catch((error) => setNotice(error.message));
  }, [status, search, sort]);

  useEffect(() => {
    if (!selectedJobId) return;
    loadSelectedJob(selectedJobId).catch((error) => setNotice(error.message));
  }, [selectedJobId]);

  useEffect(() => {
    if (!selectedJobId) return;
    const source = new EventSource(eventUrl(selectedJobId));
    source.addEventListener("progress", () => {
      loadJobs().catch(() => undefined);
      loadSelectedJob(selectedJobId).catch(() => undefined);
    });
    return () => source.close();
  }, [selectedJobId, status, search, sort]);

  async function handleUpload(files: FileList | null) {
    if (!files?.length) return;
    setLoading(true);
    try {
      const response = await uploadDocuments(files);
      setNotice(`${response.jobs.length} document job queued.`);
      await loadJobs();
      setSelectedJobId(response.jobs[0]?.id ?? null);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleSaveReview() {
    if (!selectedJob) return;
    try {
      const parsed = JSON.parse(reviewText) as Record<string, unknown>;
      const updated = await saveReview(selectedJob.id, parsed);
      setSelectedJob(updated);
      setNotice("Reviewed result saved.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Review save failed");
    }
  }

  async function handleFinalize() {
    if (!selectedJob) return;
    try {
      const updated = await finalizeJob(selectedJob.id);
      setSelectedJob(updated);
      await loadJobs();
      setNotice("Record finalized and ready to export.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Finalize failed");
    }
  }

  async function handleRetry(jobId: string) {
    try {
      await retryJob(jobId);
      await loadJobs();
      await loadSelectedJob(jobId);
      setNotice("Failed job queued for retry.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Retry failed");
    }
  }

  const selectedResult = useMemo(
    () => selectedJob?.result?.finalized_json ?? selectedJob?.result?.reviewed_json ?? selectedJob?.result?.extracted_json,
    [selectedJob],
  );

  return (
    <main className="app-shell">
      <section className="top-band">
        <div>
          <p className="eyebrow">Internship Assignment</p>
          <h1>Async Document Processing Workflow</h1>
          <p className="subcopy">Upload documents, process them through Celery, track Redis Pub/Sub progress, review results, finalize, and export.</p>
        </div>
        <label className="upload-drop">
          <UploadCloud size={28} />
          <span>{loading ? "Queueing..." : "Upload documents"}</span>
          <input type="file" multiple onChange={(event) => handleUpload(event.target.files)} />
        </label>
      </section>

      {notice && <div className="notice">{notice}</div>}

      <section className="workspace-grid">
        <aside className="job-panel">
          <div className="panel-header">
            <h2>Jobs</h2>
            <button className="icon-button" onClick={loadJobs} aria-label="Refresh jobs">
              <RefreshCcw size={18} />
            </button>
          </div>
          <div className="filters">
            <div className="search-box">
              <Search size={16} />
              <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search filename or job id" />
            </div>
            <select value={status} onChange={(event) => setStatus(event.target.value as JobStatus | "all")}>
              {statusOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
            <select value={sort} onChange={(event) => setSort(event.target.value)}>
              <option value="newest">Newest first</option>
              <option value="oldest">Oldest first</option>
            </select>
          </div>

          <div className="job-list">
            {jobs.map((job) => (
              <button
                key={job.id}
                className={`job-row ${selectedJobId === job.id ? "active" : ""}`}
                onClick={() => setSelectedJobId(job.id)}
              >
                <div className="job-title">
                  <FileText size={18} />
                  <span>{job.document.original_filename}</span>
                </div>
                <div className="job-meta">
                  <span className={`status-pill ${job.status}`}>{job.status}</span>
                  <span>{job.progress_percent}%</span>
                </div>
                <div className="progress-track">
                  <div style={{ width: `${job.progress_percent}%` }} />
                </div>
              </button>
            ))}
            {!jobs.length && <p className="empty-state">No jobs yet. Upload one or more documents to begin.</p>}
          </div>
        </aside>

        <section className="detail-panel">
          {selectedJob ? (
            <>
              <div className="detail-header">
                <div>
                  <p className="eyebrow">Document Detail</p>
                  <h2>{selectedJob.document.original_filename}</h2>
                </div>
                <span className={`status-pill ${selectedJob.status}`}>{selectedJob.status}</span>
              </div>

              <div className="metrics-row">
                <Metric label="Progress" value={`${selectedJob.progress_percent}%`} />
                <Metric label="Attempts" value={String(selectedJob.attempt_count)} />
                <Metric label="Size" value={`${Math.round(selectedJob.document.size_bytes / 1024 || 1)} KB`} />
              </div>

              <div className="progress-track large">
                <div style={{ width: `${selectedJob.progress_percent}%` }} />
              </div>

              {selectedJob.error_message && (
                <div className="error-box">
                  <span>{selectedJob.error_message}</span>
                  <button onClick={() => handleRetry(selectedJob.id)}>
                    <RotateCcw size={16} /> Retry
                  </button>
                </div>
              )}

              <div className="split-area">
                <div>
                  <h3>Progress Timeline</h3>
                  <ol className="timeline">
                    {selectedJob.events.map((event) => (
                      <li key={event.id}>
                        <CheckCircle2 size={16} />
                        <div>
                          <strong>{event.event_type}</strong>
                          <span>{event.message}</span>
                        </div>
                      </li>
                    ))}
                  </ol>
                </div>
                <div>
                  <h3>Review / Edit Result</h3>
                  <textarea value={reviewText} onChange={(event) => setReviewText(event.target.value)} spellCheck={false} />
                  <div className="actions">
                    <button onClick={handleSaveReview} disabled={!selectedResult}>
                      <Save size={16} /> Save Review
                    </button>
                    <button onClick={handleFinalize} disabled={!selectedResult}>
                      <Send size={16} /> Finalize
                    </button>
                    <a className="button-link" href={exportUrl(selectedJob.id, "json")}>
                      <Download size={16} /> JSON
                    </a>
                    <a className="button-link" href={exportUrl(selectedJob.id, "csv")}>
                      <Download size={16} /> CSV
                    </a>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="empty-detail">
              <UploadCloud size={36} />
              <h2>Upload documents to start processing</h2>
            </div>
          )}
        </section>
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
