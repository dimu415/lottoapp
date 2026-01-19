import os
import json
import itertools
import requests
from datetime import datetime
from collections import Counter

import pandas as pd


# ==================================================
# 📁 경로 설정
# ==================================================
CODE_DIR = os.path.dirname(os.path.abspath(__file__))           # home/code
BASE_DIR = os.path.dirname(CODE_DIR)                           # home
JSON_DIR = os.path.join(BASE_DIR, "Analysis_file", "json")      # home/Analysis_file/json
os.makedirs(JSON_DIR, exist_ok=True)

HISTORY_PATH = os.path.join(JSON_DIR, "lotto_history.json")
LATEST_PATH = os.path.join(JSON_DIR, "latest_lotto.json")
STATS_PATH = os.path.join(JSON_DIR, "lotto_stats.json")
STATS_LAST10_PATH = os.path.join(JSON_DIR, "lotto_stats_last10.json")


# ==================================================
# 🌐 API 설정
# ==================================================
HEADERS = {"User-Agent": "Mozilla/5.0"}

# ✅ 너가 말한 "여기서 전부 가져오는" API
LOTTO_INFO_URL = "https://www.dhlottery.co.kr/lt645/selectPstLt645Info.do"

# 판매점 (1등/2등)
SHOP_URL = "https://www.dhlottery.co.kr/wnprchsplcsrch/selectLtWnShp.do"


# ==================================================
# 🔥 전멸 구간 정의
# ==================================================
RANGES = {
    "1_10": range(1, 11),
    "11_20": range(11, 21),
    "21_30": range(21, 31),
    "31_40": range(31, 41),
    "41_45": range(41, 46),
}


# ==================================================
# ✅ 유틸: JSON 로드/저장
# ==================================================
def load_json(path: str, default_obj):
    if not os.path.exists(path):
        return default_obj
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def safe_json(res: requests.Response):
    """JSON이 아니면 에러 원인 확인 가능하게 미리보기 포함"""
    try:
        return res.json()
    except Exception:
        preview = res.text[:300].replace("\n", "\\n")
        raise RuntimeError(
            f"❌ JSONDecodeError: JSON이 아니라 HTML/텍스트가 왔습니다.\n"
            f"status={res.status_code}, content-type={res.headers.get('Content-Type')}\n"
            f"preview={preview}"
        )


# ==================================================
# ✅ 1) 최신회차 (번호/보너스/날짜/당첨금) 가져오기
#    selectPstLt645Info.do 에서 끝냄
# ==================================================
def fetch_latest_from_pst_info():
    res = requests.get(
        LOTTO_INFO_URL,
        params={"srchLtEpsd": "all"},
        headers=HEADERS,
        timeout=20
    )
    res.raise_for_status()
    data = safe_json(res)

    lst = data.get("data", {}).get("list", [])
    if not lst:
        raise RuntimeError("❌ selectPstLt645Info.do 응답 list가 비어있음")

    latest = lst[-1]

    latest_round = int(latest["ltEpsd"])
    draw_date = str(latest.get("ltRflYmd"))  # "20260117"

    numbers = [
        int(latest["tm1WnNo"]),
        int(latest["tm2WnNo"]),
        int(latest["tm3WnNo"]),
        int(latest["tm4WnNo"]),
        int(latest["tm5WnNo"]),
        int(latest["tm6WnNo"]),
    ]
    bonus = int(latest["bnsWnNo"])

    # 당첨금(1~5등)
    prize = {}
    for rank in range(1, 6):
        prize[f"rank{rank}"] = {
            "total_amount": latest.get(f"rnk{rank}SumWnAmt"),
            "winner_count": latest.get(f"rnk{rank}WnNope"),
            "per_game_amount": latest.get(f"rnk{rank}WnAmt"),
        }

    return {
        "round": latest_round,
        "draw_date": draw_date,
        "numbers": numbers,
        "bonus": bonus,
        "prize": prize,
    }


