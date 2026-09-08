# Agent Tools

이 저장소는 여러 Agent Foundry 메인 인스턴스가 함께 검색하는 프로그램 공유 저장소입니다.
`main`에 push된 `tools/<name>/manifest.json`과 소스가 검색 대상이며, 메인 서버는 주기적으로
목록을 동기화합니다. 다른 서버와 Registry DB를 공유할 필요가 없습니다.
각 서버의 별도 Worker가 필요한 프로그램의 특정 commit을 내려받아 테스트·검증 후 설치합니다.
설치일·호출 횟수·토큰 절감 추정치·secret은 각 메인 서버 DB에서 관리하며 Git에 저장하지 않습니다.

재사용 프로그램 전용 저장소입니다. 메인 서비스는 별도 저장소
[Agent Foundry](https://github.com/qmdch1/agent-foundry)에 있습니다.

```text
projects/
  agent-foundry/          # API, Registry, Router, Executor, Builder
  agent-tools/
    tools/
      csv-statistics/
        app/main.py
        tests/test_main.py
        manifest.json
        requirements.txt
        README.md
```

프로그램은 `run(dict) -> dict` 및 JSON stdin/stdout 인터페이스를 지킵니다.
운영 등록은 Foundry의 검증·배포 명령으로 수행합니다. 파일을 Git에 올리는 것만으로
ACTIVE가 되지 않습니다. Registry는 version과 full git_commit을 기록합니다.
stateless 프로그램에는 별도의 Dockerfile, Compose 또는 DB migration을 만들지 않습니다.
각 프로그램에 필요한 실행 컨테이너는 Foundry가 신뢰된 템플릿으로 구성합니다.

`csv-statistics`는 초기 표준 예제이며 실제 LLM이 생성했다고 표시하지 않습니다.
