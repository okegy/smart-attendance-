from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.hashers import check_password
from django.db.models import Q

from FacultyView.models import Student, DailySession, PeriodAttendance, ProxyViolation, PERIOD_CHOICES
from FacultyView.decorators import student_required
from FacultyView.utils import get_client_ip, get_user_agent

# --- STUDENT AUTH ---
def student_login(request):
    if request.session.get('student_roll'):
        request.session.flush()
        messages.info(request, "Previous student session cleared. Please log in again.")
        
    if request.method == 'POST':
        roll = request.POST.get('roll_number')
        passcode = request.POST.get('passcode')
        
        try:
            student = Student.objects.get(s_roll=roll, is_active=True)
            if check_password(passcode, student.passcode):
                request.session['student_roll'] = student.s_roll
                messages.success(request, f"Welcome, {student.s_fname}!")
                
                # Check for redirect parameter
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('student_dashboard')
            else:
                messages.error(request, "Invalid roll number or passcode.")
        except Student.DoesNotExist:
            messages.error(request, "Invalid roll number or passcode.")
            
    return render(request, 'student/login.html')

def student_logout(request):
    request.session.flush()
    messages.info(request, "You have been logged out.")
    return redirect('home')

# --- STUDENT DASHBOARD (Search & History) ---
@student_required
def student_dashboard(request):
    student = request.student
    
    # Get all attendance records for this student, grouped by session (day)
    history = PeriodAttendance.objects.filter(student=student).select_related('session').order_by('-session__date', 'period')
    
    # Organize history into a structured format for the template
    days_data = {}
    for att in history:
        date_str = att.session.date.strftime('%Y-%m-%d')
        if date_str not in days_data:
            days_data[date_str] = {
                'date': att.session.date,
                'periods': []
            }
        days_data[date_str]['periods'].append({
            'period': att.period,
            'status': att.status,
            'time': att.marked_at.strftime('%H:%M')
        })
        
    # Get today's attendance specifically
    today = timezone.localdate()
    today_atts = PeriodAttendance.objects.filter(student=student, session__date=today).values_list('period', flat=True)
        
    context = {
        'student': student,
        'history': list(days_data.values()),
        'today_atts': list(today_atts),
        'total_present': history.filter(status='PRESENT').count(),
        'total_od': history.filter(status='OD').count(),
    }
    return render(request, 'student/dashboard.html', context)

# --- MARK ATTENDANCE (Passwordless) ---
def mark_attendance(request, qr_token):
    # 1. Validate Session
    session = get_object_or_404(DailySession, qr_token=qr_token)
    if not session.is_active:
        messages.error(request, "This attendance session has been closed by faculty.")
        return render(request, 'student/blocked.html', {'message': 'Session Closed'})
        
    if session.date != timezone.localdate():
        messages.error(request, "This QR code is expired (not for today).")
        return render(request, 'student/blocked.html', {'message': 'Expired QR Code'})

    # 2. PROXY DETECTION LOGIC (CRITICAL)
    # Get current device info
    client_ip = get_client_ip(request)
    device_fp = request.POST.get('device_fingerprint', '') if request.method == 'POST' else request.GET.get('fp', '')
    user_agent = get_user_agent(request)

    if request.method == 'POST':
        period = int(request.POST.get('period'))
        student_id = request.POST.get('student_id')
        
        if not student_id:
            messages.error(request, "Please select your name.")
            return redirect('mark_attendance', qr_token=qr_token)
            
        student = get_object_or_404(Student, s_roll=student_id)
        
        # Check if the student is already marked present for this period by ANY device
        if PeriodAttendance.objects.filter(session=session, student=student, period=period).exists():
            messages.warning(request, f"{student.s_fname} {student.s_lname} is already marked present for Period {period}.")
            return redirect('mark_attendance', qr_token=qr_token)

        # STRICT PROXY CHECK: Has THIS DEVICE already marked attendance for ANY student in this period?
        device_usage = PeriodAttendance.objects.filter(
            session=session,
            period=period
        ).filter(
            Q(client_ip=client_ip) | Q(device_fingerprint=device_fp)
        )

        if device_usage.exists():
            original_log = device_usage.first()
            
            # Log the violation
            ProxyViolation.objects.create(
                session=session,
                period=period,
                attempted_student=student,
                original_student=original_log.student,
                client_ip=client_ip,
                device_fingerprint=device_fp,
                user_agent=user_agent
            )
            
            # Redirect to blocked screen
            return redirect('attendance_blocked')

        # 3. SUCCESS - Record Attendance
        PeriodAttendance.objects.create(
            session=session,
            student=student,
            period=period,
            status='PRESENT',
            client_ip=client_ip,
            device_fingerprint=device_fp,
            user_agent=user_agent
        )
        
        return redirect('attendance_success')
        
    # GET Request: Render period selection and student list form
    all_students = Student.objects.filter(is_active=True).order_by('s_roll')
    
    return render(request, 'student/mark.html', {
        'session': session,
        'available_periods': PERIOD_CHOICES,
        'students': all_students
    })

def attendance_success(request):
    return render(request, 'student/success.html')

def attendance_blocked(request):
    return render(request, 'student/blocked.html')
