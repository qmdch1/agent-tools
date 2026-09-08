from concurrent.futures import ThreadPoolExecutor

import pytest
from app.main import run


def ask(query):
    return run({"query": query})["data"]


def test_employee_leave_and_replay():
    registration = "직원 등록 UNIT001 가상직원 연구팀 2024-02-29 2026 15"
    first = run({"query": registration})
    assert first["data"]["remaining"] == 15
    assert first["storage"]["action"] == "created"
    assert run({"query": registration})["storage"]["action"] == "reused"
    assert ask(registration)["remaining"] == 15
    assert ask("직원 UNIT001 조회")["joined_on"] == "2024-02-29"
    assert ask("부서 연구팀 인원")["count"] == 1
    leave = run({"query": "휴가 사용 UNIT001 2026 0.5 req01"})
    assert leave["data"]["remaining"] == 14.5
    assert leave["storage"]["action"] == "created"
    assert run({"query": "휴가 사용 UNIT001 2026 0.5 req01"})["storage"]["action"] == "reused"
    assert run({"query": "직원 UNIT001 조회"})["storage"]["action"] == "read"
    assert ask("휴가 사용 UNIT001 2026 0.5 req01")["replayed"] is True
    with pytest.raises(ValueError):
        ask("휴가 사용 UNIT001 2026 1 req01")
    with pytest.raises(ValueError):
        ask("휴가 사용 UNIT001 2026 15 req02")
    assert ask("연차 UNIT001 2026 잔여")["remaining"] == 14.5
    with pytest.raises(ValueError):
        ask("직원 등록 UNIT001 다른직원 연구팀 2024-02-29 2026 15")
    assert ask("직원 UNIT001 조회")["name"] == "가상직원"
    assert ask("인사 요약")["total"] >= 1


def test_parallel_leave_never_overdraws():
    ask("직원 등록 RACE001 동시성직원 검증팀 2025-01-01 2026 1")

    def attempt(index):
        try:
            return ask(f"휴가 사용 RACE001 2026 1 parallel{index}")
        except ValueError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, range(3)))
    assert sum(item is not None for item in outcomes) == 1
    assert ask("연차 RACE001 2026 잔여")["remaining"] == 0


def test_transaction_rollback_and_year_isolation():
    ask("직원 등록 YEAR001 연도직원 연도팀 2025-01-01 2026 15")
    with pytest.raises(ValueError):
        ask("직원 등록 YEAR001 연도직원 연도팀 2025-01-01 2026 20")
    ask("직원 등록 YEAR001 연도직원 연도팀 2025-01-01 2027 16")
    ask("휴가 사용 YEAR001 2026 15 year01")
    assert ask("연차 YEAR001 2027 잔여")["remaining"] == 16
    assert ask("연차 YEAR001 2026 잔여")["remaining"] == 0


@pytest.mark.parametrize(
    "query",
    [
        "직원 없음 조회",
        "직원 등록 BAD001 오류 검증팀 2025-02-29 2026 15",
        "직원 등록 BAD001 오류 검증팀 2025-01-01 2024 15",
        "직원 등록 BAD001 오류 검증팀 2025-01-01 2026 -1",
        "직원 등록 BAD001 오류 검증팀 2025-01-01 2026 NaN",
        "직원 등록 BAD001 오류 검증팀 2025-01-01 2026 1.1",
        "직원 등록 BAD001 오류 검증팀 2025-01-01 2026 367",
        "부서 ' OR 1=1 인원",
        "연차 UNIT001 1900 잔여",
        "직원 삭제 UNIT001",
    ],
)
def test_invalid_requests(query):
    with pytest.raises(ValueError):
        ask(query)


@pytest.mark.parametrize(
    "data", [None, {}, {"query": None}, {"query": ""}, {"query": "x" * 301}, {"query": "도움말", "extra": 1}]
)
def test_invalid_shape(data):
    with pytest.raises(ValueError):
        run(data)
