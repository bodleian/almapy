## 1. Protocol and type definitions

- [x] 1.1 Add `Dumpable` runtime-checkable Protocol and `Body` type alias to `_utils.py`

## 2. Core conversion logic

- [x] 2.1 Add Dumpable isinstance check + `.dump(mode="json")` call in `AlmaClient.execute()` before retry loop

## 3. Namespace signature updates

- [x] 3.1 Update `_users.py` write methods to use `Body` type: `update_user` (user param + 2 overloads), `create_user` (user param + 2 overloads), `create_fee` (fine param)
- [x] 3.2 Update `_bibs.py` write methods to use `Body` type: `create_item` (item param + 2 overloads), `update_item` (item param + 2 overloads)
- [x] 3.3 Update `_acq.py` write methods to use `Body` type: `update_po_line` (updated_po_line param + 2 overloads), `receive_existing_item` (updated_item param + 2 overloads, note: currently `dict[str, Any] | None` — becomes `Body | None`)
- [x] 3.4 Update `_config.py` write methods to use `Body` type: `update_integration_profile` (data param + 2 overloads), `create_integration_profile` (data param + 2 overloads), `update_code_table` (data param + 2 overloads)

## 4. Tests

- [x] 4.1 Add unit test: Dumpable isinstance returns True for object with compatible dump()
- [x] 4.2 Add unit test: plain dict passes through execute() unchanged
- [x] 4.3 Add unit test: Dumpable object is auto-converted via .dump(mode="json") in execute()
- [x] 4.4 Run full test suite + mypy to verify backwards compatibility
