import asyncio
import json
from pathlib import Path
from ai_broll_autopilot.services.transition_engine import TransitionEngine
from ai_broll_autopilot.services.video_sfx_analyzer import VideoSFXAnalyzer

async def main():
    plan_path = Path(r"output\0914(6)_20260922_075620_cb9a69a9_0914(6)\edit_plan.json")
    with open(plan_path) as f:
        plan = json.load(f)

    shots = plan["shots"]
    work_dir = Path("output/workspace/test_sfx_transitions")
    work_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loaded {len(shots)} shots from plan.")

    # 1. Test Transition Engine
    te = TransitionEngine()
    shots = await te.plan_transitions(shots)
    print("\n--- Transitions Assigned ---")
    for s in shots:
        t = s.get("transition", {})
        stinger = t.get("stinger_sfx")
        stinger_name = stinger["file"] if stinger else "None"
        print(f"[{s['shot_id']}] IN: {t.get('type_in')} ({t.get('duration_in')}s) | OUT: {t.get('type_out')} | Stinger: {stinger_name}")

    # 2. Test Video SFX Analyzer
    sa = VideoSFXAnalyzer()
    shots = await sa.analyze_and_assign_sfx(shots, work_dir)
    print("\n--- Contextual SFX Assigned ---")
    for s in shots:
        sfx = s.get("contextual_sfx")
        if sfx:
            print(f"[{s['shot_id']}] SFX: {sfx['name']} ({sfx['file']}) | Vol: {sfx['volume']} | Reason: {sfx.get('reason')}")
        else:
            print(f"[{s['shot_id']}] SFX: None")

if __name__ == "__main__":
    asyncio.run(main())
