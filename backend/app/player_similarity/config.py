FEATURE_NAMES_BATTER = [
    'player_id',
	'babip',
	'gap',
	'power',
	'eye',
	'strikeouts',
	'speed',
	'steal',
	'position',
    'defensive_primary',
    'defensive_secondary'
]

FEATURE_WEIGHTS_BATTER = {
	'babip': 1.5,
	'gap': 1.5,
	'power': 1.5,
	'eye': 1.5,
	'strikeouts': 1.5,
	'speed': 0.5,
	'steal': 0.5,
	'position': 1.0,
    'defensive_primary': 1.2,
    'defensive_secondary': 0.8
}