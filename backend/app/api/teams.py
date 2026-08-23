import os

from flask import Blueprint, jsonify, current_app
from app.db.connection import get_db, close_db
from app.player_projection.contract_value import compute_surplus_value_and_recommendation

bp = Blueprint("teams", __name__, url_prefix="/api/teams")

# Levels far enough from MLB-readiness that current-rating WAR isn't a
# meaningful ranking signal (ticket 0064): BatterProjection/PitcherProjection
# compute WAR as "how good would this player be in MLB right now with his
# current ratings," with no level/league adjustment anywhere in the
# pipeline (confirmed by reading both classes) -- a fair-ish proxy for
# AAA/AA prospects close to the majors, but badly understates A-ball/
# Rookie prospects who haven't developed yet. These levels get a roster
# count per position instead of a ranked player list.
COUNT_ONLY_LEVELS = {4, 6}

# Display order for the roster-strength widget (ticket 0081) -- position
# players only, per the user 2026-08-23 (pitchers excluded, see
# get_team_roster_strength.sql's docstring). An unrecognized group_code
# (shouldn't happen; defensive only) sorts last via .get()'s default
# rather than raising.
ROSTER_STRENGTH_GROUP_ORDER = [
    "C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH",
]

# The 50th-percentile "average" cutoff (ticket 0081, resolved with the
# user 2026-08-23): a position is a weakness if this team's best player
# there ranks below league-average at that position; a surplus if 2+ of
# this team's players there rank at/above league-average.
ROSTER_STRENGTH_MEDIAN_CUTOFF = 50
ROSTER_STRENGTH_SURPLUS_MIN_COUNT = 2

# Notable-delta threshold for the over/underperformers widget (ticket
# 0080) -- first-pass heuristic per the ticket's own Design choices
# ("needs a first-pass heuristic during implementation, tunable later"),
# chosen by inspecting real actual-vs-projected WAR deltas across a real
# roster (post qualifying-sample filtering -- see
# get_team_performance_deltas.sql): observed deltas ranged roughly
# -2.6..+4.1 WAR, and 1.0 WAR (a real, standalone win of value) is a
# natural line that surfaces a meaningful subset rather than either the
# whole roster or almost nobody.
PERFORMANCE_DELTA_NOTABLE_THRESHOLD = 1.0


