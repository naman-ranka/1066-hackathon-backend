from django.db import transaction
from decimal import Decimal
from .models import Person, Group, Bill, BillParticipant, BillItem, ItemShare, Payment
from .models import SplitType


class BillService:
    @staticmethod
    @transaction.atomic
    def create_bill(validated_data, created_by):
        """
        Creates a bill with all its related records (items, shares, participants)
        using the validated data from the serializer.
        """
        # Extract and create bill
        bill_data = validated_data.get('bill', {})
        group_id = validated_data.get('group_id')
        group = Group.objects.get(id=group_id) if group_id else None
        
        bill = Bill.objects.create(
            title=bill_data.get('title'),
            description=bill_data.get('description', ''),
            date=bill_data.get('date'),
            created_by=created_by,
            group=group
        )
        
        # Track person totals for creating bill participants
        person_totals = {}
        
        # Process items and their shares
        for item_data in validated_data.get('items', []):
            # Create bill item
            bill_item = BillItem.objects.create(
                bill=bill,
                name=item_data.get('name'),
                price=item_data.get('price')
            )
            
            # Process item shares
            shares_data = item_data.get('shares', [])
            
            # Calculate share amounts based on split type
            for share_data in shares_data:
                person_id = share_data.get('person_id')
                person = Person.objects.get(id=person_id)
                split_type = share_data.get('split_type')
                
                # Create share
                item_share = ItemShare(
                    item=bill_item,
                    person=person,
                    split_type=split_type,
                    percentage=share_data.get('percentage'),
                    exact_amount=share_data.get('exact_amount'),
                    share_units=share_data.get('share_units')
                )
                item_share.save()
                
                # Calculate share amount manually since we can't rely on the property yet
                share_amount = BillService._calculate_share_amount(
                    item_share, bill_item.price, shares_data
                )
                
                # Track person totals
                if person_id not in person_totals:
                    person_totals[person_id] = Decimal('0')
                person_totals[person_id] += share_amount
        
        # Create bill participants
        for person_id, amount in person_totals.items():
            person = Person.objects.get(id=person_id)
            BillParticipant.objects.create(
                bill=bill,
                person=person,
                owed_amount=amount
            )
        
        # Process payments if provided
        for payment_data in validated_data.get('bill_paid_by', []):
            person_id = payment_data.get('person_id')
            amount = payment_data.get('amount')
            
            person = Person.objects.get(id=person_id)
            Payment.create_bill_payment(
                person=person,
                bill=bill,
                amount=amount,
                date=bill.date,
                description=f"Payment for {bill.title}"
            )
            
        return bill
    
    @staticmethod
    def _calculate_share_amount(item_share, item_price, all_shares_data):
        """Helper method to calculate share amount before saving"""
        if item_share.split_type == SplitType.EXACT:
            return item_share.exact_amount or Decimal('0.00')
            
        elif item_share.split_type == SplitType.PERCENTAGE:
            return item_price * (item_share.percentage or Decimal('0.00')) / Decimal('100.00')
            
        elif item_share.split_type == SplitType.SHARES:
            total_shares = sum(s.get('share_units', 0) for s in all_shares_data 
                              if s.get('split_type') == SplitType.SHARES)
            if total_shares > 0 and item_share.share_units:
                return item_price * Decimal(item_share.share_units) / Decimal(total_shares)
                
        else:  # Equal split
            equal_split_count = sum(1 for s in all_shares_data if s.get('split_type') == SplitType.EQUAL)
            if equal_split_count > 0:
                return item_price / Decimal(equal_split_count)
                
        return Decimal('0.00')
