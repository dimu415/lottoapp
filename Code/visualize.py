import os
import json
import math
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager

# ==================================================
# 📁 경로 설정
# ==================================================
CODE_DIR = os.path.dirname(os.path.abspath(__file__))                 # home/code
BASE_DIR = os.path.dirname(CODE_DIR)                                  # home
JSON_DIR = os.path.join(BASE_DIR, "Analysis_file", "json")            # home/Analysis_file/json
OUT_DIR = os.path.join(BASE_DIR, "Analysis_file", "visualizations")   # home/Analysis_file/visualizations
os.makedirs(OUT_DIR, exist_ok=True)

STATS_PATH = os.path.join(JSON_DIR, "lotto_stats.json")
HISTORY_PATH = os.path.join(JSON_DIR, "lotto_history.json")

# ==================================================
# ✅ 저장 이미지 크기 통일 (2048x2048)
# ==================================================
TARGET_W = 2048
TARGET_H = 2048
SAVE_DPI = 256
FIXED_FIGSIZE = (TARGET_W / SAVE_DPI, TARGET_H / SAVE_DPI)

# ==================================================
# ✅ 폰트 설정 (같은 폴더의 Maplestory Bold.ttf)
# ==================================================
FONT_FILE = "Maplestory Bold.ttf"
FONT_PATH = os.path.join(CODE_DIR, FONT_FILE)

font_prop = None
if os.path.exists(FONT_PATH):
    font_prop = font_manager.FontProperties(fname=FONT_PATH)
    plt.rcParams["font.family"] = font_prop.get_name()
plt.rcParams["axes.unicode_minus"] = False

# ==================================================
# 🎨 색상 규칙
# ==================================================
def number_bg_color(n: int):
    """
    1~10 노란색
    11~20 파란색
    21~30 자주색
    31~40 연한회색
    41~45 초록색
    """
    if 1 <= n <= 10:
        return "#FFF176"
    if 11 <= n <= 20:
        return "#64B5F6"
    if 21 <= n <= 30:
        return "#BA68C8"
    if 31 <= n <= 40:
        return "#E0E0E0"
    if 41 <= n <= 45:
        return "#81C784"
    return "white"

# ==================================================
# 🧱 공통: 폴더 생성
# ==================================================
def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

# ==================================================
# ✅ 공통: DataFrame → PNG(표 이미지) 저장
#    - 제목/표 거리 가까움
#    - 자동으로 표 크기 맞춤 (겹침/잘림 줄임)
# ==================================================
def df_to_table_image(
    df: pd.DataFrame,
    save_path: str,
    title: str = "",
    color_columns=None,
    col_widths=None,
    font_prop=None,
    title_fontsize=26,
    base_fontsize=16
):
    fig, ax = plt.subplots(figsize=FIXED_FIGSIZE, dpi=SAVE_DPI)
    ax.axis("off")

    # ✅ 여백 (왼쪽 라벨 잘림 방지에도 도움)
    fig.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.06)

    # ✅ 제목을 축 안쪽에 직접 찍는다 (표와 거리 확 줄어듦)
    if title:
        ax.text(
            0.5, 0.97, title,
            ha="center", va="top",
            fontsize=title_fontsize,
            transform=ax.transAxes,
            fontproperties=font_prop if font_prop else None
        )

    # ✅ 데이터 없음
    if df is None or df.empty:
        ax.text(
            0.5, 0.5, "데이터 없음",
            ha="center", va="center",
            fontsize=title_fontsize,
            transform=ax.transAxes,
            fontproperties=font_prop if font_prop else None
        )
        ensure_dir(os.path.dirname(save_path))
        plt.savefig(save_path, dpi=SAVE_DPI, transparent=True)
        plt.close()
        return

    df_show = df.copy().reset_index(drop=True)
    row_count = len(df_show)

    # ✅ 행 많으면 폰트 자동 감소
    font_size = base_fontsize
    if row_count >= 20:
        font_size = min(font_size, 12)
    if row_count >= 35:
        font_size = min(font_size, 10)
    if row_count >= 55:
        font_size = min(font_size, 8)

    # ✅ 셀 높이 자동 조절
    scale_y = 1.15
    if row_count >= 20:
        scale_y = 1.05
    if row_count >= 35:
        scale_y = 0.95
    if row_count >= 55:
        scale_y = 0.88

    # ✅ 표를 위쪽으로 끌어올린다 (제목과 거리 최소화)
    table = ax.table(
        cellText=df_show.values,
        colLabels=df_show.columns,
        cellLoc="center",
        colLoc="center",
        colWidths=col_widths,
        bbox=[0.02, 0.05, 0.96, 0.86]  # ✅ 핵심: 표 위치/크기 직접 고정 (위로 올림)
    )

    table.auto_set_font_size(False)
    table.set_fontsize(font_size)
    table.scale(1.0, scale_y)

    # ✅ 표 폰트 적용
    if font_prop:
        for (r, c), cell in table.get_celld().items():
            cell.get_text().set_fontproperties(font_prop)

    # ✅ 특정 컬럼 색칠
    if color_columns:
        col_index_map = {c: i for i, c in enumerate(df_show.columns)}
        for col_name in color_columns:
            if col_name not in col_index_map:
                continue
            col_idx = col_index_map[col_name]
            for r in range(row_count):
                val = df_show.iloc[r, col_idx]
                try:
                    num = int(val)
                    table[(r + 1, col_idx)].set_facecolor(number_bg_color(num))
                except:
                    pass

    ensure_dir(os.path.dirname(save_path))
    plt.savefig(save_path, dpi=SAVE_DPI, transparent=True)
    plt.close()



