"""
Kaggle Image Service for OCT Smart Tutor.

Streams OCT images on demand from the Kaggle dataset.
Uses a paginated approach — fetches batches of file listings as needed
rather than trying to load the entire 84k+ file catalog at startup.
"""
import os
import random
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

# Cache: { "train_CNV": [list of file paths], ... }
_file_list_cache: dict[str, list[str]] = {}

# Page tokens cache: { "global": next_page_token }
_page_tokens: dict[str, str | None] = {"current": None, "exhausted": False}
_total_fetched: int = 0

_api: KaggleApi | None = None

# How many files to fetch per startup batch
INITIAL_FETCH_PAGES = 100  # 100 pages * 20 files = 2000 files


def _get_api() -> KaggleApi:
    global _api
    if _api is None:
        _api = KaggleApi()
        _api.authenticate()
        print("Kaggle API authenticated successfully.")
    return _api


def _build_cache_key(split: str, condition: str) -> str:
    return f"{split}_{condition}"


def _categorize_file(name: str) -> tuple[str, str] | None:
    """Parse a file path into (split, condition) or None."""
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


def _fetch_pages(num_pages: int):
    """Fetch more pages from Kaggle and add to caches."""
    global _total_fetched

    if _page_tokens.get("exhausted"):
        return

    api = _get_api()
    page_token = _page_tokens.get("current")

    for i in range(num_pages):
        try:
            result = api.dataset_list_files(
                DATASET_NAME,
                page_token=page_token,
                page_size=20,
            )
        except Exception as e:
            print(f"[Kaggle] Error fetching page: {e}")
            break

        batch = result.files
        if not batch:
            _page_tokens["exhausted"] = True
            break

        for f in batch:
            name = f.name
            cat = _categorize_file(name)
            if cat:
                key = _build_cache_key(*cat)
                if key not in _file_list_cache:
                    _file_list_cache[key] = []
                _file_list_cache[key].append(name)

        _total_fetched += len(batch)

        page_token = result.next_page_token if hasattr(result, 'next_page_token') else None
        _page_tokens["current"] = page_token

        if not page_token:
            _page_tokens["exhausted"] = True
            break

    # Print summary
    summary = {}
    for key, files in _file_list_cache.items():
        summary[key] = len(files)
    print(f"[Kaggle] Cache status ({_total_fetched} files fetched): {summary}")


def _ensure_min_files(split: str, condition: str, min_count: int = 10):
    """Make sure we have at least min_count files for a category."""
    key = _build_cache_key(split, condition)
    current = len(_file_list_cache.get(key, []))

    if current >= min_count or _page_tokens.get("exhausted"):
        return

    # Fetch more pages
    pages_needed = max(50, (min_count - current) * 2)
    print(f"[Kaggle] Need more files for {split}/{condition} (have {current}), fetching {pages_needed} pages...")
    _fetch_pages(pages_needed)


def get_random_image_path(
    split: str,
    condition: str,
    exclude_filenames: list[str] | None = None,
) -> tuple[str, str] | None:
    """Pick a random image and download it. Returns (local_path, kaggle_path) or None."""
    _ensure_min_files(split, condition, min_count=5)

    key = _build_cache_key(split, condition)
    files = _file_list_cache.get(key, [])
    if not files:
        return None

    candidates = files
    if exclude_filenames:
        filtered = [f for f in files if os.path.basename(f) not in exclude_filenames]
        if filtered:
            candidates = filtered

    selected = random.choice(candidates)
    return _download_file(selected)


def get_specific_image_path(kaggle_file_path: str) -> str | None:
    """Download a specific file. Returns local path or None."""
    result = _download_file(kaggle_file_path)
    return result[0] if result else None


def _download_file(kaggle_file_path: str) -> tuple[str, str] | None:
    """Download a file from Kaggle to a temp directory."""
    api = _get_api()
    temp_dir = tempfile.mkdtemp(prefix="oct_tutor_")

    try:
        api.dataset_download_file(DATASET_NAME, kaggle_file_path, path=temp_dir)
        filename = os.path.basename(kaggle_file_path)
        local_path = os.path.join(temp_dir, filename)

        if os.path.exists(local_path):
            return local_path, kaggle_file_path

        # Check for zip download
        zip_path = local_path + ".zip"
        if os.path.exists(zip_path):
            import zipfile
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(temp_dir)
            os.remove(zip_path)
            if os.path.exists(local_path):
                return local_path, kaggle_file_path

        print(f"[Kaggle] File not found at: {local_path}")
        return None
    except Exception as e:
        print(f"[Kaggle] Download error for {kaggle_file_path}: {e}")
        return None


def cleanup_temp_file(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
        parent = os.path.dirname(path)
        if os.path.isdir(parent) and not os.listdir(parent):
            os.rmdir(parent)
    except Exception as e:
        print(f"[Kaggle] Cleanup error: {e}")


def encode_image_id(split: str, condition: str, filename: str) -> str:
    return f"{split}__{condition}__{filename}"


def decode_image_id(image_id: str) -> tuple[str, str, str] | None:
    parts = image_id.split("__")
    if len(parts) != 3:
        return None
    return parts[0], parts[1], parts[2]


def preload_file_lists():
    """Pre-fetch a batch of file listings at startup."""
    print("[Kaggle] Pre-loading initial file batch...")
    _fetch_pages(INITIAL_FETCH_PAGES)
    print("[Kaggle] Pre-load complete.")
