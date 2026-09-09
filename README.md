[메인 프로그램 · agent-foundry](https://github.com/qmdch1/agent-foundry) | [서브 프로그램 · agent-tools](https://github.com/qmdch1/agent-tools)

# Agent Tools

각 사용자의 PC에 설치된 Agent Foundry가 검색·설치하는 Python 프로그램 저장소입니다.
운영자의 공용 서버는 필요하지 않습니다. 소스는 GitHub에서 공유하고, 프로그램 데이터·사용 통계·API 키는 각자의 PC에 보관합니다.

## 시작하기

1. [Agent Foundry](https://github.com/qmdch1/agent-foundry)의 로컬 설치 절차를 진행합니다.
2. [로컬 MCP 가이드](https://github.com/qmdch1/agent-foundry/blob/main/LOCAL_MCP.md)에 따라 Codex 또는 STDIO MCP를 지원하는 AI 앱에 연결합니다.
3. AI에게 필요한 기능을 요청하면 설치된 프로그램을 검색합니다. GitHub 카탈로그의 프로그램은 별도 Worker가 검증·설치한 뒤 사용할 수 있습니다.

이 저장소 자체는 MCP 서버가 아닙니다. MCP 연결은 메인 프로그램이 제공하며, 프로그램이 늘어나도
모든 프로그램 정의를 AI 문맥에 넣지 않고 검색된 후보만 전달합니다.
공개 후에는 읽기·설치에 이 저장소의 쓰기 권한이나 관리자의 토큰이 필요하지 않습니다.
저장소가 비공개인 동안에는 읽기 인증이 필요합니다.

## 포함된 프로그램

| 프로그램 | 기능 | 데이터 저장 |
| --- | --- | --- |
| `csv-statistics` | CSV 숫자 열의 개수·결측·합계·평균·최솟값·최댓값 | 없음 |
| `record-store` | 이름별 문자열 기록 저장·조회 | 로컬 전용 스키마 |
| `hrms` | 직원·부서 요약·승인된 연차 배정과 사용 기록 | 로컬 전용 스키마 |
| `product-comparison` | 입력한 상품 사양 필터·비교·출처·비교 이력 조회 | 로컬 전용 스키마 |

상품 비교 프로그램은 웹 검색이나 최신 가격 검증을 수행하지 않습니다. 호출자가 확인한 사양과 출처를 입력해야 합니다.
HRMS는 기본 인사 기록 예제이며 법정 연차·급여·채용 판단 시스템이 아닙니다. 예시·테스트는 합성 자료입니다.

## 저장소 구조와 실행 규약

```text
agent-foundry/                  # 별도 메인 저장소
agent-tools/                    # 이 저장소
  tools/<program-name>/
    app/main.py
    tests/test_main.py
    manifest.json
    generation_tokens.txt
    requirements.txt            # 필요한 경우
    migrations/                 # 데이터 정의가 필요한 경우
    README.md
```

프로그램은 `run(input_data: dict) -> dict` 및 JSON stdin/stdout 인터페이스를 사용합니다.
로그를 stdout에 섞지 않습니다. 런타임·입출력 스키마·예시·제한은 manifest에 선언합니다.
Foundry는 신뢰된 템플릿으로 실행 이미지를 만들고 제한된 Docker 환경에서 테스트합니다.
소스를 Git에 올리는 것만으로 사용 가능 상태가 되지 않습니다.

카탈로그는 설정된 원격 브랜치의 `tools/<name>/manifest.json`을 읽습니다. 설치 시 전체 Git commit을
고정하여 검증하고 Registry에 버전과 commit을 기록합니다. 임의 endpoint나 shell 명령을 AI가 만들지 않습니다.

## DB와 토큰 기록

DB가 필요한 프로그램은 설치자의 로컬 PostgreSQL 안에 `tool_<program UUID hex>` 스키마를 사용합니다.
프로그램마다 DB 컨테이너를 만들지 않습니다. Worker가 스키마와 전용 계정을 준비하며,
manifest의 테이블·일반 인덱스 선언만 적용합니다. 실제 DB 데이터나 비밀번호는 이 저장소에 넣지 않습니다.
다른 PC에 설치하면 그 PC의 빈 스키마가 만들어집니다. 기존 데이터는 별도 DB 백업으로 복구합니다.

`generation_tokens.txt`에는 생성·수정에 사용된 누적 토큰의 최종 정수 한 줄만 보관합니다.
완전한 기록이 없으면 `미집계`를 유지합니다. 초기 직접 작성 예제의 일부 값은 소스 크기 환산값이며
`generation_tokens_estimated=true`로 구분합니다. AI 제공자가 보고한 실제 사용량과 동일하지 않습니다.
호출 횟수·절약 토큰·설치일은 각 Foundry의 로컬 DB에만 저장합니다.

## 개인 프로그램 생성과 공유

기본 로컬 모드는 테스트한 프로그램을 개인 PC의 Git에 commit하고 활성화하며 원격으로 push하지 않습니다.
따라서 이 저장소의 쓰기 권한 없이도 새 프로그램을 생성해 개인적으로 사용할 수 있습니다.

공유하려면:

1. 이 저장소를 자신의 GitHub 계정으로 Fork합니다.
2. Foundry 최초 설정에서 개인 Fork 주소를 지정합니다.
3. 자동 push를 원하면 개인 Fork에만 쓰기 가능한 토큰을 자신의 Worker에 연결합니다.
4. 다른 사용자에게 Fork 주소를 알려주거나 원본 저장소에 Pull Request를 제출합니다.

현재 Foundry 카탈로그는 한 설치당 승인된 원격 저장소 하나를 사용합니다. Fork 사용자는 GitHub의
Sync fork로 원본 변경을 가져올 수 있습니다. 이미 사용 중인 설치의 원격 주소만 바꾸는 이관은 지원하지 않습니다.
구체적인 설정과 로컬 commit 백업은 [공유 및 복구 안내](https://github.com/qmdch1/agent-foundry/blob/main/LOCAL_MCP.md#7-로컬-보관과-github-공유)를 참고하세요.

기여에는 소스, manifest, 정상·경계·오류 테스트, 필요한 DB 선언, 설명을 포함합니다.
비밀값·개인정보·실제 운영 데이터·로컬 설정·실행 로그는 커밋하지 않습니다. 테스트가 실패한 변경은 설치하지 않습니다.

## 라이선스

[MIT 라이선스](LICENSE)로 제공합니다. 수정·재배포 시 저작권 및 라이선스 고지를 유지하세요.
외부 패키지·자료의 권리와 AI 서비스 약관은 별도로 적용됩니다. 라이선스가 생성 코드의 정확성이나
외부 자료의 재배포 권리를 보장하지는 않습니다.
