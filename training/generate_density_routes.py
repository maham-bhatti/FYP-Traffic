"""
generate_density_routes.py
==========================
Generates THREE route files for curriculum training:

  low_routes.rou.xml    — off-peak   (25% volume  ~850 veh/hr total)
  medium_routes.rou.xml — moderate   (50% volume  ~1700 veh/hr total)
  high_routes.rou.xml   — peak-hour  (100% volume ~3378 veh/hr total)

ALL THREE FILES CONTAIN: Cars + Bikes + Buses (same as final_routes.rou.xml)
Only the vehsPerHour values are scaled. Routes and vehicle types are identical.

Run once from sumo/scripts/:
  python generate_density_routes.py
"""

import os

ROUTES = [
    ("route_41w",  "we_41_2 we_41_1 we_41_0",                              120),
    ("route_42e",  "ew_42_0 ew_42_1 ew_42_2",                               40),
    ("route_42w",  "we_42_2 we_42_1 we_42_0",                              120),
    ("route_43w",  "we_43_2 we_43_1 we_43_0",                              120),
    ("route_44e",  "ew_44_0 ew_44_1 ew_44_2",                              120),
    ("route_9s",   "ns_9th_2 ns_9th_1 ns_9th_0",                           120),
    ("route_8n",   "sn_8th_0 sn_8th_1 sn_8th_2",                           120),
    ("route_7s",   "ns_7th_2 ns_7th_1 ns_7th_0",                           120),
    ("route_6n",   "sn_6th_0 sn_6th_1 sn_6th_2",                           120),
    ("turn_9s_to_42e",  "ns_9th_2 ns_9th_1 ew_42_0 ew_42_1 ew_42_2",       40),
    ("turn_42w_to_9s",  "we_42_2 we_42_1 we_42_0 ns_9th_0",                 40),
    ("turn_8n_to_42w",  "sn_8th_0 we_42_0 ns_9th_0",                        40),
    ("turn_8n_to_42e",  "sn_8th_0 ew_42_1 ew_42_2",                         40),
    ("turn_42e_to_8n",  "ew_42_0 sn_8th_1 sn_8th_2",                        40),
    ("turn_42w_to_8n",  "we_42_1 sn_8th_1 sn_8th_2",                        40),
    ("turn_7s_to_42e",  "ns_7th_2 ns_7th_1 ew_42_2",                        40),
    ("turn_7s_to_42w",  "ns_7th_2 ns_7th_1 we_42_1 we_42_0",                40),
    ("turn_42w_to_7s",  "we_42_2 ns_7th_0 we_41_1 we_41_0",                 40),
    ("turn_42e_to_7s",  "ew_42_0 ew_42_1 ns_7th_0 we_41_1 we_41_0",         40),
    ("turn_6n_to_42w",  "sn_6th_0 we_42_2 we_42_1 we_42_0",                 40),
    ("turn_42e_to_6n",  "ew_42_0 ew_42_1 ew_42_2 sn_6th_1 sn_6th_2",       120),
    ("turn_43w_to_9s",  "we_43_0 ns_9th_1 ns_9th_0",                        40),
    ("turn_43w_to_8n",  "we_43_1 sn_8th_2 ew_44_1 ew_44_2",                 40),
    ("turn_8n_to_43w",  "sn_8th_1 we_43_0 ns_9th_1 ns_9th_0",               40),
    ("turn_43w_to_7s",  "we_43_2 ns_7th_1 ns_7th_0 we_41_1 we_41_0",        40),
    ("turn_7s_to_43w",  "ns_7th_2 we_43_1 we_43_0 ns_9th_1",                40),
    ("turn_6n_to_43w",  "sn_6th_1 we_43_2 we_43_1 we_43_0",                 40),
    ("turn_8n_to_44e",  "sn_8th_2 ew_44_1 ew_44_2",                         40),
    ("turn_44e_to_7s",  "ew_44_0 ew_44_1 ns_7th_2 ns_7th_1 ns_7th_0 we_41_1 we_41_0", 30),
    ("turn_41w_to_8n",  "we_41_1 sn_8th_0 sn_8th_1 sn_8th_2 ew_44_1",      30),
    ("turn_7s_to_41w",  "ns_7th_0 we_41_1 we_41_0",                         30),
]

VTYPES = [
    ("car",  "5.0",  "2.5", "15.0", "2.0", "4.5", "1,1,0", "passenger"),
    ("bike", "2.2",  "1.5", "12.0", "1.5", "3.0", "0,1,0", "motorcycle"),
    ("bus",  "13.0", "3.0", "10.0", "1.0", "3.0", "1,0,0", "bus"),
]

