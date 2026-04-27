"""CLI entry point for Merlin Bird ID Android automation."""

from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from config import APPIUM_SERVER_URL, ORIGINAL_IMAGES_DIR
from test_data_manager import TestDataManager
from test_runner import TestRunner

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def run_doctor() -> int:
    """Run preflight checks and print pass/fail status lines."""
    checks_ok = True

    adb_ok = shutil.which("adb") is not None
    print(f"{'✅' if adb_ok else '❌'} adb on PATH")
    checks_ok = checks_ok and adb_ok

    online_device = False
    if adb_ok:
        try:
            proc = subprocess.run(
                ["adb", "devices"], check=True, capture_output=True, text=True, timeout=15
            )
            lines = proc.stdout.strip().splitlines()[1:]
            online_device = any("\tdevice" in line for line in lines)
        except Exception as exc:
            logger.error("Failed running adb devices: %s", exc)
            online_device = False
    print(f"{'✅' if online_device else '❌'} at least one online emulator/device")
    checks_ok = checks_ok and online_device

    appium_ok = False
    try:
        req = Request(f"{APPIUM_SERVER_URL}/status", method="GET")
        with urlopen(req, timeout=5) as response:
            appium_ok = 200 <= response.status < 300
    except URLError:
        appium_ok = False
    except Exception as exc:
        logger.error("Unexpected Appium status check failure: %s", exc)
        appium_ok = False
    print(f"{'✅' if appium_ok else '❌'} Appium reachable at {APPIUM_SERVER_URL}")
    checks_ok = checks_ok and appium_ok

    originals_ok = Path(ORIGINAL_IMAGES_DIR).exists()
    print(f"{'✅' if originals_ok else '❌'} Phase 2 originals directory exists ({ORIGINAL_IMAGES_DIR})")
    checks_ok = checks_ok and originals_ok

    return 0 if checks_ok else 1


def list_images(data_manager: TestDataManager) -> None:
    """Print available original and augmented images."""
    originals = data_manager.list_available_images("original")
    augmented = data_manager.list_available_images("augmented")
    print("Original images:")
    for name in originals:
        print(f"  - {name}")
    print("Augmented images:")
    for name in augmented:
        print(f"  - {name}")


def generate_augmented_cases(data_manager: TestDataManager) -> None:
    """Generate augmented CSV rows from defaults and print additions count."""
    species_image_map = {
        "rock_pigeon": ["rock_pigeon_1.jpg"],
        "house_sparrow": ["house_sparrow_1.jpg"],
        "american_crow": ["american_crow_1.jpg"],
        "scarlet_macaw": ["scarlet_macaw_1.jpg"],
        "bald_eagle": ["bald_eagle_1.jpg"],
    }
    effects = ["rain", "snow", "fog", "night", "sunny", "autumn", "motion_blur"]
    added = data_manager.generate_augmented_test_cases(species_image_map, effects)
    print(f"Added {added} augmented test case rows.")


def main() -> int:
    """Parse CLI args and run requested operation."""
    parser = argparse.ArgumentParser(description="Bird Android automation for Merlin Bird ID.")
    parser.add_argument("--test-id", help="Run only a single test case by test_id.")
    parser.add_argument("--list-images", action="store_true", help="List original/augmented images.")
    parser.add_argument(
        "--generate-augmented-cases",
        action="store_true",
        help="Append augmented test rows to CSV.",
    )
    parser.add_argument(
        "--push-all-images",
        action="store_true",
        help="Push all Phase 2 images (originals + augmented) to emulator gallery and exit",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive mode: you pick images in Merlin manually, script observes Merlin output",
    )
    parser.add_argument(
        "--expected",
        type=str,
        default=None,
        help="(Interactive mode, optional) Expected species key for pass/fail classification",
    )
    parser.add_argument("--doctor", action="store_true", help="Run preflight diagnostics.")
    args = parser.parse_args()

    data_manager = TestDataManager()

    if args.doctor:
        return run_doctor()
    if args.list_images:
        list_images(data_manager)
        return 0
    if args.generate_augmented_cases:
        generate_augmented_cases(data_manager)
        return 0

    if args.push_all_images:
        runner = TestRunner()
        try:
            if not runner.setup():
                return 1
            if runner.interactions is None:
                return 1
            push_result = runner.interactions.push_all_test_images()
            print(push_result)
            return 0
        finally:
            runner.teardown()

    if args.interactive:
        runner = TestRunner()
        results: list[dict[str, object]] = []
        if not runner.setup():
            sys.exit(1)
        try:
            results = runner.run_interactive_mode(initial_expected=args.expected)
        finally:
            if results:
                runner.generate_report(results)
            runner.teardown()
        sys.exit(0)

    runner = TestRunner()
    test_cases = data_manager.load_test_cases()
    if args.test_id:
        test_cases = [case for case in test_cases if case.get("test_id") == args.test_id]
        if not test_cases:
            print(f"No test found with test_id={args.test_id}")
            return 1

    try:
        runner.setup()
        results = runner.run_all_tests(test_cases)
    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt received. Writing partial report.")
        partial_results = runner.test_results
        if partial_results:
            runner.generate_report(partial_results)
        return 130
    finally:
        runner.teardown()

    runner.generate_report(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
