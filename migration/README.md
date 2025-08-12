# Database Migration Guide: MySQL til SQL Server

## Trin 1: Installer SQL Server Management Tool

Vælg en af disse:

### SQL Server Management Studio (SSMS) - Anbefalet
- Download: https://aka.ms/ssmsfullsetup
- Gratis officiel Microsoft tool
- Erstatter MySQL Workbench

### Azure Data Studio - Cross-platform
- Download: https://docs.microsoft.com/en-us/sql/azure-data-studio/download
- Fungerer på alle platforme

## Trin 2: Forbered miljø

1. **Opdater .env fil:**
```bash
# Kopier eksempel-filen
cp .env.mssql.example .env

# Rediger .env med dine SQL Server detaljer
MSSQL_SERVER=din-linux-server-ip
MSSQL_DATABASE=LabSystem
MSSQL_USERNAME=sa
MSSQL_PASSWORD=dit-password
```

2. **Installer dependencies:**
```bash
pip install -r requirements.txt
```

## Trin 3: Opret SQL Server database

1. **Forbind til din Linux SQL Server**
2. **Kør database creation script:**
```sql
-- I SSMS eller Azure Data Studio
-- Åbn og kør: database/mssql_init.sql
```

## Trin 4: Migrer data

```bash
# Se hjælp
python migration/mysql_to_mssql.py --help

# Kør migration (FORSIGTIG!)
python migration/mysql_to_mssql.py

# Eller med clear target (sletter eksisterende data først)
python migration/mysql_to_mssql.py --clear-target
```

## Trin 5: Test ny applikation

```bash
# Kør med SQL Server
python run_mssql.py
```

## Fejlfinding

### Forbindelses problemer:
1. **Linux SQL Server**: Tjek at SQL Server kører
2. **Firewall**: Åbn port 1433
3. **Authentication**: Tjek SQL Server authentication mode

### Migration errors:
- Tjek `migration.log` for detaljer
- Verificer at alle tabeller er tomme i SQL Server før migration
- Tjek foreign key constraints

## Backup

**Før migration - tag backup af MySQL:**
```bash
mysqldump -u root -p lab_system > backup_before_migration.sql
```