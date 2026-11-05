import React, { useEffect, useState } from "react";
import { api } from "../api.js";

const L = ({ t, items }) => items?.length ? <div><h4>{t}</h4><ul>{items.map((x, i) => <li key={i}>{typeof x === "string" ? x : JSON.stringify(x)}</li>)}</ul></div> : null;

export default function Coach() {
  const [role, setRole] = useState("");
  const [weeks, setWeeks] = useState(8);
  const [plans, setPlans] = useState([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => { api.get("/coach/plans").then(setPlans).catch((e) => setErr(e.message)); }, []);

  async function gen() {
    setErr(""); setBusy(true);
    try { const p = await api.post("/coach/plan", { target_role: role, weeks: Number(weeks) }); setPlans([p, ...plans]); }
    catch (e) { setErr(e.message); }
    setBusy(false);
  }
  const p = plans[0]?.content;

  return (
    <div>
      <h2>AI Career Coach</h2>
      <div className="card" style={{ maxWidth: 640 }}>
        <p className="muted">Your plan uses your profile skills, latest resume and practice results.</p>
        <label>Target role (optional)</label><input value={role} onChange={(e) => setRole(e.target.value)} placeholder="e.g. Full-stack Developer" />
        <label>Plan length (weeks)</label><input type="number" min={2} max={26} value={weeks} onChange={(e) => setWeeks(e.target.value)} />
        {err && <div className="error">{err}</div>}
        <button className="btn primary" style={{ marginTop: "1rem" }} onClick={gen} disabled={busy}>{busy ? "Building your plan…" : "Generate my plan"}</button>
      </div>
      {p && (
        <>
          <div className="card"><h3>Plan for {plans[0].target_role}</h3>
            <div className="grid g2">
              <div><h4>Suggested roles</h4><ul>{p.suggested_roles?.map((r, i) => <li key={i}><strong>{r.role}</strong>: {r.reason}</li>)}</ul></div>
              <L t="Missing skills" items={p.missing_skills} />
              <L t="Daily practice tasks" items={p.daily_tasks} />
              <L t="Interview preparation plan" items={p.interview_prep_plan} />
            </div></div>
          <div className="card"><h3>Learning roadmap</h3>
            {p.roadmap?.map((w, i) => <div key={i} style={{ marginBottom: ".8rem" }}><strong>Week {w.week}: {w.focus}</strong><ul>{w.tasks?.map((t, k) => <li key={k}>{t}</li>)}</ul></div>)}</div>
          <div className="card"><h3>Project ideas</h3>
            {p.project_ideas?.map((x, i) => <div key={i}><strong>{x.name}</strong> <span className="muted small">{x.skills?.join(", ")}</span><p>{x.description}</p></div>)}</div>
        </>
      )}
    </div>
  );
}
