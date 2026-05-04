"""
ROE game-state visualizer.

Generates top-down PNG frames showing:
    - Unit positions (allied = blue circles, enemy = red)
    - Zone overlays (restricted = red, engagement = yellow, main_base = green)
    - Active ROE conclusions at this tick
    - B2 gate decision (green border = admitted, red = rejected + re-prompt)

These visualizations are more informative for the paper than raw SC2 screenshots
because they directly show the formal theory state alongside the game geometry.

Also attempts to capture the live SC2 window via PIL.ImageGrab on Windows.

Author: Anonymous Authors
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import matplotlib
    matplotlib.use("Agg")  # non-interactive, safe for game loop
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import Circle, Rectangle, FancyArrowPatch
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    import PIL.ImageGrab
    HAS_PIL_GRAB = True
except ImportError:
    HAS_PIL_GRAB = False


# Zone colour scheme
ZONE_COLOURS = {
    "main_base":           ("#2ecc71", 0.20),   # green, semi-transparent
    "enemy_base":          ("#e74c3c", 0.20),   # red
    "restricted_zone_alpha": ("#e74c3c", 0.35), # bright red, more opaque
    "engagement_zone_alpha": ("#f39c12", 0.25), # orange
    "worker_mining_area":  ("#3498db", 0.20),   # blue
    "neutral_zone":        ("#95a5a6", 0.10),   # grey
}

# Approximate zone bounding boxes as fractions of [0,1] map space
# (map centre = (0.5, 0.5), main_base near bottom-left, enemy near top-right)
ZONE_BOXES = {
    "main_base":           (0.0, 0.0, 0.25, 0.25),
    "enemy_base":          (0.75, 0.75, 1.0, 1.0),
    "restricted_zone_alpha": (0.0, 0.0, 0.08, 1.0),   # left map edge
    "engagement_zone_alpha": (0.3, 0.3, 0.7, 0.7),
    "worker_mining_area":  (0.0, 0.0, 0.20, 0.20),
    "neutral_zone":        (0.1, 0.1, 0.9, 0.9),
}


@dataclass
class FrameViz:
    """Data needed to render one game frame."""
    step: int
    map_width: float
    map_height: float
    allied_units: list[dict]   # [{"atom": str, "type": str, "x": float, "y": float}]
    enemy_units: list[dict]
    active_zones: set[str]
    roe_conclusions: list[str]
    proposed_orders: list[dict]
    admitted_orders: list[dict]
    rejected_orders: list[dict]
    reprompt_reasons: list[str]
    scenario_id: str = ""
    provider: str = ""


def _parse_zone_from_fact(fact: str, atom: str) -> str | None:
    """Extract zone name from in_zone(atom, zone) fact."""
    m = re.match(r"in_zone\(" + re.escape(atom) + r",\s*(\w+)\)", fact)
    return m.group(1) if m else None


def extract_frame_data(
    theory_facts: list[str],
    derived: list[str],
    proposed: list[dict],
    admitted: list[dict],
    rejected: list[dict],
    reprompt_reasons: list[str],
    step: int,
    map_width: float = 64.0,
    map_height: float = 64.0,
    scenario_id: str = "",
    provider: str = "",
) -> FrameViz:
    """Extract visualisation data from a theory snapshot."""
    unary_re  = re.compile(r"^(\w+)\((\w+)\)$")
    binary_re = re.compile(r"^(\w+)\((\w+),\s*(\w+)\)$")

    unit_types: dict[str, str] = {}
    unit_zones: dict[str, str] = {}
    allied: set[str] = set()
    enemy: set[str] = set()
    zones_present: set[str] = set()

    for fact in theory_facts:
        m1 = unary_re.match(fact)
        m2 = binary_re.match(fact)
        if m1:
            pred, atom = m1.group(1), m1.group(2)
            if pred in ("infantry_unit", "armored_unit", "fighter_unit",
                        "bomber_unit", "worker_unit", "military_unit"):
                unit_types[atom] = pred
                allied.add(atom)
            elif pred in ("military_target", "worker_target"):
                enemy.add(atom)
        if m2:
            pred = m2.group(1)
            if pred == "in_zone":
                atom, zone = m2.group(2), m2.group(3)
                unit_zones[atom] = zone
                zones_present.add(zone)

    # Assign grid positions based on zone heuristic
    def zone_to_pos(atom: str, is_allied: bool, idx: int):
        zone = unit_zones.get(atom, "neutral_zone")
        box = ZONE_BOXES.get(zone, (0.1, 0.1, 0.9, 0.9))
        x0, y0, x1, y1 = box
        cx = (x0 + x1) / 2 + (idx % 3 - 1) * 0.04
        cy = (y0 + y1) / 2 + (idx // 3 % 3 - 1) * 0.04
        return cx * map_width, cy * map_height

    allied_units = [
        {"atom": a, "type": unit_types.get(a, "unit"),
         "x": zone_to_pos(a, True, i)[0], "y": zone_to_pos(a, True, i)[1]}
        for i, a in enumerate(sorted(allied))
    ]
    enemy_units = [
        {"atom": a, "type": "enemy",
         "x": zone_to_pos(a, False, i)[0], "y": zone_to_pos(a, False, i)[1]}
        for i, a in enumerate(sorted(enemy))
    ]

    return FrameViz(
        step=step,
        map_width=map_width,
        map_height=map_height,
        allied_units=allied_units,
        enemy_units=enemy_units,
        active_zones=zones_present,
        roe_conclusions=derived,
        proposed_orders=proposed,
        admitted_orders=admitted,
        rejected_orders=rejected,
        reprompt_reasons=reprompt_reasons,
        scenario_id=scenario_id,
        provider=provider,
    )


def render_frame(frame: FrameViz, output_path: Path) -> None:
    """Render a game state frame to a PNG file."""
    if not HAS_MATPLOTLIB:
        return

    fig, axes = plt.subplots(1, 2, figsize=(16, 8), facecolor="#1a1a2e")
    ax_map, ax_info = axes

    # ── Map panel ────────────────────────────────────────────────────────────
    ax_map.set_facecolor("#0d0d1a")
    ax_map.set_xlim(0, frame.map_width)
    ax_map.set_ylim(0, frame.map_height)
    ax_map.set_aspect("equal")
    ax_map.set_title(f"Step {frame.step}  |  {frame.scenario_id}",
                     color="white", fontsize=12, pad=10)
    ax_map.tick_params(colors="#555")
    for spine in ax_map.spines.values():
        spine.set_color("#333")

    # Draw zone overlays
    for zone in frame.active_zones:
        colour, alpha = ZONE_COLOURS.get(zone, ("#ffffff", 0.05))
        x0, y0, x1, y1 = ZONE_BOXES.get(zone, (0, 0, 1, 1))
        ax_map.add_patch(Rectangle(
            (x0 * frame.map_width, y0 * frame.map_height),
            (x1 - x0) * frame.map_width, (y1 - y0) * frame.map_height,
            facecolor=colour, alpha=alpha, edgecolor=colour, linewidth=1.5,
            label=zone.replace("_", " "),
        ))
        # Zone label
        cx = (x0 + x1) / 2 * frame.map_width
        cy = (y0 + y1) / 2 * frame.map_height
        ax_map.text(cx, cy, zone.replace("_", "\n"),
                    ha="center", va="center", fontsize=6, color=colour, alpha=0.7)

    # Draw allied units (blue)
    for u in frame.allied_units:
        # Check if this unit has an admitted attack order
        attacks = [o for o in frame.admitted_orders
                   if o.get("unit") == u["atom"] and o.get("action") == "attack"]
        rejected_attacks = [o for o in frame.rejected_orders
                            if o.get("unit") == u["atom"] and o.get("action") == "attack"]
        edge = "#00ff00" if attacks else ("#ff4444" if rejected_attacks else "#4fc3f7")
        ax_map.add_patch(Circle((u["x"], u["y"]), 1.2,
                                facecolor="#1565c0", edgecolor=edge, linewidth=2))
        ax_map.text(u["x"], u["y"] + 1.8, u["atom"].split("_")[0],
                    ha="center", va="bottom", fontsize=5, color="#90caf9")

    # Draw enemy units (red)
    for u in frame.enemy_units:
        ax_map.add_patch(Circle((u["x"], u["y"]), 1.2,
                                facecolor="#b71c1c", edgecolor="#ef9a9a", linewidth=1.5))
        ax_map.text(u["x"], u["y"] + 1.8, u["atom"].split("_")[0],
                    ha="center", va="bottom", fontsize=5, color="#ef9a9a")

    # Draw attack arrows for admitted orders
    for order in frame.admitted_orders:
        if order.get("action") != "attack" or not order.get("target"):
            continue
        attacker = next((u for u in frame.allied_units if u["atom"] == order["unit"]), None)
        target   = next((u for u in frame.enemy_units  if u["atom"] == order["target"]), None)
        if attacker and target:
            ax_map.annotate("",
                xy=(target["x"], target["y"]),
                xytext=(attacker["x"], attacker["y"]),
                arrowprops=dict(arrowstyle="->", color="#00e676", lw=1.5),
            )

    # Draw blocked attack arrows for rejected orders
    for order in frame.rejected_orders:
        if order.get("action") != "attack" or not order.get("target"):
            continue
        attacker = next((u for u in frame.allied_units if u["atom"] == order["unit"]), None)
        target   = next((u for u in frame.enemy_units  if u["atom"] == order["target"]), None)
        if attacker and target:
            ax_map.annotate("",
                xy=(target["x"], target["y"]),
                xytext=(attacker["x"], attacker["y"]),
                arrowprops=dict(arrowstyle="->", color="#ff1744", lw=1.5,
                                linestyle="dashed"),
            )
            # Red X at midpoint
            mx = (attacker["x"] + target["x"]) / 2
            my = (attacker["y"] + target["y"]) / 2
            ax_map.text(mx, my, "✗ BLOCKED", fontsize=7, color="#ff1744",
                        ha="center", va="center",
                        bbox=dict(boxstyle="round", facecolor="#1a0000", alpha=0.8))

    # ── Info panel ────────────────────────────────────────────────────────────
    ax_info.set_facecolor("#0d0d1a")
    ax_info.set_axis_off()
    ax_info.set_title(f"ROE Decision  |  {frame.provider}",
                      color="white", fontsize=12, pad=10)

    y = 0.95
    def info_text(text, colour="#e0e0e0", size=9):
        nonlocal y
        ax_info.text(0.02, y, text, transform=ax_info.transAxes,
                     fontsize=size, color=colour, va="top",
                     fontfamily="monospace", wrap=True)
        y -= 0.035

    info_text("ADMITTED ORDERS:", "#00e676", 10)
    for o in frame.admitted_orders[:6]:
        act = o.get("action", "?").upper()
        unit = o.get("unit", "?")
        tgt  = o.get("target", "")
        info_text(f"  + {act:8s} {unit}" + (f" -> {tgt}" if tgt else ""), "#b9f6ca")

    if not frame.admitted_orders:
        info_text("  (none admitted)", "#666")
    y -= 0.02

    info_text("REJECTED ORDERS:", "#ff1744", 10)
    for o, reason in zip(frame.rejected_orders[:4],
                          frame.reprompt_reasons[:4] + [""] * 4):
        act = o.get("action", "?").upper()
        unit = o.get("unit", "?")
        tgt  = o.get("target", "")
        info_text(f"  - {act:8s} {unit}" + (f" -> {tgt}" if tgt else ""), "#ff8a80")
        if reason:
            # Word-wrap reason
            for chunk in [reason[i:i+50] for i in range(0, min(len(reason), 120), 50)]:
                info_text(f"    {chunk}", "#ff8a80", 7)
    if not frame.rejected_orders:
        info_text("  (none rejected)", "#666")
    y -= 0.02

    info_text("ROE CONCLUSIONS:", "#ffeb3b", 10)
    for c in frame.roe_conclusions[:8]:
        info_text(f"  +d {c}", "#fff59d", 8)
    if not frame.roe_conclusions:
        info_text("  (none derived)", "#666")
    y -= 0.02

    # Legend
    info_text("LEGEND:", "#9e9e9e", 9)
    info_text("  Blue circle  = friendly unit", "#4fc3f7", 8)
    info_text("  Red circle   = enemy unit", "#ef9a9a", 8)
    info_text("  Green arrow  = admitted attack", "#00e676", 8)
    info_text("  Red dashed   = blocked (ROE violation)", "#ff1744", 8)

    plt.tight_layout(pad=2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(output_path), dpi=120, bbox_inches="tight",
                facecolor="#1a1a2e")
    plt.close(fig)


def capture_window_screenshot(output_path: Path) -> bool:
    """
    Capture the SC2 game window via PIL.ImageGrab (Windows only).
    Returns True on success.
    """
    if not HAS_PIL_GRAB:
        return False
    try:
        import PIL.Image
        screenshot = PIL.ImageGrab.grab()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        screenshot.save(str(output_path))
        return True
    except Exception:
        return False
