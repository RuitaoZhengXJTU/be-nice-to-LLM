#!/usr/bin/env python3
"""
COCO val2017 data loader stub -- resolves image paths/URLs only.
No scoring, no metric computation. That is Jeremy's lane.

Usage:
    loader = CocoLoader(annotations_path="path/to/instances_val2017.json")
    images = loader.get_images(limit=10)
    for img in images:
        print(img["url"], img["id"])
"""
import json
from pathlib import Path
from typing import Optional

COCO_VAL2017_URL_PREFIX = "http://images.cocodataset.org/val2017/"


class CocoLoader:
    """Minimal wrapper around a COCO annotations file.
    Resolves image URLs (or local paths) for a given set of image IDs.
    Does not load annotations beyond what is needed to map image ids.
    """

    def __init__(
        self,
        annotations_path: Optional[str] = None,
        local_images_dir: Optional[str] = None,
    ):
        """
        Args:
            annotations_path: Path to a COCO-format JSON file (e.g. instances_val2017.json).
                If None, the loader works in URL-only mode using the public CDN.
            local_images_dir: If provided, image paths are resolved as local files instead of CDN URLs.
        """
        self.local_images_dir = Path(local_images_dir) if local_images_dir else None
        self._id_to_meta: dict = {}

        if annotations_path is not None:
            with open(annotations_path) as f:
                data = json.load(f)
            for img in data.get("images", []):
                self._id_to_meta[img["id"]] = img

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve_url(self, image_id: int) -> str:
        """Return the URL or local path for a COCO image id."""
        if self.local_images_dir is not None:
            meta = self._id_to_meta.get(image_id)
            fname = meta["file_name"] if meta else f"{image_id:012d}.jpg"
            return str(self.local_images_dir / fname)
        meta = self._id_to_meta.get(image_id)
        fname = meta["file_name"] if meta else f"{image_id:012d}.jpg"
        return COCO_VAL2017_URL_PREFIX + fname

    def get_images(
        self,
        image_ids: Optional[list] = None,
        limit: Optional[int] = None,
    ) -> list:
        """Return a list of dicts with {id, url, width, height} for the requested images.

        Args:
            image_ids: Specific image IDs to return. If None, returns all loaded images.
            limit: Cap on number of images returned (applied after filtering).
        """
        if not self._id_to_meta:
            # URL-only mode: caller must supply image_ids
            if image_ids is None:
                return []
            candidates = [{"id": iid} for iid in image_ids]
        else:
            if image_ids is not None:
                candidates = [self._id_to_meta[i] for i in image_ids if i in self._id_to_meta]
            else:
                candidates = list(self._id_to_meta.values())

        if limit is not None:
            candidates = candidates[:limit]

        return [
            {
                "id": img.get("id", img.get("id")),
                "url": self.resolve_url(img.get("id")),
                "width": img.get("width"),
                "height": img.get("height"),
                "file_name": img.get("file_name"),
            }
            for img in candidates
        ]
