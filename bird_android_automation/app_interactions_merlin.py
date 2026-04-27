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
                "//android.widget.TextView[contains(@text,'Browse')]",
                "//android.widget.TextView[contains(@text,'Images')]",
                "//android.widget.TextView[contains(@text,'Recent')]",
                "//android.widget.EditText",
            ],
            timeout=5,
        )

        if not picker_open:
            print("Picker did not open, retrying...")
            self.driver.click_with_fallbacks(SELECTORS_MERLIN["choose_photo"])
            time.sleep(2)

        all_text = self.driver.get_all_text_on_screen()
        print("PICKER SCREEN TEXT:\n", all_text)

        # Force picker into Browse flow and list view for filename-based selection.
        self.driver.click_with_fallbacks(["//android.widget.TextView[contains(@text,'Browse')]"])
        time.sleep(1)
        self.driver.click_with_fallbacks(
            [
                "//android.widget.TextView[contains(@text,'Internal storage')]",
                "//android.widget.TextView[contains(@text,'Pixel')]",
                "//android.widget.TextView[contains(@text,'This device')]",
            ]
        )
        time.sleep(1)
        self.driver.click_with_fallbacks(["//android.widget.TextView[contains(@text,'DCIM')]"])
        time.sleep(1)
        self.driver.click_with_fallbacks(["//android.widget.TextView[contains(@text,'Camera')]"])
        time.sleep(1)
        self.driver.click_with_fallbacks(
            [
                "//*[@content-desc='List view']",
                "//*[@resource-id='com.google.android.documentsui:id/sub_menu_list']",
            ]
        )
        time.sleep(1)

        image_name = os.path.basename(image_path)
        image_stem = Path(image_name).stem
        found = False
        for _ in range(4):
            if self.driver.click_with_fallbacks(
                [
                    f"//android.widget.TextView[contains(@text,'{image_name}')]",
                    f"//android.widget.TextView[contains(@text,'{image_stem}')]",
                    f"//*[contains(@content-desc,'{image_stem}')]",
                ]
            ):
                found = True
                break
            if self.driver.driver is not None:
                self.driver.driver.swipe(500, 1500, 500, 800, 400)
            time.sleep(1)

        if not found:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            dump_path = f"test_results/page_source_gallery_{ts}.xml"
            self.driver.dump_ui_to_file(dump_path)
            raise Exception(f"Could not find image {image_name} in picker")
        return True

    def wait_for_analysis_complete(self, max_wait: int = 30) -> bool:
        """Wait until result text indicates completion or timeout."""
        species_keywords = {
            keyword
            for keywords in EXPECTED_SPECIES_KEYWORDS.values()
            for keyword in keywords
        }
        completion_keywords = species_keywords.union(NO_IDENTIFICATION_KEYWORDS).union(
            UNCERTAIN_KEYWORDS
        )

        logger.info("Waiting for Merlin analysis to complete (max_wait=%ss).", max_wait)
        start = time.time()
        while time.time() - start <= max_wait:
            full_text = self.driver.get_all_text_on_screen()
            if any(keyword in full_text for keyword in completion_keywords):
                logger.info("Analysis completion keyword detected.")
                time.sleep(1.5)
                return True
            time.sleep(1)
        logger.warning("Timed out waiting for analysis completion.")
        return False

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
