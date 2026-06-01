# 📸PhotoTrip

**개인 사진으로 여행 취향을 분석하는 AI 시스템**

---

## Abstract

기존 여행 추천 시스템은 설문·클릭 로그·예약 이력 등 명시적 신호에 의존하며, 사용자가 인지하지 못하는 잠재적 취향—일상 사진에 암묵적으로 내재된 장소 감성, 색감 선호, 분위기 취향—을 반영하기 어렵다는 근본적 한계를 지닌다.

본 연구는 사용자의 일상 사진(5~7장)으로부터 여행 취향을 자동으로 정량화하고 맞춤형 여행지를 추천하는 end-to-end AI 시스템 **PhotoTrip**을 제안한다.

시스템은 네 개의 분석 모듈을 병렬로 구동한다. **(1) 장면 분류**: CLIP ViT-B/32를 beach·nature·city·culture·festival·food 6-class로 fine-tuning하여 장면 범주와 예측 confidence를 추출한다. **(2) 의미론적 분할**: OneFormer의 task-conditioned joint training으로 ADE20K·FoodSeg103·Cityscapes를 단일 모델에서 통합 학습하여 픽셀 수준의 water·sky·vegetation·building·food 비율을 산출한다. **(3) 시각 특성 분석**: OpenCV로 밝기·채도·대비·색온도를 정량화한다. **(4) 스타일 분류**: BCE Loss with class weights와 Pseudo Labeling을 적용한 MLP로 분위기·라이프스타일 벡터를 생성한다. 네 모듈의 출력을 통합한 **Preference Vector**는 코사인 유사도 기반 추천 엔진에 입력되어 Top-3 여행지를 선정하고, Gemini LLM이 결과를 자연어로 설명한다.

실험 결과, 장면 분류에서 CLIP zero-shot 64.27% 대비 fine-tuned 모델이 **93.48%**(+29.2%p)를 달성하였다. 모델 선택 과정에서 SigLIP fine-tuned는 accuracy(93.56%)가 유사하나 inference confidence가 **33~37%** 에 머무는 반면, CLIP fine-tuned는 **79~87%** confidence를 일관되게 산출하여 downstream preference vector 품질 관점에서 CLIP을 최종 채택하였다. OneFormer fine-tuning을 통해 mIoU **37.1% -> 45.6%**(+8.5%p)를 확보하였다.

분석 결과는 카테고리별 Three.js 3D 씬, CV 대시보드, 가상 탑승권 UI를 통해 시각화되며, 정량 분석과 Gemini기반 정성적 해석을 함께 제공하는 설명 가능한 추천 경험을 구현한다.

---

## System Overview

```mermaid
flowchart TD
    INPUT["사진 업로드 5~7장\n일상 사진 입력"]
    INPUT --> CLIP
    INPUT --> ONE
    INPUT --> OCV
    INPUT --> SMLP
    subgraph ANALYSIS["Per-Image Analysis - 병렬 처리"]
        CLIP["CLIP Fine-tuned\n장면 분류 Acc 93.48% Conf 79~87%\noutput: scene scores"]
        ONE["OneFormer\n의미론적 분할 mIoU 45.6%\noutput: semantic ratio"]
        OCV["OpenCV\n밝기 채도 색온도 대비\noutput: visual metrics"]
        SMLP["Style MLP\n768->512->256->128->6 BCE Loss\noutput: mood place style"]
    end
    CLIP --> PV
    ONE --> PV
    OCV --> PV
    SMLP --> PV
    subgraph VECTOR["Preference Vector Builder"]
        PV["scene + visual + semantic + style + lifestyle\nN장 평균 앙상블 - top_category confidence is_uncertain"]
    end
    PV --> REC
    PV --> GEM
    subgraph OUTPUT["Output"]
        REC["추천 엔진\n코사인 유사도 Top-3~5 여행지"]
        GEM["Gemini LLM\n취향 자연어 설명 Flying 챗봇"]
        REC --> FE
        GEM --> FE
        subgraph FE["Frontend"]
            T1["가상 탑승권\nTop-3 여행지 Gemini 취향 설명"]
            T2["Three.js 3D 씬\n6개 카테고리 인터랙티브"]
            T3["CV Dashboard\n분석 결과 Photo별 상세"]
        end
    end
    style ANALYSIS fill:#e6f1fb,stroke:#378add
    style VECTOR fill:#e1f5ee,stroke:#1d9e75
    style OUTPUT fill:#faeeda,stroke:#ba7517
    style FE fill:#fff8ee,stroke:#ef9f27
```

