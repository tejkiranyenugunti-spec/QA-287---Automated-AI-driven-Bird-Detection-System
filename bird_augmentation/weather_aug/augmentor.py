"""Albumentations-based weather augmentation utilities."""

from __future__ import annotations

from typing import Any

import numpy as np


class WeatherAugmentor:
    """Applies configurable synthetic weather effects to RGB images."""

    _VALID_INTENSITIES = {"low", "medium", "high"}

    def __init__(self, intensity: str = "medium", seed: int | None = None) -> None:
        if intensity not in self._VALID_INTENSITIES:
            raise ValueError("Intensity must be one of: low, medium, high.")

        try:
            import albumentations as A  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "Albumentations is required. Install dependencies with: "
                "pip install -r requirements.txt"
            ) from exc

        self.A = A
        self.intensity = intensity
        self.seed = seed

    def _apply(self, image: np.ndarray, transform: Any) -> np.ndarray:
        if image is None:
            raise ValueError("Input image cannot be None.")

        if image.dtype != np.uint8:
            image = image.astype(np.uint8)

        if self.seed is not None:
            old_state = np.random.get_state()
            np.random.seed(self.seed)
            try:
                return transform(image=image)["image"]
            finally:
                np.random.set_state(old_state)

        return transform(image=image)["image"]

    def _build_rain(self) -> Any:
        params = {
            "low": {"drop_length": 10, "blur_value": 3, "brightness": 0.8},
            "medium": {"drop_length": 15, "blur_value": 5, "brightness": 0.7},
            "high": {"drop_length": 20, "blur_value": 7, "brightness": 0.6},
        }[self.intensity]
        return self.A.Compose(
            [
                self.A.RandomRain(
                    slant_lower=-10,
                    slant_upper=10,
                    drop_length=params["drop_length"],
                    drop_width=1,
                    drop_color=(200, 200, 200),
                    blur_value=params["blur_value"],
                    brightness_coefficient=params["brightness"],
                    p=1.0,
                )
            ]
        )

    def _build_snow(self) -> Any:
        params = {
            "low": {"brightness": (0.1, 0.2), "density": 0.05},
            "medium": {"brightness": (0.2, 0.3), "density": 0.1},
            "high": {"brightness": (0.3, 0.4), "density": 0.2},
        }[self.intensity]
        return self.A.Compose(
            [
                self.A.RandomSnow(
                    snow_point_lower=0.1,
                    snow_point_upper=params["density"],
                    brightness_coeff=float(np.mean(params["brightness"])),
                    p=1.0,
                )
            ]
        )

    def _build_fog(self) -> Any:
        params = {
            "low": {"fog_coef": 0.2, "alpha_coef": 0.1},
            "medium": {"fog_coef": 0.35, "alpha_coef": 0.15},
            "high": {"fog_coef": 0.5, "alpha_coef": 0.2},
        }[self.intensity]
        return self.A.Compose(
            [
                self.A.RandomFog(
                    fog_coef_lower=params["fog_coef"] * 0.8,
                    fog_coef_upper=params["fog_coef"],
                    alpha_coef=params["alpha_coef"],
                    p=1.0,
                )
            ]
        )

    def _build_night(self) -> Any:
        params = {
            "low": {"brightness": (-0.1, -0.2), "contrast": (0.0, 0.1)},
            "medium": {"brightness": (-0.2, -0.3), "contrast": (0.0, 0.15)},
            "high": {"brightness": (-0.3, -0.4), "contrast": (0.0, 0.2)},
        }[self.intensity]
        return self.A.Compose(
            [
                self.A.RandomBrightnessContrast(
                    brightness_limit=params["brightness"],
                    contrast_limit=params["contrast"],
                    p=1.0,
                ),
                self.A.HueSaturationValue(
                    hue_shift_limit=5,
                    sat_shift_limit=-10,
                    val_shift_limit=-10,
                    p=1.0,
                ),
            ]
        )

    def _build_sunny(self) -> Any:
        params = {
            "low": {"brightness": (0.1, 0.2), "contrast": (0.0, 0.1)},
            "medium": {"brightness": (0.2, 0.3), "contrast": (0.05, 0.15)},
            "high": {"brightness": (0.3, 0.4), "contrast": (0.1, 0.2)},
        }[self.intensity]
        return self.A.Compose(
            [
                self.A.RandomBrightnessContrast(
                    brightness_limit=params["brightness"],
                    contrast_limit=params["contrast"],
                    p=1.0,
                ),
                self.A.RandomSunFlare(
                    flare_roi=(0.0, 0.0, 1.0, 0.5),
                    angle_lower=0.0,
                    angle_upper=1.0,
                    num_flare_circles_lower=3,
                    num_flare_circles_upper=6,
                    src_radius=50,
                    src_color=(255, 255, 255),
                    p=0.5,
                ),
            ]
        )

    def _build_autumn(self) -> Any:
        params = {
            "low": {"r_shift": (10, 20), "g_shift": (0, 10), "b_shift": (-10, 0)},
            "medium": {
                "r_shift": (20, 30),
                "g_shift": (5, 15),
                "b_shift": (-20, -10),
            },
            "high": {
                "r_shift": (30, 50),
                "g_shift": (10, 20),
                "b_shift": (-30, -10),
            },
        }[self.intensity]
        return self.A.Compose(
            [
                self.A.RGBShift(
                    r_shift_limit=params["r_shift"],
                    g_shift_limit=params["g_shift"],
                    b_shift_limit=params["b_shift"],
                    p=1.0,
                ),
                self.A.ColorJitter(
                    brightness=0.1,
                    contrast=0.1,
                    saturation=0.2,
                    hue=0.05,
                    p=0.5,
                ),
            ]
        )

    def _build_motion_blur(self) -> Any:
        blur_limit = {"low": 5, "medium": 15, "high": 30}[self.intensity]
        return self.A.Compose([self.A.MotionBlur(blur_limit=blur_limit, p=1.0)])

    def apply_rain(self, image: np.ndarray) -> np.ndarray:
        return self._apply(image, self._build_rain())

    def apply_snow(self, image: np.ndarray) -> np.ndarray:
        return self._apply(image, self._build_snow())

    def apply_fog(self, image: np.ndarray) -> np.ndarray:
        return self._apply(image, self._build_fog())

    def apply_night(self, image: np.ndarray) -> np.ndarray:
        return self._apply(image, self._build_night())

    def apply_sunny(self, image: np.ndarray) -> np.ndarray:
        return self._apply(image, self._build_sunny())

    def apply_autumn(self, image: np.ndarray) -> np.ndarray:
        return self._apply(image, self._build_autumn())

    def apply_motion_blur(self, image: np.ndarray) -> np.ndarray:
        return self._apply(image, self._build_motion_blur())

    def apply_effect(self, image: np.ndarray, effect: str) -> np.ndarray:
        effect_name = effect.lower()
        dispatch = {
            "rain": self.apply_rain,
            "snow": self.apply_snow,
            "fog": self.apply_fog,
            "night": self.apply_night,
            "sunny": self.apply_sunny,
            "autumn": self.apply_autumn,
            "motion_blur": self.apply_motion_blur,
        }
        if effect_name not in dispatch:
            raise ValueError(f"Unknown effect: {effect}")
        return dispatch[effect_name](image)
