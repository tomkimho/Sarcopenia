# Sarcopenia Foundation Model 구축전략

**Date:** 2026-03-09
**Version:** 1.0
**Project:** SARC_DCP_FM_1 — 근감소증 신약개발 파운데이션 모델

---

## 1. 프로젝트 개요

### 1.1 목표
3,894건 근감소증 논문/특허 문헌 데이터베이스 기반으로 **Novel Target 및 Biomarker 발굴**을 위한 Foundation Model 2종 구축:

1. **Sarcopenia Target Discovery FM**: 문헌 지식그래프 + 멀티오믹스 인과관계 → Novel Target 자동 발굴
2. **Sarcopenia Generative Chem FM**: 발굴 타겟 → De novo 신약 후보물질 설계

### 1.2 차별점 (AGA DCP FM 대비)
| 항목 | AGA_DCP_FM_1 | SARC_DCP_FM_1 |
|------|-------------|---------------|
| 문헌 규모 | 709건 | **3,894건** (5.5배) |
| 타겟 범위 | 5α-R, AR, Wnt 중심 | **22+ 경로** (Myostatin, mTOR, AMPK, Gut-muscle axis, Ferroptosis 등) |
| 질환 아형 | 단일 (AGA) | **7개** (노인성, 암 악액질, 약물유발, 근감소성 비만, 신경성, 폐용성, 당뇨성) |
| 바이오마커 | 탈모 특화 | **진단/예후/치료반응** 3원 체계 |
| 임상 실패 교훈 | 제한적 | **Myostatin 억제제 4종 실패** → 근육량≠기능 역설 내재화 |
| 핵심 혁신 | 국소 DDS | **기능 개선 예측 모델** (Physical Function Predictor) |

---

## 2. Foundation Model #1: Sarcopenia Target Discovery FM

### 2.1 아키텍처

```
입력층:
├── GWAS 데이터 (EWGSOP2/AWGS 2019 기반)
│   ├── Hand grip strength GWAS loci
│   ├── Walking pace GWAS loci
│   ├── ALM (Appendicular Lean Mass) GWAS loci
│   └── SARC-F 연관 loci
├── 오믹스 데이터
│   ├── eQTL: GTEx + eQTLGen (31,000명)
│   ├── pQTL: deCODE + UK Biobank
│   ├── Transcriptomics: C2C12, Human skeletal muscle
│   └── Metabolomics: SCFA, Iron, Lipid peroxidation
├── 문헌 지식그래프
│   ├── 3,894 PDF → ~15,000 nodes, ~80,000 edges
│   ├── Target-Compound-Pathway-Biomarker 관계
│   └── 치료분류 × 질환아형 매트릭스
└── 임상시험 데이터
    ├── Phase 2/3 성공/실패 사례 (Myostatin 억제제 등)
    └── ICFSR 평가변수 기준

    ↓

인코더층:
├── [Genomics Encoder] — GWAS Summary Statistics 임베딩
├── [Transcript Encoder] — Skeletal muscle 발현 프로파일
├── [Proteomics Encoder] — 혈장 단백체 (GDF-15, Irisin, CAF 등)
├── [Microbiome Encoder] — 장내 미생물 조성 (NEW)
└── [Literature Encoder] — 문헌 지식그래프 임베딩

    ↓

융합층:
├── [Cross-Modal Attention] — 멀티오믹스 인과성 학습
├── [MR Causality Module] — Mendelian Randomization 내재화
├── [Clinical Failure Learner] — 근육량↑≠기능↑ 역설 학습 (NEW)
└── [Function Predictor] — 신체기능 개선 예측 (SPPB, Grip, Gait) (NEW)

    ↓

출력층:
├── Ranked Novel Target 리스트 + 인과성 점수 (0-1)
├── Target Druggability Score (DEEPSCO 연동)
├── 예측: 근육량 효과 + **신체기능 효과** (분리 예측)
├── 바이오마커 패널 추천 (진단/예후/치료반응)
└── 근거 문헌 Citation + SHAP 설명
```

### 2.2 학습 데이터

