import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from evaluator.evaluator import compute_risk

DB_PATH = Path(__file__).parent / "redteam.db"


@contextmanager
def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_db():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_name TEXT,
            model TEXT,
            started_at TEXT,
            finished_at TEXT,
            status TEXT,
            total INTEGER
        );
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            test_id TEXT,
            category TEXT,
            prompt TEXT,
            expected TEXT,
            response TEXT,
            status TEXT,
            severity TEXT,
            case_severity TEXT,
            reason TEXT,
            evaluator TEXT,
            created_at TEXT
        );
        """)


def create_run(target_name, model, total):
    with conn() as c:
        cur = c.execute(
            "INSERT INTO runs (target_name, model, started_at, status, total) VALUES (?,?,?,?,?)",
            (target_name, model, now(), "running", total),
        )
        return cur.lastrowid


def finish_run(run_id, status="completed"):
    with conn() as c:
        c.execute("UPDATE runs SET finished_at=?, status=? WHERE id=?", (now(), status, run_id))


def save_result(run_id, case, response, verdict):
    case_severity = case.get("case_severity", case.get("severity"))
    with conn() as c:
        c.execute(
            """INSERT INTO results
               (run_id, test_id, category, prompt, expected, response,
                status, severity, case_severity, reason, evaluator, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (run_id, case["id"], case["category"], case["prompt"], case.get("expected", ""),
             response, verdict["status"], verdict["severity"], case_severity,
             verdict["reason"], verdict["evaluator"], now()),
        )


def get_runs(limit=20):
    with conn() as c:
        rows = c.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in rows]


def get_latest_run():
    with conn() as c:
        row = c.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()
        return dict(row) if row else None


def get_results(run_id):
    with conn() as c:
        rows = c.execute("SELECT * FROM results WHERE run_id=? ORDER BY id", (run_id,))
        return [dict(r) for r in rows]


def get_stats(run_id):
    results = get_results(run_id)
    passed = [r for r in results if r["status"] == "PASS"]
    failed = [r for r in results if r["status"] == "FAIL"]
    errors = [r for r in results if r["status"] == "ERROR"]

    severity = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for r in failed:
        severity[r["severity"]] += 1

    categories = {}
    for r in results:
        cat = categories.setdefault(r["category"], {"total": 0, "passed": 0, "failed": 0})
        cat["total"] += 1
        if r["status"] == "PASS":
            cat["passed"] += 1
        elif r["status"] == "FAIL":
            cat["failed"] += 1

    risk = compute_risk(results)
    return {
        "run_id": run_id,
        "total": len(results),
        "passed": len(passed),
        "failed": len(failed),
        "errors": len(errors),
        "severity": severity,
        "categories": categories,
        "risk_level": risk["level"],
        "risk_score": risk["score"],
    }


def get_run(run_id):
    with conn() as c:
        row = c.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        return dict(row) if row else None
