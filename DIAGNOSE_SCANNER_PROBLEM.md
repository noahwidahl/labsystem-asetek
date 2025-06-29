# 🚨 KRITISK DIAGNOSE: Scanner/Print Problem

## HOVEDPROBLEM IDENTIFICERET

**FLASK SERVEREN KØRER IKKE!** Det er derfor INTET virker.

## Problemerne i prioritet rækkefølge:

### 1. 🔴 KRITISK: Flask Server
- Server er ikke startet
- Alle API calls fejler
- Ingen barcode lookup mulig
- Print jobs kan ikke oprettes

### 2. 🟡 MEDIUM: Database queries
- JOIN queries i barcode.py ser korrekte ud baseret på database schema
- Tabel struktur matcher API forventninger

### 3. 🟢 MINDRE: Frontend integration
- JavaScript barcode-scanner.js er korrekt implementeret
- Scanner siden har korrekt HTML struktur
- Print job localStorage integration virker

## LØSNINGER

### Trin 1: Start Flask serveren
```bash
cd "/mnt/c/Users/noahw/Kode/LabSystem - Asetek"
python3 run.py
```

### Trin 2: Test API endpoints
```bash
# Test sample barcode
curl -X GET "http://localhost:5000/api/barcode/BC1-1751138774-1"

# Test container barcode  
curl -X GET "http://localhost:5000/api/barcode/CNT-12"
```

### Trin 3: Test barcode scanning
1. Åbn browser til `http://localhost:5000/scanner`
2. Prøv "Test Scan" knappen
3. Prøv manual input med `BC1-1751138774-1`
4. Tjek browser console for fejl

### Trin 4: Test print job integration
1. Registrer et nyt sample
2. Gå til scanner siden
3. Tjek om print job vises inden for 5 sekunder

## TEST DATA FRA DATABASE

**Samples der findes:**
- `BC1-1751138774-1` - Tester 1
- `BC1-1751138774-2` - Tester 2  
- `BC5-1751143365` - SampleName3

**Containers der findes:**
- `CNT-12` - Bepbop123
- `CNT-13` - TestForLabel

## FORVENTEDE RESULTATER

### Barcode Scanner Response:
```json
{
  "success": true,
  "type": "sample",
  "barcode": "BC1-1751138774-1",
  "sample": {
    "SampleID": 1,
    "SampleIDFormatted": "SMP-1",
    "Barcode": "BC1-1751138774-1",
    "Description": "Tester 1",
    "Status": "In Storage"
  }
}
```

### Print Jobs localStorage:
```json
[
  {
    "id": 1234567890,
    "timestamp": "2025-06-29T...",
    "sampleId": 1,
    "sampleIdFormatted": "SMP-1",
    "barcode": "BC1-1751138774-1", 
    "description": "Tester 1",
    "status": "queued"
  }
]
```

## DEBUGGING CHECKLIST

- [ ] Flask server startet
- [ ] Database forbindelse virker
- [ ] API endpoints svarer
- [ ] Browser console ingen fejl
- [ ] `window.barcodeScanner` eksisterer
- [ ] Manual barcode input virker
- [ ] Test scan knap virker
- [ ] Print jobs loader automatisk
- [ ] Sample registration triggerer print jobs

## KRITISK: Start serveren først!

Alle andre tests er meningsløse indtil Flask serveren kører.