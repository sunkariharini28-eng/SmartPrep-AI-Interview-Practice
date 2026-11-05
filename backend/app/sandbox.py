"""Runs code in a subprocess with timeout and a temporary directory.
For production, use Docker or a dedicated isolated runner.
"""
import os
import sys
import shutil
import subprocess
import tempfile
import time

from .config import settings

IS_WINDOWS = os.name == "nt"
EXECUTABLE = "main.exe" if IS_WINDOWS else "./main"

LANGS = {
    "python": {
        "file": "main.py",
        "run": [sys.executable, "main.py"],
        "bin": sys.executable
    },
    "javascript": {
        "file": "main.js",
        "run": ["node", "main.js"],
        "bin": "node"
    },
    "c": {
        "file": "main.c",
        "compile": ["gcc", "main.c", "-O2", "-o", "main.exe" if IS_WINDOWS else "main", "-lm"],
        "run": [EXECUTABLE],
        "bin": "gcc"
    },
    "cpp": {
        "file": "main.cpp",
        "compile": ["g++", "main.cpp", "-O2", "-std=c++17", "-o", "main.exe" if IS_WINDOWS else "main"],
        "run": [EXECUTABLE],
        "bin": "g++"
    },
    "java": {
        "file": "Main.java",
        "compile": ["javac", "Main.java"],
        "run": ["java", "-Xmx256m", "Main"],
        "bin": "javac"
    },
}


def _limits(language: str):
    def apply():
        import resource

        t = settings.CODE_TIMEOUT_SECONDS
        resource.setrlimit(resource.RLIMIT_CPU, (t + 1, t + 1))
        resource.setrlimit(resource.RLIMIT_FSIZE, (5_000_000, 5_000_000))

        if language != "java":
            resource.setrlimit(
                resource.RLIMIT_AS,
                (768 * 1024 * 1024, 768 * 1024 * 1024)
            )

        os.setsid()

    return apply


def _run(cmd, cwd, stdin, language, timeout):
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": cwd,
        "LANG": "C.UTF-8"
    }

    # Windows needs these environment variables.
    if IS_WINDOWS:
        for key in ("SYSTEMROOT", "WINDIR", "TEMP", "TMP"):
            if key in os.environ:
                env[key] = os.environ[key]

    kwargs = {
        "cwd": cwd,
        "input": stdin,
        "capture_output": True,
        "text": True,
        "timeout": timeout,
        "env": env
    }

    # Resource limits are supported only on Unix/Linux.
    if not IS_WINDOWS:
        kwargs["preexec_fn"] = _limits(language)

    return subprocess.run(cmd, **kwargs)


def available_languages() -> dict:
    return {
        k: bool(shutil.which(v["bin"]))
        for k, v in LANGS.items()
    }


def run_code(language: str, code: str, stdin: str = "") -> dict:
    cfg = LANGS.get(language)

    if not cfg:
        return {
            "ok": False,
            "stdout": "",
            "stderr": "Unsupported language",
            "time_ms": 0,
            "status": "error"
        }

    if not shutil.which(cfg["bin"]):
        return {
            "ok": False,
            "stdout": "",
            "stderr": f"{language} runtime is not installed on the server",
            "time_ms": 0,
            "status": "unavailable"
        }

    if len(code) > 50_000:
        return {
            "ok": False,
            "stdout": "",
            "stderr": "Code too long",
            "time_ms": 0,
            "status": "error"
        }

    with tempfile.TemporaryDirectory(prefix="sandbox_") as d:
        with open(os.path.join(d, cfg["file"]), "w", encoding="utf-8") as f:
            f.write(code)

        try:
            if "compile" in cfg:
                c = _run(cfg["compile"], d, "", language, 30)

                if c.returncode != 0:
                    return {
                        "ok": False,
                        "stdout": "",
                        "stderr": c.stderr[:3000],
                        "time_ms": 0,
                        "status": "compile_error"
                    }

            start = time.perf_counter()

            r = _run(
                cfg["run"],
                d,
                stdin,
                language,
                settings.CODE_TIMEOUT_SECONDS
            )

            ms = int((time.perf_counter() - start) * 1000)

            return {
                "ok": r.returncode == 0,
                "stdout": r.stdout[:10000],
                "stderr": r.stderr[:3000],
                "time_ms": ms,
                "status": "ok" if r.returncode == 0 else "runtime_error"
            }

        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "stdout": "",
                "stderr": f"Time limit exceeded ({settings.CODE_TIMEOUT_SECONDS}s)",
                "time_ms": settings.CODE_TIMEOUT_SECONDS * 1000,
                "status": "timeout"
            }
