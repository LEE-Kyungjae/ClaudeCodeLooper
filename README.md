# ClaudeCodeLooper

> Automated monitoring and restart system for Claude Code usage limits

**ClaudeCodeLooper**는 Claude Code의 5시간 사용 제한을 자동으로 감지하고, 대기 기간 후 자동으로 재시작하는 모니터링 시스템입니다.

Claude Code usage limit를 걱정 없이 장시간 작업할 수 있도록 도와줍니다.

---

## ✨ 주요 기능

- **🔍 자동 감지**: Claude Code 출력을 실시간 모니터링하여 사용 제한 자동 감지
- **⏰ 정확한 타이밍**: 5시간 대기 기간을 정확하게 추적하고 자동 재시작
- **🔄 무중단 운영**: 백그라운드 데몬 모드로 작업 중단 없이 모니터링
- **💬 Claude Code 통합**: 슬래시 커맨드로 간편하게 제어 (`/cl:on`, `/cl:off`, `/cl:status`, `/cl:logs`)
- **🛡️ 안전성**: 우아한 종료(graceful shutdown) 및 상태 저장으로 시스템 재부팅 후에도 복구 가능
- **📊 상세 로그**: JSON 형식의 구조화된 로깅으로 모든 이벤트 추적 가능

---

## 📋 요구사항

- **Python**: 3.11 이상
- **OS**: Windows, macOS, Linux (WSL 지원)
- **Claude Code**: 설치되어 있어야 함

---

## 🚀 빠른 설치

### 방법 1: pip로 설치 (권장)

```bash
# 1. 저장소 클론
git clone https://github.com/LEE-Kyungjae/ClaudeCodeLooper.git
cd ClaudeCodeLooper

# 2. 패키지 설치
pip install -e .

# 3. 설치 확인
claude-looper --version
```

### 방법 2: 수동 설치

```bash
# 1. 저장소 클론
git clone https://github.com/LEE-Kyungjae/ClaudeCodeLooper.git
cd ClaudeCodeLooper

# 2. 의존성 설치
pip install -r requirements.txt

# 3. Python 모듈로 실행
python -m src.cli.main --help
```

---

## 🎯 빠른 시작

### 기본 사용법

```bash
# 모니터링 시작 (데몬 모드)
claude-looper start --claude-cmd "claude" --work-dir "$PWD" --daemon

# 상태 확인
claude-looper status

# 로그 보기
claude-looper logs --tail 50

# 모니터링 중지
claude-looper stop --all
```

### Claude Code에서 슬래시 커맨드로 사용

Claude Code를 사용하는 경우 훨씬 간편합니다:

```
/cl:on        # 모니터링 시작
/cl:status    # 상태 확인
/cl:logs      # 로그 보기
/cl:off       # 모니터링 중지
```

> 💡 **Tip**: 슬래시 커맨드는 자동으로 출력을 포맷팅하고 이모지로 시각화해줍니다!

---

## 📖 사용 시나리오

### 시나리오 1: 장시간 코딩 세션

```bash
# 아침에 작업 시작
/cl:on

# [일반적으로 작업하기]
# [5시간 제한에 도달하면 자동으로 감지]
# [시스템이 5시간 대기]
# [자동으로 Claude Code 재시작]

# 저녁에 작업 종료
/cl:off
```

### 시나리오 2: CI/CD 파이프라인

```bash
# 자동화된 워크플로우에서 사용
claude-looper start \
  --claude-cmd "claude --no-interactive" \
  --work-dir "/path/to/project" \
  --daemon

# 파이프라인 작업 수행
# ...

# 완료 후 정리
claude-looper stop --all
```

### 시나리오 3: 여러 프로젝트 동시 모니터링

```bash
# 프로젝트 A 모니터링
cd /path/to/project-a
claude-looper start --claude-cmd "claude" --daemon

# 프로젝트 B 모니터링
cd /path/to/project-b
claude-looper start --claude-cmd "claude" --daemon

# 모든 세션 상태 확인
claude-looper status --verbose
```

---

## ⚙️ 설정

### 설정 파일 위치

- **기본 설정**: `config/default.json`
- **사용자 설정**: `.claude-restart-config.json` (프로젝트 루트에 생성)

### 설정 예제

`.claude-restart-config.json` 파일을 만들어 커스터마이징:

```json
{
  "detection": {
    "patterns": [
      "usage limit exceeded",
      "wait (\\d+) hours?"
    ],
    "confidence_threshold": 0.7
  },
  "timing": {
    "wait_hours": 5,
    "check_interval_seconds": 60
  },
  "restart": {
    "max_retries": 3,
    "retry_delay_seconds": 10
  },
  "logging": {
    "level": "INFO",
    "file": "logs/claude-restart-monitor.log"
  }
}
```

---

## 🔧 CLI 명령어 레퍼런스

### `start` - 모니터링 시작

```bash
claude-looper start [OPTIONS]

Options:
  --claude-cmd TEXT       Claude Code 실행 명령어 [default: claude]
  --work-dir TEXT         작업 디렉토리 [default: current directory]
  --daemon                백그라운드 데몬 모드
  --config TEXT           설정 파일 경로
  --session-id TEXT       세션 ID (자동 생성 가능)
```

**예제:**
```bash
# 기본 시작
claude-looper start

# 데몬 모드로 시작
claude-looper start --daemon

# 커스텀 설정으로 시작
claude-looper start --config /path/to/config.json --daemon
```

### `stop` - 모니터링 중지

```bash
claude-looper stop [OPTIONS]

Options:
  --session-id TEXT       특정 세션 중지
  --all                   모든 세션 중지
  --force                 강제 종료
```

