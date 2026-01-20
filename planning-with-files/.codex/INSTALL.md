# Installing planning-with-files for Codex

## Prerequisites

- Codex IDE installed
- Git installed (optional, for cloning)

## Installation

### Option 1: Clone Repository (Recommended)

```bash
mkdir -p ~/.codex/skills
cd ~/.codex/skills
git clone https://github.com/OthmanAdi/planning-with-files.git
```

### Option 2: Manual Copy

1. Download or clone this repository
2. Copy the entire `planning-with-files/` directory to `~/.codex/skills/`
3. Ensure the structure matches:
   ```
   ~/.codex/skills/planning-with-files/
   ├── planning-with-files/
   │   ├── SKILL.md
   │   ├── templates/
   │   └── scripts/
   ```

## Usage

### If Using Superpowers

If you have [obra/superpowers](https://github.com/obra/superpowers) installed:

```bash
~/.codex/superpowers/.codex/superpowers-codex use-skill planning-with-files
```

Superpowers will find it in your personal skills directory.

### If NOT Using Superpowers

Manually read the skill file when starting complex tasks:

```bash
cat ~/.codex/skills/planning-with-files/planning-with-files/SKILL.md
```

Or add to your `~/.codex/AGENTS.md`:

```markdown
## Planning with Files

<IMPORTANT>
For complex multi-step tasks (3+ steps, research, building projects):
1. Read the planning-with-files skill: `cat ~/.codex/skills/planning-with-files/planning-with-files/SKILL.md`
2. Create task_plan.md, findings.md, progress.md in your project directory
3. Follow the 3-file pattern throughout the task
</IMPORTANT>
```

## Verification

Check that the skill exists:

```bash
ls -la ~/.codex/skills/planning-with-files/planning-with-files/SKILL.md
```

## Troubleshooting

### Skill not found

- Verify path: `~/.codex/skills/planning-with-files/planning-with-files/SKILL.md`
- Check file exists and is readable
- Ensure SKILL.md has proper YAML frontmatter

### Scripts not executing

**Windows users:**
- Use PowerShell versions: `*.ps1`
- Set execution policy: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

**Unix/Mac users:**
- Make scripts executable: `chmod +x ~/.codex/skills/planning-with-files/scripts/*.sh`

## Getting Help

- Issues: https://github.com/OthmanAdi/planning-with-files/issues
- Documentation: https://github.com/OthmanAdi/planning-with-files
