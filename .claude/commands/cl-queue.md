---
command: "/cl:queue"
title: "Add Queued Task"
description: "Add a follow-up task that should run after Claude restarts."
---

# Queued Task - Add

Add a new post-restart task to the automation queue.

## Steps

1. 선택적으로 템플릿을 확인합니다.
   ```bash
   python -m src.cli.main queue templates
   ```
2. 큐에 추가할 업무를 지정합니다. 필요하다면 템플릿, 추가 체크리스트, 후속 명령을 함께 전달하세요.
   ```bash
   python -m src.cli.main queue add \
     --template backend_feature \
     --guideline "데이터 마이그레이션 영향 검토" \
     --post "pytest tests/api" \
     "에러 로깅 개선"
   ```
3. 명령이 성공했는지 확인하고, 큐가 리스트에 반영됐는지 안내합니다.
4. 사용자가 요청한 추가 메모가 있다면 `--note` 옵션으로 함께 저장하도록 알려줍니다.

### Example Usage
```bash
python -m src.cli.main queue add --template devops_incident "production 배포 점검"
```
