# Findings & Decisions

## Requirements
- Copy local Claude and Codex skill directories into this repo so collaborators can clone and use them.
- Include skills from `~/.codex/skills` and `~/.claude/skills` (non-system skills).
- Push changes to the existing Git remote.

## Research Findings
- Codex skills present locally: `multi-agent-guide`, `openai-agents-python`, `planning-with-files`, plus `.system` (system skills; should not be shared).
- Claude skills present locally: `openai-agents-python` (same contents as Codex copy).
- Current repo already includes `multi-agent-guide`, but with `skill.md` (lowercase) instead of `SKILL.md`.
- `planning-with-files` contains a nested `.git` directory that must be excluded when copying.

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Copy only non-system skills into repo root as top-level skill directories. | Keeps repo clean and matches expected skill layout for cloning. |
| Exclude `.git` when copying `planning-with-files`. | Avoid nested git repository issues. |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| - | - |

## Resources
- Local skill directories at `~/.codex/skills` and `~/.claude/skills`.
