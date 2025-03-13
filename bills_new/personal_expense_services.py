from django.db import transaction
from decimal import Decimal
from .models import Person, Bill, BillItem, ItemShare, BillParticipant, Payment, SplitType

class PersonalExpenseService:
    @staticmethod
    @transaction.atomic
    def create_expense(validated_data, created_by):
        bill_data = validated_data.get('bill', {})
        # Create the bill marked as personal expense
        bill = Bill.objects.create(
            title=bill_data.get('title'),
            description=bill_data.get('description', ''),
            date=bill_data.get('date'),
            created_by=created_by,
            is_personal=True,
        )
        # Dictionary to hold the calculated owed amounts per person
        person_totals = {}

        # Process each bill item
        for item_data in validated_data.get('items', []):
            bill_item = BillItem.objects.create(
                bill=bill,
                name=item_data.get('name'),
                price=item_data.get('price')
            )
            shares_data = item_data.get('shares', [])
            owner_share_sum = Decimal('0.00')
            # Process provided shares (ideally for the owner only)
            for share_data in shares_data:
                person_id = share_data.get('person_id')
                person = Person.objects.get(id=person_id)
                split_type = share_data.get('split_type')

                # Convert numeric values to appropriate types
                percentage = None
                if share_data.get('percentage') is not None:
                    percentage = Decimal(str(share_data.get('percentage')))
                exact_amount = None
                if share_data.get('exact_amount') is not None:
                    exact_amount = Decimal(str(share_data.get('exact_amount')))
                share_units = None
                if share_data.get('share_units') is not None:
                    try:
                        share_units = int(share_data.get('share_units'))
                    except (ValueError, TypeError):
                        share_units = 0

                item_share = ItemShare(
                    item=bill_item,
                    person=person,
                    split_type=split_type,
                    percentage=percentage,
                    exact_amount=exact_amount,
                    share_units=share_units
                )
                item_share.save()
                share_amount = PersonalExpenseService._calculate_share_amount(item_share, bill_item.price, shares_data)
                if person_id not in person_totals:
                    person_totals[person_id] = Decimal('0.00')
                person_totals[person_id] += share_amount
                if person == created_by:
                    owner_share_sum += share_amount
            # For any item where the owner's provided share is less than the item price,
            # automatically assign the remainder to the "others" person.
            remainder = bill_item.price - owner_share_sum
            if remainder > Decimal('0.00'):
                others_person = Person.objects.get_others_person()
                dummy_share = ItemShare(
                    item=bill_item,
                    person=others_person,
                    split_type=SplitType.EXACT,
                    exact_amount=remainder
                )
                dummy_share.save()
                dummy_id = others_person.id
                if dummy_id not in person_totals:
                    person_totals[dummy_id] = Decimal('0.00')
                person_totals[dummy_id] += remainder

        # Create BillParticipant records using the computed totals
        for person_id, amount in person_totals.items():
            person = Person.objects.get(id=person_id)
            BillParticipant.objects.create(
                bill=bill,
                person=person,
                owed_amount=amount
            )

        # Process any bill payments provided
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
        """
        Calculate the amount for a given item share.
        This uses the provided split type; if the share type is not provided,
        the default equal split is used.
        """
        if item_share.split_type == SplitType.EXACT:
            return item_share.exact_amount or Decimal('0.00')
        elif item_share.split_type == SplitType.PERCENTAGE:
            return item_price * (item_share.percentage or Decimal('0.00')) / Decimal('100.00')
        elif item_share.split_type == SplitType.SHARES:
            total_shares = sum(int(s.get('share_units', 0)) for s in all_shares_data if s.get('split_type') == SplitType.SHARES)
            if total_shares > 0 and item_share.share_units:
                return item_price * Decimal(item_share.share_units) / Decimal(total_shares)
        else:  # Equal split
            equal_count = sum(1 for s in all_shares_data if s.get('split_type') == SplitType.EQUAL)
            if equal_count > 0:
                return item_price / Decimal(equal_count)
        return Decimal('0.00')
