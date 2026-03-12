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
# Navy Dark Theme CSS
# ============================================================
st.markdown("""
<style>
/* === Navy Dark Theme === */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(180deg, #0a0e27 0%, #0d1b3e 30%, #111d35 100%);
    color: #e0e6f0;
}
[data-testid="stHeader"] {
    background: rgba(10,14,39,0.95);
    backdrop-filter: blur(10px);
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0b1029 0%, #101a38 100%);
    border-right: 1px solid rgba(30,136,229,0.2);
}
[data-testid="stSidebar"] * {
    color: #c0cde0 !important;
}

/* Metric cards */
[data-testid="stMetric"] {
    background: rgba(16,26,56,0.7);
    border: 1px solid rgba(30,136,229,0.25);
    border-radius: 10px;
    padding: 12px 16px;
    backdrop-filter: blur(8px);
}
[data-testid="stMetricValue"] {
    color: #4fc3f7 !important;
    font-weight: 700;
}
[data-testid="stMetricLabel"] {
    color: #90a4ae !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(13,27,62,0.8);
    border-radius: 8px;
    padding: 4px;
    gap: 2px;
    border: 1px solid rgba(30,136,229,0.15);
}
.stTabs [data-baseweb="tab"] {
    color: #8899bb !important;
    background: transparent;
    border-radius: 6px;
    font-size: 13px;
    padding: 8px 14px;
    font-weight: 500;
}
.stTabs [aria-selected="true"] {
    background: rgba(30,136,229,0.25) !important;
    color: #4fc3f7 !important;
    border-bottom: 2px solid #1E88E5;
}

/* Expander */
[data-testid="stExpander"] {
    background: rgba(13,20,50,0.6);
    border: 1px solid rgba(30,136,229,0.15);
    border-radius: 8px;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(30,136,229,0.2);
    border-radius: 8px;
}

/* Text inputs */
.stTextInput input, .stSelectbox [data-baseweb="select"],
.stMultiSelect [data-baseweb="select"] {
    background: rgba(13,20,50,0.8) !important;
    border: 1px solid rgba(30,136,229,0.3) !important;
    color: #e0e6f0 !important;
}

/* Download buttons */
.stDownloadButton button {
    background: linear-gradient(135deg, #1565c0, #1E88E5) !important;
    color: white !important;
    border: none !important;
    border-radius: 6px;
}

/* Info/Success/Error boxes */
.stAlert {
    background: rgba(13,20,50,0.6);
    border: 1px solid rgba(30,136,229,0.2);
    border-radius: 8px;
}

/* Plotly charts dark background */
.js-plotly-plot .plotly .main-svg {
    background: transparent !important;
}

/* Markdown text */
[data-testid="stAppViewContainer"] .stMarkdown,
[data-testid="stAppViewContainer"] .stMarkdown p,
[data-testid="stAppViewContainer"] .stMarkdown li {
    color: #c8d6e5;
}
[data-testid="stAppViewContainer"] .stMarkdown h1,
[data-testid="stAppViewContainer"] .stMarkdown h2,
[data-testid="stAppViewContainer"] .stMarkdown h3,
[data-testid="stAppViewContainer"] .stMarkdown h4 {
    color: #e0e6f0;
}

/* Chat messages */
[data-testid="stChatMessage"] {
    background: rgba(13,20,50,0.5);
    border: 1px solid rgba(30,136,229,0.15);
    border-radius: 10px;
}

/* Slider */
.stSlider [data-baseweb="slider"] {
    background: rgba(30,136,229,0.2);
}

/* Code block */
.stCodeBlock {
    background: rgba(8,12,30,0.8) !important;
    border: 1px solid rgba(30,136,229,0.2);
}

/* Scrollbar */
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: #0a0e27; }
::-webkit-scrollbar-thumb { background: #1E88E5; border-radius: 4px; }

/* 3D Viewer animation pulse */
@keyframes binding-pulse {
    0% { box-shadow: 0 0 5px rgba(30,136,229,0.3); }
    50% { box-shadow: 0 0 20px rgba(30,136,229,0.6); }
    100% { box-shadow: 0 0 5px rgba(30,136,229,0.3); }
}
.binding-viewer {
    animation: binding-pulse 3s ease-in-out infinite;
    border-radius: 12px;
    overflow: hidden;
}
</style>
""", unsafe_allow_html=True)

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
<div style='background: linear-gradient(135deg, #0a1628 0%, #0d2137 30%, #0f3460 60%, #1a1a4e 100%);
     padding: 28px 36px; border-radius: 14px; margin-bottom: 24px;
     border: 1px solid rgba(30,136,229,0.3);
     box-shadow: 0 4px 24px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05);'>
    <div style='display:flex; align-items:center; gap:16px;'>
        <div style='width:48px; height:48px; border-radius:12px;
             background: linear-gradient(135deg, #1E88E5, #42a5f5);
             display:flex; align-items:center; justify-content:center;
             font-size:24px; font-weight:800; color:white;
             box-shadow: 0 2px 12px rgba(30,136,229,0.4);'>S</div>
        <div>
            <h1 style='color: #4fc3f7; margin:0; font-size: 26px; font-weight: 700;
                letter-spacing: -0.5px;'>Sarcopenia Drug Discovery Platform</h1>
            <p style='color: #7899b8; margin: 4px 0 0 0; font-size: 13px; letter-spacing: 0.3px;'>
                BasGenBio &nbsp;|&nbsp; {total} papers analyzed &nbsp;|&nbsp;
                Novel Target & Biomarker Discovery &nbsp;|&nbsp; CPI Foundation Model
            </p>
        </div>
    </div>
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

    # 치료분류 필터 (개별 카테고리로 파싱)
    if "치료분류" in df_ok.columns:
        _all_cats = set()
        for v in df_ok["치료분류"].dropna():
            s = str(v).strip()
            if s.startswith("["):
                for item in s.strip("[]").split(","):
                    item = item.strip().strip("'\" ")
                    if item and len(item) > 1:
                        _all_cats.add(item)
            elif "," in s:
                for item in s.split(","):
                    item = item.strip().strip("'\" ")
                    if item and len(item) > 1:
                        _all_cats.add(item)
            else:
                if s and len(s) > 1:
                    _all_cats.add(s)
        cat_types = sorted(_all_cats)
        if cat_types:
            selected_cats = st.multiselect("Treatment Category", cat_types, default=cat_types)
            filtered = filtered[filtered["치료분류"].apply(
                lambda x: any(c in str(x) for c in selected_cats) if pd.notna(x) else False)]

    # 질환아형 필터
    if "질환아형" in df_ok.columns:
        sub_types = sorted(df_ok["질환아형"].dropna().unique().tolist())
        if sub_types:
            selected_subs = st.multiselect("질환 아형", sub_types, default=sub_types)
            filtered = filtered[filtered["질환아형"].isin(selected_subs)]

# ============================================================
# 주요 근감소증 타겟 PDB 매핑 (전역 - tab3, tab5에서 공용)
# ============================================================
SARCOPENIA_TARGET_PDB = {
    "Myostatin/GDF-8": {"pdb": "3HH2", "uniprot": "O14793", "desc": "Myostatin (Growth Differentiation Factor 8) - 근육 성장 억제 인자", "binding_residues": "W28,W30,Y33,D56,F63,K65,H67,Y111"},
    "ActRIIB": {"pdb": "2QLU", "uniprot": "Q13705", "desc": "Activin Receptor Type IIB - Myostatin 수용체", "binding_residues": "E28,Y31,K56,E63,K74,P83,F101"},
    "mTOR/PI3K/Akt": {"pdb": "4DRH", "uniprot": "P42345", "desc": "mTOR kinase - 단백질 합성 촉진 경로", "binding_residues": "L2185,Y2225,D2195,V2240,M2345"},
    "IGF-1/IGF-1R": {"pdb": "1IMX", "uniprot": "P05019", "desc": "Insulin-like Growth Factor 1 - 근육 성장 촉진", "binding_residues": "G1,P2,E3,T4,L5,C6"},
    "MuRF1/MAFbx": {"pdb": "4FZT", "uniprot": "Q969Q1", "desc": "E3 ubiquitin ligase MuRF1 - 근단백 분해", "binding_residues": "C23,H25,C44,C47,C54,H57"},
    "FoxO3": {"pdb": "2UZK", "uniprot": "O43524", "desc": "Forkhead box O3 - 근위축 전사인자", "binding_residues": "H212,S215,W234,H242,S256"},
    "AMPK/PGC-1alpha": {"pdb": "4CFE", "uniprot": "Q13131", "desc": "AMP-activated protein kinase - 에너지 센서", "binding_residues": "R83,D88,T106,N144,D151"},
    "RIPK1/RIPK3": {"pdb": "4ITJ", "uniprot": "Q9Y572", "desc": "Receptor-interacting protein kinase 3 - Necroptosis 매개", "binding_residues": "L27,V35,A48,K50,E60,D142"},
    "NF-kB": {"pdb": "1NFI", "uniprot": "Q04206", "desc": "Nuclear Factor kappa B - 염증 전사인자", "binding_residues": "R33,E39,R57,Y60,K221,R246"},
    "Androgen Receptor": {"pdb": "1E3G", "uniprot": "P10275", "desc": "Androgen Receptor - SARMs 타겟", "binding_residues": "L704,N705,R752,F764,M780,T877"},
    "GDF-15": {"pdb": "5VZ3", "uniprot": "Q99988", "desc": "Growth Differentiation Factor 15 - 식욕/체중 조절", "binding_residues": "R189,H193,D200,W203,I206"},
    "HDAC6": {"pdb": "5EDU", "uniprot": "Q9UBN7", "desc": "Histone Deacetylase 6 - 미세소관/자가포식 조절", "binding_residues": "H573,H574,D612,H614,D705,L749"},
}

# ============================================================
# 탭 구성
# ============================================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12 = st.tabs([
    "Dashboard",
    "Literature Search",
    "Target Analysis",
    "Compound Analysis",
    "CPI Binding",
    "Target-Compound Matrix",
    "AI Q&A",
    "Dark Targets",
    "AI Drug Candidates",
    "Biomarkers",
    "Research Trends",
    "Control Center",
])