### 카테고리별 분석 예시

| 입력 사진 특성 | 분류 결과 | 추천 여행지 예시 |
|--------------|---------|----------------|
| 해변, 바다, 모래 | 🏖️ beach | 발리, 몰디브, 제주 |
| 산, 숲, 자연 | 🌲 nature | 퀸스타운, 파타고니아, 설악산 |
| 도시, 야경, 빌딩 | 🌆 city | 도쿄, 홍콩, 파리 |
| 사원, 박물관, 문화유산 | 🏛️ culture | 교토, 로마, 이스탄불 |
| 공연, 축제, 음악 | 🎪 festival | 밀라노, 에든버러, 라스베가스 |
| 음식, 카페, 길거리 음식 | 🍜 food | 나폴리, 방콕, 오사카 |

## 🛠️ 기술 스택

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)
![HuggingFace](https://img.shields.io/badge/HuggingFace-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black)
![Gemini](https://img.shields.io/badge/Gemini_API-4285F4?style=for-the-badge&logo=google&logoColor=white)
![Three.js](https://img.shields.io/badge/Three.js-000000?style=for-the-badge&logo=three.js&logoColor=white)

| 계층 | 기술 |
|------|------|
| Backend | FastAPI · PyTorch · HuggingFace Transformers |
| 장면 분류 | CLIP ViT-B/32 fine-tuned |
| 의미론적 분할 | OneFormer (swin_large) |
| 시각 분석 | OpenCV |
| 스타일 분류 | MLP · BCE Loss · Pseudo Labeling |
| LLM | Google Gemini API |
| Frontend | Three.js · HTML/CSS/JS |
| 학습 환경 | Google Colab · Kaggle (GPU) |

---

## 💡 Key Contributions

1. **멀티모달 Preference Vector 앙상블**  
   CLIP 장면 분류 · OneFormer 분할 비율 · OpenCV 시각 메트릭 · MLP 스타일 점수를
   통합한 Preference Vector 설계 및 N장 평균 앙상블로 robust한 취향 표현 구축

2. **Accuracy–Confidence 트레이드오프 실험적 검증**  
   SigLIP(33~37%) vs CLIP(79~87%) confidence 비교 실험을 통해
   accuracy parity 조건 하에서 calibration 우위를 정량적으로 검증하고 CLIP 채택

3. **OneFormer 멀티데이터셋 통합 학습**  
   카테고리별 이질적 도메인(ADE20K · FoodSeg103 · Cityscapes)을
   Mask2Former 대신 OneFormer의 task-conditioned joint training으로
   단일 모델 통합 학습 → Travel-class mIoU 37.1% → 45.6%

4. **Pseudo Labeling 자동 데이터 파이프라인**  
   Pixabay API로 여행 사진 수집 후 SigLIP으로 자동 pseudo labeling,
   confidence threshold 필터링으로 학습 데이터 자동 구축

5. **MLP 기반 스타일·라이프스타일 분류**  
   BCE Loss + class weights로 클래스 불균형 처리,
   mood · place · style 3개 MLP 독립 학습 (v3/v4 실험)
   CLIP 임베딩(768차원) → 6-class multilabel 분류

6. **COLMAP + 3DGS 렌더링 실험**  
   Structure-from-Motion(COLMAP) + 3D Gaussian Splatting 파이프라인으로
   2개 씬 학습 및 렌더링 결과 확보, 웹 통합은 Three.js로 전환

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

본 프로젝트는 6개 여행 카테고리(beach, nature, city, culture, festival, food)별로 서로 다른 도메인의 데이터셋을 사용한다.

| 카테고리 | 학습 데이터셋 | 도메인 |
|---------|------------|--------|
| 자연/도시/문화 | ADE20K | 실내외 범용 장면 |
| 음식 | FoodSeg103 | 음식 특화 |
| 도시/도로 | Cityscapes | 도시 주행 장면 |

Mask2Former를 사용할 경우 데이터셋마다 별도 모델 학습이 필요하여 최소 3개 모델, 3배의 GPU 메모리·학습 시간이 요구된다. OneFormer의 task-conditioned joint training은 단일 모델로 3개 데이터셋을 통합 학습할 수 있어 채택하였으며, 실험 결과 Travel-class mIoU가 37.1% → 45.6%로 향상되었다 (Jain et al., CVPR 2023).

### SigLIP vs CLIP 채택 배경

본 시스템에서 Preference Vector는 분류 모델의 카테고리별 softmax 확률을 직접 사용한다.

```python
# Preference Vector 구성 예시
scene = {
    "beach": 0.87,   # CLIP: 명확한 신호
    "nature": 0.05,
    ...
}
# vs SigLIP
scene = {
    "beach": 0.34,   # SigLIP: 희석된 신호
    "nature": 0.31,  # 균등 분포에 가까움
    ...
}
```

SigLIP은 sigmoid loss 특성상 각 클래스를 독립적으로 평가하여 confidence가 33~37%에 머문다. 이는 6개 카테고리가 거의 균등하게 분산(약 16.7%)되는 것과 유사하여 취향 신호가 희석된다.

반면 CLIP은 softmax 기반으로 confidence가 79~87%를 달성하여 취향 신호를 명확하게 전달한다. 또한 낮은 confidence는 시스템의 `is_uncertain` 플래그를 활성화하여 랜덤 추천 fallback을 유발, 서비스 품질을 직접 저하시킨다.

| 모델 | Val Accuracy | Inference Confidence | 채택 |
|------|-------------|---------------------|------|
| SigLIP fine-tuned | 93.56% | 33~37% ❌ | 미채택 |
| **CLIP fine-tuned** | **93.48%** | **79~87% ✅** | **채택** |

---

## 모델 학습 구조

```mermaid
flowchart LR
    subgraph CLIP["CLIP 장면 분류 학습"]
        A1["Pixabay 수집\n6클래스"] --> A2["Pseudo Labeling\nSigLIP->CLIP"]
        A2 --> A3["CLIP Fine-tuning"] --> A4["Acc 93.48%\nConf 79~87%"]
    end

    subgraph ONE["OneFormer 분할 학습"]
        B1["ADE20K\nFoodSeg\nCityscapes"] --> B2["통합 학습\njoint training"]
        B2 --> B3["mIoU\n37.1%->45.6%"]
    end

    subgraph MLP["MLP 스타일 분류"]
        C1["CLIP 임베딩\n768차원"] --> C2["768->512\n->256->128->6"]
        C2 --> C3["mood\nplace\nstyle"]
    end

    subgraph OCV["OpenCV 시각 분석"]
        D1["RGB\n이미지"] --> D2["밝기 채도\n색온도 대비"]
        D2 --> D3["6개\n메트릭"]
    end

    CLIP --> PV
    ONE --> PV
    MLP --> PV
    OCV --> PV

    PV(["Preference Vector\nscene+visual+semantic\n+style+lifestyle"])

    style CLIP fill:#e6f1fb,stroke:#378add
    style ONE fill:#e1f5ee,stroke:#1d9e75
    style MLP fill:#eeedfe,stroke:#7f77dd
    style OCV fill:#faeeda,stroke:#ba7517
    style PV fill:#f1efe8,stroke:#5f5e5a
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
