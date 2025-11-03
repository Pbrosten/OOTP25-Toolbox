# def inject_db_path(template: str, db_path: str) -> str:
#     return template.replace("{{STAGING_DB_PATH}}", db_path)


def inject_heap_date(template: str, heap_date: list) -> str:
    return template.replace("{{HEAP_DATE}}", f"{heap_date[1]}-{heap_date[2]}-1")
