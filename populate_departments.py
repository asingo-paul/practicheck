#!/usr/bin/env python
# populate_departments.py - UPDATED VERSION
import os
import django
import sys

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'practicheck.settings')  
django.setup()

from attachments.models import Department

def populate_departments():
    # Updated departments with unique codes - NOW INCLUDES UNIVERSITY
    departments_data = [
        (1, "Computer Science", "CS", "Machakos University"),
        (2, "Information Technology", "IT", "Machakos University"),
        (3, "Software Engineering", "SE", "Machakos University"),
        (4, "Business Administration", "BA", "Machakos University"),
        (5, "Electrical Engineering", "EE", "Machakos University"),
        (6, "Civil Engineering", "CE", "Machakos University"),
        (7, "Mechanical Engineering", "ME", "Machakos University"),
        (8, "Education Arts", "EDUART", "Machakos University"),
        (9, "Education Science", "EDUSCI", "Machakos University"),
        (10, "Nursing", "NURS", "Machakos University"),
        (11, "Public Health", "PUBHLTH", "Machakos University"),
        (12, "Commerce", "COMM", "Machakos University"),
        (13, "Economics", "ECON", "Machakos University"),
        (14, "Law", "LAW", "Machakos University"),
        (15, "Medicine", "MED", "Machakos University"),
        (16, "Agriculture", "AGRI", "Machakos University"),
        (17, "Architecture", "ARCH", "Machakos University"),
        (18, "Pharmacy", "PHARM", "Machakos University"),
        (19, "Dentistry", "DENT", "Machakos University"),
        (20, "Veterinary Medicine", "VETMED", "Machakos University")
    ]

    print("Processing departments...")
    print("🚀 Starting department population...")
    print("-" * 50)

    created_count = 0
    updated_count = 0
    error_count = 0

    for dept_id, name, code, university in departments_data:
        try:
            # First, check if a department with this code already exists (but different ID)
            existing_with_code = Department.objects.filter(code=code).exclude(id=dept_id).first()
            if existing_with_code:
                print(f'❌ Code conflict: {code} is already used by {existing_with_code.name} (ID: {existing_with_code.id})')
                # Generate a unique code
                new_code = f"{code}_{dept_id}"
                print(f'   Using alternative code: {new_code}')
                code = new_code

            department, created = Department.objects.update_or_create(
                id=dept_id,
                defaults={
                    'name': name,
                    'code': code,
                    'university': university  # ADD THIS LINE
                }
            )
            
            if created:
                created_count += 1
                print(f'✅ Created: {name} (ID: {dept_id}, Code: {code}, University: {university})')
            else:
                updated_count += 1
                print(f'↻ Updated: {name} (ID: {dept_id}, Code: {code}, University: {university})')
                
        except Exception as e:
            error_count += 1
            print(f'❌ Error creating {name}: {str(e)}')
            # Try without specifying ID
            try:
                department, created = Department.objects.get_or_create(
                    name=name,
                    defaults={
                        'code': code,
                        'university': university  # ADD THIS LINE
                    }
                )
                if created:
                    created_count += 1
                    print(f'✅ Created (without ID): {name} (Code: {code}, University: {university})')
                else:
                    updated_count += 1
                    print(f'↻ Updated (without ID): {name} (Code: {code}, University: {university})')
            except Exception as e2:
                error_count += 1
                print(f'❌ Failed to create {name}: {str(e2)}')

    print("-" * 50)
    print(f"🎉 Department population completed!")
    print(f"📊 Created: {created_count}")
    print(f"📊 Updated: {updated_count}")
    print(f"📊 Errors: {error_count}")
    print(f"📊 Total departments in database: {Department.objects.count()}")

if __name__ == "__main__":
    populate_departments()