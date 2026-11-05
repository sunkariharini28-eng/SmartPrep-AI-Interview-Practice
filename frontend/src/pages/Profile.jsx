import React, { useState } from "react";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";

export default function Profile() {
  const { user, setUser } = useAuth();
  const [f, setF] = useState({ name: user.name, target_role: user.target_role || "", skills: (user.skills || []).join(", "), bio: user.bio || "" });
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  async function save(e) {
    e.preventDefault(); setErr(""); setMsg("");
    try {
      setUser(await api.put("/auth/me", { ...f, skills: f.skills.split(",").map((s) => s.trim()).filter(Boolean) }));
      setMsg("Profile saved.");
    } catch (ex) { setErr(ex.message); }
  }
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  return (
    <div>
      <h2>Profile</h2>
      <form className="card" style={{ maxWidth: 560 }} onSubmit={save}>
        <label>Email</label><input value={user.email} disabled />
        <label>Name</label><input value={f.name} onChange={set("name")} minLength={2} required />
        <label>Target role</label><input value={f.target_role} onChange={set("target_role")} />
        <label>Skills (comma separated)</label><input value={f.skills} onChange={set("skills")} />
        <label>About you</label><textarea value={f.bio} onChange={set("bio")} maxLength={1000} />
        {err && <div className="error">{err}</div>}{msg && <div className="notice">{msg}</div>}
        <button className="btn primary" style={{ marginTop: "1rem" }}>Save</button>
      </form>
    </div>
  );
}
