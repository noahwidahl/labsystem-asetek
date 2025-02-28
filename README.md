# Lab System

## Installation

1. Klon dette repository
2. Opret et virtuelt miljø: `python -m venv venv`
3. Aktiver miljøet: 
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
4. Installer afhængigheder: `pip install -r requirements.txt`
5. Udfyld .env med database-oplysninger
6. Kør database setup: `python setup_database.py`
7. Start applikationen: `cd app && python app.py`
