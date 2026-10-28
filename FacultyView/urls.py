from django.urls import path
from . import views

urlpatterns = [
    # Global Home
    path('', views.home_view, name='home'),
    
    # QR Entry
    path('qr-entry/<str:qr_token>/', views.qr_entry, name='qr_entry'),
    
    # Auth
    path('faculty/login/', views.faculty_login, name='faculty_login'),
    path('faculty/login/force/', views.faculty_login_force, name='faculty_login_force'),
    path('faculty/logout/', views.faculty_logout, name='faculty_logout'),
    
    # Dashboard & Sessions
    path('faculty/dashboard/', views.dashboard, name='faculty_dashboard'),
    path('faculty/session/create/', views.create_session, name='create_session'),
    path('faculty/session/<int:session_id>/', views.session_detail, name='session_detail'),
    path('faculty/session/<int:session_id>/close/', views.close_session, name='close_session'),
    path('faculty/session/<int:session_id>/export/', views.export_excel, name='export_excel'),
    
    # Student Management
    path('faculty/students/', views.manage_students, name='manage_students'),
    path('faculty/students/add/', views.add_student, name='add_student'),
    
    # Security
    path('faculty/violation/<int:violation_id>/resolve/', views.resolve_violation, name='resolve_violation'),
    
    # Live API for Dashboard polling
    path('faculty/api/session/<int:session_id>/live/', views.live_feed_api, name='live_feed_api'),
]
