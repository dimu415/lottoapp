import pandas as pd
import itertools
import json
import os
from collections import Counter

# =====================================
# 파일명 정의
# =====================================
BASE_EXCEL = "로또당첨번호.xlsx"
ADD_EXCEL = "로또당첨번호추가.xlsx"

# =====================================
# 1️⃣ 기본 엑셀 로드
# =====================================
if not os.path.exists(BASE_EXCEL):
    raise FileNotFoundError(f"{BASE_EXCEL} 파일이 없습니다.")

df_base = pd.read_excel(BASE_EXCEL)

# =====================================
# 2️⃣ 추가 엑셀 병합
# =====================================
if os.path.exists(ADD_EXCEL):
    print("📌 추가 엑셀 발견 → 병합")

    df_add = pd.read_excel(ADD_EXCEL)
    df_merged = pd.concat([df_base, df_add], ignore_index=True)
    df_merged = df_merged.drop_duplicates()

    df_merged.to_excel(BASE_EXCEL, index=False)
    os.remove(ADD_EXCEL)

else:
    df_merged = df_base

# =====================================
# 3️⃣ 당첨번호 컬럼
# =====================================
num_cols = [
    '당첨번호',
    'Unnamed: 3',
    'Unnamed: 4',
    'Unnamed: 5',
    'Unnamed: 6',
    'Unnamed: 7'
]

# =====================================
# 4️⃣ 자리별 최다 출현
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
# 5️⃣ 숫자별 등장 횟수
# =====================================
all_numbers = df_merged[num_cols].values.flatten()
number_counter = Counter(all_numbers)

df_number = pd.DataFrame(
    sorted(number_counter.items()),
    columns=["number", "count"]
)

# =====================================
# 6️⃣ 숫자 2개 동시 출현
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
# 7️⃣ 분석 결과 JSON (Unity용)
# =====================================
stats_json = {
    "total_rounds": len(df_merged),
    "position_stats": df_position.to_dict(orient="records"),
    "number_stats": df_number.to_dict(orient="records"),
    "pair_stats": df_pair.to_dict(orient="records")
}

with open("lotto_stats.json", "w", encoding="utf-8") as f:
    json.dump(stats_json, f, ensure_ascii=False, indent=2)

# =====================================
# 8️⃣ 전체 회차 JSON (🔥 추가된 부분)
# =====================================
history_rows = []

for _, row in df_merged.iterrows():
    history_rows.append({
        "round": int(row["회차"]) if "회차" in row else None,
        "numbers": [
            int(row[col]) for col in num_cols
        ]
    })

history_json = {
    "total_rounds": len(history_rows),
    "history": history_rows
}

with open("lotto_history.json", "w", encoding="utf-8") as f:
    json.dump(history_json, f, ensure_ascii=False, indent=2)

# =====================================
# 9️⃣ 완료 로그
# =====================================
print("✅ 전체 처리 완료")
print(f"- 총 회차 수: {len(df_merged)}")
print("👉 lotto_stats.json 생성")
print("👉 lotto_history.json 생성")
