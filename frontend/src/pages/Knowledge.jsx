import React, { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Knowledge() {
  const [docs, setDocs] = useState([]);
  const [docId, setDocId] = useState("");
  const [q, setQ] = useState("");
  const [res, setRes] = useState(null);
  const [gen, setGen] = useState(null);
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");

  const load = () => api.get("/rag/documents").then(setDocs).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);

  async function upload(e) {
    const f = e.target.files[0];
    if (!f) return;
    setErr(""); setBusy("upload");
    try { await api.upload("/rag/upload", f); await load(); } catch (ex) { setErr(ex.message); }
    setBusy(""); e.target.value = "";
  }
  async function ask() {
    setErr(""); setBusy("ask"); setRes(null);
    try { setRes(await api.post("/rag/ask", { question: q, document_id: docId ? Number(docId) : null })); } catch (e) { setErr(e.message); }
    setBusy("");
  }
  async function questions() {
    setErr(""); setBusy("gen"); setGen(null);
    try { setGen(await api.post("/rag/questions", { document_id: Number(docId), count: 6 })); } catch (e) { setErr(e.message); }
    setBusy("");
  }
  async function remove(d) {
    if (!confirm(`Delete ${d.filename}?`)) return;
    await api.del(`/rag/documents/${d.id}`); if (String(d.id) === docId) setDocId(""); load();
  }

  return (
    <div>
      <h2>Knowledge Assistant</h2>
      {err && <div className="error">{err}</div>}
      <div className="grid g2">
        <div className="card">
          <h3>Your study material</h3>
          <input type="file" accept=".pdf,.docx,.txt,.md" onChange={upload} disabled={busy === "upload"} />
          {busy === "upload" && <p className="muted">Indexing…</p>}
          <table style={{ marginTop: ".8rem" }}><tbody>
            {docs.map((d) => <tr key={d.id}><td>{d.filename}<div className="muted small">{d.chunks} passages</div></td>
              <td><button className="btn sm danger" onClick={() => remove(d)}>Delete</button></td></tr>)}
          </tbody></table>
          {!docs.length && <p className="muted">Upload a PDF, DOCX, TXT or MD file to get started.</p>}
        </div>
        <div className="card">
          <h3>Ask or generate</h3>
          <label>Limit to document</label>
          <select value={docId} onChange={(e) => setDocId(e.target.value)}><option value="">All documents</option>
            {docs.map((d) => <option key={d.id} value={d.id}>{d.filename}</option>)}</select>
          <label>Your question</label>
          <textarea style={{ minHeight: 80 }} value={q} onChange={(e) => setQ(e.target.value)} />
          <div className="row" style={{ marginTop: ".8rem" }}>
            <button className="btn primary" onClick={ask} disabled={busy === "ask" || q.trim().length < 3}>{busy === "ask" ? "Searching…" : "Ask"}</button>
            <button className="btn" onClick={questions} disabled={!docId || busy === "gen"}>{busy === "gen" ? "Generating…" : "Generate interview questions"}</button>
          </div>
          {!docId && <p className="muted small">Select a document to generate interview questions from it.</p>}
        </div>
      </div>
      {res && <div className="card"><h3>Answer</h3><p style={{ whiteSpace: "pre-wrap" }}>{res.answer}</p>
        {res.sources.length > 0 && <><h4>Sources</h4>{res.sources.map((s) => <details key={s.ref}><summary>[{s.ref}] {s.document} · passage {s.chunk} <span className="muted small">(relevance {s.score})</span></summary><pre>{s.snippet}</pre></details>)}</>}</div>}
      {gen && <div className="card"><h3>Interview questions</h3>
        {gen.questions?.map((x, i) => <div key={i} style={{ marginBottom: ".8rem" }}><strong>{i + 1}. {x.question}</strong> <span className="badge">{x.difficulty}</span>
          <details><summary className="small">Model answer</summary><p>{x.model_answer}</p></details></div>)}</div>}
    </div>
  );
}
