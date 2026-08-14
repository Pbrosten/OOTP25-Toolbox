DROP TABLE IF EXISTS processed_heaps;
DROP TABLE IF EXISTS players_similarity;
DROP TABLE IF EXISTS players_run_value;
DROP TABLE IF EXISTS players_pitching_run_value;
DROP TABLE IF EXISTS players_fielding_expected;
DROP TABLE IF EXISTS players_fielding_position_talent;
DROP TABLE IF EXISTS players_fielding_position;
DROP TABLE IF EXISTS players_fielding;
DROP TABLE IF EXISTS players_basepath_expected;
DROP TABLE IF EXISTS players_basepath;
DROP TABLE IF EXISTS players_batting_expected;
DROP TABLE IF EXISTS players_batting_talent;
DROP TABLE IF EXISTS players_batting;
DROP TABLE IF EXISTS players_pitching_expected;
DROP TABLE IF EXISTS players_pitching_talent;
DROP TABLE IF EXISTS players_pitch_repertoire;
DROP TABLE IF EXISTS players_pitching;
DROP TABLE IF EXISTS players_rating;
DROP TABLE IF EXISTS players_contract;
DROP TABLE IF EXISTS players_salary_history;
DROP TABLE IF EXISTS players_service_time;
DROP TABLE IF EXISTS players_career_batting_stats;
DROP TABLE IF EXISTS players_career_pitching_stats;
DROP TABLE IF EXISTS players;
DROP TABLE IF EXISTS teams;

