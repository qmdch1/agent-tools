# Agent Tools

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
