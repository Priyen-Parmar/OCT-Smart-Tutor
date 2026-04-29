"""
Kaggle Image Service for OCT Smart Tutor.

Implements a persistent local image buffer:
  - Downloads images into backend/image_cache/{condition}/ 
  - Serves images instantly from local disk (no per-request Kaggle latency)
  - Automatically refills in the background when 70% of a class is consumed
  - Persists across restarts — skips re-downloading existing images
"""
import os
import random
import threading
import time
import shutil
import tempfile
from dotenv import load_dotenv

# Load .env from the project root (one level above backend/)
_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(_env_path)

if not os.environ.get("KAGGLE_USERNAME") or not os.environ.get("KAGGLE_KEY"):
    raise RuntimeError(
        "Missing Kaggle credentials! "
        "Please create a .env file with KAGGLE_USERNAME and KAGGLE_KEY."
    )

from kaggle.api.kaggle_api_extended import KaggleApi

DATASET_NAME = "anirudhcv/labeled-optical-coherence-tomography-oct"
VALID_SPLITS = ["train", "val", "test"]
VALID_CONDITIONS = ["CNV", "DME", "DRUSEN", "NORMAL"]

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
IMAGES_PER_CLASS = 150          # Target buffer size per class
REFILL_THRESHOLD = 0.70         # Trigger refill when 70% of buffer used
PAGE_SIZE = 20                  # Kaggle API page size

# Persistent cache directory
CACHE_DIR = os.path.join(os.path.dirname(__file__), "image_cache")

# ------------------------------------------------------------------
# Internal State
# ------------------------------------------------------------------
_api: KaggleApi | None = None
_api_lock = threading.Lock()

# File listing cache: { "train_CNV": [kaggle_path, ...], ... }
_file_list_cache: dict[str, list[str]] = {}
_file_list_lock = threading.Lock()

# Listing fetch lock — only one thread fetches listings at a time
_listing_fetch_lock = threading.Lock()

# Page tokens for Kaggle file listing pagination
_page_tokens: dict[str, object] = {"current": None, "exhausted": False}
_total_listed: int = 0

# Track which images have been served (per class, by filename)
_used_images: dict[str, set[str]] = {c: set() for c in VALID_CONDITIONS}
_used_lock = threading.Lock()

# Track active refill threads to avoid duplicates
_refill_active: dict[str, bool] = {c: False for c in VALID_CONDITIONS}
_refill_lock = threading.Lock()

# Overall readiness flag
_buffer_ready = threading.Event()
# Early readiness — set when at least 1 image per class is available
_early_ready = threading.Event()
_download_progress: dict[str, int] = {c: 0 for c in VALID_CONDITIONS}


def _get_api() -> KaggleApi:
    global _api
    with _api_lock:
        if _api is None:
            _api = KaggleApi()
            _api.authenticate()
            print("[Kaggle] API authenticated successfully.")
        return _api


# ------------------------------------------------------------------
# File Listing (Paginated Catalog from Kaggle)
# ------------------------------------------------------------------

def _build_cache_key(split: str, condition: str) -> str:
    return f"{split}_{condition}"


def _categorize_file(name: str) -> tuple[str, str] | None:
    """Parse a Kaggle file path into (split, condition) or None."""
    prefix = "Dataset - train+val+test/"
    if not name.startswith(prefix):
        return None
    if not name.lower().endswith(('.jpeg', '.jpg', '.png')):
        return None
    rest = name[len(prefix):]
    parts = rest.split("/")
    if len(parts) < 3:
        return None
    split, condition = parts[0], parts[1]
    if split in VALID_SPLITS and condition in VALID_CONDITIONS:
        return split, condition
    return None


