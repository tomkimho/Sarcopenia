# bassarcopenia.com - Google Cloud Run 배포 가이드

## 1단계: 도메인 구매
- Namecheap (https://namecheap.com) 또는 가비아 (https://gabia.com) 에서
  `bassarcopenia.com` 구매 (연 ~$10-15)

## 2단계: Google Cloud 프로젝트 설정

### 2-1. GCP 계정 & 프로젝트 생성
```bash
# Google Cloud SDK 설치 (https://cloud.google.com/sdk/docs/install)
# 설치 후:
gcloud auth login
gcloud projects create bassarcopenia --name="BasSarcopenia"
gcloud config set project bassarcopenia
```

### 2-2. 결제 활성화
- https://console.cloud.google.com/billing 에서 결제 계정 연결
- Cloud Run free tier: 매월 2백만 요청 무료, 360,000 GB-초 무료

### 2-3. 필요한 API 활성화
```bash
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

## 3단계: Docker 이미지 빌드 & 배포

### 3-1. 프로젝트 폴더에서 실행
```bash
cd C:\Users\kimho\sarcopenia\data\sarcopenia_dcp

# Cloud Build로 직접 빌드 & 배포 (Docker Desktop 불필요!)
gcloud run deploy bassarcopenia \
  --source . \
  --region asia-northeast3 \
  --platform managed \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 3 \
  --port 8080
```

### 3-2. 배포 확인
```bash
# 배포된 URL 확인 (예: https://bassarcopenia-xxxxx-du.a.run.app)
gcloud run services describe bassarcopenia --region asia-northeast3 --format="value(status.url)"
```

## 4단계: 커스텀 도메인 연결

### 4-1. 도메인 소유권 확인
```bash
gcloud domains verify bassarcopenia.com
```
- Google Search Console에서 DNS TXT 레코드 추가하라고 안내됨
- 도메인 등록 업체 DNS 설정에서 TXT 레코드 추가

### 4-2. Cloud Run에 도메인 매핑
```bash
gcloud beta run domain-mappings create \
  --service bassarcopenia \
  --domain bassarcopenia.com \
  --region asia-northeast3
```

### 4-3. DNS 레코드 설정
Cloud Run이 알려주는 IP 주소를 도메인 DNS에 추가:

| Type | Name | Value |
|------|------|-------|
| A    | @    | (Cloud Run이 알려주는 IP) |
| AAAA | @    | (Cloud Run이 알려주는 IPv6) |
| CNAME| www  | bassarcopenia.com |

### 4-4. SSL 인증서 (자동)
- Cloud Run이 Let's Encrypt SSL 인증서를 자동 발급
- DNS 전파 후 10-20분 내 HTTPS 활성화

## 5단계: 업데이트 배포 (이후)

코드 수정 후 재배포:
```bash
cd C:\Users\kimho\sarcopenia\data\sarcopenia_dcp
gcloud run deploy bassarcopenia --source . --region asia-northeast3
```

## 예상 비용

| 항목 | 비용 |
|------|------|
| 도메인 (연간) | ~$10-15 |
| Cloud Run (트래픽 적음) | $0-5/월 (free tier 범위 내) |
| Cloud Build | 매일 120분 무료 |
| **합계** | **~$1-6/월** |

## 트러블슈팅

### 빌드 실패 시
```bash
# 로그 확인
gcloud builds list --limit=5
gcloud builds log <BUILD_ID>
```

### 메모리 부족 시
```bash
gcloud run services update bassarcopenia --memory 2Gi --region asia-northeast3
```

### 환경변수 설정 (Anthropic API 키 등)
```bash
gcloud run services update bassarcopenia \
  --set-env-vars ANTHROPIC_API_KEY=your-key-here \
  --region asia-northeast3
```
