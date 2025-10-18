# Queued Task - List ("/cl:큐리스트")

Display the tasks currently scheduled to run after the cooldown restart.

## Steps
1. Run:
   ```bash
   python -m src.cli.main queue list
   ```
2. 각 항목에 표시된 템플릿(`[]` 안의 레이블)과 메모를 함께 전달합니다.
3. 후속 명령이 필요하면 `queue add --post`로 추가할 수 있다는 점을 안내합니다.
4. 항목이 없으면 큐가 비어 있다고 알려 주세요.