@bp.route("", methods=["GET"])
def get_mlb_teams():
    """
    Retrieve every real MLB team, for the depth-chart/prospect-pipeline
    team pickers (tickets 0064/0070) -- the only places today that need to
    list teams rather than look one up by id.

    `level = 1` alone isn't enough: this save also tags 4 exhibition teams
    (AL/NL All-Stars, AL/NL Future Stars) as level 1, none of which have a
    real city (`city_id = 0`) or ever roster real players -- excluded via
    `city_id != 0`, the reliable "is this a real team" signal (division_id/
    league_id alone aren't -- real teams share division_id = 0 too).

    background_color/text_color (ticket 0073): the org's real colors, so
    `ProspectPipeline.vue` can theme its header the same way
    `TeamDepthChart.vue` already does from `get_org_depth_chart.sql` --
    added here rather than a new endpoint since this route already reads
    from `teams` and every consumer of this list (both pickers) already
    fetches it regardless.

    Returns:
        JSON response: a list of {team_id, name, abbr, nickname,
        background_color, text_color}, sorted by name.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute(
                "SELECT team_id, name, abbr, nickname, background_color, text_color "
                "FROM teams WHERE level = 1 AND city_id != 0 ORDER BY name"
            )
            rows = cursor.fetchall()
        return jsonify(rows)
    finally:
        close_db()


@bp.route("/<int:team_id>/depth-chart", methods=["GET"])
def get_team_depth_chart(team_id):
    """
    Retrieve an MLB team's full organizational depth chart (ticket 0063):
    its MLB roster plus its AAA/AA/A/Rookie affiliates
    (teams.parent_team_id/level, ticket 0062), grouped by level and
    position (pitchers split into SP/RP), ranked by projected WAR
    descending within each group.

    Args:
        team_id (int): The MLB team's id. Must be a level-1 (MLB) team --
            an individual affiliate's own team_id is not a valid depth-
            chart root.

    Returns:
        JSON response:
            - 404 if team_id isn't a real level-1 MLB team.
            - {"team_id": ..., "team_name": ..., "background_color": ...,
              "text_color": ..., "levels": {level: {group: ...}}}
              otherwise, where `background_color`/`text_color` are the
              MLB team's real colors (`teams.background_color`/
              `text_color`, ticket 0064) for frontend theming, `level` is
              the raw teams.level int (1/2/3/4/6 -- 5 is excluded, see
              ticket 0062) and `group` is a position code (e.g. "1B",
              "SS") or "SP"/"RP" for pitchers.
              For levels 1/2/3 (MLB/AAA/AA), `group` maps to a WAR-sorted
              list of player entries: player_id, first_name, last_name,
              team_id, team_abbr (distinguishes affiliates sharing a
              level), war (batting + pitching WAR summed for a two-way
              player, per user request -- see get_org_depth_chart.sql;
              null only for a player with no current rating at all),
              is_promotion_candidate (top 20% of
              WAR at that level *league-wide*, AAA/AA only -- see
              get_org_depth_chart.sql; always false at MLB).
              For levels 4/6 (A/High-A, Rookie/Complex), `group` maps to a
              plain roster-count int instead -- current-rating WAR isn't a
              meaningful ranking signal that far from MLB-readiness (ticket
              0064), so no player list or WAR is returned for these levels.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute(
                "SELECT level, city_id, name, nickname, background_color, "
                "text_color FROM teams WHERE team_id = %(team_id)s",
                {"team_id": team_id},
            )
            team_row = cursor.fetchone()

        # city_id != 0 excludes the save's exhibition teams (AL/NL
        # All-Stars, AL/NL Future Stars) that are also tagged level = 1 --
        # see get_mlb_teams' docstring.
        if (
            team_row is None
            or team_row["level"] != 1
            or team_row["city_id"] == 0
        ):
            return jsonify({"error": "Team not found"}), 404

        sql_path = os.path.join(
            "db", "sql_scripts", "api", "get_org_depth_chart.sql"
        )
        with current_app.open_resource(sql_path, "r") as f:
            sql = f.read()

        with con.cursor() as cursor:
            cursor.execute(sql, {"team_id": team_id})
            rows = cursor.fetchall()

        levels: dict = {}
        for row in rows:
            level = row["level"]
            # is_twp takes priority over position (ticket 0067 post-close
            # correction): a real two-way player's listed position isn't
            # always 'P' (confirmed real case: Shohei Ohtani is 'DH' but
            # has a real players_pitching row) -- checking is_twp first
            # keeps the depth chart's grouping consistent with the player
            # page's identical is_twp check, instead of only ever
            # recognizing a TWP whose position happens to read 'P'.
            if row["is_twp"]:
                group = "TWP"
            elif row["position"] == "P":
                group = row["role_group"]
            else:
                group = row["position"]
            if level in COUNT_ONLY_LEVELS:
                counts = levels.setdefault(level, {})
                counts[group] = counts.get(group, 0) + 1
                continue
            levels.setdefault(level, {}).setdefault(group, []).append(
                {
                    "player_id": row["player_id"],
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "team_id": row["team_id"],
                    "team_abbr": row["team_abbr"],
                    "war": row["war"],
                    "is_promotion_candidate": bool(row["is_promotion_candidate"]),
                }
            )

        for level, groups in levels.items():
            if level in COUNT_ONLY_LEVELS:
                continue
            for players in groups.values():
                players.sort(
                    key=lambda p: p["war"] if p["war"] is not None else float("-inf"),
                    reverse=True,
                )

        return jsonify(
            {
                "team_id": team_id,
                "team_name": f"{team_row['name']} {team_row['nickname']}".strip(),
                "background_color": team_row["background_color"],
                "text_color": team_row["text_color"],
                "levels": levels,
            }
        )
    finally:
        close_db()


