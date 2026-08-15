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

# Runs/Win (ticket 0028) is dynamic per pitcher, unlike BatterProjection's
# fixed RUNS_WIN constant -- it blends league-average and the pitcher's own
# RA9, weighted by how much of a "full game" (18 IP, i.e. both starter's and
# bullpen's innings) their average outing covers. Formula + these three
# literals verified against 'Starting/Relief Pitchers'!D*3 (Runs/Win column)
# in the source workbook -- they aren't named cells there either.
RUNS_PER_WIN_FULL_GAME_IP = 18
RUNS_PER_WIN_OFFSET = 2
RUNS_PER_WIN_SCALE = 1.5

# Playing_Time_input has no source in the OOTP ratings export (see
# docs/wiki/Projections.md#34-playing-time-scaling) -- defaulted to a full
# share for every pitcher rather than deriving a rotation/bullpen-depth
# signal from roster data. Known limitation, not a per-player value.
PLAYING_TIME_INPUT = 1.0

# === Role-specific baseline workload constants ===
# rep_per_ip ("Weighting Constants"!B41/B42): replacement-level runs/IP,
# pitching's equivalent of BatterProjection's HITTER_REPLACEMENT_RUNS.
ROLE_CONSTANTS = {
    'SP': {"ab_baseline": 900, "pa_baseline": 750, "gs_g_baseline": 27, "durability": "Starter", "rep_per_ip": 0.12},
    'RP': {"ab_baseline": 300, "pa_baseline": 300, "gs_g_baseline": 50, "durability": "Reliever", "rep_per_ip": 0.03},
}

# staging.players_pitching.role: 11 = Starting Pitcher, 12 = Relief Pitcher,
# 13 = Closer (a small subset of all-relief usage, folded into RP since the
# source spreadsheet only defines SP/RP rate curves -- see ticket 0026).
# role 0 (non-pitcher) is included here as of ticket 0067 -- a two-way
# player's role toggles between a real pitcher role and 0 depending on
# which side of their game OOTP emphasized that month, but their
# stuff/control/etc. ratings that feed this projection are still real
# regardless. Defaults to 'SP' role_constants -- same "default an
# unrecognized/absent role to Starter, more conservative" precedent
# ticket 0059 already established for the injury-discount multiplier.
ROLE_MAP = {11: 'SP', 12: 'RP', 13: 'RP', 0: 'SP'}


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
        self.hold = data.get('hold')

        self.pitch_constants = PITCH_CONSTANTS
        self.inj_constants = INJ_CONSTANTS

        self.stats = {
            "PA": None, "AB": None, "H": None, "HR": None, "BB": None,
            "HBP": None, "K": None, "BA": None, "OBP": None, "wOBA": None,
            "IP": None, "GS": None, "G": None, "RA9": None, "ERA": None,
        }
        self.value = {
            "pitching_runs": None, "baserunning_runs": None,
            "total_runs": None, "WAR": None,
        }

    def lookup_pitch(self, rating, feature):
        return self.pitch_constants.loc[rating, f"{self.role}_{feature}"]

    def lookup_baserunning(self, rating):
        # Hold -> baserunning-runs-allowed/IP -- the one rate curve shared
        # by SP and RP alike ('Projection Constants'!$AB$7:$AB$23), not
        # role-prefixed like the others.
        return self.pitch_constants.loc[rating, 'BR']

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
        # Nominally a Value-section formula (wRAA-against), but RA9/ERA
        # can't be derived without it -- stashed on self so
        # calc_player_values() (ticket 0028) reuses it instead of
        # recomputing. See wiki/Projections.md §3.5.
        self.runs_prevented = (LG_PWOBA - s['wOBA']) / WOBA_SCALE * s['PA']
        s['RA9'] = RA9_BASELINE - self.runs_prevented / s['IP'] * 9
        s['ERA'] = ERA_MULTIPLIER * s['RA9']

    def calc_player_values(self):
        v = self.value
        s = self.stats

        v['pitching_runs'] = self.runs_prevented
        v['baserunning_runs'] = s['IP'] * self.lookup_baserunning(self.hold)
        replacement_runs = s['IP'] * self.role_constants['rep_per_ip']
        v['total_runs'] = v['pitching_runs'] + v['baserunning_runs'] + replacement_runs

        # Dynamic runs/win: blends league-average RA9 and this pitcher's own
        # RA9, weighted by how much of an 18-IP "full game" their average
        # outing (IP / GS-or-G) covers -- same formula for SP and RP, only
        # the GS-vs-G divisor differs (already tracked in actual_gs_or_g).
        innings_per_outing = s['IP'] / self.actual_gs_or_g
        runs_per_win = (
            (
                (RUNS_PER_WIN_FULL_GAME_IP - innings_per_outing) * RA9_BASELINE +
                innings_per_outing * s['RA9']
            ) / RUNS_PER_WIN_FULL_GAME_IP + RUNS_PER_WIN_OFFSET
        ) * RUNS_PER_WIN_SCALE
        v['WAR'] = v['total_runs'] / runs_per_win

    def calc_expected_stats(self):
        self.calc_baseline_stats()
        self.calc_actual_playing_time()
        self.calc_scaled_stats()
        self.calc_rates()
        self.calc_player_values()

        output = {"pitching": self.stats, "pitching_value": self.value}
        for key in output:
            output[key]["rating_id"] = self.rating_id
        return output
