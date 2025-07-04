# AWS EC2 Deployment Guide - Voice of Client Agent
## Complete Step-by-Step Instructions for Debian 12

---

## PART 1: DOWNLOAD YOUR APPLICATION

### Step 1: Download Files from Replit
1. Open your Replit project
2. Click the three dots menu (⋮) in the file explorer
3. Select "Download as ZIP" 
4. Save the file to your computer
5. Extract the ZIP file to a folder called `voice-of-client-agent`

### Step 2: Verify You Have These Files
Make sure your extracted folder contains:
```
voice-of-client-agent/
├── main.py
├── app.py
├── routes.py
├── models.py
├── models_auth.py
├── auth_system.py
├── ai_analysis.py
├── task_queue.py
├── rate_limiter.py
├── data_storage.py
├── pyproject.toml
├── templates/ (folder with HTML files)
├── static/ (folder with CSS/JS files)
└── README.md
```

---

## PART 2: SET UP AWS INFRASTRUCTURE

### Step 3: Create PostgreSQL Database (RDS)
1. **Go to AWS Console** → RDS → Create Database
2. **Choose settings**:
   - Engine: PostgreSQL
   - Version: 15.4 (or latest)
   - Template: Free tier (for testing) or Production (for live use)
   - Instance: db.t3.micro (free tier) or db.t3.small (production)
   - Storage: 20 GB minimum
3. **Database settings**:
   - Database name: `voiceofclient`
   - Username: `dbadmin`
   - Password: Choose a strong password (save this!)
4. **Network settings**:
   - VPC: Default VPC
   - Publicly accessible: Yes (for now)
   - Security group: Create new (allow PostgreSQL port 5432)
5. **Click "Create Database"**
6. **Wait 10-15 minutes** for database to be ready
7. **Copy the endpoint URL** (looks like: `database-1.xxxxx.us-east-1.rds.amazonaws.com`)

### Step 4: Create EC2 Instance
1. **Go to AWS Console** → EC2 → Launch Instance
2. **Choose AMI**: Debian 12 (x86_64)
3. **Instance type**: t3.medium (recommended for 500+ users)
4. **Key pair**: Create new key pair
   - Name: `voice-of-client-key`
   - Download the `.pem` file (keep it safe!)
5. **Security groups**: Create new security group
   - Name: `voice-of-client-sg`
   - Rules:
     - SSH (port 22): Your IP address
     - HTTP (port 80): 0.0.0.0/0
     - HTTPS (port 443): 0.0.0.0/0
     - Custom TCP (port 5000): 0.0.0.0/0
6. **Storage**: 20 GB (default is fine)
7. **Click "Launch Instance"**
8. **Wait 2-3 minutes** for instance to start
9. **Copy the Public IP address** (e.g., 54.123.45.67)

---

## PART 3: CONNECT TO YOUR SERVER

### Step 5: Connect to EC2 Instance
**On Windows (use PuTTY or Windows Terminal):**
```bash
# If using Windows Terminal with OpenSSH
ssh -i voice-of-client-key.pem admin@YOUR_EC2_PUBLIC_IP

# Replace YOUR_EC2_PUBLIC_IP with your actual IP (e.g., 54.123.45.67)
```

**On Mac/Linux:**
```bash
chmod 400 voice-of-client-key.pem
ssh -i voice-of-client-key.pem admin@YOUR_EC2_PUBLIC_IP
```

You should see a Debian welcome message when connected.

---

## PART 4: INSTALL SOFTWARE ON SERVER

### Step 6: Update System and Install Python
```bash
# Update package lists
sudo apt update && sudo apt upgrade -y

# Install Python 3.11 and required packages
sudo apt install -y python3.11 python3.11-venv python3-pip git nginx postgresql-client curl unzip

# Verify Python installation
python3.11 --version
```

### Step 7: Install Application Dependencies
```bash
# Create application directory
sudo mkdir -p /opt/voice-of-client-agent
sudo chown admin:admin /opt/voice-of-client-agent
cd /opt/voice-of-client-agent

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install required packages
pip install flask==3.0.3 flask-sqlalchemy==3.1.1 gunicorn==23.0.0 psycopg2-binary==2.9.9 openai==1.35.13 pyjwt==2.8.0 email-validator==2.1.1 textblob==0.18.0.post0 werkzeug==3.0.3 sqlalchemy==2.0.31
```

---

## PART 5: UPLOAD YOUR APPLICATION

### Step 8: Transfer Files to Server
**Method 1: Using SCP (Secure Copy)**
From your local computer (in the folder with your extracted files):
```bash
# Copy all files to server
scp -i voice-of-client-key.pem -r voice-of-client-agent/* admin@YOUR_EC2_PUBLIC_IP:/opt/voice-of-client-agent/
```

**Method 2: Using GitHub (if you have a GitHub account)**
```bash
# On your local computer, create a private GitHub repository
# Upload your files to GitHub
# Then on the server:
git clone https://github.com/yourusername/voice-of-client-agent.git /opt/voice-of-client-agent
```

### Step 9: Set File Permissions
```bash
# On the server, set proper permissions
sudo chown -R admin:admin /opt/voice-of-client-agent
chmod +x /opt/voice-of-client-agent/main.py
```

---

## PART 6: CONFIGURE YOUR APPLICATION

### Step 10: Create Environment Variables
```bash
# Create environment file
cd /opt/voice-of-client-agent
nano .env
```

**Add these lines to the .env file:**
```bash
# Database connection (replace with your RDS details)
DATABASE_URL=postgresql://dbadmin:YOUR_DATABASE_PASSWORD@YOUR_RDS_ENDPOINT:5432/voiceofclient

# Security (generate a random 32-character string)
SESSION_SECRET=your-super-secure-32-character-secret-key-here

# OpenAI API (use your OpenAI API key)
OPENAI_API_KEY=your-openai-api-key-here

# Production settings
FLASK_ENV=production
```

