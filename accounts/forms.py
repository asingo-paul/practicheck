from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, StudentProfile, SupervisorProfile, LecturerProfile

# from django import forms
# from django.contrib.auth.forms import UserCreationForm
# from .models import User, StudentProfile, SupervisorProfile, LecturerProfile

# class UserRegistrationForm(UserCreationForm):
#     email = forms.EmailField(required=True)
#     user_type = forms.ChoiceField(choices=User.USER_TYPE_CHOICES)
    
#     class Meta:
#         model = User
#         fields = ['username', 'email', 'first_name', 'last_name', 'user_type', 'password1', 'password2']
    
#     def save(self, commit=True):
#         user = super().save(commit=False)
#         user.user_type = self.cleaned_data['user_type']
#         if commit:
#             user.save()
#         return user

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

class UserLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    user_type = forms.ChoiceField(choices=User.USER_TYPE_CHOICES, widget=forms.RadioSelect)
    
    # Student profile fields
    student_id = forms.CharField(max_length=20, required=False, label="Student ID")
    course = forms.CharField(max_length=100, required=False, label="Course")
    year_of_study = forms.IntegerField(required=False, min_value=1, max_value=6, label="Year of Study")
    university = forms.CharField(max_length=200, required=False, label="University")
    department = forms.CharField(max_length=100, required=False, label="Department")
    
    # Supervisor profile fields
    organization = forms.CharField(max_length=200, required=False, label="Organization")
    position = forms.CharField(max_length=100, required=False, label="Position")
    supervisor_department = forms.CharField(max_length=100, required=False, label="Department")
    
    # Lecturer profile fields
    staff_id = forms.CharField(max_length=20, required=False, label="Staff ID")
    lecturer_department = forms.CharField(max_length=100, required=False, label="Department")
    faculty = forms.CharField(max_length=100, required=False, label="Faculty")
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'user_type', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set up field requirements based on user type
        self.fields['student_id'].required = False
        self.fields['course'].required = False
        self.fields['year_of_study'].required = False
        self.fields['university'].required = False
        self.fields['department'].required = False
        
    def clean(self):
        cleaned_data = super().clean()
        user_type = cleaned_data.get('user_type')
        
        # Validate required fields based on user type
        if user_type == '1':  # Student
            if not cleaned_data.get('student_id'):
                self.add_error('student_id', 'Student ID is required for students.')
            if not cleaned_data.get('course'):
                self.add_error('course', 'Course is required for students.')
            if not cleaned_data.get('year_of_study'):
                self.add_error('year_of_study', 'Year of study is required for students.')
            if not cleaned_data.get('university'):
                self.add_error('university', 'University is required for students.')
            if not cleaned_data.get('department'):
                self.add_error('department', 'Department is required for students.')
                
        elif user_type == '2':  # Supervisor
            if not cleaned_data.get('organization'):
                self.add_error('organization', 'Organization is required for supervisors.')
            if not cleaned_data.get('position'):
                self.add_error('position', 'Position is required for supervisors.')
                
        elif user_type == '3':  # Lecturer
            if not cleaned_data.get('staff_id'):
                self.add_error('staff_id', 'Staff ID is required for lecturers.')
            if not cleaned_data.get('lecturer_department'):
                self.add_error('lecturer_department', 'Department is required for lecturers.')
            if not cleaned_data.get('faculty'):
                self.add_error('faculty', 'Faculty is required for lecturers.')
        
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = int(self.cleaned_data['user_type'])  # ✅ cast to int
    
        if commit:
            user.save()
            user_type = int(self.cleaned_data['user_type'])
            
            if user_type == 1:  # Student
                StudentProfile.objects.create(
                    user=user,
                    student_id=self.cleaned_data['student_id'],
                    course=self.cleaned_data['course'],
                    year_of_study=self.cleaned_data['year_of_study'],
                    university=self.cleaned_data['university'],
                    department=self.cleaned_data['department']
                )
            elif user_type == 2:  # Supervisor
                SupervisorProfile.objects.create(
                    user=user,
                    organization=self.cleaned_data['organization'],
                    position=self.cleaned_data['position'],
                    department=self.cleaned_data.get('supervisor_department', '')
                )
            elif user_type == 3:  # Lecturer
                LecturerProfile.objects.create(
                    user=user,
                    staff_id=self.cleaned_data['staff_id'],
                    department=self.cleaned_data['lecturer_department'],
                    faculty=self.cleaned_data['faculty']
                )
        return user

    
    # def save(self, commit=True):
    #     user = super().save(commit=False)
    #     user.user_type = self.cleaned_data['user_type']
        
    #     if commit:
    #         user.save()
            
    #         # Create profile based on user type
    #         user_type = self.cleaned_data['user_type']
            
    #         if user_type == '1':  # Student
    #             StudentProfile.objects.create(
    #                 user=user,
    #                 student_id=self.cleaned_data['student_id'],
    #                 course=self.cleaned_data['course'],
    #                 year_of_study=self.cleaned_data['year_of_study'],
    #                 university=self.cleaned_data['university'],
    #                 department=self.cleaned_data['department']
    #             )
    #         elif user_type == '2':  # Supervisor
    #             SupervisorProfile.objects.create(
    #                 user=user,
    #                 organization=self.cleaned_data['organization'],
    #                 position=self.cleaned_data['position'],
    #                 department=self.cleaned_data.get('supervisor_department', '')
    #             )
    #         elif user_type == '3':  # Lecturer
    #             LecturerProfile.objects.create(
    #                 user=user,
    #                 staff_id=self.cleaned_data['staff_id'],
    #                 department=self.cleaned_data['lecturer_department'],
    #                 faculty=self.cleaned_data['faculty']
    #             )
        
    #     return user