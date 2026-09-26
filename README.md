# MedTrack: AWS Cloud-Enabled Healthcare Management System

MedTrack is a cloud-based healthcare management system designed to streamline patient–doctor coordination through real-time appointment scheduling, clinical diagnosis management, medical history record tracking, and automated cloud notification pipelines.

Built with **Python / Flask**, architected for **Amazon Web Services (AWS)**, and supporting seamless dual-mode execution (Local Simulation Mode & Live AWS Cloud Mode).

---

## 🏗 System Architecture & AWS Tech Stack

- **Compute & Hosting**: AWS EC2 (Amazon Linux 2023 AMI), Gunicorn WSGI Server, Nginx Reverse Proxy
- **Database Layer**: Amazon DynamoDB (`MedTrack_Patients`, `MedTrack_Doctors`, `MedTrack_Appointments`, `MedTrack_Diagnoses`)
- **Messaging & Notifications**: AWS SNS (Appointment confirmation topics & Diagnosis alert topics)
- **Object Storage**: Amazon S3 (Lab reports, MRI/ECG scans, medical records)
- **Security & Access Control**: AWS IAM (Least-privilege execution roles & Role-Based Access Control)
- **Networking & DNS**: Amazon VPC, Public Subnets, Security Groups, Amazon Route 53
- **Monitoring & Auditing**: Amazon CloudWatch (Application Metrics & Security Audit Logs)

---

## 🚀 Quick Start (Running Locally Right Now)

MedTrack runs out-of-the-box locally without needing AWS credits or credentials.

### 1. Activate Environment & Install Dependencies
```bash
cd medtrack
pip install -r requirements.txt
```

### 2. Launch the Flask Application
```bash
python app.py
```

Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🧪 Pre-Seeded Evaluation Accounts

MedTrack includes 1-click autofill buttons on the login page, or you can enter credentials manually:

| Role | Email | Password | Access Capabilities |
| :--- | :--- | :--- | :--- |
| **Patient** | `alex.mercer@gmail.com` | `patient123` | Book appointments, view medical history timeline, download lab reports |
| **Doctor** | `sarah.mitchell@medtrack.org` | `doctor123` | View appointment queue, record clinical diagnoses, upload reports |

*(You can also register new patients directly via the **Register** page!)*

---

## ⚡ How to Connect to Live AWS (When You Receive Credits)

MedTrack was built with a clean abstraction layer (`services/`). You do **not** need to rewrite any code to go live on AWS!

### Step 1: Configure `.env`
Open `.env` and set:
```ini
USE_AWS=True
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
# If using AWS Academy / Learner Labs, provide your session token:
AWS_SESSION_TOKEN=your_session_token_here
```

### Step 2: Provision DynamoDB Tables
Run the automated table creator script:
```bash
python deploy/dynamodb_setup.py
```
This automatically creates the 4 DynamoDB tables in your specified AWS region with on-demand (free-tier friendly) capacity.

### Step 3: Deploy to EC2
On an EC2 Amazon Linux instance:
```bash
git clone <your-repo-link> medtrack
cd medtrack
bash deploy/setup_ec2.sh
```
Your MedTrack app will be running via Gunicorn and Nginx with systemd persistence!

---

## 📁 Repository Directory Structure

```
medtrack/
├── app.py                      # Flask Application entry point and route controller
├── config.py                   # Environment configuration (Local vs AWS flags)
├── .env                        # Active environment variables
├── .env.example                # AWS configuration template
├── requirements.txt            # Python dependencies (Flask, boto3, gunicorn)
├── services/                   # Cloud Services Abstraction Layer
│   ├── aws_client.py           # Boto3 session & credential factory
│   ├── db_service.py           # Unified DynamoDB / Local JSON persistence
│   ├── sns_service.py          # AWS SNS & simulated notification pipeline
│   ├── storage_service.py      # AWS S3 & local upload manager
│   └── cloudwatch_logger.py    # CloudWatch metrics & security audit trail
├── static/
│   ├── css/
│   │   ├── style.css           # Modern clinical design system & glassmorphism
│   │   └── dashboard.css       # Dashboards, timelines, and slot selector
│   └── js/
│       ├── main.js             # Notifications bell, alerts, and modals
│       └── dashboard.js        # Dynamic slot logic, filters, and file upload UX
├── templates/
│   ├── base.html               # Master layout with responsive navbar & status badges
│   ├── index.html              # Landing page showcasing scenarios & specialist directory
│   ├── login.html              # Tabbed role-based login with 1-click autofill
│   ├── register.html           # Comprehensive patient onboarding form
│   ├── patient_dashboard.html  # Patient portal (Appointments & Medical History)
│   ├── doctor_dashboard.html   # Doctor clinical workspace (Queue & Diagnosis modal)
│   └── architecture.html       # Interactive AWS architecture review page
└── deploy/                     # AWS Production & EC2 Automation
    ├── dynamodb_setup.py       # One-click DynamoDB table creation script
    ├── iam_policies.json       # IAM least-privilege policy document
    ├── nginx.conf              # Nginx reverse proxy configuration
    ├── gunicorn.conf.py        # Production Gunicorn WSGI configuration
    ├── medtrack.service        # Systemd daemon service definition
    └── setup_ec2.sh            # Automated EC2 deployment shell script
```
