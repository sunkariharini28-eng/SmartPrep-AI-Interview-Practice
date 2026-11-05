import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";

const Stat = ({ label, value, suffix = "" }) => (
  <div className="card"><div className="muted small">{label}</div>
    <div className="stat">{value === null || value === undefined ? "–" : value + suffix}</div></div>
);

export default function Dashboard() {
  const { user } = useAuth();
  const [d, setD] = useState(null);
  const [hist, setHist] = useState([]);
  const [err, setErr] = useState("");
  useEffect(() => {
    api.get("/analytics/summary").then(setD).catch((e) => setErr(e.message));
    api.get("/interview").then(setHist).catch(() => {});
  }, []);
  if (err) return <div className="error">{err}</div>;
  if (!d) return <div className="muted">Loading…</div>;
  const empty = d.total_interviews === 0 && !d.coding_score_pct && !d.aptitude_score_pct;
  return (
    <div>
      <h2>Hi {user.name.split(" ")[0]}, here's your progress</h2>
      <div className="row" style={{ marginBottom: "1rem" }}>
        <Link className="btn primary" to="/interview">Start interview</Link>
        <Link className="btn" to="/coding">Solve a problem</Link>
        <Link className="btn" to="/aptitude">Take aptitude test</Link>
      </div>
      {empty && <div className="notice">No practice data yet. Finish an interview, coding problem or aptitude test and your analytics will appear here.</div>}
      <div className="grid g4">
        <Stat label="Interviews completed" value={d.total_interviews} />
        <Stat label="Average interview score" value={d.avg_interview_score} suffix="/10" />
        <Stat label="Technical score" value={d.technical_score} suffix="/10" />
        <Stat label="Communication score" value={d.communication_score} suffix="/10" />
        <Stat label="Coding score" value={d.coding_score_pct} suffix="%" />
        <Stat label="Aptitude score" value={d.aptitude_score_pct} suffix="%" />
        <Stat label="Problems solved" value={d.problems_solved} />
      </div>
      <div className="grid g2">
        <div className="card">
          <h3>Interview score trend</h3>
          <div style={{ height: 240 }}>
            <ResponsiveContainer><LineChart data={d.progress}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} /><XAxis dataKey="date" /><YAxis domain={[0, 10]} /><Tooltip /><Legend />
              <Line type="monotone" dataKey="score" name="Score" stroke="#4f46e5" strokeWidth={2} />
              <Line type="monotone" dataKey="communication" name="Communication" stroke="#16a34a" strokeWidth={2} />
            </LineChart></ResponsiveContainer>
          </div>
        </div>
        <div className="card">
          <h3>Skill overview (%)</h3>
          <div style={{ height: 240 }}>
            <ResponsiveContainer><BarChart data={d.skills}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} /><XAxis dataKey="name" /><YAxis domain={[0, 100]} /><Tooltip />
              <Bar dataKey="value" fill="#7c3aed" radius={[6, 6, 0, 0]} />
            </BarChart></ResponsiveContainer>
          </div>
        </div>
      </div>
      <div className="grid g2">
        <div className="card"><h3>Weak topics</h3>
          {d.weak_topics.length ? <ul>{d.weak_topics.map((t) => <li key={t.topic}>{t.topic} <span className="badge bad">{t.avg_score}/10</span></li>)}</ul> : <p className="muted">None yet.</p>}
        </div>
        <div className="card"><h3>Strong topics</h3>
          {d.strong_topics.length ? <ul>{d.strong_topics.map((t) => <li key={t.topic}>{t.topic} <span className="badge good">{t.avg_score}/10</span></li>)}</ul> : <p className="muted">None yet.</p>}
        </div>
      </div>
      <div className="card"><h3>Interview history</h3>
        {hist.length ? <table><thead><tr><th>Date</th><th>Category</th><th>Mode</th><th>Status</th><th>Score</th></tr></thead><tbody>
          {hist.map((h) => <tr key={h.id}><td>{h.created_at.slice(0, 10)}</td><td>{h.category}</td><td>{h.mode}</td><td>{h.status}</td>
            <td>{h.avg_score ?? "–"}</td></tr>)}</tbody></table> : <p className="muted">No interviews yet.</p>}
      </div>
    </div>
  );
}
