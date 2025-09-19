from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from .models import StudentProfile, SupervisorProfile, LecturerProfile
from django.contrib.auth import get_user_model

User = get_user_model()

class UserLoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Student/Staff ID",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your ID'})
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter your password'})
    )

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    user_type = forms.ChoiceField(choices=User.USER_TYPE_CHOICES, widget=forms.RadioSelect)

    student_id = forms.CharField(max_length=50, required=False)
    course = forms.CharField(max_length=100, required=False)
    year_of_study = forms.IntegerField(required=False, min_value=1, max_value=6)
    university = forms.CharField(max_length=200, required=False)
    department = forms.CharField(max_length=100, required=False)

    organization = forms.CharField(max_length=200, required=False)
    position = forms.CharField(max_length=100, required=False)
    supervisor_department = forms.CharField(max_length=100, required=False)

    staff_id = forms.CharField(max_length=50, required=False)
    lecturer_department = forms.CharField(max_length=100, required=False)
    faculty = forms.CharField(max_length=100, required=False)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'user_type', 'password1', 'password2']
    def clean(self):
        cleaned_data = super().clean()
        user_type = cleaned_data.get('user_type')
    
        user_type_str = str(user_type) if user_type else None

    # FIXED: Check the Profile models, not User model
        if user_type_str == '1':
            student_id = cleaned_data.get('student_id')
            if student_id and StudentProfile.objects.filter(student_id=student_id).exists():
                self.add_error('student_id', 'This Student ID is already registered.')
    
    # FIXED: Check the Profile models, not User model
        elif user_type_str == '3':
            staff_id = cleaned_data.get('staff_id')
            if staff_id and LecturerProfile.objects.filter(staff_id=staff_id).exists():
                self.add_error('staff_id', 'This Staff ID is already registered.')
        
    # Check email uniqueness for all users
        email = cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            self.add_error('email', 'This email is already registered.')
    
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = int(self.cleaned_data['user_type'])
        user.email = self.cleaned_data['email']  # Make sure email is set

        # if user.user_type == 1:
        #     user.student_id = self.cleaned_data['student_id']
        # elif user.user_type == 3:
        #     user.staff_id = self.cleaned_data['staff_id']

        if commit:
            user.save()
        # Only create profile if it doesn't exist
            if user.user_type == 1 and not hasattr(user, 'student_profile'):
                StudentProfile.objects.create(
                    user=user,
                    student_id=self.cleaned_data['student_id'],
                    course=self.cleaned_data['course'],
                    year_of_study=self.cleaned_data['year_of_study'],
                    university=self.cleaned_data['university'],
                    department=self.cleaned_data['department']
                )
            elif user.user_type == 2 and not hasattr(user, 'supervisor_profile'):
                SupervisorProfile.objects.create(
                    user=user,
                    organization=self.cleaned_data['organization'],
                    position=self.cleaned_data['position'],
                    department=self.cleaned_data.get('supervisor_department', '')
                )
            elif user.user_type == 3 and not hasattr(user, 'lecturer_profile'):
                LecturerProfile.objects.create(
                    user=user,
                    staff_id=self.cleaned_data['staff_id'],
                    department=self.cleaned_data['lecturer_department'],
                    faculty=self.cleaned_data['faculty']
                )
        return user
           

class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ['student_id', 'course', 'year_of_study', 'university', 'department']

class SupervisorProfileForm(forms.ModelForm):
    class Meta:
        model = SupervisorProfile
        fields = ['organization', 'position', 'department']

class LecturerProfileForm(forms.ModelForm):
    class Meta:
        model = LecturerProfile
        fields = ['staff_id', 'department', 'faculty']