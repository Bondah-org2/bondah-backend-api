from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date

User = get_user_model()

# ── Test password (same for all accounts) ────────────────────────────────────
TEST_PASSWORD = "Bondah@2025"

# ── Love Seeker accounts ──────────────────────────────────────────────────────
SEEKERS = [
    {
        "email": "amara.osei@bondah.test",
        "name": "Amara Osei",
        "username": "amara_osei",
        "gender": "female",
        "date_of_birth": date(1995, 4, 12),
        "city": "Accra",
        "state": "Greater Accra",
        "country": "Ghana",
        "bio": "Travel enthusiast and foodie. Looking for someone who loves adventures as much as I do.",
        "religion": "Christian",
        "genotype": "AA",
        "ethnicity": "black",
        "education_level": "bachelor",
        "have_kids": "no",
        "want_kids": "yes",
        "relationship_type": "serious",
        "hobbies": ["hiking", "cooking", "photography"],
        "interests": ["travel", "music", "art"],
        "profile_picture": "https://randomuser.me/api/portraits/women/44.jpg",
    },
    {
        "email": "kofi.mensah@bondah.test",
        "name": "Kofi Mensah",
        "username": "kofi_mensah",
        "gender": "male",
        "date_of_birth": date(1991, 8, 23),
        "city": "Lagos",
        "state": "Lagos",
        "country": "Nigeria",
        "bio": "Software engineer by day, chef by night. I believe good food brings people together.",
        "religion": "Christian",
        "genotype": "AS",
        "ethnicity": "black",
        "education_level": "master",
        "have_kids": "no",
        "want_kids": "yes",
        "relationship_type": "serious",
        "hobbies": ["coding", "cooking", "football"],
        "interests": ["technology", "food", "sports"],
        "profile_picture": "https://randomuser.me/api/portraits/men/32.jpg",
    },
    {
        "email": "fatima.bello@bondah.test",
        "name": "Fatima Bello",
        "username": "fatima_bello",
        "gender": "female",
        "date_of_birth": date(1997, 1, 30),
        "city": "Abuja",
        "state": "FCT",
        "country": "Nigeria",
        "bio": "Doctor with a passion for community health. Love reading and quiet evenings.",
        "religion": "Muslim",
        "genotype": "AA",
        "ethnicity": "black",
        "education_level": "doctorate",
        "have_kids": "no",
        "want_kids": "maybe",
        "relationship_type": "serious",
        "hobbies": ["reading", "yoga", "volunteering"],
        "interests": ["health", "education", "travel"],
        "profile_picture": "https://randomuser.me/api/portraits/women/68.jpg",
    },
    {
        "email": "david.asante@bondah.test",
        "name": "David Asante",
        "username": "david_asante",
        "gender": "male",
        "date_of_birth": date(1988, 11, 5),
        "city": "Kumasi",
        "state": "Ashanti",
        "country": "Ghana",
        "bio": "Entrepreneur and gym lover. Building businesses and looking to build a family.",
        "religion": "Christian",
        "genotype": "AA",
        "ethnicity": "black",
        "education_level": "bachelor",
        "have_kids": "yes",
        "want_kids": "yes",
        "relationship_type": "serious",
        "hobbies": ["gym", "business", "reading"],
        "interests": ["entrepreneurship", "finance", "family"],
        "profile_picture": "https://randomuser.me/api/portraits/men/55.jpg",
    },
    {
        "email": "zara.ibrahim@bondah.test",
        "name": "Zara Ibrahim",
        "username": "zara_ibrahim",
        "gender": "female",
        "date_of_birth": date(1993, 6, 18),
        "city": "Nairobi",
        "state": "Nairobi County",
        "country": "Kenya",
        "bio": "Fashion designer with a love for storytelling and long walks on the beach.",
        "religion": "Muslim",
        "genotype": "AA",
        "ethnicity": "black",
        "education_level": "bachelor",
        "have_kids": "no",
        "want_kids": "yes",
        "relationship_type": "serious",
        "hobbies": ["fashion", "writing", "dancing"],
        "interests": ["art", "culture", "travel"],
        "profile_picture": "https://randomuser.me/api/portraits/women/91.jpg",
    },
]

