from django.shortcuts import render
from bills.models import Bill, Participant, Item
from django.db.models import Sum
import plotly.graph_objs as go
from plotly.utils import PlotlyJSONEncoder
import json
from django.db.models.functions import TruncMonth

def dashboard(request):
    # Spending over time
    monthly_spending = Bill.objects.annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        total=Sum('total_amount')
    ).order_by('month')

    time_series = go.Scatter(
        x=[entry['month'] for entry in monthly_spending],
        y=[float(entry['total']) for entry in monthly_spending],
        mode='lines+markers'
    )
    
    time_series_layout = go.Layout(
        title='Monthly Spending',
        xaxis={'title': 'Month'},
        yaxis={'title': 'Total Amount ($)'}
    )
    
    # Top spending locations
    location_spending = Bill.objects.values('location').annotate(
        total=Sum('total_amount')
    ).order_by('-total')[:5]

    pie_chart = go.Pie(
        labels=[loc['location'] for loc in location_spending],
        values=[float(loc['total']) for loc in location_spending]
    )
    
    pie_layout = go.Layout(title='Top Spending Locations')

    # Convert the plots to JSON
    time_series_plot = json.dumps({'data': [time_series], 'layout': time_series_layout}, cls=PlotlyJSONEncoder)
    pie_plot = json.dumps({'data': [pie_chart], 'layout': pie_layout}, cls=PlotlyJSONEncoder)

    context = {
        'time_series_plot': time_series_plot,
        'pie_plot': pie_plot
    }
    
    return render(request, 'dashboards/dashboard.html', context)
