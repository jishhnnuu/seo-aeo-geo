#!/usr/bin/env bash
set -euo pipefail

main() {
    echo "→ Uninstalling Screaming Frog extension..."
    rm -rf "${HOME}/.claude/skills/seo-screaming-frog"
    echo "✓ Removed seo-screaming-frog skill."
    echo "  (Your Screaming Frog SEO Spider licence/install is untouched — this only removes the claude-seo skill wrapper.)"
}
main "$@"
