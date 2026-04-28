"""Merlin Bird ID specific interactions: launch, navigate, upload image, scrape result."""

from __future__ import annotations

import logging
import os
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

from appium.webdriver.common.appiumby import AppiumBy

from app_driver import AppDriver
from config import (
    AUGMENTED_IMAGES_DIR,
    APP_PACKAGE,
    DEVICE_CONFIG,
    DEVICE_IMAGE_DIR,
    EXPECTED_SPECIES_KEYWORDS,
    NO_IDENTIFICATION_KEYWORDS,
    ORIGINAL_IMAGES_DIR,
    SELECTORS_MERLIN,
    UNCERTAIN_KEYWORDS,
)

logger = logging.getLogger(__name__)


class MerlinInteractions:
    """Merlin-specific interaction logic with defensive selector fallbacks."""

    def __init__(self, driver: AppDriver):
        self.driver = driver
        self.device_id = DEVICE_CONFIG["udid"]

    def _run_adb(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        cmd = ["adb", "-s", self.device_id, *args]
        logger.debug("Running ADB command: %s", " ".join(cmd))
        try:
            return subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=15)
        except subprocess.CalledProcessError as exc:
            logger.error("ADB command failed: %s", " ".join(cmd))
            logger.error("ADB stderr: %s", (exc.stderr or "").strip())
            raise
        except Exception:
            logger.exception("Unexpected ADB failure: %s", " ".join(cmd))
            raise

    def push_image_to_device(self, local_path: str) -> str:
        """Push image to emulator gallery directory and trigger media scan."""
        local_file = Path(local_path)
        if not local_file.exists():
            raise FileNotFoundError(f"Local image not found: {local_path}")

        logger.info("Preparing device image folder: %s", DEVICE_IMAGE_DIR)
        self._run_adb(["shell", "mkdir", "-p", DEVICE_IMAGE_DIR])

        logger.info("Pushing image to emulator: %s", local_file)
        self._run_adb(["push", str(local_file), f"{DEVICE_IMAGE_DIR}/"])

        device_image_path = f"{DEVICE_IMAGE_DIR}/{local_file.name}"
        logger.info("Triggering media scan for: %s", device_image_path)
        self._run_adb(
            [
                "shell",
                "am",
                "broadcast",
                "-a",
                "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
                "-d",
                f"file://{device_image_path}",
            ]
        )
        return device_image_path

    def push_all_test_images(self) -> dict[str, object]:
        """Push all original and augmented images to emulator gallery folder."""
        folders = [Path(ORIGINAL_IMAGES_DIR), Path(AUGMENTED_IMAGES_DIR)]
        patterns = ("*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG")
        files: list[Path] = []
        for folder in folders:
            if not folder.exists():
                continue
            for pattern in patterns:
                files.extend(folder.glob(pattern))

        unique_files = sorted({file.resolve() for file in files})
        pushed = 0
        failed = 0
        pushed_files: list[str] = []

        camera_dir = "/sdcard/DCIM/Camera"
        self._run_adb(["shell", "mkdir", "-p", camera_dir])
        for file_path in unique_files:
            try:
                self._run_adb(["push", str(file_path), f"{camera_dir}/{file_path.name}"])
                pushed += 1
                pushed_files.append(file_path.name)
            except Exception:
                failed += 1
                logger.exception("Failed pushing test image: %s", file_path)

        logger.info("Triggering MediaStore scan for %s", camera_dir)
        scan_script = (
            f'for f in {camera_dir}/*; do '
            f'am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE '
            f'-d "file://$f" > /dev/null 2>&1; done'
        )
        try:
            self._run_adb(["shell", scan_script])
        except Exception:
            logger.exception("MediaStore scan broadcast failed.")

        result = subprocess.run(
            ["adb", "shell", "ls", "/sdcard/DCIM/Camera"],
            capture_output=True,
            text=True,
        )
        print("Device Camera folder contents:\n", result.stdout)

        time.sleep(3)
        return {"pushed": pushed, "failed": failed, "files": pushed_files}

    def handle_first_run_dialogs(self) -> None:
        """Best-effort dismissal of common onboarding and permission dialogs."""
        common_buttons = ["Allow", "OK", "While using the app", "Continue", "Skip", "Done"]
        for label in common_buttons:
            selectors = [
                f"//*[@text='{label}']",
                f"//*[contains(@content-desc, '{label}')]",
                f"//android.widget.Button[@text='{label}']",
            ]
            element = self.driver.find_element_with_fallbacks(selectors, timeout=1)
            if element is not None:
                try:
                    element.click()
                    logger.info("Dismissed first-run dialog button: %s", label)
                    time.sleep(0.5)
                except Exception:
                    logger.debug("Failed to click first-run dialog: %s", label, exc_info=True)

    def navigate_to_photo_id(self) -> bool:
        """Open the Photo ID entry point from Merlin home."""
        logger.info("Navigating to Photo ID.")
        if self.driver.find_element_with_fallbacks(SELECTORS_MERLIN["pick_photo_button"], timeout=1):
            logger.info("Photo picker entry already visible; skipping Photo ID navigation.")
            return True

        if self.driver.driver is not None:
            for _ in range(5):
                source = self.driver.get_page_source()
                if "com.google.android.documentsui" not in source:
                    break
                logger.info("DocumentsUI detected; navigating back to Merlin.")
                try:
                    self.driver.driver.back()
                except Exception:
                    logger.debug("Back navigation from DocumentsUI failed.", exc_info=True)
                    break
                time.sleep(1)

        if self.driver.driver is not None:
            try:
                self.driver.driver.activate_app(APP_PACKAGE)
                time.sleep(1)
            except Exception:
                logger.debug("activate_app failed before Photo ID navigation.", exc_info=True)

        if self.driver.find_element_with_fallbacks(SELECTORS_MERLIN["pick_photo_button"], timeout=1):
            logger.info("Photo picker entry visible after app activation.")
            return True

        success = self.driver.click_with_fallbacks(SELECTORS_MERLIN["photo_id_entry"], timeout=5)
        if not success:
            identify_tab = [
                "//*[@content-desc='Identify']",
                "//*[@resource-id='com.labs.merlinbirdid.app:id/navigation_identify']",
                "//*[@text='Identify']",
            ]
            self.driver.click_with_fallbacks(identify_tab, timeout=2)
            success = self.driver.click_with_fallbacks(SELECTORS_MERLIN["photo_id_entry"], timeout=5)
        if success:
            time.sleep(1.5)
            logger.info("Entered Photo ID screen.")
            return True
        logger.warning("Could not find Photo ID entry.")
        return False

    def pick_photo_from_gallery(self, image_path: str) -> bool:
        """Pick an image from Android picker with deterministic folder navigation."""
        self.driver.click_with_fallbacks(SELECTORS_MERLIN["choose_photo"])
        time.sleep(1.5)

        picker_open = self.driver.wait_for_any(
            [
                "//*[@content-desc='Show roots']",
                "//*[@resource-id='com.google.android.documentsui:id/dir_list']",
                "//android.widget.TextView[contains(@text,'Recent')]",
                "//android.widget.EditText",
            ],
            timeout=5,
        )
        if not picker_open:
            logger.warning("Picker did not open, retrying choose_photo click.")
            self.driver.click_with_fallbacks(SELECTORS_MERLIN["choose_photo"])
            time.sleep(2)

        image_name = os.path.basename(image_path)
        image_stem = Path(image_name).stem

        # Optimistic: if picker remembers DCIM/Camera from a previous session,
        # we can skip drawer navigation entirely.
        if self._scroll_to_and_click_filename(image_name, image_stem):
            return True

        # Otherwise navigate explicitly through the roots drawer.
        self._navigate_picker_to_dcim_camera()
        self.driver.click_with_fallbacks(
            [
                "//*[@content-desc='List view']",
                "//*[@resource-id='com.google.android.documentsui:id/sub_menu_list']",
            ]
        )
        time.sleep(1)

        if self._scroll_to_and_click_filename(image_name, image_stem):
            return True

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dump_path = f"test_results/page_source_gallery_{ts}.xml"
        self.driver.dump_ui_to_file(dump_path)
        raise Exception(f"Could not find image {image_name} in picker")

    def _navigate_picker_to_dcim_camera(self) -> None:
        """Open roots drawer, pick internal storage, navigate to DCIM/Camera."""
        for attempt in range(3):
            self.driver.click_with_fallbacks(["//*[@content-desc='Show roots']"], timeout=2)
            time.sleep(1.2)
            if self._click_first_non_recent_root():
                logger.info("Opened device storage root on drawer attempt %s.", attempt + 1)
                break
            logger.warning("Drawer did not yield a storage root on attempt %s.", attempt + 1)
        time.sleep(1.5)

        for _ in range(3):
            if self.driver.click_with_fallbacks(
                ["//android.widget.TextView[contains(@text,'DCIM')]"], timeout=2
            ):
                break
            time.sleep(1)
        time.sleep(1.5)

        for _ in range(3):
            if self.driver.click_with_fallbacks(
                ["//android.widget.TextView[contains(@text,'Camera')]"], timeout=2
            ):
                break
            time.sleep(1)
        time.sleep(1.5)

    def _click_first_non_recent_root(self) -> bool:
        """Click the first drawer item whose label is not Recent / Downloads."""
        if self.driver.driver is None:
            return False
        try:
            roots = self.driver.driver.find_elements(
                AppiumBy.XPATH,
                "//android.widget.TextView[@resource-id='com.google.android.documentsui:id/title']",
            )
        except Exception:
            roots = []
        skip = {"recent", "downloads", "pictures"}
        for el in roots:
            try:
                label = (el.text or "").strip()
                if label and label.lower() not in skip:
                    logger.info("Tapping drawer root: %s", label)
                    el.click()
                    return True
            except Exception:
                continue
        return self.driver.click_with_fallbacks(
            [
                "//android.widget.TextView[contains(@text,'Pixel')]",
                "//android.widget.TextView[contains(@text,'sdk_gphone')]",
                "//android.widget.TextView[contains(@text,'Internal storage')]",
                "//android.widget.TextView[contains(@text,'This device')]",
                "//android.widget.TextView[contains(@text,'Phone')]",
            ],
            timeout=2,
        )

    def _scroll_to_and_click_filename(self, image_name: str, image_stem: str) -> bool:
        """Find a filename in a scrollable list by scrolling it into view, then tap it."""
        if self.driver.click_with_fallbacks(
            [
                f"//android.widget.TextView[@text='{image_name}']",
                f"//android.widget.TextView[contains(@text,'{image_name}')]",
            ],
            timeout=2,
        ):
            return True

        if self.driver.driver is None:
            return False

        candidates = [
            f'new UiScrollable(new UiSelector().scrollable(true).instance(0))'
            f'.scrollIntoView(new UiSelector().text("{image_name}"))',
            f'new UiScrollable(new UiSelector().scrollable(true).instance(0))'
            f'.scrollIntoView(new UiSelector().textContains("{image_stem}"))',
        ]
        for ua in candidates:
            try:
                element = self.driver.driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, ua)
                element.click()
                return True
            except Exception:
                logger.debug("UiScrollable lookup failed for %s", ua, exc_info=True)
        return False

    def wait_for_analysis_complete(self, max_wait: int = 90) -> bool:
        """Advance past post-pick prompts (zoom/date/location) and wait for results."""
        species_keywords = {
            keyword
            for keywords in EXPECTED_SPECIES_KEYWORDS.values()
            for keyword in keywords
        }
        completion_keywords = species_keywords.union(NO_IDENTIFICATION_KEYWORDS).union(
            UNCERTAIN_KEYWORDS
        )
        next_step_selectors = [
            "//*[@text='Next']",
            "//*[@text='Identify']",
            "//*[@text='Get Bird ID']",
            "//*[@text='Continue']",
            "//*[@text='Done']",
            "//*[contains(@text,'Get Bird')]",
            "//android.widget.Button[@text='Next']",
            "//android.widget.Button[@text='Identify']",
        ]

        logger.info("Waiting for Merlin analysis to complete (max_wait=%ss).", max_wait)
        start = time.time()
        zoom_handled = False
        while time.time() - start <= max_wait:
            full_text = self.driver.get_all_text_on_screen()
            if any(keyword in full_text for keyword in completion_keywords):
                logger.info("Analysis completion keyword detected.")
                time.sleep(1.5)
                return True
            if not zoom_handled and "zoom" in full_text:
                self._double_tap_to_zoom_out()
                zoom_handled = True
                time.sleep(0.5)
            if self.driver.click_with_fallbacks(next_step_selectors, timeout=1):
                logger.info("Tapped a post-pick advance button.")
                time.sleep(1.5)
                continue
            time.sleep(1)
        logger.warning("Timed out waiting for analysis completion.")
        return False

    def _double_tap_to_zoom_out(self) -> None:
        """Four double-taps at the screen center to zoom out the image on Merlin's zoom screen."""
        if self.driver.driver is None:
            return
        try:
            size = self.driver.driver.get_window_size()
            cx = size["width"] // 2
            cy = size["height"] // 2
            for _ in range(4):
                self.driver.driver.execute_script(
                    "mobile: doubleClickGesture", {"x": cx, "y": cy}
                )
                time.sleep(0.4)
            logger.info("Performed four double-taps at (%s, %s) to zoom out.", cx, cy)
        except Exception:
            logger.exception("Failed to double-tap for zoom-out.")

    def extract_result(self) -> dict[str, str | float | None]:
        """Extract species, confidence, full text, and raw page source."""
        species: str | None = None
        for locator in SELECTORS_MERLIN["result_species_name"]:
            species = self.driver.get_text(locator, by=AppiumBy.XPATH, timeout=2)
            if species and species.strip():
                break

        full_text = self.driver.get_all_text_on_screen()
        raw_xml = self.driver.get_page_source()

        confidence: float | None = None
        match = re.search(r"(\d{1,3})%", full_text)
        if match:
            try:
                confidence = float(int(match.group(1)))
            except ValueError:
                confidence = None

        return {
            "species": species.strip() if species else None,
            "confidence": confidence,
            "full_text": full_text,
            "raw_xml": raw_xml,
        }

    def reset_for_next_test(self) -> None:
        """Attempt to return app to a stable state for next test."""
        logger.info("Resetting app for next test.")
        for _ in range(3):
            clicked = self.driver.click_with_fallbacks(SELECTORS_MERLIN["back_button"], timeout=1)
            if not clicked and self.driver.driver is not None:
                try:
                    self.driver.driver.back()
                except Exception:
                    logger.debug("Fallback back() failed.", exc_info=True)
            time.sleep(1)

        if self.driver.driver is not None:
            try:
                self.driver.driver.activate_app(APP_PACKAGE)
                logger.info("Re-activated app package: %s", APP_PACKAGE)
            except Exception:
                logger.exception("Failed to activate app package during reset.")
