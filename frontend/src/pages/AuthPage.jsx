import React, { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";

export default function AuthPage({ mode }) {
  const { login, register } = useAuth();
  const nav = useNavigate();
  const [params] = useSearchParams();
  const [f, setF] = useState({ name: "", email: "", password: "" });
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setErr(""); setMsg(""); setBusy(true);
    try {
      if (mode === "login") { await login(f.email, f.password); nav("/dashboard"); }
      else if (mode === "register") { await register(f.name, f.email, f.password); nav("/dashboard"); }
      else if (mode === "forgot") setMsg((await api.post("/auth/forgot-password", { email: f.email })).message);
      else if (mode === "reset") {
        setMsg((await api.post("/auth/reset-password", { token: params.get("token") || "", password: f.password })).message);
        setTimeout(() => nav("/login"), 1500);
      }
    } catch (ex) { setErr(ex.message); }
    setBusy(false);
  }

  const titles = { login: "Welcome back", register: "Create your account", forgot: "Forgot password", reset: "Choose a new password" };
  return (
    <div className="auth-wrap">
      <form className="card auth-card" onSubmit={submit}>
        <Link to="/" className="brand" style={{ padding: 0 }}>SmartPrep AI</Link>
        <h2 style={{ marginTop: ".6rem" }}>{titles[mode]}</h2>
        {mode === "register" && <><label>Name</label><input required minLength={2} value={f.name} onChange={set("name")} /></>}
        {mode !== "reset" && <><label>Email</label><input type="email" required value={f.email} onChange={set("email")} /></>}
        {mode !== "forgot" && <><label>{mode === "reset" ? "New password" : "Password"}</label>
          <input type="password" required value={f.password} onChange={set("password")} />
          {mode !== "login" && <div className="muted small">8+ characters with letters and digits.</div>}</>}
        {err && <div className="error">{err}</div>}
        {msg && <div className="notice">{msg}</div>}
        <button className="btn primary" style={{ width: "100%", justifyContent: "center", marginTop: "1rem" }} disabled={busy}>
          {busy ? "Please wait…" : { login: "Log in", register: "Sign up", forgot: "Send reset link", reset: "Update password" }[mode]}
        </button>
        <div className="small muted" style={{ marginTop: "1rem" }}>
          {mode === "login" && <><Link to="/forgot">Forgot password?</Link> · <Link to="/register">Create account</Link></>}
          {mode === "register" && <>Have an account? <Link to="/login">Log in</Link></>}
          {(mode === "forgot" || mode === "reset") && <Link to="/login">Back to login</Link>}
        </div>
      </form>
    </div>
  );
}
