"""
=============================================================
09_website.py - Sarcopenia Drug Discovery Knowledge Platform
=============================================================
용도: 3,894건 논문/특허 분석 결과를 웹 플랫폼으로 제공
      타겟 발굴, 화합물 탐색, Target-Compound 매트릭스,
      AI 기반 질의응답, 보고서 자동 생성 기능

실행:
  1. pip install streamlit plotly anthropic openpyxl
  2. streamlit run 09_website.py
=============================================================
"""

import streamlit as st
import pandas as pd
import os
import sys
import re
import io
import json
from collections import Counter, defaultdict
from datetime import datetime

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ─── 설정 ────────────────────────────────────────────────
EXCEL_NAMES = ["Sarcopenia_data.xlsx", "Sarcopenia_문헌분류_결과.xlsx"]

_script_dir = os.path.dirname(os.path.abspath(__file__))
_search_dirs = [
    os.path.dirname(_script_dir),
    _script_dir,
    os.getcwd(),
    "/mount/src/dcp_sarcopenia",
    "/app",
]
_search_dirs = list(dict.fromkeys(_search_dirs))

EXCEL_PATH = None
BASE_FOLDER = _search_dirs[0]
for d in _search_dirs:
    if not os.path.isdir(d):
        continue
    for name in EXCEL_NAMES:
        candidate = os.path.join(d, name)
        if os.path.exists(candidate):
            EXCEL_PATH = candidate
            BASE_FOLDER = d
            break
    if EXCEL_PATH:
        break

if EXCEL_PATH is None:
    import streamlit as _st_debug
    _st_debug.error("데이터 파일을 찾을 수 없습니다. 02_info_extract.py를 먼저 실행하세요.")
    _st_debug.code(f"검색 디렉토리:\n" + "\n".join(
        f"  {d} -> {'EXISTS' if os.path.isdir(d) else 'NOT FOUND'}"
        for d in _search_dirs
    ))
    EXCEL_PATH = os.path.join(_search_dirs[0], EXCEL_NAMES[0])

TXT_FOLDER = os.path.join(BASE_FOLDER, "txt_추출결과")

def load_api_key():
    try:
        return st.secrets["CLAUDE_API_KEY"]
    except Exception:
        pass
    return os.environ.get("ANTHROPIC_API_KEY", "")

CLAUDE_API_KEY = load_api_key()

