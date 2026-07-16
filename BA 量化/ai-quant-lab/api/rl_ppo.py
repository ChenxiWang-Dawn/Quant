"""Local-only PPO environment.  No broker, order-routing or live-data hooks."""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np


def train_ppo(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        import gymnasium as gym
        from gymnasium import spaces
        from stable_baselines3 import PPO
    except Exception as exc:
        raise ValueError("PPO 需要本地安装 gymnasium 与 stable-baselines3") from exc

    prices = np.asarray(payload.get("prices", [100, 101, 99, 102, 104, 103, 106, 105, 108, 110, 109, 112, 114, 113, 116, 118, 120, 119, 122, 124, 123, 126, 128, 130, 129, 133, 136, 135, 138, 141]), dtype=np.float32)
    if len(prices) < 20 or np.any(prices <= 0):
        raise ValueError("PPO 训练至少需要 20 个正价格观察")
    cost, risk_penalty = float(payload.get("transactionCost", .001)), float(payload.get("riskPenalty", .05))

    class AllocationEnv(gym.Env):
        metadata = {"render_modes": []}
        def __init__(self):
            self.action_space = spaces.Box(low=np.array([0.0], dtype=np.float32), high=np.array([1.0], dtype=np.float32))
            self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(4,), dtype=np.float32)
            self.index, self.weight, self.value = 3, 0.0, 1.0
        def _observation(self):
            window = prices[self.index - 3:self.index]
            returns = window[1:] / window[:-1] - 1
            return np.asarray([returns[-1], returns.mean(), returns.std(), self.weight], dtype=np.float32)
        def reset(self, *, seed=None, options=None):
            super().reset(seed=seed); self.index, self.weight, self.value = 3, 0.0, 1.0; return self._observation(), {}
        def step(self, action):
            target = float(np.clip(action[0], 0, 1)); turnover = abs(target - self.weight)
            gross = float(prices[self.index + 1] / prices[self.index] - 1); net = target * gross - turnover * cost
            reward = float(np.log(max(1 + net, 1e-8)) - risk_penalty * net * net)
            self.value *= 1 + net; self.weight, self.index = target, self.index + 1
            terminated = self.index >= len(prices) - 1
            return self._observation() if not terminated else np.zeros(4, dtype=np.float32), reward, terminated, False, {"equity": self.value, "turnover": turnover, "netReturn": net}

    seeds = [int(seed) for seed in payload.get("seeds", [7, 17, 29])][:5]
    steps = min(int(payload.get("trainingSteps", 20_000)), 200_000)
    runs: List[Dict[str, Any]] = []
    for seed in seeds:
        environment = AllocationEnv(); model = PPO("MlpPolicy", environment, seed=seed, verbose=0, n_steps=min(128, len(prices) - 4), batch_size=min(32, len(prices) - 4), device="auto")
        model.learn(total_timesteps=steps)
        observation, _ = environment.reset(seed=seed); done, rewards, turnovers = False, [], []
        while not done:
            action, _ = model.predict(observation, deterministic=True)
            observation, reward, terminated, truncated, info = environment.step(action); done = terminated or truncated; rewards.append(reward); turnovers.append(info["turnover"])
        runs.append({"seed": seed, "finalEquity": float(environment.value), "meanReward": float(np.mean(rewards)), "turnover": float(np.mean(turnovers))})
    return {"algorithm": "PPO", "status": "simulation_completed", "seeds": runs, "aggregate": {"meanEquity": float(np.mean([item["finalEquity"] for item in runs])), "worstEquity": float(min(item["finalEquity"] for item in runs)), "seedCount": len(runs)}, "environment": {"observation": "3 historical returns + current weight", "action": "long-only target weight [0,1]", "reward": "log net return - risk penalty", "boundary": "historical simulation only"}}
