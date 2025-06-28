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
            
            # First we try to fetch data from the database
            try:
                # Get all samples including disposed samples
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
                
                # If there are results, replace our hardcoded data
                if db_results and len(db_results) > 0:
                    # Replace our hardcoded data with database data
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
            # Get pagination parameters
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 50, type=int)
            search = request.args.get('search', '')
            
            # Limit per_page to prevent excessive data
            per_page = min(per_page, 100)
            offset = (page - 1) * per_page
            
            cursor = mysql.connection.cursor()
            
            # Base query conditions
            base_conditions = """
                WHERE s.Status = 'In Storage'
                AND (ss.AmountRemaining > 0 OR ss.AmountRemaining IS NULL)
            """
            
            # Add search conditions if provided
            search_conditions = ""
            search_params = []
            if search:
                search_conditions = """
                    AND (s.Description LIKE %s 
                         OR s.Barcode LIKE %s 
                         OR s.PartNumber LIKE %s
                         OR CONCAT('SMP-', s.SampleID) LIKE %s)
                """
                search_term = f"%{search}%"
                search_params = [search_term, search_term, search_term, search_term]
            
            # Get total count for pagination
            count_query = f"""
                SELECT COUNT(DISTINCT s.SampleID)
                FROM Sample s
                LEFT JOIN SampleStorage ss ON s.SampleID = ss.SampleID
                LEFT JOIN StorageLocation sl ON ss.LocationID = sl.LocationID
                LEFT JOIN User u ON s.OwnerID = u.UserID
                LEFT JOIN Unit un ON s.UnitID = un.UnitID
                {base_conditions}
                {search_conditions}
            """
            
            cursor.execute(count_query, search_params)
            total_count = cursor.fetchone()[0]
            
            # Get active samples with their storage location and remaining amount
            # Modified query to use LEFT JOIN and handle serial numbers for unique samples
            main_query = f"""
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
                {base_conditions}
                {search_conditions}
                ORDER BY s.SampleID DESC
                LIMIT %s OFFSET %s
            """
            
            cursor.execute(main_query, search_params + [per_page, offset])
            
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
            
            # Calculate pagination metadata
            total_pages = (total_count + per_page - 1) // per_page
            has_next = page < total_pages
            has_prev = page > 1
            
            return jsonify({
                'success': True,
                'samples': samples,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_count,
                    'total_pages': total_pages,
                    'has_next': has_next,
                    'has_prev': has_prev
                }
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
            
    @blueprint.route('/api/samples/<int:sample_id>', methods=['GET'])
    def get_sample_details(sample_id):
        """
        Get detailed information about a specific sample
        """
        try:
            # Use string to avoid %d bytes error
            sample_id_str = str(sample_id)
            
            cursor = mysql.connection.cursor()
            
            # Get sample basic info with complete reception data
            cursor.execute("""
                SELECT 
                    s.SampleID,
                    s.PartNumber,
                    s.Description,
                    s.Barcode,
                    s.Status,
                    CASE
                        WHEN un.UnitName IS NULL THEN 'pcs'
                        WHEN LOWER(un.UnitName) = 'stk' THEN 'pcs'
                        ELSE un.UnitName
                    END as Unit,
                    r.Notes as Comments,
                    DATE_FORMAT(r.ReceivedDate, '%d-%m-%Y %H:%i') as RegisteredDate,
                    owner.Name as RegisteredBy,
                    ss.AmountRemaining as Amount,
                    sl.LocationName as Location,
                    c.ContainerID,
                    r.TrackingNumber,
                    sp.SupplierName,
                    r.SourceType,
                    receiver.Name as ReceivedBy
                FROM Sample s
                LEFT JOIN Reception r ON s.ReceptionID = r.ReceptionID
                LEFT JOIN User owner ON s.OwnerID = owner.UserID
                LEFT JOIN User receiver ON r.UserID = receiver.UserID
                LEFT JOIN SampleStorage ss ON s.SampleID = ss.SampleID
                LEFT JOIN StorageLocation sl ON ss.LocationID = sl.LocationID
                LEFT JOIN ContainerSample cs ON ss.StorageID = cs.SampleStorageID
                LEFT JOIN Container c ON cs.ContainerID = c.ContainerID
                LEFT JOIN Unit un ON s.UnitID = un.UnitID
                LEFT JOIN Supplier sp ON r.SupplierID = sp.SupplierID
                WHERE s.SampleID = """ + sample_id_str)
            
            sample_result = cursor.fetchone()
            
            if not sample_result:
                return jsonify({
                    'success': False,
                    'error': f'Sample with ID {sample_id} not found'
                }), 404
                
            # Get column names
            columns = [col[0] for col in cursor.description]
            sample = dict(zip(columns, sample_result))
            
            # Convert all numeric and boolean values to appropriate types
            # Ensure SampleID is a string
            if 'SampleID' in sample and sample['SampleID'] is not None:
                sample['SampleID'] = str(sample['SampleID'])
                
            # Ensure Amount is a number
            if 'Amount' in sample and sample['Amount'] is not None:
                try:
                    sample['Amount'] = float(sample['Amount'])
                except (ValueError, TypeError):
                    # If conversion fails, use a default value
                    sample['Amount'] = 0
                    
            # Ensure ContainerID is converted if present
            if 'ContainerID' in sample and sample['ContainerID'] is not None:
                try:
                    sample['ContainerID'] = int(sample['ContainerID'])
                except (ValueError, TypeError):
                    sample['ContainerID'] = None
                sample['Amount'] = float(sample['Amount'])
            
            # Sample properties are not available in this database
            properties = []
            
            # Get sample history
            cursor.execute("""
                SELECT 
                    h.LogID,
                    DATE_FORMAT(h.Timestamp, '%d-%m-%Y %H:%i') as Timestamp,
                    h.ActionType,
                    u.Name as UserName,
                    h.Notes
                FROM History h
                LEFT JOIN User u ON h.UserID = u.UserID
                WHERE h.SampleID = """ + sample_id_str + """
                ORDER BY h.Timestamp DESC
            """)
            
            history_cols = [col[0] for col in cursor.description]
            history = []
            
            # Process history records with properly formatted values
            for row in cursor.fetchall():
                history_dict = dict(zip(history_cols, row))
                
                # Ensure LogID is an integer
                if 'LogID' in history_dict and history_dict['LogID'] is not None:
                    try:
                        history_dict['LogID'] = int(history_dict['LogID'])
                    except (ValueError, TypeError):
                        pass
                        
                # Ensure timestamp is a string
                if 'Timestamp' in history_dict and history_dict['Timestamp'] is not None:
                    history_dict['Timestamp'] = str(history_dict['Timestamp'])
                    
                history.append(history_dict)
            
            cursor.close()
            
            return jsonify({
                'success': True,
                'sample': sample,
                'properties': properties,
                'history': history
            })
        except Exception as e:
            print(f"API error getting sample details: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @blueprint.route('/api/samples/<int:sample_id>/move-location', methods=['POST'])
    def move_sample_to_location(sample_id):
        """
        Move a sample to a direct storage location 
        Used by the Move Sample functionality
        """
        try:
            data = request.json
            location_id = data.get('locationId')
            # Optional move amount - default to all if not specified
            move_amount = int(data.get('amount', 0))
            
            if not location_id:
                return jsonify({
                    'success': False,
                    'error': 'Location ID is required'
                }), 400
                
            # Get current user
            current_user = get_current_user()
            user_id = current_user['UserID']
            
            cursor = mysql.connection.cursor()
            
            try:
                # Start transaction
                cursor.execute("START TRANSACTION")
                
                # Check if sample exists and get its details
                cursor.execute("""
                    SELECT 
                        s.SampleID, 
                        s.Status, 
                        s.Description,
                        s.PartNumber,
                        s.Barcode,
                        s.UnitID,
                        s.ReceptionID,
                        s.OwnerID,
                        s.Amount,
                        s.Type,
                        s.IsUnique
                    FROM Sample s
                    WHERE s.SampleID = """ + str(sample_id))
                sample_result = cursor.fetchone()
                
                if not sample_result:
                    cursor.execute("ROLLBACK")
                    return jsonify({
                        'success': False,
                        'error': f'Sample with ID {sample_id} not found'
                    }), 404
                    
                if sample_result[1] == 'Disposed':
                    cursor.execute("ROLLBACK")
                    return jsonify({
                        'success': False,
                        'error': 'Cannot move a disposed sample'
                    }), 400
                
                # Sample data
                sample_description = sample_result[2]
                sample_part_number = sample_result[3]
                sample_barcode = sample_result[4]
                sample_unit_id = sample_result[5]
                sample_reception_id = sample_result[6]
                sample_owner_id = sample_result[7]
                sample_amount = sample_result[8] if sample_result[8] is not None else 0
                sample_type = sample_result[9] or 'multiple'
                sample_is_unique = sample_result[10] or 0
                
                # Get sample storage information
                cursor.execute("""
                    SELECT 
                        ss.StorageID,
                        ss.LocationID,
                        ss.AmountRemaining,
                        IFNULL(sl.LocationName, 'Unknown') as OldLocationName
                    FROM SampleStorage ss
                    LEFT JOIN StorageLocation sl ON ss.LocationID = sl.LocationID
                    WHERE ss.SampleID = """ + str(sample_id))
                storage_result = cursor.fetchone()
                
                if not storage_result:
                    # No existing storage record - create one
                    cursor.execute("""
                        INSERT INTO SampleStorage (
                            SampleID,
                            LocationID,
                            AmountRemaining
                        ) VALUES (%s, %s, %s)
                    """, (
                        sample_id,
                        location_id,
                        1  # Default amount if no existing record
                    ))
                    
                    storage_id = cursor.lastrowid
                    old_location_name = 'None'
                    total_amount = 1
                    
                    # Set sample status to 'In Storage'
                    cursor.execute("""
                        UPDATE Sample 
                        SET Status = 'In Storage' 
                        WHERE SampleID = """ + str(sample_id))
                else:
                    storage_id = storage_result[0]
                    old_location_id = storage_result[1]
                    total_amount = int(storage_result[2])
                    old_location_name = storage_result[3]
                    
                    # If move_amount not specified, move all
                    if move_amount <= 0 or move_amount > total_amount:
                        move_amount = total_amount
                    
                    # If we're moving ALL samples, just update the location
                    if move_amount == total_amount:
                        # Remove from any containers
                        cursor.execute("""
                            DELETE FROM ContainerSample 
                            WHERE SampleStorageID = %s
                        """, (storage_id,))
                        
                        # Update storage record with new location
                        cursor.execute("""
                            UPDATE SampleStorage 
                            SET LocationID = %s 
                            WHERE StorageID = %s
                        """, (location_id, storage_id))
                    else:
                        # We're moving SOME of the samples - create a new sample record
                        
                        # First, reduce the amount in both sample and samplestorage tables
                        new_amount = total_amount - move_amount
                        
                        # Update SampleStorage.AmountRemaining
                        cursor.execute("""
                            UPDATE SampleStorage 
                            SET AmountRemaining = %s 
                            WHERE StorageID = %s
                        """, (new_amount, storage_id))
                        
                        # Also update Sample.Amount for consistency
                        cursor.execute("""
                            UPDATE Sample 
                            SET Amount = %s 
                            WHERE SampleID = %s
                        """, (new_amount, sample_id))
                        
                        # Create timestamp for unique barcode
                        import datetime
                        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                        new_barcode = f"{sample_barcode}-{timestamp}" if sample_barcode else f"MOVED-{sample_id}-{timestamp}"
                        
                        # Now create a new Sample record for the moved portion
                        cursor.execute("""
                            INSERT INTO Sample (
                                PartNumber,
                                Description,
                                Barcode,
                                Status,
                                Amount,
                                UnitID,
                                OwnerID,
                                ReceptionID,
                                Type,
                                IsUnique
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            sample_part_number,
                            sample_description,
                            new_barcode,  # Create a unique barcode with timestamp
                            'In Storage',
                            move_amount,  # Set the correct amount for the new sample
                            sample_unit_id,
                            sample_owner_id,
                            sample_reception_id,
                            sample_type,
                            sample_is_unique
                        ))
                        
                        new_sample_id = cursor.lastrowid
                        
                        # Create storage record for the new sample
                        cursor.execute("""
                            INSERT INTO SampleStorage (
                                SampleID,
                                LocationID,
                                AmountRemaining
                            ) VALUES (%s, %s, %s)
                        """, (
                            new_sample_id,
                            location_id,
                            move_amount
                        ))
                        
                        # Update sample_id for response
                        moved_sample_id = new_sample_id
                
                # Get new location name for history
                cursor.execute("""
                    SELECT LocationName 
                    FROM StorageLocation 
                    WHERE LocationID = """ + str(location_id))
                new_location_result = cursor.fetchone()
                new_location_name = new_location_result[0] if new_location_result else 'Unknown'
                
                # Log the movement in history
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
                    'Sample moved',
                    user_id,
                    sample_id,
                    f"Sample moved ({move_amount} units) from location {old_location_name} to {new_location_name}"
                ))
                
                # Commit transaction
                cursor.execute("COMMIT")
                
                return jsonify({
                    'success': True,
                    'message': f"Sample SMP-{sample_id} moved to {new_location_name}",
                    'sample_id': sample_id,
                    'moved_amount': move_amount,
                    'new_location': new_location_name
                })
                
            except Exception as tx_error:
                # Rollback on error
                cursor.execute("ROLLBACK")
                raise tx_error
                
            finally:
                cursor.close()
                
        except Exception as e:
            print(f"API error moving sample to location: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
            
    @blueprint.route('/api/samples/<int:sample_id>/remove-from-container', methods=['POST'])
    def remove_sample_from_container(sample_id):
        """
        Remove a sample from its current container
        Used by the Move Sample functionality
        """
        try:
            # Get current user
            current_user = get_current_user()
            user_id = current_user['UserID']
            
            cursor = mysql.connection.cursor()
            
            try:
                # Start transaction
                cursor.execute("START TRANSACTION")
                
                # Check if sample exists
                cursor.execute("SELECT SampleID, Status FROM Sample WHERE SampleID = " + str(sample_id))
                sample_result = cursor.fetchone()
                
                if not sample_result:
                    cursor.execute("ROLLBACK")
                    return jsonify({
                        'success': False,
                        'error': f'Sample with ID {sample_id} not found'
                    }), 404
                    
                if sample_result[1] == 'Disposed':
                    cursor.execute("ROLLBACK")
                    return jsonify({
                        'success': False,
                        'error': 'Cannot modify a disposed sample'
                    }), 400
                
                # Check if sample is in a container
                cursor.execute("""
                    SELECT 
                        cs.ContainerSampleID,
                        cs.ContainerID,
                        c.ContainerName,
                        cs.Amount
                    FROM SampleStorage ss
                    JOIN ContainerSample cs ON ss.StorageID = cs.SampleStorageID
                    JOIN Container c ON cs.ContainerID = c.ContainerID
                    WHERE ss.SampleID = """ + str(sample_id))
                container_results = cursor.fetchall()
                
                if not container_results:
                    cursor.execute("ROLLBACK")
                    return jsonify({
                        'success': False,
                        'error': 'Sample is not currently in any container'
                    }), 400
                
                # Remove from all containers
                container_names = []
                for container_result in container_results:
                    container_sample_id = container_result[0]
                    container_id = container_result[1]
                    container_name = container_result[2] or f"Container {container_id}"
                    
                    cursor.execute("""
                        DELETE FROM ContainerSample 
                        WHERE ContainerSampleID = %s
                    """, (container_sample_id,))
                    
                    container_names.append(container_name)
                
                # Log the removal in history
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
                    sample_id,
                    f"Sample removed from containers: {', '.join(container_names)}"
                ))
                
                # Commit transaction
                cursor.execute("COMMIT")
                
                return jsonify({
                    'success': True,
                    'message': f"Sample SMP-{sample_id} removed from containers",
                    'sample_id': sample_id,
                    'containers': container_names
                })
                
            except Exception as tx_error:
                # Rollback on error
                cursor.execute("ROLLBACK")
                raise tx_error
                
            finally:
                cursor.close()
                
        except Exception as e:
            print(f"API error removing sample from container: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
            
    @blueprint.route('/api/suppliers', methods=['POST'])
    def create_supplier():
        """
        API endpoint to create a new supplier
        """
        try:
            data = request.json
            
            if not data or not data.get('name'):
                return jsonify({
                    'success': False,
                    'error': 'Supplier name is required'
                }), 400
            
            supplier_name = data.get('name').strip()
            supplier_notes = data.get('notes', '').strip()
            
            # Get current user for logging
            current_user = get_current_user()
            user_id = current_user['UserID']
            
            cursor = mysql.connection.cursor()
            
            # Check if supplier already exists
            cursor.execute("SELECT SupplierID FROM Supplier WHERE SupplierName = %s", (supplier_name,))
            existing = cursor.fetchone()
            
            if existing:
                return jsonify({
                    'success': False,
                    'error': 'A supplier with this name already exists',
                    'supplier_id': existing[0]
                }), 400
            
            # Check if Notes column exists in Supplier table
            cursor.execute("SHOW COLUMNS FROM Supplier LIKE 'Notes'")
            notes_column_exists = cursor.fetchone() is not None
            
            # Insert new supplier
            if notes_column_exists and supplier_notes:
                cursor.execute("""
                    INSERT INTO Supplier (SupplierName, Notes)
                    VALUES (%s, %s)
                """, (supplier_name, supplier_notes))
            else:
                cursor.execute("""
                    INSERT INTO Supplier (SupplierName)
                    VALUES (%s)
                """, (supplier_name,))
            
            mysql.connection.commit()
            supplier_id = cursor.lastrowid
            
            # Log the operation
            cursor.execute("""
                INSERT INTO History (
                    Timestamp,
                    ActionType,
                    UserID,
                    Notes
                )
                VALUES (NOW(), %s, %s, %s)
            """, (
                'Supplier created',
                user_id,
                f"Created new supplier: {supplier_name}"
            ))
            
            mysql.connection.commit()
            cursor.close()
            
            return jsonify({
                'success': True,
                'supplier_id': supplier_id,
                'name': supplier_name
            })
            
        except Exception as e:
            print(f"API error creating supplier: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @blueprint.route('/api/samples/recent')
    def get_recent_samples():
        """
        API endpoint to get recent sample registrations
        """
        try:
            cursor = mysql.connection.cursor()
            
            # Get the 20 most recent samples
            cursor.execute("""
                SELECT 
                    s.SampleID,
                    CONCAT('SMP-', s.SampleID) as SampleIDFormatted,
                    s.Description,
                    s.PartNumber,
                    s.UnitID,
                    CASE
                        WHEN u.UnitName IS NULL THEN 'pcs'
                        WHEN LOWER(u.UnitName) = 'stk' THEN 'pcs'
                        ELSE u.UnitName
                    END as UnitName,
                    s.OwnerID,
                    DATE_FORMAT(r.ReceivedDate, '%d-%m-%Y %H:%i') as RegisteredDate
                FROM Sample s
                JOIN Reception r ON s.ReceptionID = r.ReceptionID
                LEFT JOIN Unit u ON s.UnitID = u.UnitID
                ORDER BY s.SampleID DESC
                LIMIT 20
            """)
            
            columns = [col[0] for col in cursor.description]
            samples = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            cursor.close()
            
            return jsonify({
                'success': True,
                'samples': samples
            })
            
        except Exception as e:
            print(f"API error getting recent samples: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e),
                'samples': []
            }), 500
    
    @blueprint.route('/api/samples/last')
    def get_last_sample():
        """
        API endpoint to get the most recently registered sample
        """
        try:
            cursor = mysql.connection.cursor()
            
            # Get the most recent sample
            cursor.execute("""
                SELECT 
                    s.SampleID,
                    CONCAT('SMP-', s.SampleID) as SampleIDFormatted,
                    s.Description,
                    s.PartNumber,
                    s.UnitID,
                    CASE
                        WHEN u.UnitName IS NULL THEN 'pcs'
                        WHEN LOWER(u.UnitName) = 'stk' THEN 'pcs'
                        ELSE u.UnitName
                    END as UnitName,
                    s.OwnerID,
                    DATE_FORMAT(r.ReceivedDate, '%d-%m-%Y %H:%i') as RegisteredDate
                FROM Sample s
                JOIN Reception r ON s.ReceptionID = r.ReceptionID
                LEFT JOIN Unit u ON s.UnitID = u.UnitID
                ORDER BY s.SampleID DESC
                LIMIT 1
            """)
            
            result = cursor.fetchone()
            
            if not result:
                return jsonify({
                    'success': False,
                    'error': 'No samples found',
                    'sample': None
                })
            
            columns = [col[0] for col in cursor.description]
            sample = dict(zip(columns, result))
            
            cursor.close()
            
            return jsonify({
                'success': True,
                'sample': sample
            })
            
        except Exception as e:
            print(f"API error getting last sample: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e),
                'sample': None
            }), 500
    
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