import random
import xml.etree.ElementTree as ET

# ================================================================
#   MANHATTAN TRAFFIC GENERATION WITH TURN PROBABILITIES
#   - 65% go straight
#   - 20% turn right
#   - 15% turn left
# ================================================================

# Turn probabilities
PROB_STRAIGHT = 0.65
PROB_RIGHT = 0.20
PROB_LEFT = 0.15

# Traffic scenario (change this or pass as command line argument)
SCENARIO = 'medium'  # Options: 'light', 'medium', 'heavy', 'variable'

SCENARIOS = {
    'light': {
        'veh_per_hour': 250,
        'description': 'Off-peak traffic'
    },
    'medium': {
        'veh_per_hour': 600,
        'description': 'Mid-day traffic (recommended for training)'
    },
    'heavy': {
        'veh_per_hour': 1000,
        'description': 'Peak hour traffic'
    },
    'variable': {
        'veh_per_hour': 'varies',
        'description': 'Variable traffic (250→600→1000 veh/hr)'
    }
}

# Define routes with turn types
# Format: (edges, turn_type, probability)
# turn_type: 's' = straight, 'r' = right, 'l' = left

ROUTES = [
    # STRAIGHT routes (65%)
    # East-West (streets)
    (("we_41_2", "we_41_1", "we_41_0"), 's', PROB_STRAIGHT),  # 41st full westbound
    (("ew_42_0", "ew_42_1", "ew_42_2"), 's', PROB_STRAIGHT),  # 42nd full eastbound
    (("we_42_2", "we_42_1", "we_42_0"), 's', PROB_STRAIGHT),  # 42nd full westbound
    (("we_43_2", "we_43_1", "we_43_0"), 's', PROB_STRAIGHT),  # 43rd full westbound
    (("ew_44_0", "ew_44_1", "ew_44_2"), 's', PROB_STRAIGHT),  # 44th full eastbound
    
    # North-South (avenues)
    (("ns_9th_2", "ns_9th_1", "ns_9th_0"), 's', PROB_STRAIGHT),   # 9th full southbound
    (("sn_8th_0", "sn_8th_1", "sn_8th_2"), 's', PROB_STRAIGHT),   # 8th full northbound
    (("ns_7th_2", "ns_7th_1", "ns_7th_0"), 's', PROB_STRAIGHT),   # 7th full southbound
    (("sn_6th_0", "sn_6th_1", "sn_6th_2"), 's', PROB_STRAIGHT),   # 6th full northbound
    
    # Partial straight routes (2 segments)
    (("we_41_2", "we_41_1"), 's', PROB_STRAIGHT),
    (("we_41_1", "we_41_0"), 's', PROB_STRAIGHT),
    (("ew_42_0", "ew_42_1"), 's', PROB_STRAIGHT),
    (("ew_42_1", "ew_42_2"), 's', PROB_STRAIGHT),
    (("ns_9th_2", "ns_9th_1"), 's', PROB_STRAIGHT),
    (("ns_9th_1", "ns_9th_0"), 's', PROB_STRAIGHT),
    (("sn_8th_0", "sn_8th_1"), 's', PROB_STRAIGHT),
    (("sn_8th_1", "sn_8th_2"), 's', PROB_STRAIGHT),
    
    # RIGHT TURN routes (20%)
    # From avenues to streets (turning right)
    (("ns_9th_2", "we_43_0"), 'r', PROB_RIGHT),    # 9th south → 43rd west (right)
    (("ns_9th_1", "we_42_0"), 'r', PROB_RIGHT),    # 9th south → 42nd west (right)
    (("ns_7th_2", "we_43_2"), 'r', PROB_RIGHT),    # 7th south → 43rd west (right)
    (("ns_7th_1", "we_42_2"), 'r', PROB_RIGHT),    # 7th south → 42nd west (right)
    (("sn_8th_0", "ew_42_0"), 'r', PROB_RIGHT),    # 8th north → 42nd east (right)
    (("sn_8th_1", "ew_44_0"), 'r', PROB_RIGHT),    # 8th north → 44th east (right)
    (("sn_6th_0", "ew_42_2"), 'r', PROB_RIGHT),    # 6th north → 42nd east (right)
    (("sn_6th_1", "ew_44_2"), 'r', PROB_RIGHT),    # 6th north → 44th east (right)
    
    # From streets to avenues (turning right)
    (("we_41_2", "ns_7th_0"), 'r', PROB_RIGHT),    # 41st west → 7th south (right)
    (("we_42_2", "ns_7th_1"), 'r', PROB_RIGHT),    # 42nd west → 7th south (right)
    (("we_43_2", "ns_7th_2"), 'r', PROB_RIGHT),    # 43rd west → 7th south (right)
    (("ew_42_0", "sn_8th_0"), 'r', PROB_RIGHT),    # 42nd east → 8th north (right)
    (("ew_44_0", "sn_8th_2"), 'r', PROB_RIGHT),    # 44th east → 8th north (right)
    
    # LEFT TURN routes (15%)
    # From avenues to streets (turning left)
    (("ns_9th_2", "ew_42_0"), 'l', PROB_LEFT),     # 9th south → 42nd east (left)
    (("ns_9th_1", "ew_44_0"), 'l', PROB_LEFT),     # 9th south → 44th east (left)
    (("ns_7th_2", "ew_42_2"), 'l', PROB_LEFT),     # 7th south → 42nd east (left)
    (("ns_7th_1", "ew_44_2"), 'l', PROB_LEFT),     # 7th south → 44th east (left)
    (("sn_8th_0", "we_41_0"), 'l', PROB_LEFT),     # 8th north → 41st west (left)
    (("sn_8th_1", "we_43_0"), 'l', PROB_LEFT),     # 8th north → 43rd west (left)
    (("sn_6th_0", "we_41_2"), 'l', PROB_LEFT),     # 6th north → 41st west (left)
    (("sn_6th_1", "we_43_2"), 'l', PROB_LEFT),     # 6th north → 43rd west (left)
    
    # From streets to avenues (turning left)
    (("we_41_1", "sn_8th_0"), 'l', PROB_LEFT),     # 41st west → 8th north (left)
    (("we_42_1", "sn_8th_1"), 'l', PROB_LEFT),     # 42nd west → 8th north (left)
    (("we_43_1", "sn_8th_2"), 'l', PROB_LEFT),     # 43rd west → 8th north (left)
    (("ew_42_1", "ns_7th_1"), 'l', PROB_LEFT),     # 42nd east → 7th south (left)
    (("ew_44_1", "ns_7th_2"), 'l', PROB_LEFT),     # 44th east → 7th south (left)
]