**Replace:**
- `YOUR_DATABASE_PASSWORD`: Password you set for RDS
- `YOUR_RDS_ENDPOINT`: RDS endpoint URL you copied earlier
- `your-openai-api-key-here`: Your OpenAI API key

**Save and exit:** Press `Ctrl+X`, then `Y`, then `Enter`

### Step 11: Test Database Connection
```bash
# Load environment variables
source .env

# Test database connection
python3.11 -c "
import os
import psycopg2
try:
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    print('Database connection successful!')
    conn.close()
except Exception as e:
    print(f'Database connection failed: {e}')
"
```

---

## PART 7: START YOUR APPLICATION

### Step 12: Test the Application
```bash
# Activate virtual environment
cd /opt/voice-of-client-agent
source venv/bin/activate

# Start the application in test mode
python3.11 main.py
```

You should see:
```
* Running on http://0.0.0.0:5000
* Debug mode: on
```

**Test in your browser:** Go to `http://YOUR_EC2_PUBLIC_IP:5000`

If you see your survey page, it's working! Press `Ctrl+C` to stop the test.

### Step 13: Set Up Production Service
```bash
# Create systemd service file
sudo nano /etc/systemd/system/voice-of-client.service
```

**Add this content:**
```ini
[Unit]
Description=Voice of Client Agent
After=network.target

[Service]
Type=simple
User=admin
WorkingDirectory=/opt/voice-of-client-agent
Environment=PATH=/opt/voice-of-client-agent/venv/bin
EnvironmentFile=/opt/voice-of-client-agent/.env
ExecStart=/opt/voice-of-client-agent/venv/bin/gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 60 main:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

**Save and exit**

### Step 14: Start Production Service
```bash
# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable voice-of-client.service
sudo systemctl start voice-of-client.service

# Check service status
sudo systemctl status voice-of-client.service
```

You should see "Active: active (running)" in green.

---

## PART 8: SET UP NGINX (OPTIONAL BUT RECOMMENDED)

### Step 15: Configure Nginx Reverse Proxy
```bash
# Create nginx configuration
sudo nano /etc/nginx/sites-available/voice-of-client
```

**Add this content:**
```nginx
server {
    listen 80;
    server_name YOUR_EC2_PUBLIC_IP;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /opt/voice-of-client-agent/static/;
        expires 30d;
    }
}
```

**Replace `YOUR_EC2_PUBLIC_IP` with your actual IP**

### Step 16: Enable Nginx Configuration
```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/voice-of-client /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## PART 9: FINAL TESTING

### Step 17: Test Your Application
1. **Open browser**: Go to `http://YOUR_EC2_PUBLIC_IP`
2. **Test authentication**: Go to "Get Token" and enter an email
3. **Test survey**: Complete a survey
4. **Test dashboard**: View the analytics dashboard

### Step 18: Monitor Your Application
```bash
# Check application logs
sudo journalctl -u voice-of-client.service -f

# Check nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Check system resources
htop
```

---

## PART 10: SECURITY (IMPORTANT)

### Step 19: Secure Your Instance
```bash
# Update RDS security group to only allow EC2 access
# In AWS Console → RDS → Your Database → Security Groups
# Edit inbound rules: PostgreSQL port 5432 from your EC2 security group only

# Set up automatic security updates
sudo apt install -y unattended-upgrades
sudo systemctl enable unattended-upgrades
```

### Step 20: Set Up SSL Certificate (Optional)
```bash
# Install Certbot for free SSL
sudo apt install -y certbot python3-certbot-nginx

# Get SSL certificate (replace with your domain)
sudo certbot --nginx -d your-domain.com
```

---

## TROUBLESHOOTING

### Common Issues and Solutions:

**1. Database Connection Failed**
```bash
# Check RDS security group allows port 5432
# Verify DATABASE_URL format
# Test with: psql "postgresql://dbadmin:password@endpoint:5432/voiceofclient"
```

**2. Service Won't Start**
```bash
# Check logs
sudo journalctl -u voice-of-client.service
# Check environment file
cat /opt/voice-of-client-agent/.env
```

**3. Can't Access Website**
```bash
# Check security group allows HTTP (port 80) and port 5000
# Verify service is running: sudo systemctl status voice-of-client.service
```

---

## MAINTENANCE

### Daily Operations:
```bash
# Check service status
sudo systemctl status voice-of-client.service

# View recent logs
sudo journalctl -u voice-of-client.service --since "1 hour ago"

# Restart service if needed
sudo systemctl restart voice-of-client.service
```

### Monthly Updates:
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Python packages
source /opt/voice-of-client-agent/venv/bin/activate
pip install --upgrade flask flask-sqlalchemy gunicorn psycopg2-binary openai

# Restart service
sudo systemctl restart voice-of-client.service
```

---

## COST ESTIMATION

**Monthly AWS costs:**
- EC2 t3.medium: ~$30
- RDS db.t3.micro: ~$15
- Data transfer: ~$10
- **Total: ~$55/month**

---

## SUPPORT

Your application is now running in production! 

**URLs to bookmark:**
- Application: `http://YOUR_EC2_PUBLIC_IP`
- Health check: `http://YOUR_EC2_PUBLIC_IP/health`
- Dashboard: `http://YOUR_EC2_PUBLIC_IP/dashboard`

**Key files on server:**
- Application: `/opt/voice-of-client-agent/`
- Service config: `/etc/systemd/system/voice-of-client.service`
- Nginx config: `/etc/nginx/sites-available/voice-of-client`
- Environment: `/opt/voice-of-client-agent/.env`

Your Voice of Client Agent is now live and ready to handle customer feedback!