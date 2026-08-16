import os
import logging

from flask import Blueprint, jsonify, current_app, request
from app.db.connection import get_db, close_db
from app.player_projection.prospect_value import (
    calculate_prospect_value_from_row,
    PROMOTION_READY_FV_FLOOR,
)
from app.player_projection.development_alerts import get_development_alerts

bp = Blueprint("prospects", __name__, url_prefix="/api/prospects")

logger = logging.getLogger("app.api.prospects")

# FV 30 ("Up & Down"/replacement-level org filler, per ticket 0043's
# HITTER_WAR_TO_FV/PITCHER_WAR_TO_FV) is excluded from the Prospect
# Pipeline entirely (user request, ticket 0072 follow-up) -- these players
# already carry $0 surplus value (FV_TO_VALUE's <35 floor), so listing
# hundreds of them added noise without adding a real trade-value signal.
EXCLUDED_FV = {30}


def _is_excluded(value):
    return value.get("available") and value.get("fv") in EXCLUDED_FV


def _int_or_none(value):
    return int(value) if value is not None else None


# Ticket 0076: league-wide leaderboard mode (?leaderboard=1). Top-overall
# is paginated at this page size by default; top-by-position/top-by-level
# are fixed-size sections, no pagination needed for either.
LEADERBOARD_DEFAULT_PAGE_SIZE = 50
LEADERBOARD_SECTION_SIZE = 10


def _leaderboard_entry(row):
    """Shapes one get_prospect_leaderboard.sql row into the same
    identity/value shape GET /api/prospects' org-scoped rows use, so the
    frontend (ticket 0077) can reuse its existing per-prospect rendering.
    Unlike _value_for(), there's no calc to run or failure to catch here --
    the value already sits in the row (ticket 0075's persisted table) --
    so "available" is always true; a prospect with no persisted row was
    never selected by the JOIN in the first place (see
    get_prospect_leaderboard.sql's own comment on this).
    mlb_promotion_ready is recomputed from current_fv at read time, same
    as _value_for() -- it's level-dependent and 0075 deliberately doesn't
    persist it.
    """
    value = {
        "available": True,
        "fv": row["fv"],
        "surplus_value": row["surplus_value"],
        "expected_war": row["expected_war"],
        "star_odds": row["star_odds"],
        "current_fv": row["current_fv"],
        "risk_tag": row["risk_tag"],
    }
    if row["level"] != 1:
        value["mlb_promotion_ready"] = row["current_fv"] >= PROMOTION_READY_FV_FLOOR
    return {
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
        "value": value,
    }


def _prospect_leaderboard(cursor, team_id, position, level, page, page_size):
    """Runs get_prospect_leaderboard.sql (ticket 0075's persisted table --
    no projection calls here at all) and shapes the three curated sections
    from the single, already fv-DESC-sorted result set: taking the first
    LEADERBOARD_SECTION_SIZE rows encountered per position/level group is
    equivalent to a separate top-N-per-group query, since the group
    subsets preserve the overall sort order."""
    sql_path = os.path.join("db", "sql_scripts", "api", "get_prospect_leaderboard.sql")
    with current_app.open_resource(sql_path, "r") as f:
        sql = f.read()
    cursor.execute(sql, {"team_id": team_id, "position": position, "level": level})
    rows = [row for row in cursor.fetchall() if row["fv"] not in EXCLUDED_FV]

    start = (page - 1) * page_size
    top_overall = rows[start:start + page_size]

    top_by_position = {}
    top_by_level = {}
    for row in rows:
        position_group = top_by_position.setdefault(row["position"], [])
        if len(position_group) < LEADERBOARD_SECTION_SIZE:
            position_group.append(row)

        level_group = top_by_level.setdefault(str(row["level"]), [])
        if len(level_group) < LEADERBOARD_SECTION_SIZE:
            level_group.append(row)

    return {
        "top_overall": {
            "page": page,
            "page_size": page_size,
            "total": len(rows),
            "results": [_leaderboard_entry(row) for row in top_overall],
        },
        "top_by_position": {
            pos: [_leaderboard_entry(row) for row in group]
            for pos, group in top_by_position.items()
        },
        "top_by_level": {
            lvl: [_leaderboard_entry(row) for row in group]
            for lvl, group in top_by_level.items()
        },
    }


