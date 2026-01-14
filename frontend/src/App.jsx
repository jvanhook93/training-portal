import { useEffect, useState } from "react";

function Card({ title, children }) {
  return (
    <div style={{
      border: "1px solid #334155",
      background: "rgba(15,23,42,.75)",
      borderRadius: 16,
      padding: 16
    }}>
      <div style={{ fontSize: 14, color: "#cbd5e1", marginBottom: 10 }}>{title}</div>
      {children}
    </div>
  );
}

export default function App() {
  const [me, setMe] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | authed | unauth | error
  const [page, setPage] = useState("dashboard");   // dashboard | courses

  const [courses, setCourses] = useState([]);
  const [coursesStatus, setCoursesStatus] = useState("idle"); // idle | loading | ready | error

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch("/api/me/", { credentials: "include" });

        if (r.status === 401) { setStatus("unauth"); return; }
        if (!r.ok) { setStatus("error"); return; }

        const data = await r.json();
        setMe(data);
        setStatus("authed");
      } catch {
        setStatus("error");
      }
    })();
  }, []);

  async function loadCourses() {
    try {
      setCoursesStatus("loading");
      const r = await fetch("/api/courses/", { credentials: "include" });
      if (!r.ok) throw new Error("bad response");
      const data = await r.json();
      setCourses(data.results || []);
      setCoursesStatus("ready");
    } catch {
      setCoursesStatus("error");
    }
  }

  if (status === "loading") {
    return <div style={{ padding: 24, fontFamily: "system-ui" }}>Loading…</div>;
  }

  if (status === "unauth") {
    return (
      <div style={{ padding: 24, fontFamily: "system-ui" }}>
        <h1>Training Portal</h1>
        <p>You’re not logged in.</p>
        <a href="/accounts/login/" style={{ color: "#93c5fd" }}>Go to Login</a>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div style={{ padding: 24, fontFamily: "system-ui" }}>
        <h1>Training Portal</h1>
        <p>Couldn’t load your account.</p>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", background: "#0b0f19", color: "#eef2ff", fontFamily: "system-ui" }}>
      {/* Top bar */}
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "14px 18px",
        borderBottom: "1px solid #334155",
        background: "rgba(2,6,23,.75)",
        position: "sticky",
        top: 0
      }}>
        <div style={{ fontWeight: 700 }}>Training Portal</div>

        <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
          <button
            onClick={() => setPage("dashboard")}
            style={{
              background: "transparent",
              border: "none",
              color: page === "dashboard" ? "#93c5fd" : "#e2e8f0",
              cursor: "pointer"
            }}>
            Dashboard
          </button>

          <button
            onClick={() => { setPage("courses"); if (coursesStatus === "idle") loadCourses(); }}
            style={{
              background: "transparent",
              border: "none",
              color: page === "courses" ? "#93c5fd" : "#e2e8f0",
              cursor: "pointer"
            }}>
            Courses
          </button>

          <div style={{ width: 1, height: 18, background: "#334155" }} />

          <div style={{ fontSize: 13, color: "#cbd5e1" }}>
            {me.first_name || me.username} {me.last_name || ""}
          </div>

          <a href="/accounts/logout/" style={{ color: "#93c5fd", textDecoration: "none", fontSize: 13 }}>
            Logout
          </a>
        </div>
      </div>

      {/* Content */}
      <div style={{ padding: 18, maxWidth: 1100, margin: "0 auto" }}>
        {page === "dashboard" && (
          <>
            <h2 style={{ margin: "10px 0 16px" }}>Dashboard</h2>

            <div style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
              gap: 14
            }}>
              <Card title="My Courses">
                <div style={{ fontSize: 28, fontWeight: 700 }}>0</div>
                <div style={{ color: "#94a3b8", fontSize: 13 }}>Assigned to you</div>
              </Card>

              <Card title="In Progress">
                <div style={{ fontSize: 28, fontWeight: 700 }}>0</div>
                <div style={{ color: "#94a3b8", fontSize: 13 }}>Currently working</div>
              </Card>

              <Card title="Completed">
                <div style={{ fontSize: 28, fontWeight: 700 }}>0</div>
                <div style={{ color: "#94a3b8", fontSize: 13 }}>Finished courses</div>
              </Card>
            </div>
          </>
        )}

        {page === "courses" && (
          <>
            <h2 style={{ margin: "10px 0 16px" }}>Courses</h2>

            {coursesStatus === "loading" && <p>Loading courses…</p>}
            {coursesStatus === "error" && <p>Couldn’t load courses.</p>}
            {coursesStatus === "ready" && courses.length === 0 && <p>No courses available.</p>}

            {coursesStatus === "ready" && courses.length > 0 && (
              <div style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
                gap: 14
              }}>
                {courses.map((c) => (
                  <Card key={c.id} title={`${c.title} (${c.code})`}>
                    {c.description ? (
                      <div style={{ fontSize: 13, color: "#cbd5e1", marginBottom: 10 }}>
                        {c.description}
                      </div>
                    ) : (
                      <div style={{ fontSize: 13, color: "#94a3b8", marginBottom: 10 }}>
                        No description
                      </div>
                    )}

                    {c.published_version ? (
                      <div style={{ fontSize: 13 }}>
                        Version <b>{c.published_version.version}</b> · Pass score {c.published_version.pass_score}%
                      </div>
                    ) : (
                      <div style={{ fontSize: 13, color: "#fbbf24" }}>
                        No published version yet
                      </div>
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
