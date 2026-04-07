import os

# ============================================================
#   CONTINUOUS TRAFFIC GENERATOR - FIXED VERSION
#   All your routes with syntax errors corrected!
# ============================================================

ROUTE_FILE = "final_routes.rou.xml"
CONFIG_FILE = "run.sumocfg"
NET_FILE = "manhattan.net.xml"
POI_FILE = "manhattan_labels.poi.xml"

# Cleanup
for f in [ROUTE_FILE, CONFIG_FILE]:
    if os.path.exists(f):
        try:
            os.remove(f)
        except:
            pass

print(">>> GENERATING CONTINUOUS TRAFFIC...")

# Define routes
routes = []

# Straight-through routes
routes.append(("route_41w", "we_41_2 we_41_1 we_41_0", 120))
routes.append(("route_42e", "ew_42_0 ew_42_1 ew_42_2", 40))
routes.append(("route_42w", "we_42_2 we_42_1 we_42_0", 120))
routes.append(("route_43w", "we_43_2 we_43_1 we_43_0", 120))
routes.append(("route_44e", "ew_44_0 ew_44_1 ew_44_2", 120))          
routes.append(("route_9s", "ns_9th_2 ns_9th_1 ns_9th_0", 120))
routes.append(("route_8n", "sn_8th_0 sn_8th_1 sn_8th_2", 120))
routes.append(("route_7s", "ns_7th_2 ns_7th_1 ns_7th_0", 120))
routes.append(("route_6n", "sn_6th_0 sn_6th_1 sn_6th_2", 120))

# Turning routes
# At 42-9 (n_1_0):
routes.append(("turn_9s_to_42e", "ns_9th_2 ns_9th_1 ew_42_0 ew_42_1 ew_42_2", 40))
routes.append(("turn_42w_to_9s", "we_42_2 we_42_1 we_42_0 ns_9th_0", 40))

# At 42-8 (n_1_1):
routes.append(("turn_8n_to_42w", "sn_8th_0 we_42_0 ns_9th_0", 40))
routes.append(("turn_8n_to_42e", "sn_8th_0 ew_42_1 ew_42_2", 40))
routes.append(("turn_42e_to_8n", "ew_42_0 sn_8th_1 sn_8th_2", 40))
routes.append(("turn_42w_to_8n", "we_42_1 sn_8th_1 sn_8th_2", 40))

# At 42-7 (n_1_2):
routes.append(("turn_7s_to_42e", "ns_7th_2 ns_7th_1 ew_42_2", 40))
routes.append(("turn_7s_to_42w", "ns_7th_2 ns_7th_1 we_42_1 we_42_0", 40))
routes.append(("turn_42w_to_7s", "we_42_2 ns_7th_0 we_41_1 we_41_0", 40)) 
routes.append(("turn_42e_to_7s", "ew_42_0 ew_42_1 ns_7th_0 we_41_1 we_41_0", 40))

# At 42-6 (n_1_3):
routes.append(("turn_6n_to_42w", "sn_6th_0 we_42_2 we_42_1 we_42_0", 40))
routes.append(("turn_42e_to_6n", "ew_42_0 ew_42_1 ew_42_2 sn_6th_1 sn_6th_2", 120))

# At 43-9 (n_2_0):
routes.append(("turn_43w_to_9s", "we_43_0 ns_9th_1 ns_9th_0", 40))

# At 43-8 (n_2_1):
routes.append(("turn_43w_to_8n", "we_43_1 sn_8th_2 ew_44_1 ew_44_2", 40))
routes.append(("turn_8n_to_43w", "sn_8th_1 we_43_0 ns_9th_1 ns_9th_0", 40))

# At 43-7 (n_2_2):
routes.append(("turn_43w_to_7s", "we_43_2 ns_7th_1 ns_7th_0 we_41_1 we_41_0", 40)) ##
routes.append(("turn_7s_to_43w", "ns_7th_2 we_43_1 we_43_0 ns_9th_1", 40)) ##

# At 43-6 (n_2_3):
routes.append(("turn_6n_to_43w", "sn_6th_1 we_43_2 we_43_1 we_43_0", 40))

