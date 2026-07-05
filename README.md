<div align="center">

<img width="100%" src="https://capsule-render.vercel.app/api?type=waving&height=260&color=0:E0F2FE,45:7DD3FC,100:38BDF8&text=📸%20PhotoTrip&fontSize=64&fontColor=ffffff&animation=fadeIn&fontAlignY=36&desc=Discover%20Your%20Travel%20Style%20from%20Everyday%20Photos&descSize=18&descAlignY=58&descColor=ffffff"/>

<br/>

### ✈️ 일상 사진으로 발견하는 나만의 여행 취향

**PhotoTrip은 사용자의 일상 사진 5~7장을 분석하여  
잠재적인 시각 선호를 추론하고, 맞춤 여행지를 추천하는 멀티모달 AI 서비스입니다.**

<br/>

<img src="https://img.shields.io/badge/Python_3.10+-38BDF8?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/PyTorch-0EA5E9?style=for-the-badge&logo=pytorch&logoColor=white"/>
<img src="https://img.shields.io/badge/FastAPI-0284C7?style=for-the-badge&logo=fastapi&logoColor=white"/>
<img src="https://img.shields.io/badge/OpenCV-7DD3FC?style=for-the-badge&logo=opencv&logoColor=white"/>
<img src="https://img.shields.io/badge/Three.js-075985?style=for-the-badge&logo=three.js&logoColor=white"/>
<img src="https://img.shields.io/badge/Gemini-0369A1?style=for-the-badge&logo=google&logoColor=white"/>

<br/><br/>

<img src="results/demo.gif" width="88%" style="border-radius: 18px;"/>

<br/><br/>

> ☁️ **No questionnaire. No booking history.**  
> PhotoTrip infers your travel preference only from your everyday photos.

</div>

<br/>

---

<br/>

<div align="center">

## 🛫 Boarding Now

<table>
<tr>
<td align="center" width="180">
<h3>📷</h3>
<b>Upload</b>
<br/>
5–7 daily photos
</td>
<td align="center" width="60">
<h2>→</h2>
</td>
<td align="center" width="180">
<h3>🧠</h3>
<b>Analyze</b>
<br/>
Multimodal AI
</td>
<td align="center" width="60">
<h2>→</h2>
</td>
<td align="center" width="180">
<h3>🌎</h3>
<b>Recommend</b>
<br/>
Personalized trip
</td>
<td align="center" width="60">
<h2>→</h2>
</td>
<td align="center" width="180">
<h3>🎮</h3>
<b>Explore</b>
<br/>
3D scene
</td>
</tr>
</table>

</div>

<br/>

---

<br/>

## ☁️ Why PhotoTrip?

기존 여행 추천 시스템은 사용자의 **명시적 행동 데이터**에 의존합니다.

<br/>

<div align="center">

<table>
<tr>
<td width="45%" align="center">

### 🧳 Traditional Travel Recommendation

<br/>

📝 Survey  
🛒 Booking History  
🖱 Click Log  

<br/>

<b>사용자가 직접 남긴 데이터 기반</b>

</td>
<td width="10%" align="center">

<h2>→</h2>

</td>
<td width="45%" align="center">

### 📸 PhotoTrip

<br/>

📷 Everyday Photos  
🧠 Visual Preference  
🌎 Personalized Destination  

<br/>

<b>무의식적으로 촬영한 사진 기반</b>

</td>
</tr>
</table>

</div>

<br/>

PhotoTrip은 사용자가 일상에서 자연스럽게 촬영한 사진 속에서  
**장소 선호, 공간 구성, 색감, 분위기**를 추론합니다.

핵심은 단순한 장면 분류가 아니라,

> **사용자의 시각적 취향을 하나의 Preference Vector로 표현하는 것**입니다.

<br/>

---

<br/>

## ✨ Key Features

<div align="center">

<table>
<tr>
<td width="50%" valign="top">

<h3>🧠 Multimodal AI Analysis</h3>