# ── Bondmaker accounts ────────────────────────────────────────────────────────
BONDMAKERS = [
    {
        "email": "grace.okonkwo@bondah.test",
        "name": "Grace Okonkwo",
        "username": "grace_bondmaker",
        "gender": "female",
        "date_of_birth": date(1980, 3, 14),
        "city": "Lagos",
        "state": "Lagos",
        "country": "Nigeria",
        "bio": "Certified relationship coach with 10+ years helping couples find lasting love.",
        "bondmaker_bio": "I specialise in connecting high-achieving professionals who are serious about commitment.",
        "thought_leadership": (
            "Love is not found by chance — it is built with intention. "
            "My approach combines cultural intelligence with emotional compatibility science."
        ),
        "religion": "Christian",
        "ethnicity": "black",
        "education_level": "master",
        "profile_picture": "https://randomuser.me/api/portraits/women/12.jpg",
        "is_matchmaker": True,
    },
    {
        "email": "samuel.darko@bondah.test",
        "name": "Samuel Darko",
        "username": "samuel_bondmaker",
        "gender": "male",
        "date_of_birth": date(1975, 9, 22),
        "city": "Accra",
        "state": "Greater Accra",
        "country": "Ghana",
        "bio": "Former marriage counsellor turned professional matchmaker. I believe every person deserves love.",
        "bondmaker_bio": "Specialising in diaspora Africans looking to connect with their roots through meaningful relationships.",
        "thought_leadership": (
            "The best matches are rooted in shared values, not just shared interests. "
            "I help clients discover what they truly need, not just what they think they want."
        ),
        "religion": "Christian",
        "ethnicity": "black",
        "education_level": "master",
        "profile_picture": "https://randomuser.me/api/portraits/men/78.jpg",
        "is_matchmaker": True,
    },
    {
        "email": "aisha.musa@bondah.test",
        "name": "Aisha Musa",
        "username": "aisha_bondmaker",
        "gender": "female",
        "date_of_birth": date(1983, 7, 8),
        "city": "Abuja",
        "state": "FCT",
        "country": "Nigeria",
        "bio": "Social psychologist and matchmaker. I use science and empathy to create powerful connections.",
        "bondmaker_bio": "Focused on professional Muslim women and men seeking halal relationships grounded in respect.",
        "thought_leadership": (
            "Compatibility is more than a checklist. "
            "Real connection happens when two people align in purpose, faith, and vision for the future."
        ),
        "religion": "Muslim",
        "ethnicity": "black",
        "education_level": "doctorate",
        "profile_picture": "https://randomuser.me/api/portraits/women/33.jpg",
        "is_matchmaker": True,
    },
]


class Command(BaseCommand):
    help = "Seed test accounts for Love Seekers and Bondmakers"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding test accounts..."))

        created_count = 0
        skipped_count = 0

        for data in SEEKERS + BONDMAKERS:
            user, created = User.objects.get_or_create(
                email=data["email"],
                defaults={
                    "username": data["username"],
                    "name": data["name"],
                    "gender": data.get("gender"),
                    "date_of_birth": data.get("date_of_birth"),
                    "city": data.get("city"),
                    "state": data.get("state"),
                    "country": data.get("country"),
                    "bio": data.get("bio", ""),
                    "bondmaker_bio": data.get("bondmaker_bio", ""),
                    "thought_leadership": data.get("thought_leadership", ""),
                    "religion": data.get("religion"),
                    "genotype": data.get("genotype"),
                    "ethnicity": data.get("ethnicity"),
                    "education_level": data.get("education_level"),
                    "have_kids": data.get("have_kids"),
                    "want_kids": data.get("want_kids"),
                    "relationship_type": data.get("relationship_type"),
                    "hobbies": data.get("hobbies", []),
                    "interests": data.get("interests", []),
                    "profile_picture": data.get("profile_picture"),
                    "is_matchmaker": data.get("is_matchmaker", False),
                    "is_active": True,
                },
            )

            if created:
                user.set_password(TEST_PASSWORD)
                user.save(update_fields=["password"])
                role = "Bondmaker" if user.is_matchmaker else "Love Seeker"
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ Created {role}: {user.email}")
                )
                created_count += 1
            else:
                self.stdout.write(
                    self.style.WARNING(f"  ~ Skipped (exists): {user.email}")
                )
                skipped_count += 1

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {created_count} created, {skipped_count} skipped."
            )
        )
        self.stdout.write(
            self.style.MIGRATE_HEADING(f"Password for all accounts: {TEST_PASSWORD}")
        )
