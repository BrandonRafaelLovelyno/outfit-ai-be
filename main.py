# Importing the necessary libraries
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import torch
import torchvision.transforms as transforms
from model import FasterRCNNResNet50
from PIL import Image

import os
import io
import requests

import warnings

warnings.simplefilter(action="ignore", category=FutureWarning)
warnings.simplefilter(action="ignore", category=UserWarning)

# Download the checkpoint
MODEL_PATH = "checkpoint.pth"
HF_URL = (
    "https://huggingface.co/brandonRafael/outfit-ai/resolve/main/checkpoint_epoch_4.pth"
)


MODEL_PATH = "checkpoint.pth"
HF_URL = (
    "https://huggingface.co/brandonRafael/outfit-ai/resolve/main/checkpoint_epoch_4.pth"
)


def check_pth():
    if os.path.exists(MODEL_PATH):
        return True
    else:
        return False


def download_pth():
    print("Downloading the checkpoint...")

    response = requests.get(HF_URL)

    with open(MODEL_PATH, "wb") as f:
        f.write(response.content)


# Initialize the model and load the checkpoint
pth_exist = check_pth()
if not pth_exist:
    download_pth()

checkpoint = torch.load(MODEL_PATH, map_location=torch.device("cpu"))
model = FasterRCNNResNet50()
model.load_state_dict(checkpoint["model_state_dict"])
model.eval()


# Define the request and response models
class ImageData(BaseModel):
    image_bytes: bytes


def preprocess_image(image_bytes):
    transform = transforms.Compose(
        [
            transforms.Resize((800, 800)),
            transforms.ToTensor(),
        ]
    )
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return transform(image)


# Initialize the FastAPI app
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow requests from all origins
    allow_credentials=True,  # Allow cookies and other credentials
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)


@app.get("/")
async def check_availability():
    return {"message": "Welcome to the Outfit AI API!", "isAvailable": True}


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    image_bytes = await file.read()
    image_tensor = preprocess_image(image_bytes)
    image_input = list(image_tensor.unsqueeze(0))

    with torch.no_grad():
        pred = model(image_input)[0]

    score_threshold = 0.5
    scores = pred["scores"]
    mask = scores >= score_threshold

    filtered_boxes = pred["boxes"][mask]
    filtered_labels = pred["labels"][mask]
    filtered_scores = pred["scores"][mask]

    return {
        "boxes": filtered_boxes.tolist(),
        "labels": filtered_labels.tolist(),
        "scores": filtered_scores.tolist(),
    }


# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
