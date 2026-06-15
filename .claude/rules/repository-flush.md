---
paths:
  - "**/mcr_meeting/app/db/*_repository.py"
---

# Repository flush rule (`*_repository.py`)

## Default: no `db.flush()` — let `UnitOfWork` flush

Write functions should `db.add(obj)` and return. Don't call `db.flush()`. The single flush and commit happen in `UnitOfWork.commit()` (`db/unit_of_work.py`), the only place that maps DB write errors to client errors via `raise_db_write_error` (`db/db_errors.py`): `DataError` to 422, `IntegrityError` to 409, anything else to 500.

```python
def save_thing(thing: Thing) -> Thing:
    db = get_db_session_ctx()
    db.add(thing)
    return thing
```

A DB-generated id stays readable after the `with UnitOfWork():` block, because the session reloads expired attributes after commit. Needing the id after the block is not a reason to flush.

## Flush only when code inside the block needs the write result before commit

The one legitimate case: code inside the same `UnitOfWork` block needs the result before the transaction commits. Audited example: `save_deliverable` (`deliverable_repository.py`), called by `_persist_and_dispatch` (`use_cases/request_deliverable.py`), flushes to read `deliverable.id` for Celery dispatch and to catch the concurrent-insert `IntegrityError` before commit.

If you flush, you own the error translation. An error at `flush()` is raised inside the `with UnitOfWork()` block, where `__exit__` only rolls back — it does not translate — so a raw `DataError`/`IntegrityError` escapes as a 500. A flushing repository must wrap the flush and raise a translated exception (reuse `raise_db_write_error`, or a specific one like `DeliverableConcurrentlyCreatedException`):

```python
try:
    db.flush()
except IntegrityError as exc:
    raise DeliverableConcurrentlyCreatedException(...) from exc
```

Check: is the flushed result used before the block exits? If only the caller uses it, after the block, drop the flush.
