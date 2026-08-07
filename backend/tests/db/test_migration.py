from app.db import migration as migration_module

# inject_db_path() was the SQLite-era templating function; it's been fully
# removed (see the commented-out stub at the top of migration.py) in favor
# of inject_heap_date(), the only templating this pipeline does today.


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