# ==================================================
# 1) 번호 출현 횟수 랭킹 (10개씩 페이지)
# ✅ 제목: "번호 출현 랭킹" 고정
# ✅ 제목/표 거리 가까움
# ==================================================
def make_numbercount_images(stats_json):
    out_folder = os.path.join(OUT_DIR, "numbercount")
    ensure_dir(out_folder)

    df_number = pd.DataFrame(stats_json.get("number_stats", []))
    if df_number.empty:
        df_to_table_image(
            df_number,
            os.path.join(out_folder, "nc1.png"),
            "번호 출현 랭킹",
            ["번호"],
            font_prop=font_prop
        )
        return

    df_rank = df_number.sort_values("count", ascending=False).reset_index(drop=True)
    df_rank["랭킹"] = df_rank.index + 1
    df_rank.rename(columns={"number": "번호", "count": "출현횟수"}, inplace=True)
    df_rank = df_rank[["랭킹", "번호", "출현횟수"]]

    page_size = 10
    total_pages = 5
    col_widths = [0.18, 0.22, 0.25]

    for i in range(total_pages):
        start = i * page_size
        end = start + page_size
        page_df = df_rank.iloc[start:end].copy()

        save_path = os.path.join(out_folder, f"nc{i+1}.png")

        df_to_table_image(
            page_df,
            save_path,
            "번호 출현 랭킹",  # ✅ 제목 고정
            color_columns=["번호"],
            col_widths=col_widths,
            font_prop=font_prop,
            title_fontsize=26,
            base_fontsize=15
        )


# ==================================================
# 2) 최근 10회 당첨번호 표
# ✅ 글씨 너무 큼 -> base_fontsize 낮춤
# ✅ 제목/표 거리 줄임
# ==================================================
def make_recent10_image(history_json):
    out_folder = os.path.join(OUT_DIR, "recentNumber")
    ensure_dir(out_folder)

    history = history_json.get("history", [])
    if not history:
        df_to_table_image(
            pd.DataFrame(),
            os.path.join(out_folder, "rec1.png"),
            "최근 10회 당첨번호",
            font_prop=font_prop,
            title_fontsize=24,
            base_fontsize=12
        )
        return

    recent10 = history[:10]
    rows = []
    for item in recent10:
        nums = item.get("numbers", [])
        rows.append({
            "회차": item.get("round"),
            "숫자1": nums[0] if len(nums) > 0 else None,
            "숫자2": nums[1] if len(nums) > 1 else None,
            "숫자3": nums[2] if len(nums) > 2 else None,
            "숫자4": nums[3] if len(nums) > 3 else None,
            "숫자5": nums[4] if len(nums) > 4 else None,
            "숫자6": nums[5] if len(nums) > 5 else None,
            "보너스": item.get("bonus"),
        })

    df_recent = pd.DataFrame(rows)

    save_path = os.path.join(out_folder, "rec1.png")
    df_to_table_image(
        df_recent,
        save_path,
        "최근 10회 당첨번호",
        color_columns=["숫자1", "숫자2", "숫자3", "숫자4", "숫자5", "숫자6", "보너스"],
        col_widths=[0.16, 0.12, 0.12, 0.12, 0.12, 0.12, 0.12, 0.12],
        font_prop=font_prop,
        title_fontsize=24,
        base_fontsize=11
    )


