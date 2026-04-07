"""
mappo_atsc.py
=============
Multi-Agent PPO for Adaptive Traffic Signal Control.

Architecture:
  State → Multi-layer GCN (shared) → Augmented observation
  Augmented obs → Decentralised Actor → Action (green phase choice)
  Global state  → Centralised Critic → Value estimate

Action space:
  Per junction: ACT_DIM = 1 (3-phase) or 2 (4-phase).
  Agent selects a GREEN direction only. Yellow/red are handled
  by the SUMO-native timer in the environment.

References:
  Schulman et al. 2017 (PPO)
  Yu et al. 2022 (MAPPO)
  Kwesiga et al. 2024 (MAPPO-ATSC)
  Ng et al. 1999 (potential-based reward shaping — delta queue term)
"""

import os
import numpy as np
from collections import defaultdict

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.distributions import Categorical

from gcn_encoder import (
    MultiLayerGCN, get_augmented_obs_dims,
    REAL_JUNCTIONS, JUNCTION_LANES, GREEN_PHASES,
    RAW_OBS_DIM, GCN_OUT_DIM, ACT_DIM,
)

# ─────────────────────────────────────────────────────────────────────────────
#  HYPERPARAMETERS
# ─────────────────────────────────────────────────────────────────────────────

GAMMA        = 0.99
GAE_LAMBDA   = 0.95
LR_ACTOR     = 3e-4
LR_CRITIC    = 1e-3
CLIP_EPS     = 0.2
ENTROPY_COEF = 0.01
VALUE_COEF   = 0.5
GRAD_CLIP    = 0.5
PPO_EPOCHS   = 4
ROLLOUT_LEN  = 128
MINI_BATCH   = 32
MAX_EPISODES = 1000

# Augmented + global state dimensions
AUG_OBS_DIM = get_augmented_obs_dims()
GLOBAL_DIM  = sum(AUG_OBS_DIM.values())


# ─────────────────────────────────────────────────────────────────────────────
#  ACTOR
# ─────────────────────────────────────────────────────────────────────────────

class Actor(nn.Module):
    """
    Decentralised policy pi(a | aug_obs_i).
    Output logits shape: (ACT_DIM[jid],) = 1 or 2 green choices.
    """
    def __init__(self, obs_dim: int, action_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(obs_dim,  64),  nn.ReLU(),
            nn.Linear(64,      128),  nn.ReLU(),
            nn.Linear(128, action_dim),
        )
        nn.init.orthogonal_(self.net[-1].weight, gain=0.01)
        nn.init.zeros_(self.net[-1].bias)

    def forward(self, obs: torch.Tensor) -> torch.Tensor:
        return self.net(obs)

    def get_action(self, obs: torch.Tensor):
        dist = Categorical(logits=self.forward(obs))
        a    = dist.sample()
        return a, dist.log_prob(a), dist.entropy()

    def evaluate_actions(self, obs: torch.Tensor, actions: torch.Tensor):
        dist = Categorical(logits=self.forward(obs))
        return dist.log_prob(actions), dist.entropy()


# ─────────────────────────────────────────────────────────────────────────────
#  CENTRALIZED CRITIC
# ─────────────────────────────────────────────────────────────────────────────

class CentralCritic(nn.Module):
    """Centralised V(global_state) shared across all agents."""
    def __init__(self, global_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(global_dim, 128), nn.ReLU(),
            nn.Linear(128,        256), nn.ReLU(),
            nn.Linear(256,        256), nn.ReLU(),
            nn.Linear(256,          1),
        )
        nn.init.orthogonal_(self.net[-1].weight, gain=1.0)
        nn.init.zeros_(self.net[-1].bias)

    def forward(self, gs: torch.Tensor) -> torch.Tensor:
        return self.net(gs)


# ─────────────────────────────────────────────────────────────────────────────
#  ROLLOUT BUFFER
# ─────────────────────────────────────────────────────────────────────────────

class RolloutBuffer:
    def __init__(self):
        self.clear()

    def clear(self):
        self.aug_obs   = []
        self.global_st = []
        self.actions   = []
        self.log_probs = []
        self.rewards   = []
        self.values    = []
        self.dones     = []

    def push(self, aug_obs, gs, action, lp, reward, value, done):
        self.aug_obs.append(aug_obs)
        self.global_st.append(gs)
        self.actions.append(int(action))
        self.log_probs.append(float(lp))
        self.rewards.append(float(reward))
        self.values.append(float(value))
        self.dones.append(float(done))

    def __len__(self):
        return len(self.rewards)

    def compute_gae(self, last_value: float):
        """Generalised Advantage Estimation (Schulman et al. 2016)."""
        T    = len(self.rewards)
        rew  = np.array(self.rewards,  np.float32)
        vals = np.array(self.values,   np.float32)
        done = np.array(self.dones,    np.float32)
        adv  = np.zeros(T,             np.float32)
        gae  = 0.0
        for t in reversed(range(T)):
            nv    = last_value if t == T - 1 else vals[t + 1]
            nd    = 0.0        if t == T - 1 else done[t + 1]
            delta = rew[t] + GAMMA * nv * (1 - nd) - vals[t]
            gae   = delta + GAMMA * GAE_LAMBDA * (1 - nd) * gae
            adv[t] = gae
        returns = adv + vals
        return torch.FloatTensor(adv), torch.FloatTensor(returns)

    def to_tensors(self):
        return (
            torch.FloatTensor(np.array(self.aug_obs)),
            torch.FloatTensor(np.array(self.global_st)),
            torch.LongTensor(self.actions),
            torch.FloatTensor(self.log_probs),
        )


