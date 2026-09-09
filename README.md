# Agent Tools

[메인 프로그램](https://github.com/qmdch1/agent-foundry) · [설치·AI 연결](https://github.com/qmdch1/agent-foundry/blob/main/LOCAL_MCP.md) · [상세 설명](REFERENCE.md) · [MIT](LICENSE)

Agent Foundry가 검색하고 설치하는 Python 프로그램 저장소입니다.
프로그램 소스를 공유하며, 데이터와 API 키는 각자의 PC에 보관합니다.

## 얻는 이점

- 이미 만들어진 프로그램을 다시 만들지 않고 사용합니다.
- 버전이 고정된 소스를 테스트한 뒤 설치합니다.
- DB가 필요한 프로그램은 로컬 중앙 DB의 전용 스키마를 사용합니다.

## 포함된 프로그램

| 프로그램 | 기능 |
| --- | --- |
| [CSV 통계](tools/csv-statistics) | 숫자 데이터 집계 |
| [기록 저장](tools/record-store) | 기록 저장·조회 |
| [HRMS](tools/hrms) | 직원·부서·연차 기록 관리 |
| [상품 비교](tools/product-comparison) | 입력된 상품 정보 비교·이력 조회 |

상품 비교는 제공된 정보를 처리하며, 자체 웹 검색은 하지 않습니다.

## 설치 및 동작

1. [Agent Foundry를 설치](https://github.com/qmdch1/agent-foundry#설치)하고 AI에 연결합니다.
2. AI가 필요한 프로그램을 검색하고 별도 Worker에 설치를 요청합니다.
3. Worker가 테스트·설치를 마치면 프로그램을 실행할 수 있습니다.

이 저장소는 직접 실행하는 MCP 서버가 아닙니다. 사용만 할 때는 별도로 clone할 필요가 없습니다.
새 프로그램 공유는 개인 Fork와 push 설정을 사용합니다. [공유 방법](https://github.com/qmdch1/agent-foundry/blob/main/LOCAL_MCP.md)
