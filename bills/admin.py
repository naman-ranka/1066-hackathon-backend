from django.contrib import admin
from .models import Bill, Participant, Item

class ParticipantInline(admin.TabularInline):
    model = Participant
    extra = 1

class ItemInline(admin.TabularInline):
    model = Item
    extra = 1

@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'location', 'total_amount')
    list_filter = ('date', 'location')
    search_fields = ('name', 'location', 'notes')
    inlines = [ParticipantInline, ItemInline]
    date_hierarchy = 'date'

@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ('name', 'bill', 'amount_paid', 'amount_owed')
    list_filter = ('bill',)
    search_fields = ('name',)

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'bill', 'quantity', 'price', 'tax_rate', 'split_type')
    list_filter = ('bill', 'split_type')
    search_fields = ('name',)
