"""
OCT Smart Tutor — FastAPI Backend

Serves the AI-driven OCT classification model and manages the adaptive
training curriculum using the Fair UCB algorithm.
Images are streamed from the Kaggle OCT dataset on demand.
"""
import os
import numpy as np
from io import BytesIO

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.background import BackgroundTasks
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Conditional TensorFlow import — fall back to simulation if not available
try:
    import tensorflow as tf
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from database import (
    init_db, create_user, get_user_by_username, get_user_by_id,
    create_session, record_attempt, get_user_stats, get_user_history,
    verify_password, set_user_password,
)
from fair_ucb import select_class, CLASS_NAMES
import kaggle_service

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "UGP-final-model.keras")
IMG_HEIGHT, IMG_WIDTH = 224, 224

# ------------------------------------------------------------------
# App Setup
# ------------------------------------------------------------------
app = FastAPI(title="OCT Smart Tutor API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# Global State
# ------------------------------------------------------------------
model = None


def load_model():
    """Load the Keras model once at startup."""
    global model
    if TF_AVAILABLE and os.path.exists(MODEL_PATH):
        print(f"Loading model from {MODEL_PATH}...")
        model = tf.keras.models.load_model(MODEL_PATH)
        print("Model loaded successfully!")
    else:
        print("WARNING: TensorFlow not available or model file not found.")
        print(f"  TF available: {TF_AVAILABLE}")
        print(f"  Model path exists: {os.path.exists(MODEL_PATH)}")
        print("  Running in SIMULATION mode — predictions will be random.")
        model = None


def predict_image(image_path: str) -> tuple[str, float]:
    """Run prediction on a single image. Returns (class_name, confidence)."""
    if model is not None and TF_AVAILABLE and PIL_AVAILABLE:
        try:
            img = Image.open(image_path).convert("RGB").resize((IMG_WIDTH, IMG_HEIGHT))
            img_array = tf.keras.preprocessing.image.img_to_array(img)
            img_array = tf.expand_dims(img_array, 0)
            predictions = model.predict(img_array, verbose=0)
            predicted_idx = int(np.argmax(predictions[0]))
            confidence = float(np.max(predictions[0]))
            return CLASS_NAMES[predicted_idx], confidence
        except Exception as e:
            print(f"Prediction error for {image_path}: {e}")

    # Simulation fallback: use the directory/condition name as truth
    parent_dir = os.path.basename(os.path.dirname(image_path)).upper()
    if parent_dir in CLASS_NAMES:
        confidence = round(0.90 + np.random.random() * 0.09, 4)
        return parent_dir, confidence

    # Total fallback
    cls = np.random.choice(CLASS_NAMES)
    return cls, round(0.7 + np.random.random() * 0.25, 4)


# ------------------------------------------------------------------
# Startup Event
# ------------------------------------------------------------------
@app.on_event("startup")
async def startup():
    init_db()
    load_model()
    # Pre-load Kaggle file lists in background (non-blocking for startup)
    try:
        kaggle_service.preload_file_lists()
    except Exception as e:
        print(f"WARNING: Kaggle pre-load failed: {e}")
        print("Images will be fetched on first request.")


# ------------------------------------------------------------------
# Pydantic Models
# ------------------------------------------------------------------
class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class AuthResponse(BaseModel):
    user_id: str
    username: str
    session_id: str

class DiagnosisRequest(BaseModel):
    user_id: str
    session_id: str
    image_id: str
    user_prediction: str

class DiagnosisResponse(BaseModel):
    is_correct: bool
    user_prediction: str
    ai_prediction: str
    ai_confidence: float
    true_class: str

class NextCaseResponse(BaseModel):
    image_id: str
    image_url: str

class StatsResponse(BaseModel):
    stats: dict
    total_attempts: int
    overall_accuracy: float


# ------------------------------------------------------------------
# API Endpoints — Authentication
# ------------------------------------------------------------------
@app.post("/api/register", response_model=AuthResponse)
async def register(req: RegisterRequest):
    """Register a new user account."""
    username = req.username.strip().lower()
    password = req.password

    if not username:
        raise HTTPException(400, "Username cannot be empty")
    if len(username) < 2:
        raise HTTPException(400, "Username must be at least 2 characters")
    if len(password) < 4:
        raise HTTPException(400, "Password must be at least 4 characters")

    existing = get_user_by_username(username)
    if existing:
        raise HTTPException(409, "Username already taken")

    user = create_user(username, password)
    session = create_session(user["id"])

    return AuthResponse(
        user_id=user["id"],
        username=user["username"],
        session_id=session["id"],
    )


@app.post("/api/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    """Login with username and password."""
    username = req.username.strip().lower()
    password = req.password

    if not username:
        raise HTTPException(400, "Username cannot be empty")

    user = get_user_by_username(username)
    if not user:
        raise HTTPException(401, "Invalid username or password")

    # Handle legacy users without passwords (migration path)
    if not user.get("password_hash"):
        # First login after migration — set their password
        set_user_password(user["id"], password)
    else:
        if not verify_password(password, user["password_hash"]):
            raise HTTPException(401, "Invalid username or password")

    session = create_session(user["id"])

    return AuthResponse(
        user_id=user["id"],
        username=user["username"],
        session_id=session["id"],
    )


# ------------------------------------------------------------------
# API Endpoints — Training
# ------------------------------------------------------------------
@app.get("/api/next-case/{user_id}/{session_id}", response_model=NextCaseResponse)
async def get_next_case(user_id: str, session_id: str):
    """Use Fair UCB to select the next OCT case, fetched from Kaggle."""
    stats = get_user_stats(user_id)

    # Fair UCB selects which class to focus on
    selected_cls = select_class(stats)

    # Get recent image filenames to avoid repetition
    history = get_user_history(user_id, limit=10)
    recent_filenames = []
    for h in history:
        decoded = kaggle_service.decode_image_id(h["image_id"])
        if decoded:
            recent_filenames.append(decoded[2])  # filename

    # Try all available splits to find images for the selected class
    SPLITS_TO_TRY = ["test", "train", "val"]
    result = None
    used_split = None

    for split in SPLITS_TO_TRY:
        result = kaggle_service.get_random_image_path(
            split, selected_cls, exclude_filenames=recent_filenames
        )
        if result is not None:
            used_split = split
            break

    if result is None:
        # Try other classes across all splits
        for cls in CLASS_NAMES:
            if cls != selected_cls:
                for split in SPLITS_TO_TRY:
                    result = kaggle_service.get_random_image_path(
                        split, cls, exclude_filenames=recent_filenames
                    )
                    if result is not None:
                        selected_cls = cls
                        used_split = split
                        break
                if result is not None:
                    break

    if result is None:
        raise HTTPException(503, "Failed to fetch images from Kaggle. Please check your connection and credentials.")

    local_path, kaggle_path = result
    filename = os.path.basename(kaggle_path)
    image_id = kaggle_service.encode_image_id(used_split, selected_cls, filename)

    # Run prediction on the downloaded image
    ai_prediction, ai_confidence = predict_image(local_path)

    # Store prediction data in a temp cache for the submit endpoint
    _prediction_cache[image_id] = {
        "local_path": local_path,
        "true_class": selected_cls,
        "ai_prediction": ai_prediction,
        "ai_confidence": ai_confidence,
        "kaggle_path": kaggle_path,
    }

    return NextCaseResponse(
        image_id=image_id,
        image_url=f"/api/images/{image_id}",
    )


# Temporary in-memory cache for predictions (cleared after submission)
_prediction_cache: dict[str, dict] = {}


@app.post("/api/submit-diagnosis", response_model=DiagnosisResponse)
async def submit_diagnosis(req: DiagnosisRequest):
    """Submit the doctor's diagnosis and get AI feedback."""
    cached = _prediction_cache.get(req.image_id)

    if not cached:
        # Image not in cache — try to reconstruct from the image_id
        decoded = kaggle_service.decode_image_id(req.image_id)
        if not decoded:
            raise HTTPException(404, "Image not found")

        split, condition, filename = decoded
        # Use condition as ground truth class
        confidence = round(0.90 + np.random.random() * 0.09, 4)
        cached = {
            "true_class": condition,
            "ai_prediction": condition,
            "ai_confidence": confidence,
        }

    is_correct = req.user_prediction.upper() == cached["ai_prediction"].upper()

    # Record the attempt
    record_attempt(
        session_id=req.session_id,
        user_id=req.user_id,
        image_id=req.image_id,
        true_class=cached["true_class"],
        ai_prediction=cached["ai_prediction"],
        ai_confidence=cached["ai_confidence"],
        user_prediction=req.user_prediction.upper(),
        is_correct=is_correct,
    )

    # Clean up cached prediction and temp file
    if req.image_id in _prediction_cache:
        local_path = _prediction_cache[req.image_id].get("local_path")
        if local_path:
            kaggle_service.cleanup_temp_file(local_path)
        del _prediction_cache[req.image_id]

    return DiagnosisResponse(
        is_correct=is_correct,
        user_prediction=req.user_prediction.upper(),
        ai_prediction=cached["ai_prediction"],
        ai_confidence=cached["ai_confidence"],
        true_class=cached["true_class"],
    )


@app.get("/api/images/{image_id}")
async def get_image(image_id: str, background_tasks: BackgroundTasks):
    """Serve an OCT image by its ID."""
    # Check prediction cache first (image already downloaded)
    cached = _prediction_cache.get(image_id)
    if cached and cached.get("local_path") and os.path.exists(cached["local_path"]):
        return FileResponse(cached["local_path"], media_type="image/jpeg")

    # Otherwise, download from Kaggle
    decoded = kaggle_service.decode_image_id(image_id)
    if not decoded:
        raise HTTPException(404, "Invalid image ID")

    split, condition, filename = decoded
    kaggle_path = f"Dataset - train+val+test/{split}/{condition}/{filename}"
    local_path = kaggle_service.get_specific_image_path(kaggle_path)

    if not local_path:
        raise HTTPException(503, "Failed to download image from Kaggle")

    # Schedule cleanup after response is sent
    background_tasks.add_task(kaggle_service.cleanup_temp_file, local_path)

    return FileResponse(local_path, media_type="image/jpeg")


@app.get("/api/stats/{user_id}", response_model=StatsResponse)
async def get_stats(user_id: str):
    """Get the doctor's performance stats per class."""
    stats = get_user_stats(user_id)

    total_attempts = sum(s["total"] for s in stats.values())
    total_correct = sum(s["correct"] for s in stats.values())
    overall_accuracy = total_correct / total_attempts if total_attempts > 0 else 0.0

    return StatsResponse(
        stats=stats,
        total_attempts=total_attempts,
        overall_accuracy=overall_accuracy,
    )


@app.post("/api/predict")
async def predict_scan(file: UploadFile = File(...)):
    """Real-time prediction endpoint for uploaded scans."""
    if model is None:
        raise HTTPException(503, "Model not loaded. Running in simulation mode.")

    if not PIL_AVAILABLE:
        raise HTTPException(503, "PIL not available.")

    image_data = await file.read()
    image = Image.open(BytesIO(image_data)).convert("RGB").resize((IMG_WIDTH, IMG_HEIGHT))
    img_array = tf.keras.preprocessing.image.img_to_array(image)
    img_array = tf.expand_dims(img_array, 0)

    predictions = model.predict(img_array, verbose=0)
    predicted_class = CLASS_NAMES[int(np.argmax(predictions[0]))]
    confidence = float(np.max(predictions[0]))

    return {"diagnosis": predicted_class, "confidence": confidence}


# ------------------------------------------------------------------
# Frontend Static Files (Production)
# ------------------------------------------------------------------
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        index_path = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_path):
            with open(index_path, "r") as f:
                return HTMLResponse(content=f.read(), status_code=200)
        return {"error": "Frontend build not found"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
