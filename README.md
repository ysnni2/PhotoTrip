# PhotoTrip

**개인 사진으로 여행 취향을 분석하는 AI 시스템**

---

## Abstract

PhotoTrip은 사용자가 업로드한 일상 사진(5~7장)을 입력으로 받아, 컴퓨터 비전 파이프라인을 통해 여행 취향을 정량화하고 맞춤형 여행지를 추천하는 end-to-end AI 시스템이다. 여행 추천 시스템은 전통적으로 설문·클릭 로그·예약 이력 등 명시적 선호에 의존하지만, 실제 여행 취향은 일상 사진—카페, 식사, 공연, 풍경, 실내 공간 등—에 암묵적으로 내재되어 있다.

본 시스템은 (1) CLIP fine-tuning 기반 장면 분류, (2) OneFormer 멀티데이터셋 의미론적 분할, (3) OpenCV 기반 시각 특성 추출, (4) MLP 기반 스타일·라이프스타일 분석을 통합하여 **Preference Vector**를 구성하고, 이를 기반으로 여행지 랭킹 및 Gemini 기반 자연어 설명을 생성한다. 프론트엔드는 Three.js 기반 카테고리별 3D 씬과 가상 탑승권 UI를 제공하여, 분석 결과를 직관적인 여행 경험으로 시각화한다.

핵심 과제는 validation accuracy뿐 아니라 **예측 confidence의 calibration**이다. 낮은 confidence는 downstream preference vector 및 추천 품질 저하로 직결되며, 본 연구는 accuracy parity 조건 하에서 SigLIP(33~37%) 대비 CLIP(79~87%)의 calibration 우위를 실험적으로 검증하고 CLIP을 최종 채택하였다.

---

## System Overview

```mermaid
flowchart TD
    INPUT["사진 업로드 5~7장\n일상 사진 입력"]
    INPUT --> CLIP
    INPUT --> ONE
    INPUT --> OCV
    INPUT --> SMLP
    subgraph ANALYSIS["📊 Per-Image Analysis (병렬)"]
        CLIP["🔵 CLIP Fine-tuned\n장면 분류 · 93.48%"]
        ONE["🟢 OneFormer\n의미론적 분할 · 45.6% mIoU"]
        OCV["🟡 OpenCV\n색감 · 밝기 · 채도"]
        SMLP["🟣 Style MLP\n분위기 · 스타일 분석"]
    end
    CLIP --> PV
    ONE --> PV
    OCV --> PV
    SMLP --> PV
    subgraph VECTOR["Preference Vector Builder"]
        PV["scene · visual · semantic\nstyle · lifestyle 통합"]
        PV --> ENS["앙상블 (N장 평균)\ntop_category · confidence · is_uncertain"]
    end
    ENS --> REC
    ENS --> GEM
    subgraph OUTPUT["Output"]
        REC["📍추천 엔진\nTop-3 여행지 · 코사인 유사도"]
        GEM["💬 Gemini LLM\n취향 자연어 설명"]
        REC --> FE
        GEM --> FE
        FE["🌐Frontend\nThree.js 3D 씬 · CV Dashboard · 가상 탑승권"]
    end
    style ANALYSIS fill:#e6f1fb,stroke:#378add
    style VECTOR fill:#e1f5ee,stroke:#1d9e75
    style OUTPUT fill:#faeeda,stroke:#ba7517
```

**기술 스택**

| 계층 | 기술 |
|------|------|
| Backend | FastAPI, PyTorch, Hugging Face Transformers |
| 장면 분류 | CLIP ViT-B/32 (fine-tuned), `openai/clip-vit-base-patch32` |
| 의미론적 분할 | OneFormer, `shi-labs/oneformer_ade20k_swin_large` |
| 시각 분석 | OpenCV |
| 스타일·라이프스타일 | MLP head (BCE + class weights, Pseudo Labeling) |
| LLM | Google Gemini API |
| Frontend | HTML/CSS/JS, Three.js r160 (ES modules, CDN) |

---

## Key Contributions

1. **다중 이미지 앙상블 Preference Vector**  
   사진별 CLIP 분류, OneFormer 분할 비율, OpenCV 시각 메트릭, Style MLP 점수를 통합하고, 다중 업로드 시 평균 앙상블하여 robust한 취향 표현을 구축한다.