# At 44-8 (n_3_1):
routes.append(("turn_8n_to_44e", "sn_8th_2 ew_44_1 ew_44_2", 40))

# At 44-7 (n_3_2):
routes.append(("turn_44e_to_7s", "ew_44_0 ew_44_1 ns_7th_2 ns_7th_1 ns_7th_0 we_41_1 we_41_0", 30))##

# At 41-8 (n_0_1):
routes.append(("turn_41w_to_8n", "we_41_1 sn_8th_0 sn_8th_1 sn_8th_2 ew_44_1", 30))##
routes.append(("turn_7s_to_41w",  "ns_7th_0 we_41_1 we_41_0",30))

print(f">>> {len(routes)} routes defined")

# Write route file with CONTINUOUS flows
with open(ROUTE_FILE, "w") as f:
    f.write('<routes>\n\n')
    
    # Vehicle types
    f.write('    <vType id="car" length="5.0" minGap="2.5" maxSpeed="15.0" accel="2.0" decel="4.5" color="1,1,0" guiShape="passenger"/>\n')
    f.write('    <vType id="bike" length="2.2" minGap="1.5" maxSpeed="12.0" accel="1.5" decel="3.0" color="0,1,0" guiShape="motorcycle"/>\n')
    f.write('    <vType id="bus" length="13.0" minGap="3.0" maxSpeed="10.0" accel="1.0" decel="3.0" color="1,0,0" guiShape="bus"/>\n\n')
    
    # IMPORTANT: Define routes first
    f.write('    <!-- Route Definitions -->\n')
    for route_id, edges, vol in routes:
        f.write(f'    <route id="{route_id}" edges="{edges}"/>\n')
    
    # Then create flows that reference those routes
    f.write('\n    <!-- Vehicle Flows -->\n')
    flow_id = 0
    for route_id, edges, vol in routes:
        # Cars
        f.write(f'    <flow id="f_car_{flow_id}" type="car" route="{route_id}" '
               f'begin="0" vehsPerHour="{vol}" departLane="best" departSpeed="max"/>\n')
        
        # Bikes (half volume)
        f.write(f'    <flow id="f_bike_{flow_id}" type="bike" route="{route_id}" '
               f'begin="0" vehsPerHour="{vol//2}" departLane="best" departSpeed="max"/>\n')
        
        # Buses (quarter volume)
        f.write(f'    <flow id="f_bus_{flow_id}" type="bus" route="{route_id}" '
               f'begin="0" vehsPerHour="{vol//4}" departLane="best" departSpeed="max"/>\n')
        
        flow_id += 1

    f.write('\n</routes>\n')

# Write config file - NO END TIME!
with open(CONFIG_FILE, "w") as f:
    f.write('<configuration>\n')
    f.write('    <input>\n')
    f.write(f'        <net-file value="{NET_FILE}"/>\n')
    f.write(f'        <route-files value="{ROUTE_FILE}"/>\n')
    
    if os.path.exists(POI_FILE):
        f.write(f'        <additional-files value="{POI_FILE}"/>\n')
    
    f.write('    </input>\n')
    
    # CRITICAL: No end time = runs forever!
    f.write('    <time>\n')
    f.write('        <begin value="0"/>\n')
    f.write('    </time>\n')
    
    f.write('</configuration>\n')

print("\n" + "="*60)
print("  CONTINUOUS TRAFFIC COMPLETE!")
print("="*60)
print(f"\n✅ {len(routes)} routes")
print(f"✅ ~{sum(r[2] for r in routes) * 1.75:.0f} vehicles/hour total")
print(f"\n🔄 CONTINUOUS SIMULATION:")
print(f"   • NO end time - runs forever!")
print(f"   • Vehicles spawn continuously")
print(f"   • Traffic never stops")
print(f"\n🚦 TO RUN:")
print(f"   python Gridnetwork.py")
print(f"   python final_working_simulation.py")
print(f"   sumo-gui -c run.sumocfg")
print(f"\n⏹️  TO STOP:")
print(f"   Click Stop button or close window")