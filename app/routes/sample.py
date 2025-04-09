from flask import Blueprint, render_template, jsonify, request, url_for
from app.services.sample_service import SampleService
from app.utils.auth import get_current_user
from app.utils.validators import validate_sample_data

sample_bp = Blueprint('sample', __name__)

def init_sample(blueprint, mysql):
    sample_service = SampleService(mysql)
    
    @blueprint.route('/register')
    def register():
        try:
            cursor = mysql.connection.cursor()
            
            # Get suppliers
            cursor.execute("SELECT SupplierID, SupplierName FROM Supplier")
            suppliers = [dict(SupplierID=row[0], SupplierName=row[1]) for row in cursor.fetchall()]
            
            # Get users
            cursor.execute("SELECT UserID, Name FROM User")
            users = [dict(UserID=row[0], Name=row[1]) for row in cursor.fetchall()]
            
            # Get units (translate 'stk' to 'pcs')
            cursor.execute("SELECT UnitID, UnitName FROM Unit ORDER BY UnitName")
            units = []
            for row in cursor.fetchall():
                unit_name = row[1]
                # Translate 'stk' to 'pcs' for consistency across the app
                if unit_name.lower() == 'stk':
                    unit_name = 'pcs'
                units.append(dict(UnitID=row[0], UnitName=unit_name))
            
            # Get locations
            cursor.execute("""
                SELECT l.LocationID, l.LocationName, lb.LabName
                FROM StorageLocation l
                JOIN Lab lb ON l.LabID = lb.LabID
            """)
            locations = []
            for row in cursor.fetchall():
                locations.append({
                    'LocationID': row[0],
                    'LocationName': row[1],
                    'LabName': row[2]
                })
            
            # Get container types
            cursor.execute("SELECT ContainerTypeID, TypeName, Description, DefaultCapacity FROM ContainerType")
            type_columns = [col[0] for col in cursor.description]
            container_types = [dict(zip(type_columns, row)) for row in cursor.fetchall()]
            
            cursor.close()
            
            return render_template('sections/register.html', 
                                suppliers=suppliers,
                                users=users,
                                units=units,
                                locations=locations,
                                container_types=container_types)
        except Exception as e:
            print(f"Error loading register page: {e}")
            return render_template('sections/register.html', 
                                error="Error loading registration form")
    
    @blueprint.route('/storage')
    def storage():
        try:
            # Initialize empty array for samples
            samples_for_template = []
            
            # Get filter parameters
            filter_criteria = {}
            search = request.args.get('search', '')
            location = request.args.get('location', '')
            status = request.args.get('status', '')
            date_from = request.args.get('date_from', '')
            date_to = request.args.get('date_to', '')
            
            # Tracking which filters are active
            if search:
                filter_criteria['search'] = search
            if location:
                filter_criteria['location'] = location
            if status:
                filter_criteria['status'] = status
            if date_from:
                filter_criteria['date_from'] = date_from
            if date_to:
                filter_criteria['date_to'] = date_to
            
            # Get sort parameters
            sort_by = request.args.get('sort_by', 'sample_id')
            sort_order = request.args.get('sort_order', 'DESC')
            
            cursor = mysql.connection.cursor()
            
            # Get dropdown options for filters
            cursor.execute("SELECT LocationID, LocationName FROM StorageLocation ORDER BY LocationName")
            locations = [dict(LocationID=row[0], LocationName=row[1]) for row in cursor.fetchall()]
            
            cursor.execute("SELECT DISTINCT Status FROM Sample")
            statuses = [row[0] for row in cursor.fetchall()]
            
            # Først prøver vi at hente data fra databasen
            try:
                # Hent alle samples inklusive disposed samples
                query = """
                SELECT 
                    s.SampleID, 
                    s.PartNumber, 
                    s.Description, 
                    CASE 
                        WHEN s.Status = 'Disposed' THEN 0
                        ELSE IFNULL(ss.AmountRemaining, 0)
                    END AS AmountRemaining, 
                    CASE
                        WHEN u.UnitName IS NULL THEN 'pcs'
                        WHEN LOWER(u.UnitName) = 'stk' THEN 'pcs'
                        ELSE u.UnitName
                    END as Unit,
                    IFNULL(sl.LocationName, 'Disposed') as LocationName, 
                    DATE_FORMAT(r.ReceivedDate, '%d-%m-%Y %H:%i') AS Registered,
                    s.Status 
                FROM Sample s
                JOIN Reception r ON s.ReceptionID = r.ReceptionID
                LEFT JOIN SampleStorage ss ON s.SampleID = ss.SampleID
                LEFT JOIN StorageLocation sl ON ss.LocationID = sl.LocationID
                LEFT JOIN Unit u ON s.UnitID = u.UnitID
                """
                
                cursor.execute(query)
                db_results = cursor.fetchall()
                print(f"Found {len(db_results)} samples from database")
                
                # Hvis der er resultater, erstat vores hardcoded data
                if db_results and len(db_results) > 0:
                    # Erstat vores hardcoded data med database data
                    samples_for_template = []
                    
                    for row in db_results:
                        sample = {
                            "ID": f"SMP-{row[0]}",
                            "PartNumber": row[1] or "",
                            "Description": row[2] or "",
                            "Amount": f"{row[3]} {row[4]}",
                            "Location": row[5] or "",
                            "Registered": row[6] or "",
                            "Status": row[7] or ""
                        }
                        samples_for_template.append(sample)
                    
                    print("Using real database data")
                else:
                    print("No samples found in database")
                    # No hardcoded data anymore, just empty array
            except Exception as e:
                print(f"Error fetching database data: {e}")
                import traceback
                traceback.print_exc()
                
            # Apply search filter
            if search:
                filtered_samples = []
                for sample in samples_for_template:
                    if (search.lower() in sample['Description'].lower() or
                        search.lower() in sample['PartNumber'].lower() or
                        search.lower() in sample['Location'].lower()):
                        filtered_samples.append(sample)
                samples_for_template = filtered_samples
                
            # Apply location filter
            if location:
                filtered_samples = []
                for sample in samples_for_template:
                    for loc in locations:
                        if loc['LocationID'] == int(location) and loc['LocationName'] == sample['Location']:
                            filtered_samples.append(sample)
                samples_for_template = filtered_samples
                
            # Apply status filter
            if status:
                filtered_samples = []
                for sample in samples_for_template:
                    if sample['Status'] == status:
                        filtered_samples.append(sample)
                samples_for_template = filtered_samples
            
            # Apply date range filter
            if date_from or date_to:
                filtered_samples = []
                for sample in samples_for_template:
                    # Get registered date (first 10 chars for date only)
                    sample_date = sample.get('Registered', '')[:10] if sample.get('Registered') else ''
                    
                    if date_from and date_to:
                        if date_from <= sample_date <= date_to:
                            filtered_samples.append(sample)
                    elif date_from:
                        if sample_date >= date_from:
                            filtered_samples.append(sample)
                    elif date_to:
                        if sample_date <= date_to:
                            filtered_samples.append(sample)
                            
                samples_for_template = filtered_samples
            
            # Apply sorting
            if sort_by == 'sample_id':
                samples_for_template.sort(key=lambda x: int(x['ID'].replace('SMP-', '')), 
                                         reverse=(sort_order == 'DESC'))
            elif sort_by == 'part_number':
                samples_for_template.sort(key=lambda x: x['PartNumber'].lower(),
                                         reverse=(sort_order == 'DESC'))
            elif sort_by == 'description':
                samples_for_template.sort(key=lambda x: x['Description'].lower(),
                                         reverse=(sort_order == 'DESC'))
            elif sort_by == 'registered_date':
                samples_for_template.sort(key=lambda x: x['Registered'],
                                         reverse=(sort_order == 'DESC'))
            # Keep backward compatibility with reception_date sorting
            elif sort_by == 'reception_date':
                samples_for_template.sort(key=lambda x: x['Registered'],
                                         reverse=(sort_order == 'DESC'))
            elif sort_by == 'amount':
                # Extract the number from "X pcs"
                samples_for_template.sort(key=lambda x: float(x['Amount'].split()[0]),
                                         reverse=(sort_order == 'DESC'))
            elif sort_by == 'location':
                samples_for_template.sort(key=lambda x: x['Location'].lower(),
                                         reverse=(sort_order == 'DESC'))
            elif sort_by == 'status':
                samples_for_template.sort(key=lambda x: x['Status'].lower(),
                                         reverse=(sort_order == 'DESC'))
            
            cursor.close()
            
            return render_template('sections/storage.html',
                                 samples=samples_for_template,
                                 locations=locations,
                                 statuses=statuses,
                                 current_search=search,
                                 current_sort_by=sort_by,
                                 current_sort_order=sort_order,
                                 filter_criteria=filter_criteria)
            
            # Get dropdown options
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT LocationID, LocationName FROM StorageLocation ORDER BY LocationName")
            locations = [dict(LocationID=row[0], LocationName=row[1]) for row in cursor.fetchall()]
            
            cursor.execute("SELECT DISTINCT Status FROM Sample")
            statuses = [row[0] for row in cursor.fetchall()]
            cursor.close()
            
            # Get filter parameters
            filter_criteria = {}
            search = request.args.get('search', '')
            location = request.args.get('location', '')
            status = request.args.get('status', '')
            date_from = request.args.get('date_from', '')
            date_to = request.args.get('date_to', '')
            
            # Tracking which filters are active
            if search:
                filter_criteria['search'] = search
            if location:
                filter_criteria['location'] = location
            if status:
                filter_criteria['status'] = status
            if date_from:
                filter_criteria['date_from'] = date_from
            if date_to:
                filter_criteria['date_to'] = date_to
            
            # Get sort parameters
            sort_by = request.args.get('sort_by', 'sample_id')
            sort_order = request.args.get('sort_order', 'DESC')
            
            # Apply search filter
            if search:
                filtered_samples = []
                for sample in samples_for_template:
                    if (search.lower() in sample['Description'].lower() or
                        search.lower() in sample['PartNumber'].lower() or
                        search.lower() in sample['Location'].lower()):
                        filtered_samples.append(sample)
                samples_for_template = filtered_samples
                
            # Apply location filter
            if location:
                filtered_samples = []
                for sample in samples_for_template:
                    for loc in locations:
                        if loc['LocationID'] == int(location) and loc['LocationName'] == sample['Location']:
                            filtered_samples.append(sample)
                samples_for_template = filtered_samples
                
            # Apply status filter
            if status:
                filtered_samples = []
                for sample in samples_for_template:
                    if sample['Status'] == status:
                        filtered_samples.append(sample)
                samples_for_template = filtered_samples
            
            # Apply date range filter
            if date_from or date_to:
                filtered_samples = []
                for sample in samples_for_template:
                    # Get registered date (first 10 chars for date only)
                    sample_date = sample.get('Registered', '')[:10] if sample.get('Registered') else ''
                    
                    if date_from and date_to:
                        if date_from <= sample_date <= date_to:
                            filtered_samples.append(sample)
                    elif date_from:
                        if sample_date >= date_from:
                            filtered_samples.append(sample)
                    elif date_to:
                        if sample_date <= date_to:
                            filtered_samples.append(sample)
                            
                samples_for_template = filtered_samples
            
            # Apply sorting
            if sort_by == 'sample_id':
                samples_for_template.sort(key=lambda x: int(x['ID'].replace('SMP-', '')), 
                                         reverse=(sort_order == 'DESC'))
            elif sort_by == 'part_number':
                samples_for_template.sort(key=lambda x: x['PartNumber'].lower(),
                                         reverse=(sort_order == 'DESC'))
            elif sort_by == 'description':
                samples_for_template.sort(key=lambda x: x['Description'].lower(),
                                         reverse=(sort_order == 'DESC'))
            elif sort_by == 'registered_date':
                samples_for_template.sort(key=lambda x: x['Registered'],
                                         reverse=(sort_order == 'DESC'))
            # Keep backward compatibility with reception_date sorting
            elif sort_by == 'reception_date':
                samples_for_template.sort(key=lambda x: x['Registered'],
                                         reverse=(sort_order == 'DESC'))
            elif sort_by == 'amount':
                # Extract the number from "X pcs"
                samples_for_template.sort(key=lambda x: float(x['Amount'].split()[0]),
                                         reverse=(sort_order == 'DESC'))
            elif sort_by == 'location':
                samples_for_template.sort(key=lambda x: x['Location'].lower(),
                                         reverse=(sort_order == 'DESC'))
            elif sort_by == 'status':
                samples_for_template.sort(key=lambda x: x['Status'].lower(),
                                         reverse=(sort_order == 'DESC'))
                
            return render_template('sections/storage.html',
                                 samples=samples_for_template,
                                 locations=locations,
                                 statuses=statuses,
                                 current_search=search,
                                 current_sort_by=sort_by,
                                 current_sort_order=sort_order,
                                 filter_criteria=filter_criteria)
        except Exception as e:
            print(f"Error loading storage: {e}")
            import traceback
            traceback.print_exc()
            return render_template('sections/storage.html', error=f"Error loading storage: {e}")
    
    @blueprint.route('/api/samples', methods=['POST'])
    def create_sample():
        try:
            data = request.json
            
            # Validate input
            validation_result = validate_sample_data(data)
            if not validation_result.get('valid', False):
                return jsonify({
                    'success': False, 
                    'error': validation_result.get('error'),
                    'field': validation_result.get('field')
                }), 400
            
            # Get current user
            current_user = get_current_user()
            user_id = current_user['UserID']
            
            # Create the sample via service
            result = sample_service.create_sample(data, user_id)
            
            return jsonify(result)
        except Exception as e:
            print(f"API error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @blueprint.route('/api/samples/<int:sample_id>', methods=['DELETE'])
    def delete_sample(sample_id):
        try:
            # Get current user
            current_user = get_current_user()
            user_id = current_user['UserID']
            
            # First remove any ContainerSample links
            cursor = mysql.connection.cursor()
            
            # Get SampleStorage records for this sample
            cursor.execute("SELECT StorageID FROM SampleStorage WHERE SampleID = %s", (sample_id,))
            storage_ids = [row[0] for row in cursor.fetchall()]
            
            if storage_ids:
                # Remove container-sample links
                for storage_id in storage_ids:
                    cursor.execute("DELETE FROM ContainerSample WHERE SampleStorageID = %s", (storage_id,))
            
            # Delete history records for this sample first
            cursor.execute("DELETE FROM History WHERE SampleID = %s", (sample_id,))
            
            # Delete from TestSample
            cursor.execute("DELETE FROM TestSample WHERE SampleID = %s", (sample_id,))
            
            # Delete from SampleStorage
            cursor.execute("DELETE FROM SampleStorage WHERE SampleID = %s", (sample_id,))
            
            # Delete from SampleSerialNumber
            cursor.execute("DELETE FROM SampleSerialNumber WHERE SampleID = %s", (sample_id,))
            
            # Delete from Sample
            cursor.execute("DELETE FROM Sample WHERE SampleID = %s", (sample_id,))
            
            # Log the action
            cursor.execute("""
                INSERT INTO History (
                    Timestamp, 
                    ActionType, 
                    UserID, 
                    Notes
                )
                VALUES (NOW(), %s, %s, %s)
            """, (
                'Sample deleted',
                user_id,
                f"Sample {sample_id} deleted"
            ))
            
            mysql.connection.commit()
            cursor.close()
            
            return jsonify({
                'success': True,
                'sample_id': sample_id
            })
        except Exception as e:
            print(f"API error deleting sample: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
            
    @blueprint.route('/api/activeSamples')
    def get_active_samples():
        try:
            cursor = mysql.connection.cursor()
            
            # Get active samples with their storage location and remaining amount
            # Modified query to use LEFT JOIN and handle serial numbers for unique samples
            cursor.execute("""
                SELECT 
                    s.SampleID, 
                    s.Description, 
                    s.Barcode,
                    IFNULL(s.PartNumber, '') as PartNumber,
                    ss.AmountRemaining,
                    IFNULL(sl.LocationName, 'Unknown') as LocationName,
                    IFNULL(u.Name, 'Unknown') as OwnerName,
                    CASE
                        WHEN un.UnitName IS NULL THEN 'pcs'
                        WHEN LOWER(un.UnitName) = 'stk' THEN 'pcs'
                        ELSE un.UnitName
                    END as Unit,
                    IF(s.IsUnique=1, 1, 0) as IsUnique
                FROM Sample s
                LEFT JOIN SampleStorage ss ON s.SampleID = ss.SampleID
                LEFT JOIN StorageLocation sl ON ss.LocationID = sl.LocationID
                LEFT JOIN User u ON s.OwnerID = u.UserID
                LEFT JOIN Unit un ON s.UnitID = un.UnitID
                WHERE s.Status = 'In Storage'
                AND (ss.AmountRemaining > 0 OR ss.AmountRemaining IS NULL)
                ORDER BY s.SampleID DESC
                LIMIT 100
            """)
            
            columns = [col[0] for col in cursor.description]
            samples = []
            
            for row in cursor.fetchall():
                sample_dict = dict(zip(columns, row))
                
                # Format sample ID for display
                sample_dict['SampleIDFormatted'] = f"SMP-{sample_dict['SampleID']}"
                
                # If AmountRemaining is NULL, set it to 1 as a fallback
                if sample_dict['AmountRemaining'] is None:
                    sample_dict['AmountRemaining'] = 1
                
                # Ensure unit is always available
                if not sample_dict.get('Unit'):
                    sample_dict['Unit'] = 'pcs'
                
                # For unique samples, get serial numbers
                if sample_dict.get('IsUnique') == 1:
                    # Get serial numbers for unique samples
                    serial_query = """
                        SELECT SerialNumber 
                        FROM SampleSerialNumber 
                        WHERE SampleID = %s AND Status = 'Active'
                    """
                    cursor.execute(serial_query, (sample_dict['SampleID'],))
                    serials = [row[0] for row in cursor.fetchall()]
                    sample_dict['SerialNumbers'] = serials
                    
                    # For unique samples, amount is the number of active serial numbers
                    sample_dict['AmountRemaining'] = len(serials) if serials else 1
                
                samples.append(sample_dict)
                
            cursor.close()
            
            return jsonify({
                'success': True,
                'samples': samples
            })
        except Exception as e:
            print(f"API error getting active samples: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'samples': [],
                'error': str(e)
            }), 500
    
    @blueprint.route('/api/recentDisposals')
    def get_recent_disposals():
        try:
            cursor = mysql.connection.cursor()
            
            # Get recent disposal history
            cursor.execute("""
                SELECT 
                    h.LogID,
                    DATE_FORMAT(h.Timestamp, '%d-%m-%Y %H:%i') as DisposalDate,
                    CONCAT('SMP-', h.SampleID) as SampleID,
                    SUBSTRING_INDEX(h.Notes, ':', 1) as AmountDisposed,
                    u.Name as DisposedBy
                FROM History h
                JOIN User u ON h.UserID = u.UserID
                WHERE h.ActionType = 'Disposed'
                ORDER BY h.Timestamp DESC
                LIMIT 10
            """)
            
            columns = [col[0] for col in cursor.description]
            disposals = []
            
            for row in cursor.fetchall():
                disposal_dict = dict(zip(columns, row))
                
                # Clean up amount disposed - extract just the number if possible
                amount_str = disposal_dict.get('AmountDisposed', '')
                if 'Amount' in amount_str:
                    try:
                        # Try to extract the number from format like "Amount: 5"
                        import re
                        amount_match = re.search(r'Amount:\s*(\d+)', amount_str)
                        if amount_match:
                            disposal_dict['AmountDisposed'] = amount_match.group(1)
                    except:
                        # Keep original if parsing fails
                        pass
                        
                disposals.append(disposal_dict)
                
            cursor.close()
            
            return jsonify({
                'success': True,
                'disposals': disposals
            })
        except Exception as e:
            print(f"API error getting recent disposals: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'disposals': [],
                'error': str(e)
            }), 500
    
    @blueprint.route('/api/search', methods=['GET'])
    def global_search():
        """
        Global search endpoint for the header search bar
        Searches across samples, locations, tests etc.
        """
        try:
            search_term = request.args.get('q', '').strip()
            
            if not search_term or len(search_term) < 2:
                return jsonify({
                    'success': False,
                    'error': 'Search term must be at least 2 characters',
                    'results': []
                })
            
            # Get sample-related results
            cursor = mysql.connection.cursor()
            
            # Search across multiple tables using LIKE for better matching
            query = """
                SELECT 
                    'Sample' as result_type,
                    CONCAT('SMP-', s.SampleID) as id,
                    s.Description as title,
                    IFNULL(s.PartNumber, 'No part number') as subtitle,
                    s.Status as status,
                    CONCAT('/storage?search=', %s) as url
                FROM Sample s
                WHERE 
                    s.Description LIKE %s OR
                    s.PartNumber LIKE %s OR
                    s.Barcode LIKE %s
                LIMIT 10
                
                UNION
                
                SELECT 
                    'Location' as result_type,
                    CONCAT('LOC-', sl.LocationID) as id,
                    sl.LocationName as title,
                    l.LabName as subtitle,
                    'Active' as status,
                    CONCAT('/storage?location=', CAST(sl.LocationID as CHAR)) as url
                FROM StorageLocation sl
                JOIN Lab l ON sl.LabID = l.LabID
                WHERE sl.LocationName LIKE %s
                LIMIT 5
                
                UNION
                
                SELECT 
                    'Test' as result_type,
                    CONCAT('TST-', t.TestID) as id,
                    CONCAT('Test #', t.TestID) as title,
                    u.Name as subtitle,
                    IF(EXISTS(SELECT 1 FROM History h WHERE h.TestID = t.TestID AND h.ActionType = 'Test completed'), 'Completed', 'Active') as status,
                    '/testing' as url
                FROM Test t
                JOIN User u ON t.UserID = u.UserID
                WHERE t.TestID LIKE %s
                LIMIT 5
            """
            
            # Prepare search parameters
            search_param = f"%{search_term}%"
            params = [
                search_term,  # URL param
                search_param, search_param, search_param,  # Sample searches
                search_param,  # Location search
                search_param   # Test search
            ]
            
            cursor.execute(query, params)
            
            # Format results
            columns = [col[0] for col in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                result_dict = dict(zip(columns, row))
                results.append(result_dict)
                
            cursor.close()
            
            return jsonify({
                'success': True,
                'query': search_term,
                'results': results
            })
        except Exception as e:
            print(f"API error in global search: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e),
                'results': []
            }), 500
    
    @blueprint.route('/api/createDisposal', methods=['POST'])
    def create_disposal():
        try:
            data = request.json
            
            # Validate required fields
            if not data.get('sampleId'):
                return jsonify({'success': False, 'error': 'Sample ID is required'}), 400
                
            if not data.get('amount') or int(data.get('amount', 0)) <= 0:
                return jsonify({'success': False, 'error': 'Valid amount is required'}), 400
                
            # Get user ID
            user_id = data.get('userId')
            if not user_id:
                # Try to get current user
                current_user = get_current_user()
                user_id = current_user['UserID']
                
            if not user_id:
                return jsonify({'success': False, 'error': 'User ID is required'}), 400
                
            # Create transaction
            cursor = mysql.connection.cursor()
            
            try:
                # Begin transaction
                cursor.execute("START TRANSACTION")
                
                # Get current amount from storage
                cursor.execute("""
                    SELECT StorageID, AmountRemaining 
                    FROM SampleStorage 
                    WHERE SampleID = %s 
                    AND AmountRemaining > 0
                """, (data['sampleId'],))
                
                storage_result = cursor.fetchone()
                
                if not storage_result:
                    cursor.execute("ROLLBACK")
                    return jsonify({
                        'success': False,
                        'error': 'No available storage for this sample'
                    }), 400
                    
                storage_id = storage_result[0]
                amount_remaining = storage_result[1]
                disposal_amount = int(data['amount'])
                
                if disposal_amount > amount_remaining:
                    cursor.execute("ROLLBACK")
                    return jsonify({
                        'success': False,
                        'error': f'Requested amount ({disposal_amount}) exceeds available amount ({amount_remaining})'
                    }), 400
                    
                # Update storage amount
                new_amount = amount_remaining - disposal_amount
                cursor.execute("""
                    UPDATE SampleStorage 
                    SET AmountRemaining = %s 
                    WHERE StorageID = %s
                """, (new_amount, storage_id))
                
                # Update container sample links if the sample is in any containers
                cursor.execute("""
                    SELECT ContainerSampleID, ContainerID, Amount
                    FROM ContainerSample 
                    WHERE SampleStorageID = %s
                """, (storage_id,))
                
                container_samples = cursor.fetchall()
                
                for container_sample in container_samples:
                    container_sample_id = container_sample[0]
                    container_id = container_sample[1]
                    container_amount = container_sample[2]
                    
                    # If we're disposing all or more than what's in the container, delete the link
                    if disposal_amount >= container_amount:
                        cursor.execute("""
                            DELETE FROM ContainerSample
                            WHERE ContainerSampleID = %s
                        """, (container_sample_id,))
                        
                        # Log container update
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
                            'Container updated',
                            user_id,
                            data['sampleId'],
                            f"Sample {data['sampleId']} removed from container {container_id} due to disposal"
                        ))
                    else:
                        # Otherwise, reduce the amount in the container
                        new_container_amount = container_amount - disposal_amount
                        cursor.execute("""
                            UPDATE ContainerSample
                            SET Amount = %s
                            WHERE ContainerSampleID = %s
                        """, (new_container_amount, container_sample_id))
                        
                        # Log container update
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
                            'Container updated',
                            user_id,
                            data['sampleId'],
                            f"Sample {data['sampleId']} amount reduced to {new_container_amount} in container {container_id} due to disposal"
                        ))
                
                # If all amount is disposed, update sample status
                if new_amount == 0:
                    cursor.execute("""
                        UPDATE Sample 
                        SET Status = 'Disposed' 
                        WHERE SampleID = %s
                    """, (data['sampleId'],))
                    
                # Log the disposal in history
                notes = data.get('notes') or "Disposed through system"
                notes = f"Amount: {disposal_amount} - {notes}"
                
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
                    'Disposed',
                    user_id,
                    data['sampleId'],
                    notes
                ))
                
                # Commit transaction
                cursor.execute("COMMIT")
                
                return jsonify({
                    'success': True,
                    'message': f"Successfully disposed {disposal_amount} units of sample SMP-{data['sampleId']}"
                })
                
            except Exception as tx_error:
                # Rollback transaction on error
                cursor.execute("ROLLBACK")
                raise tx_error
                
            finally:
                cursor.close()
                
        except Exception as e:
            print(f"API error creating disposal: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
            
    @blueprint.route('/disposal')
    def disposal_page():
        """
        Render the dedicated disposal page
        """
        try:
            cursor = mysql.connection.cursor()
            
            # Get users for disposal selector
            cursor.execute("SELECT UserID, Name FROM User")
            users = [dict(UserID=row[0], Name=row[1]) for row in cursor.fetchall()]
            
            # Get recent disposals for display
            cursor.execute("""
                SELECT 
                    h.LogID,
                    DATE_FORMAT(h.Timestamp, '%d-%m-%Y %H:%i') as DisposalDate,
                    CONCAT('SMP-', h.SampleID) as SampleID,
                    h.Notes as DisposalNotes,
                    u.Name as DisposedBy
                FROM History h
                JOIN User u ON h.UserID = u.UserID
                WHERE h.ActionType = 'Disposed'
                ORDER BY h.Timestamp DESC
                LIMIT 10
            """)
            
            columns = [col[0] for col in cursor.description]
            recent_disposals = []
            
            for row in cursor.fetchall():
                disposal_dict = dict(zip(columns, row))
                
                # Extract amount from notes format: "Amount: X - notes"
                notes = disposal_dict.get('DisposalNotes', '')
                try:
                    # Use regex to extract the amount number
                    import re
                    amount_match = re.search(r'Amount:\s*(\d+)', notes)
                    if amount_match:
                        disposal_dict['AmountDisposed'] = amount_match.group(1)
                    else:
                        disposal_dict['AmountDisposed'] = 'Unknown'
                except:
                    # Keep a default in case regex fails
                    disposal_dict['AmountDisposed'] = 'Unknown'
                        
                recent_disposals.append(disposal_dict)
                
            cursor.close()
            
            # Get current user
            current_user = get_current_user()
            
            return render_template('sections/disposal.html', 
                                  users=users,
                                  recent_disposals=recent_disposals,
                                  current_user=current_user)
        except Exception as e:
            print(f"Error loading disposal page: {e}")
            import traceback
            traceback.print_exc()
            return render_template('sections/disposal.html', 
                                  error="Error loading disposal page")