CLIP, OneFormer, OpenCV, Preference MLP를 함께 사용하여  
사진 속 장면, 의미 구성, 색감, 분위기를 분석합니다.

<br/>

<b>Scene · Semantic · Visual · Style</b>

</td>
<td width="50%" valign="top">

<h3>☁️ Preference Vector</h3>

사용자의 시각적 취향을  
해석 가능한 44차원 벡터로 표현합니다.

<br/>

<b>44-D Interpretable Representation</b>

</td>
</tr>

<tr>
<td width="50%" valign="top">

<h3>🌎 Personalized Destination</h3>

사용자 Preference Vector와 여행지 프로필을  
코사인 유사도로 비교하여 Top-3 여행지를 추천합니다.

<br/>

<b>Cosine Similarity Matching</b>

</td>
<td width="50%" valign="top">

<h3>🎮 Interactive 3D Scene</h3>

추천 결과를 단순 텍스트가 아니라  
Three.js 기반 인터랙티브 3D 씬으로 시각화합니다.

<br/>

<b>Three.js Travel Visualization</b>

</td>
</tr>
</table>

</div>

<br/>

---

<br/>

## 🎥 Demo

<div align="center">

| 🏙️ City | 🏛️ Culture | 🌿 Nature |
|:--:|:--:|:--:|
| [Video](https://github.com/user-attachments/assets/2e39bb36-876f-4b46-a000-fc9914e87034) | [Video](https://github.com/user-attachments/assets/aa2ad316-7270-4293-bfdf-e43aabe4dada) | [Video](https://github.com/user-attachments/assets/45d3d391-dde3-41f9-a6ee-d80ff77b4c9f) |

| 🍕 Food | 🌊 Beach | 🎆 Festival |
|:--:|:--:|:--:|
| [Video](https://github.com/user-attachments/assets/5ef5fe29-4734-4f77-87b2-511de3855b48) | [Video](https://github.com/user-attachments/assets/a79cddb6-0e5d-4cad-ab43-86cdc3fb5185) | [Video](https://github.com/user-attachments/assets/96f4ace8-f7e2-4662-9a4c-6044df3dc3ec) |

</div>

<br/>

---

<br/>

## 🏆 Key Results

<div align="center">

<table>
<tr>
<td align="center" width="33%">

<h1>93.48%</h1>

<b>CLIP Accuracy</b>

Scene Classification

</td>
<td align="center" width="33%">

<h1>45.6</h1>

<b>OneFormer mIoU</b>

Semantic Segmentation

</td>
<td align="center" width="33%">

<h1>0.9450</h1>

<b>Macro F1</b>

Preference MLP

</td>
</tr>
</table>

</div>

<br/>

<p align="center">
  <img src="results/full_experiment_history.png.png" width="82%"/>
</p>

<p align="center">
  <img src="results/confidence_comparison.png.png" width="48%"/>
  <img src="results/Oneformer_mIoU.png.png" width="48%"/>
</p>

<br/>

---

<br/>

<div align="center">

## 🌊 Core Idea

### Travel preference is not a single category.

It is a combination of

**scene meaning, semantic composition, color mood, and lifestyle preference.**

PhotoTrip integrates these heterogeneous signals into one  
**interpretable Preference Vector**.

</div>

<br/>
---

<br/>

# 🧠 Why A Single Model Is Not Enough?

Modern travel preference cannot be represented by a single computer vision model.

Each model understands **only one aspect** of an image.

PhotoTrip combines multiple complementary models to capture a user's latent visual preference.

<br/>

<div align="center">

| Model | ✅ What it Understands | ❌ What it Misses |
|:------:|:----------------------|:------------------|
| **CLIP** | Scene Category | Color, Mood, Spatial Composition |
| **OneFormer** | Semantic Composition | User Preference |
| **OpenCV** | Visual Statistics | Scene Meaning |
| **Preference MLP** | Lifestyle & Mood | Spatial Structure |

</div>

<br/>

<div align="center">

### 🌊 A Single Image Contains Multiple Signals

</div>

```text
                  📷 Input Image
                       │
     ┌──────────┬──────────┬──────────┬──────────┐
     │          │          │          │
     ▼          ▼          ▼          ▼
   CLIP    OneFormer    OpenCV      MLP
 Scene      Semantic     Color     Lifestyle
 Category   Structure   Statistics  Preference
     │          │          │          │
     └──────────┴──────────┴──────────┘
                    │
                    ▼
          ✨ Preference Vector
```

<br/>

Instead of relying on a single prediction,

PhotoTrip combines

- 🌄 Scene Information
- 🌿 Semantic Composition
- 🎨 Visual Characteristics
- 😊 Lifestyle Preference

into a unified representation.

<br/>

---

<br/>

# ☁️ Preference Vector

<div align="center">

### The Core Representation of PhotoTrip

Rather than predicting only a travel category,

PhotoTrip represents each user as an

# **44-Dimensional Preference Vector**

</div>

<br/>

<div align="center">

| Category | Dimension |
|:---------|:---------:|
| 🌄 Scene | **6** |
| 🎨 Visual Features | **6** |
| 🌿 Semantic Composition | **5** |
| 😊 Style Preference | **6** |
| 📍 Place Preference | **6** |
| 🌤 Mood Preference | **6** |
| ⭐ Personal Interests | **9** |
| **Total** | **44** |

</div>

<br/>

<div align="center">

### ✨ Preference Vector Pipeline

</div>

```text
Everyday Photos
        │
        ▼
Per-Image Analysis
(CLIP + OneFormer + OpenCV + MLP)
        │
        ▼
Feature Extraction
        │
        ▼
44-D Preference Vector
        │
        ▼
Average Ensemble
(5~7 Photos)
        │
        ▼
Cosine Similarity Matching
        │
        ▼
Recommended Destinations
```

<br/>

### Example

```json
{
  "beach": 0.82,
  "nature": 0.11,
  "water": 0.43,
  "vegetation": 0.21,
  "warm_tone": 0.79,
  "saturation": 0.74,
  "energetic": 0.68,
  "cozy": 0.14
}
```

↓

### 🌎 Recommended Destinations

🥇 Bali

🥈 Phuket

🥉 Cebu

↓

### 🤖 Gemini Explanation

> You prefer warm colors, vibrant environments, and destinations where beaches and local food coexist.

<br/>

---

<br/>

# 🏗️ System Architecture

<div align="center">

### End-to-End AI Pipeline

</div>

```text
                    📷 Upload Photos
                           │
                           ▼
                 ┌──────────────────┐
                 │   CLIP Fine-tuned │
                 │ Scene Classification │
                 └──────────────────┘
                           │
                 ┌──────────────────┐
                 │    OneFormer      │
                 │ Semantic Parsing  │
                 └──────────────────┘
                           │
                 ┌──────────────────┐
                 │      OpenCV       │
                 │ Visual Statistics │
                 └──────────────────┘
                           │
                 ┌──────────────────┐
                 │ Preference MLP    │
                 │ Lifestyle Analysis│
                 └──────────────────┘
                           │
                           ▼
                ✨ Preference Vector
                           │
                           ▼
              Cosine Similarity Retrieval
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
      🌎 Destination               🤖 Gemini
      Recommendation              Explanation
             │                           │
             └─────────────┬─────────────┘
                           ▼
                  🎮 Three.js Frontend
                           │
                           ▼
          Dashboard · Boarding Pass · 3D Scene
```

<br/>

---

<br/>

# 📦 Tech Stack

<div align="center">

<table>

<tr>

<td align="center" width="25%">

### 🧠 AI

CLIP

OneFormer

OpenCV

Preference MLP

</td>

<td align="center" width="25%">

### ⚙ Backend

FastAPI

PyTorch

Transformers

</td>

<td align="center" width="25%">

### 🎮 Frontend

Three.js

JavaScript

HTML / CSS

</td>

<td align="center" width="25%">

### ☁️ Services

Gemini API

Google Colab

Kaggle GPU

</td>

</tr>

</table>

</div>

<br/>

---
