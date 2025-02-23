from django.shortcuts import render
from bills.models import Bill, Item
from django.db.models import Sum
import plotly.graph_objs as go
from plotly.utils import PlotlyJSONEncoder
import json
from django.db.models.functions import TruncMonth, TruncWeek, TruncYear

def dashboard(request):
    # Monthly Spending
    monthly_spending = Bill.objects.annotate(
        period=TruncMonth('date')
    ).values('period').annotate(
        total=Sum('total_amount')
    ).order_by('period')

    # Weekly Spending
    weekly_spending = Bill.objects.annotate(
        period=TruncWeek('date')
    ).values('period').annotate(
        total=Sum('total_amount')
    ).order_by('period')

    # Yearly Spending
    yearly_spending = Bill.objects.annotate(
        period=TruncYear('date')
    ).values('period').annotate(
        total=Sum('total_amount')
    ).order_by('period')

    # Item Level Visualization
    item_spending = Item.objects.values('name').annotate(
        total=Sum('price')
    ).order_by('-total')[:10]

    # Calculate total spent and top spent item for each filter
    total_spent_monthly = monthly_spending.aggregate(total=Sum('total'))['total']
    total_spent_weekly = weekly_spending.aggregate(total=Sum('total'))['total']
    total_spent_yearly = yearly_spending.aggregate(total=Sum('total'))['total']

    top_spent_item_monthly = item_spending.first()
    top_spent_item_weekly = item_spending.first()
    top_spent_item_yearly = item_spending.first()

    # Convert the plots to JSON
    monthly_series_plot = json.dumps({'data': [go.Scatter(
        x=[entry['period'] for entry in monthly_spending],
        y=[float(entry['total']) for entry in monthly_spending],
        mode='lines+markers'
    )], 'layout': go.Layout(
        title='Monthly Spending',
        xaxis={'title': 'Month'},
        yaxis={'title': 'Total Amount ($)'}
    )}, cls=PlotlyJSONEncoder)

    weekly_series_plot = json.dumps({'data': [go.Scatter(
        x=[entry['period'] for entry in weekly_spending],
        y=[float(entry['total']) for entry in weekly_spending],
        mode='lines+markers'
    )], 'layout': go.Layout(
        title='Weekly Spending',
        xaxis={'title': 'Week'},
        yaxis={'title': 'Total Amount ($)'}
    )}, cls=PlotlyJSONEncoder)

    yearly_series_plot = json.dumps({'data': [go.Scatter(
        x=[entry['period'] for entry in yearly_spending],
        y=[float(entry['total']) for entry in yearly_spending],
        mode='lines+markers'
    )], 'layout': go.Layout(
        title='Yearly Spending',
        xaxis={'title': 'Year'},
        yaxis={'title': 'Total Amount ($)'}
    )}, cls=PlotlyJSONEncoder)

    item_pie_plot = json.dumps({'data': [go.Pie(
        labels=[item['name'] for item in item_spending],
        values=[float(item['total']) for item in item_spending]
    )], 'layout': go.Layout(
        title='Top 10 Items by Spending'
    )}, cls=PlotlyJSONEncoder)

    context = {
        'monthly_series_plot': monthly_series_plot,
        'weekly_series_plot': weekly_series_plot,
        'yearly_series_plot': yearly_series_plot,
        'item_pie_plot': item_pie_plot,
        'total_spent_monthly': total_spent_monthly,
        'total_spent_weekly': total_spent_weekly,
        'total_spent_yearly': total_spent_yearly,
        'top_spent_item_monthly': top_spent_item_monthly,
        'top_spent_item_weekly': top_spent_item_weekly,
        'top_spent_item_yearly': top_spent_item_yearly
    }
    
    return render(request, 'dashboards/dashboard.html', context)
