from django import forms
from .models import Student, Branch, Section, Year

class AddStudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['s_roll', 's_fname', 's_lname', 's_branch', 's_section', 's_year']
        widgets = {
            's_roll': forms.TextInput(attrs={'class': 'w-full bg-glass border border-glass rounded-lg px-4 py-3 text-white focus:outline-none input-glow placeholder-slate-500', 'placeholder': 'Roll Number'}),
            's_fname': forms.TextInput(attrs={'class': 'w-full bg-glass border border-glass rounded-lg px-4 py-3 text-white focus:outline-none input-glow placeholder-slate-500', 'placeholder': 'First Name'}),
            's_lname': forms.TextInput(attrs={'class': 'w-full bg-glass border border-glass rounded-lg px-4 py-3 text-white focus:outline-none input-glow placeholder-slate-500', 'placeholder': 'Last Name'}),
            's_branch': forms.Select(attrs={'class': 'w-full bg-[#121326] border border-glass rounded-lg px-4 py-3 text-white focus:outline-none input-glow'}),
            's_section': forms.Select(attrs={'class': 'w-full bg-[#121326] border border-glass rounded-lg px-4 py-3 text-white focus:outline-none input-glow'}),
            's_year': forms.Select(attrs={'class': 'w-full bg-[#121326] border border-glass rounded-lg px-4 py-3 text-white focus:outline-none input-glow'}),
        }
