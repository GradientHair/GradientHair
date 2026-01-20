# Changelog

All notable changes to this project will be documented in this file.

## [2.3.0] - 2026-01-17

### Added

- **Codex IDE Support**
  - Created `.codex/INSTALL.md` with installation instructions
  - Skills install to `~/.codex/skills/planning-with-files/`
  - Works with obra/superpowers or standalone
  - Added `docs/codex.md` for user documentation
  - Based on analysis of obra/superpowers Codex implementation

- **OpenCode IDE Support** (Issue #27)
  - Created `.opencode/INSTALL.md` with installation instructions
  - Global installation: `~/.config/opencode/skills/planning-with-files/`
  - Project installation: `.opencode/skills/planning-with-files/`
  - Works with obra/superpowers plugin or standalone
  - oh-my-opencode compatibility documented
  - Added `docs/opencode.md` for user documentation
  - Based on analysis of obra/superpowers OpenCode plugin

### Changed

- Updated README.md with Supported IDEs table
- Updated README.md file structure diagram
- Updated docs/installation.md with Codex and OpenCode sections
- Version bump to 2.3.0

### Documentation

- Added Codex and OpenCode to IDE support table in README
- Created comprehensive installation guides for both IDEs
- Documented skill priority system for OpenCode
- Documented integration with superpowers ecosystem

### Research

This implementation is based on real analysis of:
- [obra/superpowers](https://github.com/obra/superpowers) repository
- Codex skill system and CLI architecture
- OpenCode plugin system and skill resolution
- Skill priority and override mechanisms

### Thanks

- @Realtyxxx for feedback on Issue #27 about OpenCode support
- obra for the superpowers reference implementation

---

## [2.2.2] - 2026-01-17

### Fixed

- **Restored Skill Activation Language** (PR #34)
  - Restored the activation trigger in SKILL.md description
  - Description now includes: "Use when starting complex multi-step tasks, research projects, or any task requiring >5 tool calls"
  - This language was accidentally removed during the v2.2.1 merge
  - Helps Claude auto-activate the skill when detecting appropriate tasks

### Changed

- Updated version to 2.2.2 in all SKILL.md files and plugin.json

### Thanks

- Community members for catching this issue

---

## [2.2.1] - 2026-01-17

### Added

- **Session Recovery Feature** (PR #33 by @lasmarois)
  - Automatically detect and recover unsynced work from previous sessions after `/clear`
  - New `scripts/session-catchup.py` analyzes previous session JSONL files
  - Finds last planning file update and extracts conversation that happened after
  - Recovery triggered automatically when invoking `/planning-with-files`
  - Pure Python stdlib implementation, no external dependencies

- **PreToolUse Hook Enhancement**
  - Now triggers on Read/Glob/Grep in addition to Write/Edit/Bash
  - Keeps task_plan.md in attention during research/exploration phases
  - Better context management throughout workflow

### Changed

- SKILL.md restructured with session recovery as first instruction
- Description updated to mention session recovery feature
- README updated with session recovery workflow and instructions

### Documentation

- Added "Session Recovery" section to README
- Documented optimal workflow for context window management
- Instructions for disabling auto-compact in Claude Code settings

### Thanks

Special thanks to:
- @lasmarois for session recovery implementation (PR #33)
- Community members for testing and feedback

---

## [2.2.0] - 2026-01-17

### Added

- **Kilo Code Support** (PR #30 by @aimasteracc)
  - Added Kilo Code IDE compatibility for the planning-with-files skill
  - Created `.kilocode/rules/planning-with-files.md` with IDE-specific rules
  - Added `docs/kilocode.md` comprehensive documentation for Kilo Code users
  - Enables seamless integration with Kilo Code's planning workflow

- **Windows PowerShell Support** (Fixes #32, #25)
  - Created `check-complete.ps1` - PowerShell equivalent of bash script
  - Created `init-session.ps1` - PowerShell session initialization
  - Scripts available in all three locations (root, plugin, skills)
  - OS-aware hook execution with automatic fallback
  - Improves Windows user experience with native PowerShell support

- **CONTRIBUTORS.md**
  - Recognizes all community contributors
  - Lists code contributors with their impact
  - Acknowledges issue reporters and testers
  - Documents community forks

### Fixed

- **Stop Hook Windows Compatibility** (Fixes #32)
  - Hook now detects Windows environment automatically
  - Uses PowerShell scripts on Windows, bash on Unix/Linux/Mac
  - Graceful fallback if PowerShell not available
  - Tested on Windows 11 PowerShell and Git Bash

- **Script Path Resolution** (Fixes #25)
  - Improved `${CLAUDE_PLUGIN_ROOT}` handling across platforms
  - Scripts now work regardless of installation method
  - Added error handling for missing scripts

### Changed

- **SKILL.md Hook Configuration**
  - Stop hook now uses multi-line command with OS detection
  - Supports pwsh (PowerShell Core), powershell (Windows PowerShell), and bash
  - Automatic fallback chain for maximum compatibility

- **Documentation Updates**
  - Updated to support both Claude Code and Kilo Code environments
  - Enhanced template compatibility across different AI coding assistants
  - Updated `.gitignore` to include `findings.md` and `progress.md`

### Files Added

- `.kilocode/rules/planning-with-files.md` - Kilo Code IDE rules
- `docs/kilocode.md` - Kilo Code-specific documentation
- `scripts/check-complete.ps1` - PowerShell completion check (root level)
- `scripts/init-session.ps1` - PowerShell session init (root level)
- `planning-with-files/scripts/check-complete.ps1` - PowerShell (plugin level)
- `planning-with-files/scripts/init-session.ps1` - PowerShell (plugin level)
- `skills/planning-with-files/scripts/check-complete.ps1` - PowerShell (skills level)
- `skills/planning-with-files/scripts/init-session.ps1` - PowerShell (skills level)
- `CONTRIBUTORS.md` - Community contributor recognition
- `COMPREHENSIVE_ISSUE_ANALYSIS.md` - Detailed issue research and solutions

### Documentation

- Added Windows troubleshooting guidance
- Recognized community contributors in CONTRIBUTORS.md
- Updated README to reflect Windows and Kilo Code support

### Thanks

Special thanks to:
- @aimasteracc for Kilo Code support and PowerShell script contribution (PR #30)
- @mtuwei for reporting Windows compatibility issues (#32)
- All community members who tested and provided feedback

  - Root cause: `${CLAUDE_PLUGIN_ROOT}` resolves to repo root, but templates were only in subfolders
  - Added `templates/` and `scripts/` directories at repo root level
  - Now templates are accessible regardless of how `CLAUDE_PLUGIN_ROOT` resolves
  - Works for both plugin installs and manual installs

### Structure

After this fix, templates exist in THREE locations for maximum compatibility:
- `templates/` - At repo root (for `${CLAUDE_PLUGIN_ROOT}/templates/`)
- `planning-with-files/templates/` - For plugin marketplace installs
- `skills/planning-with-files/templates/` - For legacy `~/.claude/skills/` installs

### Workaround for Existing Users

If you still experience issues after updating:
1. Uninstall: `/plugin uninstall planning-with-files@planning-with-files`
2. Reinstall: `/plugin marketplace add OthmanAdi/planning-with-files`
3. Install: `/plugin install planning-with-files@planning-with-files`

---

## [2.1.1] - 2026-01-10

### Fixed

- **Plugin Template Path Issue** (Fixes #15)
  - Templates weren't found when installed via plugin marketplace
  - Plugin cache expected `planning-with-files/templates/` at repo root
  - Added `planning-with-files/` folder at root level for plugin installs
  - Kept `skills/planning-with-files/` for legacy `~/.claude/skills/` installs

### Structure

- `planning-with-files/` - For plugin marketplace installs
- `skills/planning-with-files/` - For manual `~/.claude/skills/` installs

---

## [2.1.0] - 2026-01-10

### Added

- **Claude Code v2.1 Compatibility**
  - Updated skill to leverage all new Claude Code v2.1 features
  - Requires Claude Code v2.1.0 or later

- **`user-invocable: true` Frontmatter**
  - Skill now appears in slash command menu
  - Users can manually invoke with `/planning-with-files`
  - Auto-detection still works as before

- **`SessionStart` Hook**
  - Notifies user when skill is loaded and ready
  - Displays message at session start confirming skill availability

- **`PostToolUse` Hook**
  - Runs after every Write/Edit operation
  - Reminds Claude to update `task_plan.md` if a phase was completed
  - Helps prevent forgotten status updates

- **YAML List Format for `allowed-tools`**
  - Migrated from comma-separated string to YAML list syntax
  - Cleaner, more maintainable frontmatter
  - Follows Claude Code v2.1 best practices

### Changed

- Version bumped to 2.1.0 in SKILL.md, plugin.json, and README.md
- README.md updated with v2.1.0 features section
- Versions table updated to reflect new release

### Compatibility

- **Minimum Claude Code Version:** v2.1.0
- **Backward Compatible:** Yes (works with older Claude Code, but new hooks may not fire)

## [2.0.1] - 2026-01-09

### Fixed

- Planning files now correctly created in project directory, not skill installation folder
- Added "Important: Where Files Go" section to SKILL.md
- Added Troubleshooting section to README.md

### Thanks

- @wqh17101 for reporting and confirming the fix

## [2.0.0] - 2026-01-08

### Added

- **Hooks Integration** (Claude Code 2.1.0+)
  - `PreToolUse` hook: Automatically reads `task_plan.md` before Write/Edit/Bash operations
  - `Stop` hook: Verifies all phases are complete before stopping
  - Implements Manus "attention manipulation" principle automatically

- **Templates Directory**
  - `templates/task_plan.md` - Structured phase tracking template
  - `templates/findings.md` - Research and discovery storage template
  - `templates/progress.md` - Session logging with test results template

- **Scripts Directory**
  - `scripts/init-session.sh` - Initialize all planning files at once
  - `scripts/check-complete.sh` - Verify all phases are complete

- **New Documentation**
  - `CHANGELOG.md` - This file

- **Enhanced SKILL.md**
  - The 2-Action Rule (save findings after every 2 view/browser operations)
  - The 3-Strike Error Protocol (structured error recovery)
  - Read vs Write Decision Matrix
  - The 5-Question Reboot Test

- **Expanded reference.md**
  - The 3 Context Engineering Strategies (Reduction, Isolation, Offloading)
  - The 7-Step Agent Loop diagram
  - Critical constraints section
  - Updated Manus statistics

### Changed

- SKILL.md restructured for progressive disclosure (<500 lines)
- Version bumped to 2.0.0 in all manifests
- README.md reorganized (Thank You section moved to top)
- Description updated to mention >5 tool calls threshold

### Preserved

- All v1.0.0 content available in `legacy` branch
- Original examples.md retained (proven patterns)
- Core 3-file pattern unchanged
- MIT License unchanged

## [1.0.0] - 2026-01-07

### Added

- Initial release
- SKILL.md with core workflow
- reference.md with 6 Manus principles
- examples.md with 4 real-world examples
- Plugin structure for Claude Code marketplace
- README.md with installation instructions

---

## Versioning

This project follows [Semantic Versioning](https://semver.org/):
- MAJOR: Breaking changes to skill behavior
- MINOR: New features, backward compatible
- PATCH: Bug fixes, documentation updates
