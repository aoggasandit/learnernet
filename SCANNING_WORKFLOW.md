# QR Code Scanning & Notification Workflow

## Overview
The scanning and notification system involves multiple roles: **Staff/Security** performs scans, **School Management** & **Super Admin** view scan logs and geofence events, and **Parents** receive SMS alerts when students leave campus.

---

## Complete Workflow

### Step 1: Set Up Your Account Structure
Before testing, ensure you have these user roles created in Admin:
- **1 Super Admin** (Full access)
- **1 School Management** (View all data, reports)
- **1 Staff/Security** (Scan QR codes)
- **1 Student** (Gets scanned)
- **1 Parent** (Receives alerts)

**Create accounts via Admin → Create User**

### Step 2: Link Parent to Student
The Parent must be linked to the Student for notifications to work.

**Admin → Manage Users → Select Parent → Link to Student**

---

## Testing the Scan & Notification Flow

### For STAFF/SECURITY Role (Performer of Scan)

1. **Sign in** as Staff/Security user
2. Go to **"Security Dashboard"** page
3. You'll see:
   - Student selector dropdown
   - Event type selector (Entry/Exit/Pickup)
   - Location description field
   - Latitude/Longitude inputs
   - Notes field

4. **Fill in the scan details:**
   - **Select student** from dropdown
   - **Choose event type**: Entry, Exit, or Pickup
   - **Enter location**: e.g., "Main Gate", "South Entrance"
   - **Enter coordinates**: Use your school's GPS coordinates (or test coordinates like 6.5244, 3.3792)
   - **Add notes** (optional): e.g., "Morning entry"

5. **Click "Record scan event"** button

6. **What happens:**
   - Scan is recorded in database with timestamp
   - If coordinates are OUTSIDE the safe perimeter → Parent gets SMS alert
   - Geofence event is created if outside safe zone
   - Success message appears: "Scan event recorded and logged"

---

### For SUPER ADMIN Role (Full Oversight)

**Navigate to Admin page:**

1. **View All Scan Events**
   - See complete log of all scans across entire school
   - Shows: Student name, Scanner name, Event type, Location, GPS coordinates, Timestamp

2. **View All Geofence Events**
   - Track every time a student left safe perimeter
   - Shows: Student name, Event type ("Exited safe perimeter"), Coordinates, Time

3. **View Late Pickups**
   - See all Pickup events from today
   - Identify students not picked up on time

4. **Download Reports**
   - Export scan history for compliance/documentation

5. **Manage Settings**
   - Configure Safe Perimeter (center lat/lng and radius in meters)
   - Manage all users and their roles
   - Set emergency contact numbers

---

### For SCHOOL MANAGEMENT Role (Dashboard View)

**Navigate to Admin page (same as Super Admin, with limited permissions):**

1. **View All Scan Events**
   - See all scans (same as Super Admin)

2. **View Geofence Events**
   - Monitor students leaving campus
   - Track unauthorized departures

3. **View Late Pickups**
   - See today's pickup logs
   - Identify at-risk students

4. **Download Reports**
   - Generate compliance documentation

---

### For PARENT Role (Alert Recipient)

**Parents see:**

1. **Their Children Dashboard**
   - List of their linked child/children
   - Child's recent scan history
   - Entry and exit times for today

2. **Receive SMS Alerts When:**
   - Student is scanned at **Exit** outside safe perimeter
   - Alert format: 
     ```
     Alert: [Student Name] Exit outside safe perimeter. 
     Location: [Location]. 
     Map: [Google Maps Link]
     ```

3. **What triggers notification:**
   - Staff/Security performs scan with event type "Exit"
   - Latitude/Longitude is checked against safe perimeter
   - If OUTSIDE perimeter → SMS sent to parent phone

---

## Step-by-Step Testing Guide

### Test Case 1: Entry Scan (No Alert)

1. **Staff/Security:**
   - Select a student
   - Event type: **Entry**
   - Location: "Main Gate"
   - Lat: 6.5244, Lng: 3.3792 (Inside safe zone)
   - Click "Record scan event"
   - Result: ✅ Scan recorded, NO alert sent

2. **Super Admin/Management:**
   - See scan in "Today's scan history"
   - See scan in "All Scan Events"

