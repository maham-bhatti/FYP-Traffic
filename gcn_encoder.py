"""
gcn_encoder.py
==============
Multi-layer GCN for Manhattan 4x4 traffic network.

VERIFIED against actual manhattan.net.xml:
  - 12 TLS junctions, all T-junctions
  - GREEN_PHASES: only green SUMO phase indices (0 and 2)
  - ACT_DIM: 1 for 3-phase junctions, 2 for 4-phase junctions
  - Phase strings confirmed from tlLogic elements

Phase strings from manhattan.net.xml:
  n_0_1 (3ph): GGGGG | yyyyy | rrrrr
  n_0_2 (4ph): GGGrr | yyyrr | rrrGG | rrryy
  n_1_0 (4ph): GGGGGrr | yyyyyrr | rrrrrGG | rrrrryy
  n_1_1 (4ph): GGGrrrrrGGg | yyyrrrrryyy | rrrGGGGGrrr | rrryyyyyrrr
  n_1_2 (4ph): rrrrrGGgGGG | rrrrryyyyyy | GGGGGrrrrrr | yyyyyrrrrrr
  n_1_3 (4ph): GGGGGrr | yyyyyrr | rrrrrGG | rrrrryy
  n_2_0 (4ph): GGGrr | yyyrr | rrrGG | rrryy
  n_2_1 (4ph): GGGrrrr | yyyrrrr | rrrGGGG | rrryyyy
  n_2_2 (4ph): GGGGrrrr | yyyyrrrr | rrrrGGGG | rrrryyyy
  n_2_3 (3ph): GGGGG | yyyyy | rrrrr
  n_3_1 (4ph): GGGrr | yyyrr | rrrGG | rrryy
  n_3_2 (3ph): GGGGG | yyyyy | rrrrr
"""

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

# ─────────────────────────────────────────────────────────────────────────────
#  JUNCTION REGISTRY
# ─────────────────────────────────────────────────────────────────────────────

REAL_JUNCTIONS = [
    "n_0_1", "n_0_2",
    "n_1_0", "n_1_1", "n_1_2", "n_1_3",
    "n_2_0", "n_2_1", "n_2_2", "n_2_3",
    "n_3_1", "n_3_2",
]
JID2IDX = {jid: i for i, jid in enumerate(REAL_JUNCTIONS)}
N_NODES  = len(REAL_JUNCTIONS)  # 12

# Actual incoming lane counts (verified from net.xml incLanes)
JUNCTION_LANES = {
    "n_0_1": 2,
    "n_0_2": 5,
    "n_1_0": 5,
    "n_1_1": 9,
    "n_1_2": 9,
    "n_1_3": 5,
    "n_2_0": 5,
    "n_2_1": 7,
    "n_2_2": 7,
    "n_2_3": 3,
    "n_3_1": 5,
    "n_3_2": 2,
}
MAX_LANES = max(JUNCTION_LANES.values())  # 9

# GREEN phase indices only — agent NEVER selects yellow or all-red
# 3-phase junctions: only Phase 0 (single movement)
# 4-phase junctions: Phase 0 (direction A) or Phase 2 (direction B)
GREEN_PHASES = {
    "n_0_1": [0],       # single movement
    "n_0_2": [0, 2],
    "n_1_0": [0, 2],
    "n_1_1": [0, 2],
    "n_1_2": [0, 2],
    "n_1_3": [0, 2],
    "n_2_0": [0, 2],
    "n_2_1": [0, 2],
    "n_2_2": [0, 2],
    "n_2_3": [0],       # single movement
    "n_3_1": [0, 2],
    "n_3_2": [0],       # single movement
}

# Action space size per junction (1 or 2 green choices)
ACT_DIM = {jid: len(GREEN_PHASES[jid]) for jid in REAL_JUNCTIONS}

# Raw observation dimension = lane counts + 1 (current action index)
RAW_OBS_DIM = {jid: JUNCTION_LANES[jid] + 1 for jid in REAL_JUNCTIONS}

# Undirected adjacency edges for GCN
ROAD_EDGES = [
    ("n_0_1", "n_0_2"),
    ("n_1_0", "n_1_1"), ("n_1_1", "n_1_2"), ("n_1_2", "n_1_3"),
    ("n_2_0", "n_2_1"), ("n_2_1", "n_2_2"), ("n_2_2", "n_2_3"),
    ("n_3_1", "n_3_2"),
    ("n_1_0", "n_2_0"),
    ("n_0_1", "n_1_1"), ("n_1_1", "n_2_1"), ("n_2_1", "n_3_1"),
    ("n_0_2", "n_1_2"), ("n_1_2", "n_2_2"), ("n_2_2", "n_3_2"),
    ("n_1_3", "n_2_3"),
]

GCN_OUT_DIM = 32


# ─────────────────────────────────────────────────────────────────────────────
#  ADJACENCY MATRIX
# ─────────────────────────────────────────────────────────────────────────────

def _build_adjacency():
    A = np.zeros((N_NODES, N_NODES), dtype=np.float32)
    edges = []
    for u, v in ROAD_EDGES:
        i, j = JID2IDX[u], JID2IDX[v]
        A[i, j] = A[j, i] = 1.0
        edges += [[i, j], [j, i]]
    A_hat = A + np.eye(N_NODES, dtype=np.float32)
    d     = A_hat.sum(1)
    D_inv = np.diag(1.0 / np.sqrt(d + 1e-8))
    A_norm = D_inv @ A_hat @ D_inv
    return torch.FloatTensor(A_norm), torch.LongTensor(np.array(edges, np.int64).T)

