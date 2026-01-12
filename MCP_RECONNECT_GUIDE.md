# Apify MCP 재연결 가이드

## 문제 상황
- MCP 세션 오류: "Session ID not found"
- Apify Actor 호출 불가

## 해결 방법

### 방법 1: Cursor 재시작
1. Cursor를 완전히 종료
2. Cursor를 다시 시작
3. MCP 서버가 자동으로 재연결됩니다

### 방법 2: MCP 서버 설정 확인
1. Cursor 설정에서 MCP 서버 확인
2. Apify MCP 서버가 실행 중인지 확인
3. 필요시 MCP 서버 재시작

### 방법 3: Apify API 토큰 확인
MCP 서버 설정에서 Apify API 토큰이 올바르게 설정되어 있는지 확인:
- `APIFY_TOKEN` 환경 변수 확인
- Apify 대시보드에서 토큰 생성/확인

## 재연결 후 확인
MCP가 복구되면 다음 명령으로 확인:
- `mcp_apify_search-actors` - Actor 검색 테스트
- `mcp_apify_call-actor` - Actor 호출 테스트

## 복구 후 작업
1. 수집 완료된 2개 키워드 데이터 저장
2. 나머지 98개 키워드 수집 계속 진행
