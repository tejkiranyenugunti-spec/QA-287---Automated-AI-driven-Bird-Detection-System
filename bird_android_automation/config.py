"""Configuration for Bird ID Android automation — Merlin Bird ID."""

# --- Merlin Bird ID app ---
APP_PACKAGE = "com.labs.merlinbirdid.app"
APP_ACTIVITY = "edu.cornell.birds.merlin.onboarding.OnBoardingActivity"

# --- Appium server ---
APPIUM_SERVER_URL = "http://127.0.0.1:4723"

# --- Device (emulator) config ---
# Update udid/platformVersion after running `adb devices` and checking
# `adb shell getprop ro.build.version.release`
DEVICE_CONFIG = {
    "platformName": "Android",
    "platformVersion": "16",  # update to match your AVD's Android version
    "deviceName": "Pixel_9_Pro",  # update to match your AVD name
    "udid": "emulator-5554",  # standard emulator UDID; verify with `adb devices`
    "automationName": "UiAutomator2",
    "appPackage": APP_PACKAGE,
    "appActivity": APP_ACTIVITY,
    "noReset": True,  # don't wipe app data between runs (Merlin's bird pack download is heavy)
    "fullReset": False,
    "autoGrantPermissions": True,
    "newCommandTimeout": 1800,
}

# --- Timeouts (seconds) ---
IMPLICIT_WAIT = 5
EXPLICIT_WAIT = 10
ELEMENT_WAIT = 5

# --- Paths ---
TEST_DATA_DIR = "test_data"
TEST_CASES_CSV = f"{TEST_DATA_DIR}/bird_test_cases.csv"
TEST_RESULTS_DIR = "test_results"
TEST_REPORTS_DIR = "reports"

# Originals + augmented images live in the Phase 2 framework
ORIGINAL_IMAGES_DIR = "../bird_augmentation/samples/original"
AUGMENTED_IMAGES_DIR = "../bird_augmentation/samples/augmented"

# Where on the emulator we push images
DEVICE_IMAGE_DIR = "/sdcard/DCIM/Camera"

# --- Expected bird species (used by ResultClassifier) ---
# Map test-case "expected_species" to a list of acceptable Merlin output strings
# (case-insensitive substring match).
EXPECTED_SPECIES_KEYWORDS = {
    "rock_pigeon": ["rock pigeon", "rock dove", "columba livia"],
    "house_sparrow": ["house sparrow", "passer domesticus"],
    "american_crow": ["american crow", "corvus brachyrhynchos"],
    "scarlet_macaw": ["scarlet macaw", "ara macao"],
    "bald_eagle": ["bald eagle", "haliaeetus leucocephalus"],
}

# --- Result-classification keyword sets ---
NO_IDENTIFICATION_KEYWORDS = [
    "no match",
    "no result",
    "couldn't identify",
    "could not identify",
    "unable to identify",
    "try again",
    "no bird detected",
    "not found",
]
UNCERTAIN_KEYWORDS = [
    "best guess",
    "possibly",
    "uncertain",
    "low confidence",
    "maybe",
    "could be",
    "might be",
    "similar to",
]

# --- XPath / accessibility selectors for Merlin Bird ID ---
# These are starting points; expect to refine after first run by dumping UI
# with `adb shell uiautomator dump`. The code defends against missing selectors
# with multiple fallback strategies.
SELECTORS_MERLIN = {
    # Home screen entry to "Photo ID"
    "photo_id_entry": [
        "//*[@resource-id='com.labs.merlinbirdid.app:id/photo_id']",
        "//*[@resource-id='com.labs.merlinbirdid.app:id/photo_id_button']",
        "//*[@resource-id='com.labs.merlinbirdid.app:id/photo_id_label']",
        "//*[@text='Photo ID']",
        "//*[contains(@content-desc, 'Photo ID')]",
        "//android.widget.TextView[@text='Photo ID']",
    ],
    # Button that opens gallery / picks a photo
    "pick_photo_button": [
        "//*[@resource-id='com.labs.merlinbirdid.app:id/gallery']",
        "//*[@resource-id='com.labs.merlinbirdid.app:id/pick_photo_button']",
        "//*[@resource-id='com.labs.merlinbirdid.app:id/select_photo_button']",
        "//*[@resource-id='com.labs.merlinbirdid.app:id/photo_picker_button']",
        "//*[@resource-id='com.labs.merlinbirdid.app:id/gallery_button']",
        "//*[@text='Pick a Photo']",
        "//*[@text='Choose Photo']",
        "//*[@text='Choose photo']",
        "//*[contains(@content-desc, 'gallery')]",
        "//*[contains(@content-desc, 'pick')]",
    ],
    "choose_photo": [
        "//*[@resource-id='com.labs.merlinbirdid.app:id/gallery']",
        "//*[@text='Choose photo']",
        "//*[@text='Choose Photo']",
    ],
    # Result species name (these resource-ids are guesses — refine after first run)
    "result_species_name": [
        "//*[@resource-id='com.labs.merlinbirdid.app:id/common_name']",
        "//*[contains(@resource-id, 'common_name')]",
        "//*[contains(@resource-id, 'speciesName')]",
        "//*[contains(@resource-id, 'commonName')]",
        "//*[contains(@resource-id, 'bird_name')]",
        "//android.widget.TextView[@resource-id='com.labs.merlinbirdid.app:id/title']",
    ],
    # Generic "any large text on result screen" — used to scrape full_text fallback
    "result_any_text": [
        "//android.widget.TextView",
    ],
    # Navigation
    "back_button": [
        "//android.widget.ImageButton[@content-desc='Navigate up']",
        "//*[@content-desc='Back']",
    ],
}

# --- Logging ---
LOG_LEVEL = "INFO"
LOG_FILE = "logs/bird_android_automation.log"
