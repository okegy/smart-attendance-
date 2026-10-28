from django.test import TestCase
from django.urls import reverse

from FacultyView.models import Branch, Section, Student, Year


class StudentCreationTests(TestCase):
    def test_add_student_creates_student_and_related_models(self):
        response = self.client.post(
            reverse("add_student"),
            {
                "s_roll": "1001",
                "s_fname": "Ava",
                "s_lname": "Roy",
                "s_branch": "CSE",
                "s_section": "A",
                "s_year": "2",
            },
        )

        self.assertRedirects(response, reverse("faculty_view"))
        self.assertTrue(Student.objects.filter(s_roll="1001").exists())
        self.assertTrue(Branch.objects.filter(branch="CSE").exists())
        self.assertTrue(Section.objects.filter(section="A").exists())
        self.assertTrue(Year.objects.filter(year=2).exists())
