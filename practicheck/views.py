from django.shortcuts import render

def home(request):
    return render(request, 'home.html')



def dashboard(request):
    return render(request, "dashboard.html")

def admin_dashboard(request):
    return render(request, "admin_dashboard.html")