2. **Accuracy–Confidence 트레이드오프 분석 기반 모델 선택**  
   SigLIP 계열은 validation accuracy가 유사하나 실제 inference confidence가 33~37%에 머무는 반면, fine-tuned CLIP은 79~87% confidence를 달성한다. 본 프로젝트는 **accuracy parity 하에서 calibration 우위**를 근거로 CLIP을 최종 채택한다.

3. **Hybrid 추천 및 설명 파이프라인**  
   규칙 기반 destination scoring과 Gemini API 기반 자연어 설명·대화(Flying 챗봇)를 결합하여, 정량 분석과 정성적 해석을 동시에 제공한다.

4. **Three.js 기반 카테고리 3D 씬**  
   COLMAP + 3D Gaussian Splatting(3DGS) 실험 후 웹 호환성을 고려하여 procedural Three.js 씬으로 전환하였으며, 카테고리별 immersive visualization을 구현한다.

---

## 배경 및 관련 연구

### Semantic Segmentation 발전

| 연도 | 모델 | 주요 기여 |
|------|------|----------|
| 2015 | FCN | 최초 end-to-end 픽셀 단위 분류 |
| 2017 | DeepLab v3 | Atrous convolution, multi-scale context 도입 |
| 2022 | Mask2Former | Universal segmentation 시도; 단, 태스크마다 개별 학습 필요 |
| 2023 | OneFormer | Task-conditioned joint training으로 단일 학습만으로 멀티 태스크/데이터셋 통합 가능 |

### OneFormer 채택 배경

초기에는 Mask2Former를 고려하였으나, 카테고리별로 ADE20K, FoodSeg103, Cityscapes 등 서로 다른 도메인의 데이터셋을 통합 학습할 경우 Mask2Former는 태스크마다 개별 학습이 필요하여 학습 시간과 리소스 비용이 과도하게 증가한다. 반면 OneFormer는 task-conditioned joint training으로 단일 학습만으로 멀티 데이터셋 통합이 가능하여 채택하였다 (Jain et al., CVPR 2023).

### SigLIP vs CLIP 배경

CLIP(Radford et al., 2021)은 4억 쌍의 이미지-텍스트 대조 학습으로 강력한 zero-shot 전이 성능을 제공한다. SigLIP(Zhai et al., ICCV 2023)은 sigmoid loss 기반으로 CLIP 대비 학습 안정성을 개선하였으나, 본 연구에서는 실제 추론 confidence 관점에서 CLIP이 우위임을 확인하였다.

| 모델 | Val Accuracy | Inference Confidence |
|------|-------------|---------------------|
| SigLIP fine-tuned | 93.56% | 33~37% |
| **CLIP fine-tuned** | **93.48%** | **79~87%** |

Preference Vector는 분류 모델의 카테고리별 softmax 확률을 직접 사용한다. SigLIP의 낮은 confidence는 모든 카테고리 점수가 균등하게 분산되어 취향 신호가 희석되는 문제를 야기하므로, accuracy parity 조건 하에서 calibration이 우수한 CLIP을 채택하였다.

---

## 모델 학습 구조

```mermaid
flowchart TD
    subgraph CLIP["🔵 CLIP 장면 분류 학습"]
        A1[Pixabay 데이터 수집\n카테고리별 6클래스] --> A2[Pseudo Labeling\nSigLIP → CLIP 자동 라벨링]
        A2 --> A3[CLIP Fine-tuning\nopenai/clip-vit-base-patch32]
        A3 --> A4["Val Acc 93.48%\nConfidence 79~87%"]
    end
    subgraph ONE["🟢 OneFormer 분할 학습"]
        B1[ADE20K\nFoodSeg103\nCityscapes] --> B2[멀티데이터셋 통합 학습\ntask-conditioned joint training]
        B2 --> B3["mIoU 37.1% → 45.6%\n+8.5%p 향상"]
    end
    subgraph MLP["🟣 MLP 스타일 분류 학습"]
        C1[CLIP 임베딩\n768차원 입력] --> C2[MLP\n768→512→256→128→6]
        C2 --> C3["mood / place / style\n카테고리별 분류"]
    end
    CLIP ~~~ ONE ~~~ MLP
```

---

## Experiments & Results

### 1. 장면 분류 (Scene Classification)

6-class travel scene classification (beach, nature, city, culture, festival, food)에 대해 다음 모델을 비교하였다.

