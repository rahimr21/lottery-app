# 🚀 Deployment Guide

## GitHub Upload Checklist

### Before Uploading to GitHub

- [ ] **Review sensitive data**: Ensure no sensitive information is in the code
- [ ] **Update README**: Replace `yourusername` with your actual GitHub username
- [ ] **Test locally**: Make sure everything works with `flask init-db` and `python app.py`
- [ ] **Check .gitignore**: Verify database files and environment files are ignored

### GitHub Repository Setup

1. **Create a new repository on GitHub**
   - Go to [GitHub](https://github.com) and click "New Repository"
   - Repository name: `lottery-app` (or your preferred name)
   - Description: "Flask web application for lottery stock tracking and daily reports"
   - Make it **Public** or **Private** based on your needs
   - Don't initialize with README (you already have one)

2. **Upload your code**
   ```bash
   # Initialize git in your project directory
   git init
   
   # Add all files
   git add .
   
   # Commit your changes
   git commit -m "Initial commit: Lottery Stock Tracker webapp"
   
   # Add remote repository (replace with your actual URL)
   git remote add origin https://github.com/yourusername/lottery-app.git
   
   # Push to GitHub
   git push -u origin main
   ```

## Production Deployment

### Environment Setup

1. **Set environment variables**
   ```bash
   export SECRET_KEY="your-very-secure-secret-key-here"
   export FLASK_ENV="production"
   ```

2. **Use a production server**
   ```bash
   # Install Gunicorn
   pip install gunicorn
   
   # Run with Gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

### Security Considerations

- [ ] **Change SECRET_KEY**: Use a strong, random secret key
- [ ] **Database security**: Consider using PostgreSQL or MySQL for production
- [ ] **HTTPS**: Enable SSL/TLS encryption
- [ ] **Firewall**: Configure proper firewall rules
- [ ] **Backup**: Set up regular database backups

### Hosting Options

#### Free Options
- **Heroku**: Easy deployment with git integration
- **Railway**: Modern hosting with automatic deployments
- **Render**: Simple deployment from GitHub

#### Self-Hosted Options
- **VPS (DigitalOcean, Linode, AWS EC2)**
- **Docker containers**

### Heroku Deployment Example

1. **Create Procfile**
   ```
   web: gunicorn app:app
   ```

2. **Update requirements.txt**
   ```bash
   pip freeze > requirements.txt
   ```

3. **Deploy to Heroku**
   ```bash
   heroku create your-app-name
   heroku config:set SECRET_KEY="your-secret-key"
   git push heroku main
   heroku run flask init-db
   ```

## Maintenance

### Regular Tasks
- [ ] **Backup database** regularly
- [ ] **Update dependencies** periodically
- [ ] **Monitor logs** for errors
- [ ] **Test functionality** after updates

### Monitoring
- Set up logging for production errors
- Monitor application performance
- Track user activity if needed

---

**Note**: This is a basic deployment guide. For production use, consult with a system administrator or DevOps engineer for proper security and scalability setup. 