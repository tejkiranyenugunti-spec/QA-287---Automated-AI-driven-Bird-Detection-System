"""Orchestrates the test run: setup, per-test execution, teardown, report generation."""

from __future__ import annotations

import json
import logging
import subprocess
import time
from datetime import datetime
from pathlib import Path

from app_driver import AppDriver
from app_interactions_merlin import MerlinInteractions
from config import DEVICE_CONFIG, DEVICE_IMAGE_DIR, EXPECTED_SPECIES_KEYWORDS, TEST_REPORTS_DIR, TEST_RESULTS_DIR
from result_classifier import ResultClassifier
from test_data_manager import TestDataManager

logger = logging.getLogger(__name__)


class TestRunner:
    """Coordinates setup, execution, and report output for Merlin automation."""

    def __init__(self) -> None:
        self.driver = AppDriver()
        self.classifier = ResultClassifier()
        self.data_manager = TestDataManager()
        self.interactions: MerlinInteractions | None = None
        self.test_results: list[dict[str, object]] = []
        self.device_id = DEVICE_CONFIG["udid"]

    def setup(self) -> bool:
        """Start driver, initialize interactions, and create output folders."""
        Path(TEST_RESULTS_DIR).mkdir(parents=True, exist_ok=True)
        Path(TEST_REPORTS_DIR).mkdir(parents=True, exist_ok=True)
        started = self.driver.start_driver()
        self.interactions = MerlinInteractions(self.driver)
        self.interactions.handle_first_run_dialogs()
        return started

    def teardown(self) -> None:
        """Stop underlying Appium driver."""
        self.driver.stop_driver()

    def run_single_test(self, test_case: dict[str, str]) -> dict[str, object]:
        """Execute one test case end-to-end and return result payload."""
        if self.interactions is None:
            raise RuntimeError("TestRunner is not set up. Call setup() before running tests.")

        test_id = test_case.get("test_id", "UNKNOWN")
        image_name = test_case.get("image_name", "")
        image_type = test_case.get("image_type", "")
        augmentation = test_case.get("augmentation", "none")
        expected_species = test_case.get("expected_species", "")
        timestamp = datetime.now().isoformat()

        before_path = str(Path(TEST_RESULTS_DIR) / f"screenshot_before_{test_id}.png")
        after_path = str(Path(TEST_RESULTS_DIR) / f"screenshot_after_{test_id}.png")

        result: dict[str, object] = {
            "test_id": test_id,
            "image_name": image_name,
            "image_type": image_type,
            "augmentation": augmentation,
            "expected_species": expected_species,
            "timestamp": timestamp,
            "status": "error",
            "app_result": None,
            "classification": None,
            "screenshot_before": before_path,
            "screenshot_after": after_path,
            "error": None,
        }

        try:
            image_path = self.data_manager.get_image_path(image_name, image_type)
            if not image_path.exists():
                raise FileNotFoundError(f"Image file not found: {image_path}")

            self.driver.take_screenshot(before_path)

            check_result = subprocess.run(
                [
                    "adb",
                    "-s",
                    self.device_id,
                    "shell",
                    "ls",
                    f"{DEVICE_IMAGE_DIR}/{image_name}",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if check_result.returncode != 0:
                logger.error(
                    "Image %s not on device — run `python main.py --push-all-images` first",
                    image_name,
                )
                return {
                    "test_id": test_case["test_id"],
                    "image_name": image_name,
                    "status": "error",
                    "error": f"Image not on device: {image_name}",
                    "classification": None,
                    "app_result": None,
                }

            if not self.interactions.navigate_to_photo_id():
                raise RuntimeError("Could not navigate to Merlin Photo ID.")

            if not self.interactions.pick_photo_from_gallery(f"{DEVICE_IMAGE_DIR}/{image_name}"):
                raise RuntimeError("Could not select test image from gallery.")

            self.interactions.wait_for_analysis_complete(max_wait=120)
            app_result = self.interactions.extract_result()
            classification = self.classifier.classify_result(app_result, expected_species)

            self.driver.take_screenshot(after_path)
            self.interactions.reset_for_next_test()

            result["app_result"] = app_result
            result["classification"] = classification
            result["status"] = (
                "passed" if classification.get("category") == "correct_species" else "failed"
            )
            logger.info("Completed test %s with status %s", test_id, result["status"])
            return result
        except KeyboardInterrupt:
            result["status"] = "interrupted"
            result["error"] = "Interrupted by user"
            self.driver.take_screenshot(after_path)
            logger.warning("Test %s interrupted by user.", test_id)
            raise
        except Exception as exc:
            result["status"] = "error"
            result["error"] = str(exc)
            self.driver.take_screenshot(after_path)
            logger.exception("Test %s failed with error.", test_id)
            return result

    def run_all_tests(self, test_cases: list[dict[str, str]]) -> list[dict[str, object]]:
        """Run all test cases and persist partial progress on interruption."""
        self.test_results = []
        for case in test_cases:
            try:
                test_result = self.run_single_test(case)
                self.test_results.append(test_result)
                time.sleep(1)
            except KeyboardInterrupt:
                interrupted_result = {
                    "test_id": case.get("test_id", "UNKNOWN"),
                    "image_name": case.get("image_name", ""),
                    "image_type": case.get("image_type", ""),
                    "augmentation": case.get("augmentation", "none"),
                    "expected_species": case.get("expected_species", ""),
                    "timestamp": datetime.now().isoformat(),
                    "status": "interrupted",
                    "app_result": None,
                    "classification": None,
                    "screenshot_before": None,
                    "screenshot_after": None,
                    "error": "Interrupted by user",
                }
                self.test_results.append(interrupted_result)
                logger.warning("Run interrupted after %s completed tests.", len(self.test_results))
                raise
        return self.test_results

    def run_interactive_mode(self, initial_expected: str | None = None) -> list[dict[str, object]]:
        """Interactive loop where user manually picks images in Merlin."""
        if self.interactions is None:
            raise RuntimeError("TestRunner is not set up. Call setup() before interactive mode.")

        print("\n" + "=" * 70)
        print("INTERACTIVE MODE")
        print("=" * 70)
        print("How this works:")
        print("  1. The emulator is already showing Merlin Bird ID.")
        print("  2. YOU tap 'Photo ID' (or whichever flow) in Merlin.")
        print("  3. YOU pick the image you want to test from the gallery.")
        print("  4. Wait for Merlin to show its identification result.")
        print("  5. Press ENTER here and the script reads what Merlin identified.")
        print("  6. Optional: pass --expected <species_key> to enable pass/fail classification.")
        print("  6. After each test, you can run another or quit.")
        print("=" * 70)

        results: list[dict[str, object]] = []
        test_count = 1
        valid_species = set(EXPECTED_SPECIES_KEYWORDS.keys())
        result_classifier = self.classifier

        expected_species = initial_expected
        if expected_species and expected_species not in valid_species:
            print(f"WARNING: unknown --expected '{expected_species}', ignoring.")
            expected_species = None

        correct_count = 0
        total_count = 0

        while True:
            if not expected_species:
                print("\nAvailable species keys:")
                for species_key in sorted(valid_species):
                    print(f"  {species_key}")
                expected_input = input("\nEnter expected species key (or 'q' to quit): ").strip()
                if expected_input.lower() in ("q", "quit", "exit", ""):
                    break
                if expected_input not in valid_species:
                    print(f"  WARNING: Unknown species key '{expected_input}'. Try again.")
                    continue
                expected_species = expected_input

            print(f"\n--- Interactive Test #{test_count} ---")
            if expected_species:
                print(f"Expected species: {expected_species}")
            else:
                print("Expected species: not set (observation-only mode)")

            print(f"\n  -> Now go to the emulator. Pick an image of '{expected_species}' in Merlin.")
            input("  -> Press ENTER here AFTER Merlin has shown the identification result...")

            print("  Reading Merlin's screen...")
            time.sleep(1.0)
            app_result = self.interactions.extract_result()

            classification_obj = result_classifier.classify_result(
                app_result,
                expected_species,
            )
            classification = str(classification_obj.get("category"))

            if classification == "correct_species":
                status = "PASS"
                correct_count += 1
            else:
                status = "FAIL"
            total_count += 1

            test_id = f"INT_{test_count:03d}"
            result: dict[str, object] = {
                "test_id": test_id,
                "image_name": "interactive",
                "image_type": "interactive",
                "augmentation": "user_selected",
                "expected_species": expected_species,
                "timestamp": datetime.now().isoformat(),
                "status": "passed" if status == "PASS" else "failed",
                "app_result": app_result,
                "classification": classification_obj,
                "screenshot_before": None,
                "screenshot_after": None,
                "error": None,
            }

            screenshot_path = f"{TEST_RESULTS_DIR}/screenshot_{test_id}.png"
            self.driver.take_screenshot(screenshot_path)
            result["screenshot_after"] = screenshot_path

            results.append(result)
            self.test_results.append(result)

            print()
            print(f"Expected:        {expected_species}")
            print(f"Merlin said:     {app_result}")
            print(f"Classification:  {classification}")
            print(f"STATUS:          {status}")
            print(f"  Screenshot:      {screenshot_path}")

            again = input("\n  Run another interactive test? (y/n): ").strip().lower()
            if again != "y":
                break

            print("  Resetting Merlin to home...")
            self.interactions.reset_for_next_test()
            time.sleep(1.5)
            test_count += 1
            if initial_expected is None:
                expected_species = None

        accuracy = (correct_count / total_count) * 100 if total_count > 0 else 0
        print(f"\nFinal Accuracy: {accuracy:.2f}%")

        return results

    def generate_report(self, results: list[dict[str, object]]) -> dict[str, object]:
        """Generate report payload and write it as a timestamped JSON file."""
        classifications = [r["classification"] for r in results if r.get("classification")]
        summary = self.classifier.summarize(classifications)  # type: ignore[arg-type]

        by_augmentation: dict[str, dict[str, int]] = {}
        by_species: dict[str, dict[str, int]] = {}

        for item in results:
            augmentation = str(item.get("augmentation", "none"))
            species = str(item.get("expected_species", "unknown"))
            status = str(item.get("status", "error"))

            if augmentation not in by_augmentation:
                by_augmentation[augmentation] = {"total": 0, "passed": 0, "failed": 0}
            by_augmentation[augmentation]["total"] += 1
            if status == "passed":
                by_augmentation[augmentation]["passed"] += 1
            elif status == "failed":
                by_augmentation[augmentation]["failed"] += 1

            if species not in by_species:
                by_species[species] = {"total": 0, "passed": 0, "failed": 0}
            by_species[species]["total"] += 1
            if status == "passed":
                by_species[species]["passed"] += 1
            elif status == "failed":
                by_species[species]["failed"] += 1

        report = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(results),
            "summary": summary,
            "test_results": results,
            "by_augmentation": by_augmentation,
            "by_species": by_species,
        }

        Path(TEST_REPORTS_DIR).mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = Path(TEST_REPORTS_DIR) / f"test_report_{ts}.json"
        with report_path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, default=str)

        accuracy = summary.get("accuracy", 0.0)
        print(f"Report generated: {report_path} | accuracy={accuracy}%")
        return report
