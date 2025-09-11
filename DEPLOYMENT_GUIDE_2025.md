# Voice of Client Agent - Complete Deployment Guide (2025)

## Overview
This deployment guide includes all recent enhancements and optimizations for the Rivvalue Inc. Voice of Client (VoC) Agent platform, featuring Vocsa - the conversational AI assistant.

## Latest Features (July 2025)
- **Vocsa Conversational AI**: Advanced conversational surveys with natural language processing
- **Complete Rating System**: NPS, satisfaction, professional services, product value, pricing, and support ratings
- **Business Relationship Analysis**: Tenure tracking and growth factor analysis using SaaS B2B lookup tables
- **Enhanced Security**: JWT-based authentication with duplicate prevention and admin access control
- **Performance Optimization**: Supports 500+ concurrent users with PostgreSQL and async processing
- **Risk Assessment**: Advanced churn risk categorization with business-aware sentiment analysis
- **Admin Authentication**: Secure export functionality with email-based admin verification

## System Requirements

### Minimum Requirements
- **OS**: Debian 12 x86_64 / Ubuntu 22.04 LTS
- **RAM**: 4GB minimum, 8GB recommended
- **CPU**: 2 cores minimum, 4 cores recommended
- **Storage**: 20GB minimum, 50GB recommended
- **Python**: 3.11+

### Production Environment (500+ Users)
- **RAM**: 16GB+
- **CPU**: 8 cores+
- **Storage**: 100GB+ SSD
- **Database**: PostgreSQL 15+
- **Load Balancer**: Nginx recommended

## Required Environment Variables

```bash
# Core Application
DATABASE_URL=postgresql://username:password@localhost:5432/voc_agent
SESSION_SECRET=your-secure-session-secret-key

# AI Services
OPENAI_API_KEY=your-openai-api-key

# Admin Access Configuration
ADMIN_EMAILS=admin@rivvalue.com,admin2@rivvalue.com

# PostgreSQL (Auto-configured in production)
PGHOST=localhost
PGPORT=5432
PGUSER=voc_user
PGPASSWORD=secure_password
PGDATABASE=voc_agent
```

## Installation Steps

### 1. System Dependencies
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11 and pip
sudo apt install python3.11 python3.11-pip python3.11-venv -y

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Install system utilities
sudo apt install git curl nginx supervisor -y
```

### 2. Database Setup
```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE voc_agent;
CREATE USER voc_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE voc_agent TO voc_user;
\q

# Configure PostgreSQL
sudo nano /etc/postgresql/15/main/postgresql.conf
# Set: listen_addresses = 'localhost'
# Set: max_connections = 100

sudo nano /etc/postgresql/15/main/pg_hba.conf
# Add: local   voc_agent   voc_user   md5

sudo systemctl restart postgresql
```

### 3. Application Deployment
```bash
# Create application user
sudo useradd -m -s /bin/bash voc_agent
sudo su - voc_agent

# Clone repository
git clone https://github.com/your-org/voc-agent.git
cd voc-agent

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create production environment file
cat > .env << EOF
DATABASE_URL=postgresql://voc_user:secure_password@localhost:5432/voc_agent
SESSION_SECRET=$(openssl rand -hex 32)
OPENAI_API_KEY=your-openai-api-key
PGHOST=localhost
PGPORT=5432
PGUSER=voc_user
PGPASSWORD=secure_password
PGDATABASE=voc_agent
EOF

# Initialize database
python -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database initialized successfully')
"
```

### 4. Production Configuration

#### Gunicorn Configuration
```bash
# Create gunicorn config
cat > gunicorn.conf.py << EOF
bind = "0.0.0.0:5000"
workers = 4
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 2
preload_app = True
reload = False
EOF
```

#### Supervisor Configuration
```bash
sudo nano /etc/supervisor/conf.d/voc_agent.conf

[program:voc_agent]
command=/home/voc_agent/voc-agent/venv/bin/gunicorn --config gunicorn.conf.py main:app
directory=/home/voc_agent/voc-agent
user=voc_agent
autostart=true
autorestart=true
startsecs=10
startretries=3
stdout_logfile=/var/log/supervisor/voc_agent.log
stderr_logfile=/var/log/supervisor/voc_agent_error.log
environment=DATABASE_URL="postgresql://voc_user:secure_password@localhost:5432/voc_agent",SESSION_SECRET="your-session-secret",OPENAI_API_KEY="your-openai-key"

sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start voc_agent
```

#### Nginx Configuration
```bash
sudo nano /etc/nginx/sites-available/voc_agent

