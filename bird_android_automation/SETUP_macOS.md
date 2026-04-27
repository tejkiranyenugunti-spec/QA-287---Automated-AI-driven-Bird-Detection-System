# SETUP macOS — Bird Android Automation (Merlin Bird ID)

This guide assumes you are starting from zero with ADB/Appium on macOS.

## 1) Install Homebrew (if needed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew --version
```

## 2) Install Node.js (required for Appium)

```bash
brew install node
node --version
npm --version
```

## 3) Install Java JDK 17

```bash
brew install --cask zulu@17
java -version
```

Add this to `~/.zshrc`:

```bash
export JAVA_HOME=$(/usr/libexec/java_home -v 17)
export PATH="$JAVA_HOME/bin:$PATH"
```

Then reload:

```bash
source ~/.zshrc
```

## 4) Install Android Studio + SDK tools

```bash
brew install --cask android-studio
```

Open Android Studio, then:

- `Tools -> SDK Manager`
- Install **Android API 34**
- Install **Android SDK Platform-Tools**

Add these lines to `~/.zshrc`:

```bash
export ANDROID_SDK_ROOT="$HOME/Library/Android/sdk"
export PATH="$ANDROID_SDK_ROOT/platform-tools:$ANDROID_SDK_ROOT/emulator:$PATH"
```

Reload shell:

```bash
source ~/.zshrc
```

## 5) Verify ADB

```bash
adb --version
adb devices
```

It is okay if `adb devices` is empty before the emulator starts.

## 6) Create an AVD

- Open Android Studio -> `Device Manager` -> `Create Virtual Device`
- Hardware profile: **Pixel 6**
- System image: **API 34 (Android 14, Google APIs)**
- AVD name: `Pixel_6_API_34`

If you choose a different AVD name, update `DEVICE_CONFIG["deviceName"]` in `config.py`.

## 7) Boot the emulator

Either launch from Android Studio Device Manager, or use:

```bash
emulator -avd Pixel_6_API_34
```

Wait for the home screen, then verify:

```bash
adb devices
```

Expected: `emulator-5554 device`

## 8) Install Appium

```bash
npm install -g appium
appium --version
```

Version should be Appium 2.x.

## 9) Install UiAutomator2 driver

```bash
appium driver install uiautomator2
appium driver list --installed
```

## 10) Install and run appium-doctor

```bash
npm install -g appium-doctor
appium-doctor --android
```

Fix any ❌ findings before continuing.

## 11) Start Appium server

Use a dedicated terminal and leave it running:

```bash
appium --base-path /
```

## 12) Install Merlin Bird ID on emulator

Preferred:
- Open Google Play Store in emulator
- Sign in with a test Google account
- Search and install **Merlin Bird ID**

Alternative:
- Download APK and run `adb install merlin.apk`
- Note: APKMirror is third-party and not officially endorsed.

First-launch onboarding:
- Open Merlin manually once
- Complete permissions + onboarding
- Download bird pack **United States: Continental US**  
  (large download; only once because `noReset=True`).

## 13) Place test images and generate augmentations

Put these files into `bird_augmentation/samples/original/`:

- `rock_pigeon_1.jpg`
- `house_sparrow_1.jpg`
- `american_crow_1.jpg`
- `scarlet_macaw_1.jpg`
- `bald_eagle_1.jpg`

Generate augmented images:

```bash
cd bird_augmentation
python generate_samples.py
```

## 14) Install Python dependencies for Phase 3

```bash
cd bird_android_automation
pip install -r requirements.txt
```

## 15) Run preflight checks

```bash
python main.py --doctor
```

All checks should be ✅.

## 16) Run one test first

```bash
python main.py --test-id TC001
```

Watch emulator behavior: open Merlin, tap Photo ID, choose image, wait for result, return.

## 17) Generate augmented cases and run full suite

```bash
python main.py --generate-augmented-cases
python main.py
```

Expected full run size once augmented rows are generated: 40 tests.

## Troubleshooting

### Selectors not finding elements

Dump live UI:

```bash
adb shell uiautomator dump /sdcard/ui_dump.xml
adb pull /sdcard/ui_dump.xml ./test_results/
```

Inspect XML and update selector fallbacks in `config.SELECTORS_MERLIN`.

### Image does not appear in gallery

Verify media scan broadcast is executed, then try:

```bash
adb shell content scan --uri file:///sdcard/Pictures/BirdTest
```

### Merlin asks for region/bird pack during test run

Re-run Step 12 manually in the emulator and complete onboarding/pack download.
