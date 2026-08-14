"""
Turn 0050's rating-trend deltas into short narrative alerts (ticket 0051).

Only rows where 0050 already flagged `exceeded` produce an alert -- this
module doesn't re-derive significance, it just puts words to it.
"""

_BATTING_LABELS = {
    "contact": "contact",
    "gap": "gap power",
    "eye": "eye",
    "strikeouts": "strikeout avoidance",
    "power": "power",
    "babip": "BABIP",
    "bunt": "bunting",
    "bunt_for_hit": "bunting for a hit",
}

_PITCHING_LABELS = {
    "stuff": "stuff",
    "movement": "movement",
    "hra": "home-run prevention",
    "pbabip": "BABIP prevention",
    "control": "control",
    "balk": "balk avoidance",
    "hp": "hit-by-pitch avoidance",
    "wild_pitch": "wild-pitch avoidance",
    "velocity": "velocity",
    "arm_slot": "arm slot",
    "stamina": "stamina",
    "ground_fly": "ground/fly-ball tendency",
    "hold": "holding runners",
}

_FIELDING_LABELS = {
    "catcher_arm": "catcher arm strength",
    "catcher_ability": "catcher ability",
    "catcher_framing": "pitch framing",
    "infield_range": "infield range",
    "infield_arm": "infield arm strength",
    "infield_doubleplay": "double-play ability",
    "infield_error": "infield error avoidance",
    "outfield_range": "outfield range",
    "outfield_arm": "outfield arm strength",
    "outfield_error": "outfield error avoidance",
}

_BASEPATH_LABELS = {
    "speed": "speed",
    "steal_rate": "stolen-base attempt rate",
    "steal": "stolen-base ability",
    "baserunning": "baserunning",
}

# OOTP's numeric position codes, matching migration_short.sql's role/position
# conventions elsewhere in this codebase (1=P .. 9=RF).
_POSITION_LABELS = {
    "pos1": "pitcher defense",
    "pos2": "catcher defense",
    "pos3": "first base defense",
    "pos4": "second base defense",
    "pos5": "third base defense",
    "pos6": "shortstop defense",
    "pos7": "left field defense",
    "pos8": "center field defense",
    "pos9": "right field defense",
}

# "Overall" (current-ability) tables -- 0050's +/-5 threshold.
_OVERALL_LABELS_BY_TABLE = {
    "players_batting": _BATTING_LABELS,
    "players_pitching": _PITCHING_LABELS,
    "players_fielding": _FIELDING_LABELS,
    "players_basepath": _BASEPATH_LABELS,
    "players_fielding_position": _POSITION_LABELS,
}

# "Talent" (potential/ceiling) tables -- 0050's +/-10 threshold. Reuse the
# same column->label text as their overall counterparts; only the message
# template differs (see _build_message).
_TALENT_LABELS_BY_TABLE = {
    "players_batting_talent": _BATTING_LABELS,
    "players_pitching_talent": _PITCHING_LABELS,
    "players_fielding_position_talent": _POSITION_LABELS,
}


def _label_for(table_name, column_name):
    labels = _OVERALL_LABELS_BY_TABLE.get(table_name) or _TALENT_LABELS_BY_TABLE.get(
        table_name, {}
    )
    return labels.get(column_name, column_name.replace("_", " "))


def _build_message(table_name, label, delta):
    if table_name in _TALENT_LABELS_BY_TABLE:
        trend_word = "upward" if delta > 0 else "downward"
        return f"Scouts have revised {label} potential {trend_word}."
    direction = "improved" if delta > 0 else "declined"
    return f"{label[0].upper()}{label[1:]} has {direction}."


def get_development_alerts(trend_rows):
    """
    Args:
        trend_rows: the row list returned by
            `get_player_rating_trends.sql` (ticket 0050) -- each a dict with
            at least `table_name`, `column_name`, `delta`, `exceeded`.

    Returns:
        A list of `{table, column, direction, delta, message}` dicts, one
        per row where `exceeded` was true. Rows below threshold are
        dropped, not just filtered from display -- they carry no signal.
    """
    alerts = []
    for row in trend_rows:
        if not row["exceeded"]:
            continue

        table_name = row["table_name"]
        column_name = row["column_name"]
        delta = row["delta"]
        label = _label_for(table_name, column_name)

        alerts.append(
            {
                "table": table_name,
                "column": column_name,
                "direction": "improved" if delta > 0 else "declined",
                "delta": delta,
                "message": _build_message(table_name, label, delta),
            }
        )
    return alerts
