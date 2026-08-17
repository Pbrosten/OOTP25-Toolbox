from math import floor
from datetime import datetime

import pandas as pd
import importlib.resources as resources

from . import constants

# === Load constants ONCE when module is imported ===
with resources.files(constants).joinpath('offensive_constants.pkl').open('rb') as f:
    BAT_CONSTANTS = pd.read_pickle(f)
with resources.files(constants).joinpath('defensive_constants.pkl').open('rb') as f:
    DEF_CONSTANTS = pd.read_pickle(f)
with resources.files(constants).joinpath('injury_constants.pkl').open('rb') as f:
    INJ_CONSTANTS = pd.read_pickle(f)

# === Global Constants ===
LG_WOBA = 0.325
FACTOR_WOBA = 1.20
FACTOR_BB = 0.7
FACTOR_1B = 0.9
FACTOR_2B = 1.25
FACTOR_3B = 1.6
FACTOR_HR = 2
HITTER_REPLACEMENT_RUNS = 0.0333
RUNS_WIN = 9.92

# === Positional Adjustments ===
def_pos_adj = {
    'C':  {"G": 120, "PA": 500, "IP": 1050, "PosAdj": 0.007},
    '1B': {"G": 150, "PA": 600, "IP": 1260, "PosAdj": -0.007},
    '2B': {"G": 140, "PA": 550, "IP": 1155, "PosAdj": 0.002},
    '3B': {"G": 140, "PA": 550, "IP": 1155, "PosAdj": 0.001},
    'SS': {"G": 140, "PA": 550, "IP": 1155, "PosAdj": 0.005},
    'LF': {"G": 140, "PA": 550, "IP": 1155, "PosAdj": -0.005},
    'CF': {"G": 140, "PA": 550, "IP": 1155, "PosAdj": 0.002},
    'RF': {"G": 140, "PA": 550, "IP": 1155, "PosAdj": -0.005},
    'DH': {"G": 160, "PA": 650, "IP": 1365, "PosAdj": -0.011}
}