A_NORM, EDGE_INDEX = _build_adjacency()


# ─────────────────────────────────────────────────────────────────────────────
#  NODE FEATURE BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def obs_to_node_features(obs_dict: dict) -> np.ndarray:
    """
    Build (N_NODES, 4) node feature matrix.
      col 0: mean queue  / 20
      col 1: max queue   / 30
      col 2: complexity  (lanes / MAX_LANES)
      col 3: action idx  / ACT_DIM
    """
    X = np.zeros((N_NODES, 4), dtype=np.float32)
    for jid, idx in JID2IDX.items():
        if jid not in obs_dict:
            continue
        obs    = obs_dict[jid]
        nl     = JUNCTION_LANES[jid]
        counts = obs[:nl]
        X[idx, 0] = float(counts.mean()) / 20.0
        X[idx, 1] = float(counts.max())  / 30.0
        X[idx, 2] = float(nl)            / MAX_LANES
        X[idx, 3] = float(obs[-1])       / max(ACT_DIM[jid], 1)
    return X


# ─────────────────────────────────────────────────────────────────────────────
#  GCN LAYERS
# ─────────────────────────────────────────────────────────────────────────────

class GCNLayer(nn.Module):
    """Single GCN layer: H' = ReLU(A_norm @ H @ W)"""
    def __init__(self, in_dim: int, out_dim: int):
        super().__init__()
        self.fc = nn.Linear(in_dim, out_dim)
        nn.init.xavier_uniform_(self.fc.weight)
        nn.init.zeros_(self.fc.bias)

    def forward(self, H: torch.Tensor, A: torch.Tensor) -> torch.Tensor:
        return F.relu(self.fc(torch.matmul(A, H)))


class MultiLayerGCN(nn.Module):
    """
    3-layer GCN encoder.
    Layer 1 (Spatial):        captures direct-neighbour queue states
    Layer 2 (Communication):  propagates coordinated signal 2 hops away
    Layer 3 (Temporal):       compresses to 32-dim embedding per junction
    """
    def __init__(self, in_dim=4, hidden1=64, hidden2=64,
                 out_dim=GCN_OUT_DIM, device="cpu"):
        super().__init__()
        self.device = torch.device(device)
        self.layer1 = GCNLayer(in_dim,   hidden1)
        self.layer2 = GCNLayer(hidden1,  hidden2)
        self.layer3 = GCNLayer(hidden2,  out_dim)
        self.register_buffer("A_norm",     A_NORM.clone())
        self.register_buffer("edge_index", EDGE_INDEX.clone())

    def forward(self, X: torch.Tensor) -> torch.Tensor:
        batched = X.dim() == 3
        if not batched:
            X = X.unsqueeze(0)
        A = self.A_norm.to(X.device)
        H = self.layer1(X, A)
        H = self.layer2(H, A)
        H = self.layer3(H, A)
        return H if batched else H.squeeze(0)

    @torch.no_grad()
    def encode(self, obs_dict: dict) -> dict:
        X = torch.FloatTensor(obs_to_node_features(obs_dict)).to(self.device)
        H = self.forward(X).cpu().numpy()
        return {jid: H[idx] for jid, idx in JID2IDX.items()}

    @torch.no_grad()
    def augment_obs(self, obs_dict: dict) -> dict:
        emb = self.encode(obs_dict)
        return {
            jid: np.concatenate([obs_dict[jid], emb[jid]]).astype(np.float32)
            for jid in obs_dict
        }


def get_augmented_obs_dims() -> dict:
    return {jid: RAW_OBS_DIM[jid] + GCN_OUT_DIM for jid in REAL_JUNCTIONS}


# ─────────────────────────────────────────────────────────────────────────────
#  SELF-TEST
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 65)
    print("  GCN Encoder — Self Test")
    print("=" * 65)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    gcn    = MultiLayerGCN(device=device).to(device)
    fake   = {jid: np.random.randint(0, 10, RAW_OBS_DIM[jid]).astype(np.float32)
              for jid in REAL_JUNCTIONS}
    aug    = gcn.augment_obs(fake)
    print(f"\n{'Junction':<10} {'Lanes':<7} {'ActDim':<8} {'RawObs':<8} {'AugObs'} GreenPhases")
    print("-" * 65)
    for jid in REAL_JUNCTIONS:
        print(f"{jid:<10} {JUNCTION_LANES[jid]:<7} {ACT_DIM[jid]:<8} "
              f"{RAW_OBS_DIM[jid]:<8} {aug[jid].shape[0]:<7} {GREEN_PHASES[jid]}")
    X = torch.FloatTensor(obs_to_node_features(fake)).to(device)
    X.requires_grad_(True)
    gcn(X).sum().backward()
    print(f"\n  GCN params : {sum(p.numel() for p in gcn.parameters()):,}")
    print(f"  ACT_DIM=2  : {sum(1 for v in ACT_DIM.values() if v==2)} junctions")
    print(f"  ACT_DIM=1  : {sum(1 for v in ACT_DIM.values() if v==1)} junctions")
    print("  Backward pass: OK")
    print("=" * 65)
