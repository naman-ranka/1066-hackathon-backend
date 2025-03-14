import cv2
import numpy as np
from typing import Union, Tuple, List, Dict, Optional
import io
from PIL import Image

def detect_and_crop_receipt(image: np.ndarray) -> np.ndarray:
    """
    Detect and crop the receipt/bill from the image background.
    
    Args:
        image: Input image as numpy array
        
    Returns:
        numpy.ndarray: Cropped image containing just the receipt
    """
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Apply adaptive thresholding
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
    )
    
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return image
    
    # Find the largest contour by area
    largest_contour = max(contours, key=cv2.contourArea)
    
    # Get the minimum area rectangle
    rect = cv2.minAreaRect(largest_contour)
    box = cv2.boxPoints(rect)
    box = np.array(box, dtype=np.int32)  # Changed from np.int0 to np.int32
    
    # Get width and height of the detected rectangle
    width = int(rect[1][0])
    height = int(rect[1][1])
    
    # Handle cases where width and height might be swapped
    if width < height:
        width, height = height, width
    
    # Get the perspective transform
    src_pts = box.astype("float32")
    dst_pts = np.array([
        [0, height-1],
        [0, 0],
        [width-1, 0],
        [width-1, height-1]
    ], dtype="float32")
    
    # Apply perspective transform
    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
    warped = cv2.warpPerspective(image, M, (width, height))
    
    return warped

def apply_canny_edge_detection(
    image_data: Union[bytes, np.ndarray],
    low_threshold: int = 50,
    high_threshold: int = 150,
    blur_kernel_size: Tuple[int, int] = (5, 5)
) -> np.ndarray:
    """
    Apply Canny edge detection to an image.
    
    Args:
        image_data: Image data either as bytes or numpy array
        low_threshold: Lower threshold for edge detection (default: 50)
        high_threshold: Higher threshold for edge detection (default: 150)
        blur_kernel_size: Kernel size for Gaussian blur (default: (5,5))
    
    Returns:
        numpy.ndarray: Edge detected image
    """
    # Convert bytes to numpy array if needed
    if isinstance(image_data, bytes):
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    else:
        img = image_data

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, blur_kernel_size, 0)
    
    # Apply Canny edge detection
    edges = cv2.Canny(blurred, low_threshold, high_threshold)
    
    return edges

def enhance_image_for_ocr(
    image_data: bytes,
    apply_edges: bool = True,
    denoise: bool = True,
    sharpen: bool = True,
    crop_receipt: bool = True,
    edge_params: Optional[Dict] = None
) -> bytes:
    """
    Enhance image for better OCR results using multiple preprocessing techniques.
    
    Args:
        image_data: Raw image bytes
        apply_edges: Whether to apply edge detection
        denoise: Whether to apply denoising
        sharpen: Whether to apply sharpening
        crop_receipt: Whether to detect and crop the receipt
        edge_params: Optional dictionary with edge detection parameters:
            - low_threshold: int (default: 50)
            - high_threshold: int (default: 150)
    
    Returns:
        bytes: Processed image in bytes format
    """
    # Convert bytes to numpy array
    nparr = np.frombuffer(image_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # First, try to detect and crop the receipt if requested
    if crop_receipt:
        img = detect_and_crop_receipt(img)
    
    # Create a copy for edge detection
    img_edges = None
    if apply_edges:
        # Get edge detection parameters
        edge_params = edge_params or {}
        low_threshold = edge_params.get('low_threshold', 50)
        high_threshold = edge_params.get('high_threshold', 150)
        
        img_edges = apply_canny_edge_detection(
            img, 
            low_threshold=low_threshold,
            high_threshold=high_threshold
        )
        # Convert back to 3 channels
        img_edges = cv2.cvtColor(img_edges, cv2.COLOR_GRAY2BGR)
    
    # Denoise the image
    if denoise:
        img = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
    
    # Sharpen the image
    if sharpen:
        kernel = np.array([[-1,-1,-1],
                         [-1, 9,-1],
                         [-1,-1,-1]])
        img = cv2.filter2D(img, -1, kernel)
    
    # Combine edge detection with original image if edges were detected
    if img_edges is not None:
        img = cv2.addWeighted(img, 0.7, img_edges, 0.3, 0)
    
    # Convert back to bytes
    success, buffer = cv2.imencode('.jpg', img)
    if not success:
        raise ValueError("Failed to encode processed image")
    
    return io.BytesIO(buffer).getvalue()

def batch_process_images(
    image_data_list: List[bytes],
    apply_edges: bool = True,
    denoise: bool = True,
    sharpen: bool = True,
    crop_receipt: bool = True,
    edge_params: Optional[Dict] = None
) -> List[bytes]:
    """
    Process multiple images in batch.

    Args:
        image_data_list: List of image data in bytes format
        apply_edges: Whether to apply edge detection to all images
        denoise: Whether to apply denoising to all images
        sharpen: Whether to apply sharpening to all images
        crop_receipt: Whether to detect and crop receipts
        edge_params: Optional dictionary with edge detection parameters
    
    Returns:
        List[bytes]: List of processed images in bytes format
    """
    return [
        enhance_image_for_ocr(
            img_data, 
            apply_edges=apply_edges,
            denoise=denoise,
            sharpen=sharpen,
            crop_receipt=crop_receipt,
            edge_params=edge_params
        ) for img_data in image_data_list
    ]

#test on an image 
if __name__ == "__main__":
    # Example usage
    image_path = 'test_images/receipt.jpg'
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    processed_image = enhance_image_for_ocr(image_data)
    
    # Save the processed image for verification
    with open('processed_image.jpg', 'wb') as f:
        f.write(processed_image)