| 데이터 소스 | 규모 | 용도 |
|------------|------|------|
| 3,894 논문/특허 | ~15,000 지식 노드 | Knowledge Graph |
| EWGSOP2/AWGS GWAS | Hand grip + Walk speed + ALM | 유전적 인과관계 |
| GTEx + eQTLGen | 31,000명 eQTL | 유전자 발현 조절 |
| UK Biobank pQTL | 혈장 단백체 | 단백질 수준 인과관계 |
| MiXeR 분석 | MetS-Sarcopenia 공유 유전변이 (44-85%) | 다면발현 |
| 9개 다면발현 유전자 | COBLL1, FRZB, PKD2 등 | Novel target 후보 |
| ClinicalTrials.gov | Myostatin 억제제 등 Phase 2/3 실패 | 실패 패턴 학습 |
| SAMP8/mdx 마우스 | 전임상 데이터 | 동물→인간 번역성 |

### 2.3 핵심 혁신: Physical Function Predictor

**문제:** 기존 Myostatin 억제제(Bimagrumab, Landogrozumab 등)는 근육량 증가에 성공했으나 **신체기능(SPPB, 보행속도) 개선에 실패**하여 임상 실패.

**해결:** Target Discovery FM에 **Physical Function Predictor** 모듈을 내장:

```
[Target Candidate] → [Muscle Mass Score] + [Physical Function Score]
                                              ↑
                                    mTORC1 vs AMPK 상충 효과 학습
                                    NMJ 안정화 기여도 평가
                                    미토콘드리아 기능 예측
```

- **Pass 기준:** Muscle Mass Score ≥ 0.6 **AND** Physical Function Score ≥ 0.5
- **Fail 패턴:** Muscle Mass ↑↑ but Function unchanged = mTORC1 과활성 → AMPK 억제 → 미토콘드리아↓

### 2.4 타겟 우선순위 매트릭스 (문헌 기반)

| Tier | Target | Druggability | 문헌 근거 | GWAS 지지 | 기능 개선 예측 |
|------|--------|-------------|----------|----------|--------------|
| T1 | Myostatin/GDF-8 | ⭐⭐⭐⭐⭐ | 다수 | Grip strength | ⚠️ 근육량만 ↑ |
| T1 | mTOR/PI3K/Akt | ⭐⭐⭐⭐⭐ | 다수 | ALM | ⚠️ AMPK 상충 |
| T1 | AMPK/PGC-1α | ⭐⭐⭐⭐ | 다수 | Walking pace | ✅ 미토콘드리아↑ |
| T2 | KLF13-Notch | ⭐⭐⭐ | JCSM 2024 | - | ✅ Clofoctol 재창출 |
| T2 | RIPK1/RIPK3 | ⭐⭐⭐ | JCSM 2023 | - | ✅ 섬유화↓ + 기능↑ |
| T2 | Ferroptosis (GPX4) | ⭐⭐⭐ | IJBS 2021 | - | ✅ 미토콘드리아 보호 |
| T2 | Gut-Muscle Axis | ⭐⭐⭐ | Nutrients 2019 | - | ✅ 염증↓ + SCFA↑ |
| T3 | ACLP | ⭐⭐⭐ | 국가연구개발 | - | ✅ rhACLP 1.5mg/kg |
| T3 | NMJ (CAF/Agrin) | ⭐⭐⭐ | IJMS 2025 | MUNIX | ✅ 탈신경 방지 |
| T3 | Exosome/miR-132-3p | ⭐⭐ | JOT 2024 | - | ✅ FoxO3 억제 |

---

## 3. Foundation Model #2: Sarcopenia Generative Chem FM

### 3.1 아키텍처

```
입력: Target (Myostatin, RIPK3, KLF13 등) + PDB 3D 구조
  ↓
[Stage 1] Target Validation
  - AlphaFold 구조 예측
  - Pocket Detection (Fpocket/P2Rank)
  - Druggability Assessment (DEEPSCO)
  ↓
[Stage 2] Molecule Generation
  - 3D Equivariant Diffusion Process
  - SE(3)-invariant noise → denoise
  - Fragment-based de novo design
  ↓
[Stage 3] Multi-Objective Filtering
  - ADMET Prediction (DEEPTD)
  - Binding Affinity (Docking)
  - SA Score (합성 용이성)
  - Sarcopenia-specific Safety Filter:
    • 경구 생체이용률 최적화 (노인 대상)
    • Drug-Drug Interaction 최소화 (다제복용)
    • 장기 사용 안전성 (만성 질환)
    • CYP450 억제 회피
    • Statin 상호작용 회피 (근감소증 유발 방지)
  ↓
[Stage 4] Function Prediction (NEW)
  - 근육량 증가 예측
  - **신체기능 개선 예측** (SPPB, Grip, 6MWD)
  - mTORC1/AMPK 균형 점수
  ↓
출력: Ranked Candidate Molecules + SMILES + SA Score + Function Score
```

