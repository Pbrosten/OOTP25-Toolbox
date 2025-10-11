SELECT
    rating_id,
    rating_date
FROM players_rating
WHERE player_id = ?
ORDER BY rating_date DESC;
