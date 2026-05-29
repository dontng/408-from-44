#!/usr/bin/env bash
# knight.sh — polls for pending spells and executes them via Claude Code
# usage:  bash wishes/knight.sh
# env:    POLL_INTERVAL=seconds (default 1800)

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SPELL_DIR="$REPO_DIR/wishes/spell"
PHANTASM_DIR="$REPO_DIR/wishes/phantasm"
POLL_INTERVAL="${POLL_INTERVAL:-1800}"

cd "$REPO_DIR"

log() { echo "[$(date '+%Y/%m/%d %H:%M:%S')] $*" >&2; }

# ── spell file helpers ────────────────────────────────────────────────────────

# Prints wish_id on line 1, prompt on remaining lines.
# Exits 1 if no [pending] wish found.
get_first_pending() {
    python3 - "$1" <<'EOF'
import sys, re

with open(sys.argv[1], encoding='utf-8') as f:
    content = f.read()

pattern = r'^--- (wish-\S+) \[pending\]\n(.*?)(?=^--- wish-|\Z)'
m = re.search(pattern, content, re.MULTILINE | re.DOTALL)
if not m:
    sys.exit(1)

print(m.group(1))
print(m.group(2).strip())
EOF
}

set_status() {
    python3 - "$1" "$2" "$3" "$4" <<'EOF'
import sys
file, wish_id, from_s, to_s = sys.argv[1:]
with open(file, encoding='utf-8') as f:
    text = f.read()
with open(file, 'w', encoding='utf-8') as f:
    f.write(text.replace(f'--- {wish_id} [{from_s}]', f'--- {wish_id} [{to_s}]', 1))
EOF
}

# ── execution ─────────────────────────────────────────────────────────────────

process_wish() {
    local spell_file="$1"
    local date_str
    date_str=$(basename "$spell_file" .md)

    local raw
    raw=$(get_first_pending "$spell_file") || return 1

    local wish_id prompt
    wish_id=$(printf '%s' "$raw" | head -1)
    prompt=$(printf '%s' "$raw" | tail -n +2)

    log "$date_str / $wish_id → running"

    # Mark running, push so the other machine sees it immediately
    set_status "$spell_file" "$wish_id" "pending" "running"
    git add "wishes/spell/${date_str}.md"
    git commit -m "wish: ${date_str}/${wish_id} [running]"
    git push

    local start_time exit_code cc_output diff_stat status
    start_time=$(date '+%Y/%m/%d %H:%M:%S')
    exit_code=0

    # Execute — capture output even on failure, allow all tools unattended
    cc_output=$(claude -p "$prompt" \
        --allowedTools "Bash Edit Read Write" \
        --allow-dangerously-skip-permissions \
        2>&1) || exit_code=$?

    local end_time
    end_time=$(date '+%Y/%m/%d %H:%M:%S')

    # Capture what actually changed on disk
    diff_stat=$(git diff --stat HEAD 2>/dev/null || echo "(no file changes)")

    # Determine final status
    if [ "$exit_code" -eq 0 ]; then
        status="done"
    elif printf '%s' "$cc_output" | grep -qiE "token|context.?window|rate.?limit"; then
        status="exhausted"
    else
        status="failed"
    fi

    # Update spell file
    set_status "$spell_file" "$wish_id" "running" "$status"

    # Append phantasm record
    local phantasm_file="$PHANTASM_DIR/${date_str}.md"
    {
        printf '\n--- %s [%s]\n' "$wish_id" "$status"
        printf '    start    %s\n' "$start_time"
        printf '    end      %s\n' "$end_time"
        printf '    exit     %s\n' "$exit_code"
        printf '\n    prompt\n'
        printf '%s\n' "$prompt" | sed 's/^/        /'
        printf '\n    diff\n'
        printf '%s\n' "$diff_stat" | sed 's/^/        /'
        printf '\n    output\n'
        printf '%s\n' "$cc_output" | sed 's/^/        /'
        printf '\n'
    } >> "$phantasm_file"

    # Commit everything + push immediately
    git add -A
    git commit -m "phantasm: ${date_str}/${wish_id} [$status]"
    git push

    log "$date_str / $wish_id → [$status]"
}

# ── main loop ─────────────────────────────────────────────────────────────────

main() {
    log "knight online  (poll interval ${POLL_INTERVAL}s)"
    mkdir -p "$SPELL_DIR" "$PHANTASM_DIR"

    while true; do
        git pull --rebase 2>/dev/null || log "git pull failed, will retry"

        local any=false
        for spell_file in "$SPELL_DIR"/*.md; do
            [ -f "$spell_file" ] || continue
            while process_wish "$spell_file"; do
                any=true
            done
        done

        if [ "$any" = false ]; then
            log "no pending spells — sleeping ${POLL_INTERVAL}s"
            sleep "$POLL_INTERVAL"
        fi
    done
}

main
