# LabSystem USB Deployment Guide
### Asetek Laboratory Management System - Complete Setup

This guide covers the complete setup process for deploying LabSystem on a new Windows computer from USB drive, including database setup, printer configuration, and Zebra scanner integration.

---

## 📋 **Before You Start**

### What You Need:
- **USB Drive** with complete LabSystem files
- **Windows 10/11** computer with admin rights
- **Docker Desktop** (will be installed if needed)
- **Internet connection** for Docker images
- **Zebra printer** (if printing labels)
- **Zebra MC330M scanner** (if scanning barcodes)

### Estimated Time:
- **Basic setup**: 15-30 minutes
- **With printer**: +15 minutes  
- **With scanner**: +30 minutes

---

## 🚀 **Part 1: USB Preparation (Original Computer)**

### 1.1 Copy Files to USB
1. **Insert USB drive** (minimum 8GB recommended)
2. **Create folder**: `LabSystem` on USB drive
3. **Copy entire project** to USB:\n   ```
   LabSystem/
   ├── USB_AUTO_SETUP.bat          ← Main setup script
   ├── docker-compose.usb.yml      ← Docker configuration
   ├── Dockerfile.usb              ← Container build file
   ├── database/
   │   └── usb_init.sql            ← Database schema
   ├── app/                        ← Flask application
   ├── static/                     ← CSS, JS files
   ├── templates/                  ← HTML templates
   ├── requirements.txt            ← Python dependencies
   ├── .gitignore                  ← Git ignore (updated)
   └── README_USB_DEPLOYMENT.md    ← This guide
   ```

### 1.2 Verify USB Contents
1. **Check all folders** are copied
2. **Verify file sizes** match original
3. **Test USB** on another computer to ensure it works
4. **Label USB**: "LabSystem v[date] - Asetek"

---

## 💻 **Part 2: New Computer Setup**

### 2.1 Install Docker Desktop
**If Docker is not installed:**
1. **Download**: https://www.docker.com/products/docker-desktop
2. **Install with default settings**
3. **Restart computer** when prompted
4. **Start Docker Desktop**
5. **Wait for "Docker is running"** status

### 2.2 Run Auto-Setup
1. **Insert USB drive** into new computer
2. **Navigate to USB** in File Explorer
3. **Right-click** `USB_AUTO_SETUP.bat`
4. **Select "Run as administrator"**
5. **Follow on-screen instructions**

### 2.3 Setup Process Details
The script will:
- ✅ **Check Docker** installation and status
- ✅ **Generate secure MySQL password** (16 characters)
- ✅ **Create .env.usb** with all configuration
- ✅ **Download MySQL 8.0** Docker image
- ✅ **Build LabSystem** application container
- ✅ **Initialize database** with complete schema
- ✅ **Start all services**
- ✅ **Open browser** to http://localhost:5000

### 2.4 Verify Installation
1. **Browser opens** automatically to LabSystem
2. **Check system status** - all green indicators
3. **Test basic functions**:
   - Navigate between pages
   - Try sample registration
   - Check database connectivity

---

## 🖨️ **Part 3: Zebra Printer Setup**

### 3.1 Printer Connection
1. **Connect Zebra printer** via USB or network
2. **Power on printer**
3. **Install driver** if Windows doesn't auto-detect:
   - Download from Zebra website
   - Install with default settings

### 3.2 Printer Configuration
1. **Open Windows Settings** → Printers & Scanners
2. **Add printer** → Select Zebra printer
3. **Set as default** if desired
4. **Print test page** to verify

### 3.3 Label Configuration in LabSystem
1. **Navigate to Settings** in LabSystem
2. **Select Print Settings**
3. **Configure label size**:
   - Width: 25mm
   - Height: 15mm
   - DPI: 203 or 300
4. **Test print** sample label
5. **Adjust margins** if needed

### 3.4 Printer Troubleshooting
**Common issues:**
- **No driver**: Download from Zebra support
- **Wrong size**: Check label roll and settings
- **Poor quality**: Clean printhead, check ribbon
- **Network issues**: Verify IP and connectivity

---

## 📱 **Part 4: Zebra MC330M Scanner Setup**

### 4.1 Scanner Initial Configuration
1. **Power on scanner**
2. **Connect to WiFi** (same network as computer)
3. **Set device name**: `Asetek-Scanner-[XX]`
4. **Note IP address** for later use

### 4.2 DataWedge Profile Setup
1. **Open DataWedge app** on scanner
2. **Create new profile**: `LabSystem`
3. **Configure Barcode Input**:
   - Enable: ✓
   - Scanner: Internal Imager
   - Illumination: Enable
   - Audio feedback: Enable
   - Haptic feedback: Enable

4. **Configure Output**:
   - Method: Keystroke output
   - Enable: ✓
   - Send TAB: Disabled
   - Send ENTER: Enabled

### 4.3 Scanner Testing
1. **Open LabSystem** in browser
2. **Navigate to Scanner page**
3. **Create test barcode**: Print `CNT-001`
4. **Scan barcode** with scanner
5. **Verify modal popup** appears with container info

### 4.4 Barcode Format Support
The system recognizes:
- **Containers**: `CNT-123`
- **Samples**: `SMP-123`, `BC1-1234567890-1`
- **Test Samples**: `TST-123`