# ─────────────────────────────────────────────────────────────────────────────
#  MAPPO AGENT  (per junction)
# ─────────────────────────────────────────────────────────────────────────────

class MAPPOAgent:
    def __init__(self, jid: str, device: torch.device,
                 shared_critic: CentralCritic):
        self.jid        = jid
        self.dev        = device
        self.na         = ACT_DIM[jid]
        self.actor      = Actor(AUG_OBS_DIM[jid], self.na).to(device)
        self.actor_opt  = optim.Adam(self.actor.parameters(), lr=LR_ACTOR)
        self.critic     = shared_critic
        self.critic_opt = optim.Adam(self.critic.parameters(), lr=LR_CRITIC)
        self.rollout    = RolloutBuffer()
        self.steps      = 0

    @torch.no_grad()
    def act(self, aug_obs: np.ndarray, global_state: np.ndarray):
        ao = torch.FloatTensor(aug_obs).unsqueeze(0).to(self.dev)
        gs = torch.FloatTensor(global_state).unsqueeze(0).to(self.dev)
        a, lp, _ = self.actor.get_action(ao)
        v = self.critic(gs).squeeze(-1)
        return int(a.item()), float(lp.item()), float(v.item())

    def store(self, aug_obs, gs, action, lp, reward, value, done):
        self.rollout.push(aug_obs, gs, action, lp, reward, value, done)

    def update(self, last_value: float, update_critic: bool = False) -> dict:
        T = len(self.rollout)
        if T == 0:
            return {}
        adv, ret = self.rollout.compute_gae(last_value)
        aug, gs, acts, old_lp = self.rollout.to_tensors()
        aug    = aug.to(self.dev);   gs     = gs.to(self.dev)
        acts   = acts.to(self.dev);  old_lp = old_lp.to(self.dev)
        adv    = adv.to(self.dev);   ret    = ret.to(self.dev)

        log = defaultdict(list)
        idx = np.arange(T)
        for _ in range(PPO_EPOCHS):
            np.random.shuffle(idx)
            for s in range(0, T, MINI_BATCH):
                mb = idx[s: s + MINI_BATCH]
                if len(mb) == 0:
                    continue
                mb_adv = adv[mb]
                mb_adv = (mb_adv - mb_adv.mean()) / (mb_adv.std() + 1e-8)
                new_lp, entropy = self.actor.evaluate_actions(aug[mb], acts[mb])
                ratio  = torch.exp(new_lp - old_lp[mb])
                surr   = -torch.min(
                    ratio * mb_adv,
                    torch.clamp(ratio, 1 - CLIP_EPS, 1 + CLIP_EPS) * mb_adv
                ).mean()
                actor_loss = surr + ENTROPY_COEF * (-entropy.mean())
                self.actor_opt.zero_grad()
                actor_loss.backward()
                nn.utils.clip_grad_norm_(self.actor.parameters(), GRAD_CLIP)
                self.actor_opt.step()
                log["ppo_loss"].append(surr.item())
                log["entropy"].append(entropy.mean().item())
                if update_critic:
                    v_pred = self.critic(gs[mb]).squeeze(-1)
                    closs  = VALUE_COEF * F.mse_loss(v_pred, ret[mb])
                    self.critic_opt.zero_grad()
                    closs.backward()
                    nn.utils.clip_grad_norm_(self.critic.parameters(), GRAD_CLIP)
                    self.critic_opt.step()
                    log["critic_loss"].append(closs.item())

        self.rollout.clear()
        self.steps += T
        return {k: float(np.mean(v)) for k, v in log.items()}

    def save(self, path: str):
        torch.save({"actor": self.actor.state_dict(), "steps": self.steps}, path)

    def load(self, path: str):
        ck = torch.load(path, map_location=self.dev)
        self.actor.load_state_dict(ck["actor"])
        self.steps = ck.get("steps", 0)


# ─────────────────────────────────────────────────────────────────────────────
#  MAPPO CONTROLLER
# ─────────────────────────────────────────────────────────────────────────────

