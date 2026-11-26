# Direct-database path (design, not yet implemented)

A design sketch for talking to the spot's MySQL database directly instead of
through its GWT web app. This replaces nothing today — `pyvariovent`'s GWT-RPC
client stays the supported path. This document explains *why* a direct path is
possible, *what* it would need, and the *safety rules* any implementation of
it must follow. It contains no manufacturer source code; table and column
names are the same kind of derived fact already published in
[`field-names.md`](field-names.md).

## Why this is possible at all

The spot runs two independent processes that only talk to each other through
the database:

```
Ventilators ──ZSA radio──  Radio module  ──serial (/dev/ttyAMA0)──  DuoSpot (C++/Qt)
                                                                         │
                                                                     MySQL ("zsalivespotwebapp")
                                                                         │
                                                                   Tomcat/GWT web app  ──  pyvariovent (today)
```

The web app never talks to the radio module. When a user changes something,
the web app writes new values into MySQL and bumps a change counter; DuoSpot
notices the counter changed, re-reads the row, and sends the change over
radio. When DuoSpot receives something back from a device, it writes the new
values into MySQL directly. **Nothing stops a third client from reading or
writing the same tables**, as long as it plays by the same counter protocol.

## The dirty-counter protocol

The table `kommunikation` holds one row per ventilator with paired counter
columns, e.g. `geaendert_zaehler_lg_parameter` /
`geaendert_zaehler_lg_parameter_merk` ("merk" = acknowledged). To change a
ventilator's parameters: write the new values into
`lueftungsgeraete_parameter`, then increment the `_zaehler` counter for that
device in `kommunikation`. DuoSpot polls on a short cycle (`config` table,
keys `KURZE_ZYKLUSZEIT_SEC` / `LANGE_ZYKLUSZEIT_SEC`), sees `_zaehler !=
_merk`, sends the change by radio, and sets `_merk = _zaehler` once done.
Reading is simpler: current state always lives in `lueftungsgeraete_parameter`
and `lueftungsgeraete`, no counter dance needed.

Relevant counters in `kommunikation` (names, not literal SQL):
`geaendert_zaehler_ba_parameter` (an operating-mode's own settings, e.g. the
humidity-mode thresholds), `geaendert_zaehler_lg_parameter` (fan level /
operating mode of a device), `geaendert_zaehler_funk_parameter` (radio-level
settings).

## What this buys over the GWT path

- No "one session per user" lockout — MySQL connections aren't tied to a
  single login, several clients can read/write concurrently.
- Error messages are the database's or ours, not the opaque "keine
  Berechtigung" text the GWT layer returns for several unrelated failure
  modes.
- Direct, typed access to every column in `docs/field-names.md`, instead of
  positional fields in a GWT object graph.
- No dependency on the aging Tomcat 7 / GWT 2.x stack at all for day-to-day
  operation.

## What it does not buy

- No faster or more reliable radio link — DuoSpot's poll cycle and the ZSA
  radio protocol are unchanged; a direct write still waits for the same
  cycle before anything reaches a ventilator.
- No access to the per-user rights model in a meaningfully different way —
  `user_rechte_lueftungsgeraete` is still the source of truth if an
  implementation wants to honor it.

## What is needed before this becomes a real integration

1. **SSH access to the spot** (see `backup/SD-KARTE-ANLEITUNG.md`), to create
   a **dedicated, least-privilege MySQL user** instead of ever using
   `root`/whatever credentials the web app uses internally — `SELECT` only on
   the tables it reads, `SELECT, UPDATE` only on `lueftungsgeraete_parameter`
   and `kommunikation` for the tables it writes, no `DROP`/`DELETE`/`GRANT`.
   This is a deliberate design choice, not a limitation found in the spot:
   MySQL's privilege system supports exactly this.
2. **A test copy of the database**, not the live one, for the first
   read/write experiments (see the SD-card-copy workflow already set up).
3. A small protocol layer in `pyvariovent` analogous to `gwt.py`: a MySQL
   client, the counter-increment write path, and the same validation rules
   `models.py` already enforces (mode/level allowed for the device and user,
   values in range) — enforced in Python since we no longer get the web
   app's server-side checks for free.
4. Tests against the **anonymized, recorded** query results, same pattern as
   `tests/fixtures/`.

## Safety rules for any implementation (extends `CLAUDE.md`)

- Never connect as a MySQL account with more than the minimum grants above.
- Never write a column DuoSpot doesn't already use to apply a change —
  writing to `lueftungsgeraete_parameter` without bumping the matching
  `kommunikation` counter leaves DuoSpot unaware of the change; bumping a
  counter without having actually changed the row makes DuoSpot re-send
  stale data over radio.
- Treat the `_merk` counters as DuoSpot's exclusively — a client that writes
  `_zaehler` must never also set `_merk`, or DuoSpot will believe a change it
  never sent was acknowledged.
- Keep the GWT path as the default until the direct path has run against a
  test copy for a meaningful period with no discrepancies.
