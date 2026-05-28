import sys

sys.path.insert(0, "backend")

from PIL import Image

from oneformer import segment
from opencv_analyzer import analyze
from preference_vector import SCENE_CATEGORIES, build_vector
from recommender import recommend
from siglip_classifier import classify
from style_analyzer import analyze_style

imgs = {
    "가방+디저트": "C:/Users/seori/OneDrive/Pictures/Screenshots/스크린샷 2026-05-17 022612.png",
    "신발(야간)": "C:/Users/seori/OneDrive/Pictures/Screenshots/스크린샷 2026-05-17 022606.png",
    "하늘+구름": "C:/Users/seori/OneDrive/Pictures/Screenshots/스크린샷 2026-05-17 022558.png",
    "치킨+떡볶이": "C:/Users/seori/OneDrive/Pictures/Screenshots/스크린샷 2026-05-17 022550.png",
    "말차음료": "C:/Users/seori/OneDrive/Pictures/Screenshots/스크린샷 2026-05-17 022542.png",
    "나무": "C:/Users/seori/OneDrive/Pictures/Screenshots/스크린샷 2026-05-17 022531.png",
    "한강야경": "C:/Users/seori/OneDrive/Pictures/Screenshots/스크린샷 2026-05-17 022521.png",
}

for name, path in imgs.items():
    img = Image.open(path).convert("RGB")
    clip_scores = classify(img, use_tta=True, temperature=1.1)
    top = max(clip_scores, key=clip_scores.get)
    all_scores = {cat: float(clip_scores.get(cat, 0.0)) for cat in SCENE_CATEGORIES}
    clip_result = {"category": top, "confidence": clip_scores[top], "all_scores": all_scores}
    from oneformer import segment_ratios

    segment_result = segment(img)
    seg_ratios = segment_ratios(segment_result)
    opencv_result = analyze(img)
    style_result = analyze_style(img, opencv_result)
    pv = build_vector(clip_result, seg_ratios, opencv_result, style_result)
    detected_objects = set(seg_ratios.keys())
    rec = recommend(pv, detected_objects=detected_objects)
    print(
        f'{name}: {top} ({clip_scores[top]:.1%}) → {rec["destinations"]} / random={rec["is_random"]}'
    )
