import numpy as np

# ==========================================
#   GCN MATRIX GENERATOR (Paper Methodology)
# ==========================================
# Based on: "Multi-intersection Traffic Optimisation"
# Methodology: Edge-weighted Graph Convolutional Encoder

# --- 1. NETWORK PARAMETERS (Your Map) ---
N_ROWS = 4
N_COLS = 4
NUM_INTERSECTIONS = N_ROWS * N_COLS

# Road Lengths defined in your simulation
LEN_EW = 500.0  # Horizontal
LEN_NS = 300.0  # Vertical
MAX_LEN = max(LEN_EW, LEN_NS)

# --- 2. CALCULATE WEIGHTS ---
# Formula: Weight = L_max / L_current
W_HORIZONTAL = MAX_LEN / LEN_EW  # 500/500 = 1.0
W_VERTICAL   = MAX_LEN / LEN_NS  # 500/300 = 1.66...

print(f">>> CALCULATING GCN WEIGHTS")
print(f"    Max Length: {MAX_LEN}m")
print(f"    Horizontal Weight: {W_HORIZONTAL:.2f}")
print(f"    Vertical Weight:   {W_VERTICAL:.2f} (Higher influence because distance is shorter)")

# --- 3. BUILD ADJACENCY MATRIX (A) ---
# We map intersections to indices 0..15
# Index = row * N_COLS + col
adj_matrix = np.zeros((NUM_INTERSECTIONS, NUM_INTERSECTIONS))

def get_id(r, c):
    return r * N_COLS + c

print("\n>>> BUILDING CONNECTIVITY...")
for row in range(N_ROWS):
    for col in range(N_COLS):
        current_id = get_id(row, col)
        
        # Check North Neighbor
        if row > 0:
            neighbor_id = get_id(row - 1, col)
            adj_matrix[current_id][neighbor_id] = W_VERTICAL
            
        # Check South Neighbor
        if row < N_ROWS - 1:
            neighbor_id = get_id(row + 1, col)
            adj_matrix[current_id][neighbor_id] = W_VERTICAL
            
        # Check West Neighbor
        if col > 0:
            neighbor_id = get_id(row, col - 1)
            adj_matrix[current_id][neighbor_id] = W_HORIZONTAL
            
        # Check East Neighbor
        if col < N_COLS - 1:
            neighbor_id = get_id(row, col + 1)
            adj_matrix[current_id][neighbor_id] = W_HORIZONTAL

# --- 4. ADD SELF-LOOPS (Identity Matrix) ---
# The paper says: "add it to a identity matrix I"
identity = np.eye(NUM_INTERSECTIONS)
adj_matrix_with_self = adj_matrix + identity

# --- 5. ROW NORMALIZATION ---
# The paper says: "normalise them row-wisely"
# We divide each element by the sum of its row
row_sums = adj_matrix_with_self.sum(axis=1)
norm_matrix = adj_matrix_with_self / row_sums[:, np.newaxis]

# --- 6. PRINT TABLE ---
print("\n" + "="*50)
print("FINAL GCN ADJACENCY TABLE (Normalized)")
print("="*50)
print("Rows/Cols represent intersections 0 to 15")
print("Values represent the influence weight")
print("-" * 50)

# Print Header
print("      ", end="")
for i in range(NUM_INTERSECTIONS):
    print(f"{i:5d} ", end="")
print("\n" + "-" * (7 + 6*NUM_INTERSECTIONS))

# Print Rows
for i in range(NUM_INTERSECTIONS):
    print(f"{i:3d} | ", end="")
    for j in range(NUM_INTERSECTIONS):
        val = norm_matrix[i][j]
        if val == 0:
            print("  .   ", end="") # Empty for readability
        else:
            print(f"{val:.3f} ", end="")
    print("|")

print("-" * (7 + 6*NUM_INTERSECTIONS))
print("\n Completed! This matrix 'norm_matrix' is your GCN Input.")