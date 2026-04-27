"""Loads test cases from CSV; resolves image paths; auto-generates augmented test cases."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from config import AUGMENTED_IMAGES_DIR, ORIGINAL_IMAGES_DIR, TEST_CASES_CSV

logger = logging.getLogger(__name__)


class TestDataManager:
    """Handles CSV-backed test data and image path resolution."""

    def load_test_cases(self) -> list[dict[str, str]]:
        """Load test cases from CSV."""
        csv_path = Path(TEST_CASES_CSV)
        if not csv_path.exists():
            logger.warning("Test case CSV not found: %s", csv_path)
            return []

        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        logger.info("Loaded %s test cases from %s", len(rows), csv_path)
        return rows

    def get_image_path(self, image_name: str, image_type: str) -> Path:
        """Resolve image path based on image_type."""
        if image_type == "original":
            return Path(ORIGINAL_IMAGES_DIR) / image_name
        if image_type == "augmented":
            return Path(AUGMENTED_IMAGES_DIR) / image_name
        raise ValueError(f"Unsupported image_type: {image_type}")

    def list_available_images(self, image_type: str = "both") -> list[str]:
        """List available image filenames from originals and/or augmented directories."""
        patterns = ("*.png", "*.jpg", "*.jpeg", "*.PNG", "*.JPG", "*.JPEG")
        image_names: list[str] = []

        target_dirs: list[Path] = []
        if image_type in ("original", "both"):
            target_dirs.append(Path(ORIGINAL_IMAGES_DIR))
        if image_type in ("augmented", "both"):
            target_dirs.append(Path(AUGMENTED_IMAGES_DIR))

        for folder in target_dirs:
            if not folder.exists():
                continue
            for pattern in patterns:
                image_names.extend(path.name for path in folder.glob(pattern))

        deduped = sorted(set(image_names))
        logger.info("Found %s images for type=%s", len(deduped), image_type)
        return deduped

    def generate_augmented_test_cases(
        self, species_image_map: dict[str, list[str]], effects: list[str]
    ) -> int:
        """Append augmented test-case rows to CSV without duplicating test IDs."""
        csv_path = Path(TEST_CASES_CSV)
        existing_rows = self.load_test_cases()
        existing_ids = {row.get("test_id", "") for row in existing_rows}

        new_rows: list[dict[str, str]] = []
        for species, images in species_image_map.items():
            for image_name in images:
                stem = Path(image_name).stem
                for idx, effect in enumerate(effects, start=1):
                    test_id = f"TC_AUG_{species}_{effect}_{idx}"
                    if test_id in existing_ids:
                        continue
                    new_rows.append(
                        {
                            "test_id": test_id,
                            "image_name": f"{stem}_{effect}.png",
                            "expected_species": species,
                            "image_type": "augmented",
                            "augmentation": effect,
                        }
                    )
                    existing_ids.add(test_id)

        if not csv_path.exists():
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "test_id",
                        "image_name",
                        "expected_species",
                        "image_type",
                        "augmentation",
                    ],
                )
                writer.writeheader()

        if new_rows:
            with csv_path.open("a", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "test_id",
                        "image_name",
                        "expected_species",
                        "image_type",
                        "augmentation",
                    ],
                )
                writer.writerows(new_rows)
            logger.info("Added %s augmented test cases to %s", len(new_rows), csv_path)
        else:
            logger.info("No new augmented test cases added.")

        return len(new_rows)
