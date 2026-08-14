-- Player rating delta/trend query (ticket 0050): for a given player,
-- compares their latest heap's ratings against the ratings from 3 heaps
-- prior (their own heap sequence, not a fixed calendar offset -- see
-- ticket 0050's Design choices for why: players can be absent from a
-- heap, e.g. free agents or players pruned by ticket 0046, so a fixed
-- 3-month lookback would under/over-count).
--
-- Returns one row per rating column across the 8 in-scope tables (5
-- "overall"/current-ability tables at a +/-5 threshold, 3 "talent"/
-- potential tables at a +/-10 threshold). If the player has fewer than 4
-- recorded heaps, prior_heap is empty and this returns zero rows (not an
-- error -- the caller distinguishes "no players_rating rows at all" via a
-- separate existence check, see app/api/ratings.py).
WITH sequenced AS (
  SELECT
    rating_id,
    rating_date,
    ROW_NUMBER() OVER (ORDER BY rating_date) AS heap_seq
  FROM players_rating
  WHERE player_id = %(player_id)s
),
current_heap AS (
  SELECT rating_id, rating_date, heap_seq
  FROM sequenced
  ORDER BY heap_seq DESC
  LIMIT 1
),
prior_heap AS (
  SELECT s.rating_id, s.rating_date
  FROM sequenced AS s
  JOIN current_heap AS c ON s.heap_seq = c.heap_seq - 3
)