# ==================================================
# ✅ 2) 판매점 정보 (1등 / 2등)
# ==================================================
def fetch_shops(latest_round: int, rank: int):
    res = requests.get(
        SHOP_URL,
        params={
            "srchWnShpRnk": rank,
            "srchLtEpsd": latest_round,
            "srchShpLctn": ""
        },
        headers=HEADERS,
        timeout=20
    )
    res.raise_for_status()
    data = safe_json(res).get("data", {})

    shop_list = []
    for item in data.get("list", []):
        address = " ".join(
            p for p in [
                item.get("tm1ShpLctnAddr"),
                item.get("tm2ShpLctnAddr"),
                item.get("tm3ShpLctnAddr"),
                item.get("tm4ShpLctnAddr"),
            ] if p
        )
        shop_list.append({
            "shop_name": item.get("shpNm"),
            "address": address,
            "type": item.get("atmtPsvYnTxt"),
            "lat": item.get("shpLat"),
            "lng": item.get("shpLot"),
        })

    return {"total": data.get("total", 0), "list": shop_list}


# ==================================================
# ✅ 3) JSON DB(history) 업데이트
# ==================================================
def update_history_db(history_json: dict, new_row: dict):
    history = history_json.get("history", [])
    existing_rounds = {int(x["round"]) for x in history if x.get("round") is not None}

    rno = int(new_row["round"])
    if rno in existing_rounds:
        return history_json, False

    # 최신회차는 맨 앞에 삽입
    history.insert(0, new_row)
    history_json["history"] = history
    history_json["total_rounds"] = len(history)
    return history_json, True


# ==================================================
# ✅ 4) 분석 함수 (전체/최근10 재사용)
# ==================================================
def analyze_history(history_rows: list):
    """
    history_rows: [
      {"round":int, "numbers":[6개], "bonus":int, "draw_date":str}
    ]
    """
    if not history_rows:
        return {
            "total_rounds": 0,
            "position_stats": [],
            "number_stats": [],
            "pair_stats": [],
            "transition_stats": [],
            "odd_even_stats": [],
            "sum_stats": [],
            "annihilation_stats": {"by_range": {}, "by_round": []}
        }

    numbers = [row["numbers"] for row in history_rows if row.get("numbers")]

    # 자리별 최다
    position_stats = []
    for pos in range(6):
        col_vals = [nums[pos] for nums in numbers if len(nums) == 6]
        vc = Counter(col_vals)
        most_num, most_cnt = vc.most_common(1)[0]
        position_stats.append({
            "position": pos + 1,
            "number": int(most_num),
            "count": int(most_cnt)
        })

    # 번호별 출현
    number_counter = Counter([n for nums in numbers for n in nums])
    df_number = pd.DataFrame(
        [(int(k), int(v)) for k, v in number_counter.items()],
        columns=["number", "count"]
    ).sort_values("number")

    # 동반 출현
    pair_counter = Counter()
    for row in numbers:
        for a, b in itertools.combinations(sorted(row), 2):
            pair_counter[(a, b)] += 1

    df_pair = pd.DataFrame(
        [(int(a), int(b), int(c)) for (a, b), c in pair_counter.items()],
        columns=["a", "b", "count"]
    ).sort_values("count", ascending=False)

    # 전이 (회차 오름차순 의미 유지)
    sorted_rows = sorted(
        [r for r in history_rows if r.get("round") is not None and r.get("numbers")],
        key=lambda x: int(x["round"])
    )

    transition_counter = Counter()
    for i in range(len(sorted_rows) - 1):
        prev_nums = sorted_rows[i]["numbers"]
        next_nums = sorted_rows[i + 1]["numbers"]
        for p in prev_nums:
            for n in next_nums:
                transition_counter[(int(p), int(n))] += 1

    df_transition = pd.DataFrame(
        [(int(p), int(n), int(c)) for (p, n), c in transition_counter.items()],
        columns=["prev", "next", "count"]
    ).sort_values("count", ascending=False)

    # 홀짝 & 합계
    odd_even_counter = Counter()
    sum_counter = Counter()
    for row in numbers:
        odd = sum(1 for x in row if x % 2 == 1)
        even = 6 - odd
        odd_even_counter[(odd, even)] += 1
        sum_counter[int(sum(row))] += 1

    df_odd_even = pd.DataFrame(
        [(int(o), int(e), int(c)) for (o, e), c in odd_even_counter.items()],
        columns=["odd", "even", "count"]
    ).sort_values("count", ascending=False)

    df_sum = pd.DataFrame(
        [(int(s), int(c)) for s, c in sum_counter.items()],
        columns=["sum", "count"]
    ).sort_values("sum")

    # 전멸
    annihilation_counter = Counter()
    annihilation_per_round = []

    for row in history_rows:
        rno = row.get("round")
        nums = set(row.get("numbers", []))
        dead_ranges = []

        for key, rr in RANGES.items():
            if not any(n in rr for n in nums):
                dead_ranges.append(key)
                annihilation_counter[key] += 1

        annihilation_per_round.append({
            "round": int(rno) if rno is not None else None,
            "count": len(dead_ranges),
            "ranges": dead_ranges
        })

    return {
        "total_rounds": len(history_rows),
        "position_stats": position_stats,
        "number_stats": df_number.to_dict("records"),
        "pair_stats": df_pair.to_dict("records"),
        "transition_stats": df_transition.to_dict("records"),
        "odd_even_stats": df_odd_even.to_dict("records"),
        "sum_stats": df_sum.to_dict("records"),
        "annihilation_stats": {
            "by_range": dict(annihilation_counter),
            "by_round": annihilation_per_round
        }
    }


