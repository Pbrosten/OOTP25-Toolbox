import os
import re
from flask import current_app

DUMP_INCLUSION_LIST = [
    'cities', 'continents', 'divisions', 'language_data', 'languages',
    'league_history', 'leagues', 'nations', 'players.mysql',
    'players_batting', 'players_fielding', 'players_career',
    'players_contract', 'players_injury', 'players_pitching',
    'players_roster_status', 'players_salary_history', 'players_value',
    'team_affiliations', 'states', 'team_roster', 'teams.mysql',
    'trade_history'
]

def check_new_heaps():
    dump_path = current_app.config['DUMP_PATH']
    heaps = os.listdir(dump_path)

    valid_heaps = [
        heap for heap in heaps
        if "_" in heap and heap.split("_")[1].isdigit() and heap.split("_")[2].isdigit()
    ]

    sorted_heaps = sorted(valid_heaps, key=lambda h: (int(h.split("_")[1]), int(h.split("_")[2])))
    return [os.path.join(dump_path, heap, "mysql") for heap in sorted_heaps]

def fix_insert_ignore(sql: str) -> str:
    return re.sub(r'^insert\s+ignore', 'insert or ignore', sql, flags=re.IGNORECASE)

def sql_dump_to_staging(db, filepath, commit_every=100):
    with open(filepath, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            if line.startswith("#") or not line.strip():
                continue
            sql = fix_insert_ignore(line) if line.lower().startswith("insert ignore") else line
            db.executescript(sql)
            if i % commit_every == 0:
                db.commit()
        db.commit()
