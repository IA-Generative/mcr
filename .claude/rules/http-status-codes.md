---
paths:
  - "**/api/**/*.py"
  - "mcr-gateway/mcr_gateway/app/services/**/*.py"
---

# HTTP status codes

Use the named constants from `fastapi.status`, never a bare number.

```python
# yes
@router.delete("/{deliverable_id}", status_code=status.HTTP_204_NO_CONTENT)
return Response(status_code=status.HTTP_204_NO_CONTENT)
raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="...")

# no
@router.delete("/{deliverable_id}", status_code=204)
return Response(status_code=204)
raise HTTPException(status_code=404, detail="...")
```

Applies to `status_code=` on route decorators, `Response(...)`, and `HTTPException(...)`, in **mcr-core and mcr-gateway alike** — the gateway is the side that historically drifted, and not only in its routers: `mcr_gateway/app/services/` raises most of the gateway's `HTTPException`s while proxying, which is why it is in scope here too.

One form that is **not** a bare number and must stay as it is: relaying a status the upstream service chose.

```python
# yes — the code comes from core, naming it would be a lie
raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
return Response(content=response.content, status_code=response.status_code)
```

Two places keep raw numbers on purpose, and neither is an exception to the rule above:

- `exceptions/exception_handler.py` maps exception types to `status.HTTP_*` constants — that mapping is the single place a status is chosen in mcr-core, so a use-case raises a domain exception rather than naming a code.
- Tests assert on numbers (`assert response.status_code == 404`). That is deliberate: a test should pin the wire contract, and comparing a constant to itself would pass even if the constant were wrong.
