# Entra ID Authentication Setup Guide

Dette dokument beskriver hvordan du opsætter Microsoft Entra ID (Azure AD) authentication i LabSystem.

## 1. Azure Portal Konfiguration

### Registrer applikationen i Azure Portal

1. Log ind på [Azure Portal](https://portal.azure.com)
2. Gå til **Microsoft Entra ID**
3. Vælg **App registrations** → **New registration**

### Application Registration Settings

- **Name:** `LabSystem-{DinVirksomhed}`
- **Supported account types:** `Accounts in this organizational directory only (Single tenant)`
- **Redirect URI:** 
  - Type: `Web`
  - URL: `http://localhost:5000/auth/callback` (eller din server URL)

### Efter registrering

1. **Kopier følgende værdier:**
   - Application (client) ID
   - Directory (tenant) ID

2. **Opret Client Secret:**
   - Gå til **Certificates & secrets**
   - Klik **New client secret**
   - Beskrivelse: `LabSystem Server Secret`
   - Expires: `24 months` (anbefalet)
   - **Kopier secret VALUE (ikke ID)**

3. **Konfigurer API permissions:**
   - Gå til **API permissions**
   - **Microsoft Graph** permissions skal allerede være tilføjet:
     - `User.Read` (Type: Delegated)
   - Hvis ikke, klik **Add a permission** → **Microsoft Graph** → **Delegated permissions** → **User.Read**

4. **Authentication indstillinger:**
   - Under **Authentication** tab
   - **Access tokens:** ✅ Checked
   - **ID tokens:** ✅ Checked
   - **Allow public client flows:** ❌ No

## 2. Server Konfiguration

### Environment Variables (.env fil)

Kopier `.env.mssql.example` til `.env` og tilføj:

```bash
# Azure/Entra ID Configuration
AZURE_CLIENT_ID=din-application-client-id
AZURE_CLIENT_SECRET=din-client-secret-value
AZURE_TENANT_ID=din-tenant-id

# Flask secret (generer en sikker nøgle)
SECRET_KEY=din-meget-sikre-hemmelighed-her
```

### Installer dependencies

```bash
pip install -r requirements.txt
```

## 3. Database Migration

Systemet vil automatisk oprette brugere baseret på deres Microsoft 365 email som WindowsLogin.

**Eksisterende brugere:** Hvis du har eksisterende brugere i `user` tabellen, opdater deres `WindowsLogin` felt til deres Microsoft 365 email adresse:

```sql
UPDATE [user] 
SET [WindowsLogin] = 'bruger@dinvirksomhed.com' 
WHERE [Name] = 'Bruger Navn';
```

## 4. Test Konfiguration

### Start server

```bash
python run_mssql.py
```

### Test authentication

1. **Åbn browser:** `http://localhost:5000`
2. **Forventet flow:**
   - Automatisk redirect til `/login`
   - Klik "Login med Microsoft 365"
   - Microsoft login popup
   - Efter succesfuld login → redirect til dashboard

### Debugging

**Tjek server logs for fejl:**

```bash
# Almindelige fejl og løsninger:

# 1. Missing Azure config
ERROR: Missing Azure/Entra ID configuration
→ Tjek at AZURE_* environment variables er sat

# 2. Token validation failed
ERROR: Invalid access token
→ Tjek at Application (client) ID er korrekt
→ Tjek at token ikke er udløbet

# 3. Database connection failed
ERROR: Error in get_or_create_entra_user
→ Tjek MSSQL database forbindelse
```

**Browser Console:**

```javascript
// Åbn Developer Tools (F12) → Console
// Forventede log entries:
"Login successful: {account: {...}}"
"EntraAuth initialization complete"

// Fejl debugging:
localStorage.getItem('access_token')  // Skulle returnere et JWT token
window.entraAuth.getCurrentUser()     // Skulle returnere user info
```

## 5. Produktions Deployment

### Linux Server Setup

1. **Install dependencies på server:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment variables:**
   ```bash
   export AZURE_CLIENT_ID="din-client-id"
   export AZURE_CLIENT_SECRET="din-client-secret"
   export AZURE_TENANT_ID="din-tenant-id"
   export SECRET_KEY="din-sikre-secret-key"
   ```

3. **Update Redirect URI i Azure:**
   - Gå til Azure Portal → Din App Registration
   - **Authentication** → **Redirect URIs**
   - Tilføj: `https://din-server.com/auth/callback`

### Nginx Configuration (anbefalet)

```nginx
server {
    listen 80;
    server_name din-server.com;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 6. Sikkerhed

### Production Security Checklist

- ✅ Brug HTTPS i produktion
- ✅ Generer sikker SECRET_KEY (ikke default)
- ✅ Begræns CORS settings hvis nødvendigt
- ✅ Regular client secret rotation (Azure Portal)
- ✅ Monitor authentication logs
- ✅ Set proper token expiration times

### Brugerstyring

**Automatisk brugeroprettelse:** Systemet opretter automatisk nye brugere første gang de logger ind.

**Rolle management:** Alle nye brugere får `Admin` rolle som standard. Opdater i databasen efter behov:

```sql
UPDATE [user] 
SET [Role] = 'User' 
WHERE [WindowsLogin] = 'bruger@dinvirksomhed.com';
```

## 7. Troubleshooting

### Almindelige problemer

| Problem | Løsning |
|---------|---------|
| "No access token provided" | Tjek at MSAL.js loader korrekt, og at popup ikke blokeres |
| "Invalid token" | Tjek Azure app konfiguration og token expiration |
| "User not authenticated" | Tjek database forbindelse og brugeroprettelse |
| Login popup blokeret | Tillad popups for din domain i browser |
| Token expired | Systemet skulle automatisk refresh - tjek browser console |

### Support

Ved spørgsmål eller problemer:

1. Tjek server logs (`python run_mssql.py`)
2. Tjek browser console (F12)
3. Verificer Azure Portal konfiguration
4. Test database forbindelse separat

## Migration fra Windows Auth

**Det gamle system** brugte Windows environment variables (`USERDOMAIN\USERNAME`).

**Det nye system** bruger Microsoft 365 email som login identifier.

**Migration steps:**

1. Kør det nye system parallelt for test
2. Opdater eksisterende brugeres `WindowsLogin` til deres email
3. Test at alle brugere kan logge ind
4. Skift til production når du er tilfreds

**Rollback:** Du kan altid gå tilbage til den gamle `get_current_user_mssql` funktion ved at ændre import i `__init___mssql.py`.