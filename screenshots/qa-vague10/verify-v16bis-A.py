"""
VAGUE 16 bis - Verification economie A : reequilibrer rewards achievements + gemReward.

Verifie :
  1. ACHIEVEMENTS contient > 5 entries avec gemReward > 0
  2. reward max dans ACHIEVEMENTS <= 5000 (gros divises par 10)
  3. 0 erreurs console
"""
import json, time, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(r"D:/alchimia/screenshots/qa-vague10")
OUT.mkdir(parents=True, exist_ok=True)
URL = "http://localhost:8770/index.html"


def main():
    results = {"checks": [], "console_errors": [], "summary": {}}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 540, "height": 960})
        page = ctx.new_page()

        # Capture erreurs console
        page.on("pageerror", lambda exc: results["console_errors"].append({"type": "pageerror", "msg": str(exc)}))
        page.on("console", lambda msg: results["console_errors"].append({"type": "consoleerror", "msg": msg.text}) if msg.type == "error" else None)

        page.goto(URL, wait_until="networkidle")
        time.sleep(1.0)

        # Skip story / onboarding si present
        try:
            page.evaluate("""() => {
                if(window.STATE) window.STATE.storySeen = true;
                const s = document.getElementById('story-intro');
                if(s){ s.style.display='none'; s.classList.add('gone'); }
            }""")
        except Exception:
            pass

        # === CHECK 1 : nombre d'achievements avec gemReward > 0 doit etre > 5
        try:
            data = page.evaluate("""() => {
                const arr = window.ACHIEVEMENTS || [];
                let withGem = 0;
                let maxReward = 0;
                let maxRewardId = null;
                const gemSamples = [];
                for(const a of arr){
                    if((a.gemReward||0) > 0){
                        withGem++;
                        if(gemSamples.length < 6) gemSamples.push({id: a.id, reward: a.reward, gemReward: a.gemReward});
                    }
                    if((a.reward||0) > maxReward){
                        maxReward = a.reward;
                        maxRewardId = a.id;
                    }
                }
                return { total: arr.length, withGem, maxReward, maxRewardId, gemSamples };
            }""")
            ok = data["withGem"] > 5
            results["checks"].append({
                "id": 1, "name": "achievements_with_gemReward_gt_5", "ok": ok,
                "total_achievements": data["total"],
                "withGem": data["withGem"],
                "samples": data["gemSamples"]
            })
            results["_max_reward_data"] = {"maxReward": data["maxReward"], "id": data["maxRewardId"]}
        except Exception as e:
            results["checks"].append({"id": 1, "name": "achievements_with_gemReward_gt_5", "ok": False, "error": str(e)})

        # === CHECK 2 : reward max dans ACHIEVEMENTS <= 5000 (gros divises par 10)
        try:
            maxinfo = results.get("_max_reward_data", {})
            mx = maxinfo.get("maxReward", 999999)
            ok = mx <= 5000
            results["checks"].append({
                "id": 2, "name": "max_reward_leq_5000", "ok": ok,
                "max_reward": mx, "max_reward_id": maxinfo.get("id")
            })
        except Exception as e:
            results["checks"].append({"id": 2, "name": "max_reward_leq_5000", "ok": False, "error": str(e)})

        # Resume
        ok_count = sum(1 for c in results["checks"] if c.get("ok"))
        total = len(results["checks"])
        results["summary"] = {
            "passed": ok_count, "total": total,
            "console_errors_count": len(results["console_errors"])
        }

        # Save
        out_json = OUT / "verify-v16bis-A-report.json"
        out_json.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

        # Output lisible
        print("=" * 60)
        print("VAGUE 16 bis - VERIFY ECONOMIE A (rewards achievements + gemReward)")
        print("=" * 60)
        for c in results["checks"]:
            mark = "OK" if c.get("ok") else "FAIL"
            print(f"  [{mark}] check #{c['id']} {c['name']}")
            if not c.get("ok"):
                print(f"          details: {json.dumps(c, ensure_ascii=False)}")
            else:
                print(f"          details: {json.dumps({k:v for k,v in c.items() if k not in ('ok','id','name')}, ensure_ascii=False)}")
        print("-" * 60)
        print(f"  passed {ok_count}/{total} - console_errors: {len(results['console_errors'])}")
        for e in results["console_errors"][:10]:
            print(f"    ERR: {e}")
        print("=" * 60)
        print(f"  report -> {out_json}")

        browser.close()

    if ok_count < total or results["console_errors"]:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
