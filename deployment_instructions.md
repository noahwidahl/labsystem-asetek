# LabSystem Deployment Instructions

## På deres lokation:

### 1. Server Setup
```bash
# På serveren/computeren:
cd "LabSystem - Asetek"
.\venv\Scripts\Activate.ps1
python start_production.py
```

### 2. MC330M Setup

#### A. WiFi Connection
1. Settings → WiFi → Forbind til deres netværk

#### B. DataWedge Configuration
1. DataWedge → Profile: "LabSystem" 
2. Applications: "*" (alle apps)
3. Barcode Input: ON
4. Keystroke Output: ON (med Enter suffix)

#### C. Chrome Bookmark Setup
1. Åbn Chrome på MC330M
2. Gå til: `http://SERVER-IP:5000/scanner-only`
3. Tryk menu (⋮) → "Add to Home screen"  
4. Navn: "LabSystem Scanner"
5. Icon kommer på hjemmeskærm

#### D. Chrome Settings (Valgfrit)
1. Chrome → Settings → Homepage
2. Sæt til: `http://SERVER-IP:5000/scanner-only`
3. Enable "Show home button"

### 3. URL Endpoints:

- **Scanner Only**: `http://SERVER-IP:5000/scanner-only`
  - Kun scanning interface
  - Ingen adgang til hele systemet
  - Optimeret til MC330M

- **Full System**: `http://SERVER-IP:5000`
  - Komplet LabSystem
  - Kun til administratorer

- **API Test**: `http://SERVER-IP:5000/api/scanner/test-barcodes`
  - Vis tilgængelige test barcodes

### 4. Bruger Instruktioner:

#### Scanner Workflow:
1. Tryk på "LabSystem Scanner" icon på hjemmeskærm
2. Scan barcode (hør bip)
3. Se resultat på skærm
4. Fortsæt med næste scan

#### Hvis problemer:
- Tjek WiFi forbindelse
- Tjek server IP er korrekt
- Restart Chrome app
- Test med manual barcode input

## Tekniske Detaljer:

### Server Konfiguration:
- Port: 5000
- Host: 0.0.0.0 (alle interfaces)
- Database: MySQL (eksisterende)
- Scanner API: `/api/scanner/data`

### Scanner Interface Features:
- ✅ Auto-focus input field
- ✅ Real-time barcode lookup  
- ✅ Connection status indicator
- ✅ Result history (last 8 scans)
- ✅ Mobile-optimized design
- ✅ No access to main system

### Security:
- Scanner interface kan ikke:
  - Tilgå samples administration
  - Ændre data
  - Se alle samples
  - Printe labels
- Kun read-only barcode lookup