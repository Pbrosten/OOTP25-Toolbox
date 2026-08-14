-- Player rating delta/trend query (ticket 0050, restricted per user request
-- after 0052 shipped -- see 0050's Design choices for the amendment): for a
-- given player, compares their latest heap's ratings against the ratings
-- from 3 heaps prior (their own heap sequence, not a fixed calendar offset
-- -- players can be absent from a heap, e.g. free agents or players pruned
-- by ticket 0046, so a fixed 3-month lookback would under/over-count).
--
-- Tracked categories are curated per player type, not "every rating
-- column":
--   Position players (players.position <> 'P'): babip, power, eye
--     (players_batting), speed (players_basepath), and defense --
--     infield_range, outfield_range, catcher_framing (players_fielding).
--   Pitchers (players.position = 'P'): stuff, movement, control
--     (players_pitching, all three also exist in players_pitching_talent),
--     velocity, stamina (players_pitching only -- no talent counterpart).
--
-- Every branch below carries an explicit `player_info.position` gate --
-- NOT relying on "the source table only has rows for one player type"
-- (migration_short.sql filters players_batting to non-pitchers and
-- players_pitching to pitchers by role, which usually but not always
-- matches players.position: confirmed against the live ootp database that
-- at least one player has position = 'P' but still carries players_batting
-- rows, the same role/position mismatch edge case ticket 0030's Design
-- choices flagged as never fully carved out for TWPs). Gating explicitly
-- on players.position, rather than on which tables happen to have rows,
-- is what actually matches "if the player is a pitcher or position
-- player."
--
-- Overall vs. talent: for the three categories that have both (babip/
-- power/eye for batters; stuff/movement/control for pitchers), which one
-- is tracked depends on whether the player has reached the majors --
-- overall ("current ability") for a player whose latest heap has
-- league_id = 203 (MLB, same convention as PlayerDetails.vue's MLB/MiLB
-- label and the pitching percentiles query's cohort filter), talent
-- ("potential") for a player who hasn't yet. velocity/stamina/speed/
-- defense have no talent-table equivalent in the schema at all, so those
-- always track the overall column regardless of MLB status.
WITH sequenced AS (
  SELECT
    rating_id,
    rating_date,
    league_id,
    ROW_NUMBER() OVER (ORDER BY rating_date) AS heap_seq
  FROM players_rating
  WHERE player_id = %(player_id)s
),
current_heap AS (
  SELECT rating_id, rating_date, league_id, heap_seq
  FROM sequenced
  ORDER BY heap_seq DESC
  LIMIT 1
),
prior_heap AS (
  SELECT s.rating_id, s.rating_date
  FROM sequenced AS s
  JOIN current_heap AS c ON s.heap_seq = c.heap_seq - 3
),
player_info AS (
  SELECT position FROM players WHERE player_id = %(player_id)s
)

SELECT * FROM (

  -- ============================== BATTING (position players) ==============================

  -- babip: overall if MLB, talent if not
  SELECT 'players_batting' AS table_name, 'babip' AS column_name, p.rating_date AS from_date, c.rating_date AS `to_date`, prior.babip AS from_value, cur.babip AS to_value, (cur.babip - prior.babip) AS delta, 5 AS threshold, (ABS(cur.babip - prior.babip) >= 5) AS exceeded FROM current_heap c CROSS JOIN prior_heap p CROSS JOIN player_info pl JOIN players_batting cur ON cur.rating_id = c.rating_id JOIN players_batting prior ON prior.rating_id = p.rating_id WHERE pl.position <> 'P' AND c.league_id = 203
  UNION ALL
  SELECT 'players_batting_talent', 'babip', p.rating_date, c.rating_date, prior.babip, cur.babip, (cur.babip - prior.babip), 10, (ABS(cur.babip - prior.babip) >= 10) FROM current_heap c CROSS JOIN prior_heap p CROSS JOIN player_info pl JOIN players_batting_talent cur ON cur.rating_id = c.rating_id JOIN players_batting_talent prior ON prior.rating_id = p.rating_id WHERE pl.position <> 'P' AND c.league_id <> 203
  UNION ALL

  -- power: overall if MLB, talent if not
  SELECT 'players_batting', 'power', p.rating_date, c.rating_date, prior.power, cur.power, (cur.power - prior.power), 5, (ABS(cur.power - prior.power) >= 5) FROM current_heap c CROSS JOIN prior_heap p CROSS JOIN player_info pl JOIN players_batting cur ON cur.rating_id = c.rating_id JOIN players_batting prior ON prior.rating_id = p.rating_id WHERE pl.position <> 'P' AND c.league_id = 203
  UNION ALL
  SELECT 'players_batting_talent', 'power', p.rating_date, c.rating_date, prior.power, cur.power, (cur.power - prior.power), 10, (ABS(cur.power - prior.power) >= 10) FROM current_heap c CROSS JOIN prior_heap p CROSS JOIN player_info pl JOIN players_batting_talent cur ON cur.rating_id = c.rating_id JOIN players_batting_talent prior ON prior.rating_id = p.rating_id WHERE pl.position <> 'P' AND c.league_id <> 203
  UNION ALL

  -- eye: overall if MLB, talent if not
  SELECT 'players_batting', 'eye', p.rating_date, c.rating_date, prior.eye, cur.eye, (cur.eye - prior.eye), 5, (ABS(cur.eye - prior.eye) >= 5) FROM current_heap c CROSS JOIN prior_heap p CROSS JOIN player_info pl JOIN players_batting cur ON cur.rating_id = c.rating_id JOIN players_batting prior ON prior.rating_id = p.rating_id WHERE pl.position <> 'P' AND c.league_id = 203
  UNION ALL
  SELECT 'players_batting_talent', 'eye', p.rating_date, c.rating_date, prior.eye, cur.eye, (cur.eye - prior.eye), 10, (ABS(cur.eye - prior.eye) >= 10) FROM current_heap c CROSS JOIN prior_heap p CROSS JOIN player_info pl JOIN players_batting_talent cur ON cur.rating_id = c.rating_id JOIN players_batting_talent prior ON prior.rating_id = p.rating_id WHERE pl.position <> 'P' AND c.league_id <> 203
  UNION ALL

  -- speed: always overall, position players only
  SELECT 'players_basepath', 'speed', p.rating_date, c.rating_date, prior.speed, cur.speed, (cur.speed - prior.speed), 5, (ABS(cur.speed - prior.speed) >= 5) FROM current_heap c CROSS JOIN prior_heap p CROSS JOIN player_info pl JOIN players_basepath cur ON cur.rating_id = c.rating_id JOIN players_basepath prior ON prior.rating_id = p.rating_id WHERE pl.position <> 'P'
  UNION ALL

  -- defense: always overall, position players only
  SELECT 'players_fielding', 'infield_range', p.rating_date, c.rating_date, prior.infield_range, cur.infield_range, (cur.infield_range - prior.infield_range), 5, (ABS(cur.infield_range - prior.infield_range) >= 5) FROM current_heap c CROSS JOIN prior_heap p CROSS JOIN player_info pl JOIN players_fielding cur ON cur.rating_id = c.rating_id JOIN players_fielding prior ON prior.rating_id = p.rating_id WHERE pl.position <> 'P'
  UNION ALL
  SELECT 'players_fielding', 'outfield_range', p.rating_date, c.rating_date, prior.outfield_range, cur.outfield_range, (cur.outfield_range - prior.outfield_range), 5, (ABS(cur.outfield_range - prior.outfield_range) >= 5) FROM current_heap c CROSS JOIN prior_heap p CROSS JOIN player_info pl JOIN players_fielding cur ON cur.rating_id = c.rating_id JOIN players_fielding prior ON prior.rating_id = p.rating_id WHERE pl.position <> 'P'
  UNION ALL
  SELECT 'players_fielding', 'catcher_framing', p.rating_date, c.rating_date, prior.catcher_framing, cur.catcher_framing, (cur.catcher_framing - prior.catcher_framing), 5, (ABS(cur.catcher_framing - prior.catcher_framing) >= 5) FROM current_heap c CROSS JOIN prior_heap p CROSS JOIN player_info pl JOIN players_fielding cur ON cur.rating_id = c.rating_id JOIN players_fielding prior ON prior.rating_id = p.rating_id WHERE pl.position <> 'P'
  UNION ALL

  -- ============================== PITCHING (pitchers) ==============================

  -- stuff: overall if MLB, talent if not
  SELECT 'players_pitching', 'stuff', p.rating_date, c.rating_date, prior.stuff, cur.stuff, (cur.stuff - prior.stuff), 5, (ABS(cur.stuff - prior.stuff) >= 5) FROM current_heap c CROSS JOIN prior_heap p CROSS JOIN player_info pl JOIN players_pitching cur ON cur.rating_id = c.rating_id JOIN players_pitching prior ON prior.rating_id = p.rating_id WHERE pl.position = 'P' AND c.league_id = 203
  UNION ALL
  SELECT 'players_pitching_talent', 'stuff', p.rating_date, c.rating_date, prior.stuff, cur.stuff, (cur.stuff - prior.stuff), 10, (ABS(cur.stuff - prior.stuff) >= 10) FROM current_heap c CROSS JOIN prior_heap p CROSS JOIN player_info pl JOIN players_pitching_talent cur ON cur.rating_id = c.rating_id JOIN players_pitching_talent prior ON prior.rating_id = p.rating_id WHERE pl.position = 'P' AND c.league_id <> 203
  UNION ALL

  -- movement: overall if MLB, talent if not
  SELECT 'players_pitching', 'movement', p.rating_date, c.rating_date, prior.movement, cur.movement, (cur.movement - prior.movement), 5, (ABS(cur.movement - prior.movement) >= 5) FROM current_heap c CROSS JOIN prior_heap p CROSS JOIN player_info pl JOIN players_pitching cur ON cur.rating_id = c.rating_id JOIN players_pitching prior ON prior.rating_id = p.rating_id WHERE pl.position = 'P' AND c.league_id = 203
  UNION ALL
  SELECT 'players_pitching_talent', 'movement', p.rating_date, c.rating_date, prior.movement, cur.movement, (cur.movement - prior.movement), 10, (ABS(cur.movement - prior.movement) >= 10) FROM current_heap c CROSS JOIN prior_heap p CROSS JOIN player_info pl JOIN players_pitching_talent cur ON cur.rating_id = c.rating_id JOIN players_pitching_talent prior ON prior.rating_id = p.rating_id WHERE pl.position = 'P' AND c.league_id <> 203
  UNION ALL

  -- control: overall if MLB, talent if not
  SELECT 'players_pitching', 'control', p.rating_date, c.rating_date, prior.control, cur.control, (cur.control - prior.control), 5, (ABS(cur.control - prior.control) >= 5) FROM current_heap c CROSS JOIN prior_heap p CROSS JOIN player_info pl JOIN players_pitching cur ON cur.rating_id = c.rating_id JOIN players_pitching prior ON prior.rating_id = p.rating_id WHERE pl.position = 'P' AND c.league_id = 203
  UNION ALL
  SELECT 'players_pitching_talent', 'control', p.rating_date, c.rating_date, prior.control, cur.control, (cur.control - prior.control), 10, (ABS(cur.control - prior.control) >= 10) FROM current_heap c CROSS JOIN prior_heap p CROSS JOIN player_info pl JOIN players_pitching_talent cur ON cur.rating_id = c.rating_id JOIN players_pitching_talent prior ON prior.rating_id = p.rating_id WHERE pl.position = 'P' AND c.league_id <> 203
  UNION ALL

  -- velocity: always overall, pitchers only, no talent counterpart exists
  SELECT 'players_pitching', 'velocity', p.rating_date, c.rating_date, prior.velocity, cur.velocity, (cur.velocity - prior.velocity), 5, (ABS(cur.velocity - prior.velocity) >= 5) FROM current_heap c CROSS JOIN prior_heap p CROSS JOIN player_info pl JOIN players_pitching cur ON cur.rating_id = c.rating_id JOIN players_pitching prior ON prior.rating_id = p.rating_id WHERE pl.position = 'P'
  UNION ALL

  -- stamina: always overall, pitchers only, no talent counterpart exists
  SELECT 'players_pitching', 'stamina', p.rating_date, c.rating_date, prior.stamina, cur.stamina, (cur.stamina - prior.stamina), 5, (ABS(cur.stamina - prior.stamina) >= 5) FROM current_heap c CROSS JOIN prior_heap p CROSS JOIN player_info pl JOIN players_pitching cur ON cur.rating_id = c.rating_id JOIN players_pitching prior ON prior.rating_id = p.rating_id WHERE pl.position = 'P'

) AS trends
ORDER BY table_name, column_name;
