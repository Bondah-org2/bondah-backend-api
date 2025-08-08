from django.core.management.base import BaseCommand
from dating.models import Job

class Command(BaseCommand):
    help = 'Create sample job data for testing'

    def handle(self, *args, **options):
        # Sample job data
        jobs_data = [
            {
                'title': 'Software Engineer',
                'job_type': 'full-time',
                'category': 'engineering',
                'status': 'open',
                'description': 'We are looking for a talented Software Engineer to join our team and help build the next generation of dating technology. You will work on developing scalable backend systems, implementing new features, and optimizing performance.',
                'location': 'Remote',
                'salary_range': '$60,000 - $80,000',
                'requirements': [
                    '3+ years experience with Python/Django',
                    'Understanding of REST APIs',
                    'Experience with PostgreSQL',
                    'Strong problem-solving skills',
                    'Knowledge of AWS or similar cloud platforms'
                ]
            },
            {
                'title': 'Frontend Developer',
                'job_type': 'full-time',
                'category': 'engineering',
                'status': 'open',
                'description': 'Join our frontend team to create beautiful, responsive user interfaces for our dating platform. You will work with React, TypeScript, and modern web technologies.',
                'location': 'Remote',
                'salary_range': '$55,000 - $75,000',
                'requirements': [
                    '2+ years experience with React',
                    'Proficiency in TypeScript',
                    'Experience with CSS/SCSS',
                    'Understanding of responsive design',
                    'Knowledge of state management (Redux, Context API)'
                ]
            },
            {
                'title': 'DevOps Engineer',
                'job_type': 'full-time',
                'category': 'engineering',
                'status': 'open',
                'description': 'Help us build and maintain our infrastructure. You will work on CI/CD pipelines, monitoring, and ensuring our platform runs smoothly at scale.',
                'location': 'Remote',
                'salary_range': '$70,000 - $90,000',
                'requirements': [
                    '3+ years experience with AWS',
                    'Experience with Docker and Kubernetes',
                    'Knowledge of CI/CD pipelines',
                    'Understanding of monitoring and logging',
                    'Experience with Terraform or similar IaC tools'
                ]
            },
            {
                'title': 'UI/UX Designer',
                'job_type': 'part-time',
                'category': 'design',
                'status': 'open',
                'description': 'Create beautiful and intuitive user experiences for our dating platform. You will work on wireframes, prototypes, and final designs.',
                'location': 'Remote',
                'salary_range': '$40,000 - $60,000',
                'requirements': [
                    '3+ years experience in UI/UX design',
                    'Proficiency in Figma or similar tools',
                    'Understanding of user-centered design',
                    'Experience with mobile app design',
                    'Portfolio showcasing dating or social apps'
                ]
            },
            {
                'title': 'Marketing Manager',
                'job_type': 'full-time',
                'category': 'marketing',
                'status': 'open',
                'description': 'Lead our marketing efforts to grow our user base. You will develop and execute marketing strategies, manage campaigns, and analyze performance.',
                'location': 'Remote',
                'salary_range': '$50,000 - $70,000',
                'requirements': [
                    '3+ years experience in digital marketing',
                    'Experience with social media marketing',
                    'Knowledge of Google Analytics',
                    'Experience with email marketing campaigns',
                    'Understanding of growth hacking techniques'
                ]
            }
        ]

        # Create jobs
        for job_data in jobs_data:
            job, created = Job.objects.get_or_create(
                title=job_data['title'],
                defaults=job_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created job: {job.title}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Job already exists: {job.title}')
                )

        self.stdout.write(
            self.style.SUCCESS('Sample job data created successfully!')
        ) 