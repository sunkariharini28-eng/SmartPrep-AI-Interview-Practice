
import React, { useEffect, useRef, useState } from "react";
import { api } from "../api.js";

const LANGS = [
  ["English", "en-US"],
  ["Hindi", "hi-IN"],
  ["Telugu", "te-IN"],
  ["Tamil", "ta-IN"],
  ["Spanish", "es-ES"],
  ["French", "fr-FR"],
  ["German", "de-DE"]
];

const FILLERS = [
  "um", "uh", "like", "you know",
  "basically", "actually", "so"
];

function speechStats(text, seconds) {
  const words = text.trim().split(/\s+/).filter(Boolean);
  const lower = " " + text.toLowerCase() + " ";

  const fillers = FILLERS.reduce(
    (n, f) =>
      n + (lower.split(new RegExp(`\\b${f}\\b`, "g")).length - 1),
    0
  );

  const wpm =
    seconds > 3
      ? Math.round((words.length / seconds) * 60)
      : null;

  const tips = [];

  if (wpm !== null) {
    if (wpm > 170) {
      tips.push(`Your pace was about ${wpm} words/min, which is fast. Slow down a little.`);
    } else if (wpm < 90) {
      tips.push(`Your pace was about ${wpm} words/min, which is slow. Try to sound more fluent.`);
    } else {
      tips.push(`Your pace was about ${wpm} words/min, a comfortable range.`);
    }
  }

  if (words.length && fillers / words.length > 0.05) {
    tips.push(`You used ${fillers} filler words; try pausing instead.`);
  }

  return {
    words: words.length,
    wpm,
    fillers,
    tips
  };
}

export default function Interview() {
  const [cats, setCats] = useState([]);
  const [resumes, setResumes] = useState([]);

  const [cfg, setCfg] = useState({
    category: "Node.js",
    difficulty: "medium",
    num_questions: 5,
    mode: "text",
    language: "English",
    resume_id: ""
  });

  const [session, setSession] = useState(null);
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [listening, setListening] = useState(false);
  const [speak, setSpeak] = useState(true);
  const [cam, setCam] = useState(false);
  const [stats, setStats] = useState(null);

  const recRef = useRef(null);
  const micStreamRef = useRef(null);
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const startRef = useRef(null);

  useEffect(() => {
    api.get("/interview/categories")
      .then((c) => setCats(c))
      .catch((e) => setErr(e.message));

    api.get("/resume")
      .then(setResumes)
      .catch(() => {});

    return () => {
      stopMic();
      stopCam();
      window.speechSynthesis?.cancel();
    };
  }, []);

  const langCode =
    LANGS.find((l) => l[0] === cfg.language)?.[1] || "en-US";

  const current =
    session?.answers?.find((a) => !a.evaluation) || null;

  const lastDone = session
    ? [...session.answers].reverse().find((a) => a.evaluation)
    : null;

  useEffect(() => {
    if (
      current &&
      cfg.mode !== "text" &&
      speak &&
      window.speechSynthesis
    ) {
      window.speechSynthesis.cancel();

      const u = new SpeechSynthesisUtterance(current.question);
      u.lang = langCode;

      window.speechSynthesis.speak(u);
    }

    setAnswer("");
    setStats(null);
    startRef.current = Date.now();
  }, [current?.id]);

  // MICROPHONE RECORDING USING MEDIARRECORDER
  async function startMic() {
    setErr("");

    if (
      !navigator.mediaDevices?.getUserMedia ||
      !window.MediaRecorder
    ) {
      setErr("Microphone recording is not supported. Please use Chrome or Edge.");
      return;
    }

    try {
      const stream =
        await navigator.mediaDevices.getUserMedia({
          audio: true
        });

      micStreamRef.current = stream;

      const types = [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/mp4"
      ];

      const mimeType = types.find((type) =>
        MediaRecorder.isTypeSupported(type)
      );

      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);

      const chunks = [];

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          chunks.push(event.data);
        }
      };

      recorder.onerror = () => {
        setErr("Recording failed. Please try again.");
        setListening(false);
      };
      const recordingStartTime = Date.now();

recorder.onstart = () => {
  console.log("Recording started");
};

