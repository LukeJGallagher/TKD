"""
Data manager for cloud annotation dashboard.
Handles loading results, thumbnails, and saving annotations.
Works with local filesystem (Azure /home/ persistent storage).
"""

import json
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from constants import TECHNIQUE_NAMES_REVERSE


def _get_data_root() -> Path:
    """Get the data root directory.
    Checks: Azure /home/ → parent/data/ → sibling data/ (standalone repo).
    """
    # Azure App Service sets WEBSITE_SITE_NAME
    if os.environ.get("WEBSITE_SITE_NAME"):
        azure_home = Path("/home/tkd_data")
        azure_home.mkdir(parents=True, exist_ok=True)
        return azure_home
    # Standard layout: dashboard_cloud/ sits inside project root
    parent_data = Path(__file__).parent.parent / "data"
    if parent_data.exists():
        return parent_data
    # Standalone repo: data/ is sibling of app.py
    sibling_data = Path(__file__).parent / "data"
    if sibling_data.exists():
        return sibling_data
    return parent_data


DATA_ROOT = _get_data_root()
RESULTS_DIR = DATA_ROOT / "results"
THUMBNAILS_DIR = DATA_ROOT / "thumbnails"
ANNOTATIONS_DIR = DATA_ROOT / "annotations"

# Fallback: local dev may have results/ at project root instead of data/results/
_PROJECT_ROOT = Path(__file__).parent.parent
_RESULTS_FALLBACK = _PROJECT_ROOT / "results"


def _results_dir() -> Path:
    """Get the results directory, checking fallback locations."""
    if RESULTS_DIR.exists() and any(RESULTS_DIR.glob("*_techniques.json")):
        return RESULTS_DIR
    if _RESULTS_FALLBACK.exists() and any(_RESULTS_FALLBACK.glob("*_techniques.json")):
        return _RESULTS_FALLBACK
    return RESULTS_DIR


def list_videos() -> List[str]:
    """List available videos (those with technique results)."""
    rdir = _results_dir()
    if not rdir.exists():
        return []
    videos = set()
    for f in rdir.glob("*_techniques.json"):
        stem = f.stem.replace("_techniques", "")
        videos.add(stem)
    return sorted(videos)


def load_techniques(video_stem: str) -> List[Dict]:
    """Load detected technique events for a video."""
    rdir = _results_dir()
    path = rdir / f"{video_stem}_techniques.json"
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_match_report(video_stem: str) -> Optional[Dict]:
    """Load match report for a video."""
    rdir = _results_dir()
    path = rdir / f"{video_stem}_match_report.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_thumbnail_path(video_stem: str, frame_num: int) -> Optional[Path]:
    """Get path to a thumbnail image for a specific frame."""
    thumb_dir = THUMBNAILS_DIR / video_stem
    if not thumb_dir.exists():
        return None
    # Try exact frame
    for ext in [".jpg", ".jpeg", ".png"]:
        p = thumb_dir / f"frame_{frame_num:06d}{ext}"
        if p.exists():
            return p
    return None


