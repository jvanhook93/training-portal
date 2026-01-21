import { useEffect, useMemo, useState } from "react";


/**
 * ENV
 * - On Cloudflare Pages: set VITE_API_BASE_URL = https://<your-railway-app>
 * - Local dev: can be blank if you proxy or serve frontend from Django
 */
const RAW_API_BASE = import.meta.env.VITE_API_BASE_URL || "";
const API_BASE = RAW_API_BASE.replace(/\/+$/, ""); // trim trailing slashes

const COLORS = {
  bg: "#0b0f19",
  surface: "rgba(15,23,42,.75)",
  topbar: "rgba(2,6,23,.75)",
  border: "#334155",
  text: "#eef2ff",
  muted: "#94a3b8",
  link: "#93c5fd",
  warn: "#fbbf24",
};

function isLocalHost() {
  const h = window.location.hostname;
  return h === "localhost" || h === "127.0.0.1";
}

function isDeployedFrontendHost() {
  const h = window.location.hostname;
  return h.endsWith("pages.dev") || h.endsWith("integranethealth.com");
}

function joinUrl(base, path) {
  if (!base) return path;
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${base}${p}`;
}

function apiUrl(path) {
  // API endpoints live on Django backend
  return joinUrl(API_BASE, path);
}

function backendUrl(path) {
  // Django pages like /accounts/login/, /admin/, /training/...
  return joinUrl(API_BASE, path);
}

async function apiFetch(path, init = {}) {
  // cookie session auth
  return fetch(apiUrl(path), { credentials: "include", ...init });
}

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(";").shift();
  return null;
}

function Card({ title, children, onClick, clickable }) {
  return (
    <div
      onClick={onClick}
      role={clickable ? "button" : undefined}
      tabIndex={clickable ? 0 : undefined}
      style={{
        border: `1px solid ${COLORS.border}`,
        background: COLORS.surface,
        borderRadius: 16,
        padding: 16,
        cursor: clickable ? "pointer" : "default",
        userSelect: "none",
      }}
    >
      <div style={{ fontSize: 14, color: "#cbd5e1", marginBottom: 10 }}>
        {title}
      </div>
      {children}
    </div>
  );
}

function Pill({ children }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "2px 8px",
        borderRadius: 999,
        border: `1px solid ${COLORS.border}`,
        background: "rgba(255,255,255,.04)",
        color: "#cbd5e1",
        fontSize: 12,
      }}
    >
      {children}
    </span>
  );
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
      const requireApiBase = isDeployedFrontendHost() && !isLocalHost();

      // Only complain about missing API base on deployed frontend (Pages/custom domain)
      if (requireApiBase && !API_BASE) {
        setStatus("nobackend");
        return;
      }

      try {
        const r = await apiFetch("/api/me/");
        if (r.status === 401) {
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
      const r = await apiFetch("/api/courses/");
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
      const r = await apiFetch("/api/me/assignments/");
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

      // If you're deployed and missing backend, block it cleanly
      if (isDeployedFrontendHost() && !API_BASE) {
        throw new Error("Backend URL is not configured.");
      }

      // Ensure CSRF cookie exists
      await apiFetch("/api/csrf/");
      const csrf = getCookie("csrftoken");

      const r = await apiFetch(`/api/assignments/${a.id}/start/`, {
        method: "POST",
        headers: {
          "X-CSRFToken": csrf || "",
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
    return <div style={{ padding: 24, fontFamily: "system-ui" }}>Loading…</div>;
  }

  if (status === "nobackend") {
    return (
      <div
        style={{
          padding: 24,
          fontFamily: "system-ui",
          color: COLORS.text,
          background: COLORS.bg,
          minHeight: "100vh",
        }}
      >
        <h1>Training Portal</h1>
        <p style={{ color: COLORS.warn }}>
          Backend is not connected. This site is running as a static preview on Cloudflare Pages.
        </p>
        <p style={{ color: COLORS.muted, maxWidth: 700 }}>
          Set <code>VITE_API_BASE_URL</code> in Cloudflare Pages to your Django backend URL (example:{" "}
          <code>https://web-production-4c59f.up.railway.app</code>).
        </p>
      </div>
    );
  }

  if (status === "unauth") {
    // Login needs to occur on backend origin to establish session cookies
    const loginUrl = backendUrl("/accounts/login/?next=/app");
    return (
      <div
        style={{
          padding: 24,
          fontFamily: "system-ui",
          color: COLORS.text,
          background: COLORS.bg,
          minHeight: "100vh",
        }}
      >
        <h1 style={{ margin: "0 0 10px" }}>Training Portal</h1>
        <p style={{ margin: "0 0 16px", color: "#cbd5e1" }}>
          You’re not logged in. Login happens on the backend so your session cookie works.
        </p>

        <a
          href={loginUrl}
          style={{
            color: "#0b0f19",
            background: COLORS.link,
            textDecoration: "none",
            padding: "10px 14px",
            borderRadius: 12,
            fontWeight: 700,
            display: "inline-block",
          }}
        >
          Login
        </a>

        {API_BASE && (
          <div style={{ marginTop: 14, color: COLORS.muted, fontSize: 12 }}>
            Backend: <code>{API_BASE}</code>
          </div>
        )}
      </div>
    );
  }

  if (status === "error") {
    return (
      <div
        style={{
          padding: 24,
          fontFamily: "system-ui",
          color: COLORS.text,
          background: COLORS.bg,
          minHeight: "100vh",
        }}
      >
        <h1>Training Portal</h1>
        <p>Couldn’t load your account.</p>
        <p style={{ color: COLORS.muted }}>
          If this is running on Cloudflare Pages, make sure <code>VITE_API_BASE_URL</code> is set and the backend is reachable.
        </p>
      </div>
    );
  }

  // ---- main app ----
  return (
    <div style={{ minHeight: "100vh", background: COLORS.bg, color: COLORS.text, fontFamily: "system-ui" }}>
      {/* Top bar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "14px 18px",
          borderBottom: `1px solid ${COLORS.border}`,
          background: COLORS.topbar,
          position: "sticky",
          top: 0,
        }}
      >
        <div style={{ fontWeight: 700 }}>Training Portal</div>

        <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
          <button
            onClick={() => setPage("dashboard")}
            style={{
              background: "transparent",
              border: "none",
              color: page === "dashboard" ? COLORS.link : "#e2e8f0",
              cursor: "pointer",
            }}
          >
            Dashboard
          </button>

          <button
            onClick={() => {
              setPage("courses");
              if (coursesStatus === "idle") loadCourses();
            }}
            style={{
              background: "transparent",
              border: "none",
              color: page === "courses" ? COLORS.link : "#e2e8f0",
              cursor: "pointer",
            }}
          >
            Courses
          </button>

          <div style={{ width: 1, height: 18, background: COLORS.border }} />

          <div style={{ fontSize: 13, color: "#cbd5e1" }}>
            {(me?.first_name || me?.username || "User") + " " + (me?.last_name || "")}
          </div>

          {(me?.is_staff || me?.is_superuser) && (
            <a
              href={backendUrl("/admin/")}
              style={{
                color: COLORS.link,
                textDecoration: "none",
                fontSize: 13,
                border: `1px solid ${COLORS.border}`,
                padding: "6px 10px",
                borderRadius: 10,
                background: "rgba(255,255,255,.04)",
              }}
            >
              Admin
            </a>
          )}

          {/* Django logout is POST in many setups; include CSRF token */}
          <form method="POST" action={backendUrl("/accounts/logout/")} style={{ margin: 0 }}>
            <input type="hidden" name="csrfmiddlewaretoken" value={getCookie("csrftoken") || ""} />
            <button
              type="submit"
              style={{
                background: "transparent",
                border: "none",
                color: COLORS.link,
                cursor: "pointer",
                fontSize: 13,
                padding: 0,
              }}
            >
              Logout
            </button>
          </form>
        </div>
      </div>

      {/* Content */}
      <div style={{ padding: 18, maxWidth: 1100, margin: "0 auto" }}>
        {page === "dashboard" && (
          <>
            <h2 style={{ margin: "10px 0 16px" }}>Dashboard</h2>

            {assignStatus === "error" && (
              <div style={{ color: COLORS.warn, marginBottom: 12 }}>
                Couldn’t load assignments. {assignError ? `(${assignError})` : ""}
              </div>
            )}

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 14 }}>
              <Card title="Assigned" clickable onClick={() => setAssignView("assigned")}>
                <div style={{ fontSize: 28, fontWeight: 700 }}>{assignStatus === "loading" ? "…" : counts.assigned}</div>
                <div style={{ color: COLORS.muted, fontSize: 13 }}>Not started yet</div>
              </Card>

              <Card title="In Progress" clickable onClick={() => setAssignView("inprogress")}>
                <div style={{ fontSize: 28, fontWeight: 700 }}>{assignStatus === "loading" ? "…" : counts.inProgress}</div>
                <div style={{ color: COLORS.muted, fontSize: 13 }}>Started</div>
              </Card>

              <Card title="Completed" clickable onClick={() => setAssignView("completed")}>
                <div style={{ fontSize: 28, fontWeight: 700 }}>{assignStatus === "loading" ? "…" : counts.completed}</div>
                <div style={{ color: COLORS.muted, fontSize: 13 }}>Finished</div>
              </Card>
            </div>

            <div style={{ height: 14 }} />

            <Card title="My Assignments">
              <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 12 }}>
                <Pill>View: {assignView === "all" ? "All" : statusLabel(assignView.toUpperCase())}</Pill>

                <button
                  onClick={() => setAssignView("all")}
                  style={{
                    background: "transparent",
                    border: `1px solid ${COLORS.border}`,
                    color: "#e2e8f0",
                    borderRadius: 10,
                    padding: "6px 10px",
                    cursor: "pointer",
                    fontSize: 12,
                  }}
                >
                  Show all
                </button>

                <button
                  onClick={loadAssignments}
                  style={{
                    background: "transparent",
                    border: `1px solid ${COLORS.border}`,
                    color: "#e2e8f0",
                    borderRadius: 10,
                    padding: "6px 10px",
                    cursor: "pointer",
                    fontSize: 12,
                  }}
                >
                  Refresh
                </button>
              </div>

              {assignStatus === "loading" && <div style={{ color: COLORS.muted }}>Loading…</div>}

              {assignStatus !== "loading" && filteredAssignments.length === 0 && (
                <div style={{ color: COLORS.muted }}>No assignments in this view.</div>
              )}

              {filteredAssignments.length > 0 && (
                <div style={{ display: "grid", gap: 10 }}>
                  {filteredAssignments.map((a) => {
                    const title = a.course?.title || a.course_title || "Course";
                    const code = a.course?.code || a.course_code || "";
                    const version = a.course_version?.version || a.version || "";
                    const due = a.due_at || null;

                    const canStart = a.status === "ASSIGNED";
                    const canResume = a.status === "IN_PROGRESS" || a.status === "COMPLETED" || a.status === "OVERDUE";

                    return (
                      <div
                        key={a.id}
                        style={{
                          border: `1px solid ${COLORS.border}`,
                          borderRadius: 14,
                          padding: 12,
                          background: "rgba(255,255,255,.03)",
                          display: "flex",
                          justifyContent: "space-between",
                          gap: 12,
                          alignItems: "center",
                          flexWrap: "wrap",
                        }}
                      >
                        <div style={{ minWidth: 240 }}>
                          <div style={{ fontWeight: 650 }}>
                            {title}{" "}
                            {code ? <span style={{ color: COLORS.muted, fontWeight: 500 }}>({code})</span> : null}
                          </div>
                          <div style={{ marginTop: 4, display: "flex", gap: 8, flexWrap: "wrap" }}>
                            <Pill>{statusLabel(a.status)}</Pill>
                            {version ? <Pill>v{version}</Pill> : null}
                            <Pill>Due: {fmtDate(due)}</Pill>
                          </div>
                        </div>

                        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                          {canStart && (
                            <button
                              disabled={busyId === a.id}
                              onClick={() => startAssignment(a)}
                              style={{
                                border: `1px solid ${COLORS.border}`,
                                background: "#111827",
                                color: "#e2e8f0",
                                borderRadius: 12,
                                padding: "8px 12px",
                                cursor: busyId === a.id ? "not-allowed" : "pointer",
                                fontSize: 13,
                              }}
                            >
                              {busyId === a.id ? "Starting…" : "Start"}
                            </button>
                          )}

                          {canResume && (
                            <button
                              onClick={() => resumeAssignment(a)}
                              style={{
                                border: `1px solid ${COLORS.border}`,
                                background: "transparent",
                                color: COLORS.link,
                                borderRadius: 12,
                                padding: "8px 12px",
                                cursor: "pointer",
                                fontSize: 13,
                              }}
                            >
                              {a.status === "COMPLETED" ? "View" : "Resume"}
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </Card>
          </>
        )}

        {page === "courses" && (
          <>
            <h2 style={{ margin: "10px 0 16px" }}>Courses</h2>

            {coursesStatus === "loading" && <p>Loading courses…</p>}
            {coursesStatus === "error" && <p>Couldn’t load courses.</p>}
            {coursesStatus === "ready" && courses.length === 0 && <p>No courses available.</p>}

            {coursesStatus === "ready" && courses.length > 0 && (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 14 }}>
                {courses.map((c) => (
                  <Card key={c.id} title={`${c.title} (${c.code})`}>
                    {c.description ? (
                      <div style={{ fontSize: 13, color: "#cbd5e1", marginBottom: 10 }}>{c.description}</div>
                    ) : (
                      <div style={{ fontSize: 13, color: COLORS.muted, marginBottom: 10 }}>No description</div>
                    )}

                    {c.published_version ? (
                      <div style={{ fontSize: 13 }}>
                        Version <b>{c.published_version.version}</b> · Pass score {c.published_version.pass_score}%
                      </div>
                    ) : (
                      <div style={{ fontSize: 13, color: COLORS.warn }}>No published version yet</div>
                    )}
                  </Card>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
