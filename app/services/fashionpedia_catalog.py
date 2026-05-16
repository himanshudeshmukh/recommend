from __future__ import annotations

"""
Helpers for loading and querying the Fashionpedia ontology catalog.
"""

# ============================================================================
# IMPORTS
# ============================================================================

import json
import logging

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


logger = logging.getLogger(__name__)


# ============================================================================
# FASHIONPEDIA CATEGORY
# ============================================================================

@dataclass(frozen=True)
class FashionpediaCategory:
    """
    Single category entry from the Fashionpedia ontology.
    """

    Id: int
    Name: str
    Supercategory: str
    Level: int
    Taxonomy_id: str


# ============================================================================
# FASHIONPEDIA ATTRIBUTE
# ============================================================================

@dataclass(frozen=True)
class FashionpediaAttribute:
    """
    Single attribute entry from the Fashionpedia ontology.
    """

    Id: int
    Name: str
    Supercategory: str
    Level: int
    Taxonomy_id: str


# ============================================================================
# FASHIONPEDIA CATALOG
# ============================================================================

class FashionpediaCatalog:
    """
    In-memory wrapper around the Fashionpedia category and attribute catalog.
    """

    NON_PRIMARY_SUPERCATEGORIES = {
        "garment parts",
        "decorations",
        "closures",
    }

    def __init__(self, catalog_path: Path) -> None:
        """
        Load the Fashionpedia catalog from disk.
        """

        logger.info(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

        logger.info(
            "📖 Loading the Fashionpedia ontology catalog "
            "(fashion categories and attributes)..."
        )

        logger.info(
            "   File path: %s",
            catalog_path,
        )

        # Store the file path
        self._catalog_path = catalog_path

        logger.info(
            "   Reading and parsing JSON catalog file..."
        )

        # Load JSON
        catalog_payload = json.loads(
            catalog_path.read_text(encoding="utf-8")
        )

        # ====================================================================
        # LOAD CATEGORIES
        # ====================================================================

        logger.info(
            "   Indexing categories..."
        )

        self._categories_by_id = {
            int(item["id"]): FashionpediaCategory(
                Id=int(item["id"]),
                Name=str(item["name"]),
                Supercategory=str(item["supercategory"]),
                Level=int(item["level"]),
                Taxonomy_id=str(item["taxonomy_id"]),
            )
            for item in catalog_payload["categories"]
        }

        logger.info(
            "   ✅ Loaded %d categories.",
            len(self._categories_by_id),
        )

        # Reverse lookup by name
        self._categories_by_name = {
            category.Name: category
            for category in self._categories_by_id.values()
        }

        # ====================================================================
        # LOAD ATTRIBUTES
        # ====================================================================

        logger.info(
            "   Indexing attributes..."
        )

        self._attributes_by_id = {
            int(item["id"]): FashionpediaAttribute(
                Id=int(item["id"]),
                Name=str(item["name"]),
                Supercategory=str(item["supercategory"]),
                Level=int(item["level"]),
                Taxonomy_id=str(item["taxonomy_id"]),
            )
            for item in catalog_payload["attributes"]
        }

        logger.info(
            "   ✅ Loaded %d attributes.",
            len(self._attributes_by_id),
        )

        # ====================================================================
        # GROUP ATTRIBUTES BY SUPERCATEGORY
        # ====================================================================

        grouped_attributes: dict[str, list[str]] = defaultdict(list)

        for attribute in self._attributes_by_id.values():
            grouped_attributes[attribute.Supercategory].append(
                attribute.Name
            )

        self._attribute_names_by_supercategory = {
            key: sorted(value)
            for key, value in grouped_attributes.items()
        }

        logger.info(
            "   Grouped attributes into %d supercategories.",
            len(self._attribute_names_by_supercategory),
        )

        # ====================================================================
        # ATTRIBUTE VALIDATION SET
        # ====================================================================

        self._attribute_name_set = {
            attribute.Name
            for attribute in self._attributes_by_id.values()
        }

        logger.info(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

        logger.info(
            "✅ Fashionpedia catalog ready — "
            "%d categories, %d attributes loaded.",
            len(self._categories_by_id),
            len(self._attributes_by_id),
        )

        logger.info(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

    # =========================================================================
    # PROPERTIES
    # =========================================================================

    @property
    def category_count(self) -> int:
        """
        Return total category count.
        """

        return len(self._categories_by_id)

    @property
    def attribute_count(self) -> int:
        """
        Return total attribute count.
        """

        return len(self._attributes_by_id)

    # =========================================================================
    # CATEGORY HELPERS
    # =========================================================================

    def get_category(
        self,
        category_id: int,
    ) -> FashionpediaCategory:
        """
        Return category by ID.
        """

        logger.debug(
            "Looking up category by ID: %d",
            category_id,
        )

        return self._categories_by_id[category_id]

    def get_category_by_name(
        self,
        category_name: str,
    ) -> FashionpediaCategory:
        """
        Return category by name.
        """

        logger.debug(
            "Looking up category by name: '%s'",
            category_name,
        )

        return self._categories_by_name[category_name]

    def list_categories(self) -> list[FashionpediaCategory]:
        """
        Return all categories ordered by ID.
        """

        logger.debug(
            "Listing all %d categories.",
            len(self._categories_by_id),
        )

        return [
            self._categories_by_id[key]
            for key in sorted(self._categories_by_id)
        ]

    def list_primary_categories(
        self,
    ) -> list[FashionpediaCategory]:
        """
        Return categories that make sense as outfit items.
        """

        result = [
            category
            for category in self.list_categories()
            if category.Supercategory
            not in self.NON_PRIMARY_SUPERCATEGORIES
        ]

        logger.debug(
            "Found %d primary categories.",
            len(result),
        )

        return result

    # =========================================================================
    # ATTRIBUTE HELPERS
    # =========================================================================

    def get_attribute_names_for_supercategory(
        self,
        supercategory: str,
    ) -> list[str]:
        """
        Return attribute names for a supercategory.
        """

        result = list(
            self._attribute_names_by_supercategory.get(
                supercategory,
                [],
            )
        )

        logger.debug(
            "Found %d attributes for supercategory '%s'.",
            len(result),
            supercategory,
        )

        return result

    def filter_known_attribute_names(
        self,
        suggestions: list[str],
    ) -> list[str]:
        """
        Filter suggestions down to known ontology attributes.
        """

        filtered: list[str] = []

        for suggestion in suggestions:
            if (
                suggestion in self._attribute_name_set
                and suggestion not in filtered
            ):
                filtered.append(suggestion)

        logger.debug(
            "Filtered %d suggestions down to %d valid attributes.",
            len(suggestions),
            len(filtered),
        )

        return filtered