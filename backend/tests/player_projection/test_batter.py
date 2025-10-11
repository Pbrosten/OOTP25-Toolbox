import pytest
from app.player_projection.batter import BatterProjection

def test_initialization(mock_ratings_data):
    player = BatterProjection(mock_ratings_data)
    assert player.player_id == "test_player"
    assert player.position == "SS"
    assert player.injury == "Normal"
    assert player.babip == 50
    assert isinstance(player.offensive_stats, dict)

def test_age_calculation(mock_ratings_data):
    player = BatterProjection(mock_ratings_data)
    age = player.calc_age()
    assert age == 25  # as of 2025-09-01 from 2000-01-01

def test_lookup_bat(mock_ratings_data):
    player = BatterProjection(mock_ratings_data)
    result = player.lookup_bat(50, 'HR')
    assert isinstance(result, float)

def test_lookup_def(mock_ratings_data):
    player = BatterProjection(mock_ratings_data)
    result = player.lookup_def(50, 'SS')
    assert isinstance(result, float)

def test_lookup_injury_category(mock_ratings_data):
    player = BatterProjection(mock_ratings_data)
    result = player.lookup_inj('Batter')
    assert isinstance(result, float)

def test_best_position_calc(mock_ratings_data):
    player = BatterProjection(mock_ratings_data)
    player.calc_defensive_runs_saved()
    best_pos, value = player.calc_best_position()
    assert best_pos in player.defensive_values

def test_calc_defensive_runs_saved(mock_ratings_data):
    player = BatterProjection(mock_ratings_data)
    player.calc_defensive_runs_saved()
    for val in player.defensive_values.values():
        assert val is not None

def test_calc_offensive_stats_base(mock_ratings_data):
    player = BatterProjection(mock_ratings_data)
    player.calc_offensive_stats_base()
    assert player.offensive_stats['_1B'] is not None
    assert player.offensive_stats['HR'] is not None
    assert player.offensive_stats['PA'] is not None

def test_calc_offensive_stats(mock_ratings_data):
    player = BatterProjection(mock_ratings_data)
    player.calc_defensive_runs_saved()
    player.calc_offensive_stats()
    assert player.offensive_stats['PA'] > 0

def test_calc_offensive_rates(mock_ratings_data):
    player = BatterProjection(mock_ratings_data)
    player.calc_defensive_runs_saved()
    player.calc_offensive_stats()
    player.calc_offensive_rates()
    assert 0 <= player.offensive_stats['AVG'] <= 1
    assert 0 <= player.offensive_stats['OBP'] <= 1
    assert 0 <= player.offensive_stats['SLG'] <= 4
    assert 0 <= player.offensive_stats['wOBA'] <= 2

def test_baserunning_stats(mock_ratings_data):
    player = BatterProjection(mock_ratings_data)
    player.calc_defensive_runs_saved()
    player.calc_offensive_stats()
    player.calc_baserunning_stats()
    assert player.baserunning_stats['SB'] is not None
    assert player.baserunning_stats['CS'] is not None

def test_calc_player_values(mock_ratings_data):
    player = BatterProjection(mock_ratings_data)
    player.calc_defensive_runs_saved()
    player.calc_offensive_stats()
    player.calc_offensive_rates()
    player.calc_player_values()
    assert player.value['WAR'] is not None
    assert player.value['Total_runs'] > 0

def test_calc_expected_stats(mock_ratings_data):
    player = BatterProjection(mock_ratings_data)
    stats = player.calc_expected_stats()
    assert 'offense' in stats
    assert 'value' in stats
    assert stats['value']['WAR'] is not None
