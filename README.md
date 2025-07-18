# Bondah Dating MVP Backend

This is the backend for the Bondah Dating MVP project. It provides RESTful API endpoints for user registration, newsletter signup, puzzle-based coin verification, and coin transactions for matchmaking services.

## Tech Stack
- Python
- Django & Django REST Framework
- PostgreSQL

## Features
- **User Registration:** Create normal users and matchmakers (no authentication required for MVP).
- **Newsletter Signup:** Collect emails for future updates.
- **Puzzle Verification:** Users must solve a simple puzzle before earning/spending coins.
- **Coin System:** Users earn/spend coins to pay matchmakers for personalized matchmaking.
- **Admin Panel:** Manage users, newsletters, puzzles, and transactions via Django admin.

## Setup
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure your PostgreSQL database in `backend/settings.py`
4. Run migrations: `python manage.py migrate`
5. Create a superuser: `python manage.py createsuperuser`
6. Start the server: `python manage.py runserver`

## API Endpoints
- `POST /api/create-user/` — Register a new user
- `POST /api/newsletter/signup/` — Newsletter signup
- `GET /api/puzzle/` — Get a puzzle for verification
- `POST /api/puzzle/verify/` — Submit puzzle answer
- `POST /api/coins/earn/` — Earn coins (after puzzle)
- `POST /api/coins/spend/` — Spend coins (after puzzle)

## Notes
- No authentication is required for MVP demo purposes.
- Make sure you have write access to the database.

---

For questions, contact the Bondah team. 