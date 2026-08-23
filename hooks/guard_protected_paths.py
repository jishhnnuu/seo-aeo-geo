#!/usr/bin/env python3
"""PreToolUse guard for Write/Edit (defense in depth).

Blocks Write/Edit calls to protected paths regardless of which agent issued
them. The primary safety guarantees in this plugin are (a) every auditor
agent's tool allowlist excludes Write/Edit, and (b) the seo-fix skill's
`disable-model-invocation: true`, which stops the model from triggering a
write on its own. This hook is the belt-and-suspenders layer underneath
those two, ported from the write guard in Hainrixz/claude-seo-ai (MIT) and
adapted to this plugin's Python-hook convention (see validate-schema.py).

Hook configuration (see hooks/hooks.json):
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "node",
            "args": [
              "${CLAUDE_PLUGIN_ROOT}/hooks/run-python-hook.js",
              "${CLAUDE_PLUGIN_ROOT}/hooks/guard_protected_paths.py",
              "${tool_input.file_path}"
            ]
          }
        ]
      }
    ]
  }
}

Exit code 2 blocks the tool call; exit code 0 allows it.
"""

import re
import sys

PROTECTED = [
    re.compile(r"(^|/)\.git(/|$)"),
    re.compile(r"(^|/)\.env(\.|$)", re.IGNORECASE),
    re.compile(r"(^|/)(id_rsa|id_ed25519)(\.|$)"),
    re.compile(r"\.(pem|key|p12|pfx)$", re.IGNORECASE),
    re.compile(r"(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|bun\.lockb)$"),
    re.compile(r"(^|/)\.ssh(/|$)"),
    re.compile(r"(^|/)\.aws(/|$)"),
    re.compile(r"(^|/)secrets?(/|\.|$)", re.IGNORECASE),
]


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else ""
    if not path:
        return 0

    if any(pattern.search(path) for pattern in PROTECTED):
        sys.stderr.write(
            "claude-seo: refusing to write to a protected path: " + path + "\n"
            "SEO fixes never modify VCS internals, secrets, env files, or "
            "lockfiles, regardless of which skill or agent requested it.\n"
        )
        return 2  # block

    return 0  # allow


if __name__ == "__main__":
    sys.exit(main())
