from django.apps import AppConfig


class BillsNewConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "bills_new"
    
    def ready(self):
        import bills_new.signals
