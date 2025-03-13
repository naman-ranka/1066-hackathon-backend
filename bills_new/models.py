from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

class PersonManager(models.Manager):
    def get_others_person(self):
        """Get or create the special 'Others' person used for personal expense tracking"""
        others_user, created = User.objects.get_or_create(
            username='__others__',
            defaults={
                'first_name': 'Others',
                'last_name': '',
                'email': 'others@example.com',
                'is_active': False  # This user should never be able to log in
            }
        )
        
        others_person, created = self.get_or_create(
            user=others_user,
            defaults={
                'phone_number': ''
            }
        )
        
        return others_person



class Person(models.Model):
    """
    Extends Django's built-in User model using a one-to-one relationship.
    Provides additional user-related fields.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=15, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)

    objects = PersonManager()
    
    def __str__(self):
        return self.user.username


class Group(models.Model):
    """
    Represents a group of people who frequently split bills together.
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='created_groups')
    members = models.ManyToManyField(Person, related_name='member_groups')  # Changed related_name to avoid clash
    
    def __str__(self):
        return self.name


class Bill(models.Model):
    """
    Represents a bill that needs to be split among people.
    """
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='created_bills')
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True, related_name='bills')
    participants = models.ManyToManyField(Person, related_name='bills', through='BillParticipant')

    # Add is_personal field to flag personal expenses
    is_personal = models.BooleanField(default=False)
    
    def __str__(self):
        return self.title
    
    @property
    def total_amount(self):
        """Calculate the total amount of the bill."""
        return sum(item.price for item in self.items.all())


