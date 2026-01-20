## Summary
- 

## Key Changes
- 

## Testing
- [ ] `scripts/run_smoke.sh`
- [ ] `python3 scripts/review_agent_safety_check.py`
- [ ] Playwright UI demo flow (manual)
  - [ ] `frontend/.env.local` 설정
    - `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`
    - `NEXT_PUBLIC_WS_URL=ws://localhost:8000`
  - [ ] `http://localhost:3000` 접속
  - [ ] 회의 제목 입력 → 참석자 추가 → 아젠다 입력
  - [ ] **회의 시작** 클릭 → `/meeting/{id}` 진입 확인
  - [ ] **데모 모드** 클릭 → 실시간 자막 출력 확인
  - [ ] 개입 메시지 확인 (`TOPIC_DRIFT`, `PRINCIPLE_VIOLATION`)
  - [ ] 개입 카드 **확인** 클릭
  - [ ] **회의 종료** 클릭 → `/review/{id}` 이동 확인
  - [ ] 저장 파일 목록 확인 (`summary.md`, `action-items.md`, `interventions.md`, `transcript.md`)

## Notes
- 
