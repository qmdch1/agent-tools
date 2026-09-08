"""Small deterministic HRMS; annual allowances are supplied by the HR administrator."""

import json
import os
import re
import sys
from datetime import date
from decimal import Decimal, InvalidOperation

import psycopg
from psycopg.rows import dict_row


def token(value):
    if not re.fullmatch(r"[A-Za-z0-9가-힣_-]{1,40}", value):
        raise ValueError("식별자·이름·부서는 1~40자의 문자, 숫자, 밑줄, 하이픈만 사용하세요.")
    return value


def year_value(value):
    if not re.fullmatch(r"20[0-9]{2}", value):
        raise ValueError("연도는 2000~2099 범위로 입력하세요.")
    return int(value)


def days_value(value):
    try:
        number = Decimal(value)
    except InvalidOperation:
        raise ValueError("휴가 일수를 확인하세요.") from None
    if not number.is_finite() or number < 0 or number > 366 or number * 2 != int(number * 2):
        raise ValueError("휴가 일수는 0~366 범위의 0.5일 단위여야 합니다.")
    return number


def result(answer, *, storage_action="read", record_type="인사 정보", record_id=None, **data):
    storage = {"action": storage_action, "record_type": record_type}
    if record_id is not None:
        storage["record_id"] = record_id
    return {"answer": answer, "data": data, "storage": storage}


def employee(conn, staff_id):
    rows = conn.execute("SELECT * FROM employees WHERE staff_id=%s LIMIT 2", (staff_id,)).fetchall()
    if len(rows) != 1:
        raise ValueError("직원이 없거나 중복 등록되어 있습니다.")
    return rows[0]


def balance(conn, staff_id, year):
    rows = conn.execute(
        "SELECT granted_days FROM allowances WHERE staff_id=%s AND leave_year=%s LIMIT 2",
        (staff_id, year),
    ).fetchall()
    if len(rows) != 1:
        raise ValueError("해당 연도에 승인된 연차 배정이 없거나 중복되어 있습니다.")
    used = conn.execute(
        "SELECT COALESCE(sum(days),0) AS days FROM leave_events WHERE staff_id=%s AND leave_year=%s",
        (staff_id, year),
    ).fetchone()["days"]
    granted = rows[0]["granted_days"]
    return {
        "staff_id": staff_id,
        "year": year,
        "granted": float(granted),
        "used": float(used),
        "remaining": float(granted - used),
    }


def lock(conn, staff_id):
    conn.execute(
        "SELECT pg_advisory_xact_lock(hashtextextended(current_schema() || ':hrms:' || %s,0))", (staff_id,)
    )