| 모델 | Val Accuracy | 비고 |
|------|-------------|------|
| CLIP Zero-shot | 64.27% | 프롬프트 기반, fine-tuning 없음 |
| SigLIP 기본 | 90.91% | `google/siglip-large-patch16-256` |
| SigLIP + large 데이터 | 90.52% | 데이터 규모 확대 시 소폭 하락 |
| SigLIP + festival 카테고리 | 93.56% | festival 클래스 추가 |
| SigLIP + Pseudo Labeling | 93.14% | pseudo label 기반 semi-supervised |
| **CLIP Fine-tuned (최종 채택)** | **93.48%** | `openai/clip-vit-base-patch32` ✅ |

**CLIP 선택 근거**

SigLIP 계열은 validation accuracy 측면에서 CLIP fine-tuned와 유사한 수준(93%대)을 기록하였으나, **실제 inference 시 예측 confidence가 33~37%에 불과**하였다. 반면 fine-tuned CLIP은 **79~87% confidence**를 일관되게 산출하였다. scene confidence는 preference vector의 `confidence` 필드 및 `is_uncertain` 플래그에 직접 반영되며, downstream recommender의 destination scoring에 영향을 미친다.

전체 실험 이력:

![](results/full_experiment_history.png)

CLIP Fine-tuned Confusion Matrix:

![](results/confusion_matrix_clip.png)

SigLIP vs CLIP Confidence 비교:

![](results/confidence_comparison.png)

---

### 2. 의미론적 분할 (Semantic Segmentation)

| 모델 | mIoU | 학습 데이터 | 비고 |
|------|------|-----------|------|
| OneFormer pretrained | 37.1% | ADE20K | 기준선 |
| OneFormer fine-tuned | **45.6%** | ADE20K + FoodSeg103 | 1 epoch, joint training |
| oneformer_top | [TBD] | 추가 학습 중 | — |

- **모델**: `shi-labs/oneformer_ade20k_swin_large`
- **목적**: ADE20K 클래스를 travel-relevant semantic ratio(water, sky, vegetation, building, food)로 집계
- **inference latency**: [TBD] ms/image (GPU)

![](results/oneformer_results.png)

---

### 3. Preference Vector 학습 (MLP)

| 항목 | 설정 |
|------|------|
| 입력 | CLIP image embedding (768-dim) |
| 구조 | MLP 768→512→256→128→6, multilabel sigmoid |
| Loss | BCE Loss with class weights (희소 클래스 보정) |
| 데이터 | Pseudo Labeling pipeline (v3 generator) |
| Sampler | Rare-class weighted sampler |
| Val F1 (macro) | [TBD] |
| Val F1 (micro) | [TBD] |

---

### 4. 3D 씬 렌더링

| 단계 | 내용 |
|------|------|
| 초기 시도 | COLMAP + 3D Gaussian Splatting (3DGS) 파이프라인 |
| 결과 | 2개 씬 학습 완료, 오프라인 렌더링 결과 확보 |
| 전환 사유 | 웹 브라우저 통합 시 호환성·로딩 시간·GPU 의존성 문제 |
| 최종 구현 | Three.js procedural scene (beach, nature, city, culture, food, festival) |
| 정량 평가 | [TBD] |

---

### 5. 종합 결과

| 항목 | 수치 / 상태 |
|------|------------|
| Scene Classification (CLIP FT) | Val Acc **93.48%** · Confidence **79~87%** |
| Segmentation (OneFormer FT) | mIoU **45.6%** (+8.5%p vs pretrained) |
| MLP (mood / place / style) | Val F1 [TBD] |
| Multi-image Ensemble | 5~7장 per-image vector 평균 앙상블 |
| Recommendation | Top-3~5 destinations, category-aware scoring |
| End-to-end Latency | [TBD] s / 7 images (GPU) |

---

## Limitations & Engineering Decisions

**주요 전환 결정 요약**

| 결정 | 초기 시도 | 최종 선택 | 이유 |
|------|---------|---------|------|
| 장면 분류 | SigLIP fine-tuned | **CLIP fine-tuned** | inference confidence 33~37% vs 79~87%; preference vector 품질에 직결 |
| Segmentation | Mask2Former | **OneFormer** | 멀티 데이터셋 통합 학습 효율; Mask2Former는 태스크별 개별 학습 필요 |
| 3D 렌더링 | COLMAP + 3DGS | **Three.js** | 웹 통합 호환성, 실시간 렌더링, GPU 의존성 제거 |

1. **Confidence over Raw Accuracy**  
   SigLIP은 validation accuracy가 높으나 inference confidence가 낮아 production 배포에 부적합하다고 판단, CLIP fine-tuned를 채택하였다.

