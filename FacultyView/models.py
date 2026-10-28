from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import secrets
import string


class Section(models.Model):
    section = models.CharField(max_length=2)

    def __str__(self) -> str:
        return self.section


class Year(models.Model):
    year = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(4)],
    )

    def __str__(self) -> str:
        return str(self.year)


class Branch(models.Model):
    branch = models.CharField(max_length=10)

    def __str__(self) -> str:
        return self.branch


class Student(models.Model):
    """Student profile with roll number as primary key."""
    s_roll = models.CharField(max_length=20, primary_key=True)
    s_fname = models.CharField(max_length=50)
    s_lname = models.CharField(max_length=50)
    s_branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    s_section = models.ForeignKey(Section, on_delete=models.CASCADE)
    s_year = models.ForeignKey(Year, on_delete=models.CASCADE)
    # New fields for authentication
    passcode = models.CharField(max_length=128, default='', blank=True,
                                help_text='Hashed passcode for student login')
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.s_fname} {self.s_lname} ({self.s_roll})"

    class Meta:
        ordering = ['s_roll']


class DailySession(models.Model):
    """
    Represents one attendance session. Multiple sessions can exist per day
    (e.g. reopen after close creates a new session with fresh attendance).
    Each session has a unique QR token.
    """
    date = models.DateField(db_index=True)  # Not unique — multiple sessions per day allowed
    qr_token = models.CharField(max_length=32, unique=True, db_index=True,
                                help_text='Random token embedded in QR URL')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='sessions_created')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        status = "ACTIVE" if self.is_active else "CLOSED"
        return f"Session {self.date} [{status}]"

    def save(self, *args, **kwargs):
        if not self.qr_token:
            self.qr_token = self._generate_token()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_token():
        """Generate a cryptographically secure 16-char token."""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(16))

    @property
    def total_present(self):
        """Count unique students who marked at least one period."""
        return self.period_attendances.values('student').distinct().count()

    class Meta:
        ordering = ['-date']


PERIOD_CHOICES = [(i, f'Period {i}') for i in range(1, 9)]

STATUS_CHOICES = [
    ('PRESENT', 'Present'),
    ('OD', 'On Duty'),
    ('ABSENT', 'Absent'),
]

MARKED_BY_CHOICES = [
    ('STUDENT', 'Student'),
    ('FACULTY', 'Faculty'),
]


class PeriodAttendance(models.Model):
    """
    Individual attendance record for one student, one period, one day.
    8 periods per day × N students = records per session.
    """
    session = models.ForeignKey(DailySession, on_delete=models.CASCADE,
                                related_name='period_attendances')
    student = models.ForeignKey(Student, on_delete=models.CASCADE,
                                related_name='attendances')
    period = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(8)],
        choices=PERIOD_CHOICES
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES,
                              default='PRESENT')
    marked_at = models.DateTimeField(auto_now_add=True)
    client_ip = models.GenericIPAddressField(null=True, blank=True)
    device_fingerprint = models.CharField(max_length=64, blank=True, default='')
    user_agent = models.TextField(blank=True, default='')
    marked_by = models.CharField(max_length=10, choices=MARKED_BY_CHOICES,
                                 default='STUDENT')

    def __str__(self) -> str:
        return (f"{self.student.s_fname} {self.student.s_lname} - "
                f"P{self.period} - {self.status}")

    class Meta:
        unique_together = ('session', 'student', 'period')
        ordering = ['period', 'student']


class ProxyViolation(models.Model):
    """
    Security log: recorded when the same IP/device fingerprint
    tries to mark attendance for a DIFFERENT student in the same
    session+period.
    """
    session = models.ForeignKey(DailySession, on_delete=models.CASCADE,
                                related_name='violations')
    period = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(8)]
    )
    attempted_student = models.ForeignKey(
        Student, on_delete=models.CASCADE,
        related_name='proxy_attempts',
        help_text='The student whose attendance was being attempted'
    )
    original_student = models.ForeignKey(
        Student, on_delete=models.CASCADE,
        related_name='proxy_originals',
        help_text='The student who originally used this IP/device'
    )
    client_ip = models.GenericIPAddressField()
    device_fingerprint = models.CharField(max_length=64, blank=True, default='')
    user_agent = models.TextField(blank=True, default='')
    attempted_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(User, null=True, blank=True,
                                    on_delete=models.SET_NULL)

    def __str__(self) -> str:
        return (f"PROXY: {self.attempted_student.s_roll} via "
                f"{self.original_student.s_roll}'s device "
                f"[P{self.period}]")

    class Meta:
        ordering = ['-attempted_at']
