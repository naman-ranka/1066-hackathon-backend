from rest_framework import serializers
from .models import Bill, Participant, Item

class ParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Participant
        fields = ['id', 'name', 'amount_paid', 'amount_owed']

class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = [
            'id', 'name', 'quantity', 'price', 'tax_rate', 'split_type'
            # If you store splits/includedParticipants, you'd handle that here (perhaps as JSONField or separate tables)
        ]

class BillSerializer(serializers.ModelSerializer):
    # We want to handle nested writes for items and participants
    participants = ParticipantSerializer(many=True)
    items = ItemSerializer(many=True)

    class Meta:
        model = Bill
        fields = [
            'id', 'name', 'date', 'location', 'notes', 'total_amount',
            'participants', 'items',
        ]

    def create(self, validated_data):
        # Extract nested data
        participants_data = validated_data.pop('participants', [])
        items_data = validated_data.pop('items', [])
        
        # Create the Bill itself
        bill = Bill.objects.create(**validated_data)
        
        # Create Participant records
        for p_data in participants_data:
            Participant.objects.create(bill=bill, **p_data)

        # Create Item records
        for i_data in items_data:
            Item.objects.create(bill=bill, **i_data)

        return bill

    def update(self, instance, validated_data):
        # We must handle nested updates too, if you plan on editing existing bills

        participants_data = validated_data.pop('participants', [])
        items_data = validated_data.pop('items', [])

        # Update basic Bill fields
        instance.name = validated_data.get('name', instance.name)
        instance.date = validated_data.get('date', instance.date)
        instance.location = validated_data.get('location', instance.location)
        instance.notes = validated_data.get('notes', instance.notes)
        instance.total_amount = validated_data.get('total_amount', instance.total_amount)
        instance.save()

        # Re-create participants or update them
        # For simplicity, we might just delete all old participants & re-create
        instance.participants.all().delete()
        for p_data in participants_data:
            Participant.objects.create(bill=instance, **p_data)

        # Similarly for items
        instance.items.all().delete()
        for i_data in items_data:
            Item.objects.create(bill=instance, **i_data)

        return instance
