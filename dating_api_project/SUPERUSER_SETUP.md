# 👤 Superuser Setup for Bondah Dating

## Automatic Superuser Creation

The production setup command will automatically create a superuser with these default credentials:

### **Default Superuser Credentials:**
- **Email:** `admin@bondah.org`
- **Password:** `Bondah@admin$$25`
- **First Name:** `Bondah`
- **Last Name:** `Admin`

## Railway Environment Variables

Add these variables to Railway for custom superuser credentials:

```
# Superuser Configuration (Optional)
SUPERUSER_EMAIL=admin@bondah.org
SUPERUSER_PASSWORD=Bondah@admin$$25
SUPERUSER_FIRST_NAME=Bondah
SUPERUSER_LAST_NAME=Admin
```

## How It Works

1. **During deployment**, the `setup_production` command runs automatically
2. **Migrations** are applied to the database
3. **Static files** are collected
4. **Superuser** is created if it doesn't exist
5. **Admin panel** becomes accessible at `/admin/`

## Access Admin Panel

After deployment, you can access the admin panel at:
```
https://your-railway-domain.up.railway.app/admin/
```

### **Login Credentials:**
- **Email:** `admin@bondah.org`
- **Password:** `Bondah@admin$$25`

## Manual Setup (if needed)

If you need to run setup manually in Railway terminal:

```bash
python manage.py setup_production
```

Or with custom credentials:

```bash
python manage.py setup_production --username=your-email@bondah.org --password=your-password
```

## Security Notes

- ✅ Superuser is only created if it doesn't exist
- ✅ Password is securely hashed
- ✅ Admin panel is protected by Django's built-in security
- ✅ Can be accessed via HTTPS only in production
