import os
import xml.etree.ElementTree as ET
import shutil

# ==========================================
#   MANHATTAN GRID NETWORK GENERATOR
#   WITH EMBEDDED TLS FIX
#
#   ROOT CAUSE OF THE BUG:
#   netconvert generates 7 internal lanes at 42nd St intersections
#   but only a 5-char phase string (GGGrr). 42nd St connections get
#   internal via-lanes at intLanes positions 5 & 6 — OUTSIDE the
#   5-char string. SUMO defaults anything outside the string to GREEN,
#   so 42nd St vehicles never stop no matter what state='o'/'O'/'r'
#   you put on the connection element — because the INTERNAL GATE
#   at position 5,6 is always open.
#
#   THE FIX (applied automatically after netconvert):
#   - Reassign 42nd St connections to linkIndex 5, 6
#   - Expand phase string to 7 chars:
#       Phase 0: GGGGGrr  (avenue green,  42nd red)
#       Phase 1: yyyyyrr  (avenue yellow, 42nd red)
#       Phase 2: rrrrrGG  (avenue red,    42nd green)
#       Phase 3: rrrrryy  (avenue red,    42nd yellow)
#   - Reorder intLanes so street via-lanes are at positions 5,6
#   - This makes SUMO's internal gate CLOSED for 42nd St on red
# ==========================================

N_ROWS     = 4
N_COLS     = 4
LEN_EW     = 500.0
LEN_NS     = 300.0
SPEED_FAST = 16.8
SPEED_NORM = 13.9

NODE_FILE = "manhattan.nod.xml"
EDGE_FILE = "manhattan.edg.xml"
NET_FILE  = "manhattan.net.xml"
POI_FILE  = "manhattan_labels.poi.xml"
CONFIG_FILE = "run.sumocfg"

# Simulation duration: 1 hour = 3600 seconds (for training episodes)
SIM_DURATION = 3600

STREET_NAMES = {0: "41st Street", 1: "42nd Street", 2: "43rd Street", 3: "44th Street"}
AVENUE_NAMES = {0: "9th Avenue",  1: "8th Avenue",  2: "7th Avenue",  3: "6th Avenue"}


# ─────────────────────────────────────────
#  NETWORK GENERATION
# ─────────────────────────────────────────

def generate_nodes():
    print("Writing Nodes...")
    with open(NODE_FILE, "w") as f:
        f.write("<nodes>\n")
        for row in range(N_ROWS):
            for col in range(N_COLS):
                x, y = col * LEN_EW, row * LEN_NS
                name = f"{AVENUE_NAMES[col]} @ {STREET_NAMES[row]}"
                f.write(f'    <node id="n_{row}_{col}" x="{x}" y="{y}" '
                        f'type="traffic_light" name="{name}"/>\n')
        f.write("</nodes>\n")


def generate_edges():
    print("Writing Edges...")
    with open(EDGE_FILE, "w") as f:
        f.write("<edges>\n")
        for row in range(N_ROWS):
            for col in range(N_COLS - 1):
                left  = f"n_{row}_{col}"
                right = f"n_{row}_{col+1}"
                if row == 0:
                    f.write(f'    <edge id="we_41_{col}" from="{right}" to="{left}" '
                            f'numLanes="2" speed="{SPEED_NORM}"/>\n')
                elif row == 1:
                    f.write(f'    <edge id="ew_42_{col}" from="{left}" to="{right}" '
                            f'numLanes="2" speed="{SPEED_FAST}"/>\n')
                    f.write(f'    <edge id="we_42_{col}" from="{right}" to="{left}" '
                            f'numLanes="2" speed="{SPEED_FAST}"/>\n')
                elif row == 2:
                    f.write(f'    <edge id="we_43_{col}" from="{right}" to="{left}" '
                            f'numLanes="2" speed="{SPEED_NORM}"/>\n')
                elif row == 3:
                    f.write(f'    <edge id="ew_44_{col}" from="{left}" to="{right}" '
                            f'numLanes="2" speed="{SPEED_NORM}"/>\n')

        for row in range(N_ROWS - 1):
            for col in range(N_COLS):
                bottom = f"n_{row}_{col}"
                top    = f"n_{row+1}_{col}"
                if col == 0:
                    f.write(f'    <edge id="ns_9th_{row}" from="{top}" to="{bottom}" '
                            f'numLanes="3" speed="{SPEED_FAST}"/>\n')
                elif col == 1:
                    f.write(f'    <edge id="sn_8th_{row}" from="{bottom}" to="{top}" '
                            f'numLanes="3" speed="{SPEED_FAST}"/>\n')
                elif col == 2:
                    f.write(f'    <edge id="ns_7th_{row}" from="{top}" to="{bottom}" '
                            f'numLanes="3" speed="{SPEED_FAST}"/>\n')
                elif col == 3:
                    f.write(f'    <edge id="sn_6th_{row}" from="{bottom}" to="{top}" '
                            f'numLanes="3" speed="{SPEED_FAST}"/>\n')
        f.write("</edges>\n")


