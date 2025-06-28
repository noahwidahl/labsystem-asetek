# Enhanced Scanner & Printer Integration Guide

Dette dokument beskriver den forbedrede opsætning og konfiguration af Zebra MC330M scanneren og Brother QL-810W labelprinter til brug med LabSystem.

## Systemudviklinger

### Udvidet Label System
- **Multiple printer support**: Forskellige printere til sample, container og location labels
- **Automatisk barcode generering**: Systemet genererer automatisk unikke barcodes
- **Forbedrede label formater**: Optimerede layouts for forskellige label typer
- **Audit trail**: Alle print og scan handlinger logges automatisk

### Forbedret Scanner Funktionalitet
- **Multi-type scanning**: Support for sample barcodes, serial numre, container barcodes og test identifikatorer
- **Serial nummer registration**: Automatisk linking af serial numre til unikke samples
- **Test sample scanning**: Direkte scanning af test identifikatorer (T1234.5_1 format)
- **Omfattende database lookup**: 4-lags søgning for maksimal fleksibilitet

## Forudsætninger

- LabSystem kører på port 5000
- Computeren og scanneren er på samme netværk
- Brother QL-810W printeren er korrekt installeret på computeren

## Forbedret Printer Konfiguration

1. **Multiple Printer Support**

   Tilføj følgende miljøvariable til `.env` fil for separate printere:

   ```
   # Sample labels (små, kompakte labels)
   BROTHER_SAMPLE_PRINTER_PATH=/sti/til/sample/printer/app
   
   # Container/Package labels (store labels)
   BROTHER_CONTAINER_PRINTER_PATH=/sti/til/container/printer/app
   BROTHER_PACKAGE_PRINTER_PATH=/sti/til/package/printer/app
   
   # Location labels (mellem størrelse)
   BROTHER_LOCATION_PRINTER_PATH=/sti/til/location/printer/app
   
   # Fallback printer (bruges hvis specifikke printere ikke er konfigureret)
   BROTHER_APP_PATH=/sti/til/standard/brother/printer/app
   ```

   **Note**: Hvis du kun har én printer, skal du kun sætte `BROTHER_APP_PATH` - systemet vil automatisk bruge denne til alle label typer.

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