"""Classifies Merlin output as correct_species, incorrect_species, no_identification, or uncertain."""

from __future__ import annotations

import logging

from config import (
    EXPECTED_SPECIES_KEYWORDS,
    NO_IDENTIFICATION_KEYWORDS,
    UNCERTAIN_KEYWORDS,
)

logger = logging.getLogger(__name__)


class ResultClassifier:
    """Classifies app output against expected species keywords."""

    def classify_result(self, app_result: dict, expected_species: str) -> dict[str, object]:
        """Return categorized classification payload for one test result."""
        species = (app_result.get("species") or "").strip()
        full_text = (app_result.get("full_text") or "").strip()
        confidence = app_result.get("confidence")
        haystack = (species if species else full_text).lower().strip()
        expected_keywords = EXPECTED_SPECIES_KEYWORDS.get(expected_species, [])
        expected_present = any(keyword in haystack for keyword in expected_keywords)

        if any(keyword in haystack for keyword in NO_IDENTIFICATION_KEYWORDS) and not expected_present:
            return {
                "category": "no_identification",
                "reason": "Merlin reported no identification",
                "app_species": "no_match",
                "expected_species": expected_species,
                "confidence": confidence,
            }

        if any(keyword in haystack for keyword in UNCERTAIN_KEYWORDS) and not expected_present:
            return {
                "category": "uncertain",
                "reason": "Merlin output indicates uncertainty",
                "app_species": species or None,
                "expected_species": expected_species,
                "confidence": confidence,
            }

        if expected_present:
            return {
                "category": "correct_species",
                "reason": f"Merlin identified expected species ({expected_species})",
                "app_species": species or None,
                "expected_species": expected_species,
                "confidence": confidence,
            }

        if species:
            for other_species, keywords in EXPECTED_SPECIES_KEYWORDS.items():
                if other_species == expected_species:
                    continue
                if any(keyword in haystack for keyword in keywords):
                    return {
                        "category": "incorrect_species",
                        "reason": (
                            f"Merlin identified '{species}' but expected "
                            f"'{expected_species}'"
                        ),
                        "app_species": species,
                        "expected_species": expected_species,
                        "confidence": confidence,
                    }

        return {
            "category": "no_identification",
            "reason": "Could not parse Merlin output",
            "app_species": species or None,
            "expected_species": expected_species,
            "confidence": confidence,
        }

    def summarize(self, classifications: list[dict]) -> dict[str, float | int]:
        """Summarize aggregate class counts and accuracy."""
        total = len(classifications)
        counts = {
            "correct_species": 0,
            "incorrect_species": 0,
            "no_identification": 0,
            "uncertain": 0,
        }
        for item in classifications:
            category = item.get("category")
            if category in counts:
                counts[category] += 1
        accuracy = round((counts["correct_species"] / total) * 100, 2) if total else 0.0
        return {
            "total": total,
            "correct_species": counts["correct_species"],
            "incorrect_species": counts["incorrect_species"],
            "no_identification": counts["no_identification"],
            "uncertain": counts["uncertain"],
            "accuracy": accuracy,
        }