server {
    listen 80;
    server_name your-domain.com;
    
    client_max_body_size 20M;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    location /static/ {
        alias /home/voc_agent/voc-agent/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}

sudo ln -s /etc/nginx/sites-available/voc_agent /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 5. SSL/HTTPS Setup (Production)
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Obtain SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## Feature Configuration

### 1. Vocsa Conversational AI
The conversational AI system includes:
- Natural language processing with OpenAI GPT-4o
- 10-step conversation flow covering all rating dimensions
- Tenure tracking for business relationship analysis
- Intelligent fallback for reliable data collection

### 2. Growth Factor Analysis
Includes SaaS B2B lookup table for NPS-based growth calculations:
- File: `growth_factor_lookup.csv`
- Automatically calculates organic growth potential
- Provides growth rate ranges based on NPS scores

### 3. Security Features
- JWT-based email authentication
- Rate limiting (10 submissions/min per IP)
- Duplicate response prevention
- Audit trails for all authentication activities
- Admin access control with email verification
- Secure export functionality with double authentication

### 4. Performance Optimization
- PostgreSQL with connection pooling
- Async background task queue (3 workers)
- Database indexing on key fields
- API pagination for large datasets

## Admin Access Configuration

### Setting Up Admin Users
The platform includes secure admin authentication for export functionality:

1. **Configure Admin Emails**: Set the `ADMIN_EMAILS` environment variable
   ```bash
   ADMIN_EMAILS=admin@rivvalue.com,admin2@rivvalue.com
   ```

2. **Admin Authentication Flow**:
   - Admin users click "Admin Login" on the dashboard
   - Enter their authorized email address
   - System generates and verifies admin token
   - Only verified admin emails can access export functionality

3. **Security Features**:
   - Double verification of admin status
   - Automatic token cleanup for non-admin users
   - Real-time admin status validation
   - Audit logging of all admin actions

### Default Admin Configuration
- **Default Admin**: admin@rivvalue.com
- **Token Expiry**: 24 hours
- **Access Level**: Export data, system monitoring

## Monitoring and Maintenance

### Health Checks
```bash
# Application health
curl http://localhost:5000/health

# Queue status
curl http://localhost:5000/api/queue_status

# Database connection
sudo -u postgres psql -d voc_agent -c "SELECT COUNT(*) FROM survey_response;"
```

### Log Monitoring
```bash
# Application logs
tail -f /var/log/supervisor/voc_agent.log

# Error logs
tail -f /var/log/supervisor/voc_agent_error.log

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### Database Maintenance
```bash
# Backup
pg_dump -U voc_user -h localhost voc_agent > backup_$(date +%Y%m%d).sql

# Vacuum and analyze
sudo -u postgres psql -d voc_agent -c "VACUUM ANALYZE;"

# Check database size
sudo -u postgres psql -d voc_agent -c "SELECT pg_size_pretty(pg_database_size('voc_agent'));"
```

## Scaling Considerations

### Horizontal Scaling
- Deploy multiple application instances behind load balancer
- Use Redis for session storage instead of database
- Implement database read replicas for analytics queries

### Performance Tuning
- Increase Gunicorn workers: `workers = (CPU_CORES * 2) + 1`
- Optimize PostgreSQL: increase `shared_buffers`, `work_mem`
- Implement caching layer (Redis/Memcached)

## Troubleshooting

### Common Issues

1. **OpenAI API Quota Exceeded**
   - Check API usage in OpenAI dashboard
   - Implement request queuing with delays
   - Add fallback to rule-based processing

2. **Database Connection Issues**
   - Check PostgreSQL service: `sudo systemctl status postgresql`
   - Verify connection string in environment variables
   - Check database user permissions

3. **High Memory Usage**
   - Monitor with: `htop` or `ps aux --sort=-%mem`
   - Reduce Gunicorn workers if needed
   - Check for memory leaks in application logs

4. **Slow Response Times**
   - Check database query performance
   - Monitor OpenAI API response times
   - Verify adequate server resources

### Support Contacts
- Technical Issues: [Your Support Email]
- OpenAI API Issues: https://platform.openai.com/docs/guides/error-codes
- PostgreSQL Documentation: https://www.postgresql.org/docs/

## Security Checklist

- [ ] Environment variables secured (.env not in git)
- [ ] PostgreSQL password changed from default
- [ ] SSL certificate installed and auto-renewing
- [ ] Firewall configured (UFW recommended)
- [ ] Regular security updates scheduled
- [ ] Application logs monitored for errors
- [ ] Database backups automated
- [ ] Rate limiting configured and tested
- [ ] CORS headers properly configured
- [ ] Session security validated
- [ ] Admin emails configured in ADMIN_EMAILS environment variable
- [ ] Admin authentication tested and verified
- [ ] Export functionality restricted to admin users only

## Version History

- **v1.0** (July 2025): Initial release with Vocsa conversational AI
- **v1.1** (July 2025): Added product value ratings and tenure analysis
- **v1.2** (July 2025): Enhanced growth factor analysis with SaaS B2B lookup

---

*This deployment guide covers the complete Rivvalue Inc. VoC Agent platform with all 2025 enhancements. For technical support, refer to the troubleshooting section or contact your system administrator.*