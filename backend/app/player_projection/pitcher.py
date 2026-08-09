import pandas as pd
import importlib.resources as resources

from . import constants

# === Load constants ONCE when module is imported ===
with resources.files(constants).joinpath('pitching_constants.pkl').open('rb') as f:
    PITCH_CONSTANTS = pd.read_pickle(f)
with resources.files(constants).joinpath('injury_constants.pkl').open('rb') as f:
    INJ_CONSTANTS = pd.read_pickle(f)

# === Global Constants (Weighting Constants sheet) ===
HBP_RATE = 0.009
FACTOR_BB = 0.7
FACTOR_HR = 2.0
LG_PWOBA = 0.327
WOBA_SCALE = 1.2
OUTS_IP_MULTIPLIER = 2.91
RA9_BASELINE = 4.65
ERA_MULTIPLIER = 0.92

# Playing_Time_input has no source in the OOTP ratings export (see
# docs/wiki/Projections.md#34-playing-time-scaling) -- defaulted to a full
# share for every pitcher rather than deriving a rotation/bullpen-depth
# signal from roster data. Known limitation, not a per-player value.
PLAYING_TIME_INPUT = 1.0

# === Role-specific baseline workload constants ===
ROLE_CONSTANTS = {
    'SP': {"ab_baseline": 900, "pa_baseline": 750, "gs_g_baseline": 27, "durability": "Starter"},
    'RP': {"ab_baseline": 300, "pa_baseline": 300, "gs_g_baseline": 50, "durability": "Reliever"},
}

# staging.players_pitching.role: 11 = Starting Pitcher, 12 = Relief Pitcher,
# 13 = Closer (a small subset of all-relief usage, folded into RP since the
# source spreadsheet only defines SP/RP rate curves -- see ticket 0026).
ROLE_MAP = {11: 'SP', 12: 'RP', 13: 'RP'}


class PitcherProjection:
    def __init__(self, data: dict):
        self.rating_id = data.get('rating_id')

        role = ROLE_MAP.get(data.get('role'))
        if role is None:
            raise ValueError(f"Unrecognized pitcher role: {data.get('role')!r}")
        self.role = role
        self.role_constants = ROLE_CONSTANTS[role]

        # Injury/durability status -- same prone_overall bucketing as
        # BatterProjection (backend/app/player_projection/batter.py:53-59).
        self.injury = data.get('prone_overall', 100)
        self.injury = (
            'Durable' if self.injury < 25 else
            'Normal' if self.injury < 125 else
            'Fragile' if self.injury < 175 else
            'Wrecked'
        )

        # Ratings (current only -- no age-development blend; see ticket
        # 0026's Design choices for why this diverges from the spreadsheet's
        # "Projected" track but matches how BatterProjection works today).
        self.stuff = data.get('stuff')
        self.control = data.get('control')
        self.pbabip = data.get('pbabip')
        self.hra = data.get('hra')
        self.stamina = data.get('stamina')

        self.pitch_constants = PITCH_CONSTANTS
        self.inj_constants = INJ_CONSTANTS

        self.stats = {
            "PA": None, "AB": None, "H": None, "HR": None, "BB": None,
            "HBP": None, "K": None, "BA": None, "OBP": None, "wOBA": None,
            "IP": None, "GS": None, "G": None, "RA9": None, "ERA": None,
        }

    def lookup_pitch(self, rating, feature):
        return self.pitch_constants.loc[rating, f"{self.role}_{feature}"]

    def lookup_inj(self):
        return self.inj_constants.loc[self.injury, self.role_constants["durability"]]

    def calc_baseline_stats(self):
        ab = self.role_constants["ab_baseline"]
        self.stats['AB'] = ab
        self.stats['K'] = ab * self.lookup_pitch(self.stuff, 'K')
        self.stats['HR'] = ab * self.lookup_pitch(self.hra, 'HR')
        self.stats['BB'] = ab * self.lookup_pitch(self.control, 'BB')
        self.stats['HBP'] = ab * HBP_RATE
        self.stats['H'] = (
            (ab - self.stats['HR'] - self.stats['K']) *
            self.lookup_pitch(self.pbabip, 'H') + self.stats['HR']
        )
        self.baseline_pa = ab + self.stats['BB'] + self.stats['HBP']

    def calc_actual_playing_time(self):
        stamina_factor = self.lookup_pitch(self.stamina, 'TBF')
        durability_factor = self.lookup_inj()
        self.actual_pa = (
            self.role_constants["pa_baseline"] * stamina_factor *
            PLAYING_TIME_INPUT * durability_factor
        )
        self.actual_gs_or_g = (
            self.role_constants["gs_g_baseline"] * stamina_factor *
            PLAYING_TIME_INPUT * durability_factor
        )

    def calc_scaled_stats(self):
        ratio = self.actual_pa / self.baseline_pa
        for stat in ('AB', 'H', 'HR', 'BB', 'HBP', 'K'):
            self.stats[stat] *= ratio
        self.stats['PA'] = self.actual_pa
        if self.role == 'SP':
            self.stats['GS'] = self.actual_gs_or_g
        else:
            self.stats['G'] = self.actual_gs_or_g

    def calc_rates(self):
        s = self.stats
        s['BA'] = s['H'] / s['AB']
        s['OBP'] = (s['H'] + s['BB'] + s['HBP']) / s['PA']
        s['wOBA'] = (
            (s['BB'] + s['HBP']) * FACTOR_BB +
            (s['H'] - s['HR']) +
            s['HR'] * FACTOR_HR
        ) / s['PA']
        s['IP'] = (s['PA'] - s['H'] - s['BB'] - s['HBP']) / OUTS_IP_MULTIPLIER
        runs_prevented = (LG_PWOBA - s['wOBA']) / WOBA_SCALE * s['PA']
        s['RA9'] = RA9_BASELINE - runs_prevented / s['IP'] * 9
        s['ERA'] = ERA_MULTIPLIER * s['RA9']

    def calc_expected_stats(self):
        self.calc_baseline_stats()
        self.calc_actual_playing_time()
        self.calc_scaled_stats()
        self.calc_rates()

        output = {"pitching": self.stats}
        for key in output:
            output[key]["rating_id"] = self.rating_id
        return output
