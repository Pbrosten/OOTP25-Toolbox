import os
import statistics
import pytest

from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.db import update as update_module
from app.player_projection import contract_value

def test_extract_heap_date_from_path():
    path = "/some/path/dump_2023_08/mysql"
    assert update_module.extract_heap_date_from_path(path) == ['dump', '2023', '08']


def test_run_migration_short_executes_statements_and_returns_rows_affected(app):
    sql_content = "INSERT INTO a VALUES (1); INSERT INTO b VALUES (2);"
    mock_file = MagicMock()
    mock_file.read.return_value = sql_content

    mock_cursor = MagicMock()
    mock_cursor.rowcount = 3
    db = MagicMock()
    db.cursor.return_value.__enter__.return_value = mock_cursor

    with app.app_context():
        with patch("app.db.update.current_app.open_resource") as mock_open:
            mock_open.return_value.__enter__.return_value = mock_file
            rows_affected = update_module.run_migration_short(["dump", "2023", "08"], db)

    expected_path = os.path.join("db", "sql_scripts", "migration", "migration_short.sql")
    mock_open.assert_called_once_with(expected_path, "r")
    executed = [c.args[0] for c in mock_cursor.execute.call_args_list]
    assert executed == ["INSERT INTO a VALUES (1)", "INSERT INTO b VALUES (2)"]
    db.commit.assert_called_once()
    db.rollback.assert_not_called()
    assert rows_affected == 6  # rowcount=3, summed across 2 statements


def test_run_migration_short_rolls_back_and_reraises_on_error(app):
    sql_content = "INSERT INTO a VALUES (1);"
    mock_file = MagicMock()
    mock_file.read.return_value = sql_content

    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = Exception("boom")
    db = MagicMock()
    db.cursor.return_value.__enter__.return_value = mock_cursor

    with app.app_context():
        with patch("app.db.update.current_app.open_resource") as mock_open:
            mock_open.return_value.__enter__.return_value = mock_file
            with pytest.raises(Exception, match="boom"):
                update_module.run_migration_short(["dump", "2023", "08"], db)

    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_run_migration_long_executes_statements_and_returns_rows_affected(app):
    sql_content = "INSERT INTO a VALUES (1); INSERT INTO b VALUES (2);"
    mock_file = MagicMock()
    mock_file.read.return_value = sql_content

    mock_cursor = MagicMock()
    mock_cursor.rowcount = 2
    db = MagicMock()
    db.cursor.return_value.__enter__.return_value = mock_cursor

    with app.app_context():
        with patch("app.db.update.current_app.open_resource") as mock_open:
            mock_open.return_value.__enter__.return_value = mock_file
            rows_affected = update_module.run_migration_long(["dump", "2023", "08"], db)

    expected_path = os.path.join("db", "sql_scripts", "migration", "migration_long.sql")
    mock_open.assert_called_once_with(expected_path, "r")
    assert mock_cursor.execute.call_count == 2
    db.commit.assert_called_once()
    assert rows_affected == 4  # rowcount=2, summed across 2 statements


def test_run_migration_long_rolls_back_and_reraises_on_error(app):
    sql_content = "INSERT INTO a VALUES (1);"
    mock_file = MagicMock()
    mock_file.read.return_value = sql_content

    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = Exception("boom")
    db = MagicMock()
    db.cursor.return_value.__enter__.return_value = mock_cursor

    with app.app_context():
        with patch("app.db.update.current_app.open_resource") as mock_open:
            mock_open.return_value.__enter__.return_value = mock_file
            with pytest.raises(Exception, match="boom"):
                update_module.run_migration_long(["dump", "2023", "08"], db)

    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_fetch_projection_inputs_returns_rows_as_dicts(app):
    sql_content = "SELECT * FROM players;"
    mock_file = MagicMock()
    mock_file.read.return_value = sql_content

    mock_cursor = MagicMock()
    mock_cursor.rowcount = 2
    mock_cursor.fetchall.return_value = [{"id": 1}, {"id": 2}]
    db = MagicMock()
    db.cursor.return_value.__enter__.return_value = mock_cursor

    with app.app_context():
        with patch("app.db.update.current_app.open_resource") as mock_open:
            mock_open.return_value.__enter__.return_value = mock_file
            result = update_module.fetch_projection_inputs(["dump", "2023", "08"], db)

    expected_path = os.path.join("db", "sql_scripts", "migration", "get_projection_inputs.sql")
    mock_open.assert_called_once_with(expected_path, "r")
    mock_cursor.execute.assert_called_once_with("SELECT * FROM players")
    db.commit.assert_called_once()
    assert result == [{"id": 1}, {"id": 2}]


