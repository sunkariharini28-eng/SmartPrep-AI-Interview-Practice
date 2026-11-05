import React, { useEffect, useState } from "react";
import { api } from "../api.js";

const BLANK = { kind: "aptitude", category: "Quantitative", difficulty: "medium", title: "", text: "", options: "", answer_index: 0, explanation: "", test_cases: "" };

export default function Admin() {
  const [tab, setTab] = useState("stats");
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [qs, setQs] = useState([]);
  const [cats, setCats] = useState([]);
  const [acts, setActs] = useState([]);
  const [form, setForm] = useState(BLANK);
  const [newCat, setNewCat] = useState({ name: "", kind: "interview" });
  const [err, setErr] = useState("");

  const wrap = (fn) => async (...a) => { setErr(""); try { await fn(...a); } catch (e) { setErr(e.message); } };
  const load = wrap(async () => {
    if (tab === "stats") setStats(await api.get("/admin/stats"));
    if (tab === "users") setUsers(await api.get("/admin/users"));
    if (tab === "questions") setQs(await api.get("/admin/questions"));
    if (tab === "categories") setCats(await api.get("/admin/categories"));
    if (tab === "activity") setActs(await api.get("/admin/activity"));
  });
  useEffect(() => { load(); }, [tab]);

  const patch = wrap(async (u, body) => { await api.patch(`/admin/users/${u.id}`, body); load(); });
  const delUser = wrap(async (u) => { if (confirm(`Delete ${u.email} and all their data?`)) { await api.del(`/admin/users/${u.id}`); load(); } });
  const delQ = wrap(async (q) => { await api.del(`/admin/questions/${q.id}`); load(); });
  const addQ = wrap(async (e) => {
    e.preventDefault();
    const body = { kind: form.kind, category: form.category, difficulty: form.difficulty, title: form.title, text: form.text, explanation: form.explanation };
    if (form.kind === "aptitude") { body.options = form.options.split("\n").map((s) => s.trim()).filter(Boolean); body.answer_index = Number(form.answer_index); }
    if (form.kind === "coding") body.test_cases = JSON.parse(form.test_cases || "[]");
    await api.post("/admin/questions", body); setForm(BLANK); load();
  });
  const addCat = wrap(async (e) => { e.preventDefault(); await api.post("/admin/categories", newCat); setNewCat({ ...newCat, name: "" }); load(); });
  const delCat = wrap(async (c) => { await api.del(`/admin/categories/${c.id}`); load(); });
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  return (
    <div>
      <h2>Admin Dashboard</h2>
      <div className="tabs">{["stats", "users", "questions", "categories", "activity"].map((t) => <button key={t} className={`btn sm ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>{t}</button>)}</div>
      {err && <div className="error">{err}</div>}

      {tab === "stats" && stats && <>
        <div className="grid g4">{[["Users", stats.users], ["Active users", stats.active_users], ["Interviews", stats.interviews], ["Finished", stats.finished_interviews],
          ["Coding submissions", stats.coding_submissions], ["Aptitude tests", stats.aptitude_tests], ["Questions", stats.questions]].map(([l, v]) =>
          <div className="card" key={l}><div className="muted small">{l}</div><div className="stat">{v}</div></div>)}</div>
        <div className="card"><h3>Interviews by category</h3><table><thead><tr><th>Category</th><th>Count</th><th>Avg score</th></tr></thead><tbody>
          {stats.by_category.map((c) => <tr key={c.category}><td>{c.category}</td><td>{c.count}</td><td>{c.avg_score ?? "–"}</td></tr>)}</tbody></table></div></>}

      {tab === "users" && <div className="card" style={{ overflowX: "auto" }}><table><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th></th></tr></thead><tbody>
        {users.map((u) => <tr key={u.id}><td>{u.name}</td><td>{u.email}</td><td>{u.role}</td>
          <td><span className={`badge ${u.is_active ? "good" : "bad"}`}>{u.is_active ? "active" : "disabled"}</span></td>
          <td className="row"><button className="btn sm" onClick={() => patch(u, { is_active: !u.is_active })}>{u.is_active ? "Disable" : "Enable"}</button>
            <button className="btn sm" onClick={() => patch(u, { role: u.role === "admin" ? "student" : "admin" })}>{u.role === "admin" ? "Make student" : "Make admin"}</button>
            <button className="btn sm danger" onClick={() => delUser(u)}>Delete</button></td></tr>)}</tbody></table></div>}

      {tab === "questions" && <>
        <form className="card" onSubmit={addQ}>
          <h3>Add question</h3>
          <div className="row">
            <div style={{ flex: 1 }}><label>Kind</label><select value={form.kind} onChange={set("kind")}><option>aptitude</option><option>coding</option><option>interview</option></select></div>
            <div style={{ flex: 1 }}><label>Category / section</label><input value={form.category} onChange={set("category")} required /></div>
            <div style={{ flex: 1 }}><label>Difficulty</label><select value={form.difficulty} onChange={set("difficulty")}><option>easy</option><option>medium</option><option>hard</option></select></div>
          </div>
          {form.kind === "coding" && <><label>Title</label><input value={form.title} onChange={set("title")} required /></>}
          <label>Question text</label><textarea value={form.text} onChange={set("text")} required minLength={5} />
          {form.kind === "aptitude" && <><label>Options (one per line)</label><textarea value={form.options} onChange={set("options")} />
            <label>Correct option number (0 = first)</label><input type="number" min={0} value={form.answer_index} onChange={set("answer_index")} />
            <label>Explanation</label><textarea style={{ minHeight: 60 }} value={form.explanation} onChange={set("explanation")} /></>}
          {form.kind === "coding" && <><label>Test cases (JSON)</label>
            <textarea value={form.test_cases} onChange={set("test_cases")} placeholder='[{"input":"3 4","expected":"7"}]' /></>}
          <button className="btn primary" style={{ marginTop: ".8rem" }}>Add</button>
        </form>
        <div className="card" style={{ overflowX: "auto" }}><table><thead><tr><th>ID</th><th>Kind</th><th>Category</th><th>Question</th><th></th></tr></thead><tbody>
          {qs.map((q) => <tr key={q.id}><td>{q.id}</td><td>{q.kind}</td><td>{q.category}</td><td>{q.title || q.text.slice(0, 90)}</td>
            <td><button className="btn sm danger" onClick={() => delQ(q)}>Delete</button></td></tr>)}</tbody></table></div></>}

      {tab === "categories" && <div className="card">
        <form className="row" onSubmit={addCat}><input style={{ maxWidth: 260 }} placeholder="New category" value={newCat.name} onChange={(e) => setNewCat({ ...newCat, name: e.target.value })} required />
          <select style={{ width: "auto" }} value={newCat.kind} onChange={(e) => setNewCat({ ...newCat, kind: e.target.value })}><option>interview</option><option>aptitude</option><option>coding</option></select>
          <button className="btn primary">Add</button></form>
        <table style={{ marginTop: "1rem" }}><tbody>{cats.map((c) => <tr key={c.id}><td>{c.name}</td><td><span className="badge">{c.kind}</span></td>
          <td><button className="btn sm danger" onClick={() => delCat(c)}>Delete</button></td></tr>)}</tbody></table></div>}

      {tab === "activity" && <div className="card" style={{ overflowX: "auto" }}><table><thead><tr><th>Time (UTC)</th><th>User</th><th>Action</th><th>Detail</th></tr></thead><tbody>
        {acts.map((a) => <tr key={a.id}><td>{a.created_at.replace("T", " ").slice(0, 19)}</td><td>{a.user}</td><td>{a.action}</td><td>{a.detail}</td></tr>)}</tbody></table></div>}
    </div>
  );
}
