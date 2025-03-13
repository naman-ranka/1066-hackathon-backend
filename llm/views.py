import os
import base64
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .utils import (
    process_receipt_with_openai, 
    process_receipt_with_gemini,
    process_images_bytes,
    process_ocr_text_with_llm,
    OCRProvider
)
from rest_framework.decorators import api_view
from PIL import Image
import tempfile
import io


class ProcessReceiptView(APIView):
    """
    Accepts an image upload and processes it using the configured LLM.
    """
    def post(self, request, format=None):
        if "file" not in request.FILES:
            return Response(
                {"error": "No file uploaded."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            image_data = request.FILES["file"].read()
            bill_content = process_receipt_with_gemini(image_data)
            #print(bill_content)
            print("bill_content: ", bill_content)
            return Response(
                {"bill": bill_content}, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['POST'])
def process_bill_images(request):
    """
    Process multiple bill images using OCR and LLM.
    Expected request format:
    - Files can be sent as multipart form data with field names 'files[]', 'file', or 'images'
    - Optional query parameter 'provider': 'google_cloud' or 'tesseract' (defaults to google_cloud)
    - Optional query parameter 'custom_prompt': Custom prompt for LLM processing
    """
    # Check for files in both standard file upload and multipart form data
    files = request.FILES.getlist('files[]') or request.FILES.getlist('file') or request.FILES.getlist('images')
    
    if not files:
        return Response(
            {"error": "No files uploaded. Please send image files with field name 'files[]', 'file', or 'images'."}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    provider_name = request.POST.get('provider', 'google_cloud')
    custom_prompt = request.POST.get('custom_prompt', None)

    try:
        # Validate provider
        try:
            provider = OCRProvider(provider_name)
        except ValueError:
            return Response(
                {'error': f'Invalid provider. Choose from: {[p.value for p in OCRProvider]}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Process images directly from memory
        image_bytes_list = []
        
        for file in files:
            if not file.content_type.startswith('image/'):
                return Response(
                    {"error": f"Invalid file type: {file.content_type}. Please upload only image files."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Read the file content directly
            file_bytes = file.read()
            image_bytes_list.append(file_bytes)
            
        # Step 1: Process the images with OCR
        ocr_results = process_images_bytes(image_bytes_list, provider)
        
        # Step 2: Extract and combine OCR text from results
        combined_ocr_text = ""
        for result in ocr_results['results']:
            if 'text' in result:
                combined_ocr_text += result['text'] + "\n\n"
            elif 'error' in result:
                return Response(
                    {'error': f"OCR Error: {result['error']}"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        # Step 3: Process OCR text with LLM
        try:
            llm_response = process_ocr_text_with_llm(combined_ocr_text, custom_prompt)
            
            # Return both OCR and LLM results
            # response_data = {
            #     'ocr_results': ocr_results,
            #     'llm_analysis': llm_response
            # }
            response_data = {
                'bill': llm_response
            }
            print(llm_response)
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f"LLM Processing Error: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# write a fucntion to process the image using google ocr and llm gemini  and output the responce 
def process_receipt_with_OCR_LLM(image_data: bytes, provider: OCRProvider = OCRProvider.GOOGLE_CLOUD, custom_prompt: str = None) -> dict:
    """
    Process a single receipt image using OCR and LLM analysis.
    
    Args:
        image_data: Raw image bytes to process
        provider: OCRProvider enum specifying which OCR service to use (default: google_cloud)
        custom_prompt: Optional custom prompt for LLM processing
    
    Returns:
        Dictionary containing OCR results and LLM analysis
    
    Raises:
        ValueError: If image data is invalid
        RuntimeError: If OCR or LLM processing fails
    """
    if not image_data:
        raise ValueError("No image data provided")
    
    try:
        # Process the image with OCR
        ocr_results = process_images_bytes([image_data], provider)
        
        # Extract OCR text from results
        if not ocr_results['results'] or 'text' not in ocr_results['results'][0]:
            raise RuntimeError("OCR failed to extract text from the image")
            
        ocr_text = ocr_results['results'][0]['text']
        
        # Process OCR text with LLM
        llm_response = process_ocr_text_with_llm(ocr_text, custom_prompt)
        
        return {
            'ocr_results': ocr_results,
            'llm_analysis': llm_response
        }
        # print llm response 
        print(llm_response)
    except Exception as e:
        raise RuntimeError(f"Error processing receipt: {str(e)}")
