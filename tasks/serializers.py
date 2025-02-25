#tasks/serializers.py
from rest_framework import serializers
from .models import Task

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'
        extra_kwargs = {
            'assigned_to': {'required': False},
            'due_date': {'required': False},
            'estimated_hours': {'required': False},
            'actual_hours': {'required': False},
            'related_app': {'required': False},
            'related_file': {'required': False},
            'api_endpoint': {'required': False},
            'ocr_engine': {'required': False}
        }