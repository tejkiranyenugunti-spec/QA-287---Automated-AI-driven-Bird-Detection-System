"""Weather augmentation package for bird image transformations."""

from .augmentor import WeatherAugmentor
from .classifier import WeatherClassifier

__all__ = ["WeatherAugmentor", "WeatherClassifier"]
