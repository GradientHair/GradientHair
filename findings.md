# Findings & Decisions

## Requirements
- App must run on localhost.
- Provide camera and voice interface (mic + speaker) in browser.

## Assumptions
- Single user can host a room; others can join via URL on same machine/network (localhost for development).
- Browser permissions are acceptable (getUserMedia).

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Use WebRTC for media | Standard browser API for camera/mic with low latency. |
| Use a lightweight signaling server | Needed for SDP/ICE exchange. |

## Risks
| Risk | Mitigation |
|------|------------|
| NAT traversal on localhost testing is limited | Keep dev on same machine; later add STUN/TURN for real use. |
| Device permission UX can confuse users | Add clear pre-join preview and permission prompts. |