def run(input_data: dict) -> dict:
    if not isinstance(input_data, dict) or set(input_data) != {"query"}:
        raise ValueError("query만 입력하세요.")
    query = input_data["query"]
    if not isinstance(query, str) or not 1 <= len(query) <= 300:
        raise ValueError("질문은 1~300자로 입력하세요.")
    parts = query.strip().split()
    if parts == ["도움말"]:
        return result(
            "직원 등록·조회, 부서별 인원, 연차 잔여·사용 기록을 관리합니다.",
            commands=[
                "직원 등록 사번 이름 부서 입사일 연도 배정일수",
                "직원 사번 조회",
                "부서 부서명 인원",
                "연차 사번 연도 잔여",
                "휴가 사용 사번 연도 일수 요청번호",
                "인사 요약",
            ],
        )
    with psycopg.connect(os.environ["FOUNDRY_TOOL_DATABASE_URL"], row_factory=dict_row) as conn:
        if len(parts) == 8 and parts[:2] == ["직원", "등록"]:
            staff_id, name, department = map(token, parts[2:5])
            joined = date.fromisoformat(parts[5]).isoformat()
            year, granted = year_value(parts[6]), days_value(parts[7])
            if date.fromisoformat(joined).year > year:
                raise ValueError("입사 연도 이전에는 연차를 배정할 수 없습니다.")
            lock(conn, staff_id)
            old = conn.execute("SELECT * FROM employees WHERE staff_id=%s LIMIT 2", (staff_id,)).fetchall()
            expected = {"staff_id": staff_id, "name": name, "department": department, "joined_on": joined}
            if old and (len(old) != 1 or old[0] != expected):
                raise ValueError("같은 사번에 다른 인사 정보가 이미 등록되어 있습니다.")
            if not old:
                conn.execute(
                    "INSERT INTO employees(staff_id,name,department,joined_on) VALUES (%s,%s,%s,%s)",
                    (staff_id, name, department, joined),
                )
            allocations = conn.execute(
                "SELECT granted_days FROM allowances WHERE staff_id=%s AND leave_year=%s LIMIT 2",
                (staff_id, year),
            ).fetchall()
            if allocations and (len(allocations) != 1 or allocations[0]["granted_days"] != granted):
                raise ValueError("같은 연도에 다른 연차 배정이 이미 등록되어 있습니다.")
            if not allocations:
                conn.execute(
                    "INSERT INTO allowances(staff_id,leave_year,granted_days) VALUES (%s,%s,%s)",
                    (staff_id, year, granted),
                )
            return result(
                f"{name}({staff_id})의 {year}년 인사 등록이 완료되었습니다.",
                storage_action="created" if not old or not allocations else "reused",
                record_type="직원·연차 배정",
                record_id=f"{staff_id}:{year}",
                **expected,
                **{k: v for k, v in balance(conn, staff_id, year).items() if k != "staff_id"},
            )
        if len(parts) == 3 and parts[0] == "직원" and parts[2] == "조회":
            row = employee(conn, token(parts[1]))
            return result(
                f"{row['name']}({row['staff_id']}) · {row['department']} · 입사일 {row['joined_on']}", **row
            )
        if len(parts) == 3 and parts[0] == "부서" and parts[2] == "인원":
            department = token(parts[1])
            count = conn.execute(
                "SELECT count(*) AS count FROM employees WHERE department=%s", (department,)
            ).fetchone()["count"]
            return result(f"{department} 인원은 {count}명입니다.", department=department, count=count)
        if len(parts) == 4 and parts[0] == "연차" and parts[3] == "잔여":
            staff_id, year = token(parts[1]), year_value(parts[2])
            employee(conn, staff_id)
            data = balance(conn, staff_id, year)
            return result(f"{staff_id}의 {year}년 잔여 연차는 {data['remaining']:g}일입니다.", **data)
        if len(parts) == 6 and parts[:2] == ["휴가", "사용"]:
            staff_id, year, days, request_id = (
                token(parts[2]),
                year_value(parts[3]),
                days_value(parts[4]),
                token(parts[5]),
            )
            if days == 0:
                raise ValueError("휴가 사용 일수는 0보다 커야 합니다.")
            lock(conn, staff_id)
            employee(conn, staff_id)
            old = conn.execute(
                "SELECT leave_year,days FROM leave_events WHERE staff_id=%s AND request_id=%s LIMIT 2",
                (staff_id, request_id),
            ).fetchall()
            if old and (len(old) != 1 or old[0]["leave_year"] != year or old[0]["days"] != days):
                raise ValueError("동일 요청번호에 다른 휴가 기록이 존재합니다.")
            data = balance(conn, staff_id, year)
            if not old:
                if days > Decimal(str(data["remaining"])):
                    raise ValueError("잔여 연차가 부족합니다.")
                conn.execute(
                    "INSERT INTO leave_events(staff_id,leave_year,days,request_id) VALUES (%s,%s,%s,%s)",
                    (staff_id, year, days, request_id),
                )
            return result(
                f"{staff_id}의 휴가 기록을 확인했습니다. 동일 요청은 한 번만 차감됩니다.",
                storage_action="reused" if old else "created",
                record_type="휴가 사용",
                record_id=f"{staff_id}:{request_id}",
                **balance(conn, staff_id, year),
                request_id=request_id,
                replayed=bool(old),
            )
        if parts == ["인사", "요약"]:
            rows = conn.execute(
                "SELECT department,count(*) AS count FROM employees GROUP BY department ORDER BY department LIMIT 100"
            ).fetchall()
            total = conn.execute("SELECT count(*) AS count FROM employees").fetchone()["count"]
            return result(f"등록 직원은 총 {total}명입니다.", total=total, departments=rows)
    raise ValueError("지원하는 인사 요청 형식을 확인하세요. HRMS 도움말로 확인할 수 있습니다.")


if __name__ == "__main__":
    print(json.dumps(run(json.load(sys.stdin)), ensure_ascii=False, allow_nan=False))
