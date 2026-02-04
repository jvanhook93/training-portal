import { useEffect, useMemo, useState } from "react";

/**
 * ✅ Branding rewrite:
 * - Removes the deep-blue/dark inline theme
 * - Uses your existing brand.css tokens/classes (light theme)
 * - Keeps the API base / unauth HTML detection logic
 * - Keeps the logout fix (top-level navigation to backend)
 *
 * NOTE: This assumes brand.css is available to the SPA.
 * If your SPA is served by Cloudflare Pages, make sure brand.css is in the SPA build:
 *   - easiest: copy backend/static/brand/brand.css into frontend/public/brand/brand.css
 * and then in main.jsx import it:
 *   import "/brand/brand.css";
 *
 * If your SPA is served same-origin from Railway (Django), you can also inject it via index.html,
 * but the above public/ import is the cleanest.
 */

const ENV_API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");

function isLocalHostHost(hostname) {
  return hostname === "localhost" || hostname === "127.0.0.1";
}

function isRailwayHost(hostname) {
  return hostname.endsWith(".up.railway.app") || hostname.includes("railway.app");
}

function isDeployedFrontendHost(hostname) {
  return hostname.endsWith("pages.dev") || hostname.endsWith("integranethealth.com");
}

function resolveApiBase() {
  const hostname = window.location.hostname;

  // If we're on Railway (Django serving /app/), ALWAYS same-origin
  if (isRailwayHost(hostname)) return "";

  // Local dev hitting Django directly is same-origin
  if (isLocalHostHost(hostname)) return "";

  // Cloudflare Pages / custom domain must use env var
  if (isDeployedFrontendHost(hostname)) return ENV_API_BASE || "";

  // Fallback
  return ENV_API_BASE || "";
}

const API_BASE = resolveApiBase();

