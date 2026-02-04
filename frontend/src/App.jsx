import { useEffect, useMemo, useState } from "react";

/**
 * API base rules:
 * - If SPA is served from Railway backend origin => use same-origin relative URLs ("")
 * - If SPA is served from Cloudflare Pages/custom domain => MUST use VITE_API_BASE_URL
 *
 * Logged OUT: Django may 302 redirect /api/me/ -> /accounts/login/...
 * fetch() follows and returns HTML. We treat non-JSON as "unauth".
 *
 * Logout:
 * - From Pages, POST logout is CSRF/cookie-tricky; use top-level GET navigation to backend.
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

  if (isRailwayHost(hostname)) return "";
  if (isLocalHostHost(hostname)) return "";
  if (isDeployedFrontendHost(hostname)) return ENV_API_BASE || "";
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

function injectAppCss() {
  // Small “glue” layer so React matches your brand.css tokens
  const id = "inet-app-css";
  if (document.getElementById(id)) return;

  const css = `
  :root{
    /* expect these from ./brand/brand.css but keep safe fallbacks */
    --bg: var(--bg, #f8fafc);
    --surface: var(--surface, #ffffff);
    --surface-alt: var(--surface-alt, #f1f5f9);
    --border: var(--border, #e2e8f0);
    --text: var(--text, #0f172a);
    --muted: var(--muted, #475569);
    --primary: var(--primary, #1e4f7a);
    --primary-soft: var(--primary-soft, #e6f0f8);
    --warn: var(--warn, #b45309);
    --error: var(--error, #b91c1c);
    --radius: var(--radius, 14px);
    --shadow: var(--shadow, 0 20px 40px rgba(15, 23, 42, 0.08));
  }

  .inet-page{
    min-height: 100vh;
    background:
      radial-gradient(1200px 600px at 10% -10%, rgba(30,79,122,.08), transparent 60%),
      radial-gradient(900px 500px at 90% 0%, rgba(30,79,122,.06), transparent 55%),
      var(--bg);
    color: var(--text);
    font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
  }

  .inet-topbar{
    position: sticky;
    top: 0;
    z-index: 50;
    background: rgba(255,255,255,.88);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid var(--border);
  }
  .inet-topbar-inner{
    max-width: 1100px;
    margin: 0 auto;
    padding: 14px 18px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }

  .inet-brand{
    display:flex;
    align-items:center;
    gap: 12px;
    min-width: 220px;
  }
  .inet-logo{
    height: 30px;
    width: auto;
    display:block;
  }
  .inet-title{
    font-size: 16px;
    font-weight: 900;
    letter-spacing: .2px;
    color: var(--primary);
    line-height: 1.1;
  }
  .inet-subtitle{
    font-size: 12px;
    color: var(--muted);
    margin-top: 2px;
  }

  .inet-nav{
    display:flex;
    align-items:center;
    gap: 12px;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .inet-linkbtn{
    appearance:none;
    border: 1px solid transparent;
    background: transparent;
    color: var(--primary);
    font-weight: 700;
    font-size: 13px;
    cursor: pointer;
    padding: 8px 10px;
    border-radius: 10px;
    text-decoration: none;
    line-height: 1;
  }
  .inet-linkbtn:hover{
    background: var(--primary-soft);
    border-color: rgba(30,79,122,.15);
  }
  .inet-linkbtn.active{
    background: var(--primary-soft);
    border-color: rgba(30,79,122,.2);
  }

  .inet-chip{
    font-size: 12px;
    color: var(--muted);
    border: 1px solid var(--border);
    background: rgba(255,255,255,.7);
    padding: 6px 10px;
    border-radius: 999px;
  }

  .inet-container{
    max-width: 1100px;
    margin: 0 auto;
    padding: 18px;
  }

  .inet-h2{
    margin: 8px 0 14px;
    font-size: 18px;
    font-weight: 900;
    letter-spacing: .2px;
    color: var(--text);
  }

  .inet-grid{
    display:grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 14px;
  }

  .inet-card{
    border: 1px solid var(--border);
    background: var(--surface);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 16px;
  }

  .inet-card.clickable{ cursor: pointer; }
  .inet-card-title{
    font-size: 13px;
    font-weight: 800;
    color: var(--muted);
    margin-bottom: 10px;
    letter-spacing: .2px;
    text-transform: uppercase;
  }

  .inet-big{
    font-size: 30px;
    font-weight: 900;
    color: var(--primary);
    line-height: 1.1;
  }
  .inet-smallmuted{ color: var(--muted); font-size: 13px; }

  .inet-row{
    display:flex;
    align-items:center;
    justify-content: space-between;
    gap: 10px;
    flex-wrap: wrap;
  }

  .inet-pill{
    display:inline-flex;
    align-items:center;
    gap: 6px;
    padding: 5px 10px;
    border-radius: 999px;
    border: 1px solid var(--border);
    background: var(--surface-alt);
    color: var(--muted);
    font-size: 12px;
    font-weight: 700;
  }

  .inet-btn{
    appearance:none;
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 13px;
    font-weight: 800;
    cursor: pointer;
    border: 1px solid var(--border);
    background: var(--surface-alt);
    color: var(--text);
  }
  .inet-btn.primary{
    background: var(--primary);
    color: #fff;
    border-color: var(--primary);
  }
  .inet-btn.primary:hover{ filter: brightness(1.05); }

  .inet-btn.ghost{
    background: transparent;
  }
  .inet-btn:disabled{
    opacity: .6;
    cursor: not-allowed;
  }

  .inet-error{
    color: var(--warn);
    font-size: 13px;
    margin-bottom: 10px;
    font-weight: 700;
  }

  .inet-list{
    display:grid;
    gap: 10px;
    margin-top: 10px;
  }

  .inet-item{
    border: 1px solid var(--border);
    background: var(--surface);
    border-radius: 12px;
    padding: 12px;
  }

  .inet-item-title{
    font-weight: 900;
    color: var(--text);
  }
  .inet-item-meta{
    margin-top: 6px;
    display:flex;
    gap: 8px;
    flex-wrap: wrap;
    align-items:center;
  }

  .inet-actions{
    display:flex;
    gap: 10px;
    align-items:center;
    flex-wrap: wrap;
  }

  .inet-slim{
    padding: 8px 12px;
    font-size: 13px;
    border-radius: 10px;
  }

  .inet-note{
    font-size: 12px;
    color: var(--muted);
    margin-top: 10px;
  }

  /* auth screens */
  .inet-center{
    min-height: 100vh;
    display:grid;
    place-items:center;
    padding: 32px 16px;
  }
  .inet-authcard{
    width: min(520px, 100%);
    border: 1px solid var(--border);
    background: var(--surface);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 24px;
  }
  .inet-auth-title{
    font-size: 18px;
    font-weight: 900;
    color: var(--primary);
    margin: 0 0 6px;
  }
  .inet-auth-muted{ color: var(--muted); margin: 0 0 14px; }
  `;

  const style = document.createElement("style");
  style.id = id;
  style.textContent = css;
  document.head.appendChild(style);
}

function Card({ title, children, onClick, clickable }) {
  return (
    <div
      className={`inet-card ${clickable ? "clickable" : ""}`}
      onClick={onClick}
      role={clickable ? "button" : undefined}
      tabIndex={clickable ? 0 : undefined}
    >
      <div className="inet-card-title">{title}</div>
      {children}
    </div>
  );
}

function Pill({ children }) {
  return <span className="inet-pill">{children}</span>;
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

  // inject CSS once
  useEffect(() => {
    injectAppCss();
  }, []);

  // ---- boot auth ----
  useEffect(() => {
    (async () => {
      const hostname = window.location.hostname;

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

  // ---- actions ----
  async function startAssignment(a) {
    try {
      setBusyId(a.id);

      const r = await apiFetch(`/api/assignments/${a.id}/start/`, {
        method: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
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

  // ---- UI states ----
  if (status === "loading") {
    return <div className="inet-page"><div className="inet-container">Loading…</div></div>;
  }

  if (status === "nobackend") {
    return (
      <div className="inet-page">
        <div className="inet-center">
          <div className="inet-authcard">
            <h1 className="inet-auth-title">IntegraNet Training Portal</h1>
            <p className="inet-auth-muted">
              Backend is not connected. This site is running as a static preview on Cloudflare Pages.
            </p>
            <p className="inet-note">
              Set <code>VITE_API_BASE_URL</code> in Cloudflare Pages to your Django backend URL (example:
              {" "} <code>https://web-production-4c59f.up.railway.app</code>).
            </p>
            <div className="inet-note">
              API Base: <code>{API_BASE || "(same-origin)"}</code>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (status === "unauth") {
    const loginUrl = backendUrl("/accounts/login/?next=/app/");
    return (
      <div className="inet-page">
        <div className="inet-center">
          <div className="inet-authcard">
            <h1 className="inet-auth-title">IntegraNet Training Portal</h1>
            <p className="inet-auth-muted">You’re not logged in.</p>

            <a className="inet-btn primary" href={loginUrl} style={{ display: "inline-block" }}>
              Login
            </a>

            <div className="inet-note">
              API Base: <code>{API_BASE || "(same-origin)"}</code>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="inet-page">
        <div className="inet-center">
          <div className="inet-authcard">
            <h1 className="inet-auth-title">IntegraNet Training Portal</h1>
            <p className="inet-auth-muted">Couldn’t load your account.</p>
            <p className="inet-note">
              If this is running on Cloudflare Pages, make sure <code>VITE_API_BASE_URL</code> is set and the backend is reachable.
            </p>
            <div className="inet-note">
              API Base: <code>{API_BASE || "(same-origin)"}</code>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const logoutUrl = backendUrl(`/accounts/logout/?next=${encodeURIComponent(window.location.href)}`);

  const fullName =
    ((me?.first_name || me?.username || "User") + " " + (me?.last_name || "")).trim();

  return (
    <div className="inet-page">
      <header className="inet-topbar">
        <div className="inet-topbar-inner">
          <div className="inet-brand">
            {/* put your Pages/React logo here (public/...) if you want it in SPA */}
            <img className="inet-logo" src="/branding/integra_logo.png" alt="IntegraNet Health" />
            <div>
              <div className="inet-title">IntegraNet Training Portal</div>
              <div className="inet-subtitle">Compliance & Annual Training</div>
            </div>
          </div>

          <nav className="inet-nav">
            <button
              className={`inet-linkbtn ${page === "dashboard" ? "active" : ""}`}
              onClick={() => setPage("dashboard")}
            >
              Dashboard
            </button>

            <button
              className={`inet-linkbtn ${page === "courses" ? "active" : ""}`}
              onClick={() => {
                setPage("courses");
                if (coursesStatus === "idle") loadCourses();
              }}
            >
              Courses
            </button>

            <span className="inet-chip">{fullName}</span>

            {(me?.is_staff || me?.is_superuser) && (
              <a className="inet-linkbtn" href={backendUrl("/admin/")}>
                Admin
              </a>
            )}

            <a className="inet-linkbtn" href={logoutUrl}>
              Logout
            </a>
          </nav>
        </div>
      </header>

      <main className="inet-container">
        {page === "dashboard" && (
          <>
            <h2 className="inet-h2">Dashboard</h2>

            {assignStatus === "error" && (
              <div className="inet-error">
                Couldn’t load assignments. {assignError ? `(${assignError})` : ""}
              </div>
            )}

            <div className="inet-grid">
              <Card title="Assigned" clickable onClick={() => setAssignView("assigned")}>
                <div className="inet-big">{assignStatus === "loading" ? "…" : counts.assigned}</div>
                <div className="inet-smallmuted">Not started yet</div>
              </Card>

              <Card title="In Progress" clickable onClick={() => setAssignView("inprogress")}>
                <div className="inet-big">{assignStatus === "loading" ? "…" : counts.inProgress}</div>
                <div className="inet-smallmuted">Started</div>
              </Card>

              <Card title="Completed" clickable onClick={() => setAssignView("completed")}>
                <div className="inet-big">{assignStatus === "loading" ? "…" : counts.completed}</div>
                <div className="inet-smallmuted">Finished</div>
              </Card>
            </div>

            <div style={{ height: 14 }} />

            <div className="inet-card">
              <div className="inet-card-title">My Assignments</div>

              <div className="inet-row" style={{ marginBottom: 10 }}>
                <Pill>View: {assignView === "all" ? "All" : statusLabel(assignView.toUpperCase())}</Pill>

                <div className="inet-actions">
                  <button className="inet-btn ghost inet-slim" onClick={() => setAssignView("all")}>
                    Show all
                  </button>
                  <button className="inet-btn ghost inet-slim" onClick={loadAssignments}>
                    Refresh
                  </button>
                </div>
              </div>

              {assignStatus === "loading" && <div className="inet-note">Loading…</div>}

              {assignStatus !== "loading" && filteredAssignments.length === 0 && (
                <div className="inet-note">No assignments in this view.</div>
              )}

              {filteredAssignments.length > 0 && (
                <div className="inet-list">
                  {filteredAssignments.map((a) => {
                    const title = a.course?.title || a.course_title || "Course";
                    const code = a.course?.code || a.course_code || "";
                    const version = a.course_version?.version || a.version || "";
                    const due = a.due_at || null;

                    const canStart = a.status === "ASSIGNED";
                    const canResume =
                      a.status === "IN_PROGRESS" || a.status === "COMPLETED" || a.status === "OVERDUE";

                    const certId = a.certificate_id || null;

                    return (
                      <div key={a.id} className="inet-item">
                        <div className="inet-row">
                          <div style={{ minWidth: 240 }}>
                            <div className="inet-item-title">
                              {title}{" "}
                              {code ? <span style={{ color: "var(--muted)", fontWeight: 700 }}>({code})</span> : null}
                            </div>

                            <div className="inet-item-meta">
                              <Pill>{statusLabel(a.status)}</Pill>
                              {version ? <Pill>v{version}</Pill> : null}
                              <Pill>Due: {fmtDate(due)}</Pill>
                            </div>
                          </div>

                          <div className="inet-actions">
                            {canStart && (
                              <button
                                className="inet-btn primary"
                                disabled={busyId === a.id}
                                onClick={() => startAssignment(a)}
                              >
                                {busyId === a.id ? "Starting…" : "Start"}
                              </button>
                            )}

                            {canResume && (
                              <button className="inet-btn" onClick={() => resumeAssignment(a)}>
                                {a.status === "COMPLETED" ? "View" : "Resume"}
                              </button>
                            )}

                            {a.status === "COMPLETED" && certId && (
                              <a
                                className="inet-btn"
                                href={backendUrl(`/audits/certificates/${certId}/download/`)}
                                target="_blank"
                                rel="noreferrer"
                              >
                                Certificate
                              </a>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </>
        )}

        {page === "courses" && (
          <>
            <h2 className="inet-h2">Courses</h2>

            {coursesStatus === "loading" && <p className="inet-note">Loading courses…</p>}
            {coursesStatus === "error" && <p className="inet-note">Couldn’t load courses.</p>}
            {coursesStatus === "ready" && courses.length === 0 && <p className="inet-note">No courses available.</p>}

            {coursesStatus === "ready" && courses.length > 0 && (
              <div className="inet-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))" }}>
                {courses.map((c) => (
                  <div key={c.id} className="inet-card">
                    <div className="inet-card-title">{c.title} ({c.code})</div>

                    {c.description ? (
                      <div className="inet-smallmuted" style={{ marginBottom: 10 }}>{c.description}</div>
                    ) : (
                      <div className="inet-note" style={{ marginBottom: 10 }}>No description</div>
                    )}

                    {c.published_version ? (
                      <div className="inet-smallmuted">
                        Version <b>{c.published_version.version}</b> · Pass score{" "}
                        <b>{c.published_version.pass_score}%</b>
                      </div>
                    ) : (
                      <div className="inet-error" style={{ margin: 0 }}>No published version yet</div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
