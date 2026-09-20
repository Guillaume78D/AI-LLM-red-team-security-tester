from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from openai import OpenAI
from pydantic import BaseModel

import config
from database import database as db
from reports.report_generator import REPORTS_DIR, build_report

app = FastAPI(title="AI LLM Security Tester")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
client = OpenAI(base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY)

db.init_db()


class ReportRequest(BaseModel):
    run_id: int
    target_name: str | None = None
    evidence: bool = True
    risk: bool = True
    recommendations: bool = True
    owasp: bool = True


@app.get("/")
def dashboard(request: Request):
    return templates.TemplateResponse(
        request, "index.html", {"target_name": config.TARGET_NAME}
    )


@app.get("/health")
def health():
    try:
        models = [m.id for m in client.models.list().data]
        reachable = True
    except Exception:
        models, reachable = [], False
    return {
        "status": "ok",
        "llm_reachable": reachable,
        "base_url": config.LLM_BASE_URL,
        "configured_model": config.MODEL_NAME,
        "available_models": models,
    }


@app.get("/ping-llm")
def ping_llm():
    try:
        r = client.chat.completions.create(
            model=config.MODEL_NAME,
            messages=[{"role": "user", "content": "Say hello in one short sentence."}],
            temperature=config.TEMPERATURE,
        )
        return {"response": r.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


def resolve_run_id(run_id):
    if run_id is not None:
        return run_id
    latest = db.get_latest_run()
    if not latest:
        raise HTTPException(status_code=404, detail="No test run yet. Run: python run_tests.py")
    return latest["id"]


@app.get("/api/runs")
def api_runs():
    return db.get_runs()


@app.get("/api/stats")
def api_stats(run_id: int | None = Query(None)):
    return db.get_stats(resolve_run_id(run_id))


@app.get("/api/results")
def api_results(run_id: int | None = Query(None), status: str | None = Query(None)):
    results = db.get_results(resolve_run_id(run_id))
    if status:
        results = [r for r in results if r["status"] == status.upper()]
    return results


@app.post("/api/report")
def api_report(req: ReportRequest):
    if not db.get_run(req.run_id):
        raise HTTPException(status_code=404, detail=f"Run #{req.run_id} not found")
    options = {
        "evidence": req.evidence,
        "risk": req.risk,
        "recommendations": req.recommendations,
        "owasp": req.owasp,
    }
    try:
        filename = build_report(req.run_id, options, req.target_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {e}")
    return {"filename": filename, "url": f"/api/report/download/{filename}"}


@app.get("/api/report/download/{filename}")
def api_report_download(filename: str):
    safe = Path(filename).name
    path = REPORTS_DIR / safe
    if not safe.endswith(".pdf") or not path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(path, media_type="application/pdf", filename=safe)