def build_network():
    print("Compiling Network with netconvert...")
    command = (
        f"netconvert "
        f"--node-files {NODE_FILE} "
        f"--edge-files {EDGE_FILE} "
        f"--output-file {NET_FILE} "
        f"--no-turnarounds true "
        f"--tls.guess true "
        f"--tls.cycle.time 90 "
        f"--tls.yellow.time 3 "
        f"--tls.left-green.time 12 "
        f"--tls.minor-left.max-speed 13.9 "
        f"--output.street-names true"
    )
    print(f"\n{command}\n")
    ret = os.system(command)
    if ret != 0 or not os.path.exists(NET_FILE):
        raise RuntimeError("netconvert failed — check SUMO installation.")
    print(f"\n✅ Raw network created: {NET_FILE}")


def generate_poi_labels():
    print("Writing Labels...")
    with open(POI_FILE, "w") as f:
        f.write('<additional>\n')
        for row in range(N_ROWS):
            for col in range(N_COLS):
                x, y = col * LEN_EW, row * LEN_NS
                name = f"{AVENUE_NAMES[col]} @\\n{STREET_NAMES[row]}"
                f.write(f'    <poi id="label_n_{row}_{col}" x="{x}" y="{y+30}" '
                        f'color="0,0,0" layer="100">{name}</poi>\n')
        f.write('</additional>\n')