# ==================================================
# ✅ MAIN
# ==================================================
def main():
    # 0) DB 로드
    history_json = load_json(HISTORY_PATH, {"total_rounds": 0, "history": []})

    # 1) 최신회차(번호/보너스/날짜/당첨금) 가져오기
    latest = fetch_latest_from_pst_info()

    latest_round = int(latest["round"])

    # 2) history DB 업데이트 (엑셀 없음)
    history_row = {
        "round": latest_round,
        "draw_date": latest["draw_date"],
        "numbers": latest["numbers"],
        "bonus": latest["bonus"]
    }

    history_json, changed = update_history_db(history_json, history_row)
    if changed:
        save_json(HISTORY_PATH, history_json)
        print(f"🆕 신규 회차 {latest_round} → lotto_history.json에 추가 완료")
    else:
        print(f"✅ 회차 {latest_round} 이미 존재 → lotto_history.json 추가 스킵")

    # 3) 판매점 정보까지 붙여서 latest_lotto.json 저장
    shops = {
        "rank1": fetch_shops(latest_round, 1),
        "rank2": fetch_shops(latest_round, 2)
    }

    latest_lotto_json = {
        "round": latest_round,
        "draw_date": latest["draw_date"],
        "numbers": latest["numbers"],
        "bonus": latest["bonus"],
        "prize": latest["prize"],
        "shops": shops,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_json(LATEST_PATH, latest_lotto_json)

    # 4) 전체 통계 생성
    full_history = history_json.get("history", [])
    stats_all = analyze_history(full_history)

    stats_all_json = {
        "base": "all",
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **stats_all
    }
    save_json(STATS_PATH, stats_all_json)

    # 5) 최근 10회 통계 생성
    last10 = full_history[:10]
    stats_last10 = analyze_history(last10)

    stats_last10_json = {
        "base": "last10",
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **stats_last10
    }
    save_json(STATS_LAST10_PATH, stats_last10_json)

    print("✅ 완료! JSON DB 기반 자동 업데이트 성공")
    print("   - lotto_history.json")
    print("   - latest_lotto.json")
    print("   - lotto_stats.json")
    print("   - lotto_stats_last10.json")


if __name__ == "__main__":
    main()
