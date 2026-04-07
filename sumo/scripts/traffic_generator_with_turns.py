import os

# ============================================================
#   HIGH DENSITY TRAFFIC GENERATOR WITH TURNING MOVEMENTS
#   Based on working final_working_simulation_ENHANCED.py
# ============================================================

ROUTE_FILE = "final_routes.rou.xml"
CONFIG_FILE = "run.sumocfg"
NET_FILE  = "manhattan.net.xml"
POI_FILE = "manhattan_labels.poi.xml"
GUI_FILE = "manhattan.gui.xml"

# 1. CLEANUP 
if os.path.exists(ROUTE_FILE):
    try:
        os.remove(ROUTE_FILE)
    except:
        print("⚠️ Could not delete route file (will overwrite)")
        
if os.path.exists(CONFIG_FILE):
    try:
        os.remove(CONFIG_FILE)
    except:
        print("⚠️ Could not delete config file (will overwrite)")

# 2. DEFINE ROUTES WITH TURNING MOVEMENTS
route_definitions = []

# Traffic volumes
VOL_STRAIGHT = 120  # 65% - going straight
VOL_TURN = 40       # 35% - turning (left + right combined)

print(f">>> GENERATING TRAFFIC WITH TURNING MOVEMENTS...")

# ============================================================
# A. HORIZONTAL TRAFFIC (STREETS) - WITH TURNS
# ============================================================

# 41st Street (Westbound) - with turns
route_definitions.append(("we_41_2", "we_41_0", VOL_STRAIGHT))  # Straight through

# 42nd Street (Both directions) - with turns
route_definitions.append(("ew_42_0", "ew_42_2", VOL_STRAIGHT))  # East straight
route_definitions.append(("we_42_2", "we_42_0", VOL_STRAIGHT))  # West straight

# 43rd Street (Westbound) - with turns
route_definitions.append(("we_43_2", "we_43_0", VOL_STRAIGHT))  # Straight through

# 44th Street (Eastbound) - with turns
route_definitions.append(("ew_44_0", "ew_44_2", VOL_STRAIGHT))  # Straight through

# ============================================================
# B. VERTICAL TRAFFIC (AVENUES) - WITH TURNS
# ============================================================

# 9th Avenue (Southbound) - with turns
route_definitions.append(("ns_9th_2", "ns_9th_0", VOL_STRAIGHT))  # Straight through

# 8th Avenue (Northbound) - with turns
route_definitions.append(("sn_8th_0", "sn_8th_2", VOL_STRAIGHT))  # Straight through

# 7th Avenue (Southbound) - with turns
route_definitions.append(("ns_7th_2", "ns_7th_0", VOL_STRAIGHT))  # Straight through

# 6th Avenue (Northbound) - with turns
route_definitions.append(("sn_6th_0", "sn_6th_2", VOL_STRAIGHT))  # Straight through

# ============================================================
# C. TURNING ROUTES AT INTERSECTIONS
# ============================================================

# These routes represent vehicles turning at intersections
# Using the same from→to pattern as your working code

# 42nd & 9th: Turns
route_definitions.append(("ns_9th_2", "ew_42_2", VOL_TURN))  # 9th south → turn left → 42nd east

route_definitions.append(("we_42_2", "ns_9th_2", VOL_TURN)) # 42nd W turn towards 9th south

# 42nd & 8th: Turns
route_definitions.append(("sn_8th_0", "we_42_0", VOL_TURN))  # 8th north → turn left → 42nd west
#route_definitions.append(("sn_8th_0", "
route_definitions.append(("ew_42_0", "sn_8th_2", VOL_TURN))  # 42nd east → turn left → 8th north

route_definitions.append(("we_42_0","sn_8th_2",VOL_TURN)) # Tke turn on 42W to N8th ave

# 42nd & 7th: Turns
route_definitions.append(("ns_7th_2", "ew_42_2", VOL_TURN))  # 7th south → turn left → 42nd east

route_definitions.append(("ns_7th_2", "we_42_2", VOL_TURN)) # 7 make turn to 42 W 
route_definitions.append(("we_42_2", "ns_7th_0", VOL_TURN))  # 42nd west → turn right → 7th south
route_definitions.append(("ew_42_2", "ns_7th_0",VOL_TURN)) # 42 E make turn to 7 ave

# 42nd & 6th: Turns  
route_definitions.append(("sn_6th_0", "we_42_2", VOL_TURN))  # 6th north → turn left → 42nd west
route_definitions.append(("ew_42_2", "sn_6th_0",VOL_TURN))

