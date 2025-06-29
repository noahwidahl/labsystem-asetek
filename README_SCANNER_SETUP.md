# Asetek Lab System - Scanner Setup Guide

## Zebra MC330M Scanner Configuration

This guide covers the complete setup process for the Zebra MC330M handheld scanner (Android 7.1.2) with Windows computer integration.

### Prerequisites
- Zebra MC330M scanner with Android 7.1.2
- Windows computer with WiFi/Bluetooth capability
- Network access to the lab system
- Administrative rights on Windows computer

---

## Step 1: Zebra MC330M Initial Setup

### 1.1 Power On and Initial Configuration
1. **Power on the scanner**
2. **Complete Android setup** if first time:
   - Select language (English)
   - Connect to WiFi network
   - Skip Google account setup if not needed
   - Set device name: `Asetek-Scanner-01`

### 1.2 Configure Scanner Settings
1. **Open Settings app** on the scanner
2. **Navigate to**: Settings → Sound & Notification
3. **Enable scanner beep**: Turn on scan beep for audio feedback
4. **Set volume**

### 1.3 Install DataWedge (Scanner Software)
1. **DataWedge should be pre-installed**. If not:
   - Download from Zebra support site
   - Install via USB or WiFi transfer
2. **Open DataWedge app**
3. **Create new profile**:
   - Profile name: `LabSystem`
   - Enable profile: ✓

### 1.4 Configure DataWedge Profile
1. **In DataWedge, select `LabSystem` profile**
2. **Configure Barcode Input**:
   - Enable: ✓
   - Scanner selection: Internal Imager
   - Decode Illumination: Enable
   - Decode Audio: Enable
   - Decode Haptic: Enable

3. **Configure Keystroke Output**:
   - Enable: ✓
   - Output method: Send via intent
   - Intent settings:
     - Intent action: `com.asetek.labsystem.SCAN`
     - Intent category: Default
     - Intent delivery: Broadcast

4. **Advanced Settings**:
   - Multi-barcode: Disabled
   - Picklist mode: Disabled
   - Aim type: Trigger
   - Trigger mode: Normal

---

## Step 2: Windows Computer Setup

### 2.1 Network Configuration
1. **Ensure Windows computer and scanner are on same network**
2. **Test network connectivity**:
   - Open Command Prompt
   - Ping scanner IP: `ping [scanner-ip]`
   - Verify response

### 2.2 Browser Configuration
1. **Use Chrome or Edge browser** 
2. **Enable JavaScript and cookies**

### 2.3 USB Debugging (Alternative Connection)
1. **Enable Developer Options** on scanner:
   - Settings → About → Tap Build Number 7 times
2. **Enable USB Debugging**:
   - Settings → Developer Options → USB Debugging: ✓
3. **Install ADB drivers** on Windows computer
4. **Connect via USB cable**

---

## Step 3: Lab System Integration

### 3.1 Scanner App Configuration
1. **Open browser on Windows computer**
2. **Navigate to lab system**: `http://[lab-system-ip]:5000`
3. **Go to Scanner page** from navigation menu
4. **Test scanner connectivity**:
   - Click "Test Scan" button
   - Verify popup appears with test data

### 3.2 Barcode Format Verification
The system supports these barcode formats:
- **Containers**: `CNT-123` (CNT- prefix + number)
- **Samples**: `SMP-123` or `BC1-1234567890-1` (SMP- prefix or BC format)
- **Test Samples**: `TST-123` (TST- prefix + number)

### 3.3 Scanner Testing Process
1. **Physical barcode test**:
   - Create test barcode with format `CNT-1`
   - Scan with Zebra scanner
   - Verify popup appears with container details

2. **Manual input test**:
   - Use manual input field on scanner page
   - Enter `SMP-1` and click search
   - Verify sample details appear

---

## Step 4: Advanced Configuration

### 4.1 Scanner Optimization
1. **Adjust scan settings** in DataWedge:
   - Scan timeout: 5 seconds
   - Decode timeout: 2 seconds
   - Same symbol timeout: 1 second
   - Different symbol timeout: 1 second

2. **Barcode symbology settings**:
   - Enable: Code 128, Code 39, EAN-13, EAN-8, UPC-A, UPC-E
   - Enable: QR Code, Data Matrix
   - Disable unused symbologies for better performance

### 4.2 Network Optimization
1. **WiFi settings on scanner**:
   - Set WiFi sleep policy: Never
   - Enable WiFi frequency band: 2.4GHz + 5GHz
   - Set WiFi optimization: Balanced

2. **Windows firewall**:
   - Allow Flask app through firewall
   - Add exception for port 5000

---

## Step 5: Troubleshooting

### 5.1 Scanner Not Scanning
**Symptoms**: Scanner doesn't trigger or respond
**Solutions**:
1. Check battery level (charge if below 20%)
2. Restart scanner: Hold power button for 10 seconds
3. Verify DataWedge profile is active
4. Check scan button is not stuck
5. Clean scan window with soft cloth

### 5.2 No Popup in Browser
**Symptoms**: Scanning doesn't show popup modal
**Solutions**:
1. Check browser JavaScript is enabled
2. Open browser developer tools (F12) → Console
3. Look for JavaScript errors
4. Refresh page and try again
5. Test with manual input first

### 5.3 Network Connection Issues
**Symptoms**: Scanner can't reach lab system
**Solutions**:
1. Verify WiFi connection on scanner
2. Check Windows computer network connection
3. Ping test from both devices
4. Restart router/WiFi if needed
5. Check firewall settings

### 5.4 Barcode Not Found
**Symptoms**: "Barcode not found" error message
**Solutions**:
1. Verify barcode format matches database
2. Check if item exists in system
3. Test with known working barcode
4. Check database connectivity

---

## Step 6: Daily Operation

### 6.1 Startup Procedure
1. **Power on scanner**
2. **Verify connection** to lab system
3. **Test scan** with known barcode
4. **Check battery level** (charge if needed)

### 6.2 Scanning Workflow
1. **Navigate to Scanner page** in lab system
2. **Aim scanner** at barcode
3. **Press trigger** to scan
4. **View results** in popup modal
5. **Take action** (move, test, etc.) as needed

### 6.3 End of Day
1. **Charge scanner** in cradle
2. **Check scan statistics** on scanner page
3. **Clear scan history** if needed
4. **Backup scan logs** if required

---

## Technical Specifications

### Supported Barcode Types
- **1D**: Code 128, Code 39, EAN-13, EAN-8, UPC-A, UPC-E, Code 93, Codabar
- **2D**: QR Code, Data Matrix, PDF417, Aztec

### Network Requirements
- **Security**: WPA/WPA2-PSK, WEP, Open
- **Protocols**: TCP/IP, HTTP/HTTPS

### System Requirements
- **Browser**: Chrome 90+, Edge 90+, Firefox 88+
- **JavaScript**: ES6 support required
- **Network**: Same subnet as lab system
- **Ports**: 5000 (HTTP), 443 (HTTPS if configured)