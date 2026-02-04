from fastapi import FastAPI, UploadFile, File, Header, HTTPException
from pydantic import BaseModel
import shutil
import os
import base64
import uuid

from scam_detector import ScamDetector

API_KEY = "scam-api-12345"   # change this in production
UPLOAD_DIR = "temp_audio"


os.makedirs(UPLOAD_DIR, exist_ok=True)


app = FastAPI(
    title="Scam Audio Detection API",
    description="Detects scam calls using audio analysis",
    version="1.0"
)


detector = ScamDetector()


class Base64Request(BaseModel):
    language: str
    audio_format: str
    audio_base64: str



@app.get("/")
def home():
    return {"message": "Scam Detection API is running 🚀"}


@app.post("/detect-scam")
async def detect_scam(
    audio: UploadFile = File(...),
    x_api_key: str = Header(...)
):
    
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    
    if not audio.content_type.startswith("audio"):
        raise HTTPException(status_code=400, detail="Only audio files are allowed")

    
    ext = audio.filename.split(".")[-1]
    file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}.{ext}")

    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)

    try:
     
        result = detector.predict(file_path)

        return {
            "status": "success",
            "filename": audio.filename,
            "prediction": result["label"],
            "confidence": result["confidence"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
       
        if os.path.exists(file_path):
            os.remove(file_path)


@app.post("/detect-scam-base64")
def detect_scam_base64(
    data: Base64Request,
    x_api_key: str = Header(...)
):
    
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

   
    tmp_path = os.path.join(
        UPLOAD_DIR, f"{uuid.uuid4()}.{data.audio_format}"
    )

    try:
        
        audio_bytes = base64.b64decode(data.audio_base64)

        with open(tmp_path, "wb") as f:
            f.write(audio_bytes)

       
        result = detector.predict(tmp_path)

        return {
            "status": "success",
            "language": data.language,
            "prediction": result["label"],
            "confidence": result["confidence"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
