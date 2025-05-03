# Scanner & Printer Integration Guide

Dette dokument beskriver, hvordan du opsætter og konfigurerer Zebra MC330M scanneren og Brother QL-810W labelprinter til brug med LabSystem.

## Forudsætninger

- LabSystem kører på port 5000
- Computeren og scanneren er på samme netværk
- Brother QL-810W printeren er korrekt installeret på computeren

## Opsætning af Flask-applikationen

1. **Miljøvariable**

   Tilføj følgende miljøvariable til din `.env` fil:

   ```
   # Printerapp konfiguration
   BROTHER_APP_PATH=/sti/til/din/brother/printer/app
   ```

   Erstat `/sti/til/din/brother/printer/app` med den faktiske sti til den lokale Brother-printerapplikation.

2. **Firewall-konfiguration**

   Sørg for, at port 5000 er åben i firewallen, så scanneren kan kommunikere med Flask-applikationen.

   ```
   # På Linux
   sudo ufw allow 5000/tcp
   
   # På Windows (som administrator)
   netsh advfirewall firewall add rule name="Flask LabSystem" dir=in action=allow protocol=TCP localport=5000
   ```

3. **Start Flask-applikationen**

   Start Flask-applikationen med følgende kommando:

   ```
   python run.py
   ```

   Dette vil starte serveren på port 5000 og gøre det tilgængelig på dit lokale netværk.

## Konfiguration af Zebra MC330M Scanner

1. **Åbn DataWedge på scanneren**

   - Find og åbn DataWedge-applikationen på din Zebra scanner
   - Gå til Profiles og find "Lab scan" profilen

2. **Konfigurér HTTP output**

   Opdatér følgende indstillinger:

   - **Basic output**: Deaktivér
   - **HTTP**: Aktivér
   - **HTTP URL**: `http://[FLASK_SERVER_IP]:5000/api/scanner/data`
      - Erstat `[FLASK_SERVER_IP]` med din Flask-servers IP-adresse
      - Du kan finde din IP-adresse i LabSystem på Scanner-siden
   - **HTTP Method**: `POST`
   - **Content-Type**: `application/json`

3. **Konfigurér Data Formatting**

   - Vælg `Enable Data Formatting`
   - Indstil Output Template til: `{"barcode":"%SCAN"}`
   - Dette sikrer, at den scannede stregkode sendes i det korrekte JSON-format

4. **Aktivér profilen**

   - Sørg for at "Lab scan" profilen er aktiveret
   - Test ved at scanne en stregkode

## Brother QL-810W Printer Integration

1. **Lokal Printer App**

   Hvis der allerede eksisterer en lokal app til at udskrive labels:
   
   - Notér stien til den lokale printerapp
   - Indstil `BROTHER_APP_PATH` miljøvariabel til denne sti
   - Sørg for at printerappen accepterer en tekstfil som input

2. **Direkte Integration**

   Hvis der ikke er en lokal app, kan du installere Python-biblioteker til Brother-printere:
   
   ```
   pip install brother_ql
   ```
   
   Og derefter opdatere printer.py til at bruge biblioteket direkte.

## Test af Integrationen

1. **Scanner Test**

   - Åbn LabSystem i en browser
   - Naviger til "Scanner"-siden
   - Tjek at serverens IP vises korrekt
   - Indtast en stregkode manuelt og klik på "Søg" for at teste
   - Scan en fysisk stregkode med Zebra-scanneren

2. **Printer Test**

   - Naviger til "Scanner"-siden
   - Klik på "Udskriv Testlabel" for at teste printeren
   - Hvis testen lykkes, skulle der blive udskrevet en testlabel

## Fejlfinding

### Scanner Problemer

- **Scanner kan ikke forbinde til Flask**: Kontrollér at enheden er på samme netværk, og at port 5000 er åben i firewallen
- **Ingen data modtages**: Kontrollér DataWedge-konfigurationen, især Output Template formatet
- **Stregkoder ikke genkendt**: Tjek databasen for at sikre, at stregkoderne er registreret korrekt

### Printer Problemer

- **Kan ikke finde printer-app**: Kontrollér sti i BROTHER_APP_PATH miljøvariablen
- **Fejl ved udskrivning**: Tjek at printeren er tændt, forbundet og har papir/labels
- **Forkert format på labels**: Justér formattering i printer.py's format_label funktion

## API Dokumentation

### Scanner API

- **Endpoint**: `/api/scanner/data`
- **Metode**: POST
- **Format**:
  ```json
  {
    "barcode": "123456789"
  }
  ```
- **Respons**:
  ```json
  {
    "status": "success",
    "message": "Stregkode scannet og fundet",
    "sample": {
      "SampleID": 123,
      "SampleIDFormatted": "SMP-123",
      "Description": "Sample description",
      ...
    }
  }
  ```

### Printer API

- **Endpoint**: `/api/print/label`
- **Metode**: POST
- **Format**:
  ```json
  {
    "label_type": "sample",
    "data": {
      "SampleIDFormatted": "SMP-123",
      "Description": "Sample description",
      ...
    }
  }
  ```
- **Respons**:
  ```json
  {
    "status": "success",
    "message": "Label udskrevet succesfuldt"
  }
  ```

## Sikkerhedsovervejelser

- Systemet er designet til brug på et internt netværk
- Der er ingen autentificering på API-endpoints, så de bør ikke eksponeres på internettet
- For øget sikkerhed, overvej at implementere API-nøgler eller anden autentificering