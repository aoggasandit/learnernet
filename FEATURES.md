# Redemption Gate – Ironclad Guard Features

This app is now a **complete school safety and learning platform** with:

## 🛡️ Ironclad Guard Security Features

### 1. **Role-Based Access Control**
- **Super Admin** — Full system control: add/remove users, change settings, view all data
- **School Management** — View all student scans, geofence events, late pickups, download reports
- **Staff/Security** — Scan QR codes at gate, mark entry/exit/pickup, view today's scans only
- **Parent** — See only their linked child's location, alerts, and geofence events
- **Student** — Consent to tracking, view own status

**How it works:** Users can only view data related to their role. A parent cannot see other children; staff cannot see historical data. Only admins can create accounts.

---

### 2. **Safe Perimeter + Geofence Alerts**
- School defines a safe zone (latitude, longitude, radius in meters)
- When a student leaves the safe perimeter, parents receive an **instant SMS with a clickable Google Maps link** to the student's exact location
- **Automatic:** Geofence checks happen when security staff logs QR scan events

**How to set it up:**
1. Go to **Admin** → **School settings**
2. Set the center latitude, longitude, and radius (meters)
3. Save. Done!

---

### 3. **QR Code Scanning & Event Logging**
- Each student has a unique QR code linked to their account
- Security staff scan at entry/exit/pickup points
- Logs timestamp, location, and coordinates automatically
- Generates Google Maps links for all events
- Parents can track when their child entered/left campus

**How to log a scan:**
1. Go to **Security** (must be logged in as Staff/Security, Management, or Admin)
2. Select student, event type (Entry/Exit/Pickup)
3. Enter location, latitude/longitude, and optional notes
4. Click "Record scan event"
5. If student is outside safe zone, geofence alert fires

---

### 4. **AI Safety Monitor (Ironclad Guard Algorithm)**
- Every post, comment, and message is scanned for explicit language, digital threats, and cyberbullying
- Flagged content triggers a **safety event log** viewable only by admins
- Content is still posted but flagged in the audit log
- Blocked keywords: kill, die, attack, threat, bully, stupid, hate, bomb, rape, harass, abuse, etc.

**How it works:**
- Text is normalized and checked against flagged keywords
- Flagged items recorded in `safety_events` table with severity (high/medium/low)
- Parents/staff can request reports from admins on safety incidents

---

### 5. **Parent-Child Relationships**
- Admins link parents to students
- Parents see ONLY their child's data
- Communication is private and secure
- Parents receive SMS alerts automatically

**How to link:**
1. Go to **Admin** → **Add parent-child relationship**
2. Select parent username and student username
3. Click "Link parent and student"

---

### 6. **Data Privacy Within Community**
- No public sign-up allowed
- Only admins can create accounts
- Parent data is encrypted and isolated
- School manages all access
- Sessions automatically clear on sign-out

---

## 📱 How the System Works

### For **Security Staff:**
1. Sign in with staff account (created by admin)
2. Go to **Security**
3. Scan student QR code or manually select student
4. Log event (Entry/Exit/Pickup) with location
5. If student is outside safe zone → parents get SMS alert instantly

### For **Parents:**
1. Sign in with parent account (created by admin)
2. Go to **Security**
3. View your child's:
   - Recent scan history (entry/exit/pickup times)
   - Last known location
   - Geofence alerts if they left campus
4. Receive SMS alerts in real-time for geofence violations

### For **Students:**
1. Sign in with student account
2. Go to **Security** to see your status
3. Your unique QR code is displayed
4. You consent to tracking via the app

### For **School Management:**
1. Sign in with management account
2. Go to **Admin** or **Security**
3. View all student scans, geofence events, late pickups
4. Download CSV reports
5. See safety events log (flagged content)

### For **Super Admins:**
1. Sign in with admin account
2. Go to **Admin**
3. Create users, set roles
4. Link parents to students
5. Configure safe zone and school settings
6. View all reports, users, safety events
7. Download data to Excel/Google Sheets