### 4.5 Scanner Troubleshooting
**Scanner not working:**
- Check battery level (>20%)
- Verify DataWedge profile active
- Restart scanner if needed
- Clean scan window

**No popup in browser:**
- Check JavaScript enabled
- Try manual input first
- Check browser console (F12)
- Refresh page

---

## ⚙️ **Part 5: System Configuration**

### 5.1 User Setup
1. **Login with default admin**:
   - Username: `admin`
   - Password: `admin123`
2. **Create new users** as needed
3. **Set user roles** appropriately
4. **Change admin password** immediately

### 5.2 Location Setup
1. **Navigate to Storage Locations**
2. **Add your lab locations**:
   - Freezers (-20°C, -80°C)
   - Fridges (4°C)
   - Room temperature storage
   - Specific rack/shelf positions

### 5.3 Supplier Configuration
1. **Add suppliers** your lab uses
2. **Include contact information**
3. **Set default supplier** if applicable

### 5.4 Container Types
1. **Add container types**:
   - Standard boxes
   - Plastic bags
   - Vials
   - Custom containers
2. **Set default capacities**

---

## 🔧 **Part 6: Daily Operations**

### 6.1 Starting the System
```batch
# If system is stopped, start with:
docker-compose -f docker-compose.usb.yml up -d

# Check status:
docker-compose -f docker-compose.usb.yml ps
```

### 6.2 Stopping the System
```batch
# Stop all services:
docker-compose -f docker-compose.usb.yml down

# Stop and remove data (careful!):
docker-compose -f docker-compose.usb.yml down -v
```

### 6.3 Backup Database
```batch
# Create backup:
docker exec labsystem_mysql_usb mysqldump -u labuser -p[password] lab_system > backup_[date].sql

# Restore backup:
docker exec -i labsystem_mysql_usb mysql -u labuser -p[password] lab_system < backup_[date].sql
```

---

## 🆘 **Part 7: Troubleshooting**

### 7.1 System Won't Start
**Error: Docker not running**
- Start Docker Desktop
- Wait for green status indicator

**Error: Port 5000 in use**
- Close other applications using port 5000
- Or change port in docker-compose.usb.yml

**Error: Database connection failed**
- Wait 2-3 minutes for MySQL to initialize
- Check MySQL password in .env.usb file

### 7.2 Performance Issues
**System slow:**
- Check computer resources (RAM, CPU)
- Restart Docker containers
- Clear browser cache

**Database queries slow:**
- Check disk space
- Restart MySQL container
- Consider upgrading computer specs

### 7.3 Network Issues
**Can't access from other computers:**
- Check Windows Firewall
- Allow port 5000 through firewall
- Verify all devices on same network

### 7.4 Data Recovery
**Lost database:**
- Use latest backup file
- Restore using backup commands above
- Check USB drive for backup copies

---

## 📞 **Part 8: Support Information**

### 8.1 System Information
- **Database**: MySQL 8.0
- **Application**: Python Flask
- **Web Server**: Development server (port 5000)
- **Container**: Docker with docker-compose

### 8.2 Important Files
- **Environment**: `.env.usb` (contains all passwords!)
- **Database backup**: `backup_[date].sql`
- **Logs**: Docker logs via `docker-compose logs`

### 8.3 Key Passwords
**MySQL Password**: Found in `.env.usb` file
```
# Look for this line:
MYSQL_PASSWORD=[your-auto-generated-password]
```

### 8.4 URLs and Ports
- **Main System**: http://localhost:5000
- **Database**: localhost:3306
- **Docker Dashboard**: Docker Desktop → Containers

---

## ✅ **Part 9: Success Checklist**

### Initial Setup Complete:
- [ ] Docker installed and running
- [ ] LabSystem containers started
- [ ] Database initialized with schema
- [ ] Web interface accessible at localhost:5000
- [ ] Admin login working

### Hardware Setup Complete:
- [ ] Zebra printer connected and tested
- [ ] Label printing working correctly
- [ ] Scanner connected to WiFi
- [ ] DataWedge profile configured
- [ ] Barcode scanning working in LabSystem

### System Configuration Complete:
- [ ] Users created and passwords changed
- [ ] Storage locations configured
- [ ] Suppliers added
- [ ] Container types set up
- [ ] First sample registered successfully

### Operational Ready:
- [ ] Backup procedure tested
- [ ] Scanner workflow verified
- [ ] Printing workflow verified
- [ ] Network access confirmed
- [ ] Documentation accessible

---

## 🎯 **Quick Reference Commands**

```batch
# Start system
docker-compose -f docker-compose.usb.yml up -d

# Stop system
docker-compose -f docker-compose.usb.yml down

# View logs
docker-compose -f docker-compose.usb.yml logs -f

# Database backup
docker exec labsystem_mysql_usb mysqldump -u labuser -p lab_system > backup.sql

# System status
docker-compose -f docker-compose.usb.yml ps
```

---

**🚀 LabSystem USB Deployment Guide**  
**Asetek Laboratory Management System**  
**For technical support, check logs and documentation**

*Last updated: [Date] - Complete setup guide for USB deployment*