@bp.route("/<int:team_id>/war-summary", methods=["GET"])
def get_team_war_summary(team_id):
    """
    Retrieve an MLB team's current-roster WAR aggregate and its power
    ranking among all real MLB teams by that same figure (ticket 0079),
    for the GM Command Center dashboard's headline stat (ticket 0038).
    Sums players_run_value.WAR (batting) + players_pitching_run_value.WAR
    (pitching) at each player's latest rating snapshot, two-way players
    counted for both sides -- same convention as get_org_depth_chart.sql
    (ticket 0063). MLB (level = 1) roster only -- full-org/affiliate WAR
    is covered in more detail by ticket 0081's per-position breakdown
    instead.

    Args:
        team_id (int): The MLB team's id. Must be a level-1 (MLB) team --
            an individual affiliate's own team_id is not valid here.

    Returns:
        JSON response:
            - 404 if team_id isn't a real level-1 MLB team.
            - {"team_id": ..., "war": ..., "rank": ..., "total_teams": ...}
              otherwise, where war is the summed team WAR (0 if the
              roster has no rated players yet), rank is this team's
              1-indexed rank by war among all real MLB teams (ties share
              a rank, per get_team_war_summary.sql's RANK() -- not
              ROW_NUMBER()), and total_teams is the league size the rank
              is out of.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute(
                "SELECT level, city_id FROM teams WHERE team_id = %(team_id)s",
                {"team_id": team_id},
            )
            team_row = cursor.fetchone()

        # city_id != 0 excludes the save's exhibition teams also tagged
        # level = 1 -- see get_mlb_teams'/get_team_depth_chart's docstrings.
        if (
            team_row is None
            or team_row["level"] != 1
            or team_row["city_id"] == 0
        ):
            return jsonify({"error": "Team not found"}), 404

        sql_path = os.path.join(
            "db", "sql_scripts", "api", "get_team_war_summary.sql"
        )
        with current_app.open_resource(sql_path, "r") as f:
            sql = f.read()

        with con.cursor() as cursor:
            cursor.execute(sql, {"team_id": team_id})
            row = cursor.fetchone()

        return jsonify(
            {
                "team_id": team_id,
                "war": row["war"],
                "rank": row["team_rank"],
                "total_teams": row["total_teams"],
            }
        )
    finally:
        close_db()


@bp.route("/<int:team_id>/roster-strength", methods=["GET"])
def get_team_roster_strength(team_id):
    """
    Classify each of an MLB team's batting position groups as a
    "weakness," "surplus," or neither (ticket 0081), for the GM Command
    Center dashboard. Position players only -- pitchers are excluded
    entirely, per the user 2026-08-23 (see get_team_roster_strength.sql's
    docstring). A group is a weakness if this team's best player there
    ranks below the 50th percentile against every real MLB team's players
    at that same group; a surplus if 2+ of this team's players there rank
    at/above the 50th percentile (ROSTER_STRENGTH_MEDIAN_CUTOFF/
    ROSTER_STRENGTH_SURPLUS_MIN_COUNT, resolved with the user
    2026-08-23). Named players are included (post-close revision) so the
    widget can say *who* is thin/deep at a position, not just the raw
    number.

    Args:
        team_id (int): The MLB team's id. Must be a level-1 (MLB) team --
            an individual affiliate's own team_id is not valid here.

    Returns:
        JSON response:
            - 404 if team_id isn't a real level-1 MLB team.
            - {"team_id": ..., "groups": [...]} otherwise, where each
              group entry is {"group": ..., "classification": "weakness"
              | "surplus" | "neutral", "best_war": ... | null,
              "best_percentile": ... | null, "best_player": {"player_id",
              "first_name", "last_name", "league_rank"} | null,
              "league_pool_size": ..., "surplus_count": ...,
              "surplus_players": [{"player_id", "first_name",
              "last_name", "war", "league_rank"}, ...]}. best_war/
              best_percentile/best_player are null when the team has no
              rated player at that group at all (always a weakness).
              league_rank is each named player's 1-indexed ordinal rank
              by WAR against every real MLB team's players at that same
              group (ties share a rank -- same convention as
              get_team_war_summary.sql's team power ranking);
              league_pool_size is the group's total rated-player count
              league-wide, i.e. what league_rank is "out of." surplus_players
              lists every one of this team's players at/above the 50th
              percentile at that group (only 2+ of them makes it an
              actual "surplus" classification, but the list is returned
              regardless of classification). Groups are ordered by
              ROSTER_STRENGTH_GROUP_ORDER.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute(
                "SELECT level, city_id FROM teams WHERE team_id = %(team_id)s",
                {"team_id": team_id},
            )
            team_row = cursor.fetchone()

        if (
            team_row is None
            or team_row["level"] != 1
            or team_row["city_id"] == 0
        ):
            return jsonify({"error": "Team not found"}), 404

        sql_path = os.path.join(
            "db", "sql_scripts", "api", "get_team_roster_strength.sql"
        )
        with current_app.open_resource(sql_path, "r") as f:
            sql = f.read()

        with con.cursor() as cursor:
            cursor.execute(sql, {"team_id": team_id})
            rows = cursor.fetchall()

        # One row per (group, this team's player) pair, plus a single
        # all-NULL-player placeholder row for a group with nobody
        # rostered there -- see get_team_roster_strength.sql's docstring.
        rows_by_group: dict = {}
        for row in rows:
            rows_by_group.setdefault(row["group_code"], []).append(row)

        groups = []
        for group_code, group_rows in rows_by_group.items():
            rated_rows = [
                r for r in group_rows if r["player_id"] is not None and r["war"] is not None
            ]

            # league_pool_size is the same for every row in a group
            # (including the all-NULL placeholder row) -- see
            # get_team_roster_strength.sql.
            league_pool_size = group_rows[0]["league_pool_size"]

            if rated_rows:
                best_row = max(rated_rows, key=lambda r: r["war"])
                best_war = best_row["war"]
                # SQL's ROUND() over a division returns a DECIMAL, which
                # pymysql/Flask would otherwise serialize as a numeric
                # *string* -- cast back to a real int for the frontend.
                best_percentile = int(best_row["league_percentile"])
                best_player = {
                    "player_id": best_row["player_id"],
                    "first_name": best_row["first_name"],
                    "last_name": best_row["last_name"],
                    "league_rank": best_row["league_rank"],
                }
            else:
                best_war = None
                best_percentile = None
                best_player = None

            surplus_players = sorted(
                (
                    {
                        "player_id": r["player_id"],
                        "first_name": r["first_name"],
                        "last_name": r["last_name"],
                        "war": r["war"],
                        "league_rank": r["league_rank"],
                    }
                    for r in rated_rows
                    if int(r["league_percentile"]) >= ROSTER_STRENGTH_MEDIAN_CUTOFF
                ),
                key=lambda p: p["war"],
                reverse=True,
            )

            if best_war is None or best_percentile < ROSTER_STRENGTH_MEDIAN_CUTOFF:
                classification = "weakness"
            elif len(surplus_players) >= ROSTER_STRENGTH_SURPLUS_MIN_COUNT:
                classification = "surplus"
            else:
                classification = "neutral"

            groups.append(
                {
                    "group": group_code,
                    "classification": classification,
                    "best_war": best_war,
                    "best_percentile": best_percentile,
                    "best_player": best_player,
                    "league_pool_size": league_pool_size,
                    "surplus_count": len(surplus_players),
                    "surplus_players": surplus_players,
                }
            )

        groups.sort(
            key=lambda g: ROSTER_STRENGTH_GROUP_ORDER.index(g["group"])
            if g["group"] in ROSTER_STRENGTH_GROUP_ORDER
            else len(ROSTER_STRENGTH_GROUP_ORDER)
        )

        return jsonify({"team_id": team_id, "groups": groups})
    finally:
        close_db()


@bp.route("/<int:team_id>/contract-decisions", methods=["GET"])
def get_team_contract_decisions(team_id):
    """
    List an MLB team's players with a live contract/arbitration decision
    (ticket 0082), for the GM Command Center dashboard -- reuses
    0056/0058's surplus-value/recommendation calculation
    (compute_surplus_value_and_recommendation) across the team's roster
    in one query instead of the frontend looping
    GET /api/players/<id>/surplus-value once per player, an N+1 fetch
    pattern for a 25-40+ player roster.

    Args:
        team_id (int): The MLB team's id. Must be a level-1 (MLB) team --
            an individual affiliate's own team_id is not valid here.

    Returns:
        JSON response:
            - 404 if team_id isn't a real level-1 MLB team.
            - {"team_id": ..., "players": [...]} otherwise, where each
              entry is {"player_id", "first_name", "last_name",
              "recommendation", "total_surplus"} for every roster player
              compute_surplus_value_and_recommendation actually returned
              a recommendation for -- currently arbitration-eligible,
              with a computable surplus value, *and* not already
              extended through their entire projected horizon (ticket
              0082 fix -- see that function's docstring for why a
              fully-signed player has no live decision to surface here).
              A player missing any of those simply doesn't appear.
              Grouping by recommendation type is left to the frontend.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute(
                "SELECT level, city_id FROM teams WHERE team_id = %(team_id)s",
                {"team_id": team_id},
            )
            team_row = cursor.fetchone()

        if (
            team_row is None
            or team_row["level"] != 1
            or team_row["city_id"] == 0
        ):
            return jsonify({"error": "Team not found"}), 404

        sql_path = os.path.join(
            "db", "sql_scripts", "api", "get_team_contract_inputs.sql"
        )
        with current_app.open_resource(sql_path, "r") as f:
            sql = f.read()

        with con.cursor() as cursor:
            cursor.execute(sql, {"team_id": team_id})
            rows = cursor.fetchall()

        players = []
        for row in rows:
            result = compute_surplus_value_and_recommendation(row)
            if result is None or "recommendation" not in result:
                continue
            players.append(
                {
                    "player_id": row["player_id"],
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "recommendation": result["recommendation"],
                    "total_surplus": result["total_surplus"],
                }
            )

        return jsonify({"team_id": team_id, "players": players})
    finally:
        close_db()


@bp.route("/<int:team_id>/performance-deltas", methods=["GET"])
def get_team_performance_deltas(team_id):
    """
    List an MLB team's active roster players whose real current-season
    actual WAR notably over/underperforms their latest projected WAR
    (ticket 0080), for the GM Command Center dashboard. "Notable" is
    |actual - projected| >= PERFORMANCE_DELTA_NOTABLE_THRESHOLD -- a
    first-pass heuristic, tunable later (ticket's own Design choices).
    Only players with a qualifying real sample this season (PA >= 50
    batting, outs >= 60 pitching) are even considered -- see
    get_team_performance_deltas.sql's docstring for why a player who
    hasn't played (yet) this season is excluded outright rather than
    compared against a fabricated zero.

    Args:
        team_id (int): The MLB team's id. Must be a level-1 (MLB) team --
            an individual affiliate's own team_id is not valid here.

    Returns:
        JSON response:
            - 404 if team_id isn't a real level-1 MLB team.
            - {"team_id": ..., "players": [...]} otherwise, where each
              entry is {"player_id", "first_name", "last_name",
              "actual_war", "projected_war", "delta"} for every
              qualifying roster player whose |delta| >=
              PERFORMANCE_DELTA_NOTABLE_THRESHOLD, sorted by delta
              descending (overperformers first). A qualifying player
              inside the threshold, or with no qualifying sample at all,
              simply doesn't appear. actual_war/delta sum batting +
              pitching for a two-way player, same convention as
              get_team_war_summary.sql.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute(
                "SELECT level, city_id FROM teams WHERE team_id = %(team_id)s",
                {"team_id": team_id},
            )
            team_row = cursor.fetchone()

        if (
            team_row is None
            or team_row["level"] != 1
            or team_row["city_id"] == 0
        ):
            return jsonify({"error": "Team not found"}), 404

        sql_path = os.path.join(
            "db", "sql_scripts", "api", "get_team_performance_deltas.sql"
        )
        with current_app.open_resource(sql_path, "r") as f:
            sql = f.read()

        with con.cursor() as cursor:
            cursor.execute(sql, {"team_id": team_id})
            rows = cursor.fetchall()

        players = []
        for row in rows:
            delta = row["delta"]
            if abs(delta) < PERFORMANCE_DELTA_NOTABLE_THRESHOLD:
                continue
            actual_war = (row["actual_batting_war"] or 0) + (row["actual_pitching_war"] or 0)
            players.append(
                {
                    "player_id": row["player_id"],
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "actual_war": actual_war,
                    "projected_war": row["projected_war"],
                    "delta": delta,
                }
            )

        return jsonify({"team_id": team_id, "players": players})
    finally:
        close_db()
