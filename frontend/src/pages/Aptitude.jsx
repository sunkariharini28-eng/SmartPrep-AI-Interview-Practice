import React, { useEffect, useRef, useState } from "react";
import { api } from "../api.js";

const fmt = (s) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

export default function Aptitude() {
  const [sections, setSections] = useState([]);
  const [cfg, setCfg] = useState({ section: "Quantitative", n: 10, minutes: 10 });
  const [qs, setQs] = useState(null);
  const [ans, setAns] = useState({});
  const [left, setLeft] = useState(0);
  const [res, setRes] = useState(null);
  const [err, setErr] = useState("");
  const startedAt = useRef(0);
  const submitted = useRef(false);

  useEffect(() => { api.get("/aptitude/sections").then(setSections).catch((e) => setErr(e.message)); }, []);

  useEffect(() => {
    if (!qs || res) return;
    if (left <= 0) { submit(); return; }
    const t = setTimeout(() => setLeft((l) => l - 1), 1000);
    return () => clearTimeout(t);
  }, [left, qs, res]);

  async function start() {
    setErr("");
    try {
      const q = await api.get(`/aptitude/questions?section=${encodeURIComponent(cfg.section)}&n=${cfg.n}`);
      setQs(q); setAns({}); setRes(null); submitted.current = false;
      setLeft(Number(cfg.minutes) * 60); startedAt.current = Date.now();
    } catch (e) { setErr(e.message); }
  }
  async function submit() {
    if (submitted.current) return;
    submitted.current = true;
    try {
      setRes(await api.post("/aptitude/submit", {
        section: cfg.section, answers: ans, question_ids: qs.map((q) => q.id),
        duration_seconds: Math.round((Date.now() - startedAt.current) / 1000),
      }));
    } catch (e) { setErr(e.message); submitted.current = false; }
  }

  if (res) {
    return (
      <div>
        <h2>{res.section} results</h2>
        <div className="card"><div className="stat">{res.correct}/{res.total} ({res.score_pct}%)</div>
          <button className="btn primary" style={{ marginTop: ".8rem" }} onClick={() => { setQs(null); setRes(null); }}>Take another test</button></div>
        {res.details.map((d, i) => (
          <div className="card" key={d.id}>
            <strong>{i + 1}. {d.text}</strong>
            {d.options.map((o, k) => <div key={k} className={`btn opt ${k === d.correct_index ? "ok" : k === d.chosen ? "no" : ""}`} style={{ cursor: "default" }}>{o}</div>)}
            <p className="small"><span className={`badge ${d.is_correct ? "good" : "bad"}`}>{d.chosen == null ? "Unanswered" : d.is_correct ? "Correct" : "Incorrect"}</span> {d.explanation}</p>
          </div>
        ))}
      </div>
    );
  }
  if (qs) {
    return (
      <div>
        <div className="row between"><h2>{cfg.section}</h2>
          <span className={`badge ${left < 60 ? "bad" : ""}`} style={{ fontSize: "1.1rem" }}>⏱ {fmt(left)}</span></div>
        {err && <div className="error">{err}</div>}
        {qs.map((q, i) => (
          <div className="card" key={q.id}>
            <strong>{i + 1}. {q.text}</strong>
            {q.options.map((o, k) => <button key={k} className={`btn opt ${ans[q.id] === k ? "sel" : ""}`} onClick={() => setAns({ ...ans, [q.id]: k })}>{o}</button>)}
          </div>
        ))}
        <button className="btn primary" onClick={submit}>Submit test ({Object.keys(ans).length}/{qs.length} answered)</button>
      </div>
    );
  }
  return (
    <div>
      <h2>Aptitude Practice</h2>
      <div className="card" style={{ maxWidth: 520 }}>
        <label>Section</label>
        <select value={cfg.section} onChange={(e) => setCfg({ ...cfg, section: e.target.value })}>
          {sections.map((s) => <option key={s.name} value={s.name}>{s.name} ({s.available} questions)</option>)}</select>
        <div className="row"><div style={{ flex: 1 }}><label>Questions</label>
          <input type="number" min={1} max={30} value={cfg.n} onChange={(e) => setCfg({ ...cfg, n: e.target.value })} /></div>
          <div style={{ flex: 1 }}><label>Time (minutes)</label>
            <input type="number" min={1} max={120} value={cfg.minutes} onChange={(e) => setCfg({ ...cfg, minutes: e.target.value })} /></div></div>
        {err && <div className="error">{err}</div>}
        <button className="btn primary" style={{ marginTop: "1rem" }} onClick={start}>Start timed test</button>
      </div>
    </div>
  );
}