def generate_sumo_config():
    """Generate SUMO configuration file with 1 hour duration."""
    print("Writing SUMO Configuration...")
    with open(CONFIG_FILE, "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<configuration>\n')
        f.write('    <input>\n')
        f.write(f'        <net-file value="{NET_FILE}"/>\n')
        f.write('        <route-files value="final_routes.rou.xml"/>\n')
        f.write('    </input>\n')
        f.write('    <time>\n')
        f.write('        <begin value="0"/>\n')
        f.write(f'        <end value="{SIM_DURATION}"/>\n')
        f.write('        <step-length value="1"/>\n')
        f.write('    </time>\n')
        f.write('    <processing>\n')
        f.write('        <time-to-teleport value="-1"/>\n')
        f.write('    </processing>\n')
        f.write('</configuration>\n')
    
    print(f"✅ Config created: {CONFIG_FILE}")
    print(f"   Duration: {SIM_DURATION} seconds ({SIM_DURATION/60:.0f} minutes)")


# ─────────────────────────────────────────
#  EMBEDDED TLS FIX  (runs automatically)
# ─────────────────────────────────────────

def _fix_junction(root, junction_id, avenue_edge, street_edge):
    """
    Reassign linkIndex for one 42nd-St junction so that the street
    connections land at positions INSIDE the expanded phase string.
    """
    # Fetch all TLS connections for this junction
    all_tls = root.findall(f".//connection[@tl='{junction_id}']")
    av_conns = [c for c in all_tls if c.get('from') == avenue_edge]
    st_conns = [c for c in all_tls if c.get('from') == street_edge]

    if not st_conns:
        print(f"    ⚠  {junction_id}: no connections found for {street_edge} — skip")
        return False

    # Remove exact-duplicate avenue connections (same from/fromLane/to/dir)
    parent_map = {child: parent for parent in root.iter() for child in parent}
    seen_keys  = set()
    for c in list(av_conns):
        key = (c.get('from'), c.get('fromLane'), c.get('to'), c.get('dir', ''))
        if key in seen_keys:
            p = parent_map.get(c)
            if p is not None:
                p.remove(c)
                av_conns.remove(c)
        else:
            seen_keys.add(key)

    # Assign avenue → linkIndex 0..n-1
    for i, c in enumerate(av_conns):
        c.set('linkIndex', str(i))
        c.set('state', 'o')

    n = len(av_conns)  # typically 5

    # Assign street → linkIndex n, n+1
    for i, c in enumerate(st_conns):
        c.set('linkIndex', str(n + i))
        c.set('tl',   junction_id)
        c.set('state', 'r')       # red at sim start

    total = n + len(st_conns)    # typically 7

    # Build new phase strings
    av_G = 'G' * n + 'r' * len(st_conns)
    av_y = 'y' * n + 'r' * len(st_conns)
    st_G = 'r' * n + 'G' * len(st_conns)
    st_y = 'r' * n + 'y' * len(st_conns)

    tl_elem = root.find(f".//tlLogic[@id='{junction_id}']")
    if tl_elem is not None:
        phases = tl_elem.findall('phase')
        target = [av_G, av_y, st_G, st_y]
        if len(phases) >= 4:
            for ph, st in zip(phases[:4], target):
                ph.set('state', st)
        else:
            for ph in phases:
                tl_elem.remove(ph)
            for state, dur in zip(target, [42, 3, 42, 3]):
                e = ET.SubElement(tl_elem, 'phase')
                e.set('duration', str(dur))
                e.set('state', state)

    # Fix intLanes ordering: avenue via-lanes first, then street via-lanes
    junction = root.find(f".//junction[@id='{junction_id}']")
    if junction is not None:
        existing = junction.get('intLanes', '').split()
        av_via   = [c.get('via') for c in av_conns if c.get('via')]
        st_via   = [c.get('via') for c in st_conns if c.get('via')]
        seen_il, new_il = set(), []
        for v in av_via + st_via:
            if v and v not in seen_il:
                new_il.append(v); seen_il.add(v)
        for v in existing:
            if v not in seen_il:
                new_il.append(v); seen_il.add(v)
        junction.set('intLanes', ' '.join(new_il))

    print(f"    ✅ {junction_id}: {total} links — "
          f"avenue idx 0-{n-1} = '{av_G[:n]}', street idx {n}-{total-1} = 'rr→GG'")
    return True


def _add_third_lane_n_0_2(root):
    """
    Fix n_0_2 (41st St & 7th Ave).
    - Adds 3rd internal lane if missing
    - Always reassigns linkIndex for ALL connections (prevents duplicate index bug)
    - Always resets TLS phase strings to correct 5-char values
    """
    # ── Add 3rd lane if missing ───────────────────────────────────────────────
    for edge in root.findall(".//edge[@id=':n_0_2_0']"):
        if len(edge.findall('lane')) < 3:
            new_lane = ET.SubElement(edge, 'lane')
            new_lane.set('id',     ':n_0_2_0_2')
            new_lane.set('index',  '2')
            new_lane.set('speed',  '8.10')
            new_lane.set('length', '14.57')
            new_lane.set('shape',  '998.40,10.40 997.65,6.55 995.40,3.80 991.65,2.15 986.40,1.60')

    for junction in root.findall(".//junction[@id='n_0_2']"):
        intlanes = junction.get('intLanes', '')
        if ':n_0_2_0_2' not in intlanes:
            junction.set('intLanes', intlanes.replace(':n_0_2_0_1', ':n_0_2_0_1 :n_0_2_0_2'))

        # Always clear ALL requests and rebuild from scratch
        # This prevents duplicate index=2 which causes SUMO assertion error
        for r in junction.findall('request'):
            junction.remove(r)
        correct_requests = [
            {'index':'0', 'response':'00000', 'foes':'11000', 'cont':'0'},
            {'index':'1', 'response':'00000', 'foes':'11000', 'cont':'0'},
            {'index':'2', 'response':'00000', 'foes':'11000', 'cont':'0'},
            {'index':'3', 'response':'00111', 'foes':'00111', 'cont':'0'},
            {'index':'4', 'response':'00111', 'foes':'00111', 'cont':'0'},
        ]
        for attrs in correct_requests:
            r = ET.SubElement(junction, 'request')
            for k, v in attrs.items():
                r.set(k, v)

    # ── Always reassign linkIndex to prevent duplicate-index bug ─────────────
    # ns_7th_0 (7th Ave approach): lane 0→idx0, lane 1→idx1, lane 2→idx2
    # we_41_2  (41st St approach): lane 0→idx3, lane 1→idx4
    ns7_idx = 0
    we41_idx = 3
    for c in root.findall(".//connection[@tl='n_0_2']"):
        frm = c.get('from', '')
        if frm == 'ns_7th_0':
            c.set('linkIndex', str(ns7_idx))
            ns7_idx += 1
        elif frm == 'we_41_2':
            c.set('linkIndex', str(we41_idx))
            we41_idx += 1

    # ── Always reset phase strings (5 links: idx 0-2=ave, 3-4=street) ───────
    _set_phases(root, 'n_0_2', ['GGGrr', 'yyyrr', 'rrrGG', 'rrryy'])

    # ── Add external connection lane 2 if missing ─────────────────────────────
    exists = any(True for c in root.findall(
        ".//connection[@from='ns_7th_0'][@to='we_41_1'][@fromLane='2']"))
    if not exists:
        last = None
        for c in root.findall(".//connection[@from='ns_7th_0'][@to='we_41_1']"):
            last = c
        if last is not None:
            parent = _parent_of(root, last)
            nc = ET.Element('connection')
            for k, v in [('from','ns_7th_0'),('to','we_41_1'),('fromLane','2'),
                         ('toLane','1'),('via',':n_0_2_0_2'),('tl','n_0_2'),
                         ('linkIndex','2'),('dir','r'),('state','o')]:
                nc.set(k, v)
            parent.insert(list(parent).index(last)+1, nc)

    # ── Add internal connection if missing ────────────────────────────────────
    exists_i = any(True for c in root.findall(
        ".//connection[@from=':n_0_2_0'][@to='we_41_1'][@fromLane='2']"))
    if not exists_i:
        last_i = None
        for c in root.findall(".//connection[@from=':n_0_2_0'][@to='we_41_1']"):
            last_i = c
        if last_i is not None:
            parent = _parent_of(root, last_i)
            nc = ET.Element('connection')
            for k, v in [('from',':n_0_2_0'),('to','we_41_1'),('fromLane','2'),
                         ('toLane','1'),('dir','r'),('state','M')]:
                nc.set(k, v)
            parent.insert(list(parent).index(last_i)+1, nc)

    print("  ✅ n_0_2 (41st & 7th): linkIndex reassigned, phases GGGrr/yyyrr/rrrGG/rrryy")


def _add_third_lane_n_3_1(root):
    """
    Fix n_3_1 (44th St & 8th Ave).
    - Adds 3rd internal lane if missing
    - Always reassigns linkIndex for ALL connections (prevents duplicate index bug)
    - Always resets TLS phase strings to correct 5-char values
    """
    # ── Add 3rd lane if missing ───────────────────────────────────────────────
    for edge in root.findall(".//edge[@id=':n_3_1_0']"):
        if len(edge.findall('lane')) < 3:
            new_lane = ET.SubElement(edge, 'lane')
            new_lane.set('id',     ':n_3_1_0_2')
            new_lane.set('index',  '2')
            new_lane.set('speed',  '8.10')
            new_lane.set('length', '14.57')
            new_lane.set('shape',  '501.60,889.60 502.35,893.45 504.60,896.20 508.35,897.85 513.60,898.40')

    for junction in root.findall(".//junction[@id='n_3_1']"):
        intlanes = junction.get('intLanes', '')
        if ':n_3_1_0_2' not in intlanes:
            junction.set('intLanes', intlanes.replace(':n_3_1_0_1', ':n_3_1_0_1 :n_3_1_0_2'))

        # Always clear ALL requests and rebuild from scratch
        # This prevents duplicate index=2 which causes SUMO assertion error
        for r in junction.findall('request'):
            junction.remove(r)
        correct_requests = [
            {'index':'0', 'response':'00000', 'foes':'11000', 'cont':'0'},
            {'index':'1', 'response':'00000', 'foes':'11000', 'cont':'0'},
            {'index':'2', 'response':'00000', 'foes':'11000', 'cont':'0'},
            {'index':'3', 'response':'00111', 'foes':'00111', 'cont':'0'},
            {'index':'4', 'response':'00111', 'foes':'00111', 'cont':'0'},
        ]
        for attrs in correct_requests:
            r = ET.SubElement(junction, 'request')
            for k, v in attrs.items():
                r.set(k, v)

    # ── Always reassign linkIndex to prevent duplicate-index bug ─────────────
    # sn_8th_2 (8th Ave approach): lane 0→idx0, lane 1→idx1, lane 2→idx2
    # ew_44_0  (44th St approach): lane 0→idx3, lane 1→idx4
    sn8_idx = 0
    ew44_idx = 3
    for c in root.findall(".//connection"):
        frm = c.get('from', '')
        fl  = int(c.get('fromLane', '0'))
        if frm == 'sn_8th_2':
            c.set('linkIndex', str(sn8_idx))
            c.set('tl', 'n_3_1')
            c.set('dir', 'r')
            sn8_idx += 1
        elif frm == 'ew_44_0':
            c.set('linkIndex', str(ew44_idx))
            c.set('tl', 'n_3_1')
            ew44_idx += 1

    # ── Always reset phase strings (5 links: idx 0-2=ave, 3-4=street) ────────
    _set_phases(root, 'n_3_1', ['GGGrr', 'yyyrr', 'rrrGG', 'rrryy'])

    # ── Add external connection lane 2 if missing ─────────────────────────────
    exists = any(True for c in root.findall(
        ".//connection[@from='sn_8th_2'][@to='ew_44_1'][@fromLane='2']"))
    if not exists:
        last = None
        for c in root.findall(".//connection[@from='sn_8th_2'][@to='ew_44_1']"):
            last = c
        if last is not None:
            parent = _parent_of(root, last)
            nc = ET.Element('connection')
            for k, v in [('from','sn_8th_2'),('to','ew_44_1'),('fromLane','2'),
                         ('toLane','1'),('via',':n_3_1_0_2'),('tl','n_3_1'),
                         ('linkIndex','2'),('dir','r'),('state','o')]:
                nc.set(k, v)
            parent.insert(list(parent).index(last)+1, nc)

    # ── Add internal connection if missing ────────────────────────────────────
    exists_i = any(True for c in root.findall(
        ".//connection[@from=':n_3_1_0'][@to='ew_44_1'][@fromLane='2']"))
    if not exists_i:
        last_i = None
        for c in root.findall(".//connection[@from=':n_3_1_0'][@to='ew_44_1']"):
            last_i = c
        if last_i is not None:
            parent = _parent_of(root, last_i)
            nc = ET.Element('connection')
            for k, v in [('from',':n_3_1_0'),('to','ew_44_1'),('fromLane','2'),
                         ('toLane','1'),('dir','r'),('state','M')]:
                nc.set(k, v)
            parent.insert(list(parent).index(last_i)+1, nc)

    print("  ✅ n_3_1 (44th & 8th): linkIndex reassigned, phases GGGrr/yyyrr/rrrGG/rrryy")


def _parent_of(root, child):
    """Return the parent element of child in the tree."""
    for parent in root.iter():
        if child in list(parent):
            return parent
    return root


def apply_tls_fix(net_file):
    """
    Fix TLS phase strings for all four 42nd Street junctions AND
    add missing 3rd lanes at n_0_2 (41st & 7th) and n_3_1 (44th & 8th).
    Called automatically by Gridnetwork.py after netconvert.
    """
    print("\n" + "="*60)
    print("  APPLYING TLS + LANE FIX — ALL JUNCTIONS")
    print("="*60)

    tree = ET.parse(net_file)
    root = tree.getroot()

    # ── 3rd lane fixes (avenue approach only gets 2 lanes from netconvert) ──
    print("\n  [Lane fixes]")
    _add_third_lane_n_0_2(root)
    _add_third_lane_n_3_1(root)

    # ── TLS phase string fixes ───────────────────────────────────────────────
    print("\n  [TLS phase fixes]")
    _fix_two_stream(root, 'n_1_0', ave_edges={'ns_9th_1'}, st42_edges={'we_42_0'})
    _fix_two_stream(root, 'n_1_3', ave_edges={'sn_6th_0'}, st42_edges={'ew_42_2'})
    _fix_n_1_1(root)
    _fix_n_1_2(root)

    # Write back
    raw = ET.tostring(root, encoding='unicode')
    with open(net_file, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(raw)

    print(f"\n  ✅ Fixed network saved: {net_file}")
    print("="*60)


def _fix_two_stream(root, jid, ave_edges, st42_edges):
    """
    Generic fix for junctions where avenue and 42nd St connections
    are clearly separated by from-edge name.
    Avenue connections get linkIndex 0..n-1, street gets n..end.
    """
    all_conns = root.findall(f".//connection[@tl='{jid}']")
    if not all_conns:
        print(f"  ⚠  {jid}: no connections found — skip")
        return

    # Separate by from-edge
    ave_c  = [c for c in all_conns if c.get('from','') in ave_edges]
    st42_c = [c for c in all_conns if c.get('from','') in st42_edges]

    # Assign linkIndex
    for i, c in enumerate(ave_c):
        c.set('linkIndex', str(i))
    n = len(ave_c)
    for i, c in enumerate(st42_c):
        c.set('linkIndex', str(n + i))
    total = n + len(st42_c)

    # Build phase strings
    ph = [
        'G'*n + 'r'*len(st42_c),   # avenue green
        'y'*n + 'r'*len(st42_c),   # avenue yellow
        'r'*n + 'G'*len(st42_c),   # 42nd green
        'r'*n + 'y'*len(st42_c),   # 42nd yellow
    ]
    _set_phases(root, jid, ph)
    print(f"  ✅ {jid}: {total} links — phases {ph[0]} / {ph[2]}")


def _fix_n_1_1(root):
    """
    Fix n_1_1 (42nd & 8th Ave) — 11 connections.
    we_42_1 → 0,1,2  |  sn_8th_0 → 3,4,5,6,7  |  ew_42_0 → 8,9,10
    Phase: 42nd both directions share one green phase, avenue has the other.
    """
    jid = 'n_1_1'
    all_conns = root.findall(f".//connection[@tl='{jid}']")
    if not all_conns:
        print(f"  ⚠  {jid}: no connections found — skip")
        return

    counters = {'we_42_1': 0, 'sn_8th_0': 3, 'ew_42_0': 8}
    for c in all_conns:
        frm = c.get('from', '')
        if frm in counters:
            c.set('linkIndex', str(counters[frm]))
            counters[frm] += 1

    # 11-char phase strings
    # Phase 0: 42nd E+W green (0-2=G, 3-7=r, 8-10=G)
    # Phase 2: 8th Ave green  (0-2=r, 3-7=G, 8-10=r)
    ph = [
        'GGGrrrrrGGG',
        'yyyrrrrryyy',
        'rrrGGGGGrrr',
        'rrryyyyyrrr',
    ]
    _set_phases(root, jid, ph)
    print(f"  ✅ {jid}: 11 links — phases {ph[0]} / {ph[2]}")


def _fix_n_1_2(root):
    """
    Fix n_1_2 (42nd & 7th Ave) — 11 connections.
    ns_7th_1 → 0,1,2,3,4  |  we_42_2 → 5,6,7  |  ew_42_1 → 8,9,10
    """
    jid = 'n_1_2'
    all_conns = root.findall(f".//connection[@tl='{jid}']")
    if not all_conns:
        print(f"  ⚠  {jid}: no connections found — skip")
        return

    counters = {'ns_7th_1': 0, 'we_42_2': 5, 'ew_42_1': 8}
    for c in all_conns:
        frm = c.get('from', '')
        if frm in counters:
            c.set('linkIndex', str(counters[frm]))
            counters[frm] += 1

    # 11-char phase strings
    # Phase 0: 42nd E+W green (0-4=r, 5-10=G)
    # Phase 2: 7th Ave green  (0-4=G, 5-10=r)
    ph = [
        'rrrrrGGGGGG',
        'rrrrryyyyyy',
        'GGGGGrrrrrr',
        'yyyyyrrrrrr',
    ]
    _set_phases(root, jid, ph)
    print(f"  ✅ {jid}: 11 links — phases {ph[0]} / {ph[2]}")


def _set_phases(root, jid, states, durations=(42, 3, 42, 3)):
    """Replace all phases in a tlLogic element with new state strings."""
    tl = root.find(f".//tlLogic[@id='{jid}']")
    if tl is None:
        print(f"  ⚠  tlLogic not found for {jid}")
        return
    for ph in tl.findall('phase'):
        tl.remove(ph)
    for state, dur in zip(states, durations):
        e = ET.SubElement(tl, 'phase')
        e.set('duration', str(dur))
        e.set('state', state)


def verify_fix(net_file):
    """Verify ALL TLS junctions: phase lengths, no duplicate requests."""
    from collections import Counter
    tree = ET.parse(net_file)
    root = tree.getroot()
    print("\n=== VERIFICATION — ALL JUNCTIONS ===")
    all_ok = True
    for tl in sorted(root.findall('.//tlLogic'), key=lambda x: x.get('id','')):
        jid   = tl.get('id','')
        conns = root.findall(f".//connection[@tl='{jid}']")
        if not conns:
            continue
        max_idx  = max(int(c.get('linkIndex', 0)) for c in conns)
        ph0      = tl.findall('phase')[0].get('state', '')
        phase_ok = len(ph0) > max_idx
        j        = root.find(f".//junction[@id='{jid}']")
        reqs     = j.findall('request') if j is not None else []
        req_ids  = [r.get('index') for r in reqs]
        dupes    = [k for k,v in Counter(req_ids).items() if v > 1]
        req_ok   = not dupes
        ok       = phase_ok and req_ok
        if not ok:
            all_ok = False
        dupe_str = f"  DUPLICATE_REQ={dupes}" if dupes else ""
        print(f"  {jid}: {len(conns)} conns  max_idx={max_idx}  "
              f"phase_len={len(ph0)}  reqs={len(reqs)}"
              f"  {'✅' if ok else '❌ BROKEN'}{dupe_str}")
    print(f"\n  {'✅ ALL JUNCTIONS OK' if all_ok else '❌ FIX INCOMPLETE — see above'}")
    print("="*40 + "\n")



# ─────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  MANHATTAN NETWORK — AUTO-FIXED SIGNAL PHASING")
    print("  Simulation Duration: 1 hour (3600 seconds)")
    print("="*60 + "\n")

    generate_nodes()
    generate_edges()
    generate_poi_labels()
    build_network()

    # Apply TLS fix for 42nd Street junctions
    apply_tls_fix(NET_FILE)
    verify_fix(NET_FILE)
    
    # Generate SUMO configuration with 1 hour duration
    generate_sumo_config()

    print("\n" + "="*60)
    print("  ✅ COMPLETE!")
    print("="*60)
    print("\n🚦 Run order:")
    print("   1. python Gridnetwork.py              ← you just ran this (builds + fixes network)")
    print("   2. python final_working_simulation.py ← generates route file")
    print("   3. sumo-gui -c run.sumocfg            ← visual test")
    print("   4. (from src/training/) python test_env.py")
    print("\n📊 Configuration:")
    print(f"   Episode duration: {SIM_DURATION} seconds ({SIM_DURATION/60:.0f} minutes)")
    print("   42nd St vehicles WILL stop on red. ✅")
    print("\n" + "="*60 + "\n")