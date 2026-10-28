from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Q
from django.contrib.auth.hashers import make_password
from django.conf import settings as django_settings
import openpyxl
import os

from .models import Student, DailySession, PeriodAttendance, ProxyViolation, Branch, Section, Year
from .decorators import faculty_required
from .utils import generate_qr_code
from .forms import AddStudentForm

# --- GLOBAL PAGES ---
def home_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('faculty_dashboard')
    if request.session.get('student_roll'):
        return redirect('student_dashboard')
    return render(request, 'home.html')

def qr_entry(request, qr_token):
    # This is the page students land on when they scan the QR code.
    # It passes the qr_token forward so they can mark attendance.
    return render(request, 'qr_entry.html', {'qr_token': qr_token})

# --- HELPERS ---
def _rotate_session_token(session):
    """
    Assign a brand-new QR token to a session, delete the old PNG,
    and save. Call this on login and on session reopen.
    """
    old_token = session.qr_token
    new_token = DailySession._generate_token()

    old_path = os.path.join(django_settings.BASE_DIR, 'static', 'qr',
                            f'session_{old_token}.png')
    try:
        os.remove(old_path)
    except OSError:
        pass

    session.qr_token = new_token
    session.save(update_fields=['qr_token'])
    return new_token


# --- FACULTY AUTH ---
def faculty_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        logout(request)
        messages.info(request, "Previous faculty session cleared. Please log in again.")
        
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_staff:
                login(request, user)
                # Rotate the QR token for any active session on login so
                # students cannot reuse a previously-scanned QR code.
                today = timezone.localdate()
                active = DailySession.objects.filter(date=today, is_active=True).first()
                if active:
                    _rotate_session_token(active)
                messages.success(request, f"Welcome back, {user.username}!")
                return redirect('faculty_dashboard')
            else:
                messages.error(request, "Access denied. Not a faculty account.")
        else:
            messages.error(request, "Invalid username or password.")
            
    return render(request, 'faculty/login.html')

def faculty_logout(request):
    request.session.flush()
    messages.info(request, "You have been logged out.")
    return redirect('home')

def faculty_login_force(request):
    logout(request)
    request.session.flush()
    messages.info(request, "Faculty session cleared. Please log in.")
    return redirect('faculty_login')

# --- FACULTY DASHBOARD ---
@faculty_required
def dashboard(request):
    today = timezone.localdate()

    active_session = DailySession.objects.filter(date=today, is_active=True).first()
    recent_sessions = DailySession.objects.exclude(
        id=active_session.id if active_session else 0
    ).order_by('-date')[:5]

    total_students = Student.objects.filter(is_active=True).count()

    qr_img_url = None
    if active_session:
        # Just generate the image for the current token — no regeneration here.
        # Token rotation is handled by create_session (reopen) and faculty_login (new login).
        generate_qr_code(active_session.qr_token)
        qr_img_url = f"/static/qr/session_{active_session.qr_token}.png"

    context = {
        'active_session': active_session,
        'recent_sessions': recent_sessions,
        'total_students': total_students,
        'qr_url': qr_img_url,
        'today': today,
    }
    return render(request, 'faculty/dashboard.html', context)

@faculty_required
def create_session(request):
    today = timezone.localdate()

    # Check if there's already an active session for today
    existing_active = DailySession.objects.filter(date=today, is_active=True).first()
    if existing_active:
        messages.info(request, "Session for today is already active.")
        return redirect('faculty_dashboard')

    # Close any lingering open sessions for today (safety)
    DailySession.objects.filter(date=today, is_active=True).update(
        is_active=False, closed_at=timezone.now()
    )

    # Always create a FRESH session row — new ID, new token, zero attendance
    DailySession.objects.create(date=today, created_by=request.user)
    messages.success(request, "New attendance session started with a fresh QR code.")
    return redirect('faculty_dashboard')

