# T10 spike: how py-unifi-access calls the API

Client: `artifacts/work/py-unifi-access`, commit `646697821023b420331d21649e6118c88163d814` (pinned). Read-only.

## 1. HTTP calls

All API calls go through one helper, `UnifiAccessApiClient._request(url, method="GET", data=None, *, params=None)` (`unifi_access_api/client.py:516`). **The path is the first argument and the method the second, defaulting to `"GET"`.** It calls `self._session.request(method, url, ...)` (aiohttp, `client.py:527`).

Two typed wrappers put the model first: `_request_obj(response_type, url, method="GET", ...)` (`client.py:492`) and `_request_list(...)` (`client.py:504`).

Excerpts:
- `client.py:325-330`: `await self._request(self._url(DOOR_UNLOCK_URL.format(door_id=door_id)), "PUT", body, params=params or None)`
- `client.py:233`: `return await self._request_list(Door, self._url(DOORS_URL))` (method defaults to GET)

Two calls bypass `_request` and call `self._session.request("GET", url, ...)` directly: the Protect key probe (`client.py:207`, not a `/api/v1/developer/` path) and the thumbnail fetch (`client.py:373`).

## 2. How paths are built

Paths are **module-level string constants** in `unifi_access_api/const.py:4-15`, with `{name}` placeholders filled by `.format(...)`, e.g. `DOOR_UNLOCK_URL = "/api/v1/developer/doors/{door_id}/unlock"`. The 11 constants hold 11 distinct `/api/v1/developer/` paths (matches VERIFIED_FACTS F10). Exceptions:
- `STATIC_URL` is concatenated with a runtime value: `self._url(f"{STATIC_URL}{path}")` (`client.py:371`), so it is **dynamic / uncheckable**.
- `DEVICE_NOTIFICATIONS_URL` is used as a websocket URI (`client.py:427`), not an HTTP call, so its method is **UNKNOWN**.

Consequence: the task card's inventory rule (literal path inside the call) finds nothing here. The inventory also resolves constant names referenced anywhere inside an HTTP call's arguments, and infers the method from the helper's `method` parameter (explicit argument or default).

## 3. Pydantic models (all `BaseModel`, most `frozen=True`)

| Class | file:line | Config |
|---|---|---|
| `DoorLockRule` | `models/door.py:52` | defaults |
| `DoorLockRuleStatus` | `models/door.py:59` | defaults |
| `EmergencyStatus` | `models/door.py:66` | defaults |
| `Device` | `models/door.py:73` | `extra="allow"` |
| `Door` | `models/door.py:89` | default extra (ignore); `model_validator(mode="before")` flattens `extras` |
| `User` | `models/user.py:18` | `extra="allow"`; uses `from __future__ import annotations` |
| `AccessMethod`, `FaceAccessMethod`, `AccessMethods`, `DeviceSettings` | `models/device_settings.py:8, 20, 27, 40` | `extra="allow"` |
| websocket models (`WebsocketMessage` and ~40 others) | `models/websocket.py` | `extra="allow"`; `LogAddData` uses `alias="_source"` + `populate_by_name` |

The websocket models parse push notifications, not documented REST responses, so they are not candidates for response mapping.

## 4. Envelope handling

The client unwraps the envelope before validation (`client.py:544-554`):

```python
if response.get("code") != "SUCCESS":
    raise ApiError(...)
if "data" not in response:
    raise ApiError(...)
return response["data"]
```

`_request_obj` validates `data` as one object (json_path `data`). `_request_list` validates each element (json_path `data[*]`). `get_devices` validates each element of each inner list (`client.py:243`, json_path `data[*][*]`).