def test_fetch_prospect_value_inputs_returns_rows_as_dicts(app):
    sql_content = "SELECT * FROM players;"
    mock_file = MagicMock()
    mock_file.read.return_value = sql_content

    mock_cursor = MagicMock()
    mock_cursor.rowcount = 2
    mock_cursor.fetchall.return_value = [{"id": 1}, {"id": 2}]
    db = MagicMock()
    db.cursor.return_value.__enter__.return_value = mock_cursor

    with app.app_context():
        with patch("app.db.update.current_app.open_resource") as mock_open:
            mock_open.return_value.__enter__.return_value = mock_file
            result = update_module.fetch_prospect_value_inputs(["dump", "2023", "08"], db)

    expected_path = os.path.join(
        "db", "sql_scripts", "migration", "get_prospect_value_inputs.sql"
    )
    mock_open.assert_called_once_with(expected_path, "r")
    mock_cursor.execute.assert_called_once_with("SELECT * FROM players")
    db.commit.assert_called_once()
    assert result == [{"id": 1}, {"id": 2}]


@patch("app.db.update.process_player", side_effect=lambda p: {"id": p["id"], "value": 42})
@patch("app.db.update.cpu_count", return_value=1)
@patch("app.db.update.Pool")
def test_project_players(mock_pool_cls, mock_cpu, mock_proc):
    mock_pool = mock_pool_cls.return_value.__enter__.return_value
    mock_pool.imap_unordered.return_value = ({"id": i, "value": 42} for i in range(10))

    players = [{"id": i} for i in range(10)]
    results = update_module.project_players(players)

    assert len(results) == 10
    assert all("value" in r for r in results)


@patch("app.db.update.update_projection_batches")
def test_insert_projections(mock_update):
    # update_projection_batches returns (batches_or_None, rows_written) when
    # inject/final -- see docs/tickets/0016.
    mock_update.return_value = (
        {"offense": [], "basepath": [], "defense": [], "value": []},
        10,
    )
    db = MagicMock()
    projections = [{"id": i} for i in range(2500)]
    rows_inserted = update_module.insert_projections(projections, db, batch_size=1000)

    # 3 calls: 2 for chunks, 1 final
    assert mock_update.call_count == 4
    # First call with projections
    assert mock_update.call_args_list[0][1]['inject'] is True
    # Last call with final=True
    assert mock_update.call_args_list[-1][1]['final'] is True
    assert rows_inserted == 40


@patch("app.db.update.process_prospect", side_effect=lambda p: {"id": p["id"], "value": 42})
@patch("app.db.update.cpu_count", return_value=1)
@patch("app.db.update.Pool")
def test_project_prospects(mock_pool_cls, mock_cpu, mock_proc):
    mock_pool = mock_pool_cls.return_value.__enter__.return_value
    mock_pool.imap_unordered.return_value = ({"id": i, "value": 42} for i in range(10))

    prospects = [{"id": i} for i in range(10)]
    results = update_module.project_prospects(prospects)

    assert len(results) == 10
    assert all("value" in r for r in results)


@patch("app.db.update.update_prospect_value_batches")
def test_insert_prospect_values(mock_update):
    mock_update.return_value = ({"prospect_value": []}, 10)
    db = MagicMock()
    prospect_values = [{"id": i} for i in range(2500)]
    rows_inserted = update_module.insert_prospect_values(prospect_values, db, batch_size=1000)

    # 4 calls: 3 for chunks (2500 / 1000), 1 final
    assert mock_update.call_count == 4
    assert mock_update.call_args_list[0][1]['inject'] is True
    assert mock_update.call_args_list[-1][1]['final'] is True
    assert rows_inserted == 40


