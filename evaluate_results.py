import json
from collections import Counter
from evaluator.evaluator import evaluate_response, compute_risk


def main():
    with open("raw_results.json", encoding="utf-8") as f:
        raw = json.load(f)

    evaluated = []
    print(f"{'ID':8} {'STATUS':7} {'SEVERITY':9} {'BY':9} REASON")
    for item in raw:
        verdict = evaluate_response(item, item["response"])
        evaluated.append({**item, **verdict})
        print(f"{item['id']:8} {verdict['status']:7} {verdict['severity']:9} "
              f"{verdict['evaluator']:9} {verdict['reason'][:60]}")

    fails = [r for r in evaluated if r["status"] == "FAIL"]
    passed = [r for r in evaluated if r["status"] == "PASS"]
    risk = compute_risk(evaluated)
    print("\n=== SUMMARY ===")
    print(f"Total: {len(evaluated)} | Passed: {len(passed)} | Failed: {len(fails)}")
    print("Failed by severity:", dict(Counter(r["severity"] for r in fails)))
    print("Evaluator usage:", dict(Counter(r["evaluator"] for r in evaluated)))
    print(f"Overall risk: {risk['level']} (score {risk['score']}%)")

    with open("evaluated_results.json", "w", encoding="utf-8") as f:
        json.dump(evaluated, f, indent=2, ensure_ascii=False)

    evaluated.append({**item, **verdict, "case_severity": item["severity"]})

if __name__ == "__main__":
    main()