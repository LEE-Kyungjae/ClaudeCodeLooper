"""Template manager for queued task automation prompts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class TaskTemplate:
    """Represents a reusable task template."""

    template_id: str
    persona_prompt: str
    quality_guidelines: List[str]
    coding_guidelines: List[str]
    post_commands: List[str]

    def build_guideline_prompt(self) -> str:
        """Render guidelines into a single prompt string."""
        lines: List[str] = []
        if self.quality_guidelines:
            lines.append("### 품질 체크리스트")
            for item in self.quality_guidelines:
                lines.append(f"- {item}")
            lines.append("")

        if self.coding_guidelines:
            lines.append("### 구현 지침")
            for item in self.coding_guidelines:
                lines.append(f"- {item}")

        return "\n".join(lines).strip()


class TemplateManager:
    """Provides access to predefined task templates."""

    _BUILTIN_TEMPLATES: Dict[str, TaskTemplate] = {
        "backend_feature": TaskTemplate(
            template_id="backend_feature",
            persona_prompt=(
                "당신은 백엔드 시니어 개발자로서 안정성과 유지보수를 최우선으로 합니다.\n"
                "- API 계약을 깨지 않도록 주의하고, 변경 사항은 데이터 일관성에 어떤 영향을 주는지 설명하세요.\n"
                "- 테스트 전략(단위/통합)을 제안하고 필요한 경우 mock 전략을 언급하세요."
            ),
            quality_guidelines=[
                "변경 전후에 영향 받는 서비스/엔드포인트를 나열합니다.",
                "성능이나 비용 영향이 있다면 수치나 추정치로 설명합니다.",
                "에러 로깅/모니터링 포인트가 필요한지 평가합니다."
            ],
            coding_guidelines=[
                "도메인 서비스 레이어 패턴을 유지합니다.",
                "의존성 주입을 활용하고 전역 상태에 의존하지 않습니다.",
                "비동기 로직은 타임아웃과 cancellation을 고려합니다."
            ],
            post_commands=[
                "pytest tests/ -k backend",
                "mypy src/"
            ]
        ),
        "devops_incident": TaskTemplate(
            template_id="devops_incident",
            persona_prompt=(
                "당신은 DevOps 엔지니어로서 운영 안정성 확보가 목표입니다.\n"
                "- 현재 상태를 점검하고, 완화 조치와 롤백 계획을 함께 제시하세요.\n"
                "- 변경 사항은 재현 가능한 스크립트나 명령으로 설명합니다."
            ),
            quality_guidelines=[
                "배포 전후 health check 또는 모니터링 지표를 확인합니다.",
                "당시 발생한 경보/로그를 수집하여 타임라인을 작성합니다.",
                "추가 모니터링/알림 개선 사항을 제안합니다."
            ],
            coding_guidelines=[
                "IaC 혹은 설정 변경은 버전 관리되는 위치를 명시합니다.",
                "비밀정보는 마스킹하고 공유 채널에 노출하지 않습니다.",
                "운영 명령은 dry-run 여부와 예상 영향을 함께 작성합니다."
            ],
            post_commands=[
                "kubectl get pods -n production",
                "kubectl describe deployment <SERVICE> -n production"
            ]
        ),
        "frontend_polish": TaskTemplate(
            template_id="frontend_polish",
            persona_prompt=(
                "당신은 프론트엔드 개발자로서 사용자 경험과 접근성을 중시합니다.\n"
                "- 디자인 시스템 가이드를 적용하고 반응형 동작을 검증하세요.\n"
                "- 시각적 변화가 있다면 스크린샷이나 스펙을 첨부해 주세요."
            ),
            quality_guidelines=[
                "접근성(A11y) 체크리스트(WAI-ARIA, 대체 텍스트 등)를 검토합니다.",
                "핵심 브라우저/디바이스 조합에서 테스트합니다.",
                "성능(번들 사이즈, hydration 시간)에 영향이 있는지 평가합니다."
            ],
            coding_guidelines=[
                "컴포넌트는 상태/스타일/비즈니스 로직을 분리합니다.",
                "스토리북 혹은 캡쳐 기반으로 변경 사항을 공유합니다.",
                "i18n/다국어 문자열 처리를 누락하지 않습니다."
            ],
            post_commands=[
                "npm run lint",
                "npm run test -- --watch=false"
            ]
        ),
    }

    def __init__(self, templates: Optional[Dict[str, TaskTemplate]] = None):
        self._templates = dict(self._BUILTIN_TEMPLATES)
        if templates:
            self._templates.update(templates)

    def available_templates(self) -> List[TaskTemplate]:
        """Return all registered templates."""
        return [self._templates[key] for key in sorted(self._templates.keys())]

    def get(self, template_id: str) -> Optional[TaskTemplate]:
        """Return a template by id."""
        return self._templates.get(template_id)
