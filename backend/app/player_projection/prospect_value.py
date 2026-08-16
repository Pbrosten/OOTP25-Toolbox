"""Prospect Future Value (FV) / surplus-value calculation (ticket 0068).

Replicates FanGraphs' Future Value framework against this app's own ratings
data (see ticket 0043's Design choices for the full derivation and source
material): a prospect's *talent* (potential) ratings are run through the
existing `BatterProjection`/`PitcherProjection` classes to get a talent-
ceiling annual WAR, which is bucketed into a 20-80 FV grade and looked up
against a surplus-value/expected-WAR/star-odds table. The same pipeline, run
against *current* ratings instead, produces an MLB-promotion-readiness
signal.
"""

from .batter import BatterProjection
from .pitcher import PitcherProjection

# === WAR -> FV lookup tables (ticket 0043 Design choices) ===
# Descending (min_war, fv) tiers. The top tier is matched with a strict '>'
# (the source table lists FV 80 as "> 7.0", every other grade as an
# inclusive floor) -- see _war_to_fv(). The final tier's floor is -inf, so
# every finite WAR resolves to some FV; FV 20 ("Org guy") has no WAR range
# in the source table and is never produced by this lookup.
HITTER_WAR_TO_FV = [
    (7.0, 80),   # Top 5 overall
    (5.0, 70),   # Top 10 overall
    (3.4, 60),   # All-Star
    (2.5, 55),   # Above-Avg Reg
    (1.6, 50),   # Avg Everyday Player
    (0.8, 45),   # Low-End Reg/Platoon
    (0.0, 40),   # Bench Player
    (float("-inf"), 30),  # Up & Down
]

# Source table was built from a starters sample (50+ IP) -- applied to
# relievers too (ticket 0068 post-close correction, user request): RP's own
# much smaller workload (ROLE_CONSTANTS in pitcher.py: ~300 PA baseline vs.
# SP's ~750, ~0.03 replacement-runs/IP vs. ~0.12) already drives a lower
# annual WAR through PitcherProjection on its own, so relievers naturally
# land in the lower FV tiers rather than needing a hard exclusion.
PITCHER_WAR_TO_FV = [
    (7.0, 80),   # Ace / #1
    (5.0, 70),   # #2 starter
    (3.5, 60),   # #3 starter
    (2.6, 55),   # #3/4 starter
    (1.8, 50),   # #4 starter
    (1.0, 45),   # #4/5 starter
    (0.0, 40),   # Backend starter
    (float("-inf"), 30),  # Up & Down
]

# FV grade -> (surplus_value $, expected_war, star_odds %). Exact figures
# from the user-supplied "Prospect Surplus Value, WAR, And Star Odds By
# Grade" table.
FV_TO_VALUE = {
    70: {"hitter": (195_000_000, 27.5, 87.5), "pitcher": (195_000_000, 27.0, 87.5)},
    65: {"hitter": (95_000_000, 13.5, 40.0), "pitcher": (95_000_000, 13.5, 40.0)},
    60: {"hitter": (82_000_000, 12.5, 33.0), "pitcher": (70_000_000, 11.0, 21.0)},
    55: {"hitter": (55_000_000, 8.0, 17.5), "pitcher": (45_000_000, 7.0, 7.0)},
    50: {"hitter": (45_000_000, 7.0, 13.5), "pitcher": (33_500_000, 5.0, 7.0)},
    45: {"hitter": (14_500_000, 2.5, 3.5), "pitcher": (9_500_000, 1.6, 1.5)},
    40: {"hitter": (5_500_000, 0.75, 0.8), "pitcher": (4_000_000, 0.55, 0.4)},
}

# Same source table's half-tiers (45+/40+/35+) -- kept for completeness/
# documentation even though HITTER_WAR_TO_FV/PITCHER_WAR_TO_FV only ever
# produce full tiers, so these are currently unreferenced by _fv_to_value().
FV_TO_VALUE_HALF_TIERS = {
    "45+": {"hitter": (18_500_000, 3.2, 6.0), "pitcher": (15_000_000, 2.6, 3.0)},
    "40+": {"hitter": (8_000_000, 1.2, 1.8), "pitcher": (7_000_000, 1.0, 1.0)},
    "35+": {"hitter": (2_000_000, 0.3, 0.4), "pitcher": (1_500_000, 0.25, 0.4)},
}

# A current-form FV at or above this tier ("Bench Player"/"Backend starter")
# is the MLB-promotion-readiness signal. Only meaningful for players
# currently below level 1 -- this module has no visibility into level, so
# gating on that is the caller's (ticket 0069) responsibility.
PROMOTION_READY_FV_FLOOR = 40


def _war_to_fv(war, tiers):
    top_min, top_fv = tiers[0]
    if war > top_min:
        return top_fv
    for min_war, fv in tiers[1:]:
        if war >= min_war:
            return fv


def _fv_to_value(fv, player_type):
    """FV 80 has no published row (the source table tops out at 70) --
    falls back to FV 70's value as a conservative floor. FV below 35 ("Org
    guy"/"Up & Down", never assigned real trade value by the source
    primer) returns $0 rather than an invented number."""
    if fv >= 80:
        fv = 70
    if fv < 35:
        return {"surplus_value": 0, "expected_war": 0.0, "star_odds": 0.0}
    surplus_value, expected_war, star_odds = FV_TO_VALUE[fv][player_type]
    return {
        "surplus_value": surplus_value,
        "expected_war": expected_war,
        "star_odds": star_odds,
    }


