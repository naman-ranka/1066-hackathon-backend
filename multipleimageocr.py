import pytesseract
from PIL import Image
import os

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
    # --- Configuration ---
    # 1. **Install Tesseract OCR:**
    #    - Follow instructions for your operating system (e.g., `apt install tesseract-ocr` on Ubuntu,
    #      or download from Tesseract website for Windows/Mac).
    # 2. **Install pytesseract (Python library):**
    #    - `pip install pytesseract Pillow`

    # 3. **Set Tesseract path (if not in your system PATH)**:
    #    - Uncomment and modify the line below if pytesseract can't find Tesseract executable.
    #      Replace with the actual path to your tesseract.exe (Windows example).
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


    # --- Example Usage ---
    image_file_paths = [
        "test_images/1.jpeg",
        "test_images/2.jpeg",
        "test_images/3.jpeg",
        "test_images/4.jpeg",
        "test_images/5.jpeg",
        "test_images/6.jpeg",
        "test_images/7.jpeg",
        "test_images/8.jpeg",
        
    ]

    # Create dummy image files for testing if you don't have any ready
    # (You'd typically get these from user input or a folder)
    for file_path in image_file_paths:
        if not os.path.exists(file_path):
            print(f"Warning: '{file_path}' not found. Please replace with actual image paths.")
            # You could create empty files or placeholder images for testing.


    combined_ocr_output = get_ocr_text_from_multiple_images(image_file_paths)

    if combined_ocr_output:
        print("--- Combined OCR Text from All Images ---")
        print(combined_ocr_output)
    else:
        print("OCR processing failed for one or more images. Check error messages above.")