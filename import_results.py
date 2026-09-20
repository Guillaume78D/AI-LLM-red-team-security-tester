import json
import config
from database import database as db

db.init_db()
with open("evaluated_results.json", encoding="utf-8") as f:
    items = json.load(f)

run_id = db.create_run(config.TARGET_NAME, config.MODEL_NAME, len(items))
for item in items:
    verdict = {k: item[k] for k in ("status", "severity", "reason", "evaluator")}
    db.save_result(run_id, item, item["response"], verdict)
db.finish_run(run_id)
print(f"Imported {len(items)} results as run #{run_id}")
