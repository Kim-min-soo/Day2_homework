import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import io
from datetime import date
import random

# ─────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="🧠 도파민 추적기",
    page_icon="🧠",
    layout="wide",
)

# ─────────────────────────────────────────────
# 엑셀 파일 파싱 함수 (캐시 적용)
# ─────────────────────────────────────────────
@st.cache_data
def parse_ott(file) -> pd.DataFrame:
    df = pd.read_excel(file)
    required = {"날짜", "플랫폼", "콘텐츠명", "시청시간(분)"}
    if not required.issubset(df.columns):
        st.error(f"엑셀 A 필수 컬럼 누락: {required - set(df.columns)}")
        return pd.DataFrame()
    df["날짜"] = pd.to_datetime(df["날짜"])
    return df

@st.cache_data
def parse_yt(file) -> pd.DataFrame:
    df = pd.read_excel(file)
    required = {"날짜", "채널명", "영상종류", "시청시간(분)"}
    if not required.issubset(df.columns):
        st.error(f"엑셀 B 필수 컬럼 누락: {required - set(df.columns)}")
        return pd.DataFrame()
    df["날짜"] = pd.to_datetime(df["날짜"])
    return df


# ─────────────────────────────────────────────
# 사이드바 — 파일 업로드 + 세부 필터
# ─────────────────────────────────────────────
with st.sidebar:
    st.title("🔍 필터")

    # ① 파일 선택
    st.markdown("**📂 데이터 파일 선택**")
    st.caption("엑셀 파일을 업로드하면 대시보드가 활성화됩니다.")

    file_ott = st.file_uploader(
        "📺 엑셀 A — OTT 시청 기록",
        type=["xlsx", "xls"],
        key="upload_ott",
    )
    file_yt = st.file_uploader(
        "▶ 엑셀 B — 유튜브 시청 기록",
        type=["xlsx", "xls"],
        key="upload_yt",
    )

    st.markdown("---")

    # 파일 로드 (업로드된 파일만 사용)
    if file_ott is not None:
        df_ott = parse_ott(file_ott)
        ott_label = f"📺 엑셀 A ({file_ott.name})"
    else:
        df_ott = pd.DataFrame()
        ott_label = "📺 엑셀 A"

    if file_yt is not None:
        df_yt = parse_yt(file_yt)
        yt_label = f"▶ 엑셀 B ({file_yt.name})"
    else:
        df_yt = pd.DataFrame()
        yt_label = "▶ 엑셀 B"

    # ② OTT 플랫폼 필터
    OTT_PLATFORMS = sorted(df_ott["플랫폼"].unique().tolist()) if not df_ott.empty else []
    st.markdown("**🎬 OTT 플랫폼**")
    sel_platforms = st.multiselect(
        "플랫폼 선택",
        options=OTT_PLATFORMS,
        default=OTT_PLATFORMS,
        disabled=df_ott.empty,
        label_visibility="collapsed",
    )

    st.markdown("---")

    # ③ 유튜브 영상종류 필터
    YT_KINDS = ["숏폼", "롱폼"]
    st.markdown("**▶ 유튜브 영상 종류**")
    sel_yt_kinds = st.multiselect(
        "영상 종류 선택",
        options=YT_KINDS,
        default=YT_KINDS,
        disabled=df_yt.empty,
        label_visibility="collapsed",
    )

    st.markdown("---")
    if not df_ott.empty or not df_yt.empty:
        st.caption(f"현재 데이터: {ott_label}  |  {yt_label}")

# ─────────────────────────────────────────────
# 제목
# ─────────────────────────────────────────────
st.title("🧠 나만의 도파민 추적기 (OTT & 유튜브 중독도 분석)")
st.markdown("---")

# 파일 미업로드 시 안내 메시지만 표시하고 종료
if df_ott.empty and df_yt.empty:
    st.info("👈 왼쪽 사이드바에서 엑셀 파일을 업로드하면 대시보드가 표시됩니다.")
    st.stop()

# ─────────────────────────────────────────────
# 두 데이터프레임 병합 → 총 도파민 소비 데이터
# ─────────────────────────────────────────────
df_ott_merged = df_ott.rename(columns={"콘텐츠명": "콘텐츠/채널"}).copy() if not df_ott.empty else pd.DataFrame(columns=["날짜","플랫폼","콘텐츠/채널","시청시간(분)","소스","영상종류"])
if not df_ott.empty:
    df_ott_merged["소스"] = ott_label
    df_ott_merged["영상종류"] = None