def get_box_metadata(video_stem: str, frame_num: int) -> List[Dict]:
    """Load box metadata for a thumbnail (which detections are in the frame)."""
    meta_path = THUMBNAILS_DIR / video_stem / "meta" / f"frame_{frame_num:06d}.json"
    if not meta_path.exists():
        return []
    with open(meta_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("boxes", [])


def load_annotations(video_stem: str) -> Dict:
    """Load annotations for a video. Returns the full annotation dict."""
    ANNOTATIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = ANNOTATIONS_DIR / f"{video_stem}_annotations.json"
    if not path.exists():
        # Check repo data/ fallback
        repo_path = Path(__file__).parent.parent / "data" / "annotations" / f"{video_stem}_annotations.json"
        if repo_path.exists():
            with open(repo_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"version": "1.1", "created_at": datetime.now().isoformat(),
                "num_annotations": 0, "annotations": []}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_annotations(video_stem: str, annotations_data: Dict):
    """Save annotations atomically with backup."""
    ANNOTATIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = ANNOTATIONS_DIR / f"{video_stem}_annotations.json"

    # Rolling backup
    if path.exists():
        backup = path.with_suffix(".json.bak")
        shutil.copy2(path, backup)

    # Update metadata
    annotations_data["num_annotations"] = len(annotations_data.get("annotations", []))

    # Atomic write
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(annotations_data, f, indent=2, ensure_ascii=False)
    shutil.move(str(tmp), str(path))


def add_annotation(video_stem: str, event: Dict, corrections: Dict,
                   annotated_by: str = "") -> str:
    """Add or update an annotation for an event.

    Args:
        video_stem: Video identifier
        event: Original technique event from _techniques.json
        corrections: Dict with corrected values (technique, target_zone, dimensions)
        annotated_by: Who made this annotation

    Returns:
        annotation_id
    """
    data = load_annotations(video_stem)
    annotations = data.get("annotations", [])

    start_frame = event.get("start_frame", 0)
    end_frame = event.get("end_frame", 0)
    fighter_color = corrections.get("fighter_color", event.get("fighter_color", "unknown"))

    # Check if annotation already exists for this event
    existing_idx = None
    for i, ann in enumerate(annotations):
        if (ann.get("start_frame") == start_frame and
            ann.get("end_frame") == end_frame and
            ann.get("fighter_color") == fighter_color):
            existing_idx = i
            break

    technique = corrections.get("technique", event.get("technique", "neutral_stance"))
    technique_id = TECHNIQUE_NAMES_REVERSE.get(technique, 9)

    annotation = {
        "video_path": f"{video_stem}.mp4",
        "start_frame": start_frame,
        "end_frame": end_frame,
        "fighter_color": fighter_color,
        "technique": technique,
        "technique_id": technique_id,
        "target_zone": corrections.get("target_zone", event.get("target_zone", "trunk")),
        "annotator": "verified" if existing_idx is not None else "manual",
        "source": f"confirmed_{event.get('classifier_tier', 'rule_based')}",
        "confidence": 1.0,
        "annotated_by": annotated_by,
        "notes": corrections.get("notes", ""),
        "created_at": datetime.now().isoformat(),
        "annotation_id": "",
        # Coach Mehdi 9 layers
        "attitude": corrections.get("attitude"),
        "guard_stance": corrections.get("guard_stance"),
        "role": corrections.get("role"),
        "action_type": corrections.get("action_type"),
        "leg_used": corrections.get("leg_used"),
        "scoring_value": corrections.get("scoring_value"),
        "penalty": corrections.get("penalty"),
        # Scoreboard
        "scoreboard_red": corrections.get("scoreboard_red"),
        "scoreboard_blue": corrections.get("scoreboard_blue"),
        "scoreboard_round": corrections.get("scoreboard_round"),
        # Match grouping
        "match_name": corrections.get("match_name"),
        "video_part": corrections.get("video_part"),
    }

    if existing_idx is not None:
        annotation["annotation_id"] = annotations[existing_idx].get("annotation_id", "")
        annotations[existing_idx] = annotation
    else:
        annotation["annotation_id"] = (
            f"{video_stem}_{fighter_color}_{start_frame}_{end_frame}_{uuid.uuid4().hex[:8]}"
        )
        annotations.append(annotation)

    data["annotations"] = annotations
    save_annotations(video_stem, data)
    return annotation["annotation_id"]


def delete_annotation(video_stem: str, start_frame: int, end_frame: int,
                      fighter_color: str) -> bool:
    """Delete an annotation matching the event."""
    data = load_annotations(video_stem)
    annotations = data.get("annotations", [])
    original_len = len(annotations)

    annotations = [
        a for a in annotations
        if not (a.get("start_frame") == start_frame and
                a.get("end_frame") == end_frame and
                a.get("fighter_color") == fighter_color)
    ]

    if len(annotations) < original_len:
        data["annotations"] = annotations
        save_annotations(video_stem, data)
        return True
    return False


def get_annotation_for_event(video_stem: str, start_frame: int, end_frame: int,
                             fighter_color: str) -> Optional[Dict]:
    """Find existing annotation for an event."""
    data = load_annotations(video_stem)
    for ann in data.get("annotations", []):
        if (ann.get("start_frame") == start_frame and
            ann.get("end_frame") == end_frame and
            ann.get("fighter_color") == fighter_color):
            return ann
    return None


def get_annotation_stats(video_stem: str, total_events: int) -> Dict:
    """Get annotation progress statistics."""
    data = load_annotations(video_stem)
    annotations = data.get("annotations", [])

    by_annotator = {}
    by_technique = {}
    for ann in annotations:
        who = ann.get("annotated_by", "Unknown") or "Unknown"
        by_annotator[who] = by_annotator.get(who, 0) + 1
        tech = ann.get("technique", "unknown")
        by_technique[tech] = by_technique.get(tech, 0) + 1

    return {
        "total_events": total_events,
        "annotated": len(annotations),
        "remaining": max(0, total_events - len(annotations)),
        "progress_pct": round(len(annotations) / max(1, total_events) * 100, 1),
        "by_annotator": by_annotator,
        "by_technique": by_technique,
    }


# ---------------------------------------------------------------------------
# Match groups — link multiple videos as parts of one match
# ---------------------------------------------------------------------------
MATCHES_FILE = ANNOTATIONS_DIR / "_matches.json"


def load_matches() -> Dict:
    """Load all match group definitions."""
    ANNOTATIONS_DIR.mkdir(parents=True, exist_ok=True)
    if MATCHES_FILE.exists():
        with open(MATCHES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_matches(matches: Dict):
    """Save match group definitions."""
    ANNOTATIONS_DIR.mkdir(parents=True, exist_ok=True)
    with open(MATCHES_FILE, "w", encoding="utf-8") as f:
        json.dump(matches, f, indent=2, ensure_ascii=False)


def get_match_for_video(video_stem: str) -> Optional[Dict]:
    """Get match info for a video, if it belongs to a match group.
    Returns dict with: match_name, video_part, red_name, blue_name, videos
    """
    matches = load_matches()
    for match_name, mdata in matches.items():
        for vinfo in mdata.get("videos", []):
            if vinfo.get("video_stem") == video_stem:
                return {
                    "match_name": match_name,
                    "video_part": vinfo.get("part", 1),
                    "red_name": mdata.get("red_name", ""),
                    "blue_name": mdata.get("blue_name", ""),
                    "videos": mdata.get("videos", []),
                }
    return None


def save_match_group(match_name: str, video_stem: str, part: int,
                     red_name: str = "", blue_name: str = ""):
    """Add or update a video in a match group."""
    matches = load_matches()
    if match_name not in matches:
        matches[match_name] = {
            "red_name": red_name,
            "blue_name": blue_name,
            "videos": [],
        }

    # Update fighter names if provided
    if red_name:
        matches[match_name]["red_name"] = red_name
    if blue_name:
        matches[match_name]["blue_name"] = blue_name

    # Add or update video entry
    videos = matches[match_name]["videos"]
    found = False
    for v in videos:
        if v["video_stem"] == video_stem:
            v["part"] = part
            found = True
            break
    if not found:
        videos.append({"video_stem": video_stem, "part": part})

    # Sort by part number
    videos.sort(key=lambda v: v.get("part", 1))
    matches[match_name]["videos"] = videos
    save_matches(matches)


def list_match_names() -> list:
    """List all existing match group names."""
    matches = load_matches()
    return sorted(matches.keys())
