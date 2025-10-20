from django.core.management.base import BaseCommand
from attachments.models import Department, Course

class Command(BaseCommand):
    help = 'Populate courses for Machakos University departments'

    def handle(self, *args, **options):
        # Course data mapped to department names
        courses_data = {
            "Computer Science": [
                ("Bachelor of Science in Computer Science", "BSC-CS"),
                ("Bachelor of Science in Computer Technology", "BSC-CT"),
                ("Bachelor of Science in Data Science", "BSC-DS")
            ],
            "Information Technology": [
                ("Bachelor of Science in Information Technology", "BSC-IT"),
                ("Bachelor of Science in Business Information Technology", "BSC-BIT")
            ],
            "Software Engineering": [
                ("Bachelor of Science in Software Engineering", "BSC-SE"),
                ("Bachelor of Science in Mobile Application Development", "BSC-MAD")
            ],
            "Business Administration": [
                ("Bachelor of Business Administration", "BBA"),
                ("Bachelor of Commerce", "BCOM")
            ],
            "Electrical Engineering": [
                ("Bachelor of Science in Electrical Engineering", "BSC-EE"),
                ("Bachelor of Science in Electronics Engineering", "BSC-ELEC")
            ],
            "Civil Engineering": [
                ("Bachelor of Science in Civil Engineering", "BSC-CE"),
                ("Bachelor of Science in Structural Engineering", "BSC-SE")
            ],
            "Mechanical Engineering": [
                ("Bachelor of Science in Mechanical Engineering", "BSC-ME"),
                ("Bachelor of Science in Automotive Engineering", "BSC-AUTO")
            ],
            "Education Arts": [
                ("Bachelor of Education (Arts)", "BED-ARTS"),
                ("Bachelor of Arts in Education", "BA-ED")
            ],
            "Education Science": [
                ("Bachelor of Education (Science)", "BED-SCI"),
                ("Bachelor of Science in Education", "BSC-ED")
            ],
            "Nursing": [
                ("Bachelor of Science in Nursing", "BSC-NURS"),
                ("Bachelor of Science in Critical Care Nursing", "BSC-CCN")
            ],
            "Public Health": [
                ("Bachelor of Science in Public Health", "BSC-PH"),
                ("Bachelor of Science in Epidemiology", "BSC-EPI")
            ],
            "Commerce": [
                ("Bachelor of Commerce", "BCOM"),
                ("Bachelor of Business Management", "BBM")
            ],
            "Economics": [
                ("Bachelor of Arts in Economics", "BA-ECON"),
                ("Bachelor of Science in Economics", "BSC-ECON")
            ],
            "Law": [
                ("Bachelor of Laws", "LLB")
            ],
            "Medicine": [
                ("Bachelor of Medicine and Bachelor of Surgery", "MBChB")
            ],
            "Agriculture": [
                ("Bachelor of Science in Agriculture", "BSC-AGRI"),
                ("Bachelor of Science in Agribusiness", "BSC-AGRIB")
            ],
            "Architecture": [
                ("Bachelor of Architecture", "BARCH")
            ],
            "Pharmacy": [
                ("Bachelor of Pharmacy", "BPharm")
            ],
            "Dentistry": [
                ("Bachelor of Dental Surgery", "BDS")
            ],
            "Veterinary Medicine": [
                ("Bachelor of Veterinary Medicine", "BVM")
            ]
        }

        self.stdout.write("🚀 Starting course population...")
        self.stdout.write("-" * 50)

        created_count = 0
        error_count = 0

        for dept_name, courses in courses_data.items():
            try:
                # Find department by name
                department = Department.objects.filter(name__icontains=dept_name).first()
                if not department:
                    self.stdout.write(self.style.ERROR(f'❌ Department not found: {dept_name}'))
                    error_count += 1
                    continue

                for course_name, course_code in courses:
                    try:
                        course, created = Course.objects.get_or_create(
                            code=course_code,
                            defaults={
                                'name': course_name,
                                'department': department
                            }
                        )
                        
                        if created:
                            created_count += 1
                            self.stdout.write(self.style.SUCCESS(f'✅ Created: {course_name} (Code: {course_code}) in {dept_name}'))
                        else:
                            self.stdout.write(f'↻ Exists: {course_name} (Code: {course_code})')
                            
                    except Exception as e:
                        error_count += 1
                        self.stdout.write(self.style.ERROR(f'❌ Error creating {course_name}: {str(e)}'))
                        
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f'❌ Error processing department {dept_name}: {str(e)}'))

        self.stdout.write("-" * 50)
        self.stdout.write(self.style.SUCCESS(f"🎉 Course population completed!"))
        self.stdout.write(f"📊 Created: {created_count}")
        self.stdout.write(f"📊 Errors: {error_count}")
        self.stdout.write(f"📊 Total courses in database: {Course.objects.count()}")