# 44th & 9th: Turns
route_definitions.append(("ew_44_0", "ns_7th_0", VOL_TURN))  # 44th east → turn right → 7th south

# 41st & 6th: Turns
route_definitions.append(("we_41_2", "sn_6th_2", VOL_TURN))  # 41st west → turn right → 6th north

# Additional turning movements for complete coverage
route_definitions.append(("ns_9th_2", "we_43_0", VOL_TURN))  # 9th → 43rd
route_definitions.append(("sn_8th_0", "ew_42_1", VOL_TURN))  # 8th → 42nd east mid
route_definitions.append(("ns_7th_2", "we_43_1", VOL_TURN))  # 7th → 43rd mid
route_definitions.append(("ew_44_0", "ns_9th_1", VOL_TURN))  # 44th → 9th mid

print(f">>> Total routes defined: {len(route_definitions)}")

# 3. GENERATE TRAFFIC FLOWS 
with open(ROUTE_FILE, "w") as f:
    f.write('<routes>\n')
    
    # Define Vehicles (EXACT same as working code)
    f.write('    <vType id="car"  length="5.0"  minGap="2.5" maxSpeed="15.0" accel="2.0" decel="4.5" color="1,1,0" guiShape="passenger"/>\n')
    f.write('    <vType id="bike" length="2.2"  minGap="1.5" maxSpeed="12.0" accel="1.5" decel="3.0" color="0,1,0" guiShape="motorcycle"/>\n')
    f.write('    <vType id="bus"  length="13.0" minGap="3.0" maxSpeed="10.0" accel="1.0" decel="3.0" color="1,0,0" guiShape="bus"/>\n')
    
    flow_id = 0
    for start, end, volume in route_definitions:
        # Cars
        f.write(f'    <flow id="f_car_{flow_id}" type="car" begin="0" end="3600" number="{volume}" from="{start}" to="{end}" departLane="random" departSpeed="max"/>\n')
        
        # Bikes (half the volume)
        bike_volume = volume // 2
        f.write(f'    <flow id="f_bike_{flow_id}" type="bike" begin="0" end="3600" number="{bike_volume}" from="{start}" to="{end}" departLane="random" departSpeed="max"/>\n')
        
        # Buses (quarter the volume)
        bus_volume = volume // 4
        f.write(f'    <flow id="f_bus_{flow_id}" type="bus" begin="0" end="3600" number="{bus_volume}" from="{start}" to="{end}" departLane="random" departSpeed="max"/>\n')
        
        flow_id += 1

    f.write('</routes>\n')

# 4. CONFIGURATION (EXACT same as working code)
print(">>> GENERATING CONFIGURATION...")

with open(CONFIG_FILE, "w") as f:
    f.write('<configuration>\n')
    
    # Input files
    f.write('    <input>\n')
    f.write(f'        <net-file value="{NET_FILE}"/>\n')
    f.write(f'        <route-files value="{ROUTE_FILE}"/>\n')
    
    # Add POI file if it exists
    if os.path.exists(POI_FILE):
        f.write(f'        <additional-files value="{POI_FILE}"/>\n')
    
    # Add GUI settings if it exists
    if os.path.exists(GUI_FILE):
        f.write(f'        <gui-settings-file value="{GUI_FILE}"/>\n')
    
    f.write('    </input>\n')
    
    # Time settings
    f.write('    <time>\n')
    f.write('        <begin value="0"/>\n')
    f.write('        <end value="3600"/>\n')
    f.write('    </time>\n')
    
    # GUI settings
    f.write('    <gui_only>\n')
    f.write('        <start value="true"/>\n')
    f.write('        <quit-on-end value="false"/>\n')
    f.write('    </gui_only>\n')
    
    f.write('</configuration>\n')

# 5. SUMMARY
total_vehicles = sum(vol for _, _, vol in route_definitions)
total_with_all_types = total_vehicles + (total_vehicles // 2) + (total_vehicles // 4)  # cars + bikes + buses

print("\n" + "="*60)
print("  TRAFFIC GENERATION COMPLETE!")
print("="*60)
print(f"\n✅ Routes: {len(route_definitions)}")
print(f"✅ Total vehicles/hour: ~{total_with_all_types}")
print(f"\n📊 Movements:")
print(f"   • Straight-through routes: {len([r for r in route_definitions if r[2] == VOL_STRAIGHT])}")
print(f"   • Turning routes: {len([r for r in route_definitions if r[2] == VOL_TURN])}")
print(f"\n🚦 TO VIEW:")
print(f"   1. sumo-gui -c run.sumocfg")
print(f"   2. Watch vehicles turning at intersections!")
print("="*60 + "\n")
