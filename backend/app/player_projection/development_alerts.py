"""
Turn 0050's rating-trend deltas into short narrative alerts (ticket 0051).

Only rows where 0050 already flagged `exceeded` produce an alert -- this
module doesn't re-derive significance, it just puts words to it.
"""

_BATTING_LABELS = {
    "babip": "BABIP",
    "power": "power",
    "eye": "eye",
}

_PITCHING_LABELS = {
    "stuff": "stuff",
    "movement": "movement",
    "control": "control",
    "velocity": "velocity",
    "stamina": "stamina",
}

_FIELDING_LABELS = {
    "infield_range": "infield range",
    "outfield_range": "outfield range",
    "catcher_framing": "pitch framing",
}

_BASEPATH_LABELS = {
    "speed": "speed",
}

# "Overall" (current-ability) tables -- 0050's +/-5 threshold. Only reached
# for a player whose latest heap has league_id = 203 (MLB) for the
# batting/pitching categories; always reached for fielding/basepath, which
# have no talent counterpart (see get_player_rating_trends.sql).
_OVERALL_LABELS_BY_TABLE = {
    "players_batting": _BATTING_LABELS,
    "players_pitching": _PITCHING_LABELS,
    "players_fielding": _FIELDING_LABELS,
    "players_basepath": _BASEPATH_LABELS,
}

# "Talent" (potential/ceiling) tables -- 0050's +/-10 threshold. Only
# reached for a non-MLB player (prospect); reuses the same column->label
# text as the overall table, only the message template differs (see
# _build_message).
_TALENT_LABELS_BY_TABLE = {
    "players_batting_talent": _BATTING_LABELS,
    "players_pitching_talent": _PITCHING_LABELS,
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