SELECT * FROM (

  -- ============================== OVERALL (threshold 5) ==============================

  -- players_batting
  SELECT 'players_batting' AS table_name, 'contact' AS column_name, p.rating_date AS from_date, c.rating_date AS `to_date`, prior.contact AS from_value, cur.contact AS to_value, (cur.contact - prior.contact) AS delta, 5 AS threshold, (ABS(cur.contact - prior.contact) >= 5) AS exceeded FROM current_heap c CROSS JOIN prior_heap p JOIN players_batting cur ON cur.rating_id = c.rating_id JOIN players_batting prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_batting', 'gap', p.rating_date, c.rating_date, prior.gap, cur.gap, (cur.gap - prior.gap), 5, (ABS(cur.gap - prior.gap) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_batting cur ON cur.rating_id = c.rating_id JOIN players_batting prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_batting', 'eye', p.rating_date, c.rating_date, prior.eye, cur.eye, (cur.eye - prior.eye), 5, (ABS(cur.eye - prior.eye) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_batting cur ON cur.rating_id = c.rating_id JOIN players_batting prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_batting', 'strikeouts', p.rating_date, c.rating_date, prior.strikeouts, cur.strikeouts, (cur.strikeouts - prior.strikeouts), 5, (ABS(cur.strikeouts - prior.strikeouts) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_batting cur ON cur.rating_id = c.rating_id JOIN players_batting prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_batting', 'power', p.rating_date, c.rating_date, prior.power, cur.power, (cur.power - prior.power), 5, (ABS(cur.power - prior.power) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_batting cur ON cur.rating_id = c.rating_id JOIN players_batting prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_batting', 'babip', p.rating_date, c.rating_date, prior.babip, cur.babip, (cur.babip - prior.babip), 5, (ABS(cur.babip - prior.babip) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_batting cur ON cur.rating_id = c.rating_id JOIN players_batting prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_batting', 'bunt', p.rating_date, c.rating_date, prior.bunt, cur.bunt, (cur.bunt - prior.bunt), 5, (ABS(cur.bunt - prior.bunt) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_batting cur ON cur.rating_id = c.rating_id JOIN players_batting prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_batting', 'bunt_for_hit', p.rating_date, c.rating_date, prior.bunt_for_hit, cur.bunt_for_hit, (cur.bunt_for_hit - prior.bunt_for_hit), 5, (ABS(cur.bunt_for_hit - prior.bunt_for_hit) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_batting cur ON cur.rating_id = c.rating_id JOIN players_batting prior ON prior.rating_id = p.rating_id
  UNION ALL

  -- players_pitching (role excluded -- it's a role code, not a rating)
  SELECT 'players_pitching', 'stuff', p.rating_date, c.rating_date, prior.stuff, cur.stuff, (cur.stuff - prior.stuff), 5, (ABS(cur.stuff - prior.stuff) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_pitching cur ON cur.rating_id = c.rating_id JOIN players_pitching prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_pitching', 'movement', p.rating_date, c.rating_date, prior.movement, cur.movement, (cur.movement - prior.movement), 5, (ABS(cur.movement - prior.movement) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_pitching cur ON cur.rating_id = c.rating_id JOIN players_pitching prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_pitching', 'hra', p.rating_date, c.rating_date, prior.hra, cur.hra, (cur.hra - prior.hra), 5, (ABS(cur.hra - prior.hra) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_pitching cur ON cur.rating_id = c.rating_id JOIN players_pitching prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_pitching', 'pbabip', p.rating_date, c.rating_date, prior.pbabip, cur.pbabip, (cur.pbabip - prior.pbabip), 5, (ABS(cur.pbabip - prior.pbabip) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_pitching cur ON cur.rating_id = c.rating_id JOIN players_pitching prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_pitching', 'control', p.rating_date, c.rating_date, prior.control, cur.control, (cur.control - prior.control), 5, (ABS(cur.control - prior.control) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_pitching cur ON cur.rating_id = c.rating_id JOIN players_pitching prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_pitching', 'balk', p.rating_date, c.rating_date, prior.balk, cur.balk, (cur.balk - prior.balk), 5, (ABS(cur.balk - prior.balk) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_pitching cur ON cur.rating_id = c.rating_id JOIN players_pitching prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_pitching', 'hp', p.rating_date, c.rating_date, prior.hp, cur.hp, (cur.hp - prior.hp), 5, (ABS(cur.hp - prior.hp) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_pitching cur ON cur.rating_id = c.rating_id JOIN players_pitching prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_pitching', 'wild_pitch', p.rating_date, c.rating_date, prior.wild_pitch, cur.wild_pitch, (cur.wild_pitch - prior.wild_pitch), 5, (ABS(cur.wild_pitch - prior.wild_pitch) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_pitching cur ON cur.rating_id = c.rating_id JOIN players_pitching prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_pitching', 'velocity', p.rating_date, c.rating_date, prior.velocity, cur.velocity, (cur.velocity - prior.velocity), 5, (ABS(cur.velocity - prior.velocity) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_pitching cur ON cur.rating_id = c.rating_id JOIN players_pitching prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_pitching', 'arm_slot', p.rating_date, c.rating_date, prior.arm_slot, cur.arm_slot, (cur.arm_slot - prior.arm_slot), 5, (ABS(cur.arm_slot - prior.arm_slot) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_pitching cur ON cur.rating_id = c.rating_id JOIN players_pitching prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_pitching', 'stamina', p.rating_date, c.rating_date, prior.stamina, cur.stamina, (cur.stamina - prior.stamina), 5, (ABS(cur.stamina - prior.stamina) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_pitching cur ON cur.rating_id = c.rating_id JOIN players_pitching prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_pitching', 'ground_fly', p.rating_date, c.rating_date, prior.ground_fly, cur.ground_fly, (cur.ground_fly - prior.ground_fly), 5, (ABS(cur.ground_fly - prior.ground_fly) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_pitching cur ON cur.rating_id = c.rating_id JOIN players_pitching prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_pitching', 'hold', p.rating_date, c.rating_date, prior.hold, cur.hold, (cur.hold - prior.hold), 5, (ABS(cur.hold - prior.hold) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_pitching cur ON cur.rating_id = c.rating_id JOIN players_pitching prior ON prior.rating_id = p.rating_id
  UNION ALL

  -- players_fielding
  SELECT 'players_fielding', 'catcher_arm', p.rating_date, c.rating_date, prior.catcher_arm, cur.catcher_arm, (cur.catcher_arm - prior.catcher_arm), 5, (ABS(cur.catcher_arm - prior.catcher_arm) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_fielding cur ON cur.rating_id = c.rating_id JOIN players_fielding prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_fielding', 'catcher_ability', p.rating_date, c.rating_date, prior.catcher_ability, cur.catcher_ability, (cur.catcher_ability - prior.catcher_ability), 5, (ABS(cur.catcher_ability - prior.catcher_ability) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_fielding cur ON cur.rating_id = c.rating_id JOIN players_fielding prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_fielding', 'catcher_framing', p.rating_date, c.rating_date, prior.catcher_framing, cur.catcher_framing, (cur.catcher_framing - prior.catcher_framing), 5, (ABS(cur.catcher_framing - prior.catcher_framing) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_fielding cur ON cur.rating_id = c.rating_id JOIN players_fielding prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_fielding', 'infield_range', p.rating_date, c.rating_date, prior.infield_range, cur.infield_range, (cur.infield_range - prior.infield_range), 5, (ABS(cur.infield_range - prior.infield_range) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_fielding cur ON cur.rating_id = c.rating_id JOIN players_fielding prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_fielding', 'infield_arm', p.rating_date, c.rating_date, prior.infield_arm, cur.infield_arm, (cur.infield_arm - prior.infield_arm), 5, (ABS(cur.infield_arm - prior.infield_arm) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_fielding cur ON cur.rating_id = c.rating_id JOIN players_fielding prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_fielding', 'infield_doubleplay', p.rating_date, c.rating_date, prior.infield_doubleplay, cur.infield_doubleplay, (cur.infield_doubleplay - prior.infield_doubleplay), 5, (ABS(cur.infield_doubleplay - prior.infield_doubleplay) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_fielding cur ON cur.rating_id = c.rating_id JOIN players_fielding prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_fielding', 'infield_error', p.rating_date, c.rating_date, prior.infield_error, cur.infield_error, (cur.infield_error - prior.infield_error), 5, (ABS(cur.infield_error - prior.infield_error) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_fielding cur ON cur.rating_id = c.rating_id JOIN players_fielding prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_fielding', 'outfield_range', p.rating_date, c.rating_date, prior.outfield_range, cur.outfield_range, (cur.outfield_range - prior.outfield_range), 5, (ABS(cur.outfield_range - prior.outfield_range) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_fielding cur ON cur.rating_id = c.rating_id JOIN players_fielding prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_fielding', 'outfield_arm', p.rating_date, c.rating_date, prior.outfield_arm, cur.outfield_arm, (cur.outfield_arm - prior.outfield_arm), 5, (ABS(cur.outfield_arm - prior.outfield_arm) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_fielding cur ON cur.rating_id = c.rating_id JOIN players_fielding prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_fielding', 'outfield_error', p.rating_date, c.rating_date, prior.outfield_error, cur.outfield_error, (cur.outfield_error - prior.outfield_error), 5, (ABS(cur.outfield_error - prior.outfield_error) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_fielding cur ON cur.rating_id = c.rating_id JOIN players_fielding prior ON prior.rating_id = p.rating_id
  UNION ALL

  -- players_basepath
  SELECT 'players_basepath', 'speed', p.rating_date, c.rating_date, prior.speed, cur.speed, (cur.speed - prior.speed), 5, (ABS(cur.speed - prior.speed) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_basepath cur ON cur.rating_id = c.rating_id JOIN players_basepath prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_basepath', 'steal_rate', p.rating_date, c.rating_date, prior.steal_rate, cur.steal_rate, (cur.steal_rate - prior.steal_rate), 5, (ABS(cur.steal_rate - prior.steal_rate) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_basepath cur ON cur.rating_id = c.rating_id JOIN players_basepath prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_basepath', 'steal', p.rating_date, c.rating_date, prior.steal, cur.steal, (cur.steal - prior.steal), 5, (ABS(cur.steal - prior.steal) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_basepath cur ON cur.rating_id = c.rating_id JOIN players_basepath prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_basepath', 'baserunning', p.rating_date, c.rating_date, prior.baserunning, cur.baserunning, (cur.baserunning - prior.baserunning), 5, (ABS(cur.baserunning - prior.baserunning) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_basepath cur ON cur.rating_id = c.rating_id JOIN players_basepath prior ON prior.rating_id = p.rating_id
  UNION ALL

  -- players_fielding_position
  SELECT 'players_fielding_position', 'pos1', p.rating_date, c.rating_date, prior.pos1, cur.pos1, (cur.pos1 - prior.pos1), 5, (ABS(cur.pos1 - prior.pos1) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_fielding_position cur ON cur.rating_id = c.rating_id JOIN players_fielding_position prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_fielding_position', 'pos2', p.rating_date, c.rating_date, prior.pos2, cur.pos2, (cur.pos2 - prior.pos2), 5, (ABS(cur.pos2 - prior.pos2) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_fielding_position cur ON cur.rating_id = c.rating_id JOIN players_fielding_position prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_fielding_position', 'pos3', p.rating_date, c.rating_date, prior.pos3, cur.pos3, (cur.pos3 - prior.pos3), 5, (ABS(cur.pos3 - prior.pos3) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_fielding_position cur ON cur.rating_id = c.rating_id JOIN players_fielding_position prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_fielding_position', 'pos4', p.rating_date, c.rating_date, prior.pos4, cur.pos4, (cur.pos4 - prior.pos4), 5, (ABS(cur.pos4 - prior.pos4) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_fielding_position cur ON cur.rating_id = c.rating_id JOIN players_fielding_position prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_fielding_position', 'pos5', p.rating_date, c.rating_date, prior.pos5, cur.pos5, (cur.pos5 - prior.pos5), 5, (ABS(cur.pos5 - prior.pos5) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_fielding_position cur ON cur.rating_id = c.rating_id JOIN players_fielding_position prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_fielding_position', 'pos6', p.rating_date, c.rating_date, prior.pos6, cur.pos6, (cur.pos6 - prior.pos6), 5, (ABS(cur.pos6 - prior.pos6) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_fielding_position cur ON cur.rating_id = c.rating_id JOIN players_fielding_position prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_fielding_position', 'pos7', p.rating_date, c.rating_date, prior.pos7, cur.pos7, (cur.pos7 - prior.pos7), 5, (ABS(cur.pos7 - prior.pos7) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_fielding_position cur ON cur.rating_id = c.rating_id JOIN players_fielding_position prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_fielding_position', 'pos8', p.rating_date, c.rating_date, prior.pos8, cur.pos8, (cur.pos8 - prior.pos8), 5, (ABS(cur.pos8 - prior.pos8) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_fielding_position cur ON cur.rating_id = c.rating_id JOIN players_fielding_position prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_fielding_position', 'pos9', p.rating_date, c.rating_date, prior.pos9, cur.pos9, (cur.pos9 - prior.pos9), 5, (ABS(cur.pos9 - prior.pos9) >= 5) FROM current_heap c CROSS JOIN prior_heap p JOIN players_fielding_position cur ON cur.rating_id = c.rating_id JOIN players_fielding_position prior ON prior.rating_id = p.rating_id
  UNION ALL

  -- ============================== TALENT / POTENTIAL (threshold 10) ==============================

  -- players_batting_talent
  SELECT 'players_batting_talent', 'contact', p.rating_date, c.rating_date, prior.contact, cur.contact, (cur.contact - prior.contact), 10, (ABS(cur.contact - prior.contact) >= 10) FROM current_heap c CROSS JOIN prior_heap p JOIN players_batting_talent cur ON cur.rating_id = c.rating_id JOIN players_batting_talent prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_batting_talent', 'gap', p.rating_date, c.rating_date, prior.gap, cur.gap, (cur.gap - prior.gap), 10, (ABS(cur.gap - prior.gap) >= 10) FROM current_heap c CROSS JOIN prior_heap p JOIN players_batting_talent cur ON cur.rating_id = c.rating_id JOIN players_batting_talent prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_batting_talent', 'eye', p.rating_date, c.rating_date, prior.eye, cur.eye, (cur.eye - prior.eye), 10, (ABS(cur.eye - prior.eye) >= 10) FROM current_heap c CROSS JOIN prior_heap p JOIN players_batting_talent cur ON cur.rating_id = c.rating_id JOIN players_batting_talent prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_batting_talent', 'strikeouts', p.rating_date, c.rating_date, prior.strikeouts, cur.strikeouts, (cur.strikeouts - prior.strikeouts), 10, (ABS(cur.strikeouts - prior.strikeouts) >= 10) FROM current_heap c CROSS JOIN prior_heap p JOIN players_batting_talent cur ON cur.rating_id = c.rating_id JOIN players_batting_talent prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_batting_talent', 'power', p.rating_date, c.rating_date, prior.power, cur.power, (cur.power - prior.power), 10, (ABS(cur.power - prior.power) >= 10) FROM current_heap c CROSS JOIN prior_heap p JOIN players_batting_talent cur ON cur.rating_id = c.rating_id JOIN players_batting_talent prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_batting_talent', 'babip', p.rating_date, c.rating_date, prior.babip, cur.babip, (cur.babip - prior.babip), 10, (ABS(cur.babip - prior.babip) >= 10) FROM current_heap c CROSS JOIN prior_heap p JOIN players_batting_talent cur ON cur.rating_id = c.rating_id JOIN players_batting_talent prior ON prior.rating_id = p.rating_id
  UNION ALL

  -- players_pitching_talent
  SELECT 'players_pitching_talent', 'stuff', p.rating_date, c.rating_date, prior.stuff, cur.stuff, (cur.stuff - prior.stuff), 10, (ABS(cur.stuff - prior.stuff) >= 10) FROM current_heap c CROSS JOIN prior_heap p JOIN players_pitching_talent cur ON cur.rating_id = c.rating_id JOIN players_pitching_talent prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_pitching_talent', 'movement', p.rating_date, c.rating_date, prior.movement, cur.movement, (cur.movement - prior.movement), 10, (ABS(cur.movement - prior.movement) >= 10) FROM current_heap c CROSS JOIN prior_heap p JOIN players_pitching_talent cur ON cur.rating_id = c.rating_id JOIN players_pitching_talent prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_pitching_talent', 'hra', p.rating_date, c.rating_date, prior.hra, cur.hra, (cur.hra - prior.hra), 10, (ABS(cur.hra - prior.hra) >= 10) FROM current_heap c CROSS JOIN prior_heap p JOIN players_pitching_talent cur ON cur.rating_id = c.rating_id JOIN players_pitching_talent prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_pitching_talent', 'pbabip', p.rating_date, c.rating_date, prior.pbabip, cur.pbabip, (cur.pbabip - prior.pbabip), 10, (ABS(cur.pbabip - prior.pbabip) >= 10) FROM current_heap c CROSS JOIN prior_heap p JOIN players_pitching_talent cur ON cur.rating_id = c.rating_id JOIN players_pitching_talent prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_pitching_talent', 'control', p.rating_date, c.rating_date, prior.control, cur.control, (cur.control - prior.control), 10, (ABS(cur.control - prior.control) >= 10) FROM current_heap c CROSS JOIN prior_heap p JOIN players_pitching_talent cur ON cur.rating_id = c.rating_id JOIN players_pitching_talent prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_pitching_talent', 'balk', p.rating_date, c.rating_date, prior.balk, cur.balk, (cur.balk - prior.balk), 10, (ABS(cur.balk - prior.balk) >= 10) FROM current_heap c CROSS JOIN prior_heap p JOIN players_pitching_talent cur ON cur.rating_id = c.rating_id JOIN players_pitching_talent prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_pitching_talent', 'hp', p.rating_date, c.rating_date, prior.hp, cur.hp, (cur.hp - prior.hp), 10, (ABS(cur.hp - prior.hp) >= 10) FROM current_heap c CROSS JOIN prior_heap p JOIN players_pitching_talent cur ON cur.rating_id = c.rating_id JOIN players_pitching_talent prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_pitching_talent', 'wild_pitch', p.rating_date, c.rating_date, prior.wild_pitch, cur.wild_pitch, (cur.wild_pitch - prior.wild_pitch), 10, (ABS(cur.wild_pitch - prior.wild_pitch) >= 10) FROM current_heap c CROSS JOIN prior_heap p JOIN players_pitching_talent cur ON cur.rating_id = c.rating_id JOIN players_pitching_talent prior ON prior.rating_id = p.rating_id
  UNION ALL

  -- players_fielding_position_talent
  SELECT 'players_fielding_position_talent', 'pos1', p.rating_date, c.rating_date, prior.pos1, cur.pos1, (cur.pos1 - prior.pos1), 10, (ABS(cur.pos1 - prior.pos1) >= 10) FROM current_heap c CROSS JOIN prior_heap p JOIN players_fielding_position_talent cur ON cur.rating_id = c.rating_id JOIN players_fielding_position_talent prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_fielding_position_talent', 'pos2', p.rating_date, c.rating_date, prior.pos2, cur.pos2, (cur.pos2 - prior.pos2), 10, (ABS(cur.pos2 - prior.pos2) >= 10) FROM current_heap c CROSS JOIN prior_heap p JOIN players_fielding_position_talent cur ON cur.rating_id = c.rating_id JOIN players_fielding_position_talent prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_fielding_position_talent', 'pos3', p.rating_date, c.rating_date, prior.pos3, cur.pos3, (cur.pos3 - prior.pos3), 10, (ABS(cur.pos3 - prior.pos3) >= 10) FROM current_heap c CROSS JOIN prior_heap p JOIN players_fielding_position_talent cur ON cur.rating_id = c.rating_id JOIN players_fielding_position_talent prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_fielding_position_talent', 'pos4', p.rating_date, c.rating_date, prior.pos4, cur.pos4, (cur.pos4 - prior.pos4), 10, (ABS(cur.pos4 - prior.pos4) >= 10) FROM current_heap c CROSS JOIN prior_heap p JOIN players_fielding_position_talent cur ON cur.rating_id = c.rating_id JOIN players_fielding_position_talent prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_fielding_position_talent', 'pos5', p.rating_date, c.rating_date, prior.pos5, cur.pos5, (cur.pos5 - prior.pos5), 10, (ABS(cur.pos5 - prior.pos5) >= 10) FROM current_heap c CROSS JOIN prior_heap p JOIN players_fielding_position_talent cur ON cur.rating_id = c.rating_id JOIN players_fielding_position_talent prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_fielding_position_talent', 'pos6', p.rating_date, c.rating_date, prior.pos6, cur.pos6, (cur.pos6 - prior.pos6), 10, (ABS(cur.pos6 - prior.pos6) >= 10) FROM current_heap c CROSS JOIN prior_heap p JOIN players_fielding_position_talent cur ON cur.rating_id = c.rating_id JOIN players_fielding_position_talent prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_fielding_position_talent', 'pos7', p.rating_date, c.rating_date, prior.pos7, cur.pos7, (cur.pos7 - prior.pos7), 10, (ABS(cur.pos7 - prior.pos7) >= 10) FROM current_heap c CROSS JOIN prior_heap p JOIN players_fielding_position_talent cur ON cur.rating_id = c.rating_id JOIN players_fielding_position_talent prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_fielding_position_talent', 'pos8', p.rating_date, c.rating_date, prior.pos8, cur.pos8, (cur.pos8 - prior.pos8), 10, (ABS(cur.pos8 - prior.pos8) >= 10) FROM current_heap c CROSS JOIN prior_heap p JOIN players_fielding_position_talent cur ON cur.rating_id = c.rating_id JOIN players_fielding_position_talent prior ON prior.rating_id = p.rating_id
  UNION ALL
  SELECT 'players_fielding_position_talent', 'pos9', p.rating_date, c.rating_date, prior.pos9, cur.pos9, (cur.pos9 - prior.pos9), 10, (ABS(cur.pos9 - prior.pos9) >= 10) FROM current_heap c CROSS JOIN prior_heap p JOIN players_fielding_position_talent cur ON cur.rating_id = c.rating_id JOIN players_fielding_position_talent prior ON prior.rating_id = p.rating_id

) AS trends
ORDER BY table_name, column_name;