# === Batter Projection Class ===
class BatterProjection:
    def __init__(self, data: dict):
        # Basic player info
        self.player_id = data.get('player_id')
        self.rating_id = data.get('rating_id')
        self.rating_date = data.get('rating_date', '9999-12-31')
        self.birth_date = data.get('birth_date', '9999-12-31')
        self.position = data.get('position')
        self.bats = data.get('bats')

        # Injury status
        self.injury = data.get('prone_overall', 100)
        self.injury = (
            'Durable' if self.injury < 25 else
            'Normal' if self.injury < 125 else
            'Fragile' if self.injury < 175 else
            'Wrecked'
        )

        # League baseline (ticket 0066): this save's own recalibrated
        # lg_woba (app/db/projection.py::compute_league_baselines), joined
        # onto every projection-input row by get_projection_inputs.sql.
        # Falls back to the hardcoded real-MLB LG_WOBA module constant
        # before the first long heap has computed one.
        lg_woba = data.get('lg_woba')
        self.lg_woba = lg_woba if lg_woba is not None else LG_WOBA

        # Ratings
        self.babip = data.get('babip')
        self.gap = data.get('gap')
        self.eye = data.get('eye')
        self.power = data.get('power')
        self.strikeouts = data.get('strikeouts')
        self.speed = data.get('speed')
        self.steal = data.get('steal')
        self.baserunning = data.get('baserunning')

        # Defense ratings
        self.defense = {
            'C': data.get('pos2'),
            '_1B': data.get('pos3'),
            '_2B': data.get('pos4'),
            '_3B': data.get('pos5'),
            'SS': data.get('pos6'),
            'LF': data.get('pos7'),
            'CF': data.get('pos8'),
            'RF': data.get('pos9')
        }

        # Formatting and constants
        self.format = '%Y-%m-%d'
        self.bat_constants = BAT_CONSTANTS
        self.def_constants = DEF_CONSTANTS
        self.inj_constants = INJ_CONSTANTS

        # Stat placeholders
        self.offensive_stats = {
            "PA": None, "AB": 550, "H": None, "_1B": None, "_2B": None,
            "_3B": None, "HR": None, "BB": None, "HBP": 5, "K": None,
            "AVG": 0.0, "OBP": 0.0, "SLG": 0.0, "wOBA": 0.0
        }
        self.baserunning_stats = {
            "SB": None, "CS": None
        }
        self.defensive_values = {
            "C": None,
            "_1B": None, "_2B": None, "_3B": None, "SS": None,
            "LF": None, "CF": None, "RF": None,
            "DH": -15
        }
        self.value = {
            "wRAA": None, "BR_runs": None, "Def_runs": None,
            "Replace_runs": None, "Total_runs": None,
            "WAR": None
        }
        self.def_innings = 1350
        self.def_divisor = 2.1
        self.def_max = ('DH', -15)
    
    def get_ratings(self):
        return {
            "offense": {
                "babip": self.babip,
                "gap": self.gap,
                "power": self.power,
                "eye": self.eye,
                "avoid_ks": self.strikeouts,
                "speed": self.speed,
                "steal": self.steal,
                "baserunning": self.baserunning
            },
            "defense": self.defense
        }

    def calc_age(self):
        days_diff = (
            datetime.strptime(self.rating_date, self.format) -
            datetime.strptime(self.birth_date, self.format)
        ).days
        return floor(days_diff / 365.25)
    
    def calc_best_position(self):
        arg_max = max(self.defensive_values, key=self.defensive_values.get)
        if arg_max == 'DH':
            self.hit_factor = 0.98
        else: self.hit_factor = 1.0
        return arg_max, self.defensive_values[arg_max] 
    
    def lookup_bat(self, rating, feature):
        return self.bat_constants.loc[rating, feature]
    
    def lookup_def(self, rating, feature):
        return self.def_constants.loc[rating, feature]
    
    def lookup_inj(self, player_type: str):
        return self.inj_constants.loc[self.injury, player_type]
    
    def calc_defensive_runs_saved(self):
        for position in self.defense:
            key = position.strip('_')
            self.defensive_values[position] = self.def_innings * (
                self.lookup_def(self.defense[position], key) +
                def_pos_adj[key]['PosAdj']
            )
        self.def_max = self.calc_best_position()
    
    def calc_offensive_stats_base(self):
        ab = self.offensive_stats['AB']
        self.offensive_stats['_2B'] = ab * self.lookup_bat(self.gap, 'XBH') * (1 - self.lookup_bat(self.speed, '3B'))
        self.offensive_stats['_3B'] = ab * self.lookup_bat(self.gap, 'XBH') * self.lookup_bat(self.speed, '3B')
        self.offensive_stats['HR'] = ab * self.lookup_bat(self.power, 'HR')
        self.offensive_stats['K'] = ab * self.lookup_bat(self.strikeouts, 'K')
        self.offensive_stats['BB'] = ab * self.lookup_bat(self.eye, 'BB')

        self.offensive_stats['_1B'] = (
            (ab - self.offensive_stats['_2B'] - self.offensive_stats['_3B'] -
             self.offensive_stats['HR'] - self.offensive_stats['K']) *
            self.lookup_bat(self.babip, '1B')
        )
        self.offensive_stats['H'] = (
            self.offensive_stats['_1B'] +
            self.offensive_stats['_2B'] +
            self.offensive_stats['_3B'] +
            self.offensive_stats['HR']
        )
        self.offensive_stats['PA'] = (
            self.offensive_stats['AB'] +
            self.offensive_stats['BB'] +
            self.offensive_stats['HBP']
        )

    def calc_offensive_stats(self):
        self.calc_offensive_stats_base()
        pa_factor_raw = def_pos_adj[self.def_max[0].strip('_')]['PA']
        self.pa_factor = (pa_factor_raw / self.lookup_inj("Batter")) / self.offensive_stats['PA']

        for stat in ['PA', 'AB', 'H', 'HBP']:
            self.offensive_stats[stat] *= self.pa_factor
        for stat in ['_1B', '_2B', '_3B', 'HR', 'BB']:
            self.offensive_stats[stat] *= self.pa_factor * self.hit_factor

        self.offensive_stats['K'] = (self.offensive_stats['K'] * self.pa_factor) / self.hit_factor
        self.calc_baserunning_stats()
    
    def calc_offensive_rates(self):
        os = self.offensive_stats
        os['AVG'] = os['H'] / os['AB']
        os['OBP'] = (os['H'] + os['BB'] + os['HBP']) / os['PA']
        os['SLG'] = (
            os['_1B'] + os['_2B'] * 2 + os['_3B'] * 3 + os['HR'] * 4
        ) / os['AB']
        os['wOBA'] = (
            (os['BB'] + os['HBP']) * FACTOR_BB +
            os['_1B'] * FACTOR_1B +
            os['_2B'] * FACTOR_2B +
            os['_3B'] * FACTOR_3B +
            os['HR'] * FACTOR_HR
        ) / os['PA']

    def calc_baserunning_stats(self):
        on_base_events = (
            self.offensive_stats['_1B'] +
            self.offensive_stats['_2B'] +
            self.offensive_stats['BB'] +
            self.offensive_stats['HBP']
        )

        self.baserunning_stats['SB'] = on_base_events * self.lookup_bat(self.steal, 'SB')
        self.baserunning_stats['CS'] = on_base_events * self.lookup_bat(self.steal, 'CS')

    def calc_player_values(self):
        os = self.offensive_stats
        self.value['wRAA'] = ((os['wOBA'] - self.lg_woba) / FACTOR_WOBA) * os['PA']
        self.value['BR_runs'] = (
            (os['_1B'] + os['_2B'] + os['BB'] + os['HBP']) *
            (
                self.lookup_bat(self.speed, 'UBR_speed') +
                self.lookup_bat(self.steal, 'wSB') +
                self.lookup_bat(self.baserunning, 'UBR_br')
            )
        )
        self.value['Def_runs'] = os['PA'] * self.def_max[1] / self.def_innings * self.def_divisor
        self.value['Replace_runs'] = os['PA'] * HITTER_REPLACEMENT_RUNS
        self.value['Total_runs'] = (
            self.value['wRAA'] + self.value['BR_runs'] +
            self.value['Def_runs'] + self.value['Replace_runs']
        )
        self.value['WAR'] = self.value['Total_runs'] / RUNS_WIN

    def calc_expected_stats(self):
        self.calc_defensive_runs_saved()
        self.calc_offensive_stats()
        self.calc_offensive_rates()
        self.calc_player_values()

        output = {
            "offense": self.offensive_stats,
            "basepath": self.baserunning_stats,
            "defense": self.defensive_values,
            "value": self.value
        }
        for key in output:
            output[key]["rating_id"] = self.rating_id

        return output