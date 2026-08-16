-- Prospect FV/value calc inputs for a single heap (ticket 0075): the same
-- prospect-eligible candidate set get_prospects.sql's prospect_candidates
-- CTE filters to (age < 26, non-MLB affiliate or zero-service MLB rookie,
-- excluding level 5/team_id 999 -- see ticket 0043's Design choices),
-- restricted to this heap's own rating_date via {{HEAP_DATE}} templating
-- (matching get_projection_inputs.sql/get_pitcher_projection_inputs.sql)
-- rather than "latest rating" -- called once per short heap during
-- update-db, not at request time.
--
-- Returns one row per candidate with every raw column ticket 0068's calc
-- needs to build both a talent-ceiling and a current-form projection
-- input, for whichever side (batting/pitching) matches players.position --
-- same shape and explicit-position-gate convention as get_prospects.sql,
-- so app/db/projection.py's process_prospect() can reuse the same
-- input-builder helpers app/api/prospects.py already uses.
SELECT
    p.player_id, p.position, p.bats, p.birth_date, p.prone_overall,
    r.rating_id, r.rating_date,

    b.babip AS bat_babip, b.gap AS bat_gap, b.eye AS bat_eye,
    b.power AS bat_power, b.strikeouts AS bat_strikeouts,
    bt.babip AS bat_babip_talent, bt.gap AS bat_gap_talent,
    bt.eye AS bat_eye_talent, bt.power AS bat_power_talent,
    bt.strikeouts AS bat_strikeouts_talent,

    bp.speed, bp.steal, bp.baserunning,

    fp.pos2, fp.pos3, fp.pos4, fp.pos5, fp.pos6, fp.pos7, fp.pos8, fp.pos9,
    fpt.pos2 AS pos2_talent, fpt.pos3 AS pos3_talent, fpt.pos4 AS pos4_talent,
    fpt.pos5 AS pos5_talent, fpt.pos6 AS pos6_talent, fpt.pos7 AS pos7_talent,
    fpt.pos8 AS pos8_talent, fpt.pos9 AS pos9_talent,

    pp.role AS pitch_role, pp.stuff AS pitch_stuff, pp.control AS pitch_control,
    pp.pbabip AS pitch_pbabip, pp.hra AS pitch_hra, pp.stamina AS pitch_stamina,
    pp.hold AS pitch_hold,
    ppt.stuff AS pitch_stuff_talent, ppt.control AS pitch_control_talent,
    ppt.pbabip AS pitch_pbabip_talent, ppt.hra AS pitch_hra_talent
FROM players p
JOIN teams t ON t.team_id = p.team_id
LEFT JOIN players_service_time st ON st.player_id = p.player_id
JOIN players_rating r ON r.player_id = p.player_id AND r.rating_date = '{{HEAP_DATE}}'
LEFT JOIN players_batting b ON b.rating_id = r.rating_id
LEFT JOIN players_batting_talent bt ON bt.rating_id = r.rating_id
LEFT JOIN players_basepath bp ON bp.rating_id = r.rating_id
LEFT JOIN players_fielding_position fp ON fp.rating_id = r.rating_id
LEFT JOIN players_fielding_position_talent fpt ON fpt.rating_id = r.rating_id
LEFT JOIN players_pitching pp ON pp.rating_id = r.rating_id
LEFT JOIN players_pitching_talent ppt ON ppt.rating_id = r.rating_id
WHERE p.retired = 0
  AND t.team_id != 999
  AND t.level != 5
  AND p.age < 26
  AND (
      t.level != 1
      OR COALESCE(st.mlb_service_years, 0) = 0
  );