class BillParticipant(models.Model):
    """
    Represents a person's participation in a bill, tracking their share obligation.
    """
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='bill_participants')
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='bill_participations')
    owed_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    _cached_paid_amount = None
    
    # class Meta:
    #     unique_together = ('bill', 'person')
    
    def calculate_owed_amount(self):
        """Calculate and store how much this person owes for the bill."""
        from django.db import transaction
        
        with transaction.atomic():
            participant = BillParticipant.objects.select_for_update().get(pk=self.pk)
            calculated = sum(item_share.share_amount for item_share in 
                           participant.person.item_shares.filter(item__bill=participant.bill))
            participant.owed_amount = calculated
            participant.save()
            
            # Update our instance to match
            self.owed_amount = calculated
            
        return self.owed_amount
    
    @property
    def paid_amount(self):
        """Calculate how much this person has paid toward the bill."""
        from django.db.models import Sum
        from django.core.cache import cache
        
        # Try to get from instance cache first
        if self._cached_paid_amount is not None:
            return self._cached_paid_amount
        
        # Try to get from Redis/Memcached cache
        cache_key = f'bill_participant_{self.pk}_paid_amount'
        cached_value = cache.get(cache_key)
        if cached_value is not None:
            self._cached_paid_amount = cached_value
            return cached_value
        
        # Calculate if not in cache
        payments = Payment.objects.filter(
            payment_type='BILL',
            person=self.person,
            bill=self.bill
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        
        # Store in both caches
        self._cached_paid_amount = payments
        cache.set(cache_key, payments, timeout=300)  # Cache for 5 minutes
        
        return payments
    
    def invalidate_paid_amount_cache(self):
        """Invalidate the paid amount cache when a new payment is made."""
        from django.core.cache import cache
        cache_key = f'bill_participant_{self.pk}_paid_amount'
        cache.delete(cache_key)
        self._cached_paid_amount = None
    
    @property
    def balance(self):
        """Calculate balance (positive: person is owed, negative: person owes)."""
        return self.paid_amount - self.owed_amount


class BillItem(models.Model):
    """
    Represents an individual item in a bill.
    """
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        ordering = ['id']
    
    def __str__(self):
        return f"{self.name} (${self.price})"


class SplitType(models.TextChoices):
    """
    Defines different methods of splitting a bill item.
    """
    EQUAL = 'EQUAL', 'Split equally'
    PERCENTAGE = 'PERCENTAGE', 'Split by percentage'
    EXACT = 'EXACT', 'Split by exact amounts'
    SHARES = 'SHARES', 'Split by share units'
    ADJUSTED = 'ADJUSTED', 'Equal split with adjustments'


class ItemShare(models.Model):
    """
    Represents how a bill item is shared by a specific person.
    """
    item = models.ForeignKey(BillItem, on_delete=models.CASCADE, related_name='shares')
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='item_shares')
    split_type = models.CharField(max_length=20, choices=SplitType.choices, default=SplitType.EQUAL)
    
    # Depending on split_type, one of these will be used:
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    exact_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    share_units = models.IntegerField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['item', 'person']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['item', 'person'], name='unique_item_person_share')
        ]

    def clean(self):
        """Validate the item share based on its split type."""
        from django.core.exceptions import ValidationError
        from django.db.models import Sum
        
        if self.split_type == SplitType.PERCENTAGE:
            if self.percentage is None:
                raise ValidationError({'percentage': 'Percentage is required for percentage split type'})
            
            # Get total percentage for this item including this share
            existing_total = ItemShare.objects.filter(
                item=self.item,
                split_type=SplitType.PERCENTAGE
            ).exclude(pk=self.pk).aggregate(
                Sum('percentage')
            )['percentage__sum'] or Decimal('0.00')
            
            total_percentage = existing_total + self.percentage
            if total_percentage > 100:
                raise ValidationError({
                    'percentage': f'Total percentage ({total_percentage}%) exceeds 100%'
                })
                
        elif self.split_type == SplitType.EXACT:
            if self.exact_amount is None:
                raise ValidationError({'exact_amount': 'Exact amount is required for exact split type'})
            
            # Get total exact amount for this item including this share
            existing_total = ItemShare.objects.filter(
                item=self.item,
                split_type=SplitType.EXACT
            ).exclude(pk=self.pk).aggregate(
                Sum('exact_amount')
            )['exact_amount__sum'] or Decimal('0.00')
            
            total_amount = existing_total + self.exact_amount
            if total_amount > self.item.price:
                raise ValidationError({
                    'exact_amount': f'Total amount ({total_amount}) exceeds item price ({self.item.price})'
                })
                
        elif self.split_type == SplitType.SHARES:
            if self.share_units is None:
                raise ValidationError({'share_units': 'Share units is required for shares split type'})
            if self.share_units <= 0:
                raise ValidationError({'share_units': 'Share units must be positive'})
    
    def save(self, *args, **kwargs):
        """Override save to perform validation and handle concurrency."""
        from django.db import transaction
        
        # Validate before saving
        self.clean()
        
        with transaction.atomic():
            # Lock the related bill participant for update to prevent concurrent modifications
            # BillParticipant.objects.select_for_update().get_or_create(
            #     bill=self.item.bill,
            #     person=self.person
            # )
            
            # Save the item share
            super().save(*args, **kwargs)
            
            # Recalculate owed amount for the participant
            # participant = BillParticipant.objects.get(
            #     bill=self.item.bill,
            #     person=self.person
            # )
            # participant.calculate_owed_amount()
    
    @property
    def share_amount(self):
        """Calculate the actual amount this person owes for this item based on split type."""
        if self.split_type == SplitType.EXACT:
            return self.exact_amount or Decimal('0.00')
        
        if self.split_type == SplitType.PERCENTAGE:
            return self.item.price * (self.percentage or Decimal('0.00')) / Decimal('100.00')
        
        if self.split_type == SplitType.SHARES:
            total_shares = sum(share.share_units or 0 for share in self.item.shares.all())
            if total_shares > 0 and self.share_units:
                return self.item.price * Decimal(self.share_units) / Decimal(total_shares)
        
        # Default to equal split
        participants_count = self.item.shares.count()
        if participants_count > 0:
            return self.item.price / Decimal(participants_count)
        
        return Decimal('0.00')