df_yt_merged = df_yt.rename(columns={"채널명": "콘텐츠/채널"}).copy() if not df_yt.empty else pd.DataFrame(columns=["날짜","영상종류","콘텐츠/채널","시청시간(분)","소스","플랫폼"])
if not df_yt.empty:
    df_yt_merged["소스"] = yt_label
    df_yt_merged["플랫폼"] = "유튜브"

df_all = pd.concat([df_ott_merged, df_yt_merged], ignore_index=True)
df_all["날짜"] = pd.to_datetime(df_all["날짜"])
df_all = df_all.sort_values("날짜")

# 필터 적용
ott_mask = (df_all["소스"] == ott_label) & (df_all["플랫폼"].isin(sel_platforms))
yt_mask  = (df_all["소스"] == yt_label) & (df_all["영상종류"].isin(sel_yt_kinds))
df_filtered = df_all[ott_mask | yt_mask].copy()

# ─────────────────────────────────────────────
# 주요 지표 (st.metric)
# ─────────────────────────────────────────────
total_min = int(df_filtered["시청시간(분)"].sum())

if not df_filtered.empty:
    today_val = df_filtered[df_filtered["날짜"] == df_filtered["날짜"].max()]["시청시간(분)"].sum()
    yesterday_val = df_filtered[
        df_filtered["날짜"] == df_filtered["날짜"].max() - pd.Timedelta(days=1)
    ]["시청시간(분)"].sum()
    delta_pct = (
        round((today_val - yesterday_val) / yesterday_val * 100, 1)
        if yesterday_val > 0 else 0.0
    )
    daily_avg = round(total_min / df_filtered["날짜"].nunique(), 1)
else:
    delta_pct = 0.0
    daily_avg = 0

ott_min = int(df_filtered[df_filtered["소스"] == ott_label]["시청시간(분)"].sum())
yt_min  = int(df_filtered[df_filtered["소스"] == yt_label]["시청시간(분)"].sum())

col1, col2, col3, col4 = st.columns(4)
col1.metric("🧠 총 시청 시간(분)", f"{total_min:,}", f"{delta_pct:+.1f}% (전날 대비)")
col2.metric("⏱ 일평균 시청(분)", f"{daily_avg:,}")
col3.metric("📺 OTT 시청(분)", f"{ott_min:,}")
col4.metric("▶ 유튜브 시청(분)", f"{yt_min:,}")

st.markdown("---")

# ─────────────────────────────────────────────
# 시각화 1: 날짜별 총 시청 시간 선 그래프
# ─────────────────────────────────────────────
st.subheader("📈 날짜별 총 도파민 소비량 (분)")

daily = df_filtered.groupby(["날짜", "소스"])["시청시간(분)"].sum().reset_index()

fig_line = px.line(
    daily,
    x="날짜",
    y="시청시간(분)",
    color="소스",
    markers=True,
    color_discrete_map={
        ott_label: "#E50914",
        yt_label:  "#FF6B00",
    },
    labels={"시청시간(분)": "시청 시간(분)", "날짜": "날짜"},
    template="plotly_dark",
)
fig_line.update_layout(
    paper_bgcolor="#0e1117",
    plot_bgcolor="#0e1117",
    font_color="#fafafa",
    legend_title_text="소스",
)
st.plotly_chart(fig_line, use_container_width=True)

# ─────────────────────────────────────────────
# 시각화 2: OTT vs 유튜브 누적 바 차트
# ─────────────────────────────────────────────
st.subheader("📊 OTT vs 유튜브 시청 비중 (날짜별)")

pivot = (
    df_filtered.groupby(["날짜", "소스"])["시청시간(분)"]
    .sum()
    .unstack(fill_value=0)
    .reset_index()
)

fig_bar = go.Figure()
for src, color in [(ott_label, "#E50914"), (yt_label, "#FF6B00")]:
    if src in pivot.columns:
        fig_bar.add_trace(go.Bar(name=src, x=pivot["날짜"], y=pivot[src], marker_color=color))

fig_bar.update_layout(
    barmode="stack",
    template="plotly_dark",
    paper_bgcolor="#0e1117",
    plot_bgcolor="#0e1117",
    font_color="#fafafa",
    xaxis_title="날짜",
    yaxis_title="시청 시간(분)",
    legend_title_text="소스",
)
st.plotly_chart(fig_bar, use_container_width=True)

