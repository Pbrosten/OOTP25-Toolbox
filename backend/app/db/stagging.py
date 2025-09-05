import os
import re
import sqlite3
from flask import current_app

DUMP_INCLUSION_LIST = [
    # 'cities', 'continents', 'divisions', 'language_data', 'languages',
    # 'league_history', 'leagues', 'nations',
    'players.mysql',
    'players_batting', 'players_fielding',
    # 'players_career',
    # 'players_contract', 'players_injury', 
    'players_pitching',
    # 'players_roster_status', 'players_salary_history', 'players_value',
    # 'team_affiliations', 'states', 'team_roster', 
    'teams.mysql',
    # 'trade_history'
]

def check_new_heaps():
    dump_path = current_app.config['DUMP_PATH']
    heaps = os.listdir(dump_path)

    valid_short_heaps = [
        heap for heap in heaps
        if "_" in heap and heap.split("_")[1].isdigit() and heap.split("_")[2].isdigit()
    ]
    valid_long_heaps = [
        heap for heap in heaps
        if "_" in heap and heap.split("_")[1].isdigit() and heap.split("_")[2]=="yearly"
    ]

    sorted_short_heaps = sorted(valid_short_heaps, key=lambda h: (int(h.split("_")[1]), int(h.split("_")[2])))
    sorted_long_heaps = sorted(valid_long_heaps, key=lambda h: (int(h.split("_")[1])))
    return [os.path.join(dump_path, heap, "mysql") for heap in sorted_short_heaps], [os.path.join(dump_path, heap, "mysql") for heap in sorted_long_heaps]

def clean_mysql_dump(sql: str) -> str:
    cleaned_lines = []
    for line in sql.splitlines():
        if line.strip().startswith("#"):
            continue
        # Convert insert ignore → INSERT OR IGNORE
        line = line.replace('insert ignore', 'INSERT OR IGNORE')
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)

def sql_dump_to_staging(db, filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        dump = clean_mysql_dump(f.read())

    try:
        db.executescript(dump)
        db.commit()
    except sqlite3.Error as e:
        print("SQLite Error during dump execution:", e)
        raise