def build_batter_talent_projection_input(
    player_row, rating_row, batting_talent_row, basepath_row,
    fielding_position_talent_row,
):
    """Builds a BatterProjection input dict for a talent-ceiling projection.

    Categories OOTP actually develops (contact-family batting grades,
    positional fitness) come from their _talent tables. Speed/steal/
    baserunning have no talent equivalent in OOTP (no players_basepath_talent
    table) and stay sourced from current ratings -- same for the underlying
    defensive skill ratings, but those don't feed BatterProjection at all
    (only position fitness does), so there's nothing to source for them
    here. See ticket 0043's Design choices.
    """
    return {
        "player_id": player_row["player_id"],
        "rating_id": rating_row["rating_id"],
        "rating_date": rating_row["rating_date"],
        "birth_date": player_row["birth_date"],
        "position": player_row["position"],
        "bats": player_row["bats"],
        "prone_overall": player_row["prone_overall"],
        "babip": batting_talent_row["babip"],
        "gap": batting_talent_row["gap"],
        "eye": batting_talent_row["eye"],
        "power": batting_talent_row["power"],
        "strikeouts": batting_talent_row["strikeouts"],
        "speed": basepath_row["speed"],
        "steal": basepath_row["steal"],
        "baserunning": basepath_row["baserunning"],
        "pos2": fielding_position_talent_row["pos2"],
        "pos3": fielding_position_talent_row["pos3"],
        "pos4": fielding_position_talent_row["pos4"],
        "pos5": fielding_position_talent_row["pos5"],
        "pos6": fielding_position_talent_row["pos6"],
        "pos7": fielding_position_talent_row["pos7"],
        "pos8": fielding_position_talent_row["pos8"],
        "pos9": fielding_position_talent_row["pos9"],
    }


def build_pitcher_talent_projection_input(
    player_row, rating_row, pitching_row, pitching_talent_row,
):
    """Builds a PitcherProjection input dict for a talent-ceiling
    projection. stuff/control/pbabip/hra come from players_pitching_talent
    (OOTP develops these). role/stamina/hold have no talent equivalent --
    role is a roster designation, not a rated attribute, and stamina/hold
    are current-only skill ratings -- so they stay sourced from the current
    players_pitching row. See ticket 0043's Design choices.
    """
    return {
        "rating_id": rating_row["rating_id"],
        "role": pitching_row["role"],
        "stuff": pitching_talent_row["stuff"],
        "control": pitching_talent_row["control"],
        "pbabip": pitching_talent_row["pbabip"],
        "hra": pitching_talent_row["hra"],
        "stamina": pitching_row["stamina"],
        "hold": pitching_row["hold"],
        "prone_overall": player_row["prone_overall"],
    }


def calculate_hitter_prospect_value(talent_input, current_input):
    """talent_input/current_input: BatterProjection-shaped dicts.
    talent_input is built via build_batter_talent_projection_input();
    current_input is the plain current-ratings dict this codebase's
    projection pipeline already builds (see get_projection_inputs.sql).

    Returns None ("not available") if either input is missing (e.g. no
    latest rating on file for this player), matching this codebase's
    established missing-input convention (ticket 0056).
    """
    if talent_input is None or current_input is None:
        return None

    talent_war = BatterProjection(talent_input).calc_expected_stats()["value"]["WAR"]
    current_war = BatterProjection(current_input).calc_expected_stats()["value"]["WAR"]

    fv = _war_to_fv(talent_war, HITTER_WAR_TO_FV)
    current_fv = _war_to_fv(current_war, HITTER_WAR_TO_FV)

    return {
        "talent_war": talent_war,
        "fv": fv,
        **_fv_to_value(fv, "hitter"),
        "current_war": current_war,
        "current_fv": current_fv,
        "mlb_promotion_ready": current_fv >= PROMOTION_READY_FV_FLOOR,
    }


def calculate_pitcher_prospect_value(talent_input, current_input):
    """Pitcher equivalent of calculate_hitter_prospect_value(). Applies to
    both SP and RP -- see PITCHER_WAR_TO_FV's comment for why no RP
    exclusion/adjustment is needed. Returns None ("not available") only for
    missing input, same as the hitter version.
    """
    if talent_input is None or current_input is None:
        return None

    talent_war = PitcherProjection(talent_input).calc_expected_stats()["pitching_value"]["WAR"]
    current_war = PitcherProjection(current_input).calc_expected_stats()["pitching_value"]["WAR"]

    fv = _war_to_fv(talent_war, PITCHER_WAR_TO_FV)
    current_fv = _war_to_fv(current_war, PITCHER_WAR_TO_FV)

    return {
        "talent_war": talent_war,
        "fv": fv,
        **_fv_to_value(fv, "pitcher"),
        "current_war": current_war,
        "current_fv": current_fv,
        "mlb_promotion_ready": current_fv >= PROMOTION_READY_FV_FLOOR,
    }