@patch("app.db.update.mark_heap_processed")
@patch("app.db.update.insert_prospect_values", return_value=5)
@patch("app.db.update.project_prospects", return_value=[{"id": 11}])
@patch("app.db.update.fetch_prospect_value_inputs", return_value=[{"id": 11}])
@patch("app.db.update.insert_pitcher_projections", return_value=3)
@patch("app.db.update.project_pitchers", return_value=[{"id": 9}])
@patch("app.db.update.fetch_pitcher_projection_inputs", return_value=[{"id": 9}])
@patch("app.db.update.insert_projections", return_value=7)
@patch("app.db.update.project_players", return_value=[{"id": 1}, {"id": 2}])
@patch("app.db.update.fetch_projection_inputs", return_value=[{"id": 1}, {"id": 2}])
@patch("app.db.update.run_migration_short", return_value=42)
@patch("app.db.update.load_sql_dumps_into_staging")
@patch("app.db.update.connect_staging_db")
@patch("app.db.update.extract_heap_date_from_path", return_value=["dump", "2023", "08"])
def test_process_single_heap_short(
    mock_extract, mock_connect, mock_load, mock_migration_short,
    mock_fetch, mock_project, mock_insert,
    mock_fetch_pitchers, mock_project_pitchers, mock_insert_pitchers,
    mock_fetch_prospects, mock_project_prospects, mock_insert_prospects,
    mock_mark_processed,
):
    mock_staging_db = MagicMock()
    mock_connect.return_value = mock_staging_db
    db = MagicMock()

    counts = update_module.process_single_heap(
        "/dummy/heap_path", 1, 10, db, short_heap=True
    )

    mock_connect.assert_called_once()
    mock_load.assert_called_once_with(mock_staging_db, "/dummy/heap_path")
    mock_staging_db.close.assert_called_once()

    mock_migration_short.assert_called_once_with(["dump", "2023", "08"], db)
    mock_fetch.assert_called_once_with(["dump", "2023", "08"], db)
    mock_project.assert_called_once_with([{"id": 1}, {"id": 2}])
    mock_insert.assert_called_once_with([{"id": 1}, {"id": 2}], db)

    mock_fetch_pitchers.assert_called_once_with(["dump", "2023", "08"], db)
    mock_project_pitchers.assert_called_once_with([{"id": 9}])
    mock_insert_pitchers.assert_called_once_with([{"id": 9}], db)

    mock_fetch_prospects.assert_called_once_with(["dump", "2023", "08"], db)
    mock_project_prospects.assert_called_once_with([{"id": 11}])
    mock_insert_prospects.assert_called_once_with([{"id": 11}], db)

    mock_mark_processed.assert_called_once_with(db, ["dump", "2023", "08"], True)

    assert counts == {"ratings_inserted": 42, "players_updated": 0, "projections_inserted": 15}


@patch("app.db.update.compute_market_constants")
@patch("app.db.update.compute_league_baselines")
@patch("app.db.update.mark_heap_processed")
@patch("app.db.update.update_player_age", return_value=5)
@patch("app.db.update.run_migration_long", return_value=10)
@patch("app.db.update.load_sql_dumps_into_staging")
@patch("app.db.update.connect_staging_db")
@patch("app.db.update.extract_heap_date_from_path", return_value=["dump", "2023", "08"])
def test_process_single_heap_long(
    mock_extract, mock_connect, mock_load, mock_migration_long,
    mock_update_age, mock_mark_processed, mock_compute_baselines,
    mock_compute_market_constants,
):
    mock_staging_db = MagicMock()
    mock_connect.return_value = mock_staging_db
    db = MagicMock()

    counts = update_module.process_single_heap(
        "/dummy/heap_path", 1, 10, db, short_heap=False
    )

    mock_connect.assert_called_once()
    mock_load.assert_called_once_with(mock_staging_db, "/dummy/heap_path")
    mock_staging_db.close.assert_called_once()

    mock_migration_long.assert_called_once_with(["dump", "2023", "08"], db)
    mock_update_age.assert_called_once_with(db=db, heap_date=["dump", "2023", "08"])
    # Ticket 0066: recalibrate this save's league baselines and market
    # constants once per long heap, after players/ages are up to date.
    mock_compute_baselines.assert_called_once_with(db)
    mock_compute_market_constants.assert_called_once_with(db)
    mock_mark_processed.assert_called_once_with(db, ["dump", "2023", "08"], False)

    assert counts == {"ratings_inserted": 0, "players_updated": 15, "projections_inserted": 0}


