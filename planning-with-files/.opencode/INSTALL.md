# Installing planning-with-files for OpenCode

## Prerequisites

- OpenCode.ai installed
- Git installed (optional, for cloning)

## Installation

### Option 1: Global Installation (All Projects)

```bash
mkdir -p ~/.config/opencode/skills
cd ~/.config/opencode/skills
git clone https://github.com/OthmanAdi/planning-with-files.git
```

### Option 2: Project-Specific Installation

```bash
# In your OpenCode project root
mkdir -p .opencode/skills
cd .opencode/skills
git clone https://github.com/OthmanAdi/planning-with-files.git
```

### Option 3: Manual Copy

**For global installation:**
1. Download or clone this repository
2. Copy to `~/.config/opencode/skills/planning-with-files/`

**For project installation:**
1. Download or clone this repository
2. Copy to `.opencode/skills/planning-with-files/` in your project

## File Structure

After installation:

```
~/.config/opencode/skills/planning-with-files/  (or .opencode/skills/planning-with-files/)
├── planning-with-files/
│   ├── SKILL.md              # Main skill file
│   ├── templates/
│   │   ├── task_plan.md
│   │   ├── findings.md
│   │   └── progress.md
│   └── scripts/
│       ├── check-complete.sh
│       ├── check-complete.ps1
│       ├── init-session.sh
│       ├── init-session.ps1
│       └── session-catchup.py
```

## Usage

### If Using Superpowers Plugin

If you have [obra/superpowers](https://github.com/obra/superpowers) installed as an OpenCode plugin:

```
Use the use_skill tool with skill_name: "planning-with-files"
```

OpenCode will find it automatically (personal skills override superpowers skills).

### If NOT Using Superpowers

You can still manually load the skill:

1. Navigate to `~/.config/opencode/skills/planning-with-files/planning-with-files/`
2. Read SKILL.md
3. Follow the instructions for creating task_plan.md, findings.md, progress.md

Or create a custom tool/command to load it.

## Skill Priority

If installed as:
- **Project skill** (`.opencode/skills/planning-with-files/`) - Highest priority
- **Personal skill** (`~/.config/opencode/skills/planning-with-files/`) - Medium priority
- If superpowers has a planning-with-files skill - Lowest priority

Project skills override personal skills, which override superpowers skills.

## Verification

**Global installation:**
```bash
ls -la ~/.config/opencode/skills/planning-with-files/planning-with-files/SKILL.md
```

**Project installation:**
```bash
ls -la .opencode/skills/planning-with-files/planning-with-files/SKILL.md
```

## Troubleshooting

### Skill not loading

1. Verify SKILL.md exists at the correct path
2. Check YAML frontmatter is valid:
   ```yaml
   ---
   name: planning-with-files
   description: ...
   ---
   ```
3. If using superpowers plugin, use `find_skills` tool to verify it's discovered

### Scripts not executing

**Windows:**
- Use PowerShell versions: `*.ps1`
- Set execution policy: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

**Unix/Mac:**
- Make executable: `chmod +x ~/.config/opencode/skills/planning-with-files/scripts/*.sh`

### oh-my-opencode Blocking

If using oh-my-opencode and the skill isn't recognized:

1. Check `~/.config/opencode/oh-my-opencode.json`
2. Ensure planning-with-files is NOT in `disabled_skills` array:
   ```json
   {
     "disabled_skills": []
   }
   ```
3. Restart OpenCode

## Getting Help

- Issues: https://github.com/OthmanAdi/planning-with-files/issues
- Documentation: https://github.com/OthmanAdi/planning-with-files