-- Processed heaps: tracks which dump directories update-db has already
-- ingested, so check_new_heaps() only returns what's actually new.
-- `month` mirrors the raw directory-name segment used by
-- extract_heap_date_from_path() ("05", "yearly", ...) so both sides of the
-- identity check use the exact same string, with no int/13 translation.
CREATE TABLE processed_heaps (
  year VARCHAR(4) NOT NULL,
  month VARCHAR(10) NOT NULL,
  is_short BOOLEAN NOT NULL,
  processed_at DATETIME NOT NULL,
  PRIMARY KEY (year, month)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Teams --
CREATE TABLE teams (
  team_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(50),
  abbr VARCHAR(50),
  nickname VARCHAR(50),
  division_id INT,
  league_id INT,
  human_team TINYINT,
  background_color VARCHAR(8),
  text_color VARCHAR(8)
  -- FOREIGN KEY (division_id) REFERENCES divisions(division_id),
  -- FOREIGN KEY (league_id) REFERENCES leagues(league_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Players --
CREATE TABLE players (
  player_id INT AUTO_INCREMENT PRIMARY KEY,
  first_name VARCHAR(50),
  last_name VARCHAR(50),
  age INT,
  birth_date DATE,
  position VARCHAR(2),
  height INT,
  weight INT,
  bats CHAR(1),
  throws CHAR(1),
  free_agent BOOLEAN,
  team_id INT,
  prone_overall INT,
  retired BOOLEAN DEFAULT FALSE,
  FOREIGN KEY (team_id) REFERENCES teams(team_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Player Career Batting --
CREATE TABLE players_career_batting_stats (
  player_id INT,
  year SMALLINT,
  team_id INT,
  game_id INT,
  league_id INT,
  level_id SMALLINT,
  split_id SMALLINT,
  ab SMALLINT,
  h SMALLINT,
  k SMALLINT,
  pa SMALLINT,
  pitches_seen SMALLINT,
  g SMALLINT,
  gs SMALLINT,
  d SMALLINT,
  t SMALLINT,
  hr SMALLINT,
  r SMALLINT,
  rbi SMALLINT,
  sb SMALLINT,
  cs SMALLINT,
  bb SMALLINT,
  ibb SMALLINT,
  gdp SMALLINT,
  sh SMALLINT,
  sf SMALLINT,
  hp SMALLINT,
  ci SMALLINT,
  wpa FLOAT,
  stint SMALLINT,
  ubr FLOAT,
  war FLOAT,
  PRIMARY KEY (player_id, year, team_id),
  FOREIGN KEY (player_id) REFERENCES players(player_id),
  FOREIGN KEY (team_id) REFERENCES teams(team_id)
  -- FOREIGN KEY (league_id) REFERENCES leagues(league_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Player Career Pitching --
CREATE TABLE players_career_pitching_stats (
  player_id INT,
  year SMALLINT,
  team_id INT,
  game_id INT,
  league_id INT,
  level_id SMALLINT,
  split_id SMALLINT,
  ip SMALLINT,
  ab SMALLINT,
  tb SMALLINT,
  ha SMALLINT,
  k SMALLINT,
  bf SMALLINT,
  rs SMALLINT,
  bb SMALLINT,
  r SMALLINT,
  er SMALLINT,
  gb SMALLINT,
  fb SMALLINT,
  pi SMALLINT,
  ipf SMALLINT,
  g SMALLINT,
  gs SMALLINT,
  w SMALLINT,
  l SMALLINT,
  s SMALLINT,
  sa SMALLINT,
  da SMALLINT,
  sh SMALLINT,
  sf SMALLINT,
  ta SMALLINT,
  hra SMALLINT,
  bk SMALLINT,
  ci SMALLINT,
  iw SMALLINT,
  wp SMALLINT,
  hp SMALLINT,
  gf SMALLINT,
  dp SMALLINT,
  qs SMALLINT,
  svo SMALLINT,
  bs SMALLINT,
  ra SMALLINT,
  cg SMALLINT,
  sho SMALLINT,
  sb SMALLINT,
  cs SMALLINT,
  hld SMALLINT,
  ir DOUBLE,
  irs DOUBLE,
  wpa DOUBLE,
  li DOUBLE,
  stint SMALLINT,
  outs SMALLINT,
  sd SMALLINT,
  md SMALLINT,
  war DOUBLE,
  ra9war DOUBLE,
  PRIMARY KEY (player_id, year, team_id),
  FOREIGN KEY (player_id) REFERENCES players(player_id),
  FOREIGN KEY (team_id) REFERENCES teams(team_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Player Rating --
CREATE TABLE players_rating (
  rating_id INT AUTO_INCREMENT PRIMARY KEY,
  player_id INT,
  rating_date DATE,
  league_id INT,
  UNIQUE (player_id, rating_date),
  FOREIGN KEY (player_id) REFERENCES players(player_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Player Batting --
CREATE TABLE players_batting (
  rating_id INT PRIMARY KEY,
  contact INT,
  gap INT,
  eye INT,
  strikeouts INT,
  power INT,
  babip INT,
  bunt INT,
  bunt_for_hit INT,
  FOREIGN KEY (rating_id) REFERENCES players_rating(rating_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Player Batting Expected --
CREATE TABLE players_batting_expected (
  rating_id INT PRIMARY KEY,
  PA INT,
  AB INT,
  H INT,
  `1B` INT,
  `2B` INT,
  `3B` INT,
  HR INT,
  BB INT,
  HBP INT,
  K INT,
  AVG FLOAT,
  OBP FLOAT,
  SLG FLOAT,
  wOBA FLOAT,
  FOREIGN KEY (rating_id) REFERENCES players_batting(rating_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Player Batting Talent --
CREATE TABLE players_batting_talent (
  rating_id INT PRIMARY KEY,
  contact INT,
  gap INT,
  eye INT,
  strikeouts INT,
  power INT,
  babip INT,
  FOREIGN KEY (rating_id) REFERENCES players_rating(rating_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Player Pitching --
CREATE TABLE players_pitching (
  rating_id INT PRIMARY KEY,
  role SMALLINT,
  stuff INT,
  movement INT,
  hra INT,
  pbabip INT,
  control INT,
  balk INT,
  hp INT,
  wild_pitch INT,
  velocity INT,
  arm_slot INT,
  stamina INT,
  ground_fly INT,
  hold INT,
  FOREIGN KEY (rating_id) REFERENCES players_rating(rating_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Player Pitching Expected --
CREATE TABLE players_pitching_expected (
  rating_id INT PRIMARY KEY,
  PA INT,
  AB INT,
  H INT,
  HR INT,
  BB INT,
  HBP INT,
  K INT,
  BA FLOAT,
  OBP FLOAT,
  wOBA FLOAT,
  IP FLOAT,
  GS INT,
  G INT,
  RA9 FLOAT,
  ERA FLOAT,
  FOREIGN KEY (rating_id) REFERENCES players_pitching(rating_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Player Pitching Talent --
CREATE TABLE players_pitching_talent (
  rating_id INT PRIMARY KEY,
  stuff INT,
  movement INT,
  hra INT,
  pbabip INT,
  control INT,
  balk INT,
  hp INT,
  wild_pitch INT,
  FOREIGN KEY (rating_id) REFERENCES players_rating(rating_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Player Pitch Repertoire --
-- One row per pitch type a player actually throws (grade > 0 in the
-- source export), not a fixed 12-column-wide row -- see ticket 0029/0031.
CREATE TABLE players_pitch_repertoire (
  rating_id INT NOT NULL,
  pitch_type VARCHAR(20) NOT NULL,
  grade INT,
  talent_grade INT,
  PRIMARY KEY (rating_id, pitch_type),
  FOREIGN KEY (rating_id) REFERENCES players_rating(rating_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Player Basepath --
CREATE TABLE players_basepath (
  rating_id INT PRIMARY KEY,
  speed INT,
  steal_rate INT,
  steal INT,
  baserunning INT,
  FOREIGN KEY (rating_id) REFERENCES players_rating(rating_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Player Basepath Expected --
CREATE TABLE players_basepath_expected (
  rating_id INT PRIMARY KEY,
  SB INT,
  CS INT,
  FOREIGN KEY (rating_id) REFERENCES players_basepath(rating_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Player Fielding --
CREATE TABLE players_fielding (
  rating_id INT PRIMARY KEY,
  catcher_arm INT,
  catcher_ability INT,
  catcher_framing INT,
  infield_range INT,
  infield_arm INT,
  infield_doubleplay INT,
  infield_error INT,
  outfield_range INT,
  outfield_arm INT,
  outfield_error INT,
  FOREIGN KEY (rating_id) REFERENCES players_rating(rating_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Player Positional Fielding --
CREATE TABLE players_fielding_position (
  rating_id INT PRIMARY KEY,
  pos1 INT,
  pos2 INT,
  pos3 INT,
  pos4 INT,
  pos5 INT,
  pos6 INT,
  pos7 INT,
  pos8 INT,
  pos9 INT,
  FOREIGN KEY (rating_id) REFERENCES players_fielding(rating_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Player Positional Talent --
CREATE TABLE players_fielding_position_talent (
  rating_id INT PRIMARY KEY,
  pos1 INT,
  pos2 INT,
  pos3 INT,
  pos4 INT,
  pos5 INT,
  pos6 INT,
  pos7 INT,
  pos8 INT,
  pos9 INT,
  FOREIGN KEY (rating_id) REFERENCES players_fielding(rating_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Player Expected Fielding --
CREATE TABLE players_fielding_expected (
  rating_id INT PRIMARY KEY,
  C FLOAT,
  `1B` FLOAT,
  `2B` FLOAT,
  `3B` FLOAT,
  SS FLOAT,
  LF FLOAT,
  CF FLOAT,
  RF FLOAT,
  DH FLOAT,
  FOREIGN KEY (rating_id) REFERENCES players_fielding_position(rating_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Player Run Value --
CREATE TABLE players_run_value (
  rating_id INT PRIMARY KEY,
  batting_runs FLOAT,
  basepath_runs FLOAT,
  fielding_runs FLOAT,
  total_runs FLOAT,
  WAR FLOAT,
  FOREIGN KEY (rating_id) REFERENCES players_rating(rating_id)
);

-- Player Pitching Run Value --
-- No defense_runs column: the source spreadsheet's pitcher defense-runs
-- curve ('Projection Constants'!V7:V23 and V4) is 0 at every rating step
-- (verified directly), and there's no pitcher fielding rating in the OOTP
-- export to drive it anyway (see ticket 0028). pitching_runs is the
-- wRAA-against equivalent (PitcherProjection.runs_prevented), baserunning_runs
-- is the Hold-based runs-allowed term. No leverage adjustment on WAR for
-- relievers -- see ticket 0028's Design choices.
CREATE TABLE players_pitching_run_value (
  rating_id INT PRIMARY KEY,
  pitching_runs FLOAT,
  baserunning_runs FLOAT,
  total_runs FLOAT,
  WAR FLOAT,
  FOREIGN KEY (rating_id) REFERENCES players_rating(rating_id)
);

CREATE TABLE players_similarity (
  player_main INTEGER,
  player_comp INTEGER,
  similarity REAL,
  player_type TEXT CHECK(player_type IN ('batter', 'pitcher')),
  PRIMARY KEY (player_main, player_comp)
);

-- Contract / salary / service-time: see ticket 0053. Current-state tables
-- (upserted per yearly heap), not dated snapshots -- these files only ever
-- appear in yearly dump heaps, and salary0..salary14 already self-describes
-- the forward schedule.
CREATE TABLE players_contract (
  player_id INT PRIMARY KEY,
  team_id INT,
  season_year INT,
  years SMALLINT,
  current_year SMALLINT,
  salary0 INT, salary1 INT, salary2 INT, salary3 INT, salary4 INT,
  salary5 INT, salary6 INT, salary7 INT, salary8 INT, salary9 INT,
  salary10 INT, salary11 INT, salary12 INT, salary13 INT, salary14 INT,
  no_trade BOOLEAN,
  last_year_team_option BOOLEAN,
  last_year_player_option BOOLEAN,
  last_year_vesting_option BOOLEAN,
  opt_out SMALLINT,
  FOREIGN KEY (player_id) REFERENCES players(player_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE players_salary_history (
  player_id INT,
  team_id INT,
  year SMALLINT,
  salary INT,
  PRIMARY KEY (player_id, year),
  FOREIGN KEY (player_id) REFERENCES players(player_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE players_service_time (
  player_id INT PRIMARY KEY,
  mlb_service_years SMALLINT,
  mlb_service_days SMALLINT,
  pro_service_years SMALLINT,
  has_received_arbitration BOOLEAN,
  FOREIGN KEY (player_id) REFERENCES players(player_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
