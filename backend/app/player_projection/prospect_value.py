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

# Development-risk tag (ticket 0072, user request): a "+"/"-" badge next to
# the FV grade showing how close a prospect's current-form ability already
# is to his talent ceiling -- a visible signal the GM can see and judge for
# themselves. Explicitly independent of prone_overall's existing
# injury-risk concept (0059's INJURY_MULTIPLIERS) per user clarification --
# "far from ceiling" and "injury-prone" aren't folded together here.
#
# Thresholds are a placeholder, tunable later against real outcomes (same
# convention as 0056's age-decline curve/0059's injury multipliers): FV
# tiers step in 5s/10s (see HITTER_WAR_TO_FV/PITCHER_WAR_TO_FV), so a
# >=20-point gap is roughly 2-3+ tiers of distance-to-ceiling ("-", risky),
# and a <=5-point gap means current form is already at or one tier from the
# ceiling grade ("+", safer bet). Anything in between gets no tag --
# most prospects, not worth flagging either way.
RISK_TAG_HIGH_GAP = 20
RISK_TAG_LOW_GAP = 5

# Post-close correction (user request): the tag now also scales
# surplus_value/star_odds, on top of (not instead of) staying visible as a
# tag -- fv/expected_war stay pure ceiling numbers, unmodified, per this
# ticket's original distinction between "what he could become" (ceiling,
# untouched) and "what he's worth right now, given how likely that is"
# (the dollar/probability outputs, which this modifier scales). Values are
# a placeholder, tunable later, same convention as RISK_TAG_HIGH_GAP/
# RISK_TAG_LOW_GAP above.
RISK_TAG_MODIFIERS = {
    "+": 1.10,  # already close to ceiling -- small premium
    "-": 0.70,  # still far from ceiling -- real discount
    None: 1.0,
}


def _risk_tag(fv, current_fv):
    gap = fv - current_fv
    if gap >= RISK_TAG_HIGH_GAP:
        return "-"
    if gap <= RISK_TAG_LOW_GAP:
        return "+"
    return None


def _apply_risk_modifier(value, risk_tag):
    modifier = RISK_TAG_MODIFIERS[risk_tag]
    return {
        **value,
        "surplus_value": round(value["surplus_value"] * modifier),
        # Capped at 100% -- a premium on an already-high base (e.g. FV 70's
        # 87.5%) shouldn't produce a nonsensical probability above certain.
        "star_odds": min(round(value["star_odds"] * modifier, 1), 100.0),
    }


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


def batter_projection_inputs_from_row(row):
    """Slices a wide SQL row (get_prospects.sql's or ticket 0075's
    get_prospect_value_inputs.sql's column shape -- both use the same
    bat_*/bat_*_talent/speed/steal/baserunning/posN/posN_talent naming) into
    (talent_input, current_input) for a position player. Promoted here
    (ticket 0075) from app/api/prospects.py's private helper of the same
    shape, so both the API route and the heap-processing persistence step
    (app/db/projection.py) share one implementation."""
    player_row = {
        "player_id": row["player_id"], "birth_date": row["birth_date"],
        "position": row["position"], "bats": row["bats"],
        "prone_overall": row["prone_overall"],
    }
    rating_row = {"rating_id": row["rating_id"], "rating_date": row["rating_date"]}
    batting_talent_row = {
        "babip": row["bat_babip_talent"], "gap": row["bat_gap_talent"],
        "eye": row["bat_eye_talent"], "power": row["bat_power_talent"],
        "strikeouts": row["bat_strikeouts_talent"],
    }
    basepath_row = {
        "speed": row["speed"], "steal": row["steal"],
        "baserunning": row["baserunning"],
    }
    fielding_position_talent_row = {
        f"pos{i}": row[f"pos{i}_talent"] for i in range(2, 10)
    }

    talent_input = build_batter_talent_projection_input(
        player_row, rating_row, batting_talent_row, basepath_row,
        fielding_position_talent_row,
    )
    current_input = {
        **player_row, **rating_row,
        "babip": row["bat_babip"], "gap": row["bat_gap"], "eye": row["bat_eye"],
        "power": row["bat_power"], "strikeouts": row["bat_strikeouts"],
        **basepath_row,
        **{f"pos{i}": row[f"pos{i}"] for i in range(2, 10)},
    }
    return talent_input, current_input