# ==================================================
# 3) 동반출현 통계 (15회 이상)
# ✅ 제목: "동반출현" 만
# ✅ 제목/표 거리 가까움
# ==================================================
def make_pairstats_images(stats_json):
    out_folder = os.path.join(OUT_DIR, "pairStats")
    ensure_dir(out_folder)

    df_pair = pd.DataFrame(stats_json.get("pair_stats", []))
    if df_pair.empty:
        df_to_table_image(
            df_pair,
            os.path.join(out_folder, "ps1.png"),
            "동반출현",
            ["번호1", "번호2"],
            font_prop=font_prop
        )
        return

    df_pair = df_pair[df_pair["count"] >= 15].sort_values("count", ascending=False).reset_index(drop=True)

    if df_pair.empty:
        df_to_table_image(
            df_pair,
            os.path.join(out_folder, "ps1.png"),
            "동반출현",
            font_prop=font_prop
        )
        return

    df_pair["랭킹"] = df_pair.index + 1
    df_pair.rename(columns={"a": "번호1", "b": "번호2", "count": "횟수"}, inplace=True)
    df_pair = df_pair[["랭킹", "번호1", "번호2", "횟수"]]

    page_size = 15
    total_pages = 10
    col_widths = [0.16, 0.22, 0.22, 0.20]

    for i in range(total_pages):
        start = i * page_size
        end = start + page_size
        page_df = df_pair.iloc[start:end].copy()

        save_path = os.path.join(out_folder, f"ps{i+1}.png")

        df_to_table_image(
            page_df,
            save_path,
            "동반출현",  # ✅ 제목 고정
            color_columns=["번호1", "번호2"],
            col_widths=col_widths,
            font_prop=font_prop,
            title_fontsize=26,
            base_fontsize=13
        )


# ==================================================
# 4) 전이 Best: prev별로 next 최다 1개만
# ✅ 제목: "전이 TOP" 만
# ✅ 제목/표 거리 가까움
# ==================================================
def make_transition_best_images(stats_json):
    out_folder = os.path.join(OUT_DIR, "transitionBest")
    ensure_dir(out_folder)

    df_tr = pd.DataFrame(stats_json.get("transition_stats", []))
    if df_tr.empty:
        df_to_table_image(
            df_tr,
            os.path.join(out_folder, "tb1.png"),
            "전이",
            font_prop=font_prop
        )
        return

    df_tr = df_tr.sort_values(["prev", "count"], ascending=[True, False])

    best_rows = []
    for prev in range(1, 46):
        sub = df_tr[df_tr["prev"] == prev]
        if sub.empty:
            best_rows.append({"번호": prev, "다음회차 최다번호": None, "횟수": 0})
        else:
            top = sub.iloc[0]
            best_rows.append({
                "번호": int(top["prev"]),
                "다음회차 최다번호": int(top["next"]),
                "횟수": int(top["count"])
            })

    df_best = pd.DataFrame(best_rows)

    page_size = 10
    total_pages = math.ceil(len(df_best) / page_size)
    col_widths = [0.18, 0.40, 0.20]

    for i in range(total_pages):
        start = i * page_size
        end = start + page_size
        page_df = df_best.iloc[start:end].copy()

        save_path = os.path.join(out_folder, f"tb{i+1}.png")

        df_to_table_image(
            page_df,
            save_path,
            "전이 TOP",  # ✅ 제목 고정
            color_columns=["번호", "다음회차 최다번호"],
            col_widths=col_widths,
            font_prop=font_prop,
            title_fontsize=26,
            base_fontsize=13
        )


