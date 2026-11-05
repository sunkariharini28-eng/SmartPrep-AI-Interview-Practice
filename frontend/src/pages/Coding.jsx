import React, { useEffect, useState } from "react";
import Editor from "@monaco-editor/react";
import { api } from "../api.js";

const STARTERS = {
  python: "import sys\n\ndata = sys.stdin.read().split()\n# write your solution\nprint()\n",
  javascript: "const lines = require('fs').readFileSync(0, 'utf8').trim().split('\\n');\n// write your solution\nconsole.log();\n",
  java: "import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        // write your solution\n    }\n}\n",
  c: "#include <stdio.h>\n\nint main() {\n    // write your solution\n    return 0;\n}\n",
  cpp: "#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    // write your solution\n    return 0;\n}\n",
};
const MONACO = { python: "python", javascript: "javascript", java: "java", c: "c", cpp: "cpp" };

export default function Coding() {
  const [problems, setProblems] = useState([]);
  const [p, setP] = useState(null);
  const [lang, setLang] = useState("python");
  const [code, setCode] = useState(STARTERS.python);
  const [stdin, setStdin] = useState("");
  const [out, setOut] = useState(null);
  const [sub, setSub] = useState(null);
  const [hint, setHint] = useState(null);
  const [avail, setAvail] = useState({});
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get("/coding/problems").then((r) => { setProblems(r); if (r.length) open(r[0].id); }).catch((e) => setErr(e.message));
    api.get("/coding/languages").then(setAvail).catch(() => {});
  }, []);

  async function open(id) {
    const d = await api.get(`/coding/problems/${id}`);
    setP(d); setSub(null); setOut(null); setHint(null);
    if (d.samples[0]) setStdin(d.samples[0].input);
  }
  const changeLang = (l) => { setLang(l); setCode(STARTERS[l]); };
  async function run() {
    setErr(""); setBusy("run");
    try { setOut(await api.post("/coding/run", { language: lang, code, stdin })); } catch (e) { setErr(e.message); }
    setBusy("");
  }
  async function submit() {
    setErr(""); setBusy("submit"); setSub(null);
    try {
      setSub(await api.post("/coding/submit", { problem_id: p.id, language: lang, code }));
      api.get("/coding/problems").then(setProblems);
    } catch (e) { setErr(e.message); }
    setBusy("");
  }
  async function getHint() {
    setErr(""); setBusy("hint");
    try { setHint(await api.post("/coding/hint", { problem_id: p.id, language: lang, code })); } catch (e) { setErr(e.message); }
    setBusy("");
  }

  return (
    <div>
      <h2>Coding Practice</h2>
      {err && <div className="error">{err}</div>}
      <div className="tabs">
        {problems.map((x) => <button key={x.id} className={`btn sm ${p?.id === x.id ? "active" : ""}`} onClick={() => open(x.id)}>
          {x.solved ? "✓ " : ""}{x.title} <span className="muted">({x.difficulty})</span></button>)}
      </div>
      {p && (
        <div className="grid g2">
          <div className="card">
            <h3>{p.title} <span className="badge">{p.difficulty}</span></h3>
            <p style={{ whiteSpace: "pre-wrap" }}>{p.text}</p>
            {p.samples.map((s, i) => <div key={i}><strong className="small">Sample {i + 1}</strong>
              <pre>Input:{"\n"}{s.input}{"\n\n"}Output:{"\n"}{s.expected}</pre></div>)}
            <p className="muted small">{p.total_tests} test cases total (some hidden). Programs read from standard input.</p>
            <button className="btn sm" onClick={getHint} disabled={busy === "hint"}>{busy === "hint" ? "Thinking…" : "Get an AI hint"}</button>
            {hint && <div className="notice"><strong>Hint:</strong> {hint.hint}<br /><span className="muted small">Concept: {hint.concept}</span></div>}
          </div>
          <div className="card">
            <div className="row between">
              <select style={{ width: "auto" }} value={lang} onChange={(e) => changeLang(e.target.value)}>
                {Object.keys(STARTERS).map((l) => <option key={l} value={l}>{l}{avail[l] === false ? " (runtime missing)" : ""}</option>)}
              </select>
              <div className="row">
                <button className="btn sm" onClick={run} disabled={!!busy}>{busy === "run" ? "Running…" : "Run"}</button>
                <button className="btn primary sm" onClick={submit} disabled={!!busy}>{busy === "submit" ? "Judging…" : "Submit"}</button>
              </div>
            </div>
            <div style={{ border: "1px solid var(--border)", borderRadius: 10, overflow: "hidden", marginTop: ".6rem" }}>
              <Editor height="320px" language={MONACO[lang]} value={code} onChange={(v) => setCode(v ?? "")}
                theme={document.documentElement.dataset.theme === "dark" ? "vs-dark" : "light"} options={{ minimap: { enabled: false }, fontSize: 14 }} />
            </div>
            <label>Custom input</label><textarea style={{ minHeight: 70 }} value={stdin} onChange={(e) => setStdin(e.target.value)} />
            {out && <div><strong className="small">Output ({out.status}, {out.time_ms} ms)</strong>
              <pre>{out.stdout}{out.stderr && `\n${out.stderr}`}</pre></div>}
          </div>
        </div>
      )}
      {sub && (
        <div className="card">
          <h3>Result: {sub.passed}/{sub.total} tests passed {sub.passed === sub.total && <span className="badge good">Accepted</span>}</h3>
          <table><thead><tr><th>#</th><th>Result</th><th>Time</th><th>Details</th></tr></thead><tbody>
            {sub.results.map((r) => <tr key={r.test}><td>{r.test}</td>
              <td><span className={`badge ${r.passed ? "good" : "bad"}`}>{r.passed ? "Passed" : r.status}</span></td><td>{r.time_ms} ms</td>
              <td className="small">{r.input !== null ? <>in: {r.input}<br />expected: {r.expected}<br />got: {r.output}</> : <span className="muted">Hidden test</span>}{r.error && <pre>{r.error}</pre>}</td></tr>)}
          </tbody></table>
          {sub.review && (sub.review.error ? <p className="muted">{sub.review.error}</p> : <div style={{ marginTop: "1rem" }}>
            <h4>AI review</h4>
            <p><span className="badge">Time {sub.review.time_complexity}</span> <span className="badge">Space {sub.review.space_complexity}</span></p>
            <p>{sub.review.correctness}</p><p>{sub.review.explanation}</p>
            {sub.review.improvements?.length > 0 && <ul>{sub.review.improvements.map((i, k) => <li key={k}>{i}</li>)}</ul>}
          </div>)}
        </div>
      )}
    </div>
  );
}