def pitcher_projection_inputs_from_row(row):
    """Pitcher equivalent of batter_projection_inputs_from_row() -- same
    promotion, same pitch_*/pitch_*_talent column naming shared by
    get_prospects.sql and get_prospect_value_inputs.sql."""
    player_row = {"prone_overall": row["prone_overall"]}
    rating_row = {"rating_id": row["rating_id"]}
    pitching_row = {
        "role": row["pitch_role"], "stamina": row["pitch_stamina"],
        "hold": row["pitch_hold"],
    }
    pitching_talent_row = {
        "stuff": row["pitch_stuff_talent"], "control": row["pitch_control_talent"],
        "pbabip": row["pitch_pbabip_talent"], "hra": row["pitch_hra_talent"],
    }

    talent_input = build_pitcher_talent_projection_input(
        player_row, rating_row, pitching_row, pitching_talent_row,
    )
    current_input = {
        **rating_row, **pitching_row, **player_row,
        "stuff": row["pitch_stuff"], "control": row["pitch_control"],
        "pbabip": row["pitch_pbabip"], "hra": row["pitch_hra"],
    }
    return talent_input, current_input


def calculate_prospect_value_from_row(row):
    """Runs the calc for whichever side matches players.position (same
    explicit-position-gate convention get_player_rating_trends.sql uses --
    a two-way player is scored on their listed-position side only). Shared
    by app/api/prospects.py (live, per-request) and app/db/projection.py's
    process_prospect() (per-heap, persisted -- ticket 0075). Doesn't catch
    exceptions itself -- callers wrap this the same way
    process_player/process_pitcher already wrap BatterProjection/
    PitcherProjection, logging and treating a failure as "no result"
    rather than crashing the whole batch/request.

    Real cases found running update-db league-wide (ticket 0075), both the
    same class of sparse-data gap as 0069's Mason Brassfield/Boston Kellner
    finding, not a real error -- a player with no matching rating-side row
    at this heap at all:
    - position = 'P' with no players_pitching row (role comes back NULL
      from the LEFT JOIN in get_prospects.sql/get_prospect_value_inputs.sql).
      PitcherProjection itself raises ValueError("Unrecognized pitcher
      role...") for a None role.
    - A position player with no players_batting and/or no
      players_batting_talent row (bat_babip/bat_babip_talent come back
      NULL the same way). BatterProjection's rating lookups
      (self.bat_constants.loc[rating, feature]) raise KeyError(None) for a
      None rating -- str(KeyError(None)) renders as the literally
      unhelpful message "None", which is what actually surfaced in the
      logs (ticket 0075's live verification).
    Both would otherwise surface as a misleading "Error processing..."
    warning at the caller for an entirely predictable, checkable
    condition -- short-circuited here to a clean "not available" instead.
    """
    if row["position"] == "P":
        if row.get("pitch_role") is None:
            return None
        talent_input, current_input = pitcher_projection_inputs_from_row(row)
        return calculate_pitcher_prospect_value(talent_input, current_input)
    if row.get("bat_babip") is None or row.get("bat_babip_talent") is None:
        return None
    talent_input, current_input = batter_projection_inputs_from_row(row)
    return calculate_hitter_prospect_value(talent_input, current_input)


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
    risk_tag = _risk_tag(fv, current_fv)

    return {
        "talent_war": talent_war,
        "fv": fv,
        **_apply_risk_modifier(_fv_to_value(fv, "hitter"), risk_tag),
        "current_war": current_war,
        "current_fv": current_fv,
        "mlb_promotion_ready": current_fv >= PROMOTION_READY_FV_FLOOR,
        "risk_tag": risk_tag,
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
    risk_tag = _risk_tag(fv, current_fv)

    return {
        "talent_war": talent_war,
        "fv": fv,
        **_apply_risk_modifier(_fv_to_value(fv, "pitcher"), risk_tag),
        "current_war": current_war,
        "current_fv": current_fv,
        "mlb_promotion_ready": current_fv >= PROMOTION_READY_FV_FLOOR,
        "risk_tag": risk_tag,
    }
