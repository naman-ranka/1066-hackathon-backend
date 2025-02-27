from django.db import models
from decimal import Decimal
from typing import List, Dict, Any
import json

class Bill(models.Model):
    """
    Represents a bill or receipt that can be split among participants.
    
    Contains information about the bill itself (name, date, location),
    as well as relationships to the participants and items in the bill.
    """
    name = models.CharField(max_length=255)
    date = models.DateField()
    location = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', 'name']
        verbose_name = 'Bill'
        verbose_name_plural = 'Bills'
    
    def __str__(self) -> str:
        """String representation of the bill."""
        return f"{self.name} ({self.date}) - ${self.total_amount}"
    
    def calculate_total(self) -> Decimal:
        """Calculate the total amount of the bill from its items."""
        return sum((item.price * item.quantity for item in self.items.all()), Decimal('0.00'))
    
    def update_total(self) -> None:
        """Update the total_amount field based on items."""
        self.total_amount = self.calculate_total()
        self.save(update_fields=['total_amount'])

class Participant(models.Model):
    """
    Represents a person who participates in splitting a bill.
    
    Tracks how much they paid and how much they actually owe.
    """
    bill = models.ForeignKey(Bill, related_name='participants', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_owed = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Participant'
        verbose_name_plural = 'Participants'
        unique_together = ['bill', 'name']
    
    def __str__(self) -> str:
        """String representation of the participant."""
        return f"{self.name} (Paid: ${self.amount_paid}, Owes: ${self.amount_owed})"
    
    def calculate_balance(self) -> Decimal:
        """Calculate the balance for this participant (paid - owed)."""
        return self.amount_paid - self.amount_owed

class Item(models.Model):
    """
    Represents an individual item on a bill.
    
    Contains information about the item itself and how it should be split.
    """
    SPLIT_TYPE_CHOICES = [
        ('equal', 'Equal Split'),
        ('percentage', 'Percentage Split'),
        ('custom', 'Custom Split'),
        ('exempt', 'Some Exempt')
    ]
    
    bill = models.ForeignKey(Bill, related_name='items', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    split_type = models.CharField(max_length=20, default='equal', choices=SPLIT_TYPE_CHOICES)
    split_details = models.TextField(blank=True)  # JSON field to store custom split data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Item'
        verbose_name_plural = 'Items'
    
    def __str__(self) -> str:
        """String representation of the item."""
        return f"{self.name} ({self.quantity} x ${self.price})"
    
    def total_price(self) -> Decimal:
        """Calculate the total price of the item including quantity."""
        return self.price * self.quantity
    
    def get_split_details(self) -> Dict[str, Any]:
        """Parse and return the split details as a dictionary."""
        if not self.split_details:
            return {}
        try:
            return json.loads(self.split_details)
        except json.JSONDecodeError:
            return {}
    
    def set_split_details(self, details: Dict[str, Any]) -> None:
        """Convert and save split details as JSON string."""
        self.split_details = json.dumps(details)