def generate_traffic(scenario='medium', sim_duration=3600, output_file='manhattan.rou.xml'):
    """
    Generate traffic with realistic turn probabilities.
    
    Args:
        scenario: 'light', 'medium', 'heavy', or 'variable'
        sim_duration: Simulation time in seconds (default 3600 = 1 hour)
        output_file: Output route file name
    """
    
    print("\n" + "="*70)
    print("  MANHATTAN TRAFFIC WITH TURN PROBABILITIES")
    print(f"  Scenario: {SCENARIOS[scenario]['description']}")
    print(f"  Turn Distribution: {PROB_STRAIGHT*100:.0f}% straight, {PROB_RIGHT*100:.0f}% right, {PROB_LEFT*100:.0f}% left")
    print("="*70 + "\n")
    
    # Create XML root
    root = ET.Element('routes')
    
    # Define vehicle type
    vtype = ET.SubElement(root, 'vType')
    vtype.set('id', 'car')
    vtype.set('accel', '2.6')
    vtype.set('decel', '4.5')
    vtype.set('sigma', '0.5')
    vtype.set('length', '5.0')
    vtype.set('maxSpeed', '16.8')
    vtype.set('color', 'yellow')
    
    # Create weighted route list based on probabilities
    weighted_routes = []
    for idx, (edges, turn_type, prob) in enumerate(ROUTES):
        # Add this route multiple times based on probability
        # Scale by 100 to get whole numbers
        count = int(prob * 100)
        for _ in range(count):
            weighted_routes.append((f'route_{idx}', edges, turn_type))
    
    # Define routes
    route_definitions = {}
    for route_id, edges, turn_type in weighted_routes:
        if route_id not in route_definitions:
            route = ET.SubElement(root, 'route')
            route.set('id', route_id)
            route.set('edges', ' '.join(edges))
            route_definitions[route_id] = turn_type
    
    # Generate vehicles based on scenario
    vehicle_id = 0
    turn_counts = {'s': 0, 'r': 0, 'l': 0}
    
    if scenario == 'variable':
        # Variable traffic: increases from light to heavy
        print("📊 Variable traffic pattern:")
        print("   0-1200s:   Light (250 veh/hr)")
        print("   1200-2400s: Medium (600 veh/hr)")
        print("   2400-3600s: Heavy (1000 veh/hr)\n")
        
        time_periods = [
            (0, 1200, 250),
            (1200, 2400, 600),
            (2400, 3600, 1000),
        ]
        
        for start_time, end_time, veh_per_hour in time_periods:
            interval = 3600 / veh_per_hour
            current_time = start_time
            
            while current_time < end_time:
                # Random route weighted by probability
                route_id, edges, turn_type = random.choice(weighted_routes)
                
                # Create vehicle
                vehicle = ET.SubElement(root, 'vehicle')
                vehicle.set('id', f'veh_{vehicle_id}')
                vehicle.set('type', 'car')
                vehicle.set('route', route_id)
                vehicle.set('depart', f'{current_time:.2f}')
                vehicle.set('departLane', 'best')
                vehicle.set('departSpeed', 'max')
                
                turn_counts[turn_type] += 1
                vehicle_id += 1
                current_time += interval + random.uniform(-interval*0.3, interval*0.3)
    
    else:
        # Fixed traffic rate
        veh_per_hour = SCENARIOS[scenario]['veh_per_hour']
        interval = 3600 / veh_per_hour
        
        print(f"📊 Traffic details:")
        print(f"   Vehicles/hour: {veh_per_hour}")
        print(f"   Average interval: {interval:.2f}s\n")
        
        current_time = 0
        while current_time < sim_duration:
            # Random route weighted by probability
            route_id, edges, turn_type = random.choice(weighted_routes)
            
            # Create vehicle
            vehicle = ET.SubElement(root, 'vehicle')
            vehicle.set('id', f'veh_{vehicle_id}')
            vehicle.set('type', 'car')
            vehicle.set('route', route_id)
            vehicle.set('depart', f'{current_time:.2f}')
            vehicle.set('departLane', 'best')
            vehicle.set('departSpeed', 'max')
            
            turn_counts[turn_type] += 1
            vehicle_id += 1
            current_time += interval + random.uniform(-interval*0.3, interval*0.3)
    
    # Write to file
    tree = ET.ElementTree(root)
    ET.indent(tree, space='    ')
    tree.write(output_file, encoding='UTF-8', xml_declaration=True)
    
    # Print statistics
    total = sum(turn_counts.values())
    print(f"✅ Generated {vehicle_id} vehicles")
    print(f"\n📊 Turn distribution:")
    print(f"   Straight: {turn_counts['s']:4d} ({turn_counts['s']/total*100:5.1f}%) [target: 65%]")
    print(f"   Right:    {turn_counts['r']:4d} ({turn_counts['r']/total*100:5.1f}%) [target: 20%]")
    print(f"   Left:     {turn_counts['l']:4d} ({turn_counts['l']/total*100:5.1f}%) [target: 15%]")
    print(f"\n💾 Saved to: {output_file}")
    
    print("\n" + "="*70)
    print("  ✅ TRAFFIC GENERATION COMPLETE")
    print("="*70 + "\n")
    
    return vehicle_id

if __name__ == "__main__":
    import sys
    
    # Get scenario from command line or use default
    if len(sys.argv) > 1:
        scenario = sys.argv[1].lower()
        if scenario not in SCENARIOS:
            print(f"❌ Invalid scenario: {scenario}")
            print(f"   Valid options: {', '.join(SCENARIOS.keys())}")
            sys.exit(1)
    else:
        scenario = SCENARIO  # Use default
        print(f"💡 Using default scenario: {scenario}")
        print(f"   Usage: python generate_traffic_with_turns.py [light|medium|heavy|variable]\n")
    
    # Generate traffic
    generate_traffic(scenario=scenario, sim_duration=3600)
    
    print("\n🚀 Next steps:")
    print("   1. Verify: sumo-gui -c run.sumocfg")
    print("   2. Watch vehicle turns at intersections")
    print("   3. Start training: python train_mappo.py")
    print("="*70 + "\n")