from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('student/login/', views.student_login, name='student_login'),
    path('student/logout/', views.student_logout, name='student_logout'),
    
    # Dashboard & History
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    
    # Mark Attendance Flow
    path('student/mark/<str:qr_token>/', views.mark_attendance, name='mark_attendance'),
    
    # Success / Blocked Pages
    path('student/success/', views.attendance_success, name='attendance_success'),
    path('student/blocked/', views.attendance_blocked, name='attendance_blocked'),
]
