# Task Plan: Sync local Claude/Codex skills into repo

## Goal
Mirror local Claude and Codex skill directories into this repo so collaborators can clone and use them.

## Current Phase
Phase 3

## Phases

### Phase 1: Requirements & Discovery
- [x] Understand user intent
- [x] Identify constraints
- [x] Document in findings.md
- **Status:** complete

### Phase 2: Planning & Structure
- [x] Define approach
- [x] Create project structure
- **Status:** complete

### Phase 3: Implementation
- [x] Copy skill directories into repo (excluding system skills and nested .git)
- [x] Update README to list new skills
- [ ] Stage and commit changes
- **Status:** in_progress

### Phase 4: Testing & Verification
- [x] Verify repo contents match local skills
- [x] Document verification in progress.md
- **Status:** complete

### Phase 5: Delivery
- [ ] Push to remote
- [ ] Summarize changes to user
- **Status:** pending

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Copy non-system skills to repo root directories. | Keeps clone usable and consistent with existing layout. |
| Exclude nested `.git` directories. | Prevents nested repo issues. |

## Errors Encountered
| Error | Resolution |
|-------|------------|
