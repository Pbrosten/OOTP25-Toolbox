-- t_* columns (ticket 0086): players_pitching_talent's ceiling grades,
-- used to run PitcherProjection a second time per rating (see
-- app/db/projection.py's process_pitcher) for the "potential" percentile
-- bars. stamina/hold have no talent counterpart -- pp.stamina/pp.hold
-- stay shared between the current and potential runs.
SELECT
    r.rating_id,
    pp.role, pp.stuff, pp.control, pp.pbabip, pp.hra, pp.stamina, pp.hold,
    p.prone_overall,
    pt.stuff AS t_stuff, pt.control AS t_control,
    pt.pbabip AS t_pbabip, pt.hra AS t_hra
FROM players AS p
JOIN players_rating AS r ON p.player_id = r.player_id
JOIN players_pitching AS pp ON r.rating_id = pp.rating_id
JOIN players_pitching_talent AS pt ON r.rating_id = pt.rating_id
WHERE r.rating_date = '{{HEAP_DATE}}';
