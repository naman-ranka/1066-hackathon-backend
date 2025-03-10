import os
import base64
import io
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from django.conf import settings
import openai
import google.generativeai as genai
import traceback
from PIL import Image
import pytesseract
from google.cloud import vision
from enum import Enum

OPENAI_MODEL = "gpt-4o-mini"
GEMINI_MODEL = "gemini-1.5-flash"  # Updated to use the newer model

class OCRProvider(Enum):
    TESSERACT = "tesseract"
    GOOGLE_CLOUD = "google_cloud"

def encode_image_to_base64(image_data):
    """Convert image data to base64 encoded string."""
    try:
        base64_image = base64.b64encode(image_data).decode("utf-8")
        return f"data:image/jpeg;base64,{base64_image}"
    except Exception as e:
        raise Exception(f"Error encoding image: {str(e)}")

def read_prompt_file():
    """Read and return the content of the prompt file."""
    prompt_file_path = os.path.join(settings.BASE_DIR, "prompt.txt")
    try:
        with open(prompt_file_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        raise Exception(f"Failed to read prompt file: {str(e)}")

def process_receipt_with_openai(image_data):
    """Process receipt using OpenAI's vision model."""
    # Get API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise Exception("OPENAI_API_KEY is not set.")
    
    # Initialize OpenAI client and prepare data
    openai.api_key = api_key
    data_url = encode_image_to_base64(image_data)
    prompt = read_prompt_file()
    
    try:
        response = openai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            max_tokens=3000,
        )
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"OpenAI API error: {str(e)}")
    
def process_receipt_with_gemini(image_bytes):
    """
    Process a receipt image using Google's Gemini vision model.
    """
    if not image_bytes:
        raise ValueError("No image data provided. 'image_bytes' is empty or None.")

    # 1. Retrieve the Gemini API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY is not set in environment variables.")

    # 2. Read prompt from prompt.txt
    try:
        prompt_text = read_prompt_file()
    except Exception as e:
        raise Exception(f"Error reading prompt file: {str(e)}")

    # 3. Configure Gemini
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        raise Exception(f"Error configuring Gemini: {str(e)}")

    # 4. Create the model
    model = genai.GenerativeModel(GEMINI_MODEL)

    # 5. Convert bytes to PIL Image
    try:
        image = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        raise Exception(f"Error opening image: {str(e)}")

    # 6. Generate content
    try:
        response = model.generate_content([prompt_text, image])
        response.resolve()  # Wait for response
    except Exception as e:
        traceback.print_exc()
        raise RuntimeError(f"Gemini API error: {str(e)}")

    # 7. Validate and return response
    if not response or not response.text:
        raise RuntimeError("Gemini returned an empty response")

    return response.text

def process_images_with_tesseract(image_paths: List[str]) -> Dict[str, Any]:
    """
    Process multiple images using Tesseract OCR and return structured data.
    
    Args:
        image_paths: List of paths to the images
        
    Returns:
        Dictionary containing extracted text and metadata
    """
    # Set tesseract path for Linux
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
    
    combined_text = []
    for image_path in image_paths:
        try:
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img)
            combined_text.append({
                'image_path': image_path,
                'text': text.strip()
            })
        except Exception as e:
            combined_text.append({
                'image_path': image_path,
                'error': str(e)
            })
    
    return {
        'provider': 'tesseract',
        'results': combined_text
    }

def process_images_with_google_vision(image_paths: List[str]) -> Dict[str, Any]:
    """
    Process multiple images using Google Cloud Vision API and return structured data.
    
    Args:
        image_paths: List of paths to the images
        
    Returns:
        Dictionary containing extracted text and metadata
    """
    # Get the absolute path to the credentials file
    BASE_DIR = Path(__file__).resolve().parent.parent
    CREDENTIALS_FILE = "coral-muse-452018-s2-171009389e4d.json"
    CREDENTIALS_PATH = os.path.join(BASE_DIR, CREDENTIALS_FILE)

    if not os.path.exists(CREDENTIALS_PATH):
        raise FileNotFoundError(f"Google Cloud credentials file not found at: {CREDENTIALS_PATH}")

    # Set credentials via absolute path
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(CREDENTIALS_PATH)
    
    # Initialize Google Cloud Vision client
    client = vision.ImageAnnotatorClient()
    
    combined_text = []
    for image_path in image_paths:
        try:
            with io.open(image_path, 'rb') as image_file:
                content = image_file.read()
            
            image = vision.Image(content=content)
            response = client.text_detection(image=image)
            
            if response.error.message:
                combined_text.append({
                    'image_path': image_path,
                    'error': response.error.message
                })
                continue
            
            texts = response.text_annotations
            if texts:
                combined_text.append({
                    'image_path': image_path,
                    'text': texts[0].description.strip()
                })
            else:
                combined_text.append({
                    'image_path': image_path,
                    'text': ''
                })
                
        except Exception as e:
            combined_text.append({
                'image_path': image_path,
                'error': str(e)
            })
    
    return {
        'provider': 'google_cloud_vision',
        'results': combined_text
    }

def process_images(image_paths: List[str], provider: OCRProvider = OCRProvider.GOOGLE_CLOUD) -> Dict[str, Any]:
    """
    Process multiple images using the specified OCR provider.
    
    Args:
        image_paths: List of paths to the images
        provider: OCRProvider enum specifying which OCR service to use
        
    Returns:
        Dictionary containing the OCR results
    """
    if not image_paths:
        raise ValueError("No image paths provided")
    
    if provider == OCRProvider.TESSERACT:
        return process_images_with_tesseract(image_paths)
    elif provider == OCRProvider.GOOGLE_CLOUD:
        return process_images_with_google_vision(image_paths)
    else:
        raise ValueError(f"Unsupported OCR provider: {provider}")

def save_ocr_results(results: Dict[str, Any], output_path: str) -> None:
    """
    Save OCR results to a JSON file.
    
    Args:
        results: Dictionary containing OCR results
        output_path: Path where to save the JSON file
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    except Exception as e:
        raise Exception(f"Failed to save OCR results: {str(e)}")