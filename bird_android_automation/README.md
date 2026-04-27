# Bird Android Test Automation — CMPE 287, QA Sentinels (Phase 3)

Automates Merlin Bird ID identification testing on an Android emulator using Appium + UiAutomator2. Feeds bird images (originals and weather-augmented variants from Phase 2) to Merlin's Photo ID feature, scrapes the result, classifies as correct/incorrect/no_id/uncertain, and writes JSON reports.

## Apps Under Test (Phase 3 scope)

- **Merlin Bird ID** (Cornell Lab of Ornithology) — `com.labs.merlinbirdid.app`

Seek by iNaturalist and iNaturalist will be added in Phase 3b.

## Quickstart

See `SETUP_macOS.md` for full setup. Once setup is done, use the commands below.

### Automated mode (CSV-driven)

```bash
# Terminal A (leave running): start Appium
appium --base-path /

# Terminal B:
cd bird_android_automation

# Optional but recommended: ensure all originals + augmented images are on emulator
../bird_augmentation/.venv/bin/python main.py --push-all-images

# Preflight checks
../bird_augmentation/.venv/bin/python main.py --doctor

# Run one test from CSV
../bird_augmentation/.venv/bin/python main.py --test-id TC001

# Run all CSV tests
../bird_augmentation/.venv/bin/python main.py
```

### Manual interactive mode (you pick image in Merlin)

```bash
# Terminal A (leave running): start Appium
appium --base-path /

# Terminal B:
cd bird_android_automation

# Observation-only interactive mode (no expected species comparison)
../bird_augmentation/.venv/bin/python main.py --interactive

# Interactive evaluation mode with expected species (PASS/FAIL)
../bird_augmentation/.venv/bin/python main.py --interactive --expected rock_pigeon
# valid expected keys:
# rock_pigeon, house_sparrow, american_crow, scarlet_macaw, bald_eagle
```

## How this connects to Phases 1 and 2

- Phase 1 was **manual** testing of TC-1 to TC-8 documented in the Conventional Test Design Document.
- Phase 2 was the **augmentation framework** in `bird_augmentation/` — generates synthetic Rain/Snow/Fog/Night/Sunny/Autumn/Motion-Blur variants of bird images.
- Phase 3 (this folder) is the **automation harness**. It reads images from Phase 2's `samples/` folders, drives Merlin via Appium, and produces reproducible test reports — turning what was 25 hours of manual testing in Phase 1 into a single command.

## Output

- `reports/test_report_<timestamp>.json` — full results, summary stats, breakdowns by augmentation and by species
- `test_results/screenshot_before_<test_id>.png` and `screenshot_after_<test_id>.png`
- `logs/bird_android_automation.log` — full execution log

## Selector maintenance

Merlin's UI may change between app versions. If selectors stop working:

```bash
adb shell uiautomator dump /sdcard/ui_dump.xml
adb pull /sdcard/ui_dump.xml ./test_results/
```

Open the XML, find the element you want by `text` or `content-desc` or `resource-id`, and update the matching list in `config.SELECTORS_MERLIN`. Each selector value is a *list* of XPaths tried in order, so add new ones without removing old ones.
