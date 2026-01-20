# Task Plan: Local meeting webtool (camera + voice)

## Goal
Design a localhost-running meeting webtool (Google Meet–like) with camera and voice interface.

## Current Phase
Phase 4

## Phases

### Phase 1: Requirements & Constraints
- [x] Confirm must run on localhost
- [x] Confirm camera + voice interface required
- [x] Capture MVP additions (transcript save, bot support, agent structure)
- **Status:** complete

### Phase 2: Architecture & UX Design
- [x] Define client/server topology for localhost
- [x] Choose WebRTC approach (P2P vs SFU)
- [x] Define media flow (camera/mic permissions, device selection)
- [x] Define UI surfaces (preview, transcript, agent controls)
- **Status:** complete

### Phase 3: Implementation Outline
- [x] Outline minimal file structure and core modules
- [x] Implement transcript streaming UI + download
- [x] Add bot toggle UI and agent registry scaffolding
- **Status:** complete

### Phase 4: Delivery
- [ ] Provide concise update and next steps
- **Status:** in_progress

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Use WebRTC for media (camera/mic) | Browser-native real-time media on localhost. |
| Use Next.js + Tailwind | Matches project docs and quick UI iteration. |
| Add agent registry module | Enables extendable AI agent structure. |

## Open Questions
| Question | Notes |
|----------|-------|
| MVP features beyond camera/mic? | e.g., chat, screen share, recording |
| Single-room vs multi-room? | Impacts routing and signaling |