2. **Mask2Former → OneFormer**  
   카테고리별로 서로 다른 도메인의 데이터셋(ADE20K, FoodSeg103 등)을 통합 학습할 때, Mask2Former는 태스크마다 개별 학습이 필요하여 학습 비용이 과도하게 증가한다. OneFormer의 task-conditioned joint training이 멀티 데이터셋 통합에 구조적으로 적합하다.

3. **3DGS → Three.js**  
   3DGS는 photorealistic novel-view synthesis에 유리하나, 웹 배포·실시간 상호작용·모바일 호환성 측면에서 Three.js procedural rendering이 더 적합하였다.

4. **Gemini API 의존**  
   자연어 설명 및 챗봇은 외부 LLM API에 의존하며, API 키(`GOOGLE_API_KEY`) 및 네트워크 연결이 필요하다.

5. **카테고리 한계**  
   6-class scene taxonomy는 여행 도메인을 coarse-grained로만 표현한다. 세부 테마(예: hiking vs. beach resort) 구분은 추가 확장이 필요하다.

6. **Cold-start**  
   업로드 사진 수(최소 5장) 및 품질에 따라 `is_uncertain` 플래그가 활성화되며, 이 경우 랜덤/보조 추천 fallback이 동작한다.

---

## Installation & Usage

### 요구 사항

- Python 3.10+
- CUDA-capable GPU (권장)
- Node.js 불필요 (정적 frontend, Three.js CDN)

### 설치

```bash
git clone <repository-url>
cd cv_project

python -m venv venv
# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
```

### 환경 변수

프로젝트 루트에 `.env` 파일을 생성한다.

```env
GOOGLE_API_KEY=your_gemini_api_key
```

### 모델 가중치

Fine-tuned CLIP 가중치를 `models/best_clip.pth`에 배치한다.  
(경로는 `backend/siglip_classifier.py`의 `DEFAULT_MODEL_PATH` 참조)

```
models/
  best_clip.pth          # CLIP fine-tuned (최종 분류 모델)
  best_siglip.pth        # SigLIP fine-tuned (실험용)
  mlp_mood_best.pth
  mlp_place_best.pth
  mlp_style_best.pth
  oneformer_top/         # OneFormer fine-tuned 체크포인트
```

### 서버 실행

```bash
uvicorn backend.main:app --reload --port 8000
```

브라우저에서 `http://localhost:8000` 접속.

### 사용 흐름

1. 메인 화면에서 **바코드(탑승권)** 클릭 → 업로드 화면 이동
2. 일상 사진 **5~7장** 업로드
3. **AI 분석 시작** → 로딩 → 결과 화면
4. 좌측: 3D 씬 + CV Analysis (미니 카드, 전체/Photo별 분석)
5. 우측: Gemini 요약, CV 상세 분석, Flying 챗봇, 탑승권 발급

### Fine-tuning (선택)

```bash
# CLIP 장면 분류 fine-tuning
python classification/clip_finetune.py \
    --train_dir data/train \
    --val_dir data/val \
    --epochs 10 --batch_size 32 --lr 1e-5

# SigLIP (실험용)
python classification/siglip_finetune.py \
    --train_dir data/train \
    --val_dir data/val \
    --epochs 10
```

---

## References

1. Radford, A., Kim, J. W., Hallacy, C., Ramesh, A., Goh, G., Agarwal, S., ... & Sutskever, I. (2021). *Learning Transferable Visual Models From Natural Language Supervision.* ICML. (CLIP)
2. Zhai, X., Mustafa, B., Kolesnikov, A., & Beyer, L. (2023). *Sigmoid Loss for Language Image Pre-Training.* ICCV. (SigLIP)
3. Jain, J., Li, J., Chiu, M. T., Hassani, A., Orlov, N., & Shi, H. (2023). *OneFormer: One Transformer to Rule Universal Image Segmentation.* CVPR.
4. Cheng, B., Misra, I., Schwing, A. G., Kirillov, A., & Girdhar, R. (2022). *Masked-attention Mask Transformer for Universal Image Segmentation (Mask2Former).* CVPR.
5. Kerbl, B., Kopanas, G., Leimkühler, T., & Drettakis, G. (2023). *3D Gaussian Splatting for Real-Time Radiance Field Rendering.* ACM Transactions on Graphics (SIGGRAPH).
6. Schönberger, J. L., & Frahm, J.-M. (2016). *Structure-from-Motion Revisited.* CVPR. (COLMAP)
7. Google DeepMind. *Gemini API Documentation.* https://ai.google.dev/

---

*PhotoTrip — Computer Vision Course Project*
