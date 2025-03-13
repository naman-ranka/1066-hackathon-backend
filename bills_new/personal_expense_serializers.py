from rest_framework import serializers
from decimal import Decimal
from .models import SplitType

class BillItemPersonalExpenseSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    # For personal expense items the frontend sends a list of share dicts.
    # (They should normally only include the owner’s share.)
    shares = serializers.ListField(child=serializers.DictField())

    def validate(self, data):
        price = data.get('price')
        if price <= 0:
            raise serializers.ValidationError("Item price must be positive")
        total_provided = Decimal('0.00')
        shares_data = data.get('shares', [])
        # For EQUAL splits the calculation uses the count provided.
        equal_count = sum(1 for s in shares_data if s.get('split_type') == SplitType.EQUAL)
        total_shares_units = sum(s.get('share_units', 0) for s in shares_data if s.get('split_type') == SplitType.SHARES)
        for s in shares_data:
            st = s.get('split_type')
            if st == SplitType.EXACT:
                amount = Decimal(str(s.get('exact_amount', '0')))
            elif st == SplitType.PERCENTAGE:
                amount = price * Decimal(str(s.get('percentage', '0'))) / Decimal('100')
            elif st == SplitType.SHARES:
                if total_shares_units > 0:
                    amount = price * Decimal(s.get('share_units', 0)) / Decimal(total_shares_units)
                else:
                    amount = Decimal('0')
            else:  # EQUAL split
                if equal_count > 0:
                    amount = price / Decimal(equal_count)
                else:
                    amount = Decimal('0')
            total_provided += amount
        if total_provided > price:
            raise serializers.ValidationError("Total provided share amounts exceed item price")
        return data

class PaymentSerializer(serializers.Serializer):
    person_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)

    def validate(self, data):
        if data.get('amount', Decimal('0')) <= 0:
            raise serializers.ValidationError("Payment amount must be positive")
        return data

class PersonalExpenseSerializer(serializers.Serializer):
    bill = serializers.DictField()  # Expect keys such as title, description, date, is_personal
    bill_total = serializers.DecimalField(max_digits=10, decimal_places=2)
    items = BillItemPersonalExpenseSerializer(many=True)
    bill_paid_by = PaymentSerializer(many=True, required=False)

    def validate(self, data):
        bill_data = data.get('bill', {})
        if not bill_data.get('is_personal', False):
            raise serializers.ValidationError("Bill must be marked as personal expense (is_personal=True)")
        total = sum(item.get('price') for item in data.get('items', []))
        if abs(total - data.get('bill_total')) > Decimal('0.01'):
            raise serializers.ValidationError("bill_total does not match sum of item prices")
        return data
