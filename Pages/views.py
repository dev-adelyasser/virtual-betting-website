from django.shortcuts import render
from .models import Match

def home_page(request):

    matches = Match.objects.all()
    

    return render(request, 'home.html', {'matches': matches})