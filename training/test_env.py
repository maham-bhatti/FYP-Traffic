"""
test_env.py
===========
Quick sanity-check for the SUMOEnv + GCN-MAPPO stack.

Place this file in:  MARL-Traffic/src/training/
Run from that folder:
  cd MARL-Traffic/src/training
  python test_env.py
"""

import sys
import os
import numpy as np

print("=" * 65)
print("  SUMOEnv Test — Manhattan 4x4 GCN-MAPPO")
print("=" * 65)

# Compute scripts path directly (no private import needed)
THIS_DIR    = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.normpath(os.path.join(THIS_DIR, "..", "..", "sumo", "scripts"))
SUMO_CFG    = os.path.join(SCRIPTS_DIR, "run.sumocfg")

# ── Step 1: imports ───────────────────────────────────────────────────────────
print("\n[1/7] Importing modules...")
try:
    from gcn_encoder import REAL_JUNCTIONS, JUNCTION_LANES, RAW_OBS_DIM, ACT_DIM
    print("      gcn_encoder : OK")
except ImportError as e:
    print(f"      gcn_encoder : FAILED — {e}")
    print("      Make sure gcn_encoder.py is in MARL-Traffic/src/training/")
    sys.exit(1)

try:
    from traci_env import SUMOEnv
    print("      traci_env   : OK")
except ImportError as e:
    print(f"      traci_env   : FAILED — {e}")
    print("      Make sure traci_env.py is in MARL-Traffic/src/training/")
    sys.exit(1)

# ── Step 2: check file paths ──────────────────────────────────────────────────
print("\n[2/7] Checking file paths...")
print(f"      sumo/scripts dir : {SCRIPTS_DIR}")

required = ["run.sumocfg", "manhattan.net.xml", "final_routes.rou.xml"]
missing  = []
for fname in required:
    fpath  = os.path.join(SCRIPTS_DIR, fname)
    exists = os.path.exists(fpath)
    print(f"      {fname:<30} {'FOUND' if exists else 'MISSING'}")
    if not exists:
        missing.append(fname)

if missing:
    print()
    print("  Some required files are missing.")
    print("  Run these from  MARL-Traffic/sumo/scripts/ :")
    print("    python Gridnetwork.py")
    print("    python final_working_simulation.py")
    sys.exit(1)

# ── Step 3: launch SUMO ───────────────────────────────────────────────────────
print("\n[3/7] Launching SUMO (short 100-step warmup for test)...")
try:
    env = SUMOEnv(
        sumocfg    = SUMO_CFG,
        use_gui    = False,
        warmup     = 100,
        ep_duration= 200,
    )
    obs = env.reset()
    print("      SUMO launched   : OK")
except Exception as e:
    print(f"      SUMO launch     : FAILED — {e}")
    print()
    print("  Fix: set SUMO_HOME environment variable, e.g.:")
    print("    setx SUMO_HOME \"C:\\Program Files (x86)\\Eclipse\\Sumo\"")
    print("  Then close and reopen your terminal.")
    sys.exit(1)

# ── Step 4: observation shapes ────────────────────────────────────────────────
print("\n[4/7] Checking observation shapes...")
shape_ok = True
for jid in REAL_JUNCTIONS:
    expected = RAW_OBS_DIM[jid]
    actual   = obs[jid].shape[0]
    ok       = actual == expected
    if not ok:
        shape_ok = False
    print(f"      {jid:<10}  shape={actual}  {'OK' if ok else f'MISMATCH expected {expected}'}")

if not shape_ok:
    env.close()
    sys.exit(1)

# ── Step 5: 50 random-action steps ───────────────────────────────────────────
print("\n[5/7] Running 50 steps with random actions...")
rewards_seen = []
done = False
step = 0
for step in range(50):
    actions = {jid: np.random.randint(0, ACT_DIM[jid]) for jid in REAL_JUNCTIONS}
    obs, rews, done, info = env.step(actions)
    rewards_seen.extend(rews.values())
    if done:
        break
print(f"      Steps completed : {step + 1}")

# ── Step 6: reward range ──────────────────────────────────────────────────────
print("\n[6/7] Checking reward range [-1.0, 0.0]...")
r_min  = min(rewards_seen)
r_max  = max(rewards_seen)
r_mean = float(np.mean(rewards_seen))
in_range = r_min >= -1.001 and r_max <= 0.001
print(f"      min={r_min:.4f}  max={r_max:.4f}  mean={r_mean:.4f}  "
      f"{'OK' if in_range else 'WARNING: outside expected range'}")

# ── Step 7: close ─────────────────────────────────────────────────────────────
print("\n[7/7] Closing SUMO...")
env.close()
print("      Closed : OK")

print()
print("=" * 65)
if shape_ok and in_range:
    print("  ALL TESTS PASSED — safe to begin training")
    print()
    print("  Next steps (run from src/training/):")
    print()
    print("  1. Generate density files (one time, from sumo/scripts/):")
    print("       cd ..\\..\\sumo\\scripts")
    print("       python generate_density_routes.py")
    print("       cd ..\\..\\src\\training")
    print()
    print("  2. Train on peak-hour traffic first:")
    print("       python traci_env.py --episodes 500 --density high --save_dir ckpt_high")
    print()
    print("  3. Curriculum training (resume from above):")
    print("       python traci_env.py --episodes 1000 --curriculum --resume ckpt_high --save_dir ckpt_final")
    print()
    print("  4. Evaluate:")
    print("       python traci_env.py --eval_only --resume ckpt_final_best --density low")
    print("       python traci_env.py --eval_only --resume ckpt_final_best --density high")
else:
    print("  SOME TESTS FAILED — fix errors above before training")
print("=" * 65)