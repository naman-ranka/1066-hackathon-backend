from django.db import models
from django.contrib.auth import get_user_model  # Import for ForeignKey to User

User = get_user_model()  # Best practice for referencing the User model

class Task(models.Model):
    STATUS_CHOICES = (
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('blocked', 'Blocked'),
        ('completed', 'Completed'),
        ('testing', 'Testing'),
    )

    TASK_TYPE_CHOICES = (
        ('ocr_script', 'OCR Script Development'),
        ('api_endpoint', 'API Endpoint Creation'),
        ('frontend_ui', 'Frontend UI Development'),
        ('model_creation', 'Database Model Creation'),
        ('authentication', 'Authentication Implementation'),
        ('prompt_tuning', 'LLM Prompt Tuning'),
        ('general', 'General Task'),  # For tasks that don't fit other categories
    )

    title = models.CharField(max_length=255)  # Keep a concise title
    description = models.TextField()       # Keep for general description
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    task_type = models.CharField(max_length=50, choices=TASK_TYPE_CHOICES, default='general')

    # --- NEW FIELDS ---
    assigned_to = models.CharField(max_length=255, null=True, blank=True, help_text="Name of the person assigned to this task")
    due_date = models.DateField(null=True, blank=True)  # Optional due date
    estimated_hours = models.FloatField(null=True, blank=True) # Optional time estimate
    actual_hours = models.FloatField(null=True, blank=True)    # Track actual time spent

    # Fields specific to certain task types (can be nullable)
    related_app = models.CharField(max_length=100, null=True, blank=True, help_text="e.g., 'bills', 'llm', 'frontend'") # Relate to the relevant Django App or Frontend component.
    related_file = models.CharField(max_length=255, null=True, blank=True, help_text="e.g., 'llm/views.py', 'components/ItemsSection.jsx'")  # File path
    api_endpoint = models.CharField(max_length=255, null=True, blank=True, help_text="e.g., '/api/llm/upload-receipt/'") #For API endpoint tasks
    ocr_engine = models.CharField(max_length=50, null=True, blank=True, choices=(('tesseract', 'Tesseract'), ('google', 'Google Cloud Vision')), help_text="For OCR tasks") #If it relates to ocr engine selection
    is_bill_splitting_task = models.BooleanField(default=False) # A general flag if it is related to the main app functionality.

    def __str__(self):
        return self.title