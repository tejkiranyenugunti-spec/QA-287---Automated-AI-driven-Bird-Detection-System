# Bird Weather Augmentation Framework

CMPE 287 — Team QA Sentinels (Tej Kiran Yenugunti, Mani Mokshith Noonety, Krishna Sai Akhil Nanduri)

## Purpose

Phase 2 of our test automation framework for bird species identification apps. This tool generates reproducible synthetic weather conditions on bird images so we can extend the manual test coverage from our Conventional Test Design Document into augmented-data scenarios — closing the gaps in our environmental condition matrix (Fog, Rain, Partial Visibility) and supporting reproducible regression testing.

## Apps Under Test

- Merlin Bird ID (Cornell Lab of Ornithology)
- Seek by iNaturalist (California Academy of Sciences)
- iNaturalist

## Quickstart

```bash
pip install -r requirements.txt

# Drop bird images into samples/original/

# Interactive UI:
streamlit run demo.py

# OR batch generation (all 7 effects on every image):
python generate_samples.py
```

## Effects Supported

Seven environmental effects, each at three intensity levels (low, medium, high):

- **Rain** — diagonal streaks, slight brightness drop
- **Snow** — overlay snowflakes, brightness shift
- **Fog** — reduced contrast, atmospheric haze
- **Night** — darken + slight desaturation
- **Sunny** — brighten + optional lens flare
- **Autumn** — warm color shift (red/orange tones)
- **Motion Blur** — directional blur for movement/wind/camera shake

Effects can be applied individually or chained (multi-select in UI).

## Components

- `weather_aug/augmentor.py` — `WeatherAugmentor` class wrapping Albumentations transforms
- `weather_aug/classifier.py` — `WeatherClassifier`, a rule-based test oracle
- `demo.py` — Streamlit UI with Old/New comparison, prediction shift detection, auto-save, logging
- `generate_samples.py` — headless batch script for full-folder augmentation
- `logs/augmentations.log` — timestamped log of every augmentation operation

## Note on the Weather Classifier

The `WeatherClassifier` is a **rule-based oracle**, not a trained CNN. It scores five weather classes (cloudy, fogsmog, rain, shine, sunrise) using simple image statistics — mean brightness, contrast (standard deviation), and RGB channel means. Its purpose is to demonstrate prediction shift caused by augmentation, not to provide ground-truth weather classification. When the augmented image's top class changes or its confidence shifts by more than 5%, the UI flags it — that signal is what we use to evaluate how aggressive an augmentation is, not whether the weather labeling is "correct."

## How This Connects to Phase 1

Our Conventional Test Design Document executed 8 manual test cases (TC-1 through TC-8) on real bird images under natural conditions, finding that all three apps fail under dark/low-light and blur conditions. Phase 2 (this tool) lets us generate those same conditions synthetically and reproducibly, so we can extend coverage to the "To Test" rows in our Section 2.4 environmental matrix (Fog Overlay, Rain Overlay, Partial Visibility) and produce regression-testable augmented datasets.