3. **Parent:**
   - No SMS alert (student is inside campus)

---

### Test Case 2: Exit Scan OUTSIDE Safe Zone (Alert Sent)

1. **First, configure safe perimeter in Admin:**
   - Go to Admin → Manage Settings
   - Set center coordinates: Lat 6.5244, Lng 3.3792
   - Set radius: 500 meters
   - Click Save

2. **Staff/Security:**
   - Select a student
   - Event type: **Exit**
   - Location: "Off Campus"
   - Lat: 6.5300, Lng: 3.3800 (Outside the 500m radius)
   - Click "Record scan event"
   - Result: ✅ Scan recorded, SMS ALERT sent

3. **Super Admin/Management:**
   - See scan in "All Scan Events"
   - See geofence event in "All Geofence Events"
   - Event shows: "[Student] Exited safe perimeter"

4. **Parent:**
   - ✅ Receives SMS alert (if phone number is configured):
     ```
     Alert: [Student Name] Exit outside safe perimeter. 
     Location: Off Campus. 
     Map: https://www.google.com/maps/search/?api=1&query=6.5300,3.3800
     ```

---

### Test Case 3: Pickup Scan (Late Pickup Detection)

1. **Staff/Security:**
   - Select a student
   - Event type: **Pickup**
   - Location: "Main Entrance"
   - Lat: 6.5244, Lng: 3.3792 (Inside safe zone)
   - Click "Record scan event"

2. **Super Admin/Management:**
   - See scan in "All Scan Events"
   - See scan in "Late Pickups" if it's today

---

## Important Configuration Requirements

### For SMS Alerts to Work:

1. **Parent phone number must be set:**
   - Admin → Create User → Enter parent's phone
   - Format: International format (e.g., +1234567890)

2. **Parent-Student relationship must exist:**
   - Admin → Manage Users → Link parent to student

3. **Safe perimeter must be configured:**
   - Admin → Manage Settings → Set coordinates and radius

4. **Twilio account must be configured:**
   - Environment variables: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`

### For Testing WITHOUT Twilio:

If SMS setup isn't complete, you'll see:
- Scan still recorded ✅
- Geofence event still created ✅
- Parent alert notification will fail silently ⚠️

---

## Data Visible to Each Role

| Data | Super Admin | Management | Staff/Security | Parent | Student |
|------|------------|-----------|----------------|--------|---------|
| All scan events | ✅ | ✅ | ❌ | Only own child | ❌ |
| Today's scans | ✅ | ✅ | ✅ | ❌ | ❌ |
| Geofence events | ✅ | ✅ | ❌ | Own child events | ❌ |
| Late pickups | ✅ | ✅ | ❌ | ❌ | ❌ |
| Download reports | ✅ | ✅ | ❌ | ❌ | ❌ |
| Receive SMS alerts | ❌ | ❌ | ❌ | ✅ | ❌ |

---

## Troubleshooting

### Scan recorded but no alert sent:
- ✅ Check if coordinates are INSIDE safe perimeter (no alert sent inside)
- ✅ Verify parent has phone number configured
- ✅ Check Twilio credentials in environment variables
- ✅ Verify parent-student relationship exists

### Parent not linked to student:
- Go to Admin → Manage Users
- Select parent user
- Click "Link to Student"
- Choose the student
- Click Save

### Safe perimeter not working:
- Go to Admin → Manage Settings
- Configure center latitude/longitude
- Set radius in meters (e.g., 500)
- Click Save

---

## Quick Testing Script

```
1. Create users:
   - Admin1 (Super Admin)
   - Security1 (Staff/Security)
   - John (Student)
   - Parent1 (Parent)

2. Link Parent1 to John (Admin → Manage Users)

3. Configure safe perimeter (Admin → Manage Settings)
   - Center: Your test coordinates
   - Radius: 500 meters

4. Sign in as Security1

5. Go to Security Dashboard

6. Scan John with Exit event outside perimeter

7. Check: 
   - ✅ Scan appears in "Today's scan history"
   - ✅ Admin sees scan in "All Scan Events"
   - ✅ Admin sees geofence event in "All Geofence Events"
   - ✅ Parent receives SMS alert (if Twilio configured)
```