@patch("app.db.update.fetch_pitching_league_baseline_pool")
@patch("app.db.update.fetch_batting_league_baseline_pool")
def test_compute_league_baselines_pools_qualifying_seasons(mock_fetch_batting, mock_fetch_pitching):
    # Ticket 0066: pooled real stats -> lg_woba/lg_pwoba/ra9_baseline via
    # the same FACTOR_* weights BatterProjection/PitcherProjection use.
    #
    # Decimal, not int: MariaDB's SUM() over an exact numeric type
    # (SMALLINT, as these source columns are) returns DECIMAL, which
    # PyMySQL maps to decimal.Decimal -- a real regression (reported
    # against a live update-db run) mixed that with the plain Python
    # floats FACTOR_BB/etc. already are, raising "unsupported operand
    # type(s) for *: 'decimal.Decimal' and 'float'". Using plain ints here
    # wouldn't have caught it.
    mock_fetch_batting.return_value = {
        "window_start_year": 2024, "window_end_year": 2026,
        "pa": Decimal("1000"), "bb": Decimal("100"), "hp": Decimal("10"),
        "h": Decimal("250"), "d": Decimal("40"), "t": Decimal("5"), "hr": Decimal("25"),
    }
    mock_fetch_pitching.return_value = {
        "window_start_year": 2024, "window_end_year": 2026,
        "bf": Decimal("900"), "bb": Decimal("80"), "hp": Decimal("8"),
        "ha": Decimal("220"), "hra": Decimal("22"), "ra": Decimal("400"), "outs": Decimal("2400"),
    }
    mock_cursor = MagicMock()
    db = MagicMock()
    db.cursor.return_value.__enter__.return_value = mock_cursor

    update_module.compute_league_baselines(db)

    mock_cursor.execute.assert_called_once()
    sql, params = mock_cursor.execute.call_args[0]
    assert "INSERT INTO league_baselines" in sql
    (
        _computed_at, window_start_year, window_end_year,
        lg_woba, lg_pwoba, ra9_baseline, batting_pa_sample, pitching_bf_sample,
    ) = params

    assert window_start_year == 2024
    assert window_end_year == 2026
    assert batting_pa_sample == 1000
    assert pitching_bf_sample == 900
    # singles = h - d - t - hr = 250 - 40 - 5 - 25 = 180
    expected_lg_woba = (
        (100 + 10) * 0.7 + 180 * 0.9 + 40 * 1.25 + 5 * 1.6 + 25 * 2
    ) / 1000
    assert lg_woba == pytest.approx(expected_lg_woba)
    expected_lg_pwoba = ((80 + 8) * 0.7 + (220 - 22) * 1.0 + 22 * 2.0) / 900
    assert lg_pwoba == pytest.approx(expected_lg_pwoba)
    expected_ra9 = 400 / (2400 / 3) * 9
    assert ra9_baseline == pytest.approx(expected_ra9)
    db.commit.assert_called_once()


@patch("app.db.update.fetch_pitching_league_baseline_pool", return_value={})
@patch("app.db.update.fetch_batting_league_baseline_pool", return_value={})
def test_compute_league_baselines_falls_back_when_no_qualifying_rows(mock_fetch_batting, mock_fetch_pitching):
    # No real history yet (e.g. before the save's first long heap) ->
    # fall back to BatterProjection/PitcherProjection's hardcoded
    # real-MLB constants rather than persisting a NULL/divide-by-zero.
    from app.player_projection import batter as batter_projection
    from app.player_projection import pitcher as pitcher_projection

    mock_cursor = MagicMock()
    db = MagicMock()
    db.cursor.return_value.__enter__.return_value = mock_cursor

    update_module.compute_league_baselines(db)

    _sql, params = mock_cursor.execute.call_args[0]
    (
        _computed_at, window_start_year, window_end_year,
        lg_woba, lg_pwoba, ra9_baseline, batting_pa_sample, pitching_bf_sample,
    ) = params

    assert window_start_year is None
    assert window_end_year is None
    assert batting_pa_sample is None
    assert pitching_bf_sample is None
    assert lg_woba == batter_projection.LG_WOBA
    assert lg_pwoba == pitcher_projection.LG_PWOBA
    assert ra9_baseline == pitcher_projection.RA9_BASELINE


