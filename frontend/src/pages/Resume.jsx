import React, { useEffect, useState } from "react";
import { api } from "../api.js";

const List = ({ title, items }) => items?.length ? <div><h4>{title}</h4><ul>{items.map((x, i) => <li key={i}>{typeof x === "string" ? x : JSON.stringify(x)}</li>)}</ul></div> : null;

export default function Resume() {
  const [list, setList] = useState([]);
  const [sel, setSel] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [role, setRole] = useState("");
  const [jd, setJd] = useState("");
  const [match, setMatch] = useState(null);

  const load = () => api.get("/resume").then((r) => { setList(r); if (!sel && r.length) setSel(r[0]); }).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);

  async function upload(e) {
    const f = e.target.files[0];
    if (!f) return;
    setErr(""); setBusy(true);
    try { const r = await api.upload("/resume/upload", f); setList([r, ...list]); setSel(r); setMatch(null); }
    catch (ex) { setErr(ex.message); }
    setBusy(false); e.target.value = "";
  }
  async function doMatch() {
    setErr(""); setBusy(true);
    try { setMatch(await api.post(`/resume/${sel.id}/match`, { role, job_description: jd })); } catch (ex) { setErr(ex.message); }
    setBusy(false);
  }
  async function remove(r) {
    if (!confirm(`Delete ${r.filename}?`)) return;
    await api.del(`/resume/${r.id}`);
    const rest = list.filter((x) => x.id !== r.id);
    setList(rest); setSel(rest[0] || null); setMatch(null);
  }
  const a = sel?.analysis;

  return (
    <div>
      <h2>Resume Analyzer</h2>
      <div className="card">
        <label>Upload resume (PDF or DOCX, max 5 MB)</label>
        <input type="file" accept=".pdf,.docx" onChange={upload} disabled={busy} />
        {busy && <p className="muted">Analysing… this can take up to a minute.</p>}
        {err && <div className="error">{err}</div>}
        {list.length > 1 && <div className="tabs" style={{ marginTop: ".8rem" }}>
          {list.map((r) => <button key={r.id} className={`btn sm ${sel?.id === r.id ? "active" : ""}`} onClick={() => { setSel(r); setMatch(null); }}>{r.filename}</button>)}</div>}
      </div>
      {a && (
        <>
          <div className="card">
            <div className="row between"><h3>{sel.filename}</h3>
              <div className="row">{a.ats_score != null && <span className="badge">ATS-readiness {a.ats_score}/100</span>}
                <button className="btn sm danger" onClick={() => remove(sel)}>Delete</button></div></div>
            <div className="grid g2">
              <List title="Skills" items={a.skills} />
              <List title="Education" items={a.education?.map((e) => `${e.degree || ""} · ${e.institution || ""} ${e.year || ""}`)} />
              <List title="Projects" items={a.projects?.map((p) => `${p.name}: ${p.summary}`)} />
              <List title="Strengths" items={a.strengths} />
              <List title="Weaknesses" items={a.weaknesses} />
              <List title="Improvement suggestions" items={a.improvements} />
            </div>
            <List title="Questions you may be asked" items={a.interview_questions} />
          </div>
          <div className="card">
            <h3>Role match score</h3>
            <label>Target role</label><input value={role} onChange={(e) => setRole(e.target.value)} placeholder="e.g. Backend Developer" />
            <label>Job description (optional)</label><textarea value={jd} onChange={(e) => setJd(e.target.value)} />
            <button className="btn primary" style={{ marginTop: ".8rem" }} disabled={busy || role.trim().length < 2} onClick={doMatch}>Calculate match</button>
            {match && <div style={{ marginTop: "1rem" }}>
              <div className="stat">{Math.round(match.match_score)}%</div><p>{match.summary}</p>
              <div className="grid g2"><List title="Matched skills" items={match.matched_skills} /><List title="Missing skills" items={match.missing_skills} /></div>
              <List title="Suggestions" items={match.suggestions} /></div>}
          </div>
        </>
      )}
    </div>
  );
}