class MAPPOController:
    """
    Coordinates all per-junction agents with shared GCN and centralized critic.
    """
    def __init__(self, device: str = "cpu", gcn_ckpt: str = None):
        self.dev    = torch.device(device)
        self.gcn    = MultiLayerGCN(device=device).to(self.dev)
        if gcn_ckpt and os.path.exists(gcn_ckpt):
            self.gcn.load_state_dict(torch.load(gcn_ckpt, map_location=self.dev))
        self.critic = CentralCritic(GLOBAL_DIM).to(self.dev)
        self.agents = {jid: MAPPOAgent(jid, self.dev, self.critic)
                       for jid in REAL_JUNCTIONS}
        self._critic_owner = REAL_JUNCTIONS[0]
        self.global_step   = 0
        self._print_summary()

    def _print_summary(self):
        gcn_p  = sum(p.numel() for p in self.gcn.parameters())
        act_p  = sum(p.numel() for p in self.agents["n_1_1"].actor.parameters())
        crit_p = sum(p.numel() for p in self.critic.parameters())
        total  = gcn_p + act_p * len(self.agents) + crit_p
        print(f"\n  MAPPOController ready")
        print(f"  Junctions : {len(self.agents)}")
        print(f"  GCN params: {gcn_p:,}  Critic: {crit_p:,}  Total: {total:,}")
        dist = defaultdict(list)
        for jid, na in ACT_DIM.items():
            dist[na].append(jid)
        for na, jids in sorted(dist.items()):
            print(f"  ACT_DIM={na}: {len(jids)} junctions — {jids}")

    def _global_state(self, aug_obs: dict) -> np.ndarray:
        return np.concatenate([aug_obs[jid] for jid in REAL_JUNCTIONS]).astype(np.float32)

    def act(self, raw_obs: dict):
        aug_obs      = self.gcn.augment_obs(raw_obs)
        global_state = self._global_state(aug_obs)
        actions, log_probs, values = {}, {}, {}
        for jid, agent in self.agents.items():
            a, lp, v           = agent.act(aug_obs[jid], global_state)
            actions[jid]       = a
            log_probs[jid]     = lp
            values[jid]        = v
        return actions, log_probs, values, aug_obs, global_state

    def store(self, aug_obs, gs, actions, lps, rewards, values, done):
        for jid, agent in self.agents.items():
            if jid in rewards:
                agent.store(aug_obs[jid], gs, actions[jid],
                            lps[jid], rewards[jid], values[jid], done)

    def update(self, last_raw_obs: dict) -> dict:
        last_aug = self.gcn.augment_obs(last_raw_obs)
        last_gs  = self._global_state(last_aug)
        lgs_t    = torch.FloatTensor(last_gs).unsqueeze(0).to(self.dev)
        with torch.no_grad():
            last_val = self.critic(lgs_t).item()
        all_logs = defaultdict(list)
        for jid, agent in self.agents.items():
            res = agent.update(last_val, update_critic=(jid == self._critic_owner))
            for k, v in res.items():
                all_logs[k].append(v)
        self.global_step += 1
        return {k: float(np.mean(v)) for k, v in all_logs.items()}

    def save(self, directory: str = "ckpt_mappo"):
        os.makedirs(directory, exist_ok=True)
        torch.save(self.gcn.state_dict(),    os.path.join(directory, "gcn.pt"))
        torch.save(self.critic.state_dict(), os.path.join(directory, "critic.pt"))
        for jid, agent in self.agents.items():
            agent.save(os.path.join(directory, f"actor_{jid}.pt"))
        print(f"  Saved -> {directory}/")

    def load(self, directory: str = "ckpt_mappo"):
        p = os.path.join(directory, "gcn.pt")
        if os.path.exists(p):
            self.gcn.load_state_dict(torch.load(p, map_location=self.dev))
        p = os.path.join(directory, "critic.pt")
        if os.path.exists(p):
            self.critic.load_state_dict(torch.load(p, map_location=self.dev))
        for jid, agent in self.agents.items():
            p = os.path.join(directory, f"actor_{jid}.pt")
            if os.path.exists(p):
                agent.load(p)
        print(f"  Loaded <- {directory}/")


# ─────────────────────────────────────────────────────────────────────────────
#  SELF-TEST
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 65)
    print("  MAPPO-ATSC Self-Test")
    print("=" * 65)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    ctrl   = MAPPOController(device=device)
    fake   = lambda: {jid: np.random.randint(0, 10, RAW_OBS_DIM[jid]).astype(np.float32)
                      for jid in REAL_JUNCTIONS}
    step = 0
    for i in range(300):
        acts, lps, vals, aug, gs = ctrl.act(fake())
        rews = {jid: float(-np.random.randint(0, 5)) for jid in REAL_JUNCTIONS}
        ctrl.store(aug, gs, acts, lps, rews, vals, False)
        step += 1
        if step >= ROLLOUT_LEN:
            loss = ctrl.update(fake())
            print(f"  Step {i:4d} | PPO={loss.get('ppo_loss',0):.4f} "
                  f"Critic={loss.get('critic_loss',0):.4f} "
                  f"H={loss.get('entropy',0):.4f}")
            step = 0
    ctrl.save("ckpt_test")
    print("\n  Self-test passed")
    print("=" * 65)
