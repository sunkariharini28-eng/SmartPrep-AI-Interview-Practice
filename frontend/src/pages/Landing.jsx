import React from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { useTheme } from "../App.jsx";

const FEATURES = [
  ["AI Interviewer", "One question at a time, scored out of 10 with feedback, model answers and adaptive difficulty."],
  ["Voice & Video Rooms", "Speak your answers with live transcripts and a spoken interviewer, with optional pace and filler-word feedback."],
  ["Resume Analyzer", "Upload a PDF or DOCX, get skills, strengths, gaps, tailored questions and a role-match score."],
  ["Coding Practice", "Python, Java, C, C++ and JavaScript run against test cases in a sandbox, with AI review and hints."],
  ["Aptitude Tests", "Timed quantitative, logical and verbal tests with automatic scoring and explanations."],
  ["Career Coach", "Role suggestions, skill gaps, weekly roadmaps, daily tasks and project ideas."],
  ["Knowledge Assistant", "Upload study material, ask questions with source references, and generate interview questions."],
  ["Analytics", "Track scores, weak and strong topics, and your full interview history."],
];

export default function Landing() {
  const { user } = useAuth();
  const [theme, toggle] = useTheme();
  return (
    <div>
      <div className="landing-nav">
        <strong className="brand" style={{ padding: 0 }}>SmartPrep AI</strong>
        <div className="row">
          <button className="btn sm" onClick={toggle}>{theme === "dark" ? "Light" : "Dark"}</button>
          {user ? <Link className="btn primary sm" to="/dashboard">Dashboard</Link> : <>
            <Link className="btn sm" to="/login">Log in</Link>
            <Link className="btn primary sm" to="/register">Get started</Link></>}
        </div>
      </div>
      <section className="hero">
        <h1>Practice interviews with an AI that actually listens</h1>
        <p className="muted" style={{ maxWidth: 640, margin: "0 auto 1.5rem", fontSize: "1.1rem" }}>
          Technical, coding, aptitude, HR and communication interviews, with instant scoring, feedback and a personalised plan to get hired.
        </p>
        <Link className="btn primary" to={user ? "/interview" : "/register"}>Start practicing free</Link>
      </section>
      <section className="features">
        <div className="grid g4" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))" }}>
          {FEATURES.map(([t, d]) => (
            <div className="card" key={t}><h3>{t}</h3><p className="muted">{d}</p></div>
          ))}
        </div>
      </section>
    </div>
  );
}
