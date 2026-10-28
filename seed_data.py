import os
import django
import sys

# Set up Django
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "QR_Attendance_System.settings")
django.setup()

from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from FacultyView.models import Branch, Section, Year, Student

def seed_data():
    admin_password = os.environ.get("DJANGO_ADMIN_PASSWORD")
    if not User.objects.filter(username='admin').exists():
        if not admin_password:
            raise RuntimeError("Set DJANGO_ADMIN_PASSWORD before creating the admin user.")
        User.objects.create_superuser('admin', 'admin@example.com', admin_password)
        
    print("Creating baseline data...")
    branch_cse, _ = Branch.objects.get_or_create(branch='CSE')
    branch_it, _ = Branch.objects.get_or_create(branch='IT')
    
    sec_a, _ = Section.objects.get_or_create(section='A')
    sec_b, _ = Section.objects.get_or_create(section='B')
    
    year_2, _ = Year.objects.get_or_create(year=2)
    year_3, _ = Year.objects.get_or_create(year=3)
    
    print("Seeding 10 demo students...")
    students_data = [
        ("210101", "Aarav", "Sharma", branch_cse, sec_a, year_2),
        ("210102", "Vivaan", "Verma", branch_cse, sec_a, year_2),
        ("210103", "Aditya", "Iyer", branch_cse, sec_a, year_2),
        ("210104", "Vihaan", "Singh", branch_cse, sec_b, year_2),
        ("210105", "Arjun", "Reddy", branch_cse, sec_b, year_2),
        ("210106", "Sai", "Krishna", branch_it, sec_a, year_3),
        ("210107", "Reyansh", "Gupta", branch_it, sec_a, year_3),
        ("210108", "Ayaan", "Khan", branch_it, sec_a, year_3),
        ("210109", "Krishna", "Patel", branch_it, sec_b, year_3),
        ("210110", "Ishaan", "Joshi", branch_it, sec_b, year_3),
    ]
    
    for roll, fname, lname, branch, sec, year in students_data:
        student, created = Student.objects.get_or_create(
            s_roll=roll,
            defaults={
                's_fname': fname,
                's_lname': lname,
                's_branch': branch,
                's_section': sec,
                's_year': year,
                'passcode': make_password(roll) # Default passcode is roll number
            }
        )
        if not created:
            student.passcode = make_password(roll)
            student.save()

    print("Data seeded successfully!")

if __name__ == '__main__':
    seed_data()
