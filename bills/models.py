from django.db import models

class Bill(models.Model):
    name = models.CharField(max_length=255)
    date = models.DateField()
    location = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

class Participant(models.Model):
    bill = models.ForeignKey(Bill, related_name='participants', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_owed = models.DecimalField(max_digits=10, decimal_places=2, default=0)

class Item(models.Model):
    bill = models.ForeignKey(Bill, related_name='items', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    split_type = models.CharField(max_length=20, default='equal')
    # If you need "splits" in the DB, you could store JSON or many-to-many relations