# ============================================================
# Plotly Dark Theme Helper
# ============================================================
_DARK_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(10,14,39,0.4)",
    font=dict(color="#c0cde0", size=12),
    title_font=dict(color="#e0e6f0", size=15),
    xaxis=dict(gridcolor="rgba(30,136,229,0.1)", zerolinecolor="rgba(30,136,229,0.2)"),
    yaxis=dict(gridcolor="rgba(30,136,229,0.1)", zerolinecolor="rgba(30,136,229,0.2)"),
    coloraxis_colorbar=dict(tickfont=dict(color="#90a4ae")),
    legend=dict(font=dict(color="#c0cde0")),
)
def _apply_dark(fig):
    fig.update_layout(**_DARK_LAYOUT)
    return fig

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
            st.plotly_chart(_apply_dark(fig1), use_container_width=True)

    with col_r:
        rel_dist = df_ok["관련도"].value_counts().sort_index().reset_index()
        rel_dist.columns = ["관련도 점수", "건수"]
        fig2 = px.bar(rel_dist, x="관련도 점수", y="건수",
                      title="관련도 점수 분포",
                      color="건수", color_continuous_scale="Reds")
        fig2.update_layout(height=350, margin=dict(t=40, b=20, l=20, r=20))
        st.plotly_chart(_apply_dark(fig2), use_container_width=True)

    # 치료분류 분포 (개별 카테고리로 파싱)
    if "치료분류" in df_ok.columns:
        _cat_items = []
        for v in df_ok["치료분류"].dropna():
            s = str(v).strip()
            # "['Nutritional', 'Diagnostic']" 형태 파싱
            if s.startswith("["):
                for item in s.strip("[]").split(","):
                    item = item.strip().strip("'\" ")
                    if item and len(item) > 1:
                        _cat_items.append(item)
            elif "," in s:
                for item in s.split(","):
                    item = item.strip().strip("'\" ")
                    if item and len(item) > 1:
                        _cat_items.append(item)
            else:
                if s and len(s) > 1:
                    _cat_items.append(s)
        _cat_counter = Counter(_cat_items)
        _cat_top = _cat_counter.most_common(12)
        if _cat_top:
            cat_dist = pd.DataFrame(_cat_top, columns=["Category", "Papers"])
            fig_cat = px.bar(cat_dist, x="Papers", y="Category", orientation="h",
                             title="Treatment Classification",
                             color="Papers", color_continuous_scale="Teal")
            fig_cat.update_layout(height=350, yaxis=dict(autorange="reversed"),
                                  margin=dict(t=40, b=20, l=20, r=20),
                                  showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(_apply_dark(fig_cat), use_container_width=True)

    # Top 타겟
    top_targets = get_top_items(df_ok, "타겟(Target)", 15, normalize_target)
    if top_targets:
        tgt_df = pd.DataFrame(top_targets, columns=["타겟", "논문수"])
        fig3 = px.bar(tgt_df, x="논문수", y="타겟", orientation="h",
                      title="Top 15 Drug Targets",
                      color="논문수", color_continuous_scale="Blues")
        fig3.update_layout(height=450, yaxis=dict(autorange="reversed"))
        st.plotly_chart(_apply_dark(fig3), use_container_width=True)

    # Top 화합물
    top_compounds = get_top_items(df_ok, "화합물(Compound)", 15)
    if top_compounds:
        comp_df = pd.DataFrame(top_compounds, columns=["화합물", "논문수"])
        fig4 = px.bar(comp_df, x="논문수", y="화합물", orientation="h",
                      title="Top 15 Compounds",
                      color="논문수", color_continuous_scale="Greens")
        fig4.update_layout(height=450, yaxis=dict(autorange="reversed"))
        st.plotly_chart(_apply_dark(fig4), use_container_width=True)

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
    import streamlit.components.v1 as _comp3
    st.markdown("### Target Analysis")

    # ── Target Biology DB (논문 AI 분석 기반) ──
    TARGET_BIOLOGY = {
        "Myostatin/GDF-8": {
            "gene": "MSTN", "chromosome": "2q32.2", "protein_size": "375 aa",
            "function": "TGF-beta superfamily 음성 조절자로 골격근 성장을 억제",
            "diseases": ["Age-related sarcopenia", "Cancer cachexia", "Muscular dystrophy", "Sarcopenic obesity", "Disuse atrophy"],
            "pathways": ["Myostatin/ActRII/SMAD2/3", "IGF-1/PI3K/Akt/mTOR", "Ubiquitin-proteasome", "NF-kB", "Wnt/beta-catenin"],
            "genes": ["MSTN", "ACVR2B", "SMAD2", "SMAD3", "SMAD7", "FSTL3 (Follistatin-like 3)", "GDF11", "TGFBR1"],
            "biomarkers": ["Myostatin level", "Grip strength", "IL-6", "TNF-alpha", "Muscle mass (ASM/ht2)"],
        },
        "ActRIIB": {
            "gene": "ACVR2B", "chromosome": "3p22.2", "protein_size": "512 aa",
            "function": "Activin/Myostatin 수용체 - 근육 성장 억제 신호 전달",
            "diseases": ["Age-related sarcopenia", "Cancer cachexia", "Muscular dystrophy", "Disuse atrophy"],
            "pathways": ["Myostatin/ActRII/SMAD2/3", "Activin A signaling", "BMP signaling", "Wnt/beta-catenin"],
            "genes": ["ACVR2B", "ACVR2A", "MSTN", "INHBA (Activin A)", "FST (Follistatin)", "BMPR1A", "SMAD4"],
            "biomarkers": ["Activin A level", "Follistatin", "Grip strength", "Lean body mass"],
        },
        "mTOR/PI3K/Akt": {
            "gene": "MTOR", "chromosome": "1p36.22", "protein_size": "2549 aa",
            "function": "세포 성장/대사 마스터 조절자 - 근단백질 합성 핵심 경로",
            "diseases": ["Age-related sarcopenia", "Sarcopenic obesity", "Diabetic sarcopenia", "Drug-induced atrophy", "Cancer cachexia"],
            "pathways": ["PI3K/Akt/mTORC1", "mTORC1/S6K1/4E-BP1", "AMPK/TSC2", "Insulin/IGF-1 signaling", "Autophagy-lysosome"],
            "genes": ["MTOR", "PIK3CA", "AKT1", "RPS6KB1 (S6K1)", "EIF4EBP1 (4E-BP1)", "TSC1", "TSC2", "RPTOR (Raptor)"],
            "biomarkers": ["p-mTOR/p-S6K1", "Muscle protein synthesis rate", "Grip strength", "SPPB score"],
        },
        "IGF-1/IGF-1R": {
            "gene": "IGF1 / IGF1R", "chromosome": "12q23.2 / 15q26.3", "protein_size": "70 aa / 1367 aa",
            "function": "근육 성장/분화 촉진 - 동화 호르몬 신호 전달",
            "diseases": ["Age-related sarcopenia", "GH deficiency", "Sarcopenic obesity", "Cancer cachexia", "Diabetic sarcopenia"],
            "pathways": ["IGF-1/IGF-1R/IRS-1", "PI3K/Akt/mTOR", "MAPK/ERK", "GH/IGF-1 axis", "Satellite cell activation"],
            "genes": ["IGF1", "IGF1R", "IRS1", "IRS2", "GHR", "GH1", "IGFBP3", "IGFBP5"],
            "biomarkers": ["Serum IGF-1", "IGFBP-3", "Grip strength", "Gait speed", "Muscle mass"],
        },
        "MuRF1/MAFbx": {
            "gene": "TRIM63 / FBXO32", "chromosome": "1p36.11 / 8q24.13", "protein_size": "353 aa / 355 aa",
            "function": "E3 유비퀴틴 리가제 - 근단백질 분해 핵심 효소",
            "diseases": ["Drug-induced atrophy", "Disuse atrophy", "Cancer cachexia", "Age-related sarcopenia", "Sepsis-induced myopathy"],
            "pathways": ["Ubiquitin-proteasome system", "FoxO3/Atrogin-1/MuRF1", "NF-kB/MuRF1", "Glucocorticoid receptor/GR", "IGF-1/Akt (inhibitory)"],
            "genes": ["TRIM63 (MuRF1)", "FBXO32 (MAFbx/Atrogin-1)", "FOXO3", "FOXO1", "UBB", "UBC", "PSMA1", "NFKB1"],
            "biomarkers": ["MuRF1 expression", "Atrogin-1 expression", "Myotube diameter", "Grip strength", "Muscle mass"],
        },
        "FoxO3": {
            "gene": "FOXO3", "chromosome": "6q21", "protein_size": "673 aa",
            "function": "전사인자 - 근위축 유전자(MuRF1/MAFbx) 발현 조절",
            "diseases": ["Age-related sarcopenia", "Diabetic sarcopenia", "Drug-induced atrophy", "Sarcopenic obesity", "Disuse atrophy"],
            "pathways": ["FoxO3/Atrogin-1/MuRF1", "Akt/FoxO3 (phosphorylation)", "AMPK/FoxO3", "Autophagy-lysosome", "SIRT1/FoxO3"],
            "genes": ["FOXO3", "FOXO1", "FOXO4", "TRIM63", "FBXO32", "BNIP3 (autophagy)", "LC3B", "SIRT1"],
            "biomarkers": ["p-FoxO3/FoxO3 ratio", "MuRF1 expression", "Grip strength", "Muscle mass"],
        },
        "AMPK/PGC-1alpha": {
            "gene": "PRKAA1 / PPARGC1A", "chromosome": "5p13.1 / 4p15.2", "protein_size": "559 aa / 798 aa",
            "function": "에너지 센서 및 미토콘드리아 생합성 마스터 조절자",
            "diseases": ["Age-related sarcopenia", "Sarcopenic obesity", "Diabetic sarcopenia", "Metabolic syndrome", "Disuse atrophy"],
            "pathways": ["AMPK/PGC-1alpha/TFAM", "Mitochondrial biogenesis", "SIRT1/PGC-1alpha", "AMPK/TSC2/mTOR", "Fatty acid oxidation"],
            "genes": ["PRKAA1 (AMPKa1)", "PRKAA2 (AMPKa2)", "PPARGC1A (PGC-1a)", "TFAM", "NRF1", "NRF2", "SIRT1", "SIRT3"],
            "biomarkers": ["p-AMPK level", "PGC-1alpha expression", "Mitochondrial DNA copy number", "Grip strength"],
        },
        "RIPK1/RIPK3": {
            "gene": "RIPK1 / RIPK3", "chromosome": "6p25.2 / 14q12", "protein_size": "671 aa / 518 aa",
            "function": "Necroptosis 핵심 키나제 - 프로그램된 괴사 및 염증 조절",
            "diseases": ["Age-related sarcopenia", "IBD-associated myopathy", "Neurodegeneration", "Muscle necroptosis"],
            "pathways": ["TNF-alpha/RIPK1/RIPK3/MLKL", "Necroptosis", "Caspase-8 apoptosis", "GSDME-mediated pyroptosis", "NF-kB (pro-survival)"],
            "genes": ["RIPK1", "RIPK3", "MLKL", "CASP8", "FADD", "TNF", "TNFRSF1A", "GSDME"],
            "biomarkers": ["p-RIPK3", "p-MLKL", "TNF-alpha", "Grip strength", "Gastrocnemius muscle index"],
        },
        "NF-kB": {
            "gene": "NFKB1 / RELA", "chromosome": "4q24 / 11q13.1", "protein_size": "969 aa / 551 aa",
            "function": "염증 마스터 전사인자 - 만성 염증 매개 근위축",
            "diseases": ["Age-related sarcopenia", "Cancer cachexia", "Sarcopenic obesity", "Inflammatory myopathy", "Sepsis"],
            "pathways": ["NF-kB canonical (IKK/IkBa)", "TNF-alpha/TNFR1/NF-kB", "IL-6/JAK-STAT3", "Inflammaging", "NLRP3 inflammasome"],
            "genes": ["NFKB1", "RELA (p65)", "NFKBIA (IkBa)", "IKBKB (IKKb)", "TNF", "IL6", "IL1B", "NLRP3"],
            "biomarkers": ["NF-kB activation", "IL-6", "TNF-alpha", "CRP", "Grip strength"],
        },
        "Androgen Receptor": {
            "gene": "AR", "chromosome": "Xq12", "protein_size": "919 aa",
            "function": "스테로이드 호르몬 수용체 - 근육 동화 작용 매개",
            "diseases": ["Hypogonadal sarcopenia", "Cancer cachexia", "Age-related sarcopenia", "Sarcopenic obesity", "PCOS-related"],
            "pathways": ["AR/Testosterone signaling", "AR/Wnt/beta-catenin", "IGF-1/PI3K/Akt (crosstalk)", "Myostatin inhibition (AR-mediated)", "Satellite cell differentiation"],
            "genes": ["AR", "SRD5A1 (5aR1)", "SRD5A2 (5aR2)", "CYP19A1 (Aromatase)", "SHBG", "IGF1", "MSTN", "MYF5"],
            "biomarkers": ["Free testosterone", "Total testosterone", "SHBG", "Grip strength", "Lean body mass"],
        },
        "GDF-15": {
            "gene": "GDF15", "chromosome": "19p13.11", "protein_size": "308 aa",
            "function": "GFRAL 수용체 리간드 - 식욕 억제 및 체중/근육량 조절",
            "diseases": ["Cancer cachexia", "Age-related sarcopenia", "Sarcopenic obesity", "Mitochondrial disease", "Heart failure-cachexia"],
            "pathways": ["GDF-15/GFRAL/RET", "MAPK/ERK", "Energy metabolism", "Appetite regulation (brainstem)", "Mitochondrial stress response"],
            "genes": ["GDF15", "GFRAL", "RET", "NRTN", "ATF4 (stress response)", "CHOP", "FGF21", "CLCN3"],
            "biomarkers": ["Serum GDF-15", "Body weight change", "Irisin", "IGF-1", "Grip strength"],
        },
        "HDAC6": {
            "gene": "HDAC6", "chromosome": "Xp11.23", "protein_size": "1215 aa",
            "function": "세포질 히스톤 탈아세틸화효소 - 미세소관/자가포식 조절",
            "diseases": ["Age-related sarcopenia", "CMT neuropathy", "Neurodegeneration", "Cancer (multiple myeloma)", "Muscle atrophy"],
            "pathways": ["HDAC6/alpha-tubulin deacetylation", "Aggresome-autophagy", "HSP90 client regulation", "Ubiquitin-proteasome", "TFEB/lysosome biogenesis"],
            "genes": ["HDAC6", "TUBA1A (alpha-tubulin)", "HSP90AA1", "SQSTM1 (p62)", "MAP1LC3B (LC3B)", "HDAC4", "SIRT1", "TFEB"],
            "biomarkers": ["Acetylated alpha-tubulin", "p62/SQSTM1", "Grip strength", "Muscle mass index"],
        },
    }

    target_counts = {t: len(idxs) for t, idxs in target_index.items() if len(t) > 1}
    sorted_targets = sorted(target_counts.keys(), key=lambda x: target_counts[x], reverse=True)
    top100 = sorted_targets[:100]
    selected_target = st.selectbox("Target Selection (by paper count)", top100,
                                    format_func=lambda x: f"{x} ({target_counts.get(x,0)} papers)")
    if selected_target:
        idxs = target_index.get(selected_target, [])
        t_papers = df_ok.loc[df_ok.index.isin(idxs)]
        avg_rel = t_papers["관련도"].mean()

        # ── 메트릭 카드 ──
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Papers", f"{len(t_papers)}")
        c2.metric("Avg Relevance", f"{avg_rel:.1f}/5")
        c3.metric("High Relevance(4+)", f"{len(t_papers[t_papers['관련도']>=4])}")
        clinical_cnt = len(t_papers[t_papers["연구유형"] == "Clinical"]) if "연구유형" in t_papers.columns else 0
        c4.metric("Clinical Studies", f"{clinical_cnt}")

        st.markdown("---")

        # ── PDB 정보 확인 ──
        _tgt_pdb_info = SARCOPENIA_TARGET_PDB.get(selected_target, None)
        _tgt_bio = TARGET_BIOLOGY.get(selected_target, None)

        # ─────────────────────────────────────
        # 상단: 3D Structure + Target Biology 카드
        # ─────────────────────────────────────
        if _tgt_pdb_info or _tgt_bio:
            col_3d, col_bio = st.columns([3, 2])

            with col_3d:
                if _tgt_pdb_info:
                    _pdb3 = _tgt_pdb_info["pdb"]
                    _br3 = _tgt_pdb_info.get("binding_residues", "")
                    _desc3 = _tgt_pdb_info.get("desc", "")
                    _uni3 = _tgt_pdb_info.get("uniprot", "")

                    _viewer3_html = f"""
<!DOCTYPE html><html><head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.7.1/jquery.min.js"></script>
<script src="https://3Dmol.org/build/3Dmol-min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background: #0a0e27; overflow:hidden; font-family: 'Segoe UI', system-ui, sans-serif; }}
#vp3 {{ width:100%; height:420px; position:relative; border-radius:12px;
    border: 1px solid rgba(30,136,229,0.3); box-shadow: 0 0 30px rgba(30,136,229,0.15); }}
#info3 {{ position:absolute; top:10px; left:10px; z-index:100;
    background: rgba(10,14,39,0.9); color:#4fc3f7; padding:8px 14px; border-radius:8px;
    font-size:11px; border: 1px solid rgba(30,136,229,0.3); backdrop-filter: blur(10px); }}
#info3 h4 {{ margin:0 0 3px 0; color:#90caf9; font-size:13px; }}
#info3 p {{ margin:1px 0; color:#7899b8; font-size:10px; }}
#ld3 {{ position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);
    color:#4fc3f7; font-size:13px; z-index:50; }}
@keyframes sp3 {{ to {{ transform: rotate(360deg); }} }}
.sp3 {{ display:inline-block; width:18px; height:18px; border:2px solid #4fc3f7;
    border-top-color:transparent; border-radius:50%; animation: sp3 1s linear infinite;
    vertical-align:middle; margin-right:6px; }}
.pocket-label {{ position:absolute; bottom:10px; right:10px; z-index:100;
    background: rgba(0,230,118,0.15); color:#00e676; padding:4px 10px; border-radius:6px;
    font-size:10px; border: 1px solid rgba(0,230,118,0.3); }}
</style></head><body>
<div id="vp3">
    <div id="info3">
        <h4>{selected_target}</h4>
        <p>PDB: {_pdb3} | UniProt: {_uni3}</p>
        <p>{_desc3}</p>
    </div>
    <div id="ld3"><span class="sp3"></span>Loading PDB...</div>
    <div class="pocket-label">Binding Pocket Highlighted</div>
</div>
<script>
(function() {{
    var el = document.getElementById("vp3");
    var viewer = $3Dmol.createViewer(el, {{ backgroundColor: 0x0a0e27, antialias: true }});
    fetch("https://files.rcsb.org/download/{_pdb3}.pdb")
        .then(function(r) {{ if (!r.ok) throw new Error("HTTP "+r.status); return r.text(); }})
        .then(function(data) {{
            document.getElementById("ld3").style.display="none";
            viewer.addModel(data, "pdb");
            viewer.setStyle({{}}, {{ cartoon: {{ color: "spectrum", opacity: 0.82, thickness: 0.28 }} }});
            var residues = "{_br3}".split(",");
            for (var i=0; i<residues.length; i++) {{
                var rn = residues[i].trim();
                var num = parseInt(rn.replace(/[A-Za-z]/g, ""));
                if (!isNaN(num)) {{
                    viewer.setStyle({{resi: num}}, {{
                        stick: {{ color: "#00e676", radius: 0.22 }},
                        sphere: {{ color: "#00e676", radius: 0.38, opacity: 0.55 }},
                        cartoon: {{ color: "#00e676", opacity: 0.95, thickness: 0.42 }}
                    }});
                    viewer.addLabel(rn, {{
                        position: {{resi: num}}, backgroundColor: "rgba(0,230,118,0.8)",
                        fontColor: "#0a0e27", fontSize: 9, borderThickness: 0.5
                    }});
                }}
            }}
            var nums = residues.map(function(r){{return parseInt(r.replace(/[A-Za-z]/g,""));}}).filter(function(n){{return !isNaN(n);}});
            if (nums.length > 0) {{
                viewer.addSurface($3Dmol.SurfaceType.VDW, {{ opacity: 0.2, color: "#00e676" }}, {{resi: nums}});
            }}
            viewer.zoomTo(); viewer.render();
            function anim() {{ viewer.rotate(0.2, "y"); viewer.render(); requestAnimationFrame(anim); }}
            anim();
        }})
        .catch(function(e) {{ document.getElementById("ld3").innerHTML = "Error: " + e.message; }});
}})();
</script></body></html>"""
                    _comp3.html(_viewer3_html, height=440)
                else:
                    st.info("PDB 구조가 등록되지 않은 타겟입니다.")

            with col_bio:
                if _tgt_bio:
                    st.markdown("#### Target Biology")
                    st.markdown(f"""
<div style="background:rgba(13,27,62,0.6); border:1px solid rgba(30,136,229,0.3); border-radius:10px; padding:14px; margin-bottom:10px;">
    <div style="color:#90caf9; font-size:13px; font-weight:700; margin-bottom:6px;">{selected_target}</div>
    <div style="color:#7899b8; font-size:11px; margin-bottom:4px;">Gene: <span style="color:#4fc3f7;">{_tgt_bio['gene']}</span> | Chr: {_tgt_bio['chromosome']}</div>
    <div style="color:#7899b8; font-size:11px; margin-bottom:4px;">Protein: {_tgt_bio['protein_size']}</div>
    <div style="color:#b0bec5; font-size:11px; line-height:1.4;">{_tgt_bio['function']}</div>
</div>
""", unsafe_allow_html=True)

                    # Diseases
                    st.markdown("#### Related Diseases")
                    _dis_colors = ["#ff6b6b", "#ffa94d", "#ffd43b", "#69db7c", "#74c0fc"]
                    _dis_html = ""
                    for i, d in enumerate(_tgt_bio.get("diseases", [])[:5]):
                        _dc = _dis_colors[i % len(_dis_colors)]
                        _dis_html += f'<span style="display:inline-block;padding:3px 10px;margin:2px 4px 2px 0;border-radius:12px;font-size:11px;background:rgba({int(_dc[1:3],16)},{int(_dc[3:5],16)},{int(_dc[5:7],16)},0.15);color:{_dc};border:1px solid {_dc}40;">{d}</span>'
                    st.markdown(_dis_html, unsafe_allow_html=True)

                    # Key Genes
                    st.markdown("#### Associated Genes")
                    _gene_html = ""
                    for g in _tgt_bio.get("genes", [])[:8]:
                        _gene_html += f'<span style="display:inline-block;padding:2px 8px;margin:2px 3px;border-radius:6px;font-size:10px;font-family:monospace;background:rgba(79,195,247,0.1);color:#4fc3f7;border:1px solid rgba(79,195,247,0.25);">{g}</span>'
                    st.markdown(_gene_html, unsafe_allow_html=True)

                    # Biomarkers
                    st.markdown("#### Key Biomarkers")
                    _bm_html = ""
                    for bm in _tgt_bio.get("biomarkers", [])[:5]:
                        _bm_html += f'<span style="display:inline-block;padding:2px 8px;margin:2px 3px;border-radius:6px;font-size:10px;background:rgba(0,230,118,0.1);color:#69f0ae;border:1px solid rgba(0,230,118,0.25);">{bm}</span>'
                    st.markdown(_bm_html, unsafe_allow_html=True)

        # ─────────────────────────────────────
        # 중단: Signaling Pathways + 연관 화합물
        # ─────────────────────────────────────
        st.markdown("---")
        col_pw, col_cmp = st.columns(2)

        with col_pw:
            st.markdown("#### Signaling Pathways")
            # 논문 기반 경로
            t_path = get_top_items(t_papers, "신호전달경로", 10) if "신호전달경로" in t_papers.columns else []
            # Biology DB 경로 병합
            _bio_paths = _tgt_bio.get("pathways", []) if _tgt_bio else []
            if _bio_paths:
                _pw_html = ""
                for i, pw in enumerate(_bio_paths[:6]):
                    _pw_cnt = ""
                    for tp, tc in t_path:
                        if any(k.lower() in tp.lower() for k in pw.split("/")[:2]):
                            _pw_cnt = f" ({tc} papers)"
                            break
                    _bar_w = max(30, min(100, 30 + i * 12))
                    _pw_html += f"""<div style="margin:4px 0;padding:6px 10px;background:linear-gradient(90deg, rgba(30,136,229,0.2) {_bar_w}%, transparent {_bar_w}%);border-radius:6px;border-left:3px solid #1E88E5;">
                        <span style="color:#90caf9;font-size:11px;font-weight:600;">{pw}</span>
                        <span style="color:#546e7a;font-size:9px;">{_pw_cnt}</span>
                    </div>"""
                st.markdown(_pw_html, unsafe_allow_html=True)
            elif t_path:
                for pw, cnt in t_path[:8]:
                    st.markdown(f'<div style="margin:3px 0;padding:4px 10px;background:rgba(30,136,229,0.1);border-radius:6px;border-left:3px solid #1E88E5;color:#90caf9;font-size:11px;">{pw} <span style="color:#546e7a;">({cnt})</span></div>', unsafe_allow_html=True)

        with col_cmp:
            st.markdown("#### Related Compounds")
            t_comp = get_top_items(t_papers, "화합물(Compound)", 10)
            if t_comp:
                t_comp_df = pd.DataFrame(t_comp, columns=["Compound", "Papers"])
                fig = px.bar(t_comp_df, x="Papers", y="Compound", orientation="h",
                            color="Papers", color_continuous_scale="YlOrRd")
                fig.update_layout(height=280, yaxis=dict(autorange="reversed"), margin=dict(t=5, b=5, l=5, r=5),
                                  showlegend=False, coloraxis_showscale=False)
                st.plotly_chart(_apply_dark(fig), use_container_width=True)

        # ─────────────────────────────────────
        # 하단: 핵심 발견 + 연구유형
        # ─────────────────────────────────────
        st.markdown("---")
        col_find, col_type = st.columns([3, 1])

        with col_find:
            st.markdown("#### Key Findings (High Relevance)")
            high_rel = t_papers.sort_values("관련도", ascending=False)
            for _, row in high_rel.head(6).iterrows():
                finding = row.get("핵심발견", "")
                if finding and str(finding) != "nan":
                    rel = int(row.get("관련도", 0))
                    _stars = "★" * rel + "☆" * (5 - rel)
                    st.markdown(f"""<div style="background:rgba(13,27,62,0.4);border-radius:8px;padding:8px 12px;margin:4px 0;border-left:3px solid {'#00e676' if rel>=4 else '#ffd740' if rel>=3 else '#78909c'};">
                        <div style="color:#546e7a;font-size:9px;margin-bottom:2px;">{_stars} {row['파일명'][:55]}...</div>
                        <div style="color:#b0bec5;font-size:11px;line-height:1.4;">{str(finding)[:200]}</div>
                    </div>""", unsafe_allow_html=True)

        with col_type:
            st.markdown("#### Study Types")
            if "연구유형" in t_papers.columns:
                _type_counts = t_papers["연구유형"].value_counts()
                for stype, cnt in _type_counts.items():
                    if str(stype) != "nan":
                        _pct = cnt / len(t_papers) * 100
                        st.markdown(f"""<div style="margin:3px 0;padding:4px 8px;background:rgba(13,27,62,0.4);border-radius:6px;">
                            <div style="color:#90caf9;font-size:11px;">{stype}</div>
                            <div style="background:rgba(30,136,229,0.15);border-radius:3px;height:6px;margin:2px 0;">
                                <div style="background:#1E88E5;width:{_pct}%;height:100%;border-radius:3px;"></div>
                            </div>
                            <div style="color:#546e7a;font-size:9px;">{cnt} ({_pct:.0f}%)</div>
                        </div>""", unsafe_allow_html=True)

        # 프로파일 다운로드
        _bio_text = ""
        if _tgt_bio:
            _bio_text = f"\n## Target Biology\n- Gene: {_tgt_bio['gene']}\n- Chromosome: {_tgt_bio['chromosome']}\n- Function: {_tgt_bio['function']}\n- Diseases: {', '.join(_tgt_bio['diseases'])}\n- Pathways: {', '.join(_tgt_bio['pathways'])}\n- Genes: {', '.join(_tgt_bio['genes'])}\n"
        profile_text = f"# {selected_target} - Target Profile Report\nDate: {datetime.now().strftime('%Y-%m-%d')}\n\n## Summary\n- Papers: {len(t_papers)}\n- Avg Relevance: {avg_rel:.1f}/5.0\n- Clinical Studies: {clinical_cnt}\n{_bio_text}"
        st.download_button("Download Target Profile (.md)", profile_text, f"{selected_target}_profile.md", "text/markdown")

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

        # ── COMPOUND_KNOWLEDGE / COMPOUND_TARGET_MAP에서 보강 정보 가져오기 ──
        _ck4 = COMPOUND_KNOWLEDGE.get(selected_compound, {}) if "COMPOUND_KNOWLEDGE" in dir() else {}
        _ctm4 = COMPOUND_TARGET_MAP.get(selected_compound, {}) if "COMPOUND_TARGET_MAP" in dir() else {}

        # ── 메트릭 카드 ──
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Papers", f"{len(c_papers)}")
        c2.metric("Avg Relevance", f"{c_papers['관련도'].mean():.1f}/5")
        clinical = len(c_papers[c_papers["연구유형"] == "Clinical"]) if "연구유형" in c_papers.columns else 0
        c3.metric("Clinical Studies", f"{clinical}")
        _cmp_phase4 = _ck4.get("phase", _ctm4.get("phase", ""))
        c4.metric("Dev Phase", _cmp_phase4 if _cmp_phase4 else "-")

        # ── MoA + Indication 요약 배너 ──
        _moa4 = _ck4.get("moa_short", _ctm4.get("moa_short", ""))
        _ind4 = _ck4.get("indication", _ctm4.get("indication", ""))
        _pw4 = _ck4.get("pathway", "")
        if _moa4 or _ind4:
            st.markdown(f"""<div style="background:linear-gradient(135deg, rgba(13,27,62,0.8), rgba(30,136,229,0.15));
                border:1px solid rgba(30,136,229,0.3); border-radius:10px; padding:12px 18px; margin:8px 0;">
                <div style="display:flex;gap:24px;flex-wrap:wrap;">
                    {"<div><span style='color:#546e7a;font-size:10px;'>MECHANISM OF ACTION</span><div style=color:#4fc3f7;font-size:13px;font-weight:600;>" + _moa4 + "</div></div>" if _moa4 else ""}
                    {"<div><span style='color:#546e7a;font-size:10px;'>INDICATION</span><div style=color:#ffcc80;font-size:13px;font-weight:600;>" + _ind4 + "</div></div>" if _ind4 else ""}
                    {"<div><span style='color:#546e7a;font-size:10px;'>KEY PATHWAY</span><div style=color:#69f0ae;font-size:12px;>" + _pw4 + "</div></div>" if _pw4 else ""}
                </div>
            </div>""", unsafe_allow_html=True)

        st.markdown("---")

        # ═══════════════════════════════════════════════════════
        # 핵심: Binding Targets → Disease → Biomarkers 연쇄 분석
        # ═══════════════════════════════════════════════════════

        # 1. 논문에서 바인딩 타겟 추출
        c_tgt = get_top_items(c_papers, "타겟(Target)", 10, normalize_target)

        # 2. 논문에서 질환아형 추출
        _c4_diseases = []
        for v in c_papers["질환아형"].dropna():
            for d in str(v).strip("[]'\" ").split(","):
                d = d.strip().strip("'\" ")
                if d and len(d) > 2:
                    _c4_diseases.append(d)
        _c4_dis_counter = Counter(_c4_diseases)

        # 3. 논문에서 바이오마커 추출
        _c4_biomarkers = []
        if "바이오마커" in c_papers.columns:
            for v in c_papers["바이오마커"].dropna():
                for b in str(v).split(","):
                    b = b.strip()
                    if b and len(b) > 2 and len(b) < 50:
                        _c4_biomarkers.append(b)
        _c4_bm_counter = Counter(_c4_biomarkers)
        _c4_bm_total = sum(_c4_bm_counter.values()) or 1

        # ── Binding Targets (좌) + Disease Indications (우) ──
        col_tgt4, col_dis4 = st.columns(2)

        with col_tgt4:
            st.markdown("#### Binding Targets")
            if c_tgt:
                _tgt4_html = ""
                _tgt4_colors = ["#4fc3f7", "#00e676", "#ffd740", "#ff4081", "#ea80fc", "#ff6e40", "#69f0ae", "#40c4ff"]
                for i, (tgt_name, tgt_cnt) in enumerate(c_tgt[:8]):
                    _tc = _tgt4_colors[i % len(_tgt4_colors)]
                    _tgt_bio4 = TARGET_BIOLOGY.get(tgt_name, {})
                    _tgt_func = _tgt_bio4.get("function", "")[:60] if _tgt_bio4 else ""
                    _tgt_pdb = SARCOPENIA_TARGET_PDB.get(tgt_name, {})
                    _pdb_id = _tgt_pdb.get("pdb", "")
                    _pdb_badge = f"<span style='padding:1px 5px;border-radius:4px;font-size:9px;background:rgba(0,230,118,0.15);color:#69f0ae;margin-left:6px;'>PDB: {_pdb_id}</span>" if _pdb_id else ""
                    _bar_pct = min(100, int(tgt_cnt / max(c_tgt[0][1], 1) * 100))
                    _tgt4_html += f"""<div style="margin:5px 0;padding:8px 12px;background:rgba(13,27,62,0.5);
                        border-radius:8px;border-left:4px solid {_tc};transition:all 0.3s;">
                        <div style="display:flex;align-items:center;justify-content:space-between;">
                            <div>
                                <span style="color:{_tc};font-size:13px;font-weight:700;">{tgt_name}</span>
                                {_pdb_badge}
                            </div>
                            <span style="color:#78909c;font-size:11px;font-weight:600;">{tgt_cnt} papers</span>
                        </div>
                        <div style="background:rgba(255,255,255,0.05);border-radius:3px;height:4px;margin:4px 0 3px 0;">
                            <div style="background:{_tc};width:{_bar_pct}%;height:100%;border-radius:3px;"></div>
                        </div>
                        {"<div style='color:#78909c;font-size:10px;line-height:1.3;'>" + _tgt_func + "</div>" if _tgt_func else ""}
                    </div>"""
                st.markdown(_tgt4_html, unsafe_allow_html=True)

        with col_dis4:
            st.markdown("#### Disease Indications")
            _dis4_colors = ["#ff6b6b", "#ffa94d", "#ffd43b", "#69db7c", "#74c0fc", "#b197fc"]
            if _c4_dis_counter:
                _dis4_html = ""
                _dis4_max = max(_c4_dis_counter.values())
                for i, (dis, cnt) in enumerate(_c4_dis_counter.most_common(6)):
                    _dc = _dis4_colors[i % len(_dis4_colors)]
                    _bar_pct = min(100, int(cnt / _dis4_max * 100))
                    # 이 질환에서 관련 타겟 찾기
                    _related_tgts = []
                    for tgt_name, tgt_bio in TARGET_BIOLOGY.items():
                        if dis in tgt_bio.get("diseases", []) or any(dis.lower() in d.lower() for d in tgt_bio.get("diseases", [])):
                            _related_tgts.append(tgt_name)
                    _tgt_tags = " ".join([f"<span style='padding:1px 4px;border-radius:3px;font-size:8px;background:rgba(79,195,247,0.12);color:#4fc3f7;'>{t}</span>" for t in _related_tgts[:3]])
                    _dis4_html += f"""<div style="margin:5px 0;padding:8px 12px;background:rgba(13,27,62,0.5);
                        border-radius:8px;border-left:4px solid {_dc};">
                        <div style="display:flex;align-items:center;justify-content:space-between;">
                            <span style="color:{_dc};font-size:12px;font-weight:600;">{dis}</span>
                            <span style="color:#78909c;font-size:11px;">{cnt} papers</span>
                        </div>
                        <div style="background:rgba(255,255,255,0.05);border-radius:3px;height:4px;margin:4px 0 3px 0;">
                            <div style="background:{_dc};width:{_bar_pct}%;height:100%;border-radius:3px;opacity:0.7;"></div>
                        </div>
                        {"<div style='margin-top:2px;display:flex;gap:3px;flex-wrap:wrap;'>" + _tgt_tags + "</div>" if _tgt_tags else ""}
                    </div>"""
                st.markdown(_dis4_html, unsafe_allow_html=True)

        # ── Biomarkers with Importance Score ──
        st.markdown("---")
        st.markdown("#### Key Biomarkers (by Evidence Strength)")
        if _c4_bm_counter:
            _bm4_top = _c4_bm_counter.most_common(12)
            _bm4_max = _bm4_top[0][1] if _bm4_top else 1
            _bm4_html = '<div style="display:flex;flex-wrap:wrap;gap:6px;">'
            for bm, cnt in _bm4_top:
                _importance = min(5, max(1, round(cnt / _bm4_max * 5)))
                _stars = "★" * _importance + "☆" * (5 - _importance)
                _pct = cnt / _c4_bm_total * 100
                # Color by importance
                if _importance >= 4:
                    _bm_color = "#00e676"
                    _bm_bg = "rgba(0,230,118,0.1)"
                elif _importance >= 3:
                    _bm_color = "#ffd740"
                    _bm_bg = "rgba(255,215,64,0.1)"
                elif _importance >= 2:
                    _bm_color = "#4fc3f7"
                    _bm_bg = "rgba(79,195,247,0.1)"
                else:
                    _bm_color = "#78909c"
                    _bm_bg = "rgba(120,144,156,0.08)"
                _bm4_html += f"""<div style="background:{_bm_bg};border:1px solid {_bm_color}30;
                    border-radius:8px;padding:8px 12px;min-width:160px;flex:1;max-width:220px;">
                    <div style="color:{_bm_color};font-size:12px;font-weight:600;margin-bottom:2px;">{bm}</div>
                    <div style="display:flex;align-items:center;justify-content:space-between;">
                        <span style="color:#ffd740;font-size:11px;letter-spacing:1px;">{_stars}</span>
                        <span style="color:#546e7a;font-size:10px;">{cnt} papers</span>
                    </div>
                    <div style="background:rgba(255,255,255,0.05);border-radius:2px;height:3px;margin-top:4px;">
                        <div style="background:{_bm_color};width:{min(100, _pct * 3)}%;height:100%;border-radius:2px;"></div>
                    </div>
                </div>"""
            _bm4_html += '</div>'
            st.markdown(_bm4_html, unsafe_allow_html=True)

        # ── 타겟 bar chart + MoA ──
        st.markdown("---")
        col_chart4, col_moa4 = st.columns(2)
        with col_chart4:
            st.markdown("#### Target Evidence Distribution")
            if c_tgt:
                c_tgt_df = pd.DataFrame(c_tgt[:10], columns=["Target", "Papers"])
                fig = px.bar(c_tgt_df, x="Papers", y="Target", orientation="h",
                            color="Papers", color_continuous_scale="YlOrRd")
                fig.update_layout(height=300, yaxis=dict(autorange="reversed"), margin=dict(t=5, b=5, l=5, r=5),
                                  showlegend=False, coloraxis_showscale=False)
                st.plotly_chart(_apply_dark(fig), use_container_width=True)
        with col_moa4:
            st.markdown("#### MoA Summary (from Literature)")
            if "기전(MoA)" in c_papers.columns:
                _moa_shown = 0
                for _, row in c_papers.sort_values("관련도", ascending=False).iterrows():
                    moa = row.get("기전(MoA)", "")
                    if moa and str(moa) != "nan" and len(str(moa)) > 10:
                        rel = int(row.get("관련도", 0))
                        st.markdown(f"""<div style="background:rgba(13,27,62,0.4);border-radius:6px;padding:6px 10px;margin:3px 0;
                            border-left:3px solid {'#00e676' if rel>=4 else '#ffd740'};">
                            <div style="color:#b0bec5;font-size:11px;line-height:1.4;">{str(moa)[:150]}</div>
                            <div style="color:#546e7a;font-size:9px;">Relevance: {'★' * rel}{'☆' * (5-rel)}</div>
                        </div>""", unsafe_allow_html=True)
                        _moa_shown += 1
                        if _moa_shown >= 5:
                            break

# ============================================================
# 탭 5: CPI Binding Visualization (3D 단백질-화합물 결합)
# ============================================================
with tab5:
    import streamlit.components.v1 as components
    import requests as _req

    st.markdown("### Compound-Protein Interaction (CPI) Binding Visualization")
    st.caption("3Dmol.js & RCSB PDB / UniProt / PubChem 3D API integration")

    # --- 주요 화합물과 결합 타겟 매핑 (binding_sites + indication + moa_short) ---
    COMPOUND_TARGET_MAP = {
        "Bimagrumab": {"targets": ["ActRIIB"], "type": "Biologic",
            "moa": "ActRII 길항 항체 - Myostatin/Activin 신호 차단",
            "moa_short": "ActRII antagonist",
            "indication": "Sarcopenia, Obesity, T2DM",
            "phase": "Phase 2/3",
            "pubchem_3d": None,
            "binding_sites": {"ActRIIB": "E28,Y31,K56"}},
        "Testosterone": {"targets": ["Androgen Receptor"], "type": "Small molecule",
            "moa": "AR 작용제 - 근단백 합성 촉진",
            "moa_short": "AR agonist",
            "indication": "Hypogonadism, Sarcopenia, Cachexia",
            "phase": "Approved",
            "pubchem_3d": "58-22-0", "smiles": "CC12CCC3C(C1CCC2O)CCC4=CC(=O)CCC34C",
            "binding_sites": {"Androgen Receptor": "L704,N705,T877"}},
        "Enobosarm": {"targets": ["Androgen Receptor"], "type": "Small molecule",
            "moa": "Selective AR Modulator (SARM) - 근육 선택적 동화작용",
            "moa_short": "SARM (selective AR modulator)",
            "indication": "Cancer cachexia, Sarcopenia, Stress urinary incontinence",
            "phase": "Phase 3",
            "pubchem_3d": "11326715", "smiles": "CC(O)C1=CC(=CC(=C1)C#N)OC2=CC(=C(C=C2)C#N)F",
            "binding_sites": {"Androgen Receptor": "R752,F764,M780"}},
        "Metformin": {"targets": ["AMPK/PGC-1alpha"], "type": "Small molecule",
            "moa": "AMPK 활성화 - 에너지 대사/미토콘드리아 기능 개선",
            "moa_short": "AMPK activator",
            "indication": "T2DM, Aging (TAME trial), Sarcopenic obesity",
            "phase": "Approved (T2DM) / Phase 3 (Aging)",
            "pubchem_3d": "4091", "smiles": "CN(C)C(=N)NC(=N)N",
            "binding_sites": {"AMPK/PGC-1alpha": "R83,D88,T106"}},
        "Rapamycin": {"targets": ["mTOR/PI3K/Akt"], "type": "Small molecule",
            "moa": "mTORC1 선택적 억제 - 자가포식 촉진/단백합성 조절",
            "moa_short": "mTORC1 inhibitor",
            "indication": "Transplant rejection, Aging, LAM",
            "phase": "Approved (Transplant) / Phase 2 (Aging)",
            "pubchem_3d": "5284616",
            "binding_sites": {"mTOR/PI3K/Akt": "L2185,Y2225,D2195"}},
        "Leucine": {"targets": ["mTOR/PI3K/Akt"], "type": "Natural product",
            "moa": "mTOR 직접 활성화 - 근단백 합성 촉진 (BCAA)",
            "moa_short": "mTOR activator (BCAA)",
            "indication": "Sarcopenia, Frailty, Post-surgical recovery",
            "phase": "Supplement / Phase 2",
            "pubchem_3d": "6106", "smiles": "CC(C)CC(N)C(=O)O",
            "binding_sites": {"mTOR/PI3K/Akt": "V2240,M2345"}},
        "GSK872": {"targets": ["RIPK1/RIPK3"], "type": "Small molecule",
            "moa": "RIPK3 키나아제 억제 - Necroptosis/염증 차단",
            "moa_short": "RIPK3 inhibitor",
            "indication": "IBD, Neurodegeneration, Muscle necroptosis",
            "phase": "Preclinical",
            "pubchem_3d": "71560588",
            "binding_sites": {"RIPK1/RIPK3": "L27,V35,A48,K50"}},
        "Tubastatin A": {"targets": ["HDAC6"], "type": "Small molecule",
            "moa": "HDAC6 선택적 억제 - 미세소관 안정화/자가포식 조절",
            "moa_short": "HDAC6 selective inhibitor",
            "indication": "CMT, Neurodegeneration, Muscle atrophy",
            "phase": "Preclinical",
            "pubchem_3d": "49850262",
            "binding_sites": {"HDAC6": "H573,H574,D612,H614"}},
        "HMB": {"targets": ["mTOR/PI3K/Akt", "MuRF1/MAFbx"], "type": "Natural product",
            "moa": "mTOR 활성화 + 유비퀴틴-프로테아좀 분해 억제",
            "moa_short": "mTOR activator + UPS inhibitor",
            "indication": "Sarcopenia, Cachexia, Exercise recovery",
            "phase": "Supplement / Phase 2",
            "pubchem_3d": "69362", "smiles": "CC(O)CC(=O)O",
            "binding_sites": {"mTOR/PI3K/Akt": "V2240", "MuRF1/MAFbx": "C23,H25"}},
        "Trevogrumab": {"targets": ["Myostatin/GDF-8"], "type": "Biologic",
            "moa": "항-Myostatin 항체 - Myostatin 직접 중화",
            "moa_short": "Anti-myostatin Ab",
            "indication": "Sarcopenia, Muscular dystrophy",
            "phase": "Phase 2 (discontinued)",
            "pubchem_3d": None,
            "binding_sites": {"Myostatin/GDF-8": "W28,W30,Y33"}},
        "Garetosmab": {"targets": ["ActRIIB"], "type": "Biologic",
            "moa": "항-Activin A 항체 - Activin 신호 차단",
            "moa_short": "Anti-activin A Ab",
            "indication": "FOP, Sarcopenia, Muscle wasting",
            "phase": "Phase 2",
            "pubchem_3d": None,
            "binding_sites": {"ActRIIB": "E63,K74,P83,F101"}},
    }

    # ── AI 논문 분석 기반 화합물 지식 DB (3,894편 논문에서 추출) ──
    COMPOUND_KNOWLEDGE = {
        "Vitamin D": {"moa_short": "VDR agonist / Anti-oxidative",
            "indication": "Age-related sarcopenia, Osteo-sarcopenia",
            "phase": "Supplement/RCT", "type": "Supplement",
            "pathway": "PI3K/Akt/mTOR, NF-kB, Oxidative stress"},
        "Testosterone": {"moa_short": "AR agonist / Anabolic",
            "indication": "Hypogonadal sarcopenia, Cachexia",
            "phase": "Approved", "type": "Hormone",
            "pathway": "AR signaling, IGF-1/PI3K/Akt/mTOR"},
        "Leucine": {"moa_short": "mTORC1 activator (BCAA)",
            "indication": "Age-related sarcopenia, Disuse atrophy",
            "phase": "Supplement/RCT", "type": "Amino acid",
            "pathway": "mTORC1, Muscle protein synthesis"},
        "Dexamethasone": {"moa_short": "GR agonist (atrophy model)",
            "indication": "Drug-induced sarcopenia (model compound)",
            "phase": "Approved (anti-inflammatory)", "type": "Steroid",
            "pathway": "FoxO3/Atrogin-1/MuRF1, UPS activation"},
        "HMB": {"moa_short": "mTOR activator + UPS inhibitor",
            "indication": "Age-related sarcopenia, Cachexia",
            "phase": "Supplement/Phase 2", "type": "Metabolite",
            "pathway": "mTOR, Ubiquitin-proteasome inhibition"},
        "Growth hormone": {"moa_short": "GH/IGF-1 axis activator",
            "indication": "Age-related sarcopenia, GH deficiency",
            "phase": "Approved/Phase 2", "type": "Biologic",
            "pathway": "GH/IGF-1 axis, Satellite cell activation"},
        "Creatine": {"moa_short": "ATP resynthesis enhancer",
            "indication": "Age-related sarcopenia, Exercise performance",
            "phase": "Supplement/RCT", "type": "Supplement",
            "pathway": "Phosphocreatine/ATP, Anti-oxidative"},
        "Metformin": {"moa_short": "AMPK activator",
            "indication": "Diabetic sarcopenia, Sarcopenic obesity",
            "phase": "Approved/Phase 3", "type": "Small molecule",
            "pathway": "AMPK/PGC-1a, Insulin sensitization"},
        "Whey protein": {"moa_short": "Protein synthesis stimulator",
            "indication": "Age-related sarcopenia, Post-stroke",
            "phase": "Supplement/RCT", "type": "Nutritional",
            "pathway": "mTOR, Muscle protein synthesis"},
        "Omega-3 fatty acids": {"moa_short": "Anti-inflammatory (EPA/DHA)",
            "indication": "Cancer cachexia, Inflammatory sarcopenia",
            "phase": "Supplement/RCT", "type": "Nutritional",
            "pathway": "NF-kB inhibition, EPA/DHA anti-inflammation"},
        "Resveratrol": {"moa_short": "SIRT1/PGC-1a activator",
            "indication": "Age-related sarcopenia, Mitochondrial dysfunction",
            "phase": "Preclinical/Phase 1", "type": "Natural product",
            "pathway": "SIRT1/PGC-1a, Mitochondrial biogenesis"},
        "Calcium": {"moa_short": "Mineral cofactor / Muscle contraction",
            "indication": "Osteo-sarcopenia, Age-related",
            "phase": "Supplement", "type": "Mineral",
            "pathway": "Ca2+ signaling, Muscle contraction"},
        "Probiotics": {"moa_short": "Gut-muscle axis modulator",
            "indication": "Age-related sarcopenia, Gut dysbiosis",
            "phase": "Supplement/RCT", "type": "Probiotic",
            "pathway": "Gut-muscle axis, SCFA, Inflammation reduction"},
        "Insulin": {"moa_short": "Insulin receptor agonist",
            "indication": "Diabetic sarcopenia, Insulin resistance",
            "phase": "Approved", "type": "Biologic",
            "pathway": "PI3K/Akt/mTOR, Glucose uptake"},
        "Branched-chain amino acids": {"moa_short": "mTORC1 activator (BCAA)",
            "indication": "Age-related sarcopenia, Liver cirrhosis",
            "phase": "Supplement/RCT", "type": "Amino acid",
            "pathway": "mTORC1, Ammonia detoxification"},
        "Selenium": {"moa_short": "Antioxidant cofactor (GPx)",
            "indication": "Age-related sarcopenia, Oxidative stress",
            "phase": "Supplement", "type": "Mineral",
            "pathway": "Glutathione peroxidase, ROS reduction"},
        "Zinc": {"moa_short": "Metalloenzyme cofactor / Antioxidant",
            "indication": "Age-related sarcopenia, Immune dysfunction",
            "phase": "Supplement", "type": "Mineral",
            "pathway": "Antioxidant defense, Protein synthesis"},
        "Vitamin E": {"moa_short": "Lipid-soluble antioxidant",
            "indication": "Age-related sarcopenia, Oxidative stress",
            "phase": "Supplement", "type": "Vitamin",
            "pathway": "Lipid peroxidation inhibition, NF-kB"},
        "Vitamin C": {"moa_short": "Antioxidant / Collagen synthesis",
            "indication": "Age-related sarcopenia, Oxidative stress",
            "phase": "Supplement", "type": "Vitamin",
            "pathway": "ROS scavenging, Collagen biosynthesis"},
        "Irisin": {"moa_short": "Myokine / Browning activator",
            "indication": "Sarcopenic obesity, Metabolic sarcopenia",
            "phase": "Preclinical", "type": "Myokine",
            "pathway": "PGC-1a/FNDC5, UCP1 browning"},
        "Cisplatin": {"moa_short": "DNA crosslinker (atrophy model)",
            "indication": "Chemo-induced cachexia (model)",
            "phase": "Approved (anticancer)", "type": "Small molecule",
            "pathway": "DNA damage, NF-kB, Muscle wasting"},
        "Essential amino acids": {"moa_short": "Protein synthesis stimulator",
            "indication": "Age-related sarcopenia, Post-surgical",
            "phase": "Supplement/RCT", "type": "Amino acid",
            "pathway": "mTORC1, Leucine-enriched EAA"},
        "Protein supplements": {"moa_short": "MPS stimulator",
            "indication": "Age-related sarcopenia, Malnutrition",
            "phase": "Supplement/RCT", "type": "Nutritional",
            "pathway": "mTOR, Muscle protein synthesis"},
        "Rapamycin": {"moa_short": "mTORC1 inhibitor",
            "indication": "Aging, Immunosuppression",
            "phase": "Approved/Phase 2", "type": "Small molecule",
            "pathway": "mTORC1, Autophagy induction"},
        "Magnesium": {"moa_short": "Enzyme cofactor / Anti-inflammatory",
            "indication": "Age-related sarcopenia, Muscle cramps",
            "phase": "Supplement", "type": "Mineral",
            "pathway": "ATP metabolism, NF-kB reduction"},
        "Enobosarm": {"moa_short": "SARM (selective AR modulator)",
            "indication": "Cancer cachexia, Sarcopenia",
            "phase": "Phase 3", "type": "Small molecule",
            "pathway": "Androgen receptor, Anabolic signaling"},
    }

    # 화합물별 고유 색상 팔레트 (밝고 구분 쉬운 8색)
    CPI_COLORS = ["#00e676","#ffd740","#ff4081","#40c4ff","#ea80fc","#ff6e40","#69f0ae","#448aff"]

    # --- 모드 선택 ---
    cpi_mode = st.radio("Analysis Mode", ["Compound -> Binding Targets", "Target Protein -> Binding Compounds"], horizontal=True)

    if cpi_mode == "Compound -> Binding Targets":
        st.markdown("---")
        compound_list = list(COMPOUND_TARGET_MAP.keys())
        # 데이터에서 추가 화합물 수집
        extra_compounds = sorted(compound_index.keys(), key=lambda x: len(compound_index[x]), reverse=True)[:50]
        all_compounds = compound_list + [c for c in extra_compounds if c not in compound_list]

        sel_cmp = st.selectbox("Select Compound", all_compounds,
                               format_func=lambda x: f"{x} ({''.join(COMPOUND_TARGET_MAP[x]['targets']) if x in COMPOUND_TARGET_MAP else 'DB'})")

        if sel_cmp:
            cmp_info = COMPOUND_TARGET_MAP.get(sel_cmp, {})
            # DB 화합물이면 COMPOUND_KNOWLEDGE에서 정보 보강
            if not cmp_info and sel_cmp in COMPOUND_KNOWLEDGE:
                _ck = COMPOUND_KNOWLEDGE[sel_cmp]
                cmp_info = {"targets": [], "type": _ck.get("type", "DB"),
                            "moa": _ck.get("moa_short", ""), "moa_short": _ck.get("moa_short", ""),
                            "indication": _ck.get("indication", ""), "phase": _ck.get("phase", ""),
                            "smiles": "", "pubchem_3d": None}
            targets_for_cmp = cmp_info.get("targets", [])

            # 데이터베이스에서 타겟 보강
            if sel_cmp in compound_index:
                c_papers_cpi = df_ok.loc[df_ok.index.isin(compound_index[sel_cmp])]
                db_targets = get_top_items(c_papers_cpi, "타겟(Target)", 10, normalize_target)
                for t, cnt in db_targets:
                    if t not in targets_for_cmp and t in SARCOPENIA_TARGET_PDB:
                        targets_for_cmp.append(t)

            col_info, col_3d = st.columns([1, 2])

            with col_info:
                st.markdown(f"#### {sel_cmp}")
                if cmp_info:
                    st.markdown(f"**Type:** {cmp_info.get('type', 'Unknown')}")
                    st.markdown(f"**MoA:** {cmp_info.get('moa', cmp_info.get('moa_short', '-'))}")
                    if cmp_info.get("indication"):
                        st.markdown(f"**Indication:** {cmp_info['indication']}")
                    if cmp_info.get("phase"):
                        st.markdown(f"**Phase:** {cmp_info['phase']}")
                    if cmp_info.get("smiles"):
                        st.code(cmp_info["smiles"], language=None)
                    # PubChem 구조 이미지
                    struct_info = structures.get(sel_cmp, {})
                    if struct_info and struct_info.get("image_url"):
                        st.image(struct_info["image_url"], caption="2D Structure", width=220)
                    elif cmp_info.get("pubchem_3d"):
                        st.image(f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/CID/{cmp_info['pubchem_3d']}/PNG?image_size=250x250", caption="2D Structure (PubChem)", width=220)

                st.markdown("#### Binding Targets")
                for t in targets_for_cmp:
                    tinfo = SARCOPENIA_TARGET_PDB.get(t, {})
                    pdb_id = tinfo.get("pdb", "N/A")
                    st.markdown(f"- **{t}** (PDB: [{pdb_id}](https://www.rcsb.org/structure/{pdb_id}))")
                    if tinfo.get("desc"):
                        st.caption(f"  {tinfo['desc']}")

            with col_3d:
                st.markdown("#### 3D Binding Visualization")
                if targets_for_cmp:
                    sel_bind_target = st.selectbox("Select binding target to visualize", targets_for_cmp)
                    tgt_pdb_info = SARCOPENIA_TARGET_PDB.get(sel_bind_target, {})
                    pdb_id = tgt_pdb_info.get("pdb", "")
                    binding_res = tgt_pdb_info.get("binding_residues", "")

                    if pdb_id:
                        # SMILES/CID 정보 준비
                        _cmp_smiles = cmp_info.get("smiles", "")
                        _cmp_cid = cmp_info.get("pubchem_3d", "")
                        if not _cmp_smiles and sel_cmp in structures:
                            _cmp_smiles = structures[sel_cmp].get("SMILES", "")
                        if not _cmp_cid and sel_cmp in structures:
                            _cmp_cid = str(structures[sel_cmp].get("CID", ""))
                        _cmp_img_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/CID/{_cmp_cid}/PNG?image_size=300x300" if _cmp_cid else ""

                        # 3Dmol.js 기반 3D 시각화 + 화합물 오버레이
                        viewer_html = f"""
<!DOCTYPE html>
<html>
<head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.7.1/jquery.min.js"></script>
<script src="https://3Dmol.org/build/3Dmol-min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background: #0a0e27; overflow:hidden; font-family: 'Segoe UI', system-ui, sans-serif; }}
#viewport {{ width:100%; height:580px; position:relative; border-radius:12px;
    border: 1px solid rgba(30,136,229,0.3);
    box-shadow: 0 0 30px rgba(30,136,229,0.15);
}}
#info-overlay {{
    position:absolute; top:12px; left:12px; z-index:100;
    background: rgba(10,14,39,0.92); color:#4fc3f7;
    padding:10px 16px; border-radius:8px; font-size:12px;
    border: 1px solid rgba(30,136,229,0.3);
    backdrop-filter: blur(10px); max-width:320px;
}}
#info-overlay h4 {{ margin:0 0 4px 0; color:#90caf9; font-size:13px; }}
#info-overlay p {{ margin:2px 0; color:#7899b8; font-size:11px; }}

/* Compound card (bottom-right) */
#compound-card {{
    position:absolute; bottom:14px; right:14px; z-index:120;
    background: rgba(10,14,39,0.95); border:1px solid rgba(0,230,118,0.4);
    border-radius:10px; padding:10px; width:200px;
    backdrop-filter: blur(10px);
    transition: all 0.3s ease;
}}
#compound-card:hover {{
    width:360px; padding:14px;
    border-color: rgba(0,230,118,0.8);
    box-shadow: 0 0 24px rgba(0,230,118,0.3);
}}
#compound-card h5 {{
    margin:0 0 4px 0; color:#00e676; font-size:13px; font-weight:700;
}}
#compound-card .smiles {{
    color:#80cbc4; font-size:10px; font-family:monospace;
    word-break:break-all; line-height:1.3;
    max-height:28px; overflow:hidden;
    transition: max-height 0.3s ease;
}}
#compound-card:hover .smiles {{
    max-height:120px;
    font-size:12px;
    color:#b2dfdb;
}}
#compound-card .struct-img {{
    width:80px; height:80px; margin-top:6px;
    border-radius:6px; border:1px solid rgba(0,230,118,0.2);
    background:#0d1b3e; object-fit:contain;
    transition: all 0.35s cubic-bezier(0.4,0,0.2,1);
    cursor: zoom-in;
}}
#compound-card:hover .struct-img {{
    width:180px; height:180px;
    border-color: rgba(0,230,118,0.6);
    box-shadow: 0 0 16px rgba(0,230,118,0.25);
}}
#compound-card .type-badge {{
    display:inline-block; padding:2px 8px; border-radius:10px;
    font-size:9px; font-weight:600; margin-top:4px;
    background: rgba(0,230,118,0.15); color:#69f0ae;
}}
#compound-card .phase-badge {{
    display:inline-block; padding:2px 8px; border-radius:10px;
    font-size:9px; font-weight:600; margin-left:4px;
    background: rgba(76,175,80,0.2); color:#81c784;
}}
#compound-card .moa-text {{
    color:#b0bec5; font-size:10px; margin-top:5px;
    line-height:1.3; font-style:italic;
}}
#compound-card .indication-text {{
    color:#ffcc80; font-size:10px; margin-top:3px;
    line-height:1.3;
    max-height:0; overflow:hidden;
    transition: max-height 0.3s ease;
}}
#compound-card:hover .indication-text {{
    max-height:60px;
}}

#binding-label {{
    position:absolute; bottom:14px; left:50%; transform:translateX(-50%);
    z-index:100; background: rgba(233,69,96,0.9); color:white;
    padding:6px 18px; border-radius:20px; font-size:11px;
    font-weight:600; animation: pulse-glow 2s ease-in-out infinite;
}}
#loading {{
    position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);
    color:#4fc3f7; font-size:14px; z-index:50;
}}
@keyframes pulse-glow {{
    0%,100% {{ box-shadow: 0 0 8px rgba(233,69,96,0.4); }}
    50% {{ box-shadow: 0 0 24px rgba(233,69,96,0.8); }}
}}
@keyframes spin {{ to {{ transform: rotate(360deg); }} }}
.spinner {{ display:inline-block; width:20px; height:20px; border:2px solid #4fc3f7;
    border-top-color:transparent; border-radius:50%; animation: spin 1s linear infinite;
    vertical-align:middle; margin-right:8px; }}
</style>
</head>
<body>
<div id="viewport">
    <div id="info-overlay">
        <h4>{sel_cmp} + {sel_bind_target}</h4>
        <p>PDB: {pdb_id} | UniProt: {tgt_pdb_info.get('uniprot', '')}</p>
        <p>Binding Site: {binding_res[:50]}</p>
    </div>
    <div id="loading"><span class="spinner"></span>Loading PDB structure...</div>
    <div id="binding-label" style="display:none;">Binding Animation Active</div>
    <div id="compound-card">
        <h5>{sel_cmp}</h5>
        <span class="type-badge">{cmp_info.get('type', 'Unknown')}</span>
        <span class="phase-badge">{cmp_info.get('phase', '')}</span>
        <div class="moa-text">{cmp_info.get('moa_short', cmp_info.get('moa', '')[:40])}</div>
        <div class="indication-text">{cmp_info.get('indication', '')}</div>
        <div class="smiles">{_cmp_smiles if _cmp_smiles else 'N/A (Biologic)'}</div>
        {"<img class='struct-img' src='" + _cmp_img_url + "' alt='2D Structure' onerror='this.style.display=&quot;none&quot;'/>" if _cmp_img_url else ""}
    </div>
</div>
<script>
(function() {{
    var element = document.getElementById("viewport");
    var viewer = $3Dmol.createViewer(element, {{
        backgroundColor: 0x0a0e27,
        antialias: true
    }});

    fetch("https://files.rcsb.org/download/{pdb_id}.pdb")
        .then(function(response) {{
            if (!response.ok) throw new Error("HTTP " + response.status);
            return response.text();
        }})
        .then(function(data) {{
            document.getElementById("loading").style.display = "none";
            document.getElementById("binding-label").style.display = "block";

            viewer.addModel(data, "pdb");

            // Protein: cartoon
            viewer.setStyle({{}}, {{
                cartoon: {{ color: "spectrum", opacity: 0.8, thickness: 0.28 }}
            }});

            // Binding residues: bright green stick + sphere (compound highlight)
            var bindingResidues = "{binding_res}".split(",");
            for (var i = 0; i < bindingResidues.length; i++) {{
                var resName = bindingResidues[i].trim();
                var resNum = parseInt(resName.replace(/[A-Za-z]/g, ""));
                if (!isNaN(resNum)) {{
                    viewer.setStyle({{resi: resNum}}, {{
                        stick: {{ color: "#00e676", radius: 0.2 }},
                        sphere: {{ color: "#00e676", radius: 0.35, opacity: 0.6 }},
                        cartoon: {{ color: "#00e676", opacity: 0.95, thickness: 0.45 }}
                    }});
                    viewer.addLabel(resName, {{
                        position: {{resi: resNum}},
                        backgroundColor: "rgba(0,230,118,0.8)",
                        fontColor: "#0a0e27",
                        fontSize: 10,
                        fontOpacity: 1,
                        borderThickness: 0.5
                    }});
                }}
            }}

            // Translucent surface for binding pocket
            var resNums = bindingResidues.map(function(r){{return parseInt(r.replace(/[A-Za-z]/g,""));}}).filter(function(n){{return !isNaN(n);}});
            if (resNums.length > 0) {{
                viewer.addSurface($3Dmol.SurfaceType.VDW, {{
                    opacity: 0.18, color: "#00e676"
                }}, {{resi: resNums}});
            }}

            viewer.zoomTo();
            viewer.render();

            // Rotation animation
            function animate() {{
                viewer.rotate(0.25, "y");
                viewer.render();
                requestAnimationFrame(animate);
            }}
            animate();
        }})
        .catch(function(err) {{
            document.getElementById("loading").innerHTML =
                '<span style="color:#e94560;">PDB {pdb_id} load failed: ' + err.message + '</span>';
        }});
}})();
</script>
</body>
</html>
"""
                        components.html(viewer_html, height=620, scrolling=False)

                        # 결합 정보 상세
                        st.markdown("#### Binding Details")
                        bd_col1, bd_col2 = st.columns(2)
                        with bd_col1:
                            st.markdown(f"**Binding Site Residues:**")
                            st.code(binding_res, language=None)
                            st.markdown(f"**PDB Structure:** [{pdb_id}](https://www.rcsb.org/structure/{pdb_id})")
                            st.markdown(f"**UniProt:** [{tgt_pdb_info.get('uniprot', '')}](https://www.uniprot.org/uniprot/{tgt_pdb_info.get('uniprot', '')})")
                        with bd_col2:
                            st.markdown("**Binding Mechanism:**")
                            st.info(cmp_info.get("moa", tgt_pdb_info.get("desc", "N/A")))
                            # AlphaFold 링크
                            af_uniprot = tgt_pdb_info.get("uniprot", "")
                            if af_uniprot:
                                st.markdown(f"**AlphaFold:** [View predicted structure](https://alphafold.ebi.ac.uk/entry/{af_uniprot})")
                    else:
                        st.warning("No PDB structure available for this target.")
                else:
                    st.info("No known binding targets for this compound. Select a curated compound for 3D visualization.")

    else:  # Target Protein -> Binding Compounds
        st.markdown("---")
        target_list = list(SARCOPENIA_TARGET_PDB.keys())
        sel_tgt = st.selectbox("Select Target Protein", target_list,
                               format_func=lambda x: f"{x} (PDB: {SARCOPENIA_TARGET_PDB[x]['pdb']})")

        if sel_tgt:
            tgt_info = SARCOPENIA_TARGET_PDB[sel_tgt]
            pdb_id = tgt_info["pdb"]
            binding_res = tgt_info.get("binding_residues", "")

            # 이 타겟에 결합하는 화합물 찾기
            binding_compounds = []
            for cmp_name, cmp_data in COMPOUND_TARGET_MAP.items():
                if sel_tgt in cmp_data.get("targets", []):
                    binding_compounds.append({"name": cmp_name, **cmp_data})
            # 데이터베이스에서 추가 화합물
            if sel_tgt in target_index:
                t_papers_cpi = df_ok.loc[df_ok.index.isin(target_index[sel_tgt])]
                db_compounds = get_top_items(t_papers_cpi, "화합물(Compound)", 15)
                for c, cnt in db_compounds:
                    if c not in [bc["name"] for bc in binding_compounds]:
                        _ck = COMPOUND_KNOWLEDGE.get(c, {})
                        binding_compounds.append({
                            "name": c,
                            "type": _ck.get("type", "DB"),
                            "moa": _ck.get("moa_short", ""),
                            "moa_short": _ck.get("moa_short", ""),
                            "indication": _ck.get("indication", ""),
                            "phase": _ck.get("phase", ""),
                            "targets": [sel_tgt],
                            "pubchem_3d": None
                        })

            col_3d, col_compounds = st.columns([2, 1])

            with col_3d:
                st.markdown(f"#### {sel_tgt} 3D Structure")
                st.caption(tgt_info["desc"])

                # Build per-compound color/residue data for JS
                _bc_colors = ["#00e676","#ffd740","#ff4081","#40c4ff","#ea80fc","#ff6e40","#69f0ae","#448aff"]
                _bc_cards_html = ""
                _js_compound_data = []  # [{name, color, residues: "R33,E39,..."}]
                for _bi, _bc in enumerate(binding_compounds[:8]):
                    _bc_color = _bc_colors[_bi % len(_bc_colors)]
                    _bc_smiles = _bc.get("smiles", "")
                    if not _bc_smiles and _bc["name"] in structures:
                        _bc_smiles = structures[_bc["name"]].get("SMILES", "")
                    _bc_cid = _bc.get("pubchem_3d", "")
                    if not _bc_cid and _bc["name"] in structures:
                        _bc_cid = str(structures[_bc["name"]].get("CID", ""))
                    _bc_img = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/CID/{_bc_cid}/PNG?image_size=300x300" if _bc_cid else ""
                    # Get compound-specific binding residues for this target
                    _bc_res = _bc.get("binding_sites", {}).get(sel_tgt, "")
                    if not _bc_res:
                        # DB compounds: assign from target's general binding residues
                        _all_res = tgt_info.get("binding_residues", "").split(",")
                        _per = max(1, len(_all_res) // max(len(binding_compounds), 1))
                        _start = _bi * _per
                        _bc_res = ",".join(_all_res[_start:_start+_per]) if _start < len(_all_res) else _all_res[-1] if _all_res else ""
                    _js_compound_data.append({"name": _bc["name"], "color": _bc_color, "residues": _bc_res})
                    # MoA / Indication / Phase
                    _bc_moa_short = _bc.get("moa_short", _bc.get("moa", "")[:40])
                    _bc_indication = _bc.get("indication", "")
                    _bc_phase = _bc.get("phase", "")
                    # Card HTML: Indication directly visible, MoA as hover tooltip
                    _tooltip_text = _bc_moa_short if _bc_moa_short else ""
                    _bc_cards_html += f"""
                    <div class="cmp-card" style="border-color:{_bc_color};" {"data-tooltip='" + _tooltip_text.replace("'", "&apos;") + "'" if _tooltip_text else ""}>
                        <div style="display:flex;align-items:center;gap:6px;">
                            <span style="width:10px;height:10px;border-radius:50%;background:{_bc_color};display:inline-block;flex-shrink:0;box-shadow:0 0 6px {_bc_color};"></span>
                            <div class="cmp-name" style="color:{_bc_color};">{_bc['name']}</div>
                        </div>
                        <span class="cmp-type">{_bc.get('type','')}</span>
                        {"<span class='cmp-phase'>" + _bc_phase + "</span>" if _bc_phase else ""}
                        {"<div class='cmp-indication'>" + _bc_indication + "</div>" if _bc_indication else ""}
                        <div class="cmp-smiles">{_bc_smiles if _bc_smiles else 'Biologic'}</div>
                        {"<img class='cmp-img' src='" + _bc_img + "' onerror='this.style.display=&quot;none&quot;'/>" if _bc_img else ""}
                    </div>"""

                # Build JS array string for compound data
                import json as _json
                _js_compounds_str = _json.dumps(_js_compound_data, ensure_ascii=False)

                # 3Dmol.js viewer + multi-color compound cards
                tgt_viewer_html = f"""
<!DOCTYPE html>
<html>
<head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.7.1/jquery.min.js"></script>
<script src="https://3Dmol.org/build/3Dmol-min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background: #0a0e27; overflow:hidden; font-family: 'Segoe UI', system-ui, sans-serif; }}
#viewport {{ width:100%; height:580px; position:relative; border-radius:12px;
    border: 1px solid rgba(30,136,229,0.3);
    box-shadow: 0 0 30px rgba(30,136,229,0.15);
}}
#info-overlay {{
    position:absolute; top:12px; left:12px; z-index:100;
    background: rgba(10,14,39,0.92); color:#4fc3f7;
    padding:10px 16px; border-radius:8px; font-size:12px;
    border: 1px solid rgba(30,136,229,0.3);
    backdrop-filter: blur(10px); max-width:300px;
}}
#info-overlay h4 {{ margin:0 0 4px 0; color:#90caf9; font-size:14px; }}
#info-overlay p {{ margin:2px 0; color:#7899b8; font-size:11px; }}
.legend-item {{ display:flex; align-items:center; gap:5px; margin:2px 0; }}
.legend-dot {{ width:8px; height:8px; border-radius:50%; flex-shrink:0; }}

#compounds-panel {{
    position:absolute; top:12px; right:12px; z-index:120;
    width:180px; max-height:560px; overflow-y:auto;
    display:flex; flex-direction:column; gap:6px;
}}
#compounds-panel::-webkit-scrollbar {{ width:4px; }}
#compounds-panel::-webkit-scrollbar-thumb {{ background:#1E88E5; border-radius:2px; }}

.cmp-card {{
    background: rgba(10,14,39,0.92); border:2px solid;
    border-radius:8px; padding:8px 10px;
    backdrop-filter: blur(10px);
    transition: all 0.3s ease; cursor:pointer;
}}
.cmp-card:hover {{
    width:340px; padding:12px;
    z-index:200; position:relative;
}}
.cmp-name {{ font-size:12px; font-weight:700; margin-bottom:2px; }}
.cmp-type {{
    display:inline-block; padding:1px 6px; border-radius:8px;
    font-size:8px; font-weight:600;
    background: rgba(255,255,255,0.08); color:#90a4ae;
}}
.cmp-indication {{
    color:#ffcc80; font-size:9px; margin-top:3px;
    line-height:1.3;
}}
.cmp-phase {{
    display:inline-block; padding:1px 6px; border-radius:8px;
    font-size:8px; font-weight:600; margin-left:4px;
    background: rgba(76,175,80,0.2); color:#81c784;
}}
/* MoA tooltip on hover */
.cmp-card {{
    position: relative;
}}
.cmp-card[data-tooltip]:hover::after {{
    content: attr(data-tooltip);
    position: absolute;
    left: -200px; top: 50%; transform: translateY(-50%);
    width: 180px; padding: 8px 12px;
    background: rgba(13,27,62,0.96);
    color: #80cbc4; font-size: 11px; line-height: 1.4;
    border: 1px solid rgba(79,195,247,0.4);
    border-radius: 8px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    backdrop-filter: blur(10px);
    z-index: 300; pointer-events: none;
    white-space: normal;
    font-style: italic;
}}
.cmp-card[data-tooltip]:hover::before {{
    content: '';
    position: absolute;
    left: -12px; top: 50%; transform: translateY(-50%);
    border: 6px solid transparent;
    border-left-color: rgba(79,195,247,0.4);
    z-index: 301; pointer-events: none;
}}
.cmp-smiles {{
    color:#80cbc4; font-size:9px; font-family:monospace;
    word-break:break-all; line-height:1.2;
    max-height:0; overflow:hidden;
    transition: max-height 0.3s ease, margin 0.3s ease;
    margin-top:0;
}}
.cmp-card:hover .cmp-smiles {{
    max-height:80px; margin-top:4px; font-size:11px;
}}
.cmp-img {{
    width:0; height:0; margin-top:0;
    border-radius:6px; border:1px solid rgba(255,255,255,0.1);
    background:#0d1b3e; object-fit:contain;
    transition: all 0.35s cubic-bezier(0.4,0,0.2,1);
    display:block;
}}
.cmp-card:hover .cmp-img {{
    width:160px; height:160px; margin-top:6px;
}}

#loading {{
    position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);
    color:#4fc3f7; font-size:14px; z-index:50;
}}
@keyframes spin {{ to {{ transform: rotate(360deg); }} }}
.spinner {{ display:inline-block; width:20px; height:20px; border:2px solid #4fc3f7;
    border-top-color:transparent; border-radius:50%; animation: spin 1s linear infinite;
    vertical-align:middle; margin-right:8px; }}
</style>
</head>
<body>
<div id="viewport">
    <div id="info-overlay">
        <h4>{sel_tgt}</h4>
        <p>PDB: {pdb_id} | UniProt: {tgt_info.get('uniprot', '')}</p>
        <p>{len(binding_compounds)} binding compounds (color-coded)</p>
        <div id="legend" style="margin-top:6px;"></div>
    </div>
    <div id="loading"><span class="spinner"></span>Loading PDB structure...</div>
    <div id="compounds-panel">{_bc_cards_html}</div>
</div>
<script>
(function() {{
    var compounds = {_js_compounds_str};
    var element = document.getElementById("viewport");
    var viewer = $3Dmol.createViewer(element, {{
        backgroundColor: 0x0a0e27, antialias: true
    }});

    // Build legend
    var legendDiv = document.getElementById("legend");
    compounds.forEach(function(c) {{
        var item = document.createElement("div");
        item.className = "legend-item";
        item.innerHTML = '<span class="legend-dot" style="background:'+c.color+';box-shadow:0 0 4px '+c.color+';"></span>'
            + '<span style="color:'+c.color+';font-size:10px;font-weight:600;">'+c.name+'</span>';
        legendDiv.appendChild(item);
    }});

    fetch("https://files.rcsb.org/download/{pdb_id}.pdb")
        .then(function(r) {{ if (!r.ok) throw new Error("HTTP "+r.status); return r.text(); }})
        .then(function(data) {{
            document.getElementById("loading").style.display = "none";
            viewer.addModel(data, "pdb");

            // Base protein: blue cartoon
            viewer.setStyle({{}}, {{
                cartoon: {{ color: "#1565c0", opacity: 0.6, thickness: 0.22 }}
            }});

            // Each compound gets its own color on its binding residues
            compounds.forEach(function(cmp) {{
                if (!cmp.residues) return;
                var residues = cmp.residues.split(",");
                residues.forEach(function(resStr) {{
                    var resNum = parseInt(resStr.trim().replace(/[A-Za-z]/g, ""));
                    if (isNaN(resNum)) return;
                    viewer.setStyle({{resi: resNum}}, {{
                        stick: {{ color: cmp.color, radius: 0.22 }},
                        sphere: {{ color: cmp.color, radius: 0.4, opacity: 0.7 }},
                        cartoon: {{ color: cmp.color, opacity: 0.95, thickness: 0.5 }}
                    }});
                    viewer.addLabel(cmp.name + " " + resStr.trim(), {{
                        position: {{resi: resNum}},
                        backgroundColor: cmp.color,
                        fontColor: "#0a0e27",
                        fontSize: 9,
                        fontOpacity: 1
                    }});
                }});
            }});

            viewer.zoomTo();
            viewer.render();

            function animate() {{
                viewer.rotate(0.2, "y");
                viewer.render();
                requestAnimationFrame(animate);
            }}
            animate();
        }})
        .catch(function(err) {{
            document.getElementById("loading").innerHTML =
                '<span style="color:#e94560;">PDB {pdb_id} load failed: '+err.message+'</span>';
        }});
}})();
</script>
</body>
</html>
"""
                components.html(tgt_viewer_html, height=620, scrolling=False)

                # External links
                link_col1, link_col2, link_col3 = st.columns(3)
                link_col1.markdown(f"[RCSB PDB](https://www.rcsb.org/structure/{pdb_id})")
                link_col2.markdown(f"[UniProt](https://www.uniprot.org/uniprot/{tgt_info.get('uniprot', '')})")
                link_col3.markdown(f"[AlphaFold](https://alphafold.ebi.ac.uk/entry/{tgt_info.get('uniprot', '')})")

            with col_compounds:
                st.markdown("#### Binding Compounds")
                for bc in binding_compounds:
                    with st.expander(f"{bc['name']} ({bc.get('type', 'Unknown')})"):
                        st.markdown(f"**MoA:** {bc.get('moa', '-')}")
                        if bc.get("smiles"):
                            st.code(bc["smiles"], language=None)
                        # Show 2D structure from PubChem
                        if bc.get("pubchem_3d"):
                            st.image(f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/CID/{bc['pubchem_3d']}/PNG?image_size=200x200",
                                     caption="2D Structure", width=180)
                        elif bc["name"] in structures:
                            s = structures[bc["name"]]
                            if s.get("image_url"):
                                st.image(s["image_url"], caption="2D Structure", width=180)

                if not binding_compounds:
                    st.info("No known compounds for this target in the database.")

    # CPI Model Info
    st.markdown("---")
    st.markdown("#### CPI Foundation Model Architecture")
    st.markdown("""
    <div style='background:rgba(13,20,50,0.6); padding:20px; border-radius:10px;
         border:1px solid rgba(30,136,229,0.2);'>
        <table style='width:100%; color:#c0cde0; font-size:13px;'>
        <tr><td style='padding:6px; color:#4fc3f7;'><b>Drug Encoder</b></td>
            <td>ChemBERTa-77M (SMILES -> 768-dim embedding)</td></tr>
        <tr><td style='padding:6px; color:#4fc3f7;'><b>Protein Encoder</b></td>
            <td>ESM-2 650M (Sequence -> 1280-dim embedding)</td></tr>
        <tr><td style='padding:6px; color:#4fc3f7;'><b>Fusion Module</b></td>
            <td>Cross-Attention (8 heads, 6 layers, 512-dim)</td></tr>
        <tr><td style='padding:6px; color:#4fc3f7;'><b>Prediction</b></td>
            <td>Binding Probability + Affinity (pKd) + Binding Site Attention</td></tr>
        <tr><td style='padding:6px; color:#4fc3f7;'><b>Training Data</b></td>
            <td>BindingDB + DAVIS + KIBA datasets</td></tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# 탭 6: Target-Compound 매트릭스
# ============================================================
with tab6:
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
    st.plotly_chart(_apply_dark(fig), use_container_width=True)

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
with tab7:
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
with tab8:
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
with tab9:
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
with tab10:
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
                st.plotly_chart(_apply_dark(fig), use_container_width=True)

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
with tab11:
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
                st.plotly_chart(_apply_dark(fig), use_container_width=True)
    else:
        st.info("No collection log found. Showing basic statistics.")
        st.metric("총 문헌 수", len(df_ok))

# ============================================================
# 탭 11: Control Center
# ============================================================
with tab12:
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
