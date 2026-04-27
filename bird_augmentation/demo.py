"""Streamlit demo app for bird weather augmentation."""

from __future__ import annotations

import os
from datetime import datetime
from io import BytesIO

import numpy as np
import streamlit as st
from PIL import Image

from weather_aug import WeatherAugmentor, WeatherClassifier

SAMPLES_ORIGINAL_DIR = os.path.join("samples", "original")
SAMPLES_AUGMENTED_DIR = os.path.join("samples", "augmented")


def ensure_dirs() -> None:
    os.makedirs(SAMPLES_ORIGINAL_DIR, exist_ok=True)
    os.makedirs(SAMPLES_AUGMENTED_DIR, exist_ok=True)


def pil_to_np(img: Image.Image) -> np.ndarray:
    return np.array(img.convert("RGB"))


def np_to_pil(arr: np.ndarray) -> Image.Image:
    return Image.fromarray(arr.astype(np.uint8))


def save_image(img: Image.Image, prefix: str, effect: str | None = None) -> str:
    ensure_dirs()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    effect_name = effect or "none"
    filename = f"{prefix}_{effect_name}_{ts}.png"
    path = os.path.join(SAMPLES_AUGMENTED_DIR, filename)
    img.save(path)
    return path


def log_augmentation(effect: str, filename: str) -> None:
    os.makedirs("logs", exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_path = os.path.join("logs", "augmentations.log")
    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"{ts} | Effect: {effect} | File: {filename}\n")


def show_prediction_block(classifier: WeatherClassifier, image: np.ndarray) -> dict[str, object]:
    details = classifier.predict_with_details(image)
    st.caption("**Weather Prediction:**")
    st.write(
        f"🔍 {details['predicted_class'].capitalize()}: {details['confidence'] * 100:.1f}%"
    )
    with st.expander("See all predictions"):
        for cls_name, score in details["top_3"]:
            st.write(f"- {cls_name.capitalize()}: {score * 100:.1f}%")
    return details


def main() -> None:
    st.set_page_config(
        page_title="QA Sentinels — Bird Weather Augmentation",
        layout="wide",
    )
    ensure_dirs()

    st.title("Bird Weather-Based Image Augmentation")
    st.markdown(
        "Upload a bird image (e.g., Rock Pigeon, House Sparrow, Scarlet Macaw), "
        "then apply weather effects like **Rain**, **Snow**, **Fog**, **Night**, "
        "**Sunny**, **Autumn**, or **Motion Blur** to test how environmental "
        "conditions affect bird species identification apps (Merlin Bird ID / "
        "Seek by iNaturalist / iNaturalist). The original image (Old) is shown "
        "on the left, and the augmented image (New) on the right. The tool flags "
        "when augmentation causes a meaningful shift in the rule-based weather "
        "oracle's prediction."
    )

    st.sidebar.header("Controls")
    intensity = st.sidebar.selectbox("Intensity", ["low", "medium", "high"], index=1)
    auto_save = st.sidebar.checkbox("Automatically save augmented images", value=True)
    enable_classifier = st.sidebar.checkbox(
        "Enable Weather Prediction (Rule-Based Oracle)", value=True
    )

    classifier = WeatherClassifier() if enable_classifier else None

    uploaded_file = st.file_uploader("Upload a bird image", type=["png", "jpg", "jpeg"])

    col_old, col_new = st.columns(2)
    original_img: Image.Image | None = None
    np_img: np.ndarray | None = None
    original_details: dict[str, object] | None = None

    if uploaded_file is not None:
        original_img = Image.open(uploaded_file).convert("RGB")
        np_img = pil_to_np(original_img)
        with col_old:
            st.subheader("Old (Original)")
            st.image(original_img, use_column_width=True)
            if classifier is not None:
                original_details = show_prediction_block(classifier, np_img)
    else:
        with col_old:
            col_old.info("Upload a bird image to get started.")

    st.markdown("### Apply Weather Effect")
    row1 = st.columns(5)
    row2 = st.columns(5)
    effect_clicked: str | None = None

    if row1[0].button("Rain"):
        effect_clicked = "rain"
    if row1[1].button("Snow"):
        effect_clicked = "snow"
    if row1[2].button("Fog"):
        effect_clicked = "fog"
    if row1[3].button("Night"):
        effect_clicked = "night"
    if row1[4].button("Sunny"):
        effect_clicked = "sunny"

    if row2[0].button("Autumn"):
        effect_clicked = "autumn"
    if row2[1].button("Motion Blur"):
        effect_clicked = "motion_blur"

    st.markdown("### Combine Effects")
    multi_effects = st.multiselect(
        "Choose multiple effects to apply in order:",
        ["rain", "snow", "fog", "night", "sunny", "autumn", "motion_blur"],
    )
    if st.button("Apply Selected Effects"):
        effect_clicked = "multi"

    if effect_clicked is not None:
        if np_img is None or original_img is None or uploaded_file is None:
            st.warning("Please upload a bird image before applying an effect.")
        else:
            try:
                augmentor = WeatherAugmentor(intensity=intensity)
                if effect_clicked == "multi":
                    np_aug = np_img.copy()
                    applied_effects: list[str] = []
                    for effect in multi_effects:
                        np_aug = augmentor.apply_effect(np_aug, effect)
                        applied_effects.append(effect)
                    effect_name = "+".join(applied_effects) if applied_effects else "none"
                else:
                    np_aug = augmentor.apply_effect(np_img, effect_clicked)
                    effect_name = effect_clicked

                aug_img = np_to_pil(np_aug)

                with col_new:
                    st.subheader("New (Augmented)")
                    st.image(aug_img, use_column_width=True)
                    st.caption(f"Effect: {effect_name.capitalize()}, Intensity: {intensity}")

                    aug_details: dict[str, object] | None = None
                    if classifier is not None:
                        aug_details = show_prediction_block(classifier, np_aug)

                    if classifier is not None and original_details is not None and aug_details is not None:
                        orig_class = str(original_details["predicted_class"])
                        aug_class = str(aug_details["predicted_class"])
                        orig_conf = float(original_details["confidence"])
                        aug_conf = float(aug_details["confidence"])
                        if orig_class != aug_class:
                            st.warning(
                                f"⚠️ Prediction changed: {orig_class.capitalize()} → "
                                f"{aug_class.capitalize()}"
                            )
                        else:
                            delta = (aug_conf - orig_conf) * 100
                            if abs(delta) > 5:
                                st.info(f"Confidence changed by {delta:+.1f}%")

                    byte_im = BytesIO()
                    aug_img.save(byte_im, format="PNG")
                    byte_im.seek(0)
                    st.download_button(
                        label="Download Image",
                        data=byte_im,
                        file_name=f"augmented_{effect_name}.png",
                        mime="image/png",
                    )

                log_augmentation(effect_name, uploaded_file.name)

                if auto_save:
                    prefix = os.path.splitext(os.path.basename(uploaded_file.name))[0]
                    path = save_image(aug_img, prefix, effect_name)
                    st.success(f"Augmented image saved to: {path}")

            except Exception as e:  # noqa: BLE001
                st.error(f"Failed to apply effect: {e}")

    if st.sidebar.button("Reset"):
        st.experimental_rerun()


if __name__ == "__main__":
    main()
