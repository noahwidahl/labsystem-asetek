from datetime import datetime
from app.models.sample import Sample
from app.utils.db import DatabaseManager

class SampleService:
    def __init__(self, mysql):
        self.mysql = mysql
        self.db = DatabaseManager(mysql)
    
    def get_all_samples(self):
        query = """
            SELECT 
                s.SampleID, 
                s.Barcode, 
                s.IsUnique,
                s.Type,
                s.Description, 
                s.Status,
                ss.AmountRemaining, 
                s.UnitID,
                s.OwnerID,
                s.ReceptionID
            FROM Sample s
            JOIN SampleStorage ss ON s.SampleID = ss.SampleID
            WHERE ss.AmountRemaining > 0
            ORDER BY s.SampleID DESC
        """
        
        result, _ = self.db.execute_query(query)
        
        samples = []
        for row in result:
            samples.append(Sample.from_db_row(row))
        
        return samples
    
    def get_sample_by_id(self, sample_id):
        query = """
            SELECT 
                s.SampleID, 
                s.Barcode, 
                s.IsUnique,
                s.Type,
                s.Description, 
                s.Status,
                ss.AmountRemaining, 
                s.UnitID,
                s.OwnerID,
                s.ReceptionID
            FROM Sample s
            JOIN SampleStorage ss ON s.SampleID = ss.SampleID
            WHERE s.SampleID = %s
        """
        
        result, _ = self.db.execute_query(query, (sample_id,))
        
        if not result or len(result) == 0:
            return None
        
        return Sample.from_db_row(result[0])
    
    def create_sample(self, sample_data, user_id):
        with self.db.transaction(isolation_level="REPEATABLE READ") as cursor:
            # Håndtering af supplier
            supplier_id = None
            if sample_data.get('supplier') and sample_data.get('supplier').strip():
                try:
                    supplier_id = int(sample_data.get('supplier'))
                except (ValueError, TypeError):
                    supplier_id = None
            
            # Sikre korrekt dato-formattering
            reception_date = datetime.now()
            if sample_data.get('receptionDate'):
                try:
                    reception_date = datetime.strptime(sample_data.get('receptionDate'), '%Y-%m-%d')
                except (ValueError, TypeError):
                    reception_date = datetime.now()
            
            # Indsæt reception post
            cursor.execute("""
                INSERT INTO Reception (
                    SupplierID, 
                    ReceivedDate, 
                    UserID, 
                    TrackingNumber,
                    SourceType,
                    Notes
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                supplier_id,
                reception_date,
                user_id,
                sample_data.get('trackingNumber', ''),
                'Ekstern' if supplier_id else 'Intern',
                sample_data.get('other', 'Registreret via lab system')
            ))
            
            reception_id = cursor.lastrowid
            
            # Bestem om det er en multi-pakke eller enkelt prøve
            is_multi_package = sample_data.get('isMultiPackage', False)
            package_count = int(sample_data.get('packageCount', 1)) if is_multi_package else 1
            
            # Generer en unik barcode hvis ikke angivet
            base_barcode = sample_data.get('barcode', '')
            if not base_barcode:
                base_barcode = f"BC{reception_id}-{int(datetime.now().timestamp())}"
            
            # Variable til at holde styr på sample_id og storage_id for den første prøve
            first_sample_id = None
            first_storage_id = None
            
            # Bestem om pakkerne har forskellige lokationer
            different_locations = sample_data.get('differentLocations', False)
            package_locations = sample_data.get('packageLocations', [])
            
            # Flag for containeroprettelse
            create_containers = sample_data.get('createContainers', False)
            container_ids = []  # Liste til at holde styr på oprettede containere
            
            # Iterér gennem antal pakker
            for i in range(package_count):
                # Generer barcode for hver pakke
                barcode = f"{base_barcode}-{i+1}" if package_count > 1 else base_barcode
                
                # Beregn mængde per pakke
                total_amount = int(sample_data.get('totalAmount', 0))
                amount_per_package = int(sample_data.get('amountPerPackage', total_amount // package_count)) if is_multi_package else total_amount
                
                # Juster sidste pakke hvis der er rest ved division
                if i == package_count - 1 and not is_multi_package and total_amount % package_count != 0:
                    amount_per_package += total_amount % package_count
                
                # Indsæt prøven i Sample tabel
                cursor.execute("""
                    INSERT INTO Sample (
                        Barcode, 
                        IsUnique, 
                        Type, 
                        Description, 
                        Status, 
                        Amount, 
                        UnitID, 
                        OwnerID, 
                        ReceptionID
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    barcode,
                    1 if sample_data.get('hasSerialNumbers') else 0,
                    sample_data.get('sampleType', 'Standard'),
                    sample_data.get('description') + (f" (Pakke {i+1})" if is_multi_package and package_count > 1 else ""),
                    "På lager",
                    amount_per_package,
                    sample_data.get('unit'),
                    sample_data.get('owner'),
                    reception_id
                ))
                
                sample_id = cursor.lastrowid
                
                # Gem den første sample_id for senere reference
                if first_sample_id is None:
                    first_sample_id = sample_id
                
                # Bestem lokation for denne pakke
                location_id = None
                if different_locations and package_locations:
                    # Find pakkedata for denne pakkenummer
                    package_data = next((p for p in package_locations if str(p.get('packageNumber', '')) == str(i+1)), None)
                    if package_data:
                        location_id = package_data.get('locationId')
                
                # Brug standard lokation hvis ingen specifik findes
                if not location_id:
                    location_id = sample_data.get('storageLocation')
                    
                # Sikkerhedstjek - sæt standard lokation hvis stadig ingen
                if not location_id:
                    location_id = "1"
                
                # Indsæt til SampleStorage med den valgte lokation
                cursor.execute("""
                    INSERT INTO SampleStorage (
                        SampleID, 
                        LocationID, 
                        AmountRemaining, 
                        ExpireDate
                    )
                    VALUES (%s, %s, %s, %s)
                """, (
                    sample_id,
                    location_id,
                    amount_per_package,
                    sample_data.get('expiryDate')
                ))
                
                storage_id = cursor.lastrowid
                
                # Gem den første storage_id for senere reference
                if first_storage_id is None:
                    first_storage_id = storage_id
                
                # Opret container hvis create_containers er true
                if create_containers:
                    # Implementer containeroprettelse her
                    pass
            
            # Håndter serienumre hvis relevant
            if sample_data.get('hasSerialNumbers') and sample_data.get('serialNumbers'):
                serial_numbers = sample_data.get('serialNumbers')
                for i, serial_number in enumerate(serial_numbers):
                    cursor.execute("""
                        INSERT INTO SampleSerialNumber (
                            SampleID, 
                            SerialNumber
                        )
                        VALUES (%s, %s)
                    """, (
                        first_sample_id,
                        serial_number
                    ))
            
            # Log aktiviteten i History tabellen
            cursor.execute("""
                INSERT INTO History (
                    Timestamp, 
                    ActionType, 
                    UserID, 
                    SampleID, 
                    Notes
                )
                VALUES (NOW(), %s, %s, %s, %s)
            """, (
                'Modtaget',
                user_id,
                first_sample_id,
                f"Prøve(r) registreret: {package_count} pakke(r) - total mængde: {sample_data.get('totalAmount')}"
            ))
            
            # Returner relevant data
            response_data = {
                'success': True, 
                'sample_id': f"PRV-{first_sample_id}", 
                'reception_id': reception_id,
                'package_count': package_count
            }
            
            if create_containers and container_ids:
                response_data['container_ids'] = container_ids
                
            return response_data