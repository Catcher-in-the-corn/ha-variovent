#!/usr/bin/env bash
# Adversarial Review in Runden: Der protokoll-reviewer (.claude/agents/protokoll-reviewer.md)
# prüft den Diff des aktuellen Branches gegen main, der Autor antwortet je Befund mit
# Fix oder Begründung, bis der Reviewer CONSENSUS schreibt oder MAX Runden vorbei sind.
# Jeder claude-Aufruf startet mit frischem Kontext.
#
#   scripts/adversarial-review.sh [plan.md]
#
# Läuft im Worktree des Branches, nie auf main, nur mit sauberem Arbeitsbaum.
# Rechte beider Rollen: scripts/agent-settings.json (kein Push, kein Merge, kein
# Zugriff auf backup/, .env.local, tests/fixtures/private/). Ergebnisse in
# .reviews/<branch>/ (nicht im Repo). Umgebung: BASE (main), MAX (4), BUDGET (USD, 5).
set -euo pipefail

PLAN="${1:-}"
BASE="${BASE:-main}"
MAX="${MAX:-4}"
BUDGET="${BUDGET:-5}"

cd "$(git rev-parse --show-toplevel)"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [ "$BRANCH" = "$BASE" ] || [ "$BRANCH" = "HEAD" ]; then
  echo "Auf '$BRANCH' wird nicht reviewt — eigenen Branch bzw. Worktree anlegen." >&2; exit 2
fi
if [ -n "$(git status --porcelain)" ]; then
  echo "Arbeitsbaum nicht sauber — erst committen, damit die Fixes des Autors getrennt bleiben." >&2; exit 2
fi
if [ -n "$PLAN" ] && [ ! -f "$PLAN" ]; then
  echo "Plan '$PLAN' nicht gefunden." >&2; exit 2
fi
if git diff --quiet "$BASE"...HEAD; then
  echo "Kein Unterschied zu $BASE." >&2; exit 2
fi

ORDNER=".reviews/${BRANCH//\//-}"
mkdir -p "$ORDNER"
EINSTELLUNGEN="scripts/agent-settings.json"
PLAN_SATZ="Kein Plan angegeben; prüfe gegen die Commit-Nachrichten (git log $BASE..HEAD)."
[ -n "$PLAN" ] && PLAN_SATZ="Plan: $PLAN."

ersteZeile() { sed -n '/[^[:space:]]/{p;q;}' "$1" | tr -d '\r[:space:]'; }

for i in $(seq 1 "$MAX"); do
  # || true: Vor der ersten Runde gibt es keine Datei, ls schlägt fehl, und mit
  # pipefail beendete das das Skript still mit Code 1.
  FRUEHER="$(ls "$ORDNER"/runde-*.md 2>/dev/null | tr '\n' ' ' || true)"
  echo "Runde $i: protokoll-reviewer prüft $BRANCH gegen $BASE …"
  git diff "$BASE"...HEAD -- . ':!tests/fixtures' \
    | claude -p --agent protokoll-reviewer \
        --settings "$EINSTELLUNGEN" \
        --allowedTools "Read" "Grep" "Glob" "Bash(git diff:*)" "Bash(git log:*)" "Bash(git show:*)" "Bash(bash scripts/test.sh:*)" \
        --max-budget-usd "$BUDGET" \
        "Prüfe den Diff von Branch $BRANCH gegen $BASE (stdin). $PLAN_SATZ Frühere Runden und Antworten des Autors: ${FRUEHER:-keine}. Ausgabe genau im Format deiner Rollenbeschreibung." \
    > "$ORDNER/runde-$i.md"

  if [ ! -s "$ORDNER/runde-$i.md" ]; then
    echo "Reviewer hat nichts geliefert (Budget, Fehler?) — Abbruch." >&2; exit 3
  fi
  if [ "$(ersteZeile "$ORDNER/runde-$i.md")" = "CONSENSUS" ]; then
    echo "Konsens nach Runde $i ($ORDNER/runde-$i.md)."; exit 0
  fi
  [ "$i" -eq "$MAX" ] && break

  echo "Runde $i: Autor antwortet auf die Befunde …"
  claude -p --permission-mode acceptEdits \
    --settings "$EINSTELLUNGEN" \
    --allowedTools "Read" "Edit" "Write" "Bash(git add:*)" "Bash(git commit:*)" "Bash(git diff:*)" "Bash(git status:*)" "Bash(git log:*)" "Bash(bash scripts/test.sh:*)" \
    --max-budget-usd "$BUDGET" \
    "Du bist Autor von Branch $BRANCH. $PLAN_SATZ Lies $ORDNER/runde-$i.md. Pro Befund: berechtigt -> beheben, bash scripts/test.sh grün halten, je Befund committen (Nachricht nennt die Befundnummer); nicht berechtigt -> begründet ablehnen. Tests nie abschwächen, um einen Befund zu erledigen. Schreibe je Befund eine Zeile 'N. behoben (Commit) | abgelehnt: Begründung' nach $ORDNER/runde-$i-antwort.md. Nicht pushen, nicht mergen." \
    > "$ORDNER/runde-$i-autor.log"
done

echo "Kein Konsens nach $MAX Runden — Entscheidung durch dich. Befunde: $ORDNER/" >&2
exit 1
