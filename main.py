import pandas as pd
import itertools
import requests
import json
import os
from collections import Counter

# =====================================
# 파일명 정의
# =====================================
BASE_EXCEL = "로또당첨번호.xlsx"
ADD_EXCEL = "로또당첨번호추가.xlsx"

# =====================================
# 1️ 기본 엑셀 로드
# =====================================
if not os.path.exists(BASE_EXCEL):
    raise FileNotFoundError(f"{BASE_EXCEL} 파일이 없습니다.")

df_base = pd.read_excel(BASE_EXCEL)

# =====================================
# 2️ 추가 엑셀 있으면 병합 (맨 위로)
# =====================================
if os.path.exists(ADD_EXCEL):
    print("📌 추가 엑셀 발견 → 맨 위로 병합")

    df_add = pd.read_excel(ADD_EXCEL)

    # 🔥 추가 엑셀을 맨 위로
    df_merged = pd.concat([df_add, df_base], ignore_index=True)

    # 중복 제거
    df_merged = df_merged.drop_duplicates()

    # 저장
    df_merged.to_excel(BASE_EXCEL, index=False)

    # 추가 엑셀 삭제
    os.remove(ADD_EXCEL)
    print("✅ 병합 완료 (추가 엑셀 맨 위)")

else:
    df_merged = df_base
    print("📌 추가 엑셀 없음")


# =====================================
# 3️ 당첨번호 컬럼
# =====================================
num_cols = [
    '당첨번호',
    'Unnamed: 3',
    'Unnamed: 4',
    'Unnamed: 5',
    'Unnamed: 6',
    'Unnamed: 7'
]
BONUS_COL = "보너스"  # ← 실제 엑셀 컬럼명에 맞게 수정
# =====================================
# 4️ 자리별 최다 출현
# =====================================
position_stats = []
for idx, col in enumerate(num_cols, start=1):
    vc = df_merged[col].value_counts()
    position_stats.append({
        "position": idx,
        "number": int(vc.idxmax()),
        "count": int(vc.max())
    })

df_position = pd.DataFrame(position_stats)

# =====================================
# 5️ 숫자별 등장 횟수
# =====================================
all_numbers = df_merged[num_cols].values.flatten()
number_counter = Counter(all_numbers)

df_number = pd.DataFrame(
    sorted(number_counter.items()),
    columns=["number", "count"]
)

# =====================================
# 6️ 숫자 2개 동시 출현
# =====================================
pair_counter = Counter()
for row in df_merged[num_cols].values:
    for a, b in itertools.combinations(sorted(row), 2):
        pair_counter[(a, b)] += 1

df_pair = pd.DataFrame(
    [(a, b, cnt) for (a, b), cnt in pair_counter.items()],
    columns=["a", "b", "count"]
).sort_values("count", ascending=False)
    
# =====================================
# 7 전회차 → 다음회차 번호 전이 통계
# =====================================
transition_counter = Counter()

numbers_only = df_merged[num_cols].values

for i in range(len(numbers_only) - 1):
    prev_nums = numbers_only[i]
    next_nums = numbers_only[i + 1]

    for p in prev_nums:
        for n in next_nums:
            transition_counter[(int(p), int(n))] += 1

df_transition = pd.DataFrame(
    [(p, n, cnt) for (p, n), cnt in transition_counter.items()],
    columns=["prev", "next", "count"]
).sort_values("count", ascending=False)

# ==================================================
# 8 최신 회차 + 당첨금 정보
# ==================================================
LOTTO_INFO_URL = "https://www.dhlottery.co.kr/lt645/selectPstLt645Info.do"

res = requests.get(
    LOTTO_INFO_URL,
    params={"srchLtEpsd": "all"},
    headers=HEADERS
)
res.raise_for_status()

data = res.json()
latest = data["data"]["list"][-1]

latest_round = latest["ltEpsd"]
draw_date = latest["ltRflYmd"]

prize = {}
for rank in range(1, 6):
    prize[f"rank{rank}"] = {
        "total_amount": latest[f"rnk{rank}SumWnAmt"],
        "winner_count": latest[f"rnk{rank}WnNope"],
        "per_game_amount": latest[f"rnk{rank}WnAmt"]
    }

# ==================================================
# 9 판매점 정보 (1등 / 2등)
# ==================================================
SHOP_URL = "https://www.dhlottery.co.kr/wnprchsplcsrch/selectLtWnShp.do"

def fetch_shops(rank):
    res = requests.get(
        SHOP_URL,
        params={
            "srchWnShpRnk": rank,
            "srchLtEpsd": latest_round,
            "srchShpLctn": ""
        },
        headers=HEADERS
    )
    res.raise_for_status()
    data = res.json()

    shop_list = []

    for item in data["data"]["list"]:
        address = " ".join([
            p for p in [
                item.get("tm1ShpLctnAddr"),
                item.get("tm2ShpLctnAddr"),
                item.get("tm3ShpLctnAddr"),
                item.get("tm4ShpLctnAddr")
            ] if p
        ])

        shop_list.append({
            "shop_name": item.get("shpNm"),
            "address": address,
            "type": item.get("atmtPsvYnTxt"),
            "lat": item.get("shpLat"),
            "lng": item.get("shpLot")
        })

    return {
        "total": data["data"]["total"],
        "list": shop_list
    }

shops = {
    "rank1": fetch_shops(1),
    "rank2": fetch_shops(2)
}

# ==================================================
# 10 최종 JSON
# ==================================================
final_result = {
    "round": latest_round,
    "draw_date": draw_date,
    "prize": prize,
    "shops": shops
}

# ==================================================
# 11 JSON 파일 저장 (있으면 덮어쓰기)
# ==================================================
FILE_NAME = "latest_lotto.json"

with open(FILE_NAME, "w", encoding="utf-8") as f:
    json.dump(final_result, f, ensure_ascii=False, indent=2)
    
# =====================================
# 12 분석 결과 JSON (Unity용)
# =====================================
stats_json = {
    "total_rounds": len(df_merged),
    "position_stats": df_position.to_dict(orient="records"),
    "number_stats": df_number.to_dict(orient="records"),
    "pair_stats": df_pair.to_dict(orient="records"),
    "transition_stats": df_transition.to_dict(orient="records")  # 🔥 추가
}

with open("lotto_stats.json", "w", encoding="utf-8") as f:
    json.dump(stats_json, f, ensure_ascii=False, indent=2)

# =====================================
# 13 전체 회차 JSON (🔥 추가된 부분)
# =====================================
history_rows = []

for _, row in df_merged.iterrows():
    history_rows.append({
    "round": int(row["회차"]) if "회차" in row else None,
    "numbers": [
        int(row[col]) for col in num_cols
    ],
    "bonus": int(row[BONUS_COL]) if BONUS_COL in row and not pd.isna(row[BONUS_COL]) else None
})

history_json = {
    "total_rounds": len(history_rows),
    "history": history_rows
}

with open("lotto_history.json", "w", encoding="utf-8") as f:
    json.dump(history_json, f, ensure_ascii=False, indent=2)





