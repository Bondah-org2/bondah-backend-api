# Railway Shell Commands Guide

If the automatic deployment doesn't work, you can run these commands directly on Railway.

## How to Access Railway Shell

1. Go to Railway Dashboard
2. Click on your Django service
3. Go to "Deployments" tab
4. Click on the latest deployment
5. Go to "Logs" tab
6. Click "Open Shell"

## Commands to Run

### 1. Check Current Status
```bash
python debug_railway.py
```

### 2. Create Tables Directly (if migrations fail)
```bash
python create_tables.py
```

### 3. Force Setup (if direct creation fails)
```bash
python force_setup.py
```

### 4. Manual Setup (alternative)
```bash
python manual_setup.py
```

### 5. Check Database Tables
```bash
python check_database.py
```

## Expected Results

After running `python create_tables.py`, you should see:
- ✅ Database connection successful
- ✅ All tables created
- ✅ Superuser created
- ✅ Django admin should work

## Login Credentials

- **URL:** https://bondah-backend-api-production.up.railway.app/admin/
- **Email:** giddehis@gmail.com
- **Password:** Cleverestboo_33

## Troubleshooting

If you get errors:
1. Run `python debug_railway.py` to see what's wrong
2. Run `python create_tables.py` to create tables directly
3. Check Railway logs for any error messages
4. Make sure all environment variables are set correctly
