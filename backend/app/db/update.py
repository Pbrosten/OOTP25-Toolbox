import os
import logging
import statistics
from datetime import date, datetime
from pathlib import Path
from multiprocessing import Pool, cpu_count

from tqdm import tqdm
from flask import current_app

from app.player_projection import batter as batter_projection
from app.player_projection import pitcher as pitcher_projection
from app.player_projection import contract_value

from .staging import (
    load_sql_dumps_into_staging,
    connect_staging_db,
    DUMP_INCLUSION_LIST,
)
from .migration import inject_heap_date
from .projection import (
    process_player,
    process_pitcher,
    process_prospect,
    update_projection_batches,
    update_pitching_projection_batches,
    update_prospect_value_batches,
)

logger = logging.getLogger("api/db/update")


def process_single_heap(heap_path, heap_index, total_heaps, db, short_heap=True):
    heap_date = extract_heap_date_from_path(heap_path)
    logger.info(
        f"[{heap_index}/{total_heaps}] Processing {'short' if short_heap else 'long'} heap: {heap_date[1]}_{heap_date[2]}"
    )

    # Connect and reset staging
    staging_db = connect_staging_db()
    try:
        load_sql_dumps_into_staging(staging_db, heap_path)
    finally:
        staging_db.close()

    counts = {"ratings_inserted": 0, "players_updated": 0, "projections_inserted": 0}

    if short_heap:
        counts["ratings_inserted"] = run_migration_short(heap_date, db)
        players = fetch_projection_inputs(heap_date, db)
        logger.info(f"Number of players: {len(players)}")

        projections = project_players(players)
        logger.info(f"Generated {len(projections)} projections (after filtering None)")

        if projections:
            logger.debug(f"First projection: {projections[0]}")

        counts["projections_inserted"] = insert_projections(projections, db)

        pitchers = fetch_pitcher_projection_inputs(heap_date, db)
        logger.info(f"Number of pitchers: {len(pitchers)}")

        pitcher_projections = project_pitchers(pitchers)
        logger.info(
            f"Generated {len(pitcher_projections)} pitcher projections (after filtering None)"
        )

        if pitcher_projections:
            logger.debug(f"First pitcher projection: {pitcher_projections[0]}")

        counts["projections_inserted"] += insert_pitcher_projections(pitcher_projections, db)

        # Ticket 0075: persist ticket 0068's FV/value calc per heap for the
        # league-wide leaderboard (0074/0076), scoped to prospect-eligible
        # candidates only (same definition 0069's live-compute path uses --
        # see get_prospect_value_inputs.sql). Short-heap-only, same reasoning
        # as the player/pitcher projections above -- talent/current ratings
        # only refresh on short heaps.
        prospects = fetch_prospect_value_inputs(heap_date, db)
        logger.info(f"Number of prospect-eligible candidates: {len(prospects)}")

        prospect_values = project_prospects(prospects)
        logger.info(
            f"Generated {len(prospect_values)} prospect values (after filtering None)"
        )

        counts["projections_inserted"] += insert_prospect_values(prospect_values, db)
    else:
        counts["players_updated"] = run_migration_long(heap_date, db)
        counts["players_updated"] += update_player_age(db=db, heap_date=heap_date)
        compute_league_baselines(db)
        compute_market_constants(db)

    mark_heap_processed(db, heap_date, short_heap)
    return counts


def mark_heap_processed(db, heap_date, short_heap):
    """Record that this heap's migration/projection work has fully committed,
    so check_new_heaps() won't return it again."""
    with db.cursor() as cursor:
        cursor.execute(
            "INSERT INTO processed_heaps (year, month, is_short, processed_at) "
            "VALUES (%s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE is_short = VALUES(is_short), "
            "processed_at = VALUES(processed_at)",
            (heap_date[1], heap_date[2], short_heap, datetime.now()),
        )
    db.commit()