def _fetch_file_listing_pages(num_pages: int):
    """Fetch pages of file listings from Kaggle into _file_list_cache.
    Thread-safe: only one thread fetches at a time."""
    global _total_listed

    with _listing_fetch_lock:
        if _page_tokens.get("exhausted"):
            return

        api = _get_api()
        page_token = _page_tokens.get("current")

        for _ in range(num_pages):
            try:
                result = api.dataset_list_files(
                    DATASET_NAME,
                    page_token=page_token,
                    page_size=PAGE_SIZE,
                )
            except Exception as e:
                print(f"[Kaggle] Error fetching file listing page: {e}")
                break

            batch = result.files
            if not batch:
                _page_tokens["exhausted"] = True
                break

            with _file_list_lock:
                for f in batch:
                    name = f.name
                    cat = _categorize_file(name)
                    if cat:
                        key = _build_cache_key(*cat)
                        if key not in _file_list_cache:
                            _file_list_cache[key] = []
                        _file_list_cache[key].append(name)

            _total_listed += len(batch)

            page_token = result.next_page_token if hasattr(result, 'next_page_token') else None
            _page_tokens["current"] = page_token

            if not page_token:
                _page_tokens["exhausted"] = True
                break


def _get_listings_for_condition(condition: str) -> list[str]:
    """Get all known file listings for a condition across all splits."""
    paths = []
    with _file_list_lock:
        for split in VALID_SPLITS:
            key = _build_cache_key(split, condition)
            paths.extend(_file_list_cache.get(key, []))
    return paths


# ------------------------------------------------------------------
# Local Cache Management
# ------------------------------------------------------------------

def _get_cache_path(condition: str, filename: str) -> str:
    """Get the local path for a cached image."""
    condition_dir = os.path.join(CACHE_DIR, condition)
    os.makedirs(condition_dir, exist_ok=True)
    return os.path.join(condition_dir, filename)


def _get_cached_images(condition: str) -> list[str]:
    """Get list of filenames already in the local cache for a condition."""
    condition_dir = os.path.join(CACHE_DIR, condition)
    if not os.path.isdir(condition_dir):
        return []
    return [
        f for f in os.listdir(condition_dir)
        if f.lower().endswith(('.jpeg', '.jpg', '.png')) and os.path.isfile(os.path.join(condition_dir, f))
    ]


def _download_to_cache(kaggle_path: str, condition: str) -> str | None:
    """Download a single image from Kaggle into the persistent cache. Returns local path or None."""
    filename = os.path.basename(kaggle_path)
    dest_path = _get_cache_path(condition, filename)

    # Already cached
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
        return dest_path

    api = _get_api()
    temp_dir = tempfile.mkdtemp(prefix="oct_dl_")

    try:
        api.dataset_download_file(DATASET_NAME, kaggle_path, path=temp_dir)
        temp_file = os.path.join(temp_dir, filename)

        if os.path.exists(temp_file):
            shutil.move(temp_file, dest_path)
            return dest_path

        # Check for zip download
        zip_path = temp_file + ".zip"
        if os.path.exists(zip_path):
            import zipfile
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(temp_dir)
            os.remove(zip_path)
            if os.path.exists(temp_file):
                shutil.move(temp_file, dest_path)
                return dest_path

        return None
    except Exception as e:
        print(f"[Kaggle] Download error for {kaggle_path}: {e}")
        return None
    finally:
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


# ------------------------------------------------------------------
# Buffer Pre-Download (Background)
# ------------------------------------------------------------------

def _download_batch_for_condition(condition: str, paths: list[str], target: int, existing_set: set, start_count: int) -> int:
    """Download images for a condition from the given paths. Returns total downloaded count."""
    downloaded = 0
    needed = target - start_count - downloaded

    for kaggle_path in paths:
        if downloaded >= needed:
            break
        fname = os.path.basename(kaggle_path)
        if fname in existing_set:
            continue
        result = _download_to_cache(kaggle_path, condition)
        if result:
            existing_set.add(fname)
            downloaded += 1
            _download_progress[condition] = start_count + downloaded
            if downloaded % 5 == 0:
                print(f"[Buffer] {condition}: downloaded {start_count + downloaded}/{target}")
            # Check if early ready (at least 1 image per class)
            if not _early_ready.is_set():
                _check_early_ready()

    return downloaded


def _check_early_ready():
    """Set early_ready flag if we have at least 1 image for every class."""
    for c in VALID_CONDITIONS:
        if not _get_cached_images(c):
            return
    _early_ready.set()
    print("[Buffer] ✓ Early ready — at least 1 image per class available!")


