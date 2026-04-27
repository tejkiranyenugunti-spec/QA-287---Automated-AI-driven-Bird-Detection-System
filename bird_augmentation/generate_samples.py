"""Batch weather augmentation generator for bird image samples."""

from __future__ import annotations

import glob
import os
from datetime import datetime

import cv2

from weather_aug import WeatherAugmentor

SAMPLES_ORIGINAL_DIR = os.path.join("samples", "original")
SAMPLES_AUGMENTED_DIR = os.path.join("samples", "augmented")
EFFECTS = ["rain", "snow", "fog", "night", "sunny", "autumn", "motion_blur"]


def ensure_dirs() -> None:
    os.makedirs(SAMPLES_ORIGINAL_DIR, exist_ok=True)
    os.makedirs(SAMPLES_AUGMENTED_DIR, exist_ok=True)
    os.makedirs("logs", exist_ok=True)


def log_augmentation(effect: str, filename: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_path = os.path.join("logs", "augmentations.log")
    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"{ts} | Effect: {effect} | File: {filename}\n")


def generate_samples() -> None:
    ensure_dirs()
    patterns = ["*.png", "*.jpg", "*.jpeg", "*.PNG", "*.JPG", "*.JPEG"]
    image_paths: list[str] = []
    for pattern in patterns:
        image_paths.extend(glob.glob(os.path.join(SAMPLES_ORIGINAL_DIR, pattern)))

    if not image_paths:
        print(
            f"No images found in {SAMPLES_ORIGINAL_DIR}. "
            "Please add bird images and try again."
        )
        return

    augmentor = WeatherAugmentor(intensity="medium")

    for img_path in image_paths:
        image_bgr = cv2.imread(img_path)
        if image_bgr is None:
            print(f"Skipping unreadable image: {img_path}")
            continue

        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        base_name = os.path.splitext(os.path.basename(img_path))[0]

        for effect in EFFECTS:
            try:
                aug_rgb = augmentor.apply_effect(image_rgb, effect)
                aug_bgr = cv2.cvtColor(aug_rgb, cv2.COLOR_RGB2BGR)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                out_filename = f"{base_name}_{effect}_{ts}.png"
                out_path = os.path.join(SAMPLES_AUGMENTED_DIR, out_filename)
                cv2.imwrite(out_path, aug_bgr)
                print(f"Saved {effect} image to {out_path}")
                log_augmentation(effect, os.path.basename(img_path))
            except Exception as e:  # noqa: BLE001
                print(f"Failed to apply {effect} to {img_path}: {e}")


if __name__ == "__main__":
    generate_samples()
