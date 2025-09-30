# Create new file: attachments/admin_views.py or add to existing views.py
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, Q
from django.utils import timezone

def is_admin(user):
    return user.is_authenticated and (user.is_superuser or user.user_type == 1)

@user_passes_test(is_admin)
def admin_dashboard(request):
    # Statistics
    total_students = User.objects.filter(user_type=4).count()  # Assuming 4 is student type
    total_lecturers = Lecturer.objects.filter(is_active=True).count()
    total_placements = PlacementFormSubmission.objects.count()
    pending_placements = PlacementFormSubmission.objects.filter(status='pending').count()
    
    # Department-wise placements
    department_stats = Department.objects.annotate(
        total_placements=Count('placementformsubmission'),
        pending_placements=Count('placementformsubmission', filter=Q(placementformsubmission__status='pending')),
        assigned_placements=Count('placementformsubmission', 
                                filter=Q(placementformsubmission__student_assignment__isnull=False))
    )
    
    # Recent placements
    recent_placements = PlacementFormSubmission.objects.select_related(
        'student', 'department'
    ).order_by('-submitted_at')[:10]
    
    # Lecturer workload
    lecturer_workload = Lecturer.objects.filter(is_active=True).annotate(
        assigned_count=Count('assigned_students'),
        available_slots=models.F('max_students') - Count('assigned_students')
    ).order_by('department__name', 'user__first_name')
    
    context = {
        'total_students': total_students,
        'total_lecturers': total_lecturers,
        'total_placements': total_placements,
        'pending_placements': pending_placements,
        'department_stats': department_stats,
        'recent_placements': recent_placements,
        'lecturer_workload': lecturer_workload,
        'current_year': timezone.now().year,
    }
    
    return render(request, 'attachments/admin_dashboard.html', context)

@user_passes_test(is_admin)
def department_placements(request, department_id):
    department = get_object_or_404(Department, id=department_id)
    placements = PlacementFormSubmission.objects.filter(
        department=department
    ).select_related('student').prefetch_related('student_assignment')
    
    # Available lecturers in this department
    available_lecturers = Lecturer.objects.filter(
        department=department, 
        is_active=True
    ).annotate(
        assigned_count=Count('assigned_students'),
        available_slots=models.F('max_students') - Count('assigned_students')
    )
    
    context = {
        'department': department,
        'placements': placements,
        'available_lecturers': available_lecturers,
    }
    
    return render(request, 'attachments/department_placements.html', context)

@user_passes_test(is_admin)
def assign_student(request, placement_id, lecturer_id):
    placement = get_object_or_404(PlacementFormSubmission, id=placement_id)
    lecturer = get_object_or_404(Lecturer, id=lecturer_id)
    
    # Check if student already assigned for this academic year
    current_year = timezone.now().year
    existing_assignment = StudentAssignment.objects.filter(
        student=placement.student,
        academic_year=current_year
    ).exists()
    
    if existing_assignment:
        messages.error(request, 'This student is already assigned to a lecturer for this academic year.')
    else:
        # Create assignment
        assignment = StudentAssignment(
            student=placement.student,
            lecturer=lecturer,
            placement_form=placement,
            academic_year=current_year
        )
        assignment.save()
        messages.success(request, f'Student successfully assigned to {lecturer.user.get_full_name()}')
    
    return redirect('attachments:department_placements', department_id=placement.department.id)

@user_passes_test(is_admin)
def manage_lecturers(request):
    if request.method == 'POST':
        # Handle lecturer registration
        form_type = request.POST.get('form_type')
        
        if form_type == 'create_lecturer':
            # Create new lecturer
            username = request.POST.get('username')
            email = request.POST.get('email')
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            staff_id = request.POST.get('staff_id')
            department_id = request.POST.get('department')
            phone_number = request.POST.get('phone_number')
            office_location = request.POST.get('office_location')
            max_students = request.POST.get('max_students', 10)
            
            try:
                # Create user
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password='temp123',  # Temporary password
                    first_name=first_name,
                    last_name=last_name,
                    user_type=2  # Assuming 2 is lecturer type
                )
                
                # Create lecturer profile
                department = Department.objects.get(id=department_id)
                lecturer = Lecturer.objects.create(
                    user=user,
                    staff_id=staff_id,
                    department=department,
                    phone_number=phone_number,
                    office_location=office_location,
                    max_students=max_students
                )
                
                messages.success(request, f'Lecturer {first_name} {last_name} created successfully!')
                
            except Exception as e:
                messages.error(request, f'Error creating lecturer: {str(e)}')
    
    departments = Department.objects.all()
    lecturers = Lecturer.objects.select_related('user', 'department').all()
    
    context = {
        'departments': departments,
        'lecturers': lecturers,
    }
    
    return render(request, 'attachments/manage_lecturers.html', context)