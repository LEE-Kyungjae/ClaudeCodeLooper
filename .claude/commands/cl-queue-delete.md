# Queued Task - Remove ("/cl:큐딜리트")

Remove one or more queued tasks by their list numbers.

## Steps
1. Review the current queue if needed:
   ```bash
   python -m src.cli.main queue list
   ```
2. Remove the desired entries by specifying their numbers separated by spaces:
   ```bash
   python -m src.cli.main queue remove 1 3 5
   ```
3. Confirm the removal output (템플릿/메모 정보 포함)과 함께 삭제된 업무를 사용자에게 알려 주세요.
4. 일련 번호는 리스트와 동일하게 1부터 시작하므로, 제거 후 다시 `queue list`로 남은 항목을 확인하는 것도 권장합니다.
