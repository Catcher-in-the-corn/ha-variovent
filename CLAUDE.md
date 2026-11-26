# Variovent DUO-Live – Home Assistant Integration

Local Home Assistant integration for Variovent / ZSA DUO-Live ventilation via the
DUO-Live X-Spot. It speaks the spot's own GWT-RPC web API (firmware V2.08). The library
lives in `custom_components/variovent/pyvariovent` and is published as `pyvariovent`.

Run tests with `bash scripts/test.sh` (works on Windows and Linux).

## Schutzregeln (protection rules)

Each rule is here because getting it wrong controls a real ventilation system wrongly,
corrupts the spot's data, or breaks existing installs. A change that touches a rule's
area must be checked against it.

1. **This controls real hardware.** A write must send exactly what the user asked and
   nothing else. Never send a command as a side effect of reading. `set_fan_level` /
   `set_mode` fetch a fresh device first (`_fresh`) and modify only the intended fields.
   A fan-level change may switch mode to normal first — that is intended and documented;
   no other implicit mode changes are allowed.

2. **Field indices are authoritative, not guessed.** Every index into a GWT DTO
   (`models.P`, `models.LG`, the `MODE_SETTINGS` table, session/rights indices in
   `client.py`) must match `docs/field-names.md`, which is derived from the server's own
   classes (javap alphabetical field order = GWT wire order) and cross-checked against
   live data. Changing or adding an index requires citing the field name from that file.

3. **The GWT codec is symmetric.** `gwt.py` must round-trip: anything decoded from a
   response must re-serialize to the same wire form (needed because updates resend the
   whole DTO). A `parse_response` of an `//OK` payload must consume every token
   (the `remaining` check). Long values use the GWT base64 variant.

4. **The spot allows one session per user.** A login elsewhere invalidates ours and
   calls then fail with an error result that has no message text and no "expired" flag.
   Such results trigger exactly one re-login and retry; a still-failing session is a
   temporary failure (`UpdateFailed`), never wrong credentials (no reauth prompt).

5. **Only offer what the device and user allow.** Operating modes depend on the device
   type (`MODE_DEVICE_TYPES`) and the user's per-device rights (`UserRechteLueftungsgeraete`).
   Fan level 0/4 is forbidden in air-quality / humidity mode. Never expose a mode or level
   the web UI would reject; validate before sending (fail with a clear error).

6. **Sensors of a switched-off device are `unavailable`**, like the web UI — the device
   does not measure then and the last value would be stale. Do not report stale values as
   current, and do not feed them into history.

7. **Never widen a config-flow error into "cannot connect".** A reachable spot that
   refuses a request (missing rights, etc.) is reported as `spot_error` with the spot's
   own message; wrong credentials as `invalid_auth`; only a real network failure as
   `cannot_connect`.

8. **Secrets and private data stay out of the repo.** `.env.local`, `backup/`,
   `tests/fixtures/private/` are gitignored and must never be committed, read into
   committed files, or printed into code/docs. Test fixtures are anonymized
   (`scripts/capture_fixtures.py`). The decompiled server code and the manufacturer's
   update credentials found in the SD image are reference-only and never leave `backup/`.

9. **Tests are not weakened to pass.** Fix the code, not the test. A new behavior needs a
   test; `bash scripts/test.sh` must stay green.

10. **Keep versions in step.** `manifest.json`, `pyproject.toml` and
    `pyvariovent/__init__.py` carry the same version; bump together for a user-visible
    change.