DENSITIES = {
    "low":    {"file": "low_routes.rou.xml",    "scale": 0.25,
               "label": "Off-peak (~25% volume)",
               "real_world": "Early morning / late night / weekends"},
    "medium": {"file": "medium_routes.rou.xml", "scale": 0.50,
               "label": "Moderate (~50% volume)",
               "real_world": "Mid-morning / afternoon"},
    "high":   {"file": "high_routes.rou.xml",   "scale": 1.00,
               "label": "Peak-hour (100% volume)",
               "real_world": "Morning rush / evening rush"},
}


def write_route_file(density_name, cfg):
    filename = cfg["file"]
    scale    = cfg["scale"]
    stats    = {"cars": 0, "bikes": 0, "buses": 0}

    with open(filename, "w") as f:
        f.write(f'<!-- {cfg["label"]} | {cfg["real_world"]} -->\n')
        f.write('<routes>\n\n')

        f.write('    <!-- Vehicle Types — Cars + Bikes + Buses in ALL density files -->\n')
        for tid, length, mingap, maxspeed, accel, decel, color, shape in VTYPES:
            f.write(f'    <vType id="{tid}" length="{length}" minGap="{mingap}" '
                    f'maxSpeed="{maxspeed}" accel="{accel}" decel="{decel}" '
                    f'color="{color}" guiShape="{shape}"/>\n')
        f.write('\n')

        f.write('    <!-- Route Definitions — identical edges in all density files -->\n')
        for route_id, edges, _ in ROUTES:
            f.write(f'    <route id="{route_id}" edges="{edges}"/>\n')
        f.write('\n')

        f.write(f'    <!-- Flows scaled to {int(scale*100)}% of base volume -->\n')
        flow_id = 0
        for route_id, _, base_vol in ROUTES:
            car_vol  = max(1, int(base_vol * scale))
            bike_vol = max(1, car_vol // 2)
            bus_vol  = max(1, car_vol // 4)

            f.write(f'    <flow id="f_car_{flow_id}"  type="car"  route="{route_id}" '
                    f'begin="0" vehsPerHour="{car_vol}"  departLane="best" departSpeed="max"/>\n')
            f.write(f'    <flow id="f_bike_{flow_id}" type="bike" route="{route_id}" '
                    f'begin="0" vehsPerHour="{bike_vol}" departLane="best" departSpeed="max"/>\n')
            f.write(f'    <flow id="f_bus_{flow_id}"  type="bus"  route="{route_id}" '
                    f'begin="0" vehsPerHour="{bus_vol}"  departLane="best" departSpeed="max"/>\n')

            stats["cars"]  += car_vol
            stats["bikes"] += bike_vol
            stats["buses"] += bus_vol
            flow_id += 1

        f.write('\n</routes>\n')

    return stats


def main():
    print("=" * 65)
    print("  Density Route File Generator")
    print("  Cars + Bikes + Buses in ALL files")
    print("=" * 65)
    print()

    for density_name, cfg in DENSITIES.items():
        stats = write_route_file(density_name, cfg)
        size_kb = os.path.getsize(cfg["file"]) / 1024
        print(f"  ✅ {cfg['file']:<28} ({cfg['label']})")
        print(f"     Cars: {stats['cars']:5d} veh/hr | "
              f"Bikes: {stats['bikes']:4d} | Buses: {stats['buses']:4d} | "
              f"File: {size_kb:.1f} KB")
        print(f"     Real world: {cfg['real_world']}")
        print()

    print("=" * 65)
    print("  TRAINING PLAN — run from src/training/")
    print("=" * 65)
    print()
    print("  Stage 0 — Baseline (300 ep) — agent learns fundamentals")
    print("    python traci_env.py --episodes 300 --save_dir ckpt_base")
    print()
    print("  Stage 1 — Off-peak (200 ep) — learns quiet roads")
    print("    python traci_env.py --episodes 200 --density low")
    print("      --resume ckpt_base --save_dir ckpt_low")
    print()
    print("  Stage 2 — Moderate (200 ep) — mid-day conditions")
    print("    python traci_env.py --episodes 200 --density medium")
    print("      --resume ckpt_low --save_dir ckpt_med")
    print()
    print("  Stage 3 — Peak hour (400 ep) — hardest, most important")
    print("    python traci_env.py --episodes 400 --density high")
    print("      --resume ckpt_med --save_dir ckpt_high")
    print()
    print("  Final Evaluation (same model, all 3 densities)")
    print("    python traci_env.py --eval_only --resume ckpt_high_best --density low")
    print("    python traci_env.py --eval_only --resume ckpt_high_best")
    print("    python traci_env.py --eval_only --resume ckpt_high_best --density high")
    print("=" * 65)


if __name__ == "__main__":
    main()