def update_player_age(db, heap_date):
    """
    Update the 'age' field of all players based on their birth_date and the heap_date.

    Args:
        db: MariaDB connection object
        heap_date: tuple or list like (year, month, day) or (something, year, month)
    """
    current_date = date.fromisoformat(f"{heap_date[1]}-01-01")
    rows_updated = 0

    with db.cursor() as cursor:
        cursor.execute("SELECT player_id, birth_date FROM players")
        rows = cursor.fetchall()

        batch = []
        for row in rows:
            player_id = row.get("player_id")
            birth_date = row.get("birth_date")
            if not player_id or not birth_date:
                continue

            logger.debug("current_date=%s birth_date=%s", current_date, birth_date)
            delta = current_date - birth_date
            age = round(delta.days / 365.25)
            batch.append((age, player_id))

            if len(batch) >= 500:
                cursor.executemany(
                    "UPDATE players SET age = %s WHERE player_id = %s", batch
                )
                rows_updated += cursor.rowcount
                db.commit()
                batch.clear()

        if batch:
            cursor.executemany(
                "UPDATE players SET age = %s WHERE player_id = %s", batch
            )
            rows_updated += cursor.rowcount
            db.commit()
    logger.info("Player ages updated")
    return rows_updated


def extract_heap_date_from_path(heap_path):
    # Expects "{DUMP_PATH}/dump_yyyy_mm/mysql"
    return Path(heap_path).parts[-2].split("_")


def _run_sql_script(script_path, db, heap_date=None, fetch=False):
    """Run every ';'-split statement in a .sql resource against db, inside
    one cursor/transaction. Rolls back and re-raises on any exception;
    commits on success.

    Args:
        script_path: path passed to current_app.open_resource(), relative
            to the app package (e.g. "db/sql_scripts/migration/x.sql").
        db: MariaDB connection object.
        heap_date: if given, injected via inject_heap_date() before running.
        fetch: if True, return the last statement's result rows as a list
            of dicts (for a script whose final statement is a SELECT)
            instead of a row count.

    Returns:
        [dict, ...] if fetch=True, else the total rows affected (summed
        cursor.rowcount) across every executed statement.
    """
    with current_app.open_resource(script_path, "r") as f:
        sql_script = f.read()
    if heap_date is not None:
        sql_script = inject_heap_date(sql_script, heap_date)

    rows_affected = 0
    with db.cursor() as cursor:
        try:
            for statement in sql_script.strip().split(";"):
                statement = statement.strip()
                if statement:
                    cursor.execute(statement)
                    if cursor.rowcount > 0:
                        rows_affected += cursor.rowcount
        except Exception as e:
            db.rollback()
            logger.error(f"Migration failed: {e}")
            raise
        else:
            db.commit()

        if fetch:
            return [dict(row) for row in cursor.fetchall()]
    return rows_affected


def run_migration_short(heap_date, db):
    script_path = os.path.join("db", "sql_scripts", "migration", "migration_short.sql")
    return _run_sql_script(script_path, db, heap_date=heap_date)


def run_migration_long(heap_date, db):
    script_path = os.path.join("db", "sql_scripts", "migration", "migration_long.sql")
    return _run_sql_script(script_path, db)


def fetch_projection_inputs(heap_date, db):
    query_path = os.path.join(
        "db", "sql_scripts", "migration", "get_projection_inputs.sql"
    )
    return _run_sql_script(query_path, db, heap_date=heap_date, fetch=True)


def fetch_pitcher_projection_inputs(heap_date, db):
    query_path = os.path.join(
        "db", "sql_scripts", "migration", "get_pitcher_projection_inputs.sql"
    )
    return _run_sql_script(query_path, db, heap_date=heap_date, fetch=True)


def fetch_prospect_value_inputs(heap_date, db):
    query_path = os.path.join(
        "db", "sql_scripts", "migration", "get_prospect_value_inputs.sql"
    )
    return _run_sql_script(query_path, db, heap_date=heap_date, fetch=True)


def fetch_batting_league_baseline_pool(db):
    query_path = os.path.join(
        "db", "sql_scripts", "migration", "get_batting_league_baseline_pool.sql"
    )
    rows = _run_sql_script(query_path, db, fetch=True)
    return rows[0] if rows else {}


