# 상품 사양 비교

출처가 첨부된 상품 JSON을 받아 조건에 맞는 상품을 고르고 사양 표 데이터를 반환합니다. 상품이나 시계 모델을 하드코딩하지 않습니다. 웹 검색, 페이지 수집, 출처 진위/최신성 검증, 추천 점수 생성은 하지 않습니다. 호출자가 확인한 사양을 공급해야 합니다.

`run({"payload": {...}})` 또는 stdin JSON / stdout JSON을 사용합니다. Agent 프롬프트에서는 `product-comparison {JSON payload}`로 결정론적으로 호출합니다. 일반 자연어에서 인터넷 상품을 찾는 전체 과정은 별도의 검색 계층이 필요합니다.

- `fields`: 필드명별 `type` (`number`, `string`, `boolean`)과 `unit`. 숫자는 명시적 단위가 필요하고 나머지 단위는 null입니다. 단위 없는 숫자는 `count`, 비율은 `ratio`처럼 의미를 명시합니다.
- `products`: 1~100개. 각각 고유 `id`, `name`, `sources` (HTTPS `url`, `checked_at` 날짜), `specs`를 갖습니다. 사양은 `{value, unit}`이며 선언 단위와 정확히 같아야 합니다.
- `filters`: `{field, op, value, unit}` 목록을 AND로 적용합니다. `eq`는 타입이 같은 정확한 값 비교, `gte`/`lte`는 숫자 전용입니다. 단위 변환, 문자열 숫자 변환, 동의어 추론은 하지 않습니다.
- `sort`: 선택 사항 `{field, direction: asc|desc}`. 동률은 입력 순서를 유지하고 누락은 양방향 모두 마지막입니다.
- `limit`: 1~100. 필터 통과 수 `matched_count`와 실제 반환 수 `returned_count`를 구분합니다.
- 누락/명시적 null 사양은 `status: unknown`, 제공 사양은 `provided`로 반환합니다. 필터 대상의 누락은 제외 사유 `unknown`으로 기록합니다. 누락된 인증을 false로 바꾸지 않습니다.

시계의 방수 등급과 다이버 인증은 별도 필드로 전달하십시오. 200m 방수로 다이버 인증을 추론하지 않습니다. 케이스 폭과 지름도 각각 별도 필드여야 합니다. 다른 통화·단위는 호출 전에 출처 있는 방식으로 변환하거나 별도 필드로 유지하십시오.

예제 입출력은 manifest.json에 있습니다. 예제의 example.com 제품은 테스트용 가상 자료입니다. 실제 상품 데이터는 저장소에 보관하지 않습니다.

외부 의존성, DB, 네트워크가 필요 없습니다. Agent Foundry Worker가 비루트·읽기 전용·네트워크 차단 컨테이너에서 구문, 단위 테스트, 스키마, 반복 샘플을 검증한 후 배포합니다.

`generation_tokens.txt`는 코드·테스트 UTF-8 바이트 수를 4로 나누어 올림한 생성 비용 대용값입니다. 실제 세션 청구 토큰이 아니며 manifest의 `generation_tokens_estimated=true`로 구분합니다. 후속 수정 비용은 정책에 따라 누적하고 최종 합계만 저장합니다.
