FEATURE_NAMES_BATTER = [
    'player_id',
	'babip',
	'gap',
	'power',
	'eye',
	'strikeouts',
	'speed',
	'steal',
	'baserunning',
	'position',
	'catcher_arm',
	'catcher_framing',
	'infield_range',
	'infield_arm',
	'infield_doubleplay',
	'outfield_range',
	'outfield_arm'
]

FEATURE_WEIGHTS_BATTER = {
	'babip': 1.5,
	'gap': 1.5,
	'power': 1.5,
	'eye': 1.5,
	'strikeouts': 1.5,
	'speed': 0.7,
	'steal': 0.7,
	'baserunning': 0.7,
	'position': 0.5,
	'catcher_arm': 0.5,
	'catcher_framing': 1.2,
	'infield_range': 1.2,
	'infield_arm': 0.8,
	'infield_doubleplay': 0.5,
	'outfield_range': 1.2,
	'outfield_arm': 0.5
}