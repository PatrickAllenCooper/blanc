# ROE Demo Visual Assets

This directory holds visual assets for the DeFAb-ROE dual-environment benchmark
demonstration. Assets pair game screenshots/renders with the formal defeasible
theory state and verifier derivation trace.

## SC2 Assets (`sc2/`)

StarCraft II screenshots illustrating each of the 6 Level 3 ROE seed scenarios.
These can be captured via PySC2 (`rgb_screen` observation) or from SC2 replays.

### Required Screenshots

| Filename | Scenario | What to Show |
|---|---|---|
| `sc2_exclusion_zone.png` | self_defense_exclusion_zone | Marine in red-highlighted restricted zone, enemy squad approaching, "FIRE PROHIBITED" overlay |
| `sc2_worker_repair.png` | worker_exception_repair | Enemy probes repairing a cannon firing at allied forces, "WORKERS PROTECTED" vs "EXCEPTION FIRES" |
| `sc2_all_in_rush.png` | all_in_rush_retreat_override | Zealot outnumbered but all-in rush wave approaching main base, "HOLD POSITION" override active |
| `sc2_stealth_recon.png` | stealth_break_direct_fire | Ghost unit cloaked on recon mission, then taking fire, stealth posture breaking |
| `sc2_hvt_pursuit.png` | hvt_retreat_override | Viking fighter pursuing mothership despite outnumbered, "HIGH VALUE TARGET IN RANGE" |
| `sc2_siege_tank_min_force.png` | proportionality_critical_threat | Siege tank near worker mining line, critical threat wave incoming, "PROPORTIONALITY OVERRIDE" |

### SC2 Screenshot Capture (PySC2)

```python
import pysc2
from pysc2.env import sc2_env
from pysc2.lib import features

env = sc2_env.SC2Env(
    map_name="Simple64",
    players=[sc2_env.Agent(sc2_env.Race.terran)],
    agent_interface_format=features.AgentInterfaceFormat(
        feature_dimensions=features.Dimensions(screen=84, minimap=64),
        rgb_dimensions=features.Dimensions(screen=256, minimap=128),
        use_feature_units=True,
    ),
    step_mul=8,
    game_steps_per_episode=0,
    visualize=True,
)

obs = env.reset()
# obs[0].observation["rgb_screen"] -> numpy array (H, W, 3)
import PIL.Image
img = PIL.Image.fromarray(obs[0].observation["rgb_screen"])
img.save("assets/roe_demo/sc2/sc2_exclusion_zone.png")
```

---

## Lux AI S3 Assets (`lux_ai_s3/`)

Lux AI S3 replay renders from the official web visualizer: https://s3vis.lux-ai.org

### Required Renders

| Filename | Scenario | What to Show |
|---|---|---|
| `lux_energy_retreat.png` | energy_critical_retreat_override | Ship adjacent to relic node (glowing), energy bar critical (red), "WIN CONDITION OVERRIDE" |
| `lux_laser_evasion.png` | stealth_break_laser_incoming | Ship in nebula (purple), laser beam visible, ship breaking stealth to evade |
| `lux_relic_in_nebula.png` | relic_inside_nebula | Relic node visible inside nebula cloud, ship approaching despite energy drain |
| `lux_probe_suspended.png` | probe_suspended_combat | Enemy ship adjacent to ally, energy node nearby, "PROBING SUSPENDED" |
| `lux_laser_engagement.png` | laser_engagement_blocked_path | Ship firing laser at enemy blocking path to relic |
| `lux_final_push.png` | contested_relic_final_push | Two ships contesting a relic, "FINAL MATCH - PUSH" override active |

### Lux AI S3 Replay Generation

```bash
# Install Lux AI S3
pip install luxai-s3

# Generate a match between two scripted agents
luxai-s3 bots/rts_roe_agent.py bots/rts_roe_agent.py --output replay.json

# Load in web visualizer
# 1. Open https://s3vis.lux-ai.org
# 2. Load replay.json
# 3. Navigate to the scenario step
# 4. Screenshot via browser
```

### Programmatic Render (Jax environment)

```python
from luxai_s3.env import LuxAIS3Env
import jax
import jax.numpy as jnp

env = LuxAIS3Env()
key = jax.random.PRNGKey(42)
obs, state = env.reset(key)
# state contains board visualization data
# Use env.render() or export to JSON for s3vis
```

---

## Demo Narrative Structure

Each visual asset is paired with:

1. **Game screenshot** -- what the player sees
2. **Theory state box** -- the formal D^- theory at that moment (rules listed)
3. **Verifier trace** -- step-by-step derivation showing which rule fired
4. **Anomaly box** -- the unexpected conclusion that needs explanation
5. **Exception construction** -- the model's proposed defeater
6. **Verification result** -- PASS/FAIL from DefeasibleEngine

This creates the visual narrative:
> "The unit is in this situation [screenshot]. The formal theory at this
>  moment looks like this [theory box]. The default rules say X, but the
>  context triggers an exception Y [verifier trace]. Without the exception,
>  the system cannot authorize the correct action [anomaly]. The model must
>  construct the missing exception [exception box]. The verifier confirms
>  the exception is valid and conservative [verification]."

---

## Paper Figure Captions (LaTeX)

```latex
\begin{figure}[t]
\centering
\includegraphics[width=0.48\textwidth]{assets/roe_demo/sc2/sc2_exclusion_zone.png}
\hfill
\includegraphics[width=0.48\textwidth]{assets/roe_demo/lux_ai_s3/lux_energy_retreat.png}
\caption{
  \textbf{DeFAb-ROE in two game environments.}
  \textit{Left}: StarCraft~II (SC2). A marine unit is under direct fire inside
  a restricted exclusion zone. The default ROE prohibit engagement in this zone,
  but the self-defense override -- when present -- authorizes response.
  \textit{Right}: Lux AI Season~3. A ship with critical energy is adjacent to a
  relic node in the final match with a score tie. The default self-preservation
  rule orders retreat, but the win-condition exception overrides it.
  In both cases, the DeFAb polynomial-time verifier certifies whether the
  model's proposed exception is valid (resolves the anomaly) and conservative
  (preserves all unrelated behavioral rules).
}
\label{fig:roe_dual_env}
\end{figure}
```

---

## Cross-Environment Hypothesis (H5)

If foundation models score comparably on SC2 and Lux AI Level 3 instances
despite completely different game vocabularies (marines/zones/exclusion vs.
ships/nebulae/relics), this demonstrates that DeFAb measures structural
defeasible reasoning rather than domain-specific vocabulary knowledge.

The visual demonstration makes this claim concrete and compelling:
the same formal machinery (DefeasibleEngine, AbductiveInstance, Level3Evaluator)
works identically across both game environments.
