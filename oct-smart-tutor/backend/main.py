"""
OCT Smart Tutor — FastAPI Backend

Serves the AI-driven OCT classification model and manages the adaptive
training curriculum using the Fair UCB algorithm.
"""
import os
import uuid
import numpy as np
from pathlib import Path
from io import BytesIO

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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

from database import init_db, create_user, get_user_by_username, create_session, record_attempt, get_user_stats, get_user_history
from fair_ucb import select_class, select_image, CLASS_NAMES

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "UGP-seond-try-model.keras")
SAMPLE_IMAGES_DIR = os.path.join(os.path.dirname(__file__), "sample_images")
IMG_HEIGHT, IMG_WIDTH = 224, 224

# ------------------------------------------------------------------
# App Setup
# ------------------------------------------------------------------
app = FastAPI(title="OCT Smart Tutor API", version="1.0.0")

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
image_catalog: dict[str, list[dict]] = {}  # {class_name: [{id, path, ai_prediction, ai_confidence}]}


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
    
    # Simulation fallback: use the directory name as truth, high confidence
    parent_dir = os.path.basename(os.path.dirname(image_path)).upper()
    if parent_dir in CLASS_NAMES:
        # Simulate high-confidence correct prediction (as the model is ~97% accurate)
        confidence = round(0.90 + np.random.random() * 0.09, 4)
        return parent_dir, confidence
    
    # Total fallback
    cls = np.random.choice(CLASS_NAMES)
    return cls, round(0.7 + np.random.random() * 0.25, 4)


def build_image_catalog():
    """Scan sample images directory and pre-compute predictions."""
    global image_catalog
    image_catalog = {cls: [] for cls in CLASS_NAMES}
    
    if not os.path.exists(SAMPLE_IMAGES_DIR):
        print(f"WARNING: Sample images directory not found: {SAMPLE_IMAGES_DIR}")
        return
    
    for cls in CLASS_NAMES:
        cls_dir = os.path.join(SAMPLE_IMAGES_DIR, cls)
        if not os.path.isdir(cls_dir):
            print(f"  No directory for class {cls}")
            continue
        
        for filename in os.listdir(cls_dir):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                filepath = os.path.join(cls_dir, filename)
                image_id = f"{cls}_{filename}"
                ai_prediction, ai_confidence = predict_image(filepath)
                
                image_catalog[cls].append({
                    "id": image_id,
                    "filename": filename,
                    "true_class": cls,
                    "ai_prediction": ai_prediction,
                    "ai_confidence": ai_confidence,
                    "path": filepath,
                })
        
        print(f"  Cataloged {len(image_catalog[cls])} images for class {cls}")
    
    total = sum(len(v) for v in image_catalog.values())
    print(f"Image catalog built: {total} total images")


# ------------------------------------------------------------------
# Startup Event
# ------------------------------------------------------------------
@app.on_event("startup")
async def startup():
    init_db()
    load_model()
    build_image_catalog()


# ------------------------------------------------------------------
# Pydantic Models
# ------------------------------------------------------------------
class LoginRequest(BaseModel):
    username: str

class LoginResponse(BaseModel):
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
    selected_class: str  # The class the UCB algorithm chose (for frontend display)

class StatsResponse(BaseModel):
    stats: dict
    total_attempts: int
    overall_accuracy: float


# ------------------------------------------------------------------
# API Endpoints
# ------------------------------------------------------------------
@app.post("/api/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """Login or register a user. Creates a new session."""
    username = req.username.strip().lower()
    if not username:
        raise HTTPException(400, "Username cannot be empty")
    
    user = get_user_by_username(username)
    if not user:
        user = create_user(username)
    
    session = create_session(user["id"])
    
    return LoginResponse(
        user_id=user["id"],
        username=user["username"],
        session_id=session["id"],
    )


@app.get("/api/next-case/{user_id}/{session_id}", response_model=NextCaseResponse)
async def get_next_case(user_id: str, session_id: str):
    """Use Fair UCB to select the next OCT case for the doctor."""
    stats = get_user_stats(user_id)
    
    # Fair UCB selects which class to focus on
    selected_cls = select_class(stats)
    
    # Get recent image IDs to avoid repetition
    history = get_user_history(user_id, limit=10)
    recent_ids = [h["image_id"] for h in history]
    
    # Select an image from the chosen class
    image_info = select_image(selected_cls, image_catalog, recent_ids)
    
    if image_info is None:
        # If no image found in the selected class, try other classes
        for cls in CLASS_NAMES:
            if cls != selected_cls:
                image_info = select_image(cls, image_catalog, recent_ids)
                if image_info is not None:
                    selected_cls = cls
                    break
    
    if image_info is None:
        raise HTTPException(404, "No images available. Please add sample images.")
    
    return NextCaseResponse(
        image_id=image_info["id"],
        image_url=f"/api/images/{image_info['id']}",
        selected_class=selected_cls,
    )


@app.post("/api/submit-diagnosis", response_model=DiagnosisResponse)
async def submit_diagnosis(req: DiagnosisRequest):
    """Submit the doctor's diagnosis and get AI feedback."""
    # Find the image in the catalog
    image_info = None
    for cls in CLASS_NAMES:
        for img in image_catalog.get(cls, []):
            if img["id"] == req.image_id:
                image_info = img
                break
        if image_info:
            break
    
    if not image_info:
        raise HTTPException(404, "Image not found in catalog")
    
    is_correct = req.user_prediction.upper() == image_info["ai_prediction"].upper()
    
    # Record the attempt
    record_attempt(
        session_id=req.session_id,
        user_id=req.user_id,
        image_id=req.image_id,
        true_class=image_info["true_class"],
        ai_prediction=image_info["ai_prediction"],
        ai_confidence=image_info["ai_confidence"],
        user_prediction=req.user_prediction.upper(),
        is_correct=is_correct,
    )
    
    return DiagnosisResponse(
        is_correct=is_correct,
        user_prediction=req.user_prediction.upper(),
        ai_prediction=image_info["ai_prediction"],
        ai_confidence=image_info["ai_confidence"],
        true_class=image_info["true_class"],
    )


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


@app.get("/api/images/{image_id}")
async def get_image(image_id: str):
    """Serve an OCT image by its ID."""
    for cls in CLASS_NAMES:
        for img in image_catalog.get(cls, []):
            if img["id"] == image_id:
                return FileResponse(img["path"])
    
    raise HTTPException(404, "Image not found")


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