class Payment(models.Model):
    """
    Represents a payment transaction between users.
    For settlements, two mirrored records are created (positive and negative).
    For bill payments, a single record is created.
    """
    PAYMENT_TYPES = [
        ('BILL', 'Bill Payment'),         # Payment toward a bill
        ('SETTLEMENT', 'Debt Settlement'), # Direct payment between users
    ]
    
    payment_type = models.CharField(max_length=10, choices=PAYMENT_TYPES)
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='payments')
    other_person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='involved_payments', 
                                    null=True, blank=True)  # The counterparty in the transaction
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # Can be positive or negative
    date = models.DateField()
    description = models.TextField(blank=True)
    
    # Optional bill reference (can be null for direct settlements)
    bill = models.ForeignKey(Bill, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    
    # For linking paired settlement records
    paired_payment = models.OneToOneField('self', on_delete=models.CASCADE, null=True, blank=True, 
                                        related_name='counterpart')
    
    class Meta:
        indexes = [
            models.Index(fields=['payment_type', 'person', 'bill']),
            models.Index(fields=['payment_type', 'person', 'other_person']),
        ]

    def __str__(self):
        if self.payment_type == 'BILL':
            return f"{self.person} contributed {abs(self.amount)} to bill: {self.bill}"
        else:
            direction = "paid" if self.amount > 0 else "received"
            return f"{self.person} {direction} {abs(self.amount)} {'to' if self.amount > 0 else 'from'} {self.other_person}"
    
    @classmethod
    def create_settlement(cls, from_person, to_person, amount, date, description=""):
        """
        Creates a pair of settlement records - one positive (from payer) and one negative (to receiver).
        Returns the primary payment record (from payer).
        """
        # Create payer's record (positive amount - money going out)
        payer_payment = cls.objects.create(
            payment_type='SETTLEMENT',
            person=from_person,
            other_person=to_person,
            amount=amount,  # Positive amount
            date=date,
            description=description
        )
        
        # Create receiver's record (negative amount - money coming in)
        receiver_payment = cls.objects.create(
            payment_type='SETTLEMENT',
            person=to_person,
            other_person=from_person,
            amount=-amount,  # Negative amount
            date=date,
            description=description
        )
        
        # Link the two payments
        payer_payment.paired_payment = receiver_payment
        receiver_payment.paired_payment = payer_payment
        payer_payment.save()
        receiver_payment.save()
        
        return payer_payment
    
    @classmethod
    def create_bill_payment(cls, person, bill, amount, date, description=""):
        """
        Creates a bill payment record.
        This represents a contribution to a bill's total amount.
        """
        from django.db import transaction
        
        with transaction.atomic():
            payment = cls.objects.create(
                payment_type='BILL',
                person=person,
                bill=bill,
                amount=amount,
                date=date,
                description=description
            )
            
            # Make sure the person is a participant in the bill
            participant, created = BillParticipant.objects.get_or_create(
                bill=bill,
                person=person
            )
            
            # If the participant is new, calculate their share
            if created:
                participant.calculate_owed_amount()
            
            # Always invalidate the paid amount cache when a new payment is made
            participant.invalidate_paid_amount_cache()
            
            return payment
    
    @classmethod
    def get_balance(cls, person):
        """
        Calculate the total balance for a person across all settlements.
        Positive value means the person is owed money.
        Negative value means the person owes money.
        """
        # Sum all settlement payment amounts for this person
        settlements = cls.objects.filter(
            person=person,
            payment_type='SETTLEMENT'
        ).aggregate(models.Sum('amount'))['amount__sum'] or Decimal('0.00')
        
        return settlements
    
    @classmethod
    def get_balance_between(cls, person1, person2):
        """
        Calculate the balance between two people.
        Returns how much person1 owes person2 (negative if person1 owes, positive if person1 is owed).
        """
        from django.db.models import Sum
        # Get relevant payments where these two people are involved
        payments_to_consider = cls.objects.filter(
            payment_type='SETTLEMENT',
            person=person1,
            other_person=person2
        )
        
        # Sum them up
        balance = payments_to_consider.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        return balance
    
    @classmethod
    def get_bill_contributions(cls, bill):
        """
        Get all contributions made toward a specific bill.
        """
        return cls.objects.filter(
            payment_type='BILL',
            bill=bill
        )
