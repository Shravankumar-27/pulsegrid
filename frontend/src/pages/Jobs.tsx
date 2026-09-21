import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  JobLastResult,
  Theater,
  TrackingJob,
  clearToken,
  createWatchJob,
  deleteJob,
  getJobResults,
  listJobs,
  listTheaters,
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

function formatIST(value: string | null): string {
  if (!value) return "—";
  try {
    const d = new Date(value);
    return (
      d.toLocaleString("en-IN", {
        timeZone: "Asia/Kolkata",
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
        hour12: true,
      }) + " IST"
    );
  } catch {
    return value;
  }
}

function toLocalInputValue(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}`
  );
}

function localInputToIso(value: string): string {
  return new Date(value).toISOString();
}

function defaultFormTimes() {
  const start = new Date();
  start.setMinutes(0, 0, 0);
  const end = new Date(start);
  end.setDate(end.getDate() + 1);
  end.setHours(23, 59, 0, 0);
  return {
    start_at: toLocalInputValue(start),
    end_at: toLocalInputValue(end),
  };
}

export function Jobs({ onLogout }: JobsProps) {
  const [jobs, setJobs] = useState<TrackingJob[]>([]);
  const [theaters, setTheaters] = useState<Theater[]>([]);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("ALL");
  const [platformFilter, setPlatformFilter] = useState<PlatformFilter>("ALL");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [actingId, setActingId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [selectedJobForResults, setSelectedJobForResults] =
    useState<TrackingJob | null>(null);
  const [activeResults, setActiveResults] = useState<JobLastResult | null>(null);
  const [loadingResults, setLoadingResults] = useState(false);

  const defaults = useMemo(() => defaultFormTimes(), []);
  const [movieName, setMovieName] = useState("");
  const [city, setCity] = useState("Hyderabad");
  const [useBms, setUseBms] = useState(true);
  const [useDistrict, setUseDistrict] = useState(false);
  const [bmsTarget, setBmsTarget] = useState("");
  const [districtTarget, setDistrictTarget] = useState("");
  const [startAt, setStartAt] = useState(defaults.start_at);
  const [endAt, setEndAt] = useState(defaults.end_at);
  const [pollSeconds, setPollSeconds] = useState("60");
  const [theaterMode, setTheaterMode] = useState<"saved" | "new" | "any">(
    "any",
  );
  const [savedTheaterId, setSavedTheaterId] = useState("");
  const [theaterName, setTheaterName] = useState("");
  const [bmsVenueId, setBmsVenueId] = useState("");
  const [districtVenueId, setDistrictVenueId] = useState("");

  const refresh = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const [jobData, theaterData] = await Promise.all([
        listJobs(),
        listTheaters(),
      ]);
      setJobs(jobData);
      setTheaters(theaterData);
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

  const selectedTheater = useMemo(() => {
    if (!savedTheaterId) return null;
    return theaters.find((t) => String(t.id) === savedTheaterId) ?? null;
  }, [savedTheaterId, theaters]);

  useEffect(() => {
    if (!selectedTheater) return;
    setTheaterName(selectedTheater.name);
    setCity(selectedTheater.city);
    setBmsVenueId(selectedTheater.bookmyshow_venue_id ?? "");
    setDistrictVenueId(selectedTheater.district_venue_id ?? "");
  }, [selectedTheater]);

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

  async function handleViewResults(job: TrackingJob) {
    setSelectedJobForResults(job);
    setActiveResults(job.last_result_json ?? null);
    setLoadingResults(true);
    try {
      const res = await getJobResults(job.id);
      setActiveResults(res.result);
    } catch (err) {
      setActiveResults({
        available: false,
        message: err instanceof Error ? err.message : "Failed to fetch results.",
        sessions: [],
      });
    } finally {
      setLoadingResults(false);
    }
  }

  function handleLogout() {
    clearToken();
    onLogout();
  }

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setNotice(null);

    const platforms: Array<"bookmyshow" | "district"> = [];
    if (useBms) platforms.push("bookmyshow");
    if (useDistrict) platforms.push("district");

    if (platforms.length === 0) {
      setError("Select BookMyShow, District, or both.");
      return;
    }

    setCreating(true);
    try {
      const result = await createWatchJob({
        movie_name: movieName.trim(),
        city: city.trim(),
        start_at: localInputToIso(startAt),
        end_at: localInputToIso(endAt),
        platforms,
        bookmyshow_target: useBms ? bmsTarget.trim() : null,
        district_target: useDistrict ? districtTarget.trim() : null,
        theater_id:
          theaterMode === "saved" && savedTheaterId
            ? Number(savedTheaterId)
            : null,
        theater_name:
          theaterMode === "any"
            ? "Any"
            : theaterMode === "new"
              ? theaterName.trim() || "Any"
              : selectedTheater?.name ?? "Any",
        bookmyshow_venue_id: bmsVenueId.trim() || null,
        district_venue_id: districtVenueId.trim() || null,
        poll_interval_seconds: Math.max(10, Number(pollSeconds) || 60),
        start_immediately: true,
      });

      setNotice(
        `Created ${result.jobs.length} running job(s). Alerts go to your Telegram when showtimes appear (worker must be running).`,
      );
      setShowForm(false);
      setMovieName("");
      setBmsTarget("");
      setDistrictTarget("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create job.");
    } finally {
      setCreating(false);
    }
  }

  return (
    <main className="ops-shell">
      <header className="ops-header">
        <div>
          <p className="eyebrow">PulseGrid Ops</p>
          <h1>Tracking jobs</h1>
        </div>
        <div className="header-actions">
          <button
            type="button"
            onClick={() => {
              setShowForm((v) => !v);
              setError(null);
              setNotice(null);
            }}
          >
            {showForm ? "Close form" : "New watch"}
          </button>
          <button type="button" className="ghost" onClick={() => void refresh()}>
            Refresh
          </button>
          <button type="button" className="ghost" onClick={handleLogout}>
            Sign out
          </button>
        </div>
      </header>

      {showForm ? (
        <section className="create-panel" aria-label="Create watch">
          <h2>Watch a movie</h2>
          <p className="lede">
            Enter the movie name and platform IDs. When matching showtimes
            appear, PulseGrid notifies you on Telegram.
          </p>

          <form className="create-form" onSubmit={(e) => void handleCreate(e)}>
            <label>
              Movie name
              <input
                value={movieName}
                onChange={(e) => setMovieName(e.target.value)}
                placeholder="e.g. Coolie"
                required
              />
            </label>

            <fieldset className="platform-picks">
              <legend>Platforms</legend>
              <label className="check">
                <input
                  type="checkbox"
                  checked={useBms}
                  onChange={(e) => setUseBms(e.target.checked)}
                />
                BookMyShow
              </label>
              <label className="check">
                <input
                  type="checkbox"
                  checked={useDistrict}
                  onChange={(e) => setUseDistrict(e.target.checked)}
                />
                District
              </label>
            </fieldset>

            {useBms ? (
              <label>
                BookMyShow event code
                <input
                  className="mono"
                  value={bmsTarget}
                  onChange={(e) => setBmsTarget(e.target.value)}
                  placeholder="ET00514261"
                  required
                />
              </label>
            ) : null}

            {useDistrict ? (
              <label>
                District movie code
                <input
                  className="mono"
                  value={districtTarget}
                  onChange={(e) => setDistrictTarget(e.target.value)}
                  placeholder="MV181196"
                  required
                />
              </label>
            ) : null}

            <label>
              City
              <input
                value={city}
                onChange={(e) => setCity(e.target.value)}
                required
              />
            </label>

            <div className="form-row">
              <label>
                Scan from
                <input
                  type="datetime-local"
                  value={startAt}
                  onChange={(e) => setStartAt(e.target.value)}
                  required
                />
              </label>
              <label>
                Scan until
                <input
                  type="datetime-local"
                  value={endAt}
                  onChange={(e) => setEndAt(e.target.value)}
                  required
                />
              </label>
              <label>
                Poll (seconds)
                <input
                  type="number"
                  min={10}
                  value={pollSeconds}
                  onChange={(e) => setPollSeconds(e.target.value)}
                  required
                />
              </label>
            </div>

            <fieldset className="theater-picks">
              <legend>Theater</legend>
              <label className="check">
                <input
                  type="radio"
                  name="theater-mode"
                  checked={theaterMode === "any"}
                  onChange={() => setTheaterMode("any")}
                />
                Any theater
              </label>
              <label className="check">
                <input
                  type="radio"
                  name="theater-mode"
                  checked={theaterMode === "saved"}
                  onChange={() => setTheaterMode("saved")}
                />
                Saved theater
              </label>
              <label className="check">
                <input
                  type="radio"
                  name="theater-mode"
                  checked={theaterMode === "new"}
                  onChange={() => setTheaterMode("new")}
                />
                New theater (saved for reuse)
              </label>
            </fieldset>

            {theaterMode === "saved" ? (
              <label>
                Choose saved theater
                <select
                  value={savedTheaterId}
                  onChange={(e) => setSavedTheaterId(e.target.value)}
                  required
                >
                  <option value="">Select…</option>
                  {theaters.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name} · {t.city}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}

            {theaterMode === "new" || theaterMode === "saved" ? (
              <>
                {theaterMode === "new" ? (
                  <label>
                    Theater name
                    <input
                      value={theaterName}
                      onChange={(e) => setTheaterName(e.target.value)}
                      placeholder="AMB Cinemas"
                      required
                    />
                  </label>
                ) : null}
                <div className="form-row">
                  <label>
                    BookMyShow venue id (optional)
                    <input
                      className="mono"
                      value={bmsVenueId}
                      onChange={(e) => setBmsVenueId(e.target.value)}
                      placeholder="venue code"
                    />
                  </label>
                  <label>
                    District venue id (optional)
                    <input
                      className="mono"
                      value={districtVenueId}
                      onChange={(e) => setDistrictVenueId(e.target.value)}
                      placeholder="venue code"
                    />
                  </label>
                </div>
              </>
            ) : null}

            <button type="submit" disabled={creating}>
              {creating ? "Creating…" : "Start watching"}
            </button>
          </form>
        </section>
      ) : null}

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
      {notice ? <p className="notice banner">{notice}</p> : null}

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
                <th>Movie</th>
                <th>Target</th>
                <th>Platform</th>
                <th>City</th>
                <th>Theater</th>
                <th>Window</th>
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
                    <td>{job.movie_name || "—"}</td>
                    <td className="mono">{job.target_name}</td>
                    <td>{job.platform}</td>
                    <td>{job.city}</td>
                    <td>{job.theater}</td>
                    <td className="mono muted">
                      {formatIST(job.start_at)}
                      <br />
                      {formatIST(job.end_at)}
                    </td>
                    <td>
                      <span
                        className={`status status-${job.status.toLowerCase()}`}
                      >
                        {job.status}
                      </span>
                    </td>
                    <td className="mono">{job.poll_interval_seconds}s</td>
                    <td className="mono muted">
                      {formatIST(job.last_checked_at)}
                    </td>
                    <td>
                      <div className="row-actions">
                        <button
                          type="button"
                          className="ghost"
                          onClick={() => void handleViewResults(job)}
                        >
                          Show Results
                        </button>
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

      {selectedJobForResults ? (
        <div className="modal-overlay" onClick={() => setSelectedJobForResults(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <header className="modal-header">
              <div>
                <h2>
                  {selectedJobForResults.movie_name ||
                    selectedJobForResults.target_name}
                </h2>
                <p className="eyebrow">
                  Job #{selectedJobForResults.id} · {selectedJobForResults.platform} ·{" "}
                  {selectedJobForResults.city}
                </p>
              </div>
              <button
                type="button"
                className="ghost"
                onClick={() => setSelectedJobForResults(null)}
              >
                Close
              </button>
            </header>

            <div className="modal-body">
              <div className="result-meta-grid">
                <div className="meta-item">
                  <span className="meta-label">Theater</span>
                  <span className="meta-val">{selectedJobForResults.theater}</span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Last Polled (IST)</span>
                  <span className="meta-val">
                    {formatIST(selectedJobForResults.last_checked_at)}
                  </span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Poll Interval</span>
                  <span className="meta-val">
                    Every {selectedJobForResults.poll_interval_seconds}s
                  </span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Job Status</span>
                  <span className={`status status-${selectedJobForResults.status.toLowerCase()}`}>
                    {selectedJobForResults.status}
                  </span>
                </div>
              </div>

              {loadingResults ? (
                <p className="muted">Loading live availability results…</p>
              ) : !activeResults ? (
                <p className="muted">No showtimes polling data recorded yet.</p>
              ) : (
                <div className="results-container">
                  <h3>
                    Showtimes & Availability ({activeResults.sessions?.length ?? 0}{" "}
                    detected)
                  </h3>
                  {activeResults.message ? (
                    <p className="lede">{activeResults.message}</p>
                  ) : null}

                  {activeResults.sessions && activeResults.sessions.length > 0 ? (
                    <div className="sessions-list">
                      {activeResults.sessions.map((sess, idx) => (
                        <div key={sess.id ?? idx} className="session-card">
                          <div className="session-main">
                            <span className="session-time">
                              🕐 {sess.time || "Time unstated"}
                            </span>
                            <span className="session-details">
                              🏢 {sess.cinema || selectedJobForResults.theater} · 🎞️{" "}
                              {sess.format || "2D"} {sess.language ? `· ${sess.language}` : ""}
                            </span>
                          </div>
                          <span className="badge-tag">
                            ID: {sess.id || "N/A"}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="muted">
                      No matching sessions currently available for this window.
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}