### 3.2 Sarcopenia-Specific Design Rules

1. **경구 투여 최적화:** LogP 1-3, MW < 500, HBD ≤ 5 (Lipinski 엄격 적용)
2. **Polypharmacy 안전:** CYP3A4/2D6 억제 회피 (노인 다제복용)
3. **mTORC1-AMPK 균형:** 근육 동화 + 미토콘드리아 기능 동시 달성
4. **스타틴 병용 안전:** 근감소증 환자의 스타틴 복용 빈도 높음
5. **장기 안전성:** 6개월+ 투여 기준 독성 예측

---

## 4. 로드맵 (18개월)

| Phase | 기간 | 목표 | 산출물 |
|-------|------|------|--------|
| Phase 1 | M1-4 | 데이터 준비 + KG 구축 | 3,894건 KG, 15K nodes, 80K edges |
| Phase 2 | M3-10 | Target Discovery FM v1 | AUC > 0.85 (known target 재발견) |
| Phase 3 | M8-16 | Generative Chem FM | Top-10 후보 SMILES + SA Score |
| Phase 4 | M14-18 | 통합 + Wet-lab 검증 | Top-3 후보 in vitro 검증 |

### Phase 1 상세 (M1-4)
- PDF 3,894건 → 텍스트 추출 완료
- Claude AI 정보 추출 (타겟/화합물/기전/바이오마커)
- Knowledge Graph 구축 (NetworkX → Neo4j)
- PubChem 화합물 구조 수집
- 바이오마커 3원 분류 (진단/예후/치료반응)

### Phase 2 상세 (M3-10)
- GWAS Summary Statistics 수집 (Hand grip, Walk speed, ALM)
- eQTL/pQTL 인과관계 분석 (MR)
- Physical Function Predictor 학습
- Dark Target 발굴 알고리즘 고도화
- 임상 실패 사례 학습 (Myostatin 억제제 4종)

### Phase 3 상세 (M8-16)
- AlphaFold 기반 타겟 구조 예측
- 3D Diffusion 기반 분자 생성
- ADMET + Sarcopenia-specific 필터
- mTORC1-AMPK 균형 점수 모듈

### Phase 4 상세 (M14-18)
- Top-3 후보물질 합성
- C2C12 myotube 분화/위축 모델
- SAMP8 노화 마우스 in vivo
- DEX-유도 근위축 모델 검증

---

## 5. 비용 추정

| 항목 | 비용 | 비고 |
|------|------|------|
| Claude AI 정보 추출 (3,894건) | $120-300 | 1회 |
| 월간 업데이트 (APPEND) | $20-40/월 | PubMed 신규 |
| GPU 학습 (A100 40GB) | $5,000-10,000 | Phase 2-3 |
| AlphaFold 추론 | $500-1,000 | Phase 3 |
| Wet-lab 검증 | $50,000-100,000 | Phase 4 |
| **총 18개월** | **$70,000-150,000** | |

---

## 6. 기대 성과

1. **Novel Target 20+개 발굴** (Dark Target + MR 인과관계 검증)
2. **바이오마커 패널 3종** (진단/예후/치료반응)
3. **신약 후보 10+개** (SMILES + Druggability + Function Score)
4. **임상 실패 회피 모델** (Physical Function Predictor)
5. **First-in-Class 기회** (FDA/KFDA 승인 근감소증 치료제 없음)

---

## 참고자료

1. Chen LK, et al. Asian Working Group for Sarcopenia: 2019 Consensus Update. JAMDA 2020
2. Cruz-Jentoft AJ, et al. Sarcopenia: EWGSOP2. Age Ageing 2019
3. Ticinesi A, et al. Gut Microbiota, Muscle Mass and Function in Aging. Nutrients 2019
4. ICFSR Task Force. Drug Development Challenges for Sarcopenia. J Frailty Aging 2022
5. 한국바이오협회. 근감소증 치료제 국내외 개발 동향. Bio Economy Brief 2022
6. 대한정형외과학회지. 근감소증 원인 및 치료 종합 리뷰. 2025
7. Donini LM, et al. ESPEN/EASO Sarcopenic Obesity. Clin Nutr 2022

---

**— EoD —**
*Sarcopenia DCP FM_1 구축전략 v1.0 | BasGenBio R&D Division | 2026-03-09*
