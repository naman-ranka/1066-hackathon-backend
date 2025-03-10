import pytesseract
from PIL import Image
import os

# Set tesseract path for Linux - it's already in the system PATH
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

def get_ocr_text_from_multiple_images(image_paths):
    """
    Performs OCR on a list of images and combines the extracted text.

    Args:
        image_paths: A list of paths to image files.

    Returns:
        A string containing the combined OCR text from all images,
        or None if there's an error in processing any image.
    """

    combined_text = ""
    for image_path in image_paths:
        try:
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img)  # Perform OCR
            combined_text += f"\n--- OCR Result for: {os.path.basename(image_path)} ---\n" + text
        except Exception as e:
            print(f"Error processing image: {image_path} - {e}")
            return None  # Indicate an error occurred

    return combined_text

if __name__ == "__main__":
    # Example Usage
    image_file_paths = [
        "test_images/1.jpeg",
        "test_images/2.jpeg",
        "test_images/3.jpeg",
        "test_images/4.jpeg",
        "test_images/5.jpeg",
        "test_images/6.jpeg",
        "test_images/7.jpeg",
        "test_images/8.jpeg"
    ]

    combined_ocr_output = get_ocr_text_from_multiple_images(image_file_paths)

    if combined_ocr_output:
        print("--- Combined OCR Text from All Images ---")
        print(combined_ocr_output)
    else:
        print("OCR processing failed for one or more images. Check error messages above.")