# CSV statistics

CSV 숫자 열의 count, missing_count, sum, mean, min, max를 계산합니다.
소수 정확도를 보존하려고 숫자 결과는 문자열로 반환합니다. 입력은 500 KB, 10,000행으로
제한합니다. 결측값은 계산에서 제외하고 별도 집계하며 잘못된 숫자는 오류로 처리합니다.
Decimal 50자리 정밀도를 사용합니다. 평균의 무한소수는 이 정밀도에서 반올림됩니다.

`run({"csv_text":"value\n0.1\n0.2\n","column":"value"})`

CLI: `python app/main.py`에 JSON을 stdin으로 전달합니다. 출력은 JSON 하나입니다.
검증: `python -m pytest tests`.

운영 실행은 Agent Foundry의 관리형 non-root Docker sandbox를 사용합니다.
독립 HTTP 서비스, 자체 Docker Compose, 데이터베이스가 필요하지 않습니다.
