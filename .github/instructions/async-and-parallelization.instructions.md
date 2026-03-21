---
description: Mandatory rules for async migration and parallelization of I/O-bound operations. Applies to all Python code in this service.
applyTo: "**/*.py"
---

<critical>Note: This is a living document and will be updated as we refine our processes. Always refer back to this for the latest guidelines. Update whenever necessary.</critical>

# Async & Parallelization Guidelines

This service is being migrated from synchronous pymongo to **async motor** as part of **M31: Async Migration**. All new code MUST be async-first. When modifying existing synchronous code, migrate it to async as part of the change.

---

## 1. Stack Migration Rules

### MongoDB: pymongo → motor

```toml
# BEFORE (pyproject.toml)
"pymongo>=4.12"

# AFTER
"motor>=3.6,<4"
```

- **motor** is the official async driver for MongoDB. It wraps pymongo and provides an async API.
- Use `motor.motor_asyncio.AsyncIOMotorClient` instead of `pymongo.MongoClient`.
- All repository methods that perform I/O MUST be `async def` and use `await`.

```python
# BEFORE
from pymongo import MongoClient
client = MongoClient(settings.mongo_uri)
result = collection.find_one({"_id": ObjectId(id)})

# AFTER
from motor.motor_asyncio import AsyncIOMotorClient
client = AsyncIOMotorClient(settings.mongo_uri)
result = await collection.find_one({"_id": ObjectId(id)})
```

### HTTP Clients: httpx sync → httpx.AsyncClient

```python
# BEFORE
resp = httpx.get(url, timeout=10.0)

# AFTER
async with httpx.AsyncClient() as client:
    resp = await client.get(url, timeout=10.0)
```

- Prefer **session-scoped `AsyncClient`** (via DI) over creating one per request.
- Set explicit `timeout` on every HTTP call.

### FastAPI Endpoints

```python
# BEFORE
@router.get("/items/{id}")
def get_item(id: str, service: ItemService = Depends(get_service)):
    return service.get(id)

# AFTER
@router.get("/items/{id}")
async def get_item(id: str, service: ItemService = Depends(get_service)):
    return await service.get(id)
```

- All endpoints that call async services MUST use `async def`.
- FastAPI runs `def` endpoints in a threadpool — after migration, there is no reason to keep sync endpoints.

---

## 2. Parallelization with `asyncio.gather()`

<critical>Whenever multiple independent I/O operations exist (DB queries, HTTP calls, file reads), they MUST be parallelized using `asyncio.gather()`. Sequential `await` in a loop is a code-smell that should be flagged and refactored.</critical>

### Pattern: Sequential loop → gather

```python
# ❌ WRONG — sequential awaits in a loop
results = []
for item_id in item_ids:
    result = await service.get(item_id)
    results.append(result)

# ✅ CORRECT — parallel gather
results = await asyncio.gather(
    *[service.get(item_id) for item_id in item_ids]
)
```

### Pattern: Multiple independent calls → gather

```python
# ❌ WRONG — sequential independent calls
contracts = await contracts_client.list()
ships = await ships_client.list()
locations = await maps_client.list()

# ✅ CORRECT — parallel independent calls
contracts, ships, locations = await asyncio.gather(
    contracts_client.list(),
    ships_client.list(),
    maps_client.list(),
)
```

### Error handling with gather

```python
results = await asyncio.gather(*tasks, return_exceptions=True)
successes = [r for r in results if not isinstance(r, Exception)]
failures = [r for r in results if isinstance(r, Exception)]
for err in failures:
    logger.error("Task failed: %s", err)
```

- Use `return_exceptions=True` when partial failures are acceptable.
- Without it, the first exception cancels all other tasks — use this when all-or-nothing semantics are needed.

### Rate limiting with Semaphore

When calling external APIs or shared resources, limit concurrency to avoid overwhelming the target:

```python
semaphore = asyncio.Semaphore(10)  # max 10 concurrent

async def limited_fetch(item_id: str) -> Item:
    async with semaphore:
        return await client.get(f"/items/{item_id}")

results = await asyncio.gather(*[limited_fetch(id) for id in ids])
```

---

## 3. Dependency Injection Adjustments

### Motor client in DI module

```python
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

class AppModule(opyoid.Module):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def configure(self) -> None:
        client = AsyncIOMotorClient(self._settings.mongo_uri)
        db = client[self._settings.mongo_db]
        self.bind(AsyncIOMotorDatabase, to_instance=db)
        # Collection bindings
        self.bind(AsyncIOMotorCollection, to_instance=db["items"])
```

### FastAPI lifespan for client cleanup

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Motor client cleanup happens automatically on process exit,
    # but explicit close is preferred for graceful shutdown.
    app.state.motor_client.close()
```

---

## 4. Seed Scripts

Seed scripts that insert multiple independent records MUST use `asyncio.gather()` or `insert_many()`:

```python
# ❌ WRONG — sequential inserts
for item in items:
    await collection.insert_one(item)

# ✅ CORRECT — batch insert
await collection.insert_many(items)

# ✅ ALSO CORRECT — parallel inserts (when insert_many is not applicable)
await asyncio.gather(*[collection.insert_one(item) for item in items])
```

If the seed has **dependency phases** (e.g., permissions → roles → groups), parallelize **within** each phase but keep phases sequential:

```python
# Phase 1: permissions (all independent)
perm_results = await asyncio.gather(*[create_perm(p) for p in PERMISSIONS])

# Phase 2: roles (depend on permissions, but independent of each other)
role_results = await asyncio.gather(*[create_role(r, perm_map) for r in ROLES])

# Phase 3: groups (depend on roles)
group_results = await asyncio.gather(*[create_group(g, role_map) for g in GROUPS])
```

---

## 5. Testing

- Add `pytest-asyncio>=0.25` to `[project.optional-dependencies] dev`.
- Use `@pytest.mark.asyncio` on async test functions.
- Use `AsyncIOMotorClient` with testcontainers or mock the collection.

```python
import pytest

@pytest.mark.asyncio
async def test_get_item(repository):
    result = await repository.get("item-1")
    assert result is not None
```

- When testing parallelized code, verify that the number of I/O calls matches expectations (no N+1 queries).

---

## 6. What NOT to Do

- **Never** use `asyncio.run()` inside an async context — it creates a nested event loop.
- **Never** use `loop.run_until_complete()` in production code — it blocks the event loop.
- **Never** use `time.sleep()` in async code — use `await asyncio.sleep()`.
- **Never** mix sync pymongo calls with async motor calls — pick one driver per repository.
- **Never** use threading for I/O parallelism when asyncio is available — threads add overhead and complexity.
