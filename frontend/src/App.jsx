import React, { useEffect, useState } from "react";
import { Link, NavLink, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import Landing from "./pages/Landing.jsx";
import AuthPage from "./pages/AuthPage.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Interview from "./pages/Interview.jsx";
import Resume from "./pages/Resume.jsx";
import Coding from "./pages/Coding.jsx";
import Aptitude from "./pages/Aptitude.jsx";
import Coach from "./pages/Coach.jsx";
import Knowledge from "./pages/Knowledge.jsx";
import Profile from "./pages/Profile.jsx";
import Admin from "./pages/Admin.jsx";

export function useTheme() {
  const [theme, setTheme] = useState(localStorage.getItem("theme") || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);
  return [theme, () => setTheme(theme === "dark" ? "light" : "dark")];
}

function Shell({ children }) {
  const { user, logout } = useAuth();
  const [theme, toggle] = useTheme();
  const nav = useNavigate();
  const links = [
    ["/dashboard", "Dashboard"], ["/interview", "AI Interview"], ["/coding", "Coding"], ["/aptitude", "Aptitude"],
    ["/resume", "Resume"], ["/coach", "Career Coach"], ["/knowledge", "Knowledge"], ["/profile", "Profile"],
  ];
  if (user.role === "admin") links.push(["/admin", "Admin"]);
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">SmartPrep AI</div>
        <nav className="nav">
          {links.map(([to, label]) => <NavLink key={to} to={to}>{label}</NavLink>)}
        </nav>
        <div style={{ marginTop: "auto" }} className="row">
          <button className="btn sm" onClick={toggle}>{theme === "dark" ? "Light" : "Dark"} mode</button>
          <button className="btn sm" onClick={() => { logout(); nav("/"); }}>Logout</button>
        </div>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}

function Private({ children, admin }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="main muted">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (admin && user.role !== "admin") return <Navigate to="/dashboard" replace />;
  return <Shell>{children}</Shell>;
}

export default function App() {
  useTheme();
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<AuthPage mode="login" />} />
      <Route path="/register" element={<AuthPage mode="register" />} />
      <Route path="/forgot" element={<AuthPage mode="forgot" />} />
      <Route path="/reset" element={<AuthPage mode="reset" />} />
      <Route path="/dashboard" element={<Private><Dashboard /></Private>} />
      <Route path="/interview" element={<Private><Interview /></Private>} />
      <Route path="/coding" element={<Private><Coding /></Private>} />
      <Route path="/aptitude" element={<Private><Aptitude /></Private>} />
      <Route path="/resume" element={<Private><Resume /></Private>} />
      <Route path="/coach" element={<Private><Coach /></Private>} />
      <Route path="/knowledge" element={<Private><Knowledge /></Private>} />
      <Route path="/profile" element={<Private><Profile /></Private>} />
      <Route path="/admin" element={<Private admin><Admin /></Private>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