function joinUrl(base, path) {
  if (!base) return path;
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${base}${p}`;
}

function apiUrl(path) {
  return joinUrl(API_BASE, path);
}

function backendUrl(path) {
  return joinUrl(API_BASE, path);
}

async function apiFetch(path, init = {}) {
  return fetch(apiUrl(path), { credentials: "include", ...init });
}

function fmtDate(s) {
  if (!s) return "—";
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString();
}

function statusLabel(s) {
  if (s === "ASSIGNED") return "Assigned";
  if (s === "IN_PROGRESS") return "In Progress";
  if (s === "COMPLETED") return "Completed";
  if (s === "OVERDUE") return "Overdue";
  return s || "—";
}

function StatCard({ label, value, hint, onClick }) {
  return (
    <div
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      className="brand-card"
      style={{
        padding: 16,
        cursor: onClick ? "pointer" : "default",
        userSelect: "none",
      }}
    >
      <div className="brand-sub" style={{ fontWeight: 700, marginBottom: 10 }}>
        {label}
      </div>
      <div style={{ fontSize: 32, fontWeight: 900, lineHeight: 1 }}>{value}</div>
      <div className="brand-sub" style={{ marginTop: 6 }}>
        {hint}
      </div>
    </div>
  );
}

function Badge({ children }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "2px 10px",
        borderRadius: 999,
        border: "1px solid var(--border)",
        background: "var(--surface-alt)",
        color: "var(--muted)",
        fontSize: 12,
        fontWeight: 700,
      }}
    >
      {children}
    </span>
  );
}

export default function App() {
  const [me, setMe] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | authed | unauth | error | nobackend
  const [page, setPage] = useState("dashboard"); // dashboard | courses

  const [courses, setCourses] = useState([]);
  const [coursesStatus, setCoursesStatus] = useState("idle"); // idle | loading | ready | error

  const [assignments, setAssignments] = useState([]);
  const [assignStatus, setAssignStatus] = useState("idle"); // idle | loading | ready | error
  const [assignError, setAssignError] = useState("");

  const [assignView, setAssignView] = useState("all"); // all | assigned | inprogress | completed
  const [busyId, setBusyId] = useState(null);

  // ---- boot auth ----
  useEffect(() => {
    (async () => {
      const hostname = window.location.hostname;

      // Only require API_BASE on Cloudflare Pages/custom domain.
      if (isDeployedFrontendHost(hostname) && !API_BASE) {
        setStatus("nobackend");
        return;
      }

      try {
        const r = await apiFetch("/api/me/", { headers: { Accept: "application/json" } });

        if (r.status === 401) {
          setStatus("unauth");
          return;
        }

        const ct = (r.headers.get("content-type") || "").toLowerCase();
        if (!ct.includes("application/json")) {
          setStatus("unauth");
          return;
        }

        if (!r.ok) {
          setStatus("error");
          return;
        }

        const data = await r.json();
        setMe(data);
        setStatus("authed");
      } catch {
        setStatus("error");
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadCourses() {
    try {
      setCoursesStatus("loading");
      const r = await apiFetch("/api/courses/", { headers: { Accept: "application/json" } });
      if (!r.ok) throw new Error("bad response");
      const data = await r.json();
      setCourses(data.results || []);
      setCoursesStatus("ready");
    } catch {
      setCoursesStatus("error");
    }
  }

  async function loadAssignments() {
    try {
      setAssignError("");
      setAssignStatus("loading");

      const r = await apiFetch("/api/me/assignments/", { headers: { Accept: "application/json" } });

      if (r.status === 401) {
        setStatus("unauth");
        return;
      }

      const ct = (r.headers.get("content-type") || "").toLowerCase();
      if (!ct.includes("application/json")) {
        setStatus("unauth");
        return;
      }

      if (!r.ok) {
        const txt = await r.text().catch(() => "");
        throw new Error(`assignments load failed: ${r.status} ${txt}`);
      }

      const data = await r.json();
      setAssignments(data.results || []);
      setAssignStatus("ready");
    } catch (e) {
      setAssignStatus("error");
      setAssignError(String(e?.message || e));
    }
  }

  useEffect(() => {
    if (status === "authed" && assignStatus === "idle") loadAssignments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  const counts = useMemo(() => {
    const completed = assignments.filter((a) => a.status === "COMPLETED").length;
    const inProgress = assignments.filter((a) => a.status === "IN_PROGRESS").length;
    const assigned = assignments.filter((a) => a.status === "ASSIGNED").length;
    const overdue = assignments.filter((a) => a.status === "OVERDUE").length;
    return { assigned, inProgress, completed, overdue, total: assignments.length };
  }, [assignments]);

  const filteredAssignments = useMemo(() => {
    if (assignView === "assigned") return assignments.filter((a) => a.status === "ASSIGNED");
    if (assignView === "inprogress") return assignments.filter((a) => a.status === "IN_PROGRESS");
    if (assignView === "completed") return assignments.filter((a) => a.status === "COMPLETED");
    return assignments;
  }, [assignments, assignView]);

  async function startAssignment(a) {
    try {
      setBusyId(a.id);

      // NOTE: When served from Pages, CSRF for POST can be tricky cross-site.
      // If this ever 403s from Pages, the recommended fix is to make this endpoint CSRF-exempt
      // and require session auth + SameSite=None cookies (which you already have).
      const r = await apiFetch(`/api/assignments/${a.id}/start/`, {
        method: "POST",
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });

      if (!r.ok) {
        const txt = await r.text().catch(() => "");
        throw new Error(`Start failed: ${r.status} ${txt}`);
      }

      await loadAssignments();

      const cvId = a.course_version?.id || a.course_version_id || a.course_version;
      if (cvId) window.location.href = backendUrl(`/training/${cvId}/`);
    } catch (e) {
      alert(e?.message || "Could not start assignment");
    } finally {
      setBusyId(null);
    }
  }

  function resumeAssignment(a) {
    const cvId = a.course_version?.id || a.course_version_id || a.course_version;
    if (cvId) window.location.href = backendUrl(`/training/${cvId}/`);
  }

  // Logout URL (GET + redirect back to current page)
  const logoutUrl = backendUrl(`/accounts/logout/?next=${encodeURIComponent(window.location.href)}`);

  // ---- UI states ----
  if (status === "loading") {
    return (
      <div className="brand-wrap">
        <div className="brand-card" style={{ width: "min(520px, 100%)" }}>
          <div className="brand-title">IntegraNet Training Portal</div>
          <div className="brand-sub" style={{ marginTop: 6 }}>
            Loading…
          </div>
        </div>
      </div>
    );
  }

  if (status === "nobackend") {
    return (
      <div className="brand-wrap">
        <div className="brand-card" style={{ width: "min(720px, 100%)" }}>
          <div className="brand-title">IntegraNet Training Portal</div>
          <div className="brand-sub" style={{ marginTop: 6 }}>
            Backend is not connected. This site is running as a static preview on Cloudflare Pages.
          </div>

          <div className="brand-hint" style={{ marginTop: 12 }}>
            Set <code>VITE_API_BASE_URL</code> in Cloudflare Pages to your Django backend URL (example:{" "}
            <code>https://web-production-4c59f.up.railway.app</code>).
          </div>

          <div className="brand-hint" style={{ marginTop: 10 }}>
            API Base: <code>{API_BASE || "(same-origin)"}</code>
          </div>
        </div>
      </div>
    );
  }

  if (status === "unauth") {
    const loginUrl = backendUrl("/accounts/login/?next=/app/");
    return (
      <div className="brand-wrap">
        <div className="brand-card" style={{ width: "min(520px, 100%)" }}>
          <div className="brand-title">IntegraNet Training Portal</div>
          <div className="brand-sub" style={{ marginTop: 6 }}>
            You’re not logged in.
          </div>

          <div className="brand-actions" style={{ marginTop: 16 }}>
            <a className="brand-btn primary" href={loginUrl} style={{ display: "inline-flex", alignItems: "center" }}>
              Login
            </a>
            <div className="brand-hint">You’ll be redirected back after login.</div>
          </div>

          <div className="brand-hint" style={{ marginTop: 10 }}>
            API Base: <code>{API_BASE || "(same-origin)"}</code>
          </div>
        </div>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="brand-wrap">
        <div className="brand-card" style={{ width: "min(720px, 100%)" }}>
          <div className="brand-title">IntegraNet Training Portal</div>
          <div className="brand-sub" style={{ marginTop: 6 }}>
            Couldn’t load your account.
          </div>

          <div className="brand-hint" style={{ marginTop: 12 }}>
            If this is running on Cloudflare Pages, make sure <code>VITE_API_BASE_URL</code> is set and the backend is reachable.
          </div>

          <div className="brand-hint" style={{ marginTop: 10 }}>
            API Base: <code>{API_BASE || "(same-origin)"}</code>
          </div>
        </div>
      </div>
    );
  }

  // ---- main app ----
  return (
    <div className="brand-wrap" style={{ alignItems: "flex-start" }}>
      <div style={{ width: "min(1100px, 100%)" }}>
        {/* Header */}
        <div className="brand-card" style={{ padding: 16, marginBottom: 14 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <div>
              <div className="brand-title">IntegraNet Training Portal</div>
              <div className="brand-sub">
                {(me?.first_name || me?.username || "User") + " " + (me?.last_name || "")}
              </div>
            </div>

            <div style={{ marginLeft: "auto", display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
              <button
                className="brand-btn"
                onClick={() => setPage("dashboard")}
                style={{
                  borderColor: page === "dashboard" ? "var(--primary)" : "var(--border)",
                }}
              >
                Dashboard
              </button>

              <button
                className="brand-btn"
                onClick={() => {
                  setPage("courses");
                  if (coursesStatus === "idle") loadCourses();
                }}
                style={{
                  borderColor: page === "courses" ? "var(--primary)" : "var(--border)",
                }}
              >
                Courses
              </button>

              {(me?.is_staff || me?.is_superuser) && (
                <a className="brand-btn" href={backendUrl("/admin/")}>
                  Admin
                </a>
              )}

              <a className="brand-btn" href={logoutUrl}>
                Logout
              </a>
            </div>
          </div>
        </div>

        {/* Dashboard */}
        {page === "dashboard" && (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 14 }}>
              <StatCard
                label="Assigned"
                value={assignStatus === "loading" ? "…" : counts.assigned}
                hint="Not started yet"
                onClick={() => setAssignView("assigned")}
              />
              <StatCard
                label="In Progress"
                value={assignStatus === "loading" ? "…" : counts.inProgress}
                hint="Started"
                onClick={() => setAssignView("inprogress")}
              />
              <StatCard
                label="Completed"
                value={assignStatus === "loading" ? "…" : counts.completed}
                hint="Finished"
                onClick={() => setAssignView("completed")}
              />
            </div>

            <div style={{ height: 14 }} />

            <div className="brand-card" style={{ width: "100%", padding: 18 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
                <div>
                  <div className="brand-title" style={{ fontSize: 18 }}>My Assignments</div>
                  <div className="brand-sub" style={{ marginTop: 2 }}>
                    View:{" "}
                    <b>{assignView === "all" ? "All" : assignView === "inprogress" ? "In Progress" : assignView.charAt(0).toUpperCase() + assignView.slice(1)}</b>
                  </div>
                </div>

                <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                  <Badge>{assignView === "all" ? "All" : statusLabel(assignView.toUpperCase())}</Badge>

                  <button className="brand-btn" onClick={() => setAssignView("all")}>
                    Show all
                  </button>

                  <button className="brand-btn primary" onClick={loadAssignments}>
                    Refresh
                  </button>
                </div>
              </div>

              {assignStatus === "error" && (
                <div className="brand-error" style={{ marginTop: 10 }}>
                  Couldn’t load assignments. {assignError ? `(${assignError})` : ""}
                </div>
              )}

              {assignStatus === "loading" && <div className="brand-hint" style={{ marginTop: 12 }}>Loading…</div>}

              {assignStatus !== "loading" && filteredAssignments.length === 0 && (
                <div className="brand-hint" style={{ marginTop: 12 }}>No assignments in this view.</div>
              )}

              {filteredAssignments.length > 0 && (
                <div style={{ display: "grid", gap: 10, marginTop: 12 }}>
                  {filteredAssignments.map((a) => {
                    const title = a.course?.title || a.course_title || "Course";
                    const code = a.course?.code || a.course_code || "";
                    const version = a.course_version?.version || a.version || "";
                    const due = a.due_at || null;

                    const canStart = a.status === "ASSIGNED";
                    const canResume = a.status === "IN_PROGRESS" || a.status === "COMPLETED" || a.status === "OVERDUE";
                    const certId = a.certificate_id || null;

                    return (
                      <div
                        key={a.id}
                        style={{
                          border: "1px solid var(--border)",
                          borderRadius: 12,
                          padding: 12,
                          background: "var(--surface-alt)",
                          display: "flex",
                          justifyContent: "space-between",
                          gap: 12,
                          alignItems: "center",
                          flexWrap: "wrap",
                        }}
                      >
                        <div style={{ minWidth: 240 }}>
                          <div style={{ fontWeight: 900, color: "var(--text)" }}>
                            {title}{" "}
                            {code ? <span style={{ color: "var(--muted)", fontWeight: 700 }}>({code})</span> : null}
                          </div>

                          <div style={{ marginTop: 6, display: "flex", gap: 8, flexWrap: "wrap" }}>
                            <Badge>{statusLabel(a.status)}</Badge>
                            {version ? <Badge>v{version}</Badge> : null}
                            <Badge>Due: {fmtDate(due)}</Badge>
                          </div>
                        </div>

                        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                          {canStart && (
                            <button
                              className="brand-btn primary"
                              disabled={busyId === a.id}
                              onClick={() => startAssignment(a)}
                              style={{
                                opacity: busyId === a.id ? 0.7 : 1,
                                cursor: busyId === a.id ? "not-allowed" : "pointer",
                              }}
                            >
                              {busyId === a.id ? "Starting…" : "Start"}
                            </button>
                          )}

                          {canResume && (
                            <button className="brand-btn" onClick={() => resumeAssignment(a)}>
                              {a.status === "COMPLETED" ? "View" : "Resume"}
                            </button>
                          )}

                          {a.status === "COMPLETED" && certId && (
                            <a className="brand-btn" href={backendUrl(`/audits/certificates/${certId}/download/`)} target="_blank" rel="noreferrer">
                              Certificate
                            </a>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </>
        )}

        {/* Courses */}
        {page === "courses" && (
          <div className="brand-card" style={{ width: "100%", padding: 18 }}>
            <div className="brand-title" style={{ fontSize: 18 }}>Courses</div>

            {coursesStatus === "loading" && <p className="brand-hint">Loading courses…</p>}
            {coursesStatus === "error" && <p className="brand-error">Couldn’t load courses.</p>}
            {coursesStatus === "ready" && courses.length === 0 && <p className="brand-hint">No courses available.</p>}

            {coursesStatus === "ready" && courses.length > 0 && (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 14, marginTop: 12 }}>
                {courses.map((c) => (
                  <div key={c.id} className="brand-card" style={{ padding: 16 }}>
                    <div style={{ fontWeight: 900 }}>
                      {c.title}{" "}
                      <span style={{ color: "var(--muted)", fontWeight: 700 }}>({c.code})</span>
                    </div>

                    {c.description ? (
                      <div className="brand-sub" style={{ marginTop: 8 }}>{c.description}</div>
                    ) : (
                      <div className="brand-sub" style={{ marginTop: 8 }}>No description</div>
                    )}

                    <div style={{ marginTop: 10 }}>
                      {c.published_version ? (
                        <div className="brand-sub">
                          Version <b style={{ color: "var(--text)" }}>{c.published_version.version}</b> · Pass score{" "}
                          <b style={{ color: "var(--text)" }}>{c.published_version.pass_score}%</b>
                        </div>
                      ) : (
                        <div className="brand-sub" style={{ color: "var(--warn)" }}>No published version yet</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="brand-hint" style={{ marginTop: 14, textAlign: "center" }}>
          © {new Date().getFullYear()} IntegraNet Health
        </div>
      </div>
    </div>
  );
}
