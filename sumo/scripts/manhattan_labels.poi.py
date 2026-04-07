import os

# ============================================================
#   QUICK FIX - Regenerate POI Labels Only
#   Fixes the imgFile error
# ============================================================

POI_FILE = "manhattan_labels.poi.xml"

N_ROWS = 4
N_COLS = 4
LEN_EW = 500.0
LEN_NS = 300.0

STREET_NAMES = {
    0: "41st Street",
    1: "42nd Street", 
    2: "43rd Street",
    3: "44th Street"
}

AVENUE_NAMES = {
    0: "9th Avenue",
    1: "8th Avenue",
    2: "7th Avenue",
    3: "6th Avenue"
}

print("Fixing POI labels (removing empty imgFile attribute)...")

with open(POI_FILE, "w") as f:
    f.write('<additional>\n')
    
    for row in range(N_ROWS):
        for col in range(N_COLS):
            x = col * LEN_EW
            y = row * LEN_NS
            
            street = STREET_NAMES[row]
            avenue = AVENUE_NAMES[col]
            intersection_name = f"{avenue} @\\n{street}"
            
            # FIXED: Removed imgFile and angle attributes
            f.write(f'    <poi id="label_n_{row}_{col}" type="intersection_label" '
                   f'x="{x}" y="{y + 30}" '
                   f'color="0,0,0" layer="100">{intersection_name}</poi>\n')
    
    f.write('</additional>\n')

print(f"\n✅ Fixed: {POI_FILE}")
print("✅ Now run: sumo-gui -c run.sumocfg")