def fetch_pitching_league_baseline_pool(db):
    query_path = os.path.join(
        "db", "sql_scripts", "migration", "get_pitching_league_baseline_pool.sql"
    )
    rows = _run_sql_script(query_path, db, fetch=True)
    return rows[0] if rows else {}


def compute_league_baselines(db):
    """Ticket 0066: recalibrate this save's own lg_woba/lg_pwoba/
    ra9_baseline from a rolling 3-season pooled window of real
    players_career_batting_stats/players_career_pitching_stats totals
    (league_id = 203, PA/outs-qualifying rows only -- see
    get_batting_league_baseline_pool.sql/get_pitching_league_baseline_
    pool.sql), and persist a new league_baselines row. Called once per
    long/yearly heap -- short heaps just reuse whatever the most recent
    long heap computed, via get_projection_inputs.sql's/
    get_pitcher_projection_inputs.sql's LEFT JOIN onto the latest row.

    Uses the same FACTOR_BB/FACTOR_1B/FACTOR_2B/FACTOR_3B/FACTOR_HR
    weights BatterProjection/PitcherProjection already compute their own
    projected wOBA with (imported, not restated), so the real-stat
    baseline and the projected value it's compared against are on the
    same scale. Falls back to the existing hardcoded real-MLB constants
    for whichever side has no qualifying pool yet (e.g. before enough
    real season history has accumulated) instead of persisting a NULL/
    divide-by-zero.
    """
    batting = fetch_batting_league_baseline_pool(db)
    pitching = fetch_pitching_league_baseline_pool(db)

    # MariaDB's SUM() over an exact numeric type (SMALLINT here) returns
    # DECIMAL, which PyMySQL maps to decimal.Decimal -- arithmetic mixing
    # that with the plain Python floats FACTOR_BB/etc. already are raises
    # "unsupported operand type(s) for *: 'decimal.Decimal' and 'float'".
    # Coerce once here rather than at every use site below.
    for key in ("pa", "bb", "hp", "h", "d", "t", "hr"):
        if batting.get(key) is not None:
            batting[key] = float(batting[key])
    for key in ("bf", "bb", "hp", "ha", "hra", "ra", "outs"):
        if pitching.get(key) is not None:
            pitching[key] = float(pitching[key])

    if batting.get("pa"):
        lg_woba = (
            (batting["bb"] + batting["hp"]) * batter_projection.FACTOR_BB
            + (batting["h"] - batting["d"] - batting["t"] - batting["hr"]) * batter_projection.FACTOR_1B
            + batting["d"] * batter_projection.FACTOR_2B
            + batting["t"] * batter_projection.FACTOR_3B
            + batting["hr"] * batter_projection.FACTOR_HR
        ) / batting["pa"]
    else:
        logger.warning(
            "No qualifying batting rows for league baseline recalibration; "
            "falling back to LG_WOBA=%.4f", batter_projection.LG_WOBA
        )
        lg_woba = batter_projection.LG_WOBA

    if pitching.get("bf") and pitching.get("outs"):
        lg_pwoba = (
            (pitching["bb"] + pitching["hp"]) * pitcher_projection.FACTOR_BB
            + (pitching["ha"] - pitching["hra"]) * 1.0
            + pitching["hra"] * pitcher_projection.FACTOR_HR
        ) / pitching["bf"]
        ra9_baseline = pitching["ra"] / (pitching["outs"] / 3) * 9
    else:
        logger.warning(
            "No qualifying pitching rows for league baseline recalibration; "
            "falling back to LG_PWOBA=%.4f RA9_BASELINE=%.3f",
            pitcher_projection.LG_PWOBA, pitcher_projection.RA9_BASELINE,
        )
        lg_pwoba = pitcher_projection.LG_PWOBA
        ra9_baseline = pitcher_projection.RA9_BASELINE

    window_start_year = batting.get("window_start_year") or pitching.get("window_start_year")
    window_end_year = batting.get("window_end_year") or pitching.get("window_end_year")

    with db.cursor() as cursor:
        cursor.execute(
            "INSERT INTO league_baselines "
            "(computed_at, window_start_year, window_end_year, lg_woba, "
            "lg_pwoba, ra9_baseline, batting_pa_sample, pitching_bf_sample) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (
                datetime.now(),
                window_start_year,
                window_end_year,
                lg_woba,
                lg_pwoba,
                ra9_baseline,
                batting.get("pa"),
                pitching.get("bf"),
            ),
        )
    db.commit()

    logger.info(
        "Recalibrated league baselines (years %s-%s): lg_woba=%.4f "
        "lg_pwoba=%.4f ra9_baseline=%.3f",
        window_start_year, window_end_year, lg_woba, lg_pwoba, ra9_baseline,
    )