def _market_row(batting_war, pitching_war, age, current_year, years, salary0, current_salary):
    salaries = {f"salary{i}": 0 for i in range(15)}
    salaries["salary0"] = salary0
    salaries[f"salary{current_year}"] = current_salary
    return {
        "age": age, "prone_overall": 100,
        "batting_war": batting_war, "pitching_war": pitching_war,
        "pitching_role": None, "mlb_service_years": 4,
        "current_year": current_year, "years": years,
        **salaries,
    }


@patch("app.db.update.contract_value.calculate_surplus_value")
@patch("app.db.update.fetch_market_constants_inputs")
def test_compute_market_constants_pools_qualifying_cohorts(mock_fetch, mock_calc_surplus):
    # Ticket 0066: re-derive WAR_DOLLAR_VALUE (median $/WAR, salary >= $15M
    # and WAR >= 1.5) and RECOMMENDATION_EXTEND_THRESHOLD (p70 of
    # avg-surplus-per-year, salary0 > $1M) from real contract data.
    rows = [
        _market_row(3.0, None, 28, 0, 3, 16_000_000, 16_000_000),  # both cohorts
        _market_row(1.0, None, 30, 0, 2, 5_000_000, 5_000_000),    # threshold cohort only (WAR < 1.5)
        _market_row(None, 2.0, 25, 1, 4, 1_500_000, 20_000_000),   # both cohorts
        _market_row(2.0, 2.0, 26, 0, 1, 20_000_000, 20_000_000),   # two-way -> skipped entirely
    ]
    mock_fetch.return_value = rows
    mock_calc_surplus.side_effect = [
        {"years": [1, 2, 3], "total_surplus": 3_000_000},      # 1,000,000/yr
        {"years": [1, 2], "total_surplus": 20_000_000},        # 10,000,000/yr
        {"years": [1, 2, 3, 4], "total_surplus": 40_000_000},  # 10,000,000/yr
    ]

    db = MagicMock()
    mock_cursor = MagicMock()
    db.cursor.return_value.__enter__.return_value = mock_cursor

    update_module.compute_market_constants(db)

    mock_cursor.execute.assert_called_once()
    _sql, params = mock_cursor.execute.call_args[0]
    (
        _computed_at, war_dollar_value, war_dollar_value_sample,
        recommendation_extend_threshold, threshold_cohort_sample,
    ) = params

    expected_ratios = [16_000_000 / 3.0, 20_000_000 / 2.0]
    assert war_dollar_value_sample == 2
    assert war_dollar_value == pytest.approx(statistics.median(expected_ratios))

    assert threshold_cohort_sample == 3
    assert mock_calc_surplus.call_count == 3
    for call in mock_calc_surplus.call_args_list:
        assert call.kwargs["war_dollar_value"] == pytest.approx(war_dollar_value)

    expected_surplus_per_year = [1_000_000, 10_000_000, 10_000_000]
    expected_threshold = statistics.quantiles(
        expected_surplus_per_year, n=10, method="inclusive"
    )[6]
    assert recommendation_extend_threshold == pytest.approx(expected_threshold)

    db.commit.assert_called_once()


@patch("app.db.update.contract_value.calculate_surplus_value")
@patch("app.db.update.fetch_market_constants_inputs", return_value=[])
def test_compute_market_constants_falls_back_when_no_qualifying_rows(mock_fetch, mock_calc_surplus):
    db = MagicMock()
    mock_cursor = MagicMock()
    db.cursor.return_value.__enter__.return_value = mock_cursor

    update_module.compute_market_constants(db)

    mock_calc_surplus.assert_not_called()
    _sql, params = mock_cursor.execute.call_args[0]
    (
        _computed_at, war_dollar_value, war_dollar_value_sample,
        recommendation_extend_threshold, threshold_cohort_sample,
    ) = params

    assert war_dollar_value_sample == 0
    assert threshold_cohort_sample == 0
    assert war_dollar_value == contract_value.WAR_DOLLAR_VALUE
    assert recommendation_extend_threshold == contract_value.RECOMMENDATION_EXTEND_THRESHOLD
