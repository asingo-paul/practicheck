# accounts/middleware.py
from django.http import HttpResponseForbidden
from django.urls import reverse
from django.shortcuts import redirect

class RoleAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Skip middleware for auth pages and admin
        if request.path.startswith('/accounts/') or request.path.startswith('/admin/'):
            return None
            
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return None
            
        # Define allowed URLs for each user type
        student_urls = ['attachments:dashboard', 'attachments:logbook', 
                       'attachments:report_upload', 'attachments:assessment', 
                       'attachments:communication', 'accounts:profile']
                       
        supervisor_urls = ['evaluations:supervisor_dashboard', 'evaluations:evaluation_form',
                          'attachments:dashboard', 'accounts:profile']
                          
        lecturer_urls = ['evaluations:lecturer_dashboard', 'evaluations:grading_panel',
                        'attachments:dashboard', 'accounts:profile']
        
        # Get the current view name
        current_view = request.resolver_match.url_name if request.resolver_match else None
        
        # Check access based on user type
        if request.user.user_type == 1 and current_view not in student_urls:
            return HttpResponseForbidden("You don't have permission to access this page.")
            
        elif request.user.user_type == 2 and current_view not in supervisor_urls:
            return HttpResponseForbidden("You don't have permission to access this page.")
            
        elif request.user.user_type == 3 and current_view not in lecturer_urls:
            return HttpResponseForbidden("You don't have permission to access this page.")
            
        return None