def fetch_market_constants_inputs(db):
    query_path = os.path.join(
        "db", "sql_scripts", "migration", "get_market_constants_inputs.sql"
    )
    return _run_sql_script(query_path, db, fetch=True)


def compute_market_constants(db):
    """Ticket 0066: re-derive contract_value.py's WAR_DOLLAR_VALUE/
    RECOMMENDATION_EXTEND_THRESHOLD from this save's own real
    players_contract data each long heap -- automates tickets 0056's/
    0058's original one-time manual methodology (median implied $/WAR
    across market-rate contracts; p70 of average-surplus-per-year across a
    curated cohort) instead of leaving those constants as a stale snapshot
    once compute_league_baselines' recalibration shifts the WAR scale.
    Called once per long/yearly heap, right after compute_league_baselines.

    Deliberately reads whatever players_run_value/players_pitching_run_
    value already contains at that point -- last short heap's projections,
    computed under the *previous* lg_woba/lg_pwoba/ra9_baseline, not this
    heap's brand new one (those tables only refresh on the next short
    heap). A one-heap lag, same as any annual re-derivation would have;
    not worth blocking on a projection re-run that hasn't happened yet.

    Two-way players are skipped in both cohorts (batting_war and
    pitching_war both non-null), matching ticket 0056's original
    precedent -- not app/api/players.py's later TWP-sum deviation, which
    was explicitly scoped to that one endpoint.
    """
    rows = fetch_market_constants_inputs(db)

    dollar_war_ratios = []
    threshold_candidates = []
    for row in rows:
        batting_war = row["batting_war"]
        pitching_war = row["pitching_war"]
        if batting_war is not None and pitching_war is not None:
            continue
        war = batting_war if batting_war is not None else pitching_war
        if war is None or row["age"] is None or row["current_year"] is None:
            continue

        salaries = [row[f"salary{i}"] for i in range(15)]
        current_year_salary = salaries[row["current_year"]]

        if current_year_salary is not None and current_year_salary >= 15_000_000 and war >= 1.5:
            dollar_war_ratios.append(current_year_salary / war)

        if salaries[0] is not None and salaries[0] > 1_000_000:
            threshold_candidates.append({
                "base_war": war,
                "current_age": row["age"],
                "mlb_service_years": row["mlb_service_years"] or 0,
                "contract": {
                    "current_year": row["current_year"],
                    "years": row["years"],
                    **{f"salary{i}": salaries[i] for i in range(15)},
                },
                "prone_overall": row["prone_overall"],
                "is_pitcher": pitching_war is not None,
                "pitching_role": row["pitching_role"],
            })

    if dollar_war_ratios:
        war_dollar_value = statistics.median(dollar_war_ratios)
    else:
        logger.warning(
            "No qualifying market-rate contracts for WAR_DOLLAR_VALUE "
            "recalibration; falling back to %s", contract_value.WAR_DOLLAR_VALUE
        )
        war_dollar_value = contract_value.WAR_DOLLAR_VALUE

    surplus_per_year = []
    for candidate in threshold_candidates:
        result = contract_value.calculate_surplus_value(
            **candidate, war_dollar_value=war_dollar_value,
        )
        if result is not None and result["years"]:
            surplus_per_year.append(result["total_surplus"] / len(result["years"]))

    if len(surplus_per_year) >= 2:
        # p70, matching ticket 0058's original derivation -- quantiles(n=10)
        # returns the 10th/20th/.../90th percentile cutpoints, index 6 is
        # the 70th (100 * 7 / 10).
        recommendation_extend_threshold = statistics.quantiles(
            surplus_per_year, n=10, method="inclusive"
        )[6]
    else:
        logger.warning(
            "No qualifying contracts for RECOMMENDATION_EXTEND_THRESHOLD "
            "recalibration; falling back to %s",
            contract_value.RECOMMENDATION_EXTEND_THRESHOLD,
        )
        recommendation_extend_threshold = contract_value.RECOMMENDATION_EXTEND_THRESHOLD

    with db.cursor() as cursor:
        cursor.execute(
            "INSERT INTO market_baselines "
            "(computed_at, war_dollar_value, war_dollar_value_sample, "
            "recommendation_extend_threshold, threshold_cohort_sample) "
            "VALUES (%s, %s, %s, %s, %s)",
            (
                datetime.now(),
                war_dollar_value,
                len(dollar_war_ratios),
                recommendation_extend_threshold,
                len(surplus_per_year),
            ),
        )
    db.commit()

    logger.info(
        "Recalibrated market constants: war_dollar_value=%.0f (n=%d) "
        "recommendation_extend_threshold=%.0f (n=%d)",
        war_dollar_value, len(dollar_war_ratios),
        recommendation_extend_threshold, len(surplus_per_year),
    )