def start_buffer_prefill():
    """Start background prefill: fetch listings then download images for all classes."""
    os.makedirs(CACHE_DIR, exist_ok=True)

    def _worker():
        print("[Buffer] Starting pre-download of image buffer...")

        # Check existing cache first
        for condition in VALID_CONDITIONS:
            existing = _get_cached_images(condition)
            _download_progress[condition] = len(existing)
            if existing:
                print(f"[Buffer] {condition}: {len(existing)} images already cached")
        _check_early_ready()

        # If all classes already have enough, we're done
        all_full = all(
            len(_get_cached_images(c)) >= IMAGES_PER_CLASS
            for c in VALID_CONDITIONS
        )
        if all_full:
            _buffer_ready.set()
            print("[Buffer] ✓ All classes already fully cached!")
            return

        # Phase 1: Fetch file listings in batches, downloading as we go
        # This interleaves listing fetches with downloads so images
        # start appearing as quickly as possible
        print("[Buffer] Phase 1: Fetching listings and downloading...")

        listing_rounds = 0
        max_listing_rounds = 200  # Safety limit (200 * 20 pages * 20 files = 80k files max)

        while listing_rounds < max_listing_rounds:
            # Check if all classes are full
            all_full = all(
                len(_get_cached_images(c)) >= IMAGES_PER_CLASS
                for c in VALID_CONDITIONS
            )
            if all_full:
                break

            if _page_tokens.get("exhausted"):
                break

            # Fetch a batch of file listings
            _fetch_file_listing_pages(20)  # 20 pages = ~400 file paths
            listing_rounds += 1

            # For each condition that still needs images, download what we have
            for condition in VALID_CONDITIONS:
                existing = _get_cached_images(condition)
                if len(existing) >= IMAGES_PER_CLASS:
                    continue

                listings = _get_listings_for_condition(condition)
                if not listings:
                    continue

                existing_set = set(existing)
                available = [p for p in listings if os.path.basename(p) not in existing_set]
                if not available:
                    continue

                random.shuffle(available)
                # Download up to 10 images per round per class to keep things responsive
                batch = available[:10]
                count = _download_batch_for_condition(
                    condition, batch, IMAGES_PER_CLASS, existing_set, len(existing)
                )

            # Log progress every 5 rounds
            if listing_rounds % 5 == 0:
                status = {c: len(_get_cached_images(c)) for c in VALID_CONDITIONS}
                print(f"[Buffer] Round {listing_rounds} — cache status: {status}")

        # Final status
        for condition in VALID_CONDITIONS:
            count = len(_get_cached_images(condition))
            _download_progress[condition] = count
            print(f"[Buffer] {condition}: final count = {count}/{IMAGES_PER_CLASS}")

        _buffer_ready.set()
        _early_ready.set()
        print("[Buffer] ✓ Pre-download complete — buffer is ready!")

    thread = threading.Thread(target=_worker, daemon=True, name="buffer-prefill")
    thread.start()
    return thread


def _background_refill(condition: str):
    """Refill a single class in the background."""
    with _refill_lock:
        if _refill_active.get(condition):
            return  # Already refilling
        _refill_active[condition] = True

    def _worker():
        try:
            print(f"[Buffer] Auto-refilling {condition}...")
            existing = _get_cached_images(condition)
            existing_set = set(existing)

            # Try to download more using existing listings
            listings = _get_listings_for_condition(condition)
            available = [p for p in listings if os.path.basename(p) not in existing_set]

            if not available and not _page_tokens.get("exhausted"):
                # Fetch more listings
                _fetch_file_listing_pages(50)
                listings = _get_listings_for_condition(condition)
                available = [p for p in listings if os.path.basename(p) not in existing_set]

            if available:
                random.shuffle(available)
                needed = IMAGES_PER_CLASS - len(existing)
                batch = available[:max(needed, 50)]
                _download_batch_for_condition(
                    condition, batch, IMAGES_PER_CLASS, existing_set, len(existing)
                )

            # Reset used tracking since we have fresh images
            with _used_lock:
                cached = set(_get_cached_images(condition))
                _used_images[condition] = _used_images[condition] & cached

            final = len(_get_cached_images(condition))
            _download_progress[condition] = final
            print(f"[Buffer] Refill done for {condition}: {final} images")
        except Exception as e:
            print(f"[Buffer] Refill error for {condition}: {e}")
        finally:
            with _refill_lock:
                _refill_active[condition] = False

    thread = threading.Thread(target=_worker, daemon=True, name=f"refill-{condition}")
    thread.start()


