from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from .models import Student

def faculty_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            messages.error(request, "Access denied. Faculty credentials required.")
            return redirect('faculty_login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def student_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        student_roll = request.session.get('student_roll')
        if not student_roll:
            messages.error(request, "Please log in to your student portal first.")
            return redirect('student_login')
        
        try:
            student = Student.objects.get(s_roll=student_roll)
            request.student = student  # Attach student object to request
            return view_func(request, *args, **kwargs)
        except Student.DoesNotExist:
            del request.session['student_roll']
            messages.error(request, "Session invalid. Please log in again.")
            return redirect('student_login')
            
    return _wrapped_view
