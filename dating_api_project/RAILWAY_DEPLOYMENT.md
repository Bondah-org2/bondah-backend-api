# 🚀 Railway Deployment Guide for Bondah Dating

## Prerequisites

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **GitHub Repository**: Your code should be on GitHub
3. **Gmail App Password**: For email functionality

## Step 1: Connect to Railway

1. **Login to Railway** and create a new project
2. **Connect your GitHub repository**
3. **Select the repository** containing your Bondah Dating project

## Step 2: Add PostgreSQL Database

1. **Add a new service** → **Database** → **PostgreSQL**
2. **Railway will automatically provide** `DATABASE_URL` environment variable
3. **Copy the database URL** for later use

## Step 3: Configure Environment Variables

In your Railway project settings, add these environment variables:

### **Required Variables:**
```
SECRET_KEY=your-production-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-railway-domain.railway.app
DATABASE_URL=postgresql://username:password@host:port/database
```

### **Email Configuration:**
```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com
```

### **CORS Settings:**
```
CORS_ALLOWED_ORIGINS=https://your-frontend-domain.com,https://bondah-dating.vercel.app
```

## Step 4: Deploy

1. **Railway will automatically detect** your Django project
2. **Build will start automatically** when you push to main branch
3. **Monitor the build logs** for any issues

## Step 5: Run Migrations

After deployment, run database migrations:

1. **Go to your Railway project**
2. **Open the terminal** in your service
3. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

## Step 6: Create Superuser (Optional)

```bash
python manage.py createsuperuser
```

## Step 7: Test Your API

Your API will be available at:
```
https://your-railway-domain.railway.app/api/
```

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | `django-insecure-...` |
| `DEBUG` | Debug mode | `False` |
| `ALLOWED_HOSTS` | Allowed domains | `your-domain.railway.app` |
| `DATABASE_URL` | PostgreSQL connection | `postgresql://...` |
| `EMAIL_HOST_USER` | Gmail address | `your-email@gmail.com` |
| `EMAIL_HOST_PASSWORD` | Gmail app password | `abcd efgh ijkl mnop` |
| `CORS_ALLOWED_ORIGINS` | Frontend domains | `https://your-frontend.com` |

## Troubleshooting

### **Build Fails:**
- Check the build logs in Railway
- Ensure all dependencies are in `requirements.txt`
- Verify Python version in `runtime.txt`

### **Database Connection Issues:**
- Verify `DATABASE_URL` is set correctly
- Check if PostgreSQL service is running
- Run migrations manually if needed

### **Email Not Working:**
- Verify Gmail app password is correct
- Check if 2FA is enabled on Gmail
- Test email configuration locally first

### **CORS Issues:**
- Update `CORS_ALLOWED_ORIGINS` with your frontend domain
- Ensure frontend is making requests to the correct API URL

## Production Checklist

- [ ] Environment variables configured
- [ ] Database migrations run
- [ ] Email system tested
- [ ] CORS settings updated
- [ ] Static files collected
- [ ] API endpoints tested
- [ ] Security settings enabled

## Monitoring

- **Railway Dashboard**: Monitor logs and performance
- **Health Check**: Set up health check endpoint
- **Error Tracking**: Consider adding error tracking service

## Scaling

- **Railway automatically scales** based on traffic
- **Monitor usage** in Railway dashboard
- **Upgrade plan** if needed for higher limits

---

**Your Bondah Dating API is now ready for production! 🎉**
