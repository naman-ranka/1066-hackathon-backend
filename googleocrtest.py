import os
import io
from google.cloud import vision
from typing import List, Dict
from pathlib import Path
from django.conf import settings

# Get the absolute path to the credentials file
BASE_DIR = Path(__file__).resolve().parent
CREDENTIALS_FILE = "coral-muse-452018-s2-171009389e4d.json"
CREDENTIALS_PATH = os.path.join(BASE_DIR, CREDENTIALS_FILE)

if not os.path.exists(CREDENTIALS_PATH):
    # Try one directory up if not found
    CREDENTIALS_PATH = os.path.join(BASE_DIR.parent, CREDENTIALS_FILE)

if not os.path.exists(CREDENTIALS_PATH):
    raise FileNotFoundError(f"Google Cloud credentials file not found. Tried paths: {BASE_DIR}/{CREDENTIALS_FILE} and {BASE_DIR.parent}/{CREDENTIALS_FILE}")

# Set credentials via absolute path
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(CREDENTIALS_PATH)

def detect_text(image_path: str) -> List[str]:
    # Instantiate a client for the Vision API
    client = vision.ImageAnnotatorClient()
    
    # Read the image file
    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()
    
    # Prepare the image for the API
    image = vision.Image(content=content)
    
    # Call the API's text detection method
    response = client.text_detection(image=image)
    texts = response.text_annotations
    
    # Handle any potential errors
    if response.error.message:
        raise Exception(f"API Error: {response.error.message}")
    
    # Return the detected text
    if texts:
        return [text.description for text in texts]
    return []

def process_multiple_images(image_paths: List[str]) -> Dict[str, List[str]]:
    """
    Process multiple images and return their text content.
    
    Args:
        image_paths: List of paths to image files
        
    Returns:
        Dictionary with image paths as keys and lists of detected text as values
    """
    results = {}
    for image_path in image_paths:
        try:
            results[image_path] = detect_text(image_path)
        except Exception as e:
            results[image_path] = [f"Error processing image: {str(e)}"]
    return results

if __name__ == '__main__':
    # Example usage with multiple images
    test_images = [
        os.path.join(BASE_DIR, "test_images", "1.jpeg"),
        os.path.join(BASE_DIR, "test_images", "2.jpeg"),
        os.path.join(BASE_DIR, "test_images", "3.jpeg"),
        os.path.join(BASE_DIR, "test_images", "4.jpeg"),
        os.path.join(BASE_DIR, "test_images", "5.jpeg"),
        os.path.join(BASE_DIR, "test_images", "6.jpeg"),
        os.path.join(BASE_DIR, "test_images", "7.jpeg"),
        os.path.join(BASE_DIR, "test_images", "8.jpeg")
    ]
    results = process_multiple_images(test_images)
    # save results in a text file names ocr-result.txt  
    with open(os.path.join(BASE_DIR, "ocr-result.txt"), "w") as f:
        for image_path, texts in results.items():
            f.write(f"\nResults for {image_path}:\n")
            if texts:
                f.write("\n".join(texts))
            else:
                f.write("No text found.")
            f.write("\n")
    # results in json file names ocr-result.json
    import json
    with open(os.path.join(BASE_DIR, "ocr-result.json"), "w") as f:
        json.dump(results, f)
                
    # Print results
    for image_path, texts in results.items():
        print(f"\nResults for {image_path}:")
        if texts:
            print("\n".join(texts))
        else:
            print("No text found.")
