# QR Code Scanner Guide

## Overview

The Redemption Gate system uses QR codes for fast and reliable student identification at gates. QR codes can be scanned using various methods - from smartphones to professional handheld scanners.

---

## QR Code Scanning Methods

### Method 1: Smartphone Camera (Free - Built-in)

**Requirements:**
- Any modern smartphone (iOS or Android)
- Built-in camera app

**Steps:**
1. Open your phone's camera app
2. Point at the QR code on screen
3. A popup notification appears with the student code
4. Tap the notification to copy or read the code
5. Use for manual verification if needed

**Pros:** No app installation, instant
**Cons:** Requires manual entry into system

---

### Method 2: QR Scanner App (Free - Recommended)

**Recommended Apps:**
- **QR Scanner** (iOS & Android) - Free
- **QR Code Reader** (iOS & Android) - Free
- **Google Lens** (Android) - Free
- **NFC Tools** (For NFC-enabled badges) - Free

**Steps:**
1. Download a QR scanner app from App Store or Google Play
2. Open the app
3. Point camera at QR code
4. App displays the student code
5. Use for reference or manual entry

**Pros:** Dedicated functionality, clear display
**Cons:** Requires app installation

---

### Method 3: Professional Handheld Scanner (Recommended for High Volume)

**Equipment:**
- Laser or image-based handheld barcode/QR scanner
- Examples: Zebra DS3678, Honeywell PM45, etc.
- Cost: $200-$1000

**Brands:**
- Zebra Technologies
- Honeywell
- Datalogic
- Symbol Technologies

**Setup:**
1. Connect scanner to computer/tablet at gate
2. Configure scanner to read QR codes
3. Point laser at QR code printed on badge
4. Data automatically transmits to system
5. Event logged instantly

**Pros:** Fast, professional, high throughput (100+ students/hour)
**Cons:** Equipment cost

---

### Method 4: Tablet/iPad at Gate (Budget-Friendly Alternative)

**Requirements:**
- Old iPad or Android tablet
- Free QR scanner app
- Mounted at gate entrance

**Setup:**
1. Install QR scanner app on tablet
2. Mount tablet at gate with good lighting
3. Staff point students' QR codes at tablet camera
4. App displays student code
5. Staff manually selects event (Entry/Exit/Pickup)
6. System records event

**Pros:** Affordable, reusable
**Cons:** Manual entry still required

---

## Current System Setup

### At Security Dashboard

**Option 1: QR Scanner Method**
1. Select "Pre-configured gates" location
2. Display QR code on screen
3. Staff scans QR code using:
   - Smartphone camera
   - QR scanner app
   - Handheld scanner
   - Tablet camera
4. Student identified instantly
5. Select event type (Entry/Exit/Pickup)
6. Click "Record scan event"

**Option 2: Manual Entry Method (Backup)**
1. View the text code displayed
2. Manually search for student name
3. Select from dropdown
4. Fill event details
5. Record scan

---

## Printing QR Codes

### For Student Badges

1. **Generate QR codes in Redemption Gate:**
   - Admin → Download Reports
   - Export student QR codes as PDF
   - Each student gets unique QR code

2. **Print options:**
   - Small (1"x1") on student ID badge
   - Medium (2"x2") on wristband
   - Large (4"x4") on printed poster at gates

3. **Materials:**
   - Laminated badge cards ($1-2 each)
   - Wristband stickers ($0.50 each)
   - Durable outdoor labels for gates

4. **Distribution:**
   - Give students their badge with QR code
   - Display QR codes at all gates
   - Emergency contact cards with QR code

---

## Best Practices

### For High-Volume Scanning (100+ students)

1. **Use professional handheld scanner**
   - Connected to gate computer
   - Fastest throughput
   - Hands-free operation

2. **Mount displays at gates**
   - Show student schedules
   - Display QR codes to scan
   - Real-time event logging

3. **Train staff**
   - Practice scanning technique
   - Understand QR angle (45-90 degrees works)
   - Know backup manual entry

### For Low-Volume Scanning (Under 50 students)

1. **Use smartphone camera**
   - No equipment cost
   - Staff already have phones
   - Built-in functionality

2. **Display QR on screen**
   - Or print on student badges
   - Keep backup manual entry option

3. **Simple workflow:**
   - Scan QR with phone
   - Enter event manually
   - Done

---

## Troubleshooting

### QR Code Won't Scan

**Problem:** Scanner can't read QR code
**Solutions:**
- Ensure adequate lighting
- Point directly at code (not at angle)
- Increase QR code size
- Check for glare on screen
- Use manual entry backup

### Scanner App Not Working

**Problem:** QR scanner app freezes or won't read
**Solutions:**
- Restart the app
- Update the app to latest version
- Check camera permissions (Settings → Camera)
- Switch to different app
- Use smartphone camera native function
- Use manual entry backup

### Student Code Doesn't Match

**Problem:** Scanned code shows wrong student
**Solutions:**
- Verify QR code is for correct student
- Check if student has been edited/updated
- Rescan carefully
- Use manual search method

### High Failure Rate

**Problem:** Many scans fail, staff frustrated
**Solutions:**
- Provide better lighting at gates
- Increase QR code size
- Train staff on proper scanning technique
- Consider handheld scanner equipment
- Implement backup manual entry workflow

---

## Recommended Setup by School Size

### Small School (100-200 students)

**Setup:**
- Smartphone camera apps for staff
- Display QR on computer screen at gate
- Print QR codes on student badges
- Use manual entry as backup

**Cost:** $0 (free smartphone app)
**Throughput:** 50-100 students/hour

---

### Medium School (200-500 students)

**Setup:**
- Tablet at gate with QR scanner app
- Print QR codes on student ID badges
- Handheld scanner optional for peak times

**Cost:** $100-200 (tablet + stand)
**Throughput:** 100-200 students/hour

---

### Large School (500+ students)

**Setup:**
- Professional handheld QR scanner
- Connected to gate computer
- Mounted displays showing real-time logs
- Dedicated security staff

**Cost:** $500-2000 (handheld scanner + setup)
**Throughput:** 200+ students/hour

---

## Integration with Redemption Gate

### Automatic Event Logging

When QR code is scanned:
1. ✅ Student identified instantly
2. ✅ Event type selected (Entry/Exit/Pickup)
3. ✅ Location auto-populated
4. ✅ Timestamp recorded
5. ✅ GPS coordinates logged
6. ✅ Event appears in dashboard
7. ✅ Parent notified if outside safe zone

### Real-Time Monitoring

**Staff/Security Dashboard shows:**
- Today's scans (live updates)
- Which students are on campus
- Who has exited
- Late pickups

**Management Dashboard shows:**
- Scan history (searchable)
- Geofence events
- Anomalies and alerts
- Compliance reports

---

## Next Steps

1. **Choose your scanning method** (smartphone, app, handheld)
2. **Train your staff** on the workflow
3. **Print QR codes** on student badges/cards
4. **Test the system** with a few students
5. **Refine based on feedback**
6. **Roll out to full school**

---

## Support

**QR Code Not Working?**
- Check [SCANNING_WORKFLOW.md](SCANNING_WORKFLOW.md) for general workflow
- Try manual entry method
- Contact admin to regenerate QR code

**Questions?**
- Refer to staff training materials
- Contact school administrator
- Use manual entry backup method