# ============================================================
# 페이지 설정
# ============================================================
st.set_page_config(
    page_title="Sarcopenia Drug Discovery Platform",
    page_icon="S",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 타겟 이름 정규화
# ============================================================
TARGET_NORMALIZE = {
    "Myostatin": "Myostatin/GDF-8",
    "GDF-8": "Myostatin/GDF-8",
    "GDF8": "Myostatin/GDF-8",
    "myostatin": "Myostatin/GDF-8",
    "Activin receptor type IIB": "ActRIIB",
    "ActRII": "ActRIIB",
    "ACVR2B": "ActRIIB",
    "mTOR": "mTOR/PI3K/Akt",
    "PI3K/Akt": "mTOR/PI3K/Akt",
    "Akt/mTOR": "mTOR/PI3K/Akt",
    "IGF-1": "IGF-1/IGF-1R",
    "IGF1": "IGF-1/IGF-1R",
    "IGF-1R": "IGF-1/IGF-1R",
    "MuRF1": "MuRF1/MAFbx",
    "MAFbx": "MuRF1/MAFbx",
    "Atrogin-1": "MuRF1/MAFbx",
    "FOXO3": "FoxO3",
    "FoxO3a": "FoxO3",
    "AMPK": "AMPK/PGC-1α",
    "PGC-1α": "AMPK/PGC-1α",
    "RIPK3": "RIPK1/RIPK3",
    "RIPK1": "RIPK1/RIPK3",
    "NF-κB": "NF-κB",
    "NF-kB": "NF-κB",
    "androgen receptor": "Androgen Receptor",
    "AR": "Androgen Receptor",
}

def normalize_target(name):
    name = name.strip()
    return TARGET_NORMALIZE.get(name, name)

# ============================================================
# 데이터 로딩
# ============================================================
@st.cache_data
def load_data():
    if not os.path.exists(EXCEL_PATH):
        return None
    df = pd.read_excel(EXCEL_PATH)
    df["관련도"] = pd.to_numeric(df.get("관련도(1-5)", 0), errors="coerce").fillna(0).astype(int)
    return df

@st.cache_data
def build_target_index(df):
    target_map = {}
    for idx, row in df.iterrows():
        targets = str(row.get("타겟(Target)", ""))
        if targets == "nan":
            continue
        for t in targets.split(","):
            t = normalize_target(t)
            if len(t) > 1:
                target_map.setdefault(t, []).append(idx)
    return target_map

@st.cache_data
def build_compound_index(df):
    compound_map = {}
    for idx, row in df.iterrows():
        compounds = str(row.get("화합물(Compound)", ""))
        if compounds == "nan":
            continue
        for c in compounds.split(","):
            c = c.strip()
            if len(c) > 1:
                compound_map.setdefault(c, []).append(idx)
    return compound_map

def get_top_items(df, column, top_n=20, normalize_fn=None):
    counter = Counter()
    for val in df[column].dropna():
        for item in str(val).split(","):
            item = item.strip()
            if normalize_fn:
                item = normalize_fn(item)
            if len(item) > 1:
                counter[item] += 1
    return counter.most_common(top_n)

@st.cache_data
def load_structures():
    for d in _search_dirs:
        candidate = os.path.join(d, "compound_structures.json")
        if os.path.exists(candidate):
            with open(candidate, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {item["name"]: item for item in data if item.get("status") == "found"}
    return {}

@st.cache_data
def load_natural_products():
    for d in _search_dirs:
        candidate = os.path.join(d, "natural_product_actives.json")
        if os.path.exists(candidate):
            with open(candidate, "r", encoding="utf-8") as f:
                return json.load(f)
    return {}

# ============================================================
# 데이터 로딩 실행
# ============================================================
df = load_data()

if df is None:
    st.error("데이터가 없습니다. 02_info_extract.py를 먼저 실행하세요.")
    st.stop()

target_index = build_target_index(df)
compound_index = build_compound_index(df)
structures = load_structures()
np_data = load_natural_products()

df_ok = df[df["처리상태"].isin(["성공", "OK"])].copy() if "처리상태" in df.columns else df.copy()

# ============================================================
# 헤더
# ============================================================
st.markdown("""
<div style='background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
     padding: 20px 30px; border-radius: 12px; margin-bottom: 20px;'>
    <h1 style='color: #e94560; margin:0; font-size: 28px;'>Sarcopenia Drug Discovery Platform</h1>
    <p style='color: #a8a8a8; margin: 5px 0 0 0; font-size: 14px;'>
        근감소증 신약개발 문헌 데이터베이스 &nbsp;|&nbsp;
        {total}건 논문 분석 완료 &nbsp;|&nbsp; Novel Target & Biomarker Discovery
    </p>
</div>
""".format(total=len(df_ok)), unsafe_allow_html=True)

# ============================================================
# 사이드바: 글로벌 필터
# ============================================================
with st.sidebar:
    st.markdown("### Filter")

    study_types = sorted(df_ok["연구유형"].dropna().unique().tolist()) if "연구유형" in df_ok.columns else []
    selected_studies = st.multiselect("연구 유형", study_types, default=study_types)

    doc_types = sorted(df_ok["문서유형"].dropna().unique().tolist()) if "문서유형" in df_ok.columns else []
    selected_docs = st.multiselect("문서 유형", doc_types, default=doc_types)

    min_rel = st.slider("최소 관련도", 1, 5, 1)
    keyword_filter = st.text_input("키워드 필터", placeholder="예: Myostatin, mTOR, ferroptosis...")

    st.markdown("---")

    filtered = df_ok.copy()
    if "연구유형" in filtered.columns:
        filtered = filtered[filtered["연구유형"].isin(selected_studies)]
    if "문서유형" in filtered.columns:
        filtered = filtered[filtered["문서유형"].isin(selected_docs)]
    filtered = filtered[filtered["관련도"] >= min_rel]

    if keyword_filter:
        mask = filtered.apply(lambda row: keyword_filter.lower() in str(row.values).lower(), axis=1)
        filtered = filtered[mask]

    st.metric("검색 결과", f"{len(filtered)} / {len(df_ok)}건")
    st.caption(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d')}")

    # 치료분류 필터 (근감소증 특화)
    if "치료분류" in df_ok.columns:
        cat_types = sorted(df_ok["치료분류"].dropna().unique().tolist())
        if cat_types:
            selected_cats = st.multiselect("치료 분류", cat_types, default=cat_types)
            filtered = filtered[filtered["치료분류"].isin(selected_cats)]

    # 질환아형 필터
    if "질환아형" in df_ok.columns:
        sub_types = sorted(df_ok["질환아형"].dropna().unique().tolist())
        if sub_types:
            selected_subs = st.multiselect("질환 아형", sub_types, default=sub_types)
            filtered = filtered[filtered["질환아형"].isin(selected_subs)]

# ============================================================
# 탭 구성
# ============================================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11 = st.tabs([
    "Dashboard",
    "Literature Search",
    "Target Analysis",
    "Compound Analysis",
    "Target-Compound Matrix",
    "AI Q&A",
    "Dark Targets",
    "AI Drug Candidates",
    "Biomarkers",
    "Research Trends",
    "Control Center",
])

# ============================================================
# 탭 1: 대시보드
# ============================================================
with tab1:
    import plotly.express as px
    import plotly.graph_objects as go

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("총 문헌", f"{len(df_ok)}")
    paper_count = len(df_ok[df_ok['문서유형']=='Paper']) if '문서유형' in df_ok.columns else 0
    patent_count = len(df_ok[df_ok['문서유형']=='Patent']) if '문서유형' in df_ok.columns else 0
    c2.metric("논문", f"{paper_count}")
    c3.metric("특허", f"{patent_count}")
    c4.metric("고유 타겟", f"{len(target_index)}")
    c5.metric("고유 화합물", f"{len(compound_index)}")

    st.markdown("---")
    col_l, col_r = st.columns(2)

    with col_l:
        if "연구유형" in df_ok.columns:
            study_dist = df_ok["연구유형"].value_counts().reset_index()
            study_dist.columns = ["연구유형", "건수"]
            fig1 = px.pie(study_dist, values="건수", names="연구유형",
                          title="연구 유형 분포", hole=0.4,
                          color_discrete_sequence=px.colors.qualitative.Set2)
            fig1.update_layout(height=350, margin=dict(t=40, b=20, l=20, r=20))
            st.plotly_chart(fig1, use_container_width=True)

    with col_r:
        rel_dist = df_ok["관련도"].value_counts().sort_index().reset_index()
        rel_dist.columns = ["관련도 점수", "건수"]
        fig2 = px.bar(rel_dist, x="관련도 점수", y="건수",
                      title="관련도 점수 분포",
                      color="건수", color_continuous_scale="Reds")
        fig2.update_layout(height=350, margin=dict(t=40, b=20, l=20, r=20))
        st.plotly_chart(fig2, use_container_width=True)

    # 치료분류 분포 (근감소증 특화)
    if "치료분류" in df_ok.columns:
        cat_dist = df_ok["치료분류"].value_counts().reset_index()
        cat_dist.columns = ["치료분류", "건수"]
        fig_cat = px.bar(cat_dist, x="건수", y="치료분류", orientation="h",
                         title="치료 분류별 분포",
                         color="건수", color_continuous_scale="Teal")
        fig_cat.update_layout(height=350, yaxis=dict(autorange="reversed"),
                              margin=dict(t=40, b=20, l=20, r=20))
        st.plotly_chart(fig_cat, use_container_width=True)

    # Top 타겟
    top_targets = get_top_items(df_ok, "타겟(Target)", 15, normalize_target)
    if top_targets:
        tgt_df = pd.DataFrame(top_targets, columns=["타겟", "논문수"])
        fig3 = px.bar(tgt_df, x="논문수", y="타겟", orientation="h",
                      title="Top 15 Drug Targets",
                      color="논문수", color_continuous_scale="Blues")
        fig3.update_layout(height=450, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig3, use_container_width=True)

    # Top 화합물
    top_compounds = get_top_items(df_ok, "화합물(Compound)", 15)
    if top_compounds:
        comp_df = pd.DataFrame(top_compounds, columns=["화합물", "논문수"])
        fig4 = px.bar(comp_df, x="논문수", y="화합물", orientation="h",
                      title="Top 15 Compounds",
                      color="논문수", color_continuous_scale="Greens")
        fig4.update_layout(height=450, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig4, use_container_width=True)

# ============================================================
# 탭 2: 문헌 검색
# ============================================================
with tab2:
    st.markdown("### Literature Search")
    search_q = st.text_input("검색어 입력", placeholder="타겟, 화합물, 기전, 키워드 등...")
    display = filtered.copy()
    if search_q:
        mask = display.apply(lambda r: search_q.lower() in str(r.values).lower(), axis=1)
        display = display[mask]
    st.write(f"**{len(display)}건** 검색됨")

    show_cols = [c for c in ["파일명", "문서유형", "연구유형", "타겟(Target)", "화합물(Compound)",
                 "기전(MoA)", "핵심발견", "치료분류", "질환아형", "관련도"] if c in display.columns]

    st.dataframe(display[show_cols], use_container_width=True, height=500,
                 column_config={"관련도": st.column_config.ProgressColumn("관련도", min_value=0, max_value=5, format="%d")})

    st.markdown("---")
    st.markdown("#### Paper Detail")
    if len(display) > 0:
        paper_names = display["파일명"].tolist()
        selected_paper = st.selectbox("논문 선택", paper_names)
        if selected_paper:
            row = display[display["파일명"] == selected_paper].iloc[0]
            col_a, col_b = st.columns(2)
            with col_a:
                for field in ["문서유형", "연구유형", "타겟(Target)", "화합물(Compound)", "치료분류", "질환아형"]:
                    if field in row.index:
                        st.markdown(f"**{field}:** {row.get(field, '')}")
                st.markdown(f"**관련도:** {int(row.get('관련도', 0))}/5")
            with col_b:
                for field in ["기전(MoA)", "신호전달경로", "세포/모델", "바이오마커"]:
                    if field in row.index:
                        st.markdown(f"**{field}:** {row.get(field, '')}")
            st.markdown("**핵심 발견:**")
            st.info(row.get("핵심발견", ""))

            txt_file = os.path.join(TXT_FOLDER, selected_paper)
            if os.path.exists(txt_file):
                with st.expander("View Original Text"):
                    with open(txt_file, "r", encoding="utf-8") as f:
                        st.text(f.read()[:5000] + "\n... (이하 생략)")

    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        csv_data = display[show_cols].to_csv(index=False, encoding="utf-8-sig")
        st.download_button("CSV Download", csv_data.encode("utf-8-sig"), "Sarcopenia_검색결과.csv", "text/csv")
    with col_dl2:
        buf = io.BytesIO()
        display[show_cols].to_excel(buf, index=False, engine="openpyxl")
        st.download_button("Excel Download", buf.getvalue(), "Sarcopenia_검색결과.xlsx",
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ============================================================
# 탭 3: 타겟 분석
# ============================================================
with tab3:
    import plotly.express as px
    st.markdown("### Target Analysis")
    target_counts = {t: len(idxs) for t, idxs in target_index.items() if len(t) > 1}
    sorted_targets = sorted(target_counts.keys(), key=lambda x: target_counts[x], reverse=True)
    top100 = sorted_targets[:100]
    selected_target = st.selectbox("타겟 선택 (논문수 순)", top100,
                                    format_func=lambda x: f"{x} ({target_counts.get(x,0)}건)")
    if selected_target:
        idxs = target_index.get(selected_target, [])
        t_papers = df_ok.loc[df_ok.index.isin(idxs)]
        c1, c2, c3 = st.columns(3)
        c1.metric("관련 논문 수", f"{len(t_papers)}건")
        avg_rel = t_papers["관련도"].mean()
        c2.metric("평균 관련도", f"{avg_rel:.1f}")
        c3.metric("고관련도(4+)", f"{len(t_papers[t_papers['관련도']>=4])}건")
        st.markdown("---")
        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("#### 연관 화합물")
            t_comp = get_top_items(t_papers, "화합물(Compound)", 10)
            if t_comp:
                t_comp_df = pd.DataFrame(t_comp, columns=["화합물", "건수"])
                fig = px.bar(t_comp_df, x="건수", y="화합물", orientation="h",
                            color="건수", color_continuous_scale="Oranges")
                fig.update_layout(height=300, yaxis=dict(autorange="reversed"), margin=dict(t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)
        with col_r:
            st.markdown("#### 관련 신호전달 경로")
            t_path = get_top_items(t_papers, "신호전달경로", 10) if "신호전달경로" in t_papers.columns else []
            if t_path:
                for pw, cnt in t_path:
                    st.write(f"- **{pw}** ({cnt}건)")
            st.markdown("#### 연구유형 분포")
            if "연구유형" in t_papers.columns:
                for stype, cnt in t_papers["연구유형"].value_counts().items():
                    st.write(f"- {stype}: {cnt}건")

        st.markdown("#### 핵심 발견 (고관련도 순)")
        high_rel = t_papers.sort_values("관련도", ascending=False)
        for _, row in high_rel.head(8).iterrows():
            finding = row.get("핵심발견", "")
            if finding and str(finding) != "nan":
                rel = int(row.get("관련도", 0))
                st.markdown(f"[{rel}/5] **{row['파일명'][:60]}...**")
                st.caption(finding)

        # 프로파일 다운로드
        profile_text = f"""# {selected_target} - Target Profile Report\n생성일: {datetime.now().strftime('%Y-%m-%d')}\n\n## 기본 정보\n- 관련 논문: {len(t_papers)}건\n- 평균 관련도: {avg_rel:.1f}/5.0\n"""
        st.download_button("Target Profile (.md)", profile_text, f"{selected_target}_profile.md", "text/markdown")

# ============================================================
# 탭 4: 화합물 분석
# ============================================================
with tab4:
    import plotly.express as px
    st.markdown("### Compound Analysis")
    comp_counts = {c: len(idxs) for c, idxs in compound_index.items() if len(c) > 1}
    sorted_compounds = sorted(comp_counts.keys(), key=lambda x: comp_counts[x], reverse=True)
    top100c = sorted_compounds[:100]
    selected_compound = st.selectbox("화합물 선택 (논문수 순)", top100c,
                                      format_func=lambda x: f"{x} ({comp_counts.get(x,0)}건)")
    if selected_compound:
        c_idxs = compound_index.get(selected_compound, [])
        c_papers = df_ok.loc[df_ok.index.isin(c_idxs)]

        struct = structures.get(selected_compound, {})
        if struct:
            st.markdown("#### Compound Structure")
            img_col, info_col = st.columns([1, 2])
            with img_col:
                img_url = struct.get("image_url", "")
                if img_url:
                    st.image(img_url, caption=f"{selected_compound} 2D Structure", width=250)
            with info_col:
                st.markdown(f"**분자식:** {struct.get('MolecularFormula', '-')}")
                st.markdown(f"**분자량:** {struct.get('MolecularWeight', '-')} g/mol")
                st.markdown(f"**SMILES:** `{struct.get('SMILES', '-')}`")
                st.markdown(f"**PubChem CID:** [{struct.get('CID', '')}]({struct.get('pubchem_url', '')})")

        # 천연물 활성성분
        np_mapping = np_data.get("natural_product_mapping", {})
        np_actives_db = np_data.get("active_compounds", {})
        active_list = np_mapping.get(selected_compound, [])
        if not active_list:
            for np_name, actives in np_mapping.items():
                if np_name in selected_compound or selected_compound in np_name:
                    active_list = actives
                    break
        if active_list and not struct:
            st.markdown("#### Natural Product Active Ingredients")
            for act_name in active_list:
                act_info = np_actives_db.get(act_name, {})
                if act_info.get("status") == "found":
                    st.markdown(f"**{act_name}** — {act_info.get('MolecularFormula', '')} · MW: {act_info.get('MolecularWeight', '')} g/mol")

        c1, c2, c3 = st.columns(3)
        c1.metric("관련 논문 수", f"{len(c_papers)}건")
        c2.metric("평균 관련도", f"{c_papers['관련도'].mean():.1f}")
        clinical = len(c_papers[c_papers["연구유형"] == "Clinical"]) if "연구유형" in c_papers.columns else 0
        c3.metric("임상 연구", f"{clinical}건")

        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("#### 타겟")
            c_tgt = get_top_items(c_papers, "타겟(Target)", 10, normalize_target)
            if c_tgt:
                c_tgt_df = pd.DataFrame(c_tgt, columns=["타겟", "건수"])
                fig = px.bar(c_tgt_df, x="건수", y="타겟", orientation="h",
                            color="건수", color_continuous_scale="Purples")
                fig.update_layout(height=300, yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig, use_container_width=True)
        with col_r:
            st.markdown("#### 기전 (MoA) 요약")
            if "기전(MoA)" in c_papers.columns:
                for _, row in c_papers.head(5).iterrows():
                    moa = row.get("기전(MoA)", "")
                    if moa and str(moa) != "nan":
                        st.caption(f"• {moa}")

# ============================================================
# 탭 5: Target-Compound 매트릭스
# ============================================================
with tab5:
    import plotly.graph_objects as go
    st.markdown("### Target-Compound Relationship Matrix")
    n_targets = st.slider("상위 타겟 수", 5, 20, 10)
    n_compounds = st.slider("상위 화합물 수", 5, 20, 10)

    top_t = [t for t, _ in get_top_items(df_ok, "타겟(Target)", n_targets, normalize_target)]
    top_c = [c for c, _ in get_top_items(df_ok, "화합물(Compound)", n_compounds)]

    matrix = pd.DataFrame(0, index=top_t, columns=top_c)
    for _, row in df_ok.iterrows():
        targets = str(row.get("타겟(Target)", ""))
        compounds = str(row.get("화합물(Compound)", ""))
        if targets == "nan" or compounds == "nan":
            continue
        row_targets = [normalize_target(t) for t in targets.split(",") if t.strip()]
        row_compounds = [c.strip() for c in compounds.split(",") if c.strip()]
        for t in row_targets:
            for c in row_compounds:
                if t in matrix.index and c in matrix.columns:
                    matrix.loc[t, c] += 1

    fig = go.Figure(data=go.Heatmap(
        z=matrix.values, x=matrix.columns.tolist(), y=matrix.index.tolist(),
        colorscale="YlOrRd", text=matrix.values, texttemplate="%{text}",
        textfont={"size": 11},
        hovertemplate="타겟: %{y}<br>화합물: %{x}<br>공출현: %{z}건<extra></extra>"
    ))
    fig.update_layout(title="Target-Compound Co-occurrence Matrix", height=500,
                      yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig, use_container_width=True)

    buf = io.BytesIO()
    matrix.to_excel(buf, engine="openpyxl")
    st.download_button("Matrix Excel", buf.getvalue(), "Target_Compound_Matrix.xlsx")

    # Novel Target 후보
    st.markdown("---")
    st.markdown("#### Novel Target Candidates (Low frequency + High relevance)")
    novel_candidates = []
    for t, idxs in target_index.items():
        if len(t) <= 2:
            continue
        papers = df_ok.loc[df_ok.index.isin(idxs)]
        if 1 <= len(papers) < 5:
            avg_r = papers["관련도"].mean()
            if avg_r >= 4.0:
                novel_candidates.append({
                    "타겟": t, "논문수": len(papers), "평균관련도": round(avg_r, 1),
                    "연관화합물": ", ".join([c for c, _ in get_top_items(papers, "화합물(Compound)", 3)])
                })
    if novel_candidates:
        novel_df = pd.DataFrame(novel_candidates).sort_values("평균관련도", ascending=False)
        st.dataframe(novel_df.head(100), use_container_width=True)

# ============================================================
# 탭 6: AI 질의응답 (RAG)
# ============================================================
with tab6:
    st.markdown("### AI Q&A")
    st.caption("근감소증 논문 데이터베이스 기반 AI 답변")

    example_qs = [
        "Myostatin 억제제가 근력 개선에 실패한 이유는?",
        "Gut-muscle axis를 타겟으로 하는 치료 전략은?",
        "Ferroptosis가 근감소증에서 어떤 역할을 하나?",
        "근감소증 신약개발에서 가장 유망한 타겟은?",
        "약물 유발 근감소증의 원인 약물과 기전은?",
    ]
    st.markdown("**예시 질문:**")
    for q in example_qs:
        st.caption(f"  • {q}")

    if "messages" not in st.session_state:
        st.session_state.messages = []
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    question = st.chat_input("질문을 입력하세요...")
    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        keywords = [kw for kw in question.lower().split() if len(kw) > 1]
        relevant = df_ok[df_ok.apply(
            lambda row: sum(1 for kw in keywords if kw in str(row.values).lower()) >= 1, axis=1
        )].sort_values("관련도", ascending=False).head(15)

        context_parts = []
        for _, row in relevant.iterrows():
            parts = []
            for col in ["파일명", "타겟(Target)", "화합물(Compound)", "기전(MoA)", "핵심발견", "신호전달경로", "바이오마커"]:
                val = row.get(col, "")
                if val and str(val) != "nan":
                    parts.append(f"{col}: {val}")
            context_parts.append("\n".join(parts))
        context = "\n---\n".join(context_parts)

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
            prompt = f"""You are an expert in Sarcopenia drug development and muscle biology.
Below is information from a database of {len(df_ok)} sarcopenia-related papers and patents.
Answer the question based on this data. Answer in Korean. Cite source paper filenames.

[Retrieved Data]
{context}

[Question]
{question}"""
            response = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=2000,
                                              messages=[{"role": "user", "content": prompt}])
            answer = response.content[0].text
        except Exception as e:
            answer = f"오류: {str(e)[:200]}\n\n키워드 검색 결과 {len(relevant)}건 관련 논문 발견."

        st.session_state.messages.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.markdown(answer)

# ============================================================
# 탭 7: Dark Targets
# ============================================================
with tab7:
    st.markdown("### Dark Targets")

    _intel_report = None
    for d in _search_dirs + [os.path.join(d, 'output') for d in _search_dirs]:
        ir_path = os.path.join(d, 'intelligence_report.json')
        if os.path.exists(ir_path):
            try:
                with open(ir_path, 'r', encoding='utf-8') as f:
                    _intel_report = json.load(f)
                break
            except Exception:
                pass

    if _intel_report:
        ts = _intel_report.get('timestamp', '')
        st.success(f"마지막 분석: {ts[:19]}")

        dark_targets = _intel_report.get('top_dark_targets', [])
        if dark_targets:
            st.markdown("#### Dark Target Ranking (Novelty Index)")
            dt_rows = [{"순위": i, "타겟": dt.get('target', ''),
                       "Novelty Index": round(dt.get('novelty_index', 0), 4),
                       "논문 수": dt.get('paper_count', 0),
                       "관련도": round(dt.get('avg_relevance', 0), 1)}
                      for i, dt in enumerate(dark_targets[:100], 1)]
            st.dataframe(pd.DataFrame(dt_rows), use_container_width=True, hide_index=True)

            for dt in dark_targets[:20]:
                with st.expander(f"{dt.get('target', '')} (NI={dt.get('novelty_index', 0):.4f})"):
                    st.markdown(f"**논문 수:** {dt.get('paper_count', 0)}건 | **관련도:** {dt.get('avg_relevance', 0):.1f}/5")
                    if dt.get('pathways'):
                        st.markdown(f"**경로:** {', '.join(dt['pathways'][:10])}")
                    if dt.get('compounds'):
                        st.markdown(f"**화합물:** {', '.join(dt['compounds'][:10])}")

        gaps = _intel_report.get('top_gaps', [])
        if gaps:
            st.markdown("#### Gap Analysis")
            gap_rows = [{"타겟": g.get('target', ''), "화합물": g.get('compound', ''),
                        "Gap Score": round(g.get('gap_score', 0), 3)} for g in gaps[:100]]
            st.dataframe(pd.DataFrame(gap_rows), use_container_width=True, hide_index=True)

        synergies = _intel_report.get('top_synergies', [])
        if synergies:
            st.markdown("#### Multi-target Synergy")
            syn_rows = [{"타겟 1": s.get('target1', ''), "타겟 2": s.get('target2', ''),
                        "시너지 점수": round(s.get('synergy_score', 0), 3)} for s in synergies[:100]]
            st.dataframe(pd.DataFrame(syn_rows), use_container_width=True, hide_index=True)
    else:
        st.info("Pattern analysis not yet run. Execute: python scripts/10_pattern_analysis.py")

# ============================================================
# 탭 8: AI 신약 후보
# ============================================================
with tab8:
    st.markdown("### AI Drug Candidates")

    _candidates_data = None
    for d in _search_dirs + [os.path.join(d, 'output') for d in _search_dirs]:
        cm_path = os.path.join(d, 'candidate_molecules.json')
        if os.path.exists(cm_path):
            try:
                with open(cm_path, 'r', encoding='utf-8') as f:
                    _candidates_data = json.load(f)
                break
            except Exception:
                pass

    if _candidates_data:
        total = _candidates_data.get('total_candidates', 0)
        st.success(f"총 {total}개 후보물질")
        candidates = _candidates_data.get('candidates', [])
        if candidates:
            by_target = defaultdict(list)
            for c in candidates:
                by_target[c.get('target', 'Unknown')].append(c)
            for target, cands in by_target.items():
                st.markdown(f"#### {target}")
                for i, c in enumerate(cands, 1):
                    valid = c.get('validation_status', '') == 'Valid'
                    label = '[Valid]' if valid else '[Check]'
                    with st.expander(f"{label} Candidate #{i}: {c.get('smiles', 'N/A')[:50]}"):
                        st.code(c.get('smiles', ''), language=None)
                        st.markdown(f"**근거:** {c.get('rationale', 'N/A')}")
                        st.markdown(f"**Novelty Score:** {c.get('novelty_score', 'N/A')}")
                        if c.get('mechanism'):
                            st.markdown(f"**기전:** {c.get('mechanism')}")
    else:
        st.info("Drug candidates not yet generated. Execute: python scripts/11_drug_candidates.py")

# ============================================================
# 탭 9: 바이오마커
# ============================================================
with tab9:
    st.markdown("### Biomarker Analysis")

    _biomarker_data = None
    for d in _search_dirs + [os.path.join(d, 'output') for d in _search_dirs]:
        bm_path = os.path.join(d, 'biomarker_analysis.json')
        if os.path.exists(bm_path):
            try:
                with open(bm_path, 'r', encoding='utf-8') as f:
                    _biomarker_data = json.load(f)
                break
            except Exception:
                pass

    if _biomarker_data:
        total_bm = _biomarker_data.get('total_biomarkers', 0)
        st.success(f"총 {total_bm}종 바이오마커")

        top_bm = _biomarker_data.get('top_biomarkers', [])
        if top_bm:
            import plotly.express as px
            bm_df = pd.DataFrame(top_bm[:100])
            if not bm_df.empty and 'name' in bm_df.columns:
                fig = px.bar(bm_df, x='name', y='count', title='바이오마커 빈도 Top 100',
                           color='count', color_continuous_scale='Viridis')
                fig.update_layout(xaxis_tickangle=-45, height=400)
                st.plotly_chart(fig, use_container_width=True)

        # 카테고리별
        categories = _biomarker_data.get('categories', {})
        if categories:
            st.markdown("#### Biomarkers by Category")
            for cat, items in categories.items():
                with st.expander(f"**{cat}** ({len(items)}종)"):
                    for item in items[:100]:
                        st.markdown(f"- **{item['name']}** ({item['count']}건)")

        # 진단/예후/치료반응
        st.markdown("#### Biomarker Usage Classification")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**진단 마커**")
            for m in _biomarker_data.get('diagnostic_markers', []):
                st.write(f"- {m}")
        with col2:
            st.markdown("**예후 마커**")
            for m in _biomarker_data.get('prognostic_markers', []):
                st.write(f"- {m}")
        with col3:
            st.markdown("**치료반응 마커**")
            for m in _biomarker_data.get('therapeutic_markers', []):
                st.write(f"- {m}")
    else:
        st.info("Biomarker analysis not yet run. Execute: python scripts/12_biomarker_analysis.py")

# ============================================================
# 탭 10: 연구 동향
# ============================================================
with tab10:
    st.markdown("### Research Trends")

    _trend_log = []
    for d in _search_dirs:
        cl_path = os.path.join(d, "collection_log.json")
        if os.path.exists(cl_path):
            try:
                with open(cl_path, "r", encoding="utf-8") as f:
                    _trend_log = json.load(f)
                break
            except Exception:
                pass

    if _trend_log:
        st.success(f"총 {len(_trend_log)}건 수집 기록")
        papers = sum(1 for x in _trend_log if 'pmid' in x)
        patents = sum(1 for x in _trend_log if 'patent_number' in x)
        biorxiv = sum(1 for x in _trend_log if x.get('source') in ('biorxiv', 'medrxiv'))
        c1, c2, c3 = st.columns(3)
        c1.metric("Papers", papers)
        c2.metric("Patents", patents)
        c3.metric("Preprints", biorxiv)

        import plotly.express as px
        # 핫 키워드
        all_titles = [e.get('title', '').lower() for e in _trend_log if e.get('title')]
        if all_titles:
            stop_words = {'the', 'a', 'an', 'of', 'in', 'for', 'and', 'or', 'to', 'with',
                         'by', 'on', 'is', 'are', 'was', 'were', 'from', 'at', 'as', 'its',
                         'that', 'this', 'be', 'it', 'not', 'but', 'has', 'have', 'had'}
            word_counts = Counter()
            for title in all_titles:
                words = re.findall(r'[a-z]{3,}', title)
                for w in words:
                    if w not in stop_words:
                        word_counts[w] += 1
            if word_counts:
                kw_df = pd.DataFrame([{"키워드": k, "빈도": v} for k, v in word_counts.most_common(30)])
                fig = px.bar(kw_df, x='빈도', y='키워드', orientation='h', title='핫 키워드 Top 30',
                           color='빈도', color_continuous_scale='Reds')
                fig.update_layout(height=600, yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No collection log found. Showing basic statistics.")
        st.metric("총 문헌 수", len(df_ok))

# ============================================================
# 탭 11: Control Center
# ============================================================
with tab11:
    st.markdown("### Sarcopenia Research Control Center")

    pipeline_status = {}
    for d in _search_dirs:
        ps_path = os.path.join(d, "pipeline_status.json")
        if os.path.exists(ps_path):
            with open(ps_path, "r", encoding="utf-8") as f:
                pipeline_status = json.load(f)
            break

    agents = [
        {"id": "paper_searcher", "name": "Paper Scout", "icon": "[S]", "role": "PubMed/bioRxiv 논문 검색"},
        {"id": "patent_searcher", "name": "Patent Hunter", "icon": "[P]", "role": "USPTO/KIPRIS 특허 검색"},
        {"id": "text_extractor", "name": "Text Miner", "icon": "[T]", "role": "PDF 텍스트 추출"},
        {"id": "claude_analyzer", "name": "AI Analyst", "icon": "[A]", "role": "Claude AI 정보 분석"},
        {"id": "compound_fetcher", "name": "Chem Detective", "icon": "[C]", "role": "PubChem 구조 수집"},
        {"id": "biomarker_analyst", "name": "Biomarker Scout", "icon": "[B]", "role": "바이오마커 분석"},
        {"id": "deploy_manager", "name": "Deploy Bot", "icon": "[D]", "role": "Streamlit 배포 관리"},
    ]

    cols = st.columns(len(agents))
    for col, agent in zip(cols, agents):
        status = pipeline_status.get(agent["id"], {})
        if isinstance(status, dict):
            state = status.get("status", "idle")
        else:
            state = "idle"
        color = {"working": "[ON]", "completed": "[OK]", "error": "[ERR]"}.get(state, "[--]")
        with col:
            st.markdown(f"### {agent['icon']}")
            st.markdown(f"**{agent['name']}**")
            st.caption(f"{agent['role']}")
            st.markdown(f"{color} {state}")

    st.markdown("---")
    overall = pipeline_status.get("overall_status", "idle")
    last_update = pipeline_status.get("last_update", "N/A")
    st.markdown(f"**파이프라인 상태:** {overall} | **마지막 실행:** {last_update}")

    st.markdown("---")
    st.markdown("#### Quick Run")
    st.code("""
# 전체 파이프라인 실행
python scripts/08_orchestrator.py --weekly

# 또는 단계별 실행
python scripts/05_pubmed_collect.py --years 2
python scripts/01_pdf_extract.py
python scripts/02_info_extract.py --append
python scripts/10_pattern_analysis.py
python scripts/11_drug_candidates.py
python scripts/12_biomarker_analysis.py
    """, language="bash")
