import os
import logging

from flask import Blueprint, jsonify, current_app, request
from app.db.connection import get_db, close_db
from app.player_projection.prospect_value import (
    build_batter_talent_projection_input,
    build_pitcher_talent_projection_input,
    calculate_hitter_prospect_value,
    calculate_pitcher_prospect_value,
)
from app.player_projection.development_alerts import get_development_alerts

bp = Blueprint("prospects", __name__, url_prefix="/api/prospects")

logger = logging.getLogger("app.api.prospects")


def _int_or_none(value):
    return int(value) if value is not None else None


def _batter_projection_inputs(row):
    """Returns (talent_input, current_input) for a position player -- see
    ticket 0068's build_batter_talent_projection_input for which columns
    come from talent vs. current tables."""
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


def _pitcher_projection_inputs(row):
    """Returns (talent_input, current_input) for a pitcher -- see ticket
    0068's build_pitcher_talent_projection_input for which columns come
    from talent vs. current tables."""
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


def _value_for(row):
    """Runs ticket 0068's calc for whichever side matches players.position
    (same explicit-position-gate convention as get_player_rating_trends.sql
    -- a two-way player is scored on their listed-position side only, not
    both). Returns {"available": False} for RP prospects, missing ratings,
    or any projection failure (mirrors app/db/projection.py's
    process_player/process_pitcher, which also treat a projection error as
    "no result" rather than a hard failure)."""
    try:
        if row["position"] == "P":
            talent_input, current_input = _pitcher_projection_inputs(row)
            result = calculate_pitcher_prospect_value(talent_input, current_input)
        else:
            talent_input, current_input = _batter_projection_inputs(row)
            result = calculate_hitter_prospect_value(talent_input, current_input)
    except Exception as e:
        logger.warning(f"Prospect value calc failed for player {row['player_id']}: {e}")
        result = None

    if result is None:
        return {"available": False}

    value = {
        "available": True,
        "fv": result["fv"],
        "surplus_value": result["surplus_value"],
        "expected_war": result["expected_war"],
        "star_odds": result["star_odds"],
        "current_fv": result["current_fv"],
    }
    # MLB-promotion-readiness is only meaningful for a player not yet in
    # the majors (ticket 0043's Design choices) -- omitted at level 1.
    if row["level"] != 1:
        value["mlb_promotion_ready"] = result["mlb_promotion_ready"]
    return value


def _trend_for(cursor, player_id):
    """Reuses ticket 0050/0051's trend query + alert layer as-is (no new
    SQL) -- collapses the per-category alert list into a single up/down/
    mixed/flat direction plus the underlying alerts."""
    with current_app.open_resource(
        os.path.join("db", "sql_scripts", "api", "get_player_rating_trends.sql"), "r",
    ) as f:
        sql = f.read()
    cursor.execute(sql, {"player_id": player_id})
    alerts = get_development_alerts(cursor.fetchall())

    directions = {a["direction"] for a in alerts}
    if not directions:
        direction = "flat"
    elif directions == {"improved"}:
        direction = "up"
    elif directions == {"declined"}:
        direction = "down"
    else:
        direction = "mixed"

    return {"direction": direction, "alerts": alerts}


@bp.route("", methods=["GET"])
def get_prospects():
    """
    Retrieve every prospect-eligible player (ticket 0069): currently on a
    non-MLB affiliate, or a just-debuted MLB rookie with zero recorded MLB
    service (see ticket 0043's Design choices for the full "prospect"
    definition).

    Query Parameters:
        - team_id (int, optional): scope to a single org -- the given MLB
          team plus every affiliate whose parent_team_id points at it.
        - position (str, optional): scope to a single players.position.
        - level (int, optional): scope to a single teams.level (1/2/3/4/6).

    Returns:
        JSON response: a list of objects, one per prospect --
            {player_id, first_name, last_name, position, age, team_id,
             team_abbr, level, parent_team_id, mlb_service_years,
             value: {available, fv, surplus_value, expected_war, star_odds,
                      current_fv, mlb_promotion_ready?},
             trend: {direction, alerts}}.
            value.available is false for RP-role prospects (ticket 0068's
            starters-only FV table) or any player with no usable rating
            data. mlb_promotion_ready is only present at level != 1.
    """
    team_id = _int_or_none(request.args.get("team_id"))
    position = request.args.get("position")
    level = _int_or_none(request.args.get("level"))

    con = get_db()
    try:
        sql_path = os.path.join("db", "sql_scripts", "api", "get_prospects.sql")
        with current_app.open_resource(sql_path, "r") as f:
            sql = f.read()

        with con.cursor() as cursor:
            cursor.execute(
                sql, {"team_id": team_id, "position": position, "level": level}
            )
            rows = cursor.fetchall()

            prospects = []
            for row in rows:
                prospects.append(
                    {
                        "player_id": row["player_id"],
                        "first_name": row["first_name"],
                        "last_name": row["last_name"],
                        "position": row["position"],
                        "age": row["age"],
                        "team_id": row["team_id"],
                        "team_abbr": row["team_abbr"],
                        "level": row["level"],
                        "parent_team_id": row["parent_team_id"],
                        "mlb_service_years": row["mlb_service_years"],
                        "value": _value_for(row),
                        "trend": _trend_for(cursor, row["player_id"]),
                    }
                )

        return jsonify(prospects)
    finally:
        close_db()
