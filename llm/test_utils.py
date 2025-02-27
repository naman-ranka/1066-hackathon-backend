import os
import unittest
import io
from unittest.mock import patch, MagicMock
from PIL import Image
import base64
import sys
import django

# Setup Django environment
sys.path.append('/home/naman/bill-split/back-end/1066-hackathon-backend')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hackathon_backend.settings")
django.setup()

from llm.utils import (
    encode_image_to_base64,
    read_prompt_file,
    process_receipt_with_openai,
    process_receipt_with_gemini,
    process_multiple_images_ocr
)

class TestUtilsFunctions(unittest.TestCase):
    """Test cases for functions in utils.py"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_image_dir = os.path.join(os.path.dirname(__file__), 'ocrtestimages')
        os.makedirs(self.test_image_dir, exist_ok=True)

        # Create a test image for testing
        self.create_test_image_if_needed()
        
        # Mock environment variables
        os.environ["OPENAI_API_KEY"] = "test-openai-key"
        os.environ["GEMINI_API_KEY"] = "test-gemini-key"

    def create_test_image_if_needed(self):
        """Create a test image with text for OCR testing"""
        self.test_image_path = os.path.join(self.test_image_dir, 'test_receipt.png')
        
        if not os.path.exists(self.test_image_path):
            # Create a simple image with text for OCR
            img = Image.new('RGB', (300, 100), color='white')
            # You would normally use a library like PIL.ImageDraw to add text
            # But for simplicity, just saving a blank image
            img.save(self.test_image_path)
    
    def test_encode_image_to_base64(self):
        """Test encoding image to base64 string"""
        with open(self.test_image_path, 'rb') as f:
            image_data = f.read()
        
        # Call the function
        result = encode_image_to_base64(image_data)
        
        # Assert result is a string and has the correct format
        self.assertIsInstance(result, str)
        self.assertTrue(result.startswith('data:image/jpeg;base64,'))
        
        # Decode the base64 part to verify it's valid
        try:
            base64.b64decode(result.split('base64,')[1])
        except Exception:
            self.fail("Failed to decode base64 string")

    @patch('llm.utils.open')
    @patch('llm.utils.settings')
    def test_read_prompt_file(self, mock_settings, mock_open):
        """Test reading prompt file"""
        # Setup mock
        mock_settings.BASE_DIR = '/mock/path'
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = "test prompt"
        mock_open.return_value = mock_file
        
        # Call function
        result = read_prompt_file()
        
        # Assert result
        self.assertEqual(result, "test prompt")
        mock_open.assert_called_with(os.path.join('/mock/path', 'prompt.txt'), 'r', encoding='utf-8')

    @patch('llm.utils.openai')
    @patch('llm.utils.encode_image_to_base64')
    @patch('llm.utils.read_prompt_file')
    def test_process_receipt_with_openai(self, mock_read_prompt, mock_encode, mock_openai):
        """Test OpenAI receipt processing"""
        # Setup mocks
        mock_read_prompt.return_value = "Analyze this receipt"
        mock_encode.return_value = "data:image/jpeg;base64,testbase64string"
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "OpenAI analysis result"
        mock_openai.chat.completions.create.return_value = mock_response
        
        # Prepare test image
        with open(self.test_image_path, 'rb') as f:
            image_data = f.read()
        
        # Call function
        result = process_receipt_with_openai(image_data)
        
        # Assert results
        self.assertEqual(result, "OpenAI analysis result")
        mock_encode.assert_called_with(image_data)
        mock_read_prompt.assert_called_once()
        mock_openai.chat.completions.create.assert_called_once()

    @patch('llm.utils.genai')
    @patch('llm.utils.read_prompt_file')
    def test_process_receipt_with_gemini(self, mock_read_prompt, mock_genai):
        """Test Gemini receipt processing"""
        # Setup mocks
        mock_read_prompt.return_value = "Analyze this receipt"
        mock_response = MagicMock()
        mock_response.text = "Gemini analysis result"
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        # Prepare test image
        with open(self.test_image_path, 'rb') as f:
            image_data = f.read()
        
        # Call function
        result = process_receipt_with_gemini(image_data)
        
        # Assert results
        self.assertEqual(result, "Gemini analysis result")
        mock_read_prompt.assert_called_once()
        mock_genai.configure.assert_called_once()
        mock_genai.GenerativeModel.assert_called_once()
        mock_model.generate_content.assert_called_once()

    @patch('llm.utils.pytesseract')
    def test_process_multiple_images_ocr(self, mock_pytesseract):
        """Test OCR processing on multiple images"""
        # Setup mocks
        mock_pytesseract.image_to_string.side_effect = ["OCR result 1", "OCR result 2"]
        
        # Create a list of test images
        image_list = []
        test_image_paths = [
            os.path.join(self.test_image_dir, 'test_receipt.png'),
            os.path.join(self.test_image_dir, 'test_receipt2.png')
        ]
        
        # Create second test image if needed
        if not os.path.exists(test_image_paths[1]):
            img = Image.new('RGB', (300, 100), color='white')
            img.save(test_image_paths[1])
        
        # Read images
        for path in test_image_paths:
            with open(path, 'rb') as f:
                image_list.append(f.read())
        
        # Call function
        result = process_multiple_images_ocr(image_list)
        
        # Assert results
        self.assertIn("OCR Result for Image 1", result)
        self.assertIn("OCR Result for Image 2", result)
        self.assertIn("OCR result 1", result)
        self.assertIn("OCR result 2", result)
        self.assertEqual(mock_pytesseract.image_to_string.call_count, 2)

if __name__ == '__main__':
    unittest.main()