---

## 🚀 Setup Instructions

### 1. **Initial Setup**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. **Environment Variables (Optional but Recommended)**
Create a `.env` file:
```
SUPER_ADMIN_USERNAME=admin
SUPER_ADMIN_PASSWORD=Admin1234!
SUPER_ADMIN_EMAIL=admin@redemptiongate.local
SUPER_ADMIN_PHONE=+1234567890

# For SMS alerts via Twilio:
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=+1234567890
EMERGENCY_SMS_RECIPIENTS=+1234567890,+0987654321

# For password reset emails:
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

### 3. **Run the App**
```bash
streamlit run app.py
```

### 4. **First Login**
- Username: `admin` (or value of `SUPER_ADMIN_USERNAME`)
- Password: `Admin1234!` (or value of `SUPER_ADMIN_PASSWORD`)

### 5. **Create Your School Users**
1. Go to **Admin**
2. Add parents, students, staff under their respective roles
3. Configure safe zone
4. Link parents to students
5. Start logging scans!

---

## 📊 Features at a Glance

| Feature | Super Admin | Management | Staff/Security | Parent | Student |
|---------|:-----------:|:----------:|:-------------:|:------:|:-------:|
| Create users | ✓ | ✗ | ✗ | ✗ | ✗ |
| Scan QR code | ✓ | ✓ | ✓ | ✗ | ✗ |
| View all scans | ✓ | ✓ | ✓ (today only) | ✗ | ✗ |
| View child scans | ✓ | ✓ | ✗ | ✓ | ✗ |
| See geofence alerts | ✓ | ✓ | ✗ | ✓ | ✗ |
| Download reports | ✓ | ✓ | ✗ | ✗ | ✗ |
| View safety events | ✓ | ✗ | ✗ | ✗ | ✗ |
| Manage safe zone | ✓ | ✗ | ✗ | ✗ | ✗ |

---

## 🔐 Security Best Practices

1. **Change admin password** immediately on first login
2. **Use strong passwords** (12+ chars, mixed case, numbers, symbols)
3. **Update Twilio credentials** if using SMS alerts (don't leave test tokens)
4. **Rotate emergency phone numbers** quarterly
5. **Back up database** regularly (`social_learning.db`)
6. **Review safety events** weekly in the admin panel
7. **Deactivate inactive accounts** to prevent unauthorized access

---

## 🐛 Troubleshooting

### SMS alerts not sending?
- Check Twilio credentials in `.env`
- Verify parent phone numbers are in E.164 format: `+1234567890`
- Check Twilio account balance

### QR codes not generating?
- QR code image uses Google Charts API (no local dependency)
- If offline, generate QR codes locally: install `qrcode` package

### Database locked?
- Stop the app and restart
- Don't run multiple instances of Streamlit simultaneously

### Password reset not working?
- Set `SMTP_USERNAME` and `SMTP_PASSWORD` in `.env`
- Or set up Google OAuth (see README.md)

---

## 📝 Logging & Auditing

All critical events are logged:
- User logins (in session state)
- QR scans (qr_scans table)
- Geofence violations (geofence_events table)
- Safety flags (safety_events table)
- Admin actions (user creation, settings changes)

**Export reports to Excel/Google Sheets:**
1. Go to **Admin**
2. Scroll to "Download scan report CSV"
3. Import CSV into Excel or Google Sheets

---

## 🎓 Learning Features (Unchanged)

The app still includes:
- Research & Learning Feed (posts, comments, likes)
- Shared Learning Resources
- AI Research Assistant (GPT-3.5-turbo)
- AI Media Studio (image generation/editing)
- Direct Messaging
- User Profiles

All learning features use the same role-based access and content safety checks.

---

## License & Support

Built on Streamlit. For support, contact your system administrator.

**Version:** 2.0 – Ironclad Guard Edition
**Last updated:** June 2026