def _value_for(row):
    """Runs ticket 0068's calc (via the shared
    calculate_prospect_value_from_row(), promoted to prospect_value.py in
    ticket 0075 so the heap-processing persistence step can reuse it too).
    Returns {"available": False} for missing ratings or any projection
    failure (mirrors app/db/projection.py's process_player/process_pitcher,
    which also treat a projection error as "no result" rather than a hard
    failure)."""
    try:
        result = calculate_prospect_value_from_row(row)
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
        # "+"/"-"/null development-risk tag (ticket 0072): how close the
        # player's current-form ability already is to his talent ceiling.
        "risk_tag": result["risk_tag"],
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
    definition). Excludes FV 30 ("Up & Down") players entirely (ticket
    0072 follow-up, user request) -- see EXCLUDED_FV.

    With `?leaderboard=1` (ticket 0076), switches to the league-wide
    leaderboard mode instead: reads ticket 0075's persisted
    players_prospect_value table (no per-request projection calls) and
    returns three curated sections instead of a flat list -- see the
    Returns section below. team_id/position/level still apply as filters
    in this mode too.

    Query Parameters:
        - team_id (int, optional): scope to a single org -- the given MLB
          team plus every affiliate whose parent_team_id points at it.
        - position (str, optional): scope to a single players.position.
        - level (int, optional): scope to a single teams.level (1/2/3/4/6).
        - leaderboard (optional): any truthy value switches to leaderboard
          mode (see above).
        - page, page_size (int, optional; leaderboard mode only): paginate
          the top_overall section. Defaults to page 1,
          LEADERBOARD_DEFAULT_PAGE_SIZE (50) per page.

    Returns:
        Default mode -- JSON response: a list of objects, one per
        prospect --
            {player_id, first_name, last_name, position, age, team_id,
             team_abbr, level, parent_team_id, mlb_service_years,
             value: {available, fv, surplus_value, expected_war, star_odds,
                      current_fv, risk_tag, mlb_promotion_ready?},
             trend: {direction, alerts}}.
            risk_tag (ticket 0072) is "+"/"-"/null: "-" if the player's
            fv is >= 20 points above current_fv (far from his talent
            ceiling, riskier bet), "+" if within 5 points (already close),
            null otherwise. Independent of prone_overall injury risk.
            value.available is false only for a player with no usable
            rating data (RP prospects get a real value -- ticket 0068's
            FV table applies to both SP and RP, a reliever's own smaller
            workload naturally produces a lower WAR/FV rather than needing
            exclusion). mlb_promotion_ready is only present at level != 1.

        Leaderboard mode -- JSON response:
            {"top_overall": {"page": ..., "page_size": ..., "total": ...,
                              "results": [<prospect entry>, ...]},
             "top_by_position": {"<position>": [<prospect entry>, ...]},
             "top_by_level": {"<level>": [<prospect entry>, ...]}}.
            Each <prospect entry> is the same identity/value shape as the
            default mode's list rows, minus "trend" (not computed in this
            mode -- see ticket 0076's Design choices). top_by_position/
            top_by_level cap at 10 entries per group; top_overall paginates
            per page/page_size. Every entry has value.available == true --
            a prospect with no persisted row simply isn't in the result set
            (see get_prospect_leaderboard.sql).
    """
    team_id = _int_or_none(request.args.get("team_id"))
    position = request.args.get("position")
    level = _int_or_none(request.args.get("level"))

    con = get_db()
    try:
        if request.args.get("leaderboard"):
            page = max(_int_or_none(request.args.get("page")) or 1, 1)
            page_size = _int_or_none(request.args.get("page_size")) or LEADERBOARD_DEFAULT_PAGE_SIZE
            with con.cursor() as cursor:
                return jsonify(
                    _prospect_leaderboard(cursor, team_id, position, level, page, page_size)
                )

        sql_path = os.path.join("db", "sql_scripts", "api", "get_prospects.sql")
        with current_app.open_resource(sql_path, "r") as f:
            sql = f.read()

        with con.cursor() as cursor:
            cursor.execute(
                sql,
                {"team_id": team_id, "position": position, "level": level, "player_id": None},
            )
            rows = cursor.fetchall()

            prospects = []
            for row in rows:
                value = _value_for(row)
                if _is_excluded(value):
                    continue
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
                        "value": value,
                        "trend": _trend_for(cursor, row["player_id"]),
                    }
                )

        return jsonify(prospects)
    finally:
        close_db()


@bp.route("/<int:player_id>", methods=["GET"])
def get_prospect_value(player_id):
    """
    Retrieve a single player's FV-based prospect value (ticket 0071), for
    the player page to show in place of 0056's contract-based surplus value
    whenever the player qualifies as a prospect (0043's definition) --
    reuses `get_prospects.sql` with its `player_id` filter rather than a
    parallel single-player query.

    Args:
        player_id (int): The unique ID of the player.

    Returns:
        JSON response:
            - {"is_prospect": false} if the player doesn't currently
              qualify as a prospect (the frontend should fall back to
              GET /api/players/<id>/surplus-value in this case), including
              an FV 30 ("Up & Down") player -- excluded the same way
              GET /api/prospects excludes them (ticket 0072 follow-up).
            - {"is_prospect": true, "available": ..., "fv": ...,
              "surplus_value": ..., "expected_war": ..., "star_odds": ...,
              "current_fv": ..., "risk_tag": ..., "mlb_promotion_ready": ...}
              otherwise -- same "value" shape as each row of
              GET /api/prospects, flattened to the top level. "available"
              can still be false (missing rating data) even when
              "is_prospect" is true.
    """
    con = get_db()
    try:
        sql_path = os.path.join("db", "sql_scripts", "api", "get_prospects.sql")
        with current_app.open_resource(sql_path, "r") as f:
            sql = f.read()

        with con.cursor() as cursor:
            cursor.execute(
                sql,
                {"team_id": None, "position": None, "level": None, "player_id": player_id},
            )
            row = cursor.fetchone()

        if row is None:
            return jsonify({"is_prospect": False})

        value = _value_for(row)
        if _is_excluded(value):
            return jsonify({"is_prospect": False})

        return jsonify({"is_prospect": True, **value})
    finally:
        close_db()