def _check_refill_needed(condition: str):
    """Check if a class needs refilling and trigger if so."""
    cached = _get_cached_images(condition)
    total = len(cached)
    if total == 0:
        _background_refill(condition)
        return

    with _used_lock:
        used_count = len(_used_images[condition])

    usage_ratio = used_count / total if total > 0 else 1.0
    if usage_ratio >= REFILL_THRESHOLD:
        print(f"[Buffer] {condition} at {usage_ratio:.0%} usage ({used_count}/{total}), triggering refill")
        _background_refill(condition)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def get_buffer_status() -> dict:
    """Get the current buffer status for all classes."""
    status = {}
    for condition in VALID_CONDITIONS:
        cached = _get_cached_images(condition)
        total_cached = len(cached)
        with _used_lock:
            used = len(_used_images[condition])
        available = total_cached - used

        with _refill_lock:
            refilling = _refill_active.get(condition, False)

        status[condition] = {
            "cached": total_cached,
            "used": used,
            "available": max(0, available),
            "target": IMAGES_PER_CLASS,
            "progress": _download_progress.get(condition, 0),
            "refilling": refilling,
        }

    return {
        "ready": _buffer_ready.is_set(),
        "classes": status,
        "total_cached": sum(s["cached"] for s in status.values()),
        "total_available": sum(s["available"] for s in status.values()),
    }


def get_random_image_path(
    condition: str,
    exclude_filenames: list[str] | None = None,
) -> tuple[str, str] | None:
    """
    Pick a random image from the local cache.
    Returns (local_path, condition) or None if buffer is empty.
    Triggers background refill if usage threshold is exceeded.
    """
    cached_files = _get_cached_images(condition)
    if not cached_files:
        return None

    # Prefer un-used images
    with _used_lock:
        used = _used_images[condition]

    unused = [f for f in cached_files if f not in used]
    if exclude_filenames:
        unused = [f for f in unused if f not in exclude_filenames]

    # If all used, reset and allow re-use (but still exclude recent)
    if not unused:
        candidates = cached_files
        if exclude_filenames:
            candidates = [f for f in candidates if f not in exclude_filenames]
        if not candidates:
            candidates = cached_files  # Last resort: allow even recent
        selected = random.choice(candidates)
    else:
        selected = random.choice(unused)

    # Mark as used
    with _used_lock:
        _used_images[condition].add(selected)

    local_path = _get_cache_path(condition, selected)

    # Check if refill needed (non-blocking)
    _check_refill_needed(condition)

    return local_path, condition


def get_specific_image_path(condition: str, filename: str) -> str | None:
    """Get a specific image from cache. Returns local path or None."""
    path = _get_cache_path(condition, filename)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    return None


def encode_image_id(condition: str, filename: str) -> str:
    """Encode condition + filename into a single image ID string."""
    return f"{condition}__{filename}"


def decode_image_id(image_id: str) -> tuple[str, str] | None:
    """Decode an image ID into (condition, filename) or None."""
    parts = image_id.split("__", 1)
    if len(parts) != 2:
        return None
    condition, filename = parts
    if condition not in VALID_CONDITIONS:
        return None
    return condition, filename


def is_buffer_ready() -> bool:
    """Check if initial buffer download is complete."""
    return _buffer_ready.is_set()


def has_any_images() -> bool:
    """Check if we have at least 1 image for any class (enough to start)."""
    for condition in VALID_CONDITIONS:
        if _get_cached_images(condition):
            return True
    return False


def cleanup_temp_file(path: str):
    """Legacy cleanup — no-op since we use persistent cache now."""
    pass
