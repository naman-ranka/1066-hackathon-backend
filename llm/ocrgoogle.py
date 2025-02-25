from google.cloud import vision
import os

def get_ocr_text_from_multiple_images_google_api(image_paths):
    """
    Performs OCR on a list of images using Google Cloud Vision API
    and combines the extracted text.

    Args:
        image_paths: A list of paths to image files.

    Returns:
        A string containing the combined OCR text from all images,
        or None if there's an error in processing any image.
    """

    combined_text = ""
    client = vision.ImageAnnotatorClient()  # Initialize Vision API client

    for image_path in image_paths:
        try:
            with open(image_path, 'rb') as image_file:
                content = image_file.read()

            image = vision.Image(content=content)
            response = client.text_detection(image=image)  # Use text_detection for general text

            if response.error.message:
                raise Exception(
                    '{}\nFor more info on error messages, check: '
                    'https://cloud.google.com/apis/design/errors'.format(
                        response.error.message))

            image_text = ""
            for page in response.full_text_annotation.pages:
                for block in page.blocks:
                    for paragraph in block.paragraphs:
                        for word in paragraph.words:
                            word_text = ''.join([symbol.text for symbol in word.symbols])
                            image_text += word_text + " "
                        image_text += "\n"  # Paragraph break

            combined_text += f"\n--- OCR Result for: {os.path.basename(image_path)} ---\n" + image_text

        except Exception as e:
            print(f"Error processing image: {image_path} - {e}")
            print(f"Google Vision API Error Details: {e}") # Print detailed error for debugging
            return None  # Indicate an error occurred

    return combined_text

if __name__ == "__main__":
    # --- Configuration ---
    # 1. **Set up Google Cloud Project and Enable Vision API:**
    #    - Go to: https://console.cloud.google.com/
    #    - Create a new project or select an existing one.
    #    - Enable the "Cloud Vision API" for your project.
    # 2. **Install Google Cloud Client Library for Vision:**
    #    - `pip install google-cloud-vision`
    # 3. **Set up Authentication (VERY IMPORTANT):**
    #    - **Recommended: Service Account Key (JSON file):**
    #      - In your Google Cloud Console, go to "IAM & Admin" -> "Service Accounts".
    #      - Create a service account (or use an existing one).
    #      - Grant it the "Cloud Vision API" role.
    #      - Create a JSON key file for the service account and download it.
    #      - **Set the GOOGLE_APPLICATION_CREDENTIALS environment variable** to the path of this JSON key file.
    #        Example (in your terminal before running the script):
    #        `export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service_account_key.json"` (Linux/macOS)
    #        `set GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\your\service_account_key.json` (Windows)
    #    - **Alternatively (less secure for production, OK for local testing): Google Cloud SDK (gcloud auth):**
    #      - If you have the Google Cloud SDK installed and configured (`gcloud init`, `gcloud auth login`),
    #        the script might be able to authenticate using your active gcloud account.
    #        However, using a service account key is generally more robust and recommended.

    # --- Example Usage ---
    image_file_paths = [
        "image1.jpg",  # Replace with your image file paths
        "image2.png",
        "image3.jpeg",
        # Add more image paths here
    ]

    # Create dummy image files for testing if you don't have any ready
    # (You'd typically get these from user input or a folder)
    for file_path in image_file_paths:
        if not os.path.exists(file_path):
            print(f"Warning: '{file_path}' not found. Please replace with actual image paths.")
            # You could create empty files or placeholder images for testing.

    combined_ocr_output = get_ocr_text_from_multiple_images_google_api(image_file_paths)

    if combined_ocr_output:
        print("--- Combined OCR Text from All Images (Google Cloud Vision API) ---")
        print(combined_ocr_output)
    else:
        print("OCR processing failed for one or more images using Google Cloud Vision API. Check error messages above and your Google Cloud setup.")