# ==================================================
# 5) 합계 20단위 버킷 - 비율 막대그래프
# ✅ 하단 글씨 겹침 -> 짧게 + 회전 + 폰트 작게
# ✅ 시작 구간: 41~60 부터 나오게 (1~20 제거)
# ==================================================
def make_sum_bucket_bar(stats_json):
    out_folder = os.path.join(OUT_DIR, "sumBucket")
    ensure_dir(out_folder)

    df_sum = pd.DataFrame(stats_json.get("sum_stats", []))
    if df_sum.empty:
        fig, ax = plt.subplots(figsize=FIXED_FIGSIZE, dpi=SAVE_DPI)
        fig.subplots_adjust(left=0.95, right=0.95, top=0.90, bottom=0.22)

        ax.axis("off")
        ax.text(0.5, 0.5, "sum_stats 데이터 없음", ha="center", va="center",
                fontsize=20, fontproperties=font_prop if font_prop else None)
        plt.savefig(os.path.join(out_folder, "sum_bucket.png"), dpi=SAVE_DPI, transparent=True)
        plt.close()
        return

    df_sum["sum"] = df_sum["sum"].astype(int)
    df_sum["count"] = df_sum["count"].astype(int)

    # ✅ 20단위 버킷을 21부터 시작하도록 변경 (1~20 제거)
    def bucket_label(s):
        # 21~40, 41~60, 61~80 ...
        start = ((s - 21) // 20) * 20 + 21
        end = start + 19
        return f"{start}~{end}"

    df_sum["bucket"] = df_sum["sum"].apply(bucket_label)
    bucket_df = df_sum.groupby("bucket")["count"].sum().reset_index()

    total = bucket_df["count"].sum()
    bucket_df["ratio"] = (bucket_df["count"] / total) * 100

    # ✅ 시작을 41~60부터 보여주고 싶다 -> 정렬 후 21~40은 제거(있으면)
    def start_value(label):
        return int(label.split("~")[0])

    bucket_df = bucket_df.sort_values(by="bucket", key=lambda s: s.map(start_value)).reset_index(drop=True)
    bucket_df = bucket_df[bucket_df["bucket"] != "21~40"].reset_index(drop=True)

    max_r = bucket_df["ratio"].max()
    min_r = bucket_df["ratio"].min()

    def lerp_color(t):
        green = (76/255, 175/255, 80/255)   # #4CAF50
        yellow = (255/255, 235/255, 59/255) # #FFEB3B
        return (
            green[0] + (yellow[0] - green[0]) * t,
            green[1] + (yellow[1] - green[1]) * t,
            green[2] + (yellow[2] - green[2]) * t
        )

    colors = []
    for r in bucket_df["ratio"]:
        if max_r == min_r:
            t = 0.5
        else:
            t = (max_r - r) / (max_r - min_r)
        colors.append(lerp_color(t))

    fig, ax = plt.subplots(figsize=FIXED_FIGSIZE, dpi=SAVE_DPI)
    ax.set_position([0.08, 0.18, 0.88, 0.75])  # ✅ 아래 공간 확보 (겹침 방지)

    bars = ax.bar(bucket_df["bucket"], bucket_df["ratio"], color=colors)

    ax.set_title("당첨번호합계", fontproperties=font_prop if font_prop else None, fontsize=26, pad=6)
    ax.set_xlabel("합계 구간(20단위)", fontproperties=font_prop if font_prop else None, fontsize=18, labelpad=10)
    ax.set_ylabel("비율(%)", fontproperties=font_prop if font_prop else None, fontsize=18, labelpad=10)

    ax.grid(True, axis="y", alpha=0.25)

    # ✅ x축 라벨 짧게/작게/회전해서 겹침 방지
    ax.tick_params(axis="x", labelrotation=35, labelsize=12)
    ax.tick_params(axis="y", labelsize=14)

    for bar, ratio in zip(bars, bucket_df["ratio"]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{ratio:.1f}%",
            ha="center",
            va="bottom",
            fontsize=14,
            fontproperties=font_prop if font_prop else None
        )

    plt.savefig(os.path.join(out_folder, "sum_bucket.png"), dpi=SAVE_DPI, transparent=True)
    plt.close()


# ==================================================
# 6) 홀짝 파이
# ✅ 파이 안 % 글씨를 "중간"에 위치시키기
# ✅ 오른쪽 표기(홀:짝 1:6 12.3%) 가 안 잘리게 안쪽에 넣기
# ==================================================
def make_odd_even_pie(stats_json):
    out_folder = os.path.join(OUT_DIR, "oddEven")
    ensure_dir(out_folder)

    df_oe = pd.DataFrame(stats_json.get("odd_even_stats", []))
    if df_oe.empty:
        fig, ax = plt.subplots(figsize=FIXED_FIGSIZE, dpi=SAVE_DPI)
        ax.axis("off")
        ax.text(0.5, 0.5, "odd_even_stats 데이터 없음", ha="center", va="center",
                fontsize=20, fontproperties=font_prop if font_prop else None)
        plt.savefig(os.path.join(out_folder, "odd_even_pie.png"), dpi=SAVE_DPI, transparent=True)
        plt.close()
        return

    df_oe["odd"] = df_oe["odd"].astype(int)
    df_oe["even"] = df_oe["even"].astype(int)
    df_oe["count"] = df_oe["count"].astype(int)

    df_oe = df_oe.sort_values("count", ascending=False).reset_index(drop=True)

    labels_raw = [f"{o}:{e}" for o, e in zip(df_oe["odd"], df_oe["even"])]
    sizes = df_oe["count"].tolist()

    total = sum(sizes)
    percentages = [(v / total) * 100 for v in sizes]

    # ✅ 범례 라벨: "1:6 12.3%" 형태로
    legend_labels = [f"{lab}  {pct:.1f}%" for lab, pct in zip(labels_raw, percentages)]

    # ✅ 상위 4개만 % 표시
    def make_autopct():
        idx = {"i": -1}
        def _autopct(pct):
            idx["i"] += 1
            if idx["i"] < 4:
                return f"{pct:.1f}%"
            return ""
        return _autopct

    fig, ax = plt.subplots(figsize=FIXED_FIGSIZE, dpi=SAVE_DPI)

    # ✅ 오른쪽 공간 만들기 (범례 안 잘리게)
    ax.set_position([0.06, 0.12, 0.66, 0.78])

    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=None,
        autopct=make_autopct(),
        pctdistance=0.70,             # ✅ % 글씨 "중간" 위치
        startangle=90,
        wedgeprops={"width": 0.50, "edgecolor": "white"}  # 도넛 두껍게
    )

    ax.set_title("홀짝 비율", fontproperties=font_prop if font_prop else None, fontsize=26, pad=6)

    # ✅ % 글씨 크기 키우기
    for t in autotexts:
        t.set_fontsize(16)
        if font_prop:
            t.set_fontproperties(font_prop)

    # ✅ 범례를 그림 안쪽(오른쪽)으로 넣기 → 안 잘림
    legend = ax.legend(
        wedges,
        legend_labels,
        title="표기: 홀:짝",
        loc="center left",
        bbox_to_anchor=(1.00, 0.5),
        prop=font_prop if font_prop else None,
        title_fontproperties=font_prop if font_prop else None,
        frameon=False
    )

    plt.savefig(os.path.join(out_folder, "odd_even_pie.png"), dpi=SAVE_DPI, transparent=True)
    plt.close()


# ==================================================
# ✅ 실행
# ==================================================
def main():
    if not os.path.exists(STATS_PATH):
        raise FileNotFoundError(f"lotto_stats.json 없음: {STATS_PATH}")

    with open(STATS_PATH, "r", encoding="utf-8") as f:
        stats_json = json.load(f)

    history_json = {"history": []}
    if os.path.exists(HISTORY_PATH):
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            history_json = json.load(f)

    # 1) 번호 출현 랭킹
    make_numbercount_images(stats_json)

    # 2) 최근 10회차 표
    make_recent10_image(history_json)

    # 3) 동반출현
    make_pairstats_images(stats_json)

    # 4) 전이 TOP
    make_transition_best_images(stats_json)

    # 5) 합계 버킷 막대
    make_sum_bucket_bar(stats_json)

    # 6) 홀짝 파이
    make_odd_even_pie(stats_json)

    print("✅ 시각화 이미지 저장 완료!")
    print("📁 저장 위치:", OUT_DIR)


if __name__ == "__main__":
    main()