recorder.onstop = () => {
  console.log(
    "Recording duration:",
    (Date.now() - recordingStartTime) / 1000,
    "seconds"
  );
};
      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        micStreamRef.current = null;
        setListening(false);

        if (chunks.length === 0) {
          setErr("No audio recorded. Please try again.");
          return;
        }

        try {
          setBusy(true);

          const blob = new Blob(chunks, {
            type: recorder.mimeType || "audio/webm"
          });

          const extension = blob.type.includes("mp4")
            ? "mp4"
            : "webm";

          const audioFile = new File(
            [blob],
            `answer.${extension}`,
            { type: blob.type }
          );

          const result = await api.upload(
            "/interview/transcribe",
            audioFile
          );

          if (!result.text?.trim()) {
            setErr("No speech detected. Please record again.");
          } else {
            setAnswer((previous) =>
              [previous, result.text].filter(Boolean).join(" ")
            );
          }
        } catch (e) {
          setErr("Voice transcription failed: " + e.message);
        } finally {
          setBusy(false);
        }
      };

      recRef.current = recorder;
      recorder.start(1000);
      setListening(true);

    } catch (e) {
      setErr(
        "Microphone permission denied or unavailable: " + e.message
      );
    }
  }

  function stopMic() {
    if (
      recRef.current &&
      recRef.current.state !== "inactive"
    ) {
      recRef.current.stop();
    } else {
      micStreamRef.current
        ?.getTracks()
        .forEach((track) => track.stop());

      micStreamRef.current = null;
      setListening(false);
    }
  }

  // CAMERA
  async function toggleCam(on) {
    if (!on) {
      stopCam();
      return;
    }

    try {
      const s =
        await navigator.mediaDevices.getUserMedia({
          video: true
        });

      streamRef.current = s;
      setCam(true);

      setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = s;
        }
      }, 50);

    } catch {
      setErr("Camera permission denied or unavailable.");
    }
  }

  function stopCam() {
    streamRef.current
      ?.getTracks()
      .forEach((track) => track.stop());

    streamRef.current = null;
    setCam(false);
  }

  // START INTERVIEW
  async function start() {
    setErr("");
    setBusy(true);

    try {
      const body = {
        ...cfg,
        resume_id: cfg.resume_id
          ? Number(cfg.resume_id)
          : null,
        num_questions: Number(cfg.num_questions)
      };

      setSession(
        await api.post("/interview/start", body)
      );

    } catch (e) {
      setErr(e.message);
    }

    setBusy(false);
  }

  // SUBMIT ANSWER
  async function submit() {
    stopMic();
    window.speechSynthesis?.cancel();

    setErr("");
    setBusy(true);

    const secs =
      (Date.now() - startRef.current) / 1000;

    try {
      const s = await api.post(
        `/interview/${session.id}/answer`,
        {
          answer,
          duration_seconds: secs
        }
      );

      if (cfg.mode !== "text") {
        setStats(speechStats(answer, secs));
      }

      setSession(s);

    } catch (e) {
      setErr(e.message);
    }

    setBusy(false);
  }

  const reset = () => {
    setSession(null);
    stopMic();
    stopCam();
    setStats(null);
    setErr("");
  };

  // INTERVIEW SETTINGS PAGE
  if (!session) {
    return (
      <div>
        <h2>AI Interview Room</h2>

        <div className="card" style={{ maxWidth: 640 }}>
          <label>Category</label>

          <select
            value={cfg.category}
            onChange={(e) =>
              setCfg({ ...cfg, category: e.target.value })
            }
            disabled={!!cfg.resume_id}
          >
            {cats.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>

          {resumes.length > 0 && (
            <>
              <label>Or interview me on my resume</label>

              <select
                value={cfg.resume_id}
                onChange={(e) =>
                  setCfg({ ...cfg, resume_id: e.target.value })
                }
              >
                <option value="">
                  No, use the category above
                </option>

                {resumes.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.filename}
                  </option>
                ))}
              </select>
            </>
          )}

          <div className="row">
            <div style={{ flex: 1 }}>
              <label>Starting difficulty</label>

              <select
                value={cfg.difficulty}
                onChange={(e) =>
                  setCfg({ ...cfg, difficulty: e.target.value })
                }
              >
                <option>easy</option>
                <option>medium</option>
                <option>hard</option>
              </select>
            </div>

            <div style={{ flex: 1 }}>
              <label>Questions</label>

              <input
                type="number"
                min={1}
                max={20}
                value={cfg.num_questions}
                onChange={(e) =>
                  setCfg({
                    ...cfg,
                    num_questions: e.target.value
                  })
                }
              />
            </div>
          </div>

          <div className="row">
            <div style={{ flex: 1 }}>
              <label>Mode</label>

              <select
                value={cfg.mode}
                onChange={(e) =>
                  setCfg({ ...cfg, mode: e.target.value })
                }
              >
                <option value="text">Text</option>
                <option value="voice">Voice</option>
                <option value="video">Video + voice</option>
              </select>
            </div>

            <div style={{ flex: 1 }}>
              <label>Language</label>

              <select
                value={cfg.language}
                onChange={(e) =>
                  setCfg({ ...cfg, language: e.target.value })
                }
              >
                {LANGS.map((l) => (
                  <option key={l[0]}>{l[0]}</option>
                ))}
              </select>
            </div>
          </div>

          {err && <div className="error">{err}</div>}

          <button
            className="btn primary"
            style={{ marginTop: "1rem" }}
            onClick={start}
            disabled={busy}
          >
            {busy
              ? "Preparing first question…"
              : "Start interview"}
          </button>
        </div>
      </div>
    );
  }

  // ACTIVE INTERVIEW
  const done = session.status === "finished";
  const ev = lastDone?.evaluation;

  return (
    <div>
      <div className="row between">
        <h2>{session.category} interview</h2>

        <span className="badge">
          {done
            ? "Finished"
            : current
            ? `Question ${current.idx} of ${session.num_questions} · ${current.difficulty}`
            : "Loading next question..."}
        </span>
      </div>

      {err && <div className="error">{err}</div>}

      {!done && current && (
        <div
          className="grid"
          style={{
            gridTemplateColumns:
              cfg.mode === "video"
                ? "minmax(0,1fr) 280px"
                : "1fr"
          }}
        >
          <div className="card">
            <div className="q-box">
              {current.question || "Loading question..."}
            </div>

            {cfg.mode !== "text" && (
              <div
                className="row small muted"
                style={{ marginTop: ".5rem" }}
              >
                <button
                  className="btn sm"
                  onClick={() => {
                    window.speechSynthesis?.cancel();

                    const u = new SpeechSynthesisUtterance(
                      current.question
                    );

                    u.lang = langCode;
                    window.speechSynthesis?.speak(u);
                  }}
                >
                  Replay question
                </button>

                <label style={{ margin: 0 }}>
                  <input
                    type="checkbox"
                    style={{ width: "auto" }}
                    checked={speak}
                    onChange={(e) =>
                      setSpeak(e.target.checked)
                    }
                  />
                  Read questions aloud
                </label>
              </div>
            )}

            <label>
              {cfg.mode === "text"
                ? "Your answer"
                : "Voice transcript (editable)"}
            </label>

            <textarea
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder={
                cfg.mode === "text"
                  ? "Type your answer…"
                  : "Press Record answer and start speaking…"
              }
            />

            <div
              className="row"
              style={{ marginTop: ".8rem" }}
            >
              {cfg.mode !== "text" &&
                (listening ? (
                  <button
                    className="btn danger"
                    onClick={stopMic}
                  >
                    Stop recording
                  </button>
                ) : (
                  <button
                    className="btn"
                    onClick={startMic}
                    disabled={busy}
                  >
                    Record answer
                  </button>
                ))}

              <button
                className="btn primary"
                onClick={submit}
                disabled={busy || !answer.trim() || listening}
              >
                {busy ? "Evaluating…" : "Submit answer"}
              </button>
            </div>
          </div>

          {cfg.mode === "video" && (
            <div className="card">
              {cam ? (
                <video
                  ref={videoRef}
                  className="video"
                  autoPlay
                  muted
                  playsInline
                />
              ) : (
                <p className="muted small">
                  Camera is off. It stays on your device;
                  nothing is uploaded.
                </p>
              )}

              <button
                className="btn sm"
                style={{ marginTop: ".6rem" }}
                onClick={() => toggleCam(!cam)}
              >
                {cam
                  ? "Turn camera off"
                  : "Turn camera on"}
              </button>

              <p className="muted small">
                The camera is a practice mirror so you can
                check posture and eye contact. Feedback is
                based only on your speech pace and filler
                words, never on your face or appearance.
              </p>
            </div>
          )}
        </div>
      )}

      {/* ANSWER FEEDBACK */}
      {ev && (
        <div className="card">
          <div className="row between">
            <h3>
              Feedback on question {lastDone.idx}
            </h3>

            <div>
              <span className="score">{ev.score}</span>/10
              <span className="badge">
                Communication {ev.communication}/10
              </span>
            </div>
          </div>

          <p>{ev.feedback}</p>

          <h4>Model answer</h4>
          <p>{ev.correct_answer}</p>

          {ev.improvements?.length > 0 && (
            <>
              <h4>How to improve</h4>
              <ul>
                {ev.improvements.map((i, k) => (
                  <li key={k}>{i}</li>
                ))}
              </ul>
            </>
          )}

          {stats && (
            <div className="notice small">
              <strong>Speaking feedback:</strong>{" "}
              {stats.words} words. {stats.tips.join(" ")}
            </div>
          )}
        </div>
      )}

      {/* FINAL SUMMARY */}
      {done && (
        <div className="card">
          <h3>Interview complete</h3>

          <div className="row">
            <span className="score">
              {session.avg_score}
            </span>
            /10 average

            <span className="badge">
              Communication {session.avg_communication}/10
            </span>
          </div>

          {session.summary && (
            <>
              <p>{session.summary.overall}</p>

              <div className="grid g2">
                <div>
                  <h4>Strengths</h4>
                  <ul>
                    {session.summary.strengths?.map(
                      (s, i) => <li key={i}>{s}</li>
                    )}
                  </ul>
                </div>

                <div>
                  <h4>Needs work</h4>
                  <ul>
                    {session.summary.weaknesses?.map(
                      (s, i) => <li key={i}>{s}</li>
                    )}
                  </ul>
                </div>
              </div>

              <h4>Next steps</h4>
              <ul>
                {session.summary.next_steps?.map(
                  (s, i) => <li key={i}>{s}</li>
                )}
              </ul>
            </>
          )}

          <h4>All questions</h4>

          <table>
            <tbody>
              {session.answers.map((a) => (
                <tr key={a.id}>
                  <td>Q{a.idx}</td>
                  <td>{a.question}</td>
                  <td>
                    <span className="badge">
                      {a.evaluation?.score}/10
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <button
            className="btn primary"
            style={{ marginTop: "1rem" }}
            onClick={reset}
          >
            New interview
          </button>
        </div>
      )}
    </div>
  );
}
