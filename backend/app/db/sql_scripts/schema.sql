DROP TABLE IF EXISTS players;
DROP TABLE IF EXISTS teams;
DROP TABLE IF EXISTS players_career_batting_stats;
DROP TABLE IF EXISTS players_rating;
DROP TABLE IF EXISTS players_batting;
DROP TABLE IF EXISTS players_basepath;
DROP TABLE IF EXISTS players_basepath_expected;
DROP TABLE IF EXISTS players_fielding;
DROP TABLE IF EXISTS players_fielding_position;
DROP TABLE IF EXISTS players_fielding_position_talent;
DROP TABLE IF EXISTS players_fielding_expected;
DROP TABLE IF EXISTS players_batting_talent;
DROP TABLE IF EXISTS players_batting_expected;
DROP TABLE IF EXISTS players_run_value;


CREATE TABLE players (
  player_id INTEGER PRIMARY KEY,
  first_name VARCHAR(50),
  last_name VARCHAR(50),
  age INTEGER,
  birth_date DATE,
  position VARCHAR(2),  -- e.g., 'P', 'SS' 'CF', etc.
  height INTEGER, -- Height in cm
  weight INTEGER, -- Weight in pounds
  bats VARCHAR(1), -- e.g., 'R', 'L', 'S'
  throws VARCHAR(1), -- e.g., 'R', 'L'
  free_agent BOOLEAN,  -- TRUE if current free_agent
  team_id INTEGER,
  prone_overall INTEGER,
  FOREIGN KEY (team_id) REFERENCES teams(team_id)
);

CREATE TABLE teams (
  team_id INTEGER PRIMARY KEY,
  name VARCHAR(50),
  abbr VARCHAR(50),
  nickname VARCHAR(50),
  division_id INTEGER,
  league_id INTEGER,
  human_team TINYINT,
  background_color VARCHAR(8),
  text_color VARCHAR(8),
  FOREIGN KEY (division_id) REFERENCES divisions(division_id),
  FOREIGN KEY (league_id) REFERENCES leagues(league_id)
);

CREATE TABLE players_career_batting_stats (
  player_id INTEGER,
  year SMALLINT,
  team_id INTEGER,
  game_id INTEGER,
  league_id INTEGER,
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
  wpa REAL,
  stint SMALLINT,
  ubr REAL,
  war REAL,
  FOREIGN KEY (player_id) REFERENCES players(player_id),
  FOREIGN KEY (team_id) REFERENCES teams(team_id),
  FOREIGN KEY (league_id) REFERENCES leagues(league_id)
);

CREATE TABLE players_rating (
  rating_id INTEGER PRIMARY KEY AUTOINCREMENT,
  player_id INTEGER,
  rating_date DATE,
  FOREIGN KEY (player_id) REFERENCES players(player_id),
  UNIQUE(player_id, rating_date)
);

CREATE TABLE players_batting (
  rating_id INTEGER PRIMARY KEY,
  contact INTEGER,
  gap INTEGER,
  eye INTEGER,
  strikeouts INTEGER,
  power INTEGER,
  babip INTEGER,
  bunt INTEGER,
  bunt_for_hit INTEGER,
  FOREIGN KEY (rating_id) REFERENCES players_rating(rating_id)
);

CREATE TABLE players_batting_expected (
  rating_id INTEGER PRIMARY KEY,
  PA INTEGER,
  AB INTEGER,
  H INTEGER,
  "1B" INTEGER,
  "2B" INTEGER,
  "3B" INTEGER,
  HR INTEGER,
  BB INTEGER,
  HBP INTEGER,
  K INTEGER,
  AVG REAL,
  OBP REAL,
  SLG REAL,
  wOBA REAL,
  FOREIGN KEY (rating_id) REFERENCES players_batting(rating_id)
);

CREATE TABLE players_batting_talent (
  rating_id INTEGER PRIMARY KEY,
  contact INTEGER,
  gap INTEGER,
  eye INTEGER,
  strikeouts INTEGER,
  power INTEGER,
  babip INTEGER,
  FOREIGN KEY (rating_id) REFERENCES players_rating(rating_id)
);

CREATE TABLE players_basepath (
  rating_id INTEGER PRIMARY KEY,
  speed INTEGER,
  steal_rate INTEGER,
  steal INTEGER,
  baserunning INTEGER,
  FOREIGN KEY (rating_id) REFERENCES players_rating(rating_id)
);

CREATE TABLE players_basepath_expected (
  rating_id INTEGER PRIMARY KEY,
  SB INTEGER,
  CS INTEGER,
  FOREIGN KEY (rating_id) REFERENCES players_basepath(rating_id)
);

CREATE TABLE players_fielding (
  rating_id INTEGER PRIMARY KEY,
  catcher_arm INTEGER,
  catcher_ability INTEGER,
  catcher_framing INTEGER,
  infield_range INTEGER,
  infield_arm INTEGER,
  infield_doubleplay INTEGER,
  infield_error INTEGER,
  outfield_range INTEGER,
  outfield_arm INTEGER,
  outfield_error INTEGER,
  FOREIGN KEY (rating_id) REFERENCES players_rating(rating_id)
);

CREATE TABLE players_fielding_position (
  rating_id INTEGER PRIMARY KEY,
  pos1 INTEGER,
  pos2 INTEGER,
  pos3 INTEGER,
  pos4 INTEGER,
  pos5 INTEGER,
  pos6 INTEGER,
  pos7 INTEGER,
  pos8 INTEGER,
  pos9 INTEGER,
  FOREIGN KEY (rating_id) REFERENCES players_fielding(rating_id)
);

CREATE TABLE players_fielding_position_talent (
  rating_id INTEGER PRIMARY KEY,
  pos1 INTEGER,
  pos2 INTEGER,
  pos3 INTEGER,
  pos4 INTEGER,
  pos5 INTEGER,
  pos6 INTEGER,
  pos7 INTEGER,
  pos8 INTEGER,
  pos9 INTEGER,
  FOREIGN KEY (rating_id) REFERENCES players_fielding(rating_id)
);

CREATE TABLE players_fielding_expected (
  rating_id INTEGER PRIMARY KEY,
  C REAL,
  "1B" REAL,
  "2B" REAL,
  "3B" REAL,
  SS REAL,
  LF REAL,
  CF REAL,
  RF REAL,
  DH REAL,
  FOREIGN KEY (rating_id) REFERENCES players_fielding_position(rating_id)
);

CREATE TABLE players_run_value (
  rating_id INTEGER PRIMARY KEY,
  batting_runs REAL,
  basepath_runs REAL,
  fielding_runs REAL,
  total_runs REAL,
  WAR REAL,
  FOREIGN KEY (rating_id) REFERENCES players_rating(rating_id)
);