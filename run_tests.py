import config
from tests.engine import load_test_cases, run_test, CATEGORY_LABELS
from evaluator.evaluator import evaluate_response
from database import database as db


def main():
    db.init_db()
    cases = load_test_cases()
    total = sum(len(v) for v in cases.values())
    print(f"[*] Loaded {total} test cases")

    run_id = db.create_run(config.TARGET_NAME, config.MODEL_NAME, total)
    print(f"[*] Run #{run_id} against '{config.TARGET_NAME}' ({config.MODEL_NAME})")

    consecutive_errors = 0
    aborted = False

    for category, items in cases.items():
        if aborted:
            break
        print(f"[*] {CATEGORY_LABELS.get(category, category)} ({len(items)})")
        for item in items:
            case = {"category": category, **item}
            try:
                response = run_test(case["prompt"])
            except Exception as e:
                response = f"[ERROR] {e}"

            verdict = evaluate_response(case, response)
            db.save_result(run_id, case, response, verdict)
            print(f"    {case['id']:8} {verdict['status']:6} {verdict['severity']:9} ({verdict['evaluator']})")

            consecutive_errors = consecutive_errors + 1 if verdict["status"] == "ERROR" else 0
            if consecutive_errors >= 3:
                print("[!] 3 consecutive errors: is Ollama running? Aborting.")
                aborted = True
                break

    db.finish_run(run_id, "aborted" if aborted else "completed")
    stats = db.get_stats(run_id)
    print(f"[*] Done. Passed {stats['passed']} | Failed {stats['failed']} | "
          f"Errors {stats['errors']} | Risk {stats['risk_level']}")


if __name__ == "__main__":
    main()