def project_players(players):
    with Pool(processes=cpu_count()) as pool:
        results = list(
            tqdm(
                pool.imap_unordered(process_player, players),
                total=len(players),
                desc="Projecting players",
            )
        )
    return [r for r in results if r is not None]


def project_pitchers(pitchers):
    with Pool(processes=cpu_count()) as pool:
        results = list(
            tqdm(
                pool.imap_unordered(process_pitcher, pitchers),
                total=len(pitchers),
                desc="Projecting pitchers",
            )
        )
    return [r for r in results if r is not None]


def project_prospects(prospects):
    with Pool(processes=cpu_count()) as pool:
        results = list(
            tqdm(
                pool.imap_unordered(process_prospect, prospects),
                total=len(prospects),
                desc="Projecting prospect values",
            )
        )
    return [r for r in results if r is not None]


def insert_prospect_values(prospect_values, db, batch_size=1000):
    batches = {key: [] for key in ("prospect_value",)}
    rows_inserted = 0
    for i in range(0, len(prospect_values), batch_size):
        chunk = prospect_values[i : i + batch_size]
        batches, chunk_rows = update_prospect_value_batches(
            batches, projections=chunk, inject=True, db=db
        )
        rows_inserted += chunk_rows
    _, final_rows = update_prospect_value_batches(batches, db=db, final=True)
    rows_inserted += final_rows
    return rows_inserted


def insert_projections(projections, db, batch_size=1000):
    batches = {
        key: []
        for key in (
            "offense",
            "basepath",
            "defense",
            "value",
            "offense_talent",
            "defense_talent",
            "value_talent",
        )
    }
    rows_inserted = 0
    for i in range(0, len(projections), batch_size):
        chunk = projections[i : i + batch_size]
        batches, chunk_rows = update_projection_batches(
            batches, projections=chunk, inject=True, db=db
        )
        rows_inserted += chunk_rows
    _, final_rows = update_projection_batches(batches, db=db, final=True)
    rows_inserted += final_rows
    return rows_inserted


def insert_pitcher_projections(projections, db, batch_size=1000):
    batches = {
        key: []
        for key in (
            "pitching",
            "pitching_value",
            "pitching_talent",
            "pitching_value_talent",
        )
    }
    rows_inserted = 0
    for i in range(0, len(projections), batch_size):
        chunk = projections[i : i + batch_size]
        batches, chunk_rows = update_pitching_projection_batches(
            batches, projections=chunk, inject=True, db=db
        )
        rows_inserted += chunk_rows
    _, final_rows = update_pitching_projection_batches(batches, db=db, final=True)
    rows_inserted += final_rows
    return rows_inserted