**예제:**
```bash
# 모든 세션 정상 종료
claude-looper stop --all

# 특정 세션 중지
claude-looper stop --session-id sess_abc123

# 강제 종료
claude-looper stop --all --force
```

### `status` - 상태 확인

```bash
claude-looper status [OPTIONS]

Options:
  --verbose               상세 정보 표시
  --format [text|json]    출력 형식
  --session-id TEXT       특정 세션 상태
```

**예제:**
```bash
# 기본 상태
claude-looper status

# 상세 정보
claude-looper status --verbose

# JSON 형식
claude-looper status --format json
```

### `logs` - 로그 보기

```bash
claude-looper logs [OPTIONS]

Options:
  --tail INTEGER          마지막 N줄 표시 [default: 50]
  --follow                실시간 로그 스트리밍
  --filter TEXT           필터 (detection, error, warning)
  --session-id TEXT       특정 세션 로그
```

**예제:**
```bash
# 최근 50줄
claude-looper logs

# 최근 100줄
claude-looper logs --tail 100

# 실시간 스트리밍
claude-looper logs --follow

# 에러만 필터링
claude-looper logs --filter error

# 감지 이벤트만
claude-looper logs --filter detection
```

### `config` - 설정 관리

```bash
claude-looper config [OPTIONS]

Options:
  --show                  현재 설정 표시
  --set KEY VALUE         설정 값 변경
  --reset                 기본값으로 리셋
```

**예제:**
```bash
# 현재 설정 보기
claude-looper config --show

# 대기 시간 변경
claude-looper config --set timing.wait_hours 6

# 기본값 복구
claude-looper config --reset
```

---

## 🐛 문제 해결

### 모니터링이 시작되지 않아요

```bash
# 1. 로그 확인
claude-looper logs --filter error

# 2. 권한 확인
ls -la logs/

# 3. Python 버전 확인
python --version  # 3.11 이상이어야 함

# 4. 의존성 재설치
pip install -r requirements.txt --force-reinstall
```

### 자동 재시작이 안 돼요

```bash
# 1. 감지 패턴 확인
claude-looper logs --filter detection

# 2. 설정 확인
claude-looper config --show

# 3. 상세 상태 확인
claude-looper status --verbose
```

### Claude Code를 찾을 수 없다고 나와요

```bash
# 1. Claude Code 설치 확인
which claude

# 2. PATH 설정 확인
echo $PATH

# 3. 절대 경로로 지정
claude-looper start --claude-cmd "/full/path/to/claude"
```

### 로그 파일이 너무 커요

```bash
# 로그 파일 정리
rm logs/claude-restart-monitor.log

# 또는 로그 레벨 조정
claude-looper config --set logging.level WARNING
```

---

## 👨‍💻 개발자 가이드

### 개발 환경 설정

```bash
# 저장소 클론
git clone https://github.com/LEE-Kyungjae/ClaudeCodeLooper.git
cd ClaudeCodeLooper

# 개발 모드로 설치
pip install -e ".[dev]"

# 테스트 실행
pytest tests/ -v

# 코드 품질 검사
black src/ tests/
flake8 src/ tests/
mypy src/
```

### 프로젝트 구조

```
ClaudeCodeLooper/
├── src/
│   ├── cli/                 # CLI 인터페이스
│   │   ├── main.py
│   │   └── commands/        # 각 명령어 구현
│   ├── models/              # 데이터 모델 (Pydantic)
│   ├── services/            # 핵심 서비스
│   │   ├── process_monitor.py      # 프로세스 모니터링 오케스트레이터
│   │   ├── process_launcher.py     # 프로세스 실행 관리
│   │   ├── output_capture.py       # 출력 캡처
│   │   ├── health_checker.py       # 상태 모니터링
│   │   ├── pattern_detector.py     # 패턴 감지
│   │   └── restart_controller.py   # 재시작 제어
│   ├── utils/               # 유틸리티
│   │   └── logging.py       # 구조화된 로깅
│   └── exceptions.py        # 예외 계층
├── tests/
│   ├── contract/            # 계약 테스트
│   ├── integration/         # 통합 테스트
│   └── unit/                # 단위 테스트
├── config/
│   └── default.json         # 기본 설정
├── .claude/
│   └── commands/            # Claude Code 슬래시 커맨드
└── docs/                    # 추가 문서
```

### 테스트 작성

```python
# tests/unit/services/test_example.py
import pytest
from src.services.process_monitor import ProcessMonitor

def test_monitor_initialization():
    monitor = ProcessMonitor(config)
    assert monitor is not None

@pytest.mark.asyncio
async def test_async_operation():
    # 비동기 테스트 예제
    pass
```

### 새 기능 추가하기

1. **브랜치 생성**: `git checkout -b feature/your-feature`
2. **테스트 작성**: TDD 방식으로 먼저 테스트 작성
3. **구현**: 테스트를 통과하도록 구현
4. **품질 검사**: `black`, `flake8`, `mypy` 실행
5. **커밋**: 명확한 커밋 메시지 작성
6. **Pull Request**: 메인 브랜치에 PR 생성

---

## 📄 라이선스

MIT License - 자유롭게 사용, 수정, 배포할 수 있습니다.

---

## 🤝 기여하기

버그 리포트, 기능 제안, Pull Request 환영합니다!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📞 지원

- **Issues**: [GitHub Issues](https://github.com/LEE-Kyungjae/ClaudeCodeLooper/issues)
- **Documentation**: [Wiki](https://github.com/LEE-Kyungjae/ClaudeCodeLooper/wiki)
- **Email**: your-email@example.com

---

## 🙏 감사의 말

Claude Code를 더 편하게 사용할 수 있도록 이 프로젝트를 만들었습니다.
피드백과 기여를 환영합니다!

---

**Made with ❤️ for Claude Code users**
