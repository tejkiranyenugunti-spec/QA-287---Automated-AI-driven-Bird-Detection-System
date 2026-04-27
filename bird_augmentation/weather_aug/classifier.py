"""Rule-based weather classification helpers for augmented image checks."""

from __future__ import annotations

import cv2
import numpy as np


class WeatherClassifier:
    """Lightweight rule-based weather classifier used as a test oracle.

    Analyzes simple image statistics (mean brightness, contrast as standard
    deviation, RGB channel means) to assign probability scores across five weather
    classes. The purpose is to demonstrate prediction shift caused by augmentation
    — i.e., to flag when an augmentation perturbs the image enough to change which
    weather class scores highest. This is not a trained model and should not be
    interpreted as ground-truth weather classification.
    """

    classes = ["cloudy", "fogsmog", "rain", "shine", "sunrise"]
    input_size = (224, 224)

    def predict(self, image: np.ndarray) -> dict[str, float]:
        if image.ndim == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)

        img_resized = cv2.resize(image, self.input_size)

        brightness = float(np.mean(img_resized))
        contrast = float(np.std(img_resized))
        red_channel = float(np.mean(img_resized[:, :, 0]))
        green_channel = float(np.mean(img_resized[:, :, 1]))
        blue_channel = float(np.mean(img_resized[:, :, 2]))

        _ = green_channel

        closeness_to_mid = 1.0 - abs(brightness - 120.0) / 120.0
        raw_scores = {
            "cloudy": max(0.0, closeness_to_mid * 0.6 + (1 - contrast / 50.0) * 0.4),
            "fogsmog": max(0.0, (brightness / 255.0) * 0.5 + (1 - contrast / 80.0) * 0.5),
            "rain": max(0.0, (1 - brightness / 255.0) * 0.6 + (blue_channel / 255.0) * 0.4),
            "shine": max(0.0, (brightness / 255.0) * 0.6 + (contrast / 80.0) * 0.4),
            "sunrise": max(
                0.0,
                (red_channel / 255.0) * 0.5 + ((red_channel - blue_channel) / 255.0) * 0.5,
            ),
        }

        total = sum(raw_scores.values())
        if total == 0:
            uniform = 1.0 / len(self.classes)
            return {name: uniform for name in self.classes}

        return {name: score / total for name, score in raw_scores.items()}

    def get_top_prediction(self, image: np.ndarray) -> tuple[str, float]:
        predictions = self.predict(image)
        return max(predictions.items(), key=lambda x: x[1])

    def predict_with_details(self, image: np.ndarray) -> dict[str, object]:
        predictions = self.predict(image)
        top_3 = sorted(predictions.items(), key=lambda x: x[1], reverse=True)[:3]
        predicted_class, confidence = top_3[0]
        return {
            "predictions": predictions,
            "top_3": top_3,
            "predicted_class": predicted_class,
            "confidence": confidence,
        }
