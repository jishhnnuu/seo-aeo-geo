#!/usr/bin/env bash
# Claude SEO — Screaming Frog SEO Spider extension installer.
#
# Wraps the existing scripts/screaming_frog_run.py into a discoverable
# seo-screaming-frog skill. No API key — this automates a Screaming Frog
# SEO Spider licence the user already owns (or is buying); the installer
# does not purchase, download, or crack the product itself.
set -euo pipefail

main() {
    SKILL_DIR="${HOME}/.claude/skills"

    echo "════════════════════════════════════════"
    echo "║   Claude SEO — Screaming Frog        ║"
    echo "════════════════════════════════════════"

    command -v python3 >/dev/null 2>&1 || { echo "✗ Python 3 required."; exit 1; }
    [ ! -d "${SKILL_DIR}/seo" ] && { echo "✗ claude-seo base not installed."; exit 1; }

    if ! command -v screamingfrogseospider >/dev/null 2>&1; then
        echo "✗ screamingfrogseospider not found on PATH."
        echo "  This extension automates a Screaming Frog SEO Spider licence"
        echo "  you already own (or are buying) — it does not include one."
        echo "  1. Buy/download: https://www.screamingfrog.co.uk/seo-spider/"
        echo "  2. Install it and make sure its CLI binary is on \$PATH."
        echo "  3. Re-run this installer."
        exit 1
    fi

    SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" >/dev/null 2>&1 && pwd)"

    mkdir -p "${SKILL_DIR}/seo-screaming-frog"
    cp "${SOURCE_DIR}/skills/seo-screaming-frog/SKILL.md" "${SKILL_DIR}/seo-screaming-frog/SKILL.md"
    echo "✓ Installed skill: ${SKILL_DIR}/seo-screaming-frog"
    echo
    echo "Done. Try: /seo screaming-frog https://example.com"
    echo "Full docs: extensions/screaming-frog/docs/SCREAMING-FROG-SETUP.md"
}
main "$@"
