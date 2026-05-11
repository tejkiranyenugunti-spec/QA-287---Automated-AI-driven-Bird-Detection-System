# QA-287: Automated AI-Driven Bird Detection System

CMPE 287 — Team **QA Sentinels**: Tej Kiran Yenugunti, Mani Mokshith Noonety, Krishna Sai Akhil Nanduri.

A three-phase test automation framework for evaluating mobile bird-species
identification apps (Merlin Bird ID, Seek by iNaturalist, iNaturalist) under
controlled and synthetically augmented conditions.

## Phases

| Phase | What | Where |
|------:|------|-------|
| **1** | Manual testing of 8 baseline cases (TC-1 … TC-8) across natural conditions, documented in the Conventional Test Design Document | (document, not in repo) |
| **2** | **Weather augmentation framework** — generates reproducible Rain / Snow / Fog / Night / Sunny / Autumn / Motion-Blur variants of bird images using Albumentations, with a Streamlit demo UI and a rule-based prediction-shift oracle | [`bird_augmentation/`](bird_augmentation/) |
| **3** | **Android automation harness** — drives Merlin Bird ID on an Android emulator via Appium + UiAutomator2, feeds Phase 2 images, scrapes results, classifies, and emits JSON reports + screenshots | [`bird_android_automation/`](bird_android_automation/) |

## Repository layout

```
.
├── bird_augmentation/         # Phase 2 — synthetic weather augmentation
│   ├── weather_aug/           #   augmentor + rule-based classifier
│   ├── demo.py                #   Streamlit UI
│   ├── generate_samples.py    #   headless batch generator
│   └── samples/               #   original/ and augmented/ bird images
└── bird_android_automation/   # Phase 3 — Appium-based test harness
    ├── main.py                #   CLI entry point
    ├── test_runner.py         #   orchestration
    ├── app_interactions_merlin.py  # Merlin-specific UI interactions
    ├── result_classifier.py   #   correct / incorrect / no_id / uncertain
    ├── test_data/             #   bird_test_cases.csv
    └── SETUP_macOS.md         #   full Appium/emulator setup
```

## Getting started

Each subproject has its own README and `requirements.txt`. Start there:

- **Phase 2 — augmentation:** [`bird_augmentation/README.md`](bird_augmentation/README.md)
- **Phase 3 — Android automation:** [`bird_android_automation/README.md`](bird_android_automation/README.md) and [`bird_android_automation/SETUP_macOS.md`](bird_android_automation/SETUP_macOS.md)

Typical end-to-end flow:

1. Drop bird images in [`bird_augmentation/samples/original/`](bird_augmentation/samples/).
2. Run the augmentation pipeline to produce weather variants in `samples/augmented/`.
3. Boot the Android emulator + Appium, install Merlin Bird ID.
4. From `bird_android_automation/`, run `python main.py --push-all-images` to load images onto the device, then `python main.py` to execute the CSV test plan (or `--interactive` for manual driving).
5. Inspect `bird_android_automation/reports/*.json` and `test_results/` screenshots.

## Apps under test

- **Merlin Bird ID** (Cornell Lab of Ornithology) — `com.labs.merlinbirdid.app` — Phase 3 (implemented)
- **Seek by iNaturalist** (California Academy of Sciences) — Phase 3b (planned)
- **iNaturalist** — Phase 3b (planned)
