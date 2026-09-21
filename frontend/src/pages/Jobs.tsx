import { useCallback, useEffect, useMemo, useState } from "react";
import {
  TrackingJob,
  clearToken,
  deleteJob,
  listJobs,
  pauseJob,
  resumeJob,
  startJob,
  stopJob,
} from "../api";

interface JobsProps {
  onLogout: () => void;
}

type StatusFilter = "ALL" | string;
type PlatformFilter = "ALL" | string;

function formatWhen(value: string | null): string {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

export function Jobs({ onLogout }: JobsProps) {
  const [jobs, setJobs] = useState<TrackingJob[]>([]);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("ALL");
  const [platformFilter, setPlatformFilter] = useState<PlatformFilter>("ALL");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [actingId, setActingId] = useState<number | null>(null);

  const refresh = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const data = await listJobs();
      setJobs(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load jobs.");
      if (err instanceof Error && err.message.includes("Unauthorized")) {
        onLogout();
      }
    } finally {
      setLoading(false);
    }
  }, [onLogout]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const filtered = useMemo(() => {
    return jobs.filter((job) => {
      if (statusFilter !== "ALL" && job.status !== statusFilter) return false;
      if (platformFilter !== "ALL" && job.platform !== platformFilter) {
        return false;
      }
      return true;
    });
  }, [jobs, statusFilter, platformFilter]);

  async function runAction(
    jobId: number,
    action: (id: number) => Promise<unknown>,
  ) {
    setActingId(jobId);
    setError(null);
    try {
      await action(jobId);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed.");
    } finally {
      setActingId(null);
    }
  }

  function handleLogout() {
    clearToken();
    onLogout();
  }

  return (
    <main className="ops-shell">
      <header className="ops-header">
        <div>
          <p className="eyebrow">PulseGrid Ops</p>
          <h1>Tracking jobs</h1>
        </div>
        <div className="header-actions">
          <button type="button" className="ghost" onClick={() => void refresh()}>
            Refresh
          </button>
          <button type="button" className="ghost" onClick={handleLogout}>
            Sign out
          </button>
        </div>
      </header>

      <section className="filters" aria-label="Filters">
        <label>
          Status
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="ALL">All</option>
            <option value="RUNNING">RUNNING</option>
            <option value="PAUSED">PAUSED</option>
            <option value="PENDING">PENDING</option>
            <option value="STOPPED">STOPPED</option>
            <option value="COMPLETED">COMPLETED</option>
          </select>
        </label>
        <label>
          Platform
          <select
            value={platformFilter}
            onChange={(e) => setPlatformFilter(e.target.value)}
          >
            <option value="ALL">All</option>
            <option value="bookmyshow">bookmyshow</option>
            <option value="district">district</option>
            <option value="mock">mock</option>
          </select>
        </label>
        <p className="filter-meta">
          {filtered.length} of {jobs.length} jobs
        </p>
      </section>

      {error ? <p className="error banner">{error}</p> : null}

      <div className="table-wrap">
        {loading ? (
          <p className="muted">Loading jobs…</p>
        ) : filtered.length === 0 ? (
          <p className="muted">No jobs match these filters.</p>
        ) : (
          <table className="jobs-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Target</th>
                <th>Platform</th>
                <th>City</th>
                <th>Theater</th>
                <th>Date</th>
                <th>Status</th>
                <th>Poll</th>
                <th>Last checked</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((job) => {
                const busy = actingId === job.id;
                return (
                  <tr key={job.id}>
                    <td className="mono">#{job.id}</td>
                    <td className="mono">{job.target_name}</td>
                    <td>{job.platform}</td>
                    <td>{job.city}</td>
                    <td>{job.theater}</td>
                    <td className="mono">{job.target_date}</td>
                    <td>
                      <span className={`status status-${job.status.toLowerCase()}`}>
                        {job.status}
                      </span>
                    </td>
                    <td className="mono">{job.poll_interval_seconds}s</td>
                    <td className="mono muted">{formatWhen(job.last_checked_at)}</td>
                    <td>
                      <div className="row-actions">
                        {job.status === "RUNNING" ? (
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => void runAction(job.id, pauseJob)}
                          >
                            Pause
                          </button>
                        ) : null}
                        {job.status === "PAUSED" || job.status === "PENDING" ? (
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() =>
                              void runAction(
                                job.id,
                                job.status === "PENDING" ? startJob : resumeJob,
                              )
                            }
                          >
                            {job.status === "PENDING" ? "Start" : "Resume"}
                          </button>
                        ) : null}
                        {job.status === "RUNNING" || job.status === "PAUSED" ? (
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => void runAction(job.id, stopJob)}
                          >
                            Stop
                          </button>
                        ) : null}
                        <button
                          type="button"
                          className="danger"
                          disabled={busy}
                          onClick={() => {
                            if (
                              window.confirm(
                                `Delete job #${job.id} (${job.target_name})?`,
                              )
                            ) {
                              void runAction(job.id, deleteJob);
                            }
                          }}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </main>
  );
}