# ─────────────────────────────────────────────
# 시각화 3: OTT 플랫폼별 / 유튜브 영상종류별 파이 차트
# ─────────────────────────────────────────────
st.subheader("🥧 세부 카테고리별 시청 비중")

pie_col1, pie_col2 = st.columns(2)

with pie_col1:
    ott_pie = (
        df_filtered[df_filtered["소스"] == ott_label]
        .groupby("플랫폼")["시청시간(분)"]
        .sum()
        .reset_index()
    )
    if not ott_pie.empty:
        fig_pie_ott = px.pie(
            ott_pie,
            names="플랫폼",
            values="시청시간(분)",
            title="📺 OTT 플랫폼별 비중",
            hole=0.4,
            template="plotly_dark",
            color_discrete_map={
                "넷플릭스":   "#E50914",
                "TVING":      "#FF153C",
                "쿠팡플레이": "#1A4FBA",
            },
        )
        fig_pie_ott.update_layout(paper_bgcolor="#0e1117", font_color="#fafafa")
        st.plotly_chart(fig_pie_ott, use_container_width=True)
    else:
        st.info("OTT 데이터가 없습니다.")

with pie_col2:
    yt_pie = (
        df_filtered[df_filtered["소스"] == yt_label]
        .groupby("영상종류")["시청시간(분)"]
        .sum()
        .reset_index()
    )
    if not yt_pie.empty:
        fig_pie_yt = px.pie(
            yt_pie,
            names="영상종류",
            values="시청시간(분)",
            title="▶ 유튜브 영상 종류별 비중",
            hole=0.4,
            template="plotly_dark",
            color_discrete_map={
                "숏폼": "#FF6B00",
                "롱폼": "#FFA500",
            },
        )
        fig_pie_yt.update_layout(paper_bgcolor="#0e1117", font_color="#fafafa")
        st.plotly_chart(fig_pie_yt, use_container_width=True)
    else:
        st.info("유튜브 데이터가 없습니다.")

st.markdown("---")

# ─────────────────────────────────────────────
# 외부 API 연동: Advice Slip API (랜덤 조언)
# ─────────────────────────────────────────────
with st.container():
    st.subheader("💊 스마트폰 내려놓기 원동력 주입!")
    st.caption("버튼을 누르면 도파민 중독 탈출을 위한 랜덤 조언이 도착합니다.")

    if st.button("🔔 원동력 주입하기!"):
        try:
            resp = requests.get("https://api.adviceslip.com/advice", timeout=5)
            resp.raise_for_status()
            advice_en = resp.json()["slip"]["advice"]
            tips = [
                "지금 이 순간, 화면 대신 창밖을 바라보세요. 🌿",
                "5분만 스트레칭해보세요. 몸이 감사해할 거예요. 🙆",
                "물 한 잔 마시고 심호흡 세 번! 🌬",
                "오늘 통화하지 못한 소중한 사람에게 연락해보세요. 📞",
                "짧은 산책이 유튜브 30분보다 도파민을 더 오래 줍니다. 🚶",
            ]
            st.success(f"**[EN] {advice_en}**")
            st.info(f"💡 {random.choice(tips)}")
        except Exception as e:
            st.error(f"API 호출에 실패했습니다: {e}")
            st.info("💡 스마트폰을 내려놓고, 지금 당장 밖으로 나가세요! 🌤")

st.markdown("---")

# ─────────────────────────────────────────────
# 병합 방식 안내 + 다운로드
# ─────────────────────────────────────────────
st.subheader("📋 전체 도파민 소비 로그")

# 다운로드 버튼
display_cols = ["날짜", "소스", "플랫폼", "영상종류", "콘텐츠/채널", "시청시간(분)"]
df_download = df_filtered[display_cols].sort_values("날짜", ascending=False).reset_index(drop=True)

dl_col1, dl_col2 = st.columns([1, 1])

with dl_col1:
    csv_data = df_download.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        label="⬇ CSV로 다운로드",
        data=csv_data,
        file_name="도파민_소비_병합데이터.csv",
        mime="text/csv",
        use_container_width=True,
    )

with dl_col2:
    xlsx_buf = io.BytesIO()
    with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as writer:
        df_download.to_excel(writer, index=False, sheet_name="도파민소비로그")
    xlsx_buf.seek(0)
    st.download_button(
        label="⬇ Excel로 다운로드",
        data=xlsx_buf,
        file_name="도파민_소비_병합데이터.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

st.dataframe(df_download, use_container_width=True, height=400)