@faculty_required
def close_session(request, session_id):
    session = get_object_or_404(DailySession, id=session_id)
    session.is_active = False
    session.closed_at = timezone.now()
    session.save()
    messages.success(request, f"Session for {session.date} closed successfully.")
    return redirect('faculty_dashboard')

@faculty_required
def session_detail(request, session_id):
    session = get_object_or_404(DailySession, id=session_id)
    generate_qr_code(session.qr_token)
    qr_img_url = f"/static/qr/session_{session.qr_token}.png"
    
    return render(request, 'faculty/session_detail.html', {
        'session': session,
        'qr_url': qr_img_url
    })

# --- STUDENT MANAGEMENT ---
@faculty_required
def manage_students(request):
    students = Student.objects.all().select_related('s_branch', 's_section', 's_year')
    form = AddStudentForm()
    return render(request, 'faculty/manage_students.html', {
        'students': students,
        'form': form
    })

@faculty_required
def add_student(request):
    if request.method == 'POST':
        form = AddStudentForm(request.POST)
        if form.is_valid():
            student = form.save(commit=False)
            # Set default passcode as roll number
            student.passcode = make_password(student.s_roll)
            student.save()
            messages.success(request, f"Student {student.s_fname} added successfully.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    return redirect('manage_students')

# --- SECURITY ALERTS ---
@faculty_required
def resolve_violation(request, violation_id):
    violation = get_object_or_404(ProxyViolation, id=violation_id)
    violation.resolved = True
    violation.resolved_by = request.user
    violation.save()
    return JsonResponse({'status': 'success'})

# --- LIVE API ---
@faculty_required
def live_feed_api(request, session_id):
    session = get_object_or_404(DailySession, id=session_id)
    
    # Get today's attendance summary (Group by student, collect periods)
    attendances = PeriodAttendance.objects.filter(session=session).select_related('student')
    
    # Format data for frontend grid
    # For a classroom, we want to know which students are present for which periods today
    students_data = {}
    for att in attendances:
        roll = att.student.s_roll
        if roll not in students_data:
            students_data[roll] = {
                'name': f"{att.student.s_fname} {att.student.s_lname}",
                'roll': roll,
                'periods': []
            }
        students_data[roll]['periods'].append({
            'period': att.period,
            'status': att.status,
            'time': timezone.localtime(att.marked_at).strftime('%H:%M')
        })
        
    # Unresolved violations
    violations = ProxyViolation.objects.filter(session=session, resolved=False).select_related('attempted_student', 'original_student')
    violations_data = [{
        'id': v.id,
        'attempted': v.attempted_student.s_roll,
        'original': v.original_student.s_roll,
        'period': v.period,
        'time': timezone.localtime(v.attempted_at).strftime('%H:%M:%S'),
        'ip': v.client_ip
    } for v in violations]
    
    return JsonResponse({
        'attendees': list(students_data.values()),
        'violations': violations_data,
        'total_unique': len(students_data),
        'is_active': session.is_active
    })

# --- EXPORT REPORTS ---
@faculty_required
def export_excel(request, session_id):
    session = get_object_or_404(DailySession, id=session_id)
    students = Student.objects.filter(is_active=True).order_by('s_roll')
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Attendance {session.date}"
    
    # Headers
    headers = ['Roll Number', 'Name', 'Branch', 'Section'] + [f'Period {i}' for i in range(1, 9)]
    ws.append(headers)
    
    # Pre-fetch attendances
    atts = PeriodAttendance.objects.filter(session=session)
    att_map = {(a.student_id, a.period): a.status for a in atts}
    
    for student in students:
        row = [
            student.s_roll,
            f"{student.s_fname} {student.s_lname}",
            student.s_branch.branch,
            f"{student.s_year.year}{student.s_section.section}"
        ]
        
        for p in range(1, 9):
            status = att_map.get((student.s_roll, p), 'ABSENT')
            row.append(status)
            
        ws.append(row)
        
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename=Attendance_{session.date}.xlsx'
    wb.save(response)
    return response
