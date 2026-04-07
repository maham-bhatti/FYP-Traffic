import os
import sys
import traci
import sumolib  # Needed for Traci3 logic
from collections import defaultdict

# ==========================================
#   MASTER TRACI CONTROLLER
#   Combines: Info, Control, Stats, & Tables
# ==========================================

# --- 1. ENVIRONMENT SETUP ---
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME'")

# File Config
NET_FILE = "manhattan.net.xml"  # map network
CONFIG_FILE = "run.sumocfg"     # sumo config

# --- 2. STATIC NETWORK ANALYSIS (From Traci3.py) ---
print("... ANALYZING STATIC NETWORK (Traci3 Logic)...")
try:
    net = sumolib.net.readNet(NET_FILE)
    speedsum = 0
    edgecount = 0
    for edge in net.getEdges():
        speedsum += edge.getSpeed()
        edgecount += 1
    
    avg_limit = speedsum / edgecount if edgecount > 0 else 0
    print(f"   - Total Edges: {edgecount}")
    print(f"   - Average Speed Limit across Map: {avg_limit:.2f} m/s")
except Exception as e:
    print(f"   - Warning: Could not analyze static network ({e})")

# --- 3. STARTING SIMULATION ---
sumoCmd = [
    'sumo-gui',
    '-c', CONFIG_FILE,
    '--step-length', '0.1',  # Slower steps for better visibility
    '--start'
]
traci.start(sumoCmd)

# --- 4. DATA HOLDERS ---
step_count = 0

def print_separator(title=""):
    print(f"\n{'='*20} {title} {'='*20}")

# --- MAIN LOOP ---
while traci.simulation.getMinExpectedNumber() > 0:
    traci.simulationStep()
    step_count += 1

    # Only print report every 10 steps to keep console readable
    if step_count % 10 != 0:
        continue

    # =======================================================
    #   DATA COLLECTION (Combining Traciinfo-1 & DetailTraci)
    # =======================================================
    
    # 1. Vehicle Data
    veh_ids = traci.vehicle.getIDList()
    
    # Categorize Vehicles
    data_by_type = defaultdict(list)
    total_sim_speed = 0
    
    for vid in veh_ids:
        v_type = traci.vehicle.getTypeID(vid) # 'car', 'bus', 'bike'
        speed = traci.vehicle.getSpeed(vid)
        pos = traci.vehicle.getPosition(vid)
        angle = traci.vehicle.getAngle(vid) # From Traci2
        
        # Store for table
        data_by_type[v_type].append({
            'id': vid,
            'speed': speed,
            'pos': pos,
            'angle': angle
        })
        
        total_sim_speed += speed

    # 2. Lane Data (From DetailTraci.py)
    lane_ids = traci.lane.getIDList()
    lane_stats = []
    
    total_queue = 0
    total_waiting = 0
    
    for lane in lane_ids:
        # Get queue (halting number) and waiting time
        queue = traci.lane.getLastStepHaltingNumber(lane)
        wait = traci.lane.getWaitingTime(lane)
        count = traci.lane.getLastStepVehicleNumber(lane)
        
        if count > 0 or queue > 0: # Only store interesting lanes
            lane_stats.append({
                'id': lane,
                'count': count,
                'queue': queue,
                'wait': wait
            })
            total_queue += queue
            total_waiting += wait

    # =======================================================
    #   REPORT GENERATION ("Proper Table")
    # =======================================================
    
    print("\n" * 50) # Clear console "fake" refresh
    print_separator(f"SIMULATION STEP: {step_count}")

    # --- TABLE 1: VEHICLE METRICS BY TYPE ---
    print(f"\n{'TYPE':<10} | {'ID':<10} | {'SPEED (m/s)':<12} | {'POSITION (X,Y)':<20} | {'ANGLE':<10}")
    print("-" * 70)
    
    # Calculate Averages for Summary
    type_summaries = {}
    
    for v_type, vehicles in data_by_type.items():
        type_speed_sum = 0
        for v in vehicles:
            # Print row
            pos_str = f"({v['pos'][0]:.1f}, {v['pos'][1]:.1f})"
            print(f"{v_type:<10} | {v['id']:<10} | {v['speed']:<12.2f} | {pos_str:<20} | {v['angle']:<10.1f}")
            type_speed_sum += v['speed']
        
        # Store avg for later
        avg = type_speed_sum / len(vehicles) if vehicles else 0
        type_summaries[v_type] = {'count': len(vehicles), 'avg_speed': avg}
        print("-" * 70)

    # --- TABLE 2: TRAFFIC DETAILS ---
    print_separator("NETWORK DETAILS")
    print(f"{'METRICS':<25} | {'VALUE':<15}")
    print("-" * 45)
    print(f"{'Total Vehicles':<25} | {len(veh_ids)}")
    print(f"{'Total Accum. Speed':<25} | {total_sim_speed:.2f} m/s")
    
    avg_all = total_sim_speed / len(veh_ids) if veh_ids else 0
    print(f"{'Avg Fleet Speed':<25} | {avg_all:.2f} m/s")
    print(f"{'Total Queue Length':<25} | {total_queue} vehs")
    print(f"{'Total Waiting Time':<25} | {total_waiting:.2f} s")

    # --- TABLE 3: TYPE BREAKDOWN ---
    print_separator("TYPE BREAKDOWN")
    print(f"{'TYPE':<10} | {'COUNT':<10} | {'AVG SPEED':<15}")
    print("-" * 45)
    for v_type, stats in type_summaries.items():
        print(f"{v_type:<10} | {stats['count']:<10} | {stats['avg_speed']:.2f} m/s")

    # --- TABLE 4: CONGESTED LANES (From DetailTraci) ---
    if lane_stats:
        print_separator("CONGESTED LANES (>0 Vehicles)")
        print(f"{'LANE ID':<20} | {'VEHS':<6} | {'QUEUE':<6} | {'WAIT(s)':<8}")
        print("-" * 50)
        # Sort by queue length descending
        lane_stats.sort(key=lambda x: x['queue'], reverse=True)
        
        for l in lane_stats[:5]: # Show top 5 worst lanes
            print(f"{l['id']:<20} | {l['count']:<6} | {l['queue']:<6} | {l['wait']:<8.1f}")

# --- 5. CLEANUP ---
traci.close()
print("\nSimulation Finished.")
