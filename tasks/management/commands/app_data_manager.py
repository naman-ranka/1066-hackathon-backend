import os
import json
from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction

APP_NAME = "tasks"  # Replace this with your actual app name
EXPORT_FILE = f"{APP_NAME}_data.json"

class Command(BaseCommand):
    help = "Export, empty, and import data for a specific Django app"

    def add_arguments(self, parser):
        parser.add_argument("operation", type=str, choices=["export", "empty", "import"], help="Operation to perform")

    def handle(self, *args, **kwargs):
        operation = kwargs["operation"]
        
        if operation == "export":
            self.export_data()
        elif operation == "empty":
            self.empty_tables()
        elif operation == "import":
            self.import_data()
        else:
            self.stdout.write(self.style.ERROR("Invalid operation"))

    def export_data(self):
        """Exports all table data from the app into a JSON file."""
        data = {}
        models = apps.get_app_config(APP_NAME).get_models()

        for model in models:
            data[model.__name__] = list(model.objects.all().values())

        with open(EXPORT_FILE, "w") as f:
            json.dump(data, f, indent=4)

        self.stdout.write(self.style.SUCCESS(f"Data exported to {EXPORT_FILE}"))

    def empty_tables(self):
        """Deletes all data from tables belonging to the app."""
        models = apps.get_app_config(APP_NAME).get_models()

        with transaction.atomic():
            for model in models:
                model.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(f"All tables in '{APP_NAME}' emptied."))

    def import_data(self):
        """Imports data from JSON into the app's tables."""
        if not os.path.exists(EXPORT_FILE):
            self.stdout.write(self.style.ERROR(f"No export file found: {EXPORT_FILE}"))
            return

        with open(EXPORT_FILE, "r") as f:
            data = json.load(f)

        models = {model.__name__: model for model in apps.get_app_config(APP_NAME).get_models()}

        with transaction.atomic():
            for model_name, records in data.items():
                if model_name in models:
                    model = models[model_name]
                    model.objects.bulk_create([model(**record) for record in records])

        self.stdout.write(self.style.SUCCESS(f"Data imported from {EXPORT_FILE}"))

