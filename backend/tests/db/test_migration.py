import pytest
from app.db import migration as migration_module

def test_inject_db_path_replaces_placeholder():
    template = "Path is {{STAGGING_DB_PATH}} here."
    db_path = "/tmp/db.sqlite"
    result = migration_module.inject_db_path(template, db_path)
    assert result == f"Path is {db_path} here."

def test_inject_db_path_no_placeholder():
    template = "No placeholder here."
    db_path = "/tmp/db.sqlite"
    result = migration_module.inject_db_path(template, db_path)
    assert result == template

def test_inject_db_path_multiple_placeholders():
    template = "{{STAGGING_DB_PATH}} and {{STAGGING_DB_PATH}} again."
    db_path = "/tmp/db.sqlite"
    result = migration_module.inject_db_path(template, db_path)
    assert result == f"{db_path} and {db_path} again."

def test_inject_heap_date_replaces_placeholder():
    template = "Date is {{HEAP_DATE}}."
    heap_date = [2024, 7, 9]  # year, month, day
    result = migration_module.inject_heap_date(template, heap_date)
    assert result == "Date is 7-9-1."

def test_inject_heap_date_no_placeholder():
    template = "No date placeholder."
    heap_date = [2024, 7, 9]
    result = migration_module.inject_heap_date(template, heap_date)
    assert result == template

def test_inject_heap_date_multiple_placeholders():
    template = "{{HEAP_DATE}} and {{HEAP_DATE}} again."
    heap_date = [2024, 7, 9]
    result = migration_module.inject_heap_date(template, heap_date)
    assert result == "7-9-1 and 7-9-1 again."
