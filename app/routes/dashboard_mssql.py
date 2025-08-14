from flask import Blueprint, render_template, jsonify, request
from app.utils.mssql_db import mssql_db

dashboard_mssql_bp = Blueprint('dashboard_mssql', __name__)

def _get_storage_locations_mssql():
    """Retrieves storage locations from the database - SQL Server version"""
    query = """
        SELECT 
            sl.LocationID,
            sl.LocationName,
            sl.Description,
            COUNT(ss.StorageID) as count,
            CASE WHEN COUNT(ss.StorageID) > 0 THEN 'occupied' ELSE 'available' END as status,
            ISNULL(l.LabName, 'Unknown') as LabName,
            sl.Rack,
            sl.Section,
            sl.Shelf
        FROM [storagelocation] sl
        LEFT JOIN [lab] l ON sl.LabID = l.LabID
        LEFT JOIN [samplestorage] ss ON sl.LocationID = ss.LocationID AND ss.AmountRemaining > 0
        GROUP BY sl.LocationID, sl.LocationName, sl.Description, l.LabName, sl.Rack, sl.Section, sl.Shelf
        ORDER BY 
            ISNULL(sl.Rack, 999),
            ISNULL(sl.Section, 999),
            ISNULL(sl.Shelf, 999)
    """
    
    try:
        results = mssql_db.execute_query(query, fetch_all=True)
        
        locations = []
        for row in results:
            location = {
                'LocationID': row[0],
                'LocationName': row[1],
                'Description': row[2],
                'count': row[3],
                'status': row[4],
                'LabName': row[5],
                'Rack': row[6],
                'Section': row[7],
                'Shelf': row[8]
            }
            
            # For locations where Rack, Section, Shelf are NULL, extract them from LocationName
            if location.get('Rack') is None or location.get('Section') is None or location.get('Shelf') is None:
                parts = location.get('LocationName', '').split('.')
                if len(parts) == 3:
                    location['Rack'] = int(parts[0]) if parts[0].isdigit() else None
                    location['Section'] = int(parts[1]) if parts[1].isdigit() else None
                    location['Shelf'] = int(parts[2]) if parts[2].isdigit() else None
            
            locations.append(location)
        
        return locations
    except Exception as e:
        print(f"Error getting storage locations: {e}")
        return []

@dashboard_mssql_bp.route('/')
@dashboard_mssql_bp.route('/dashboard')
def dashboard():
    try:
        # Get number of samples in storage
        sample_count = mssql_db.execute_query(
            "SELECT COUNT(*) FROM [sample] WHERE [Status] = 'In Storage'", 
            fetch_one=True
        )[0] or 0
        
        # Get samples expiring soon (within 14 days) - SQL Server version
        expiring_count = mssql_db.execute_query("""
            SELECT COUNT(*) FROM [sample] s
            WHERE (
                (s.ExpireDate <= CAST(GETDATE() AS DATE)) OR 
                (s.ExpireDate > CAST(GETDATE() AS DATE) AND s.ExpireDate <= DATEADD(DAY, 14, CAST(GETDATE() AS DATE)))
            )
            AND s.Status = 'In Storage'
        """, fetch_one=True)[0] or 0
        
        # Get new samples today
        new_today = mssql_db.execute_query("""
            SELECT COUNT(*) FROM [reception]
            WHERE CAST([ReceivedDate] AS DATE) = CAST(GETDATE() AS DATE)
        """, fetch_one=True)[0] or 0
        
        # Get number of active tests (In Progress or Created status)
        active_tests_count = mssql_db.execute_query("""
            SELECT COUNT(*) FROM [test] t
            WHERE t.[Status] IN ('In Progress', 'Created')
        """, fetch_one=True)[0] or 0
        
        # Get recent history
        history_results = mssql_db.execute_query("""
            SELECT TOP 5
                h.LogID, 
                h.ActionType, 
                h.Notes,
                ISNULL(s.Description, 'N/A') as SampleDesc,
                u.Name as UserName,
                FORMAT(h.Timestamp, 'dd-MM-yyyy HH:mm') as Timestamp
            FROM [history] h
            LEFT JOIN [sample] s ON h.SampleID = s.SampleID
            LEFT JOIN [user] u ON h.UserID = u.UserID
            ORDER BY h.Timestamp DESC
        """, fetch_all=True)
        
        history_items = []
        for row in history_results:
            history_items.append({
                "LogID": row[0],
                "ActionType": row[1],
                "Notes": row[2],
                "SampleDesc": row[3],
                "UserName": row[4],
                "Timestamp": row[5]
            })
        
        # Get storage locations using the helper function
        locations = _get_storage_locations_mssql()
        
        return render_template('sections/dashboard.html', 
                            sample_count=sample_count,
                            expiring_count=expiring_count,
                            new_today=new_today,
                            active_tests_count=active_tests_count,
                            history_items=history_items,
                            locations=locations)
    except Exception as e:
        import traceback
        error_message = f"Error: {str(e)}\n{traceback.format_exc()}"
        print(error_message)
        return render_template('sections/dashboard.html', 
                            error=error_message,
                            sample_count=0,
                            expiring_count=0,
                            new_today=0,
                            active_tests_count=0,
                            history_items=[],
                            locations=[])

@dashboard_mssql_bp.route('/api/storage-locations')
def api_storage_locations():
    try:
        locations = _get_storage_locations_mssql()
        
        # Force locations to show 0 count after clearing data
        for location in locations:
            # Ensure count is 0 or an actual count (not None)
            location['count'] = int(location.get('count', 0) or 0)
        
        return jsonify({
            'success': True,
            'locations': locations
        })
    except Exception as e:
        import traceback
        error_message = f"Error getting storage locations: {str(e)}\n{traceback.format_exc()}"
        print(error_message)
        return jsonify({
            'success': False,
            'error': error_message
        }), 500

@dashboard_mssql_bp.route('/history')
def history():
    try:
        history_results = mssql_db.execute_query("""
            SELECT TOP 100
                h.LogID,
                FORMAT(h.Timestamp, 'dd MMM yyyy HH:mm') as FormattedDate,
                h.ActionType,
                u.Name as UserName,
                CASE 
                    WHEN h.SampleID IS NOT NULL THEN CAST(h.SampleID AS NVARCHAR)
                    WHEN h.TestID IS NOT NULL THEN t.TestNo
                    ELSE 'N/A'
                END as ItemID,
                h.Notes,
                r.ReceptionID,
                s.Description as SampleDescription,
                s.PartNumber as SamplePartNumber,
                h.SampleID as RawSampleID
            FROM [history] h
            LEFT JOIN [user] u ON h.UserID = u.UserID
            LEFT JOIN [sample] s ON h.SampleID = s.SampleID
            LEFT JOIN [test] t ON h.TestID = t.TestID
            LEFT JOIN [reception] r ON s.ReceptionID = r.ReceptionID
            ORDER BY h.Timestamp DESC
        """, fetch_all=True)
        
        # Get distinct action types for filter dropdown
        action_types_results = mssql_db.execute_query(
            "SELECT DISTINCT ActionType FROM [history] ORDER BY ActionType", 
            fetch_all=True
        )
        action_types = [row[0] for row in action_types_results]
        
        history_items = []
        for item in history_results:
            # Format display text based on what's available
            item_id = item[4]
            action_type = item[2]
            sample_description = item[7] if len(item) > 7 else None
            sample_part_number = item[8] if len(item) > 8 else None
            raw_sample_id = item[9] if len(item) > 9 else None
            
            # Prioritize sample description for display
            display_text = None
            if sample_description and sample_description.strip():
                display_text = sample_description
            elif item_id and item_id != 'N/A':
                if str(item_id).startswith('T'):  # Test number
                    display_text = str(item_id)
                else:  # Sample ID
                    display_text = f"SMP-{item_id}"
            elif action_type and action_type.lower() in ['container created', 'container updated', 'container deleted']:
                display_text = None  # Will be handled in template
            else:
                display_text = 'N/A'
                
            history_items.append({
                "LogID": item[0],
                "Timestamp": str(item[1]) if item[1] else "",
                "ActionType": str(item[2]) if item[2] else "",
                "UserName": str(item[3]) if item[3] else "",
                "SampleDesc": str(display_text) if display_text else "",  # Now shows description preferentially
                "Notes": str(item[5]) if item[5] else "",
                "ReceptionID": item[6] if item[6] else None,
                "SampleDescription": str(sample_description) if sample_description else "",
                "SamplePartNumber": str(sample_part_number) if sample_part_number else "",
                "SampleID": f"SMP-{raw_sample_id}" if raw_sample_id else "",
                "RawSampleID": raw_sample_id
            })
        
        return render_template('sections/history.html', 
                             history_items=history_items,
                             action_types=action_types)
    except Exception as e:
        print("Error loading history:", str(e))
        return render_template('sections/history.html', 
                             error="Error loading history",
                             history_items=[],
                             action_types=[])

@dashboard_mssql_bp.route('/api/history', methods=['GET'])
def api_get_history():
    """API endpoint to get history records with pagination and filtering"""
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        action_type = request.args.get('action', '')
        user = request.args.get('user', '')
        date_from = request.args.get('dateFrom', '')
        date_to = request.args.get('dateTo', '')
        notes = request.args.get('notes', '')
        
        # Start building the query
        query = """
            SELECT 
                h.LogID,
                FORMAT(h.Timestamp, 'dd MMM yyyy HH:mm') as FormattedDate,
                h.ActionType,
                u.Name as UserName,
                CASE 
                    WHEN h.SampleID IS NOT NULL THEN CAST(h.SampleID AS NVARCHAR)
                    WHEN h.TestID IS NOT NULL THEN t.TestNo
                    ELSE 'N/A'
                END as ItemID,
                h.Notes,
                r.ReceptionID
            FROM [history] h
            LEFT JOIN [user] u ON h.UserID = u.UserID
            LEFT JOIN [sample] s ON h.SampleID = s.SampleID
            LEFT JOIN [test] t ON h.TestID = t.TestID
            LEFT JOIN [reception] r ON s.ReceptionID = r.ReceptionID
            WHERE 1=1
        """
        params = []
        
        # Add filters to the query
        if search:
            query += " AND (ISNULL(CAST(s.SampleID AS NVARCHAR), ISNULL(t.TestNo, '')) LIKE ? OR h.Notes LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        
        if action_type:
            query += " AND h.ActionType = ?"
            params.append(action_type)
        
        if user:
            query += " AND u.Name = ?"
            params.append(user)
        
        if date_from:
            query += " AND CAST(h.Timestamp AS DATE) >= ?"
            params.append(date_from)
        
        if date_to:
            query += " AND CAST(h.Timestamp AS DATE) <= ?"
            params.append(date_to)
        
        if notes:
            query += " AND h.Notes LIKE ?"
            params.append(f"%{notes}%")
        
        # Add ordering and pagination - SQL Server style
        query += " ORDER BY h.Timestamp DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
        params.append((page - 1) * per_page)
        params.append(per_page)
        
        # Execute the query
        history_data = mssql_db.execute_query(query, params, fetch_all=True)
        
        # Format the results
        history_items = []
        for item in history_data:
            # Format ItemID based on type
            item_id = item[4]
            if item_id and item_id != 'N/A':
                if str(item_id).startswith('T'):  # Test number
                    sample_desc = item_id
                else:  # Sample ID
                    sample_desc = f"SMP-{item_id}"
            else:
                sample_desc = 'N/A'
                
            history_items.append({
                "LogID": item[0],
                "Timestamp": item[1],
                "ActionType": item[2],
                "UserName": item[3],
                "SampleDesc": sample_desc,
                "Notes": item[5],
                "ReceptionID": item[6] if item[6] else None
            })
        
        return jsonify({
            'success': True,
            'history_items': history_items,
            'page': page,
            'per_page': per_page,
            'has_more': len(history_items) == per_page
        })
        
    except Exception as e:
        print(f"API error when fetching history: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dashboard_mssql_bp.route('/api/history/details/<int:log_id>', methods=['GET'])
def api_history_details(log_id):
    """API endpoint to get detailed information about a specific history record"""
    try:
        # Simple query - just get the basic history record first
        basic_query = """
            SELECT 
                h.LogID,
                h.Timestamp,
                h.ActionType,
                h.Notes,
                h.SampleID,
                h.TestID,
                h.UserID
            FROM [history] h
            WHERE h.LogID = ?
        """
        
        log_data = mssql_db.execute_query(basic_query, (log_id,), fetch_one=True)
        
        if not log_data:
            return jsonify({
                'success': False,
                'error': 'History record not found'
            }), 404
        
        # Get user name separately to avoid join issues
        user_name = 'Unknown User'
        if log_data[6]:  # UserID
            try:
                user_result = mssql_db.execute_query("SELECT [Name] FROM [user] WHERE [UserID] = ?", (log_data[6],), fetch_one=True)
                if user_result:
                    user_name = user_result[0]
            except:
                pass  # Keep default if query fails
        
        # Format timestamp
        formatted_timestamp = log_data[1].strftime('%d %b %Y %H:%M') if log_data[1] else 'Unknown time'
        
        # Format sample description
        sample_desc = 'N/A'
        if log_data[4]:  # SampleID
            sample_desc = f"SMP-{log_data[4]}"
        elif log_data[2] and 'container' in log_data[2].lower():
            sample_desc = 'Container Action'
        
        log_details = {
            "LogID": log_data[0],
            "Timestamp": formatted_timestamp,
            "ActionType": log_data[2] or 'Unknown Action',
            "UserName": user_name,
            "SampleDesc": sample_desc,
            "Notes": log_data[3] or 'No notes available',
            "SampleID": log_data[4],
            "TestID": log_data[5]
        }
        
        # Only show sample info for sample-related actions
        sample_info = None
        sample_history = []
        sample_related_actions = [
            'Received', 'Sample created', 'Sample registered', 'Sample moved', 'Sample assigned to task',
            'Disposed', 'Sample consumed', 'Sample partially consumed', 'Sample transferred',
            'Sample added to container', 'Sample removed from container'
        ]
        
        action_type = log_data[2] or ''
        is_sample_relevant = any(action in action_type for action in sample_related_actions) or log_data[4] is not None
        
        if is_sample_relevant and log_data[4]:
            try:
                sample_data = mssql_db.execute_query("SELECT [SampleID], [Description], [Status], [PartNumber] FROM [sample] WHERE [SampleID] = ?", (log_data[4],), fetch_one=True)
                if sample_data:
                    sample_info = {
                        "SampleID": sample_data[0],
                        "Description": sample_data[1] or 'No description',
                        "Status": sample_data[2] or 'Unknown',
                        "PartNumber": sample_data[3] or 'No part number'
                        # Removed Location as requested
                    }
                    
                    # Get basic sample history
                    try:
                        history_query = """
                            SELECT TOP 5
                                FORMAT(h.Timestamp, 'dd MMM yyyy HH:mm') as FormattedDate,
                                h.ActionType,
                                h.Notes
                            FROM [history] h
                            WHERE h.SampleID = ?
                            ORDER BY h.Timestamp DESC
                        """
                        history_results = mssql_db.execute_query(history_query, (log_data[4],), fetch_all=True)
                        for history_row in history_results:
                            sample_history.append({
                                "Timestamp": history_row[0],
                                "ActionType": history_row[1],
                                "UserName": "System",  # Simplified
                                "Notes": history_row[2] or 'No notes'
                            })
                    except:
                        pass  # Keep empty list if history query fails
            except:
                pass  # Keep None if query fails
        
        return jsonify({
            'success': True,
            'details': log_details,
            'sample_info': sample_info,
            'sample_history': sample_history
        })
        
    except Exception as e:
        print(f"API error when fetching history details: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Database error: {str(e)}'
        }), 500

@dashboard_mssql_bp.route('/api/history/export', methods=['GET'])
def api_export_history():
    """API endpoint to export history records to CSV based on filters"""
    try:
        # Get query parameters (same as in api_get_history)
        search = request.args.get('search', '')
        action_type = request.args.get('action', '')
        user = request.args.get('user', '')
        date_from = request.args.get('dateFrom', '')
        date_to = request.args.get('dateTo', '')
        notes = request.args.get('notes', '')
        
        # Start building the query
        query = """
            SELECT 
                h.LogID,
                FORMAT(h.Timestamp, 'yyyy-MM-dd HH:mm:ss') as FormattedDate,
                h.ActionType,
                u.Name as UserName,
                CASE 
                    WHEN h.SampleID IS NOT NULL THEN CAST(h.SampleID AS NVARCHAR)
                    WHEN h.TestID IS NOT NULL THEN t.TestNo
                    ELSE 'N/A'
                END as ItemID,
                ISNULL(s.Description, 'N/A') as SampleDescription,
                h.Notes,
                ISNULL(sl.LocationName, 'N/A') as Location
            FROM [history] h
            LEFT JOIN [user] u ON h.UserID = u.UserID
            LEFT JOIN [sample] s ON h.SampleID = s.SampleID
            LEFT JOIN [test] t ON h.TestID = t.TestID
            LEFT JOIN [samplestorage] ss ON s.SampleID = ss.SampleID AND ss.AmountRemaining > 0
            LEFT JOIN [storagelocation] sl ON ss.LocationID = sl.LocationID
            WHERE 1=1
        """
        params = []
        
        # Add filters to the query (same as in api_get_history)
        if search:
            query += " AND (ISNULL(CAST(s.SampleID AS NVARCHAR), ISNULL(t.TestNo, '')) LIKE ? OR h.Notes LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        
        if action_type:
            query += " AND h.ActionType = ?"
            params.append(action_type)
        
        if user:
            query += " AND u.Name = ?"
            params.append(user)
        
        if date_from:
            query += " AND CAST(h.Timestamp AS DATE) >= ?"
            params.append(date_from)
        
        if date_to:
            query += " AND CAST(h.Timestamp AS DATE) <= ?"
            params.append(date_to)
        
        if notes:
            query += " AND h.Notes LIKE ?"
            params.append(f"%{notes}%")
        
        # Add ordering but no limit for export
        query += " ORDER BY h.Timestamp DESC"
        
        # Execute the query
        history_data = mssql_db.execute_query(query, params, fetch_all=True)
        
        # Prepare CSV response
        import csv
        import io
        
        csv_file = io.StringIO()
        csv_writer = csv.writer(csv_file)
        
        # Write header
        csv_writer.writerow([
            'ID', 'Date & Time', 'Action Type', 'User', 
            'Sample ID', 'Sample Description', 'Notes', 'Location'
        ])
        
        # Write data
        for row in history_data:
            sample_id = f"SMP-{row[4]}" if row[4] and row[4] != 'N/A' else 'N/A'
            csv_writer.writerow([
                row[0],          # LogID
                row[1],          # Timestamp
                row[2],          # ActionType
                row[3],          # UserName
                sample_id,       # SampleDesc
                row[5],          # SampleDescription
                row[6],          # Notes
                row[7]           # Location
            ])
        
        # Create response
        from flask import Response
        from datetime import datetime
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        response = Response(
            csv_file.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=history_export_{timestamp}.csv'
            }
        )
        
        return response
        
    except Exception as e:
        print(f"API error when exporting history: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dashboard_mssql_bp.route('/api/storage/add-section', methods=['POST'])
def add_storage_section():
    try:
        data = request.json
        # Validate input
        if not data.get('rackNum') or not data.get('sectionNum'):
            return jsonify({'success': False, 'error': 'Rack and section number are required'}), 400
        
        # Get lab ID
        lab_result = mssql_db.execute_query("SELECT TOP 1 [LabID] FROM [lab]", fetch_one=True)
        lab_id = lab_result[0] if lab_result else 1
        
        rack_num = data.get('rackNum')
        section_num = data.get('sectionNum')
        
        # Create 5 shelves for this section
        for shelf in range(1, 6):
            location_name = f"{rack_num}.{section_num}.{shelf}"
            mssql_db.execute_query("""
                INSERT INTO [StorageLocation] ([LocationName], [LabID])
                VALUES (?, ?)
            """, (location_name, lab_id))
        
        return jsonify({
            'success': True, 
            'message': f'Section {section_num} created for rack {rack_num}'
        })
    except Exception as e:
        print(f"Error creating section: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@dashboard_mssql_bp.route('/api/storage/remove-section', methods=['POST'])
def remove_storage_section():
    try:
        data = request.json
        
        # Validate input
        if not data.get('rackNum') or not data.get('sectionNum'):
            return jsonify({'success': False, 'error': 'Rack and section number are required'}), 400
        
        rack_num = str(data.get('rackNum'))
        section_num = str(data.get('sectionNum'))
        
        # Log the values for debugging
        print(f"Attempting to delete section with rack={rack_num}, section={section_num}")
        
        # Check if there are samples at the locations
        pattern = f"{rack_num}.{section_num}.%"
        print(f"Using pattern for deletion: {pattern}")
        
        count = mssql_db.execute_query("""
            SELECT COUNT(*) FROM [SampleStorage] ss
            JOIN [StorageLocation] sl ON ss.LocationID = sl.LocationID
            WHERE sl.LocationName LIKE ?
            AND ss.AmountRemaining > 0
        """, (pattern,), fetch_one=True)[0]
        
        if count > 0:
            return jsonify({
                'success': False, 
                'error': f'Cannot delete section with {count} samples'
            }), 400
        
        # Get the locations before deleting them (for the response)
        locations_to_delete = mssql_db.execute_query("""
            SELECT [LocationID], [LocationName] FROM [StorageLocation]
            WHERE [LocationName] LIKE ?
        """, (pattern,), fetch_all=True)
        
        if not locations_to_delete:
            return jsonify({
                'success': False,
                'error': f'No locations found matching pattern {pattern}'
            }), 404
        
        # Print debug info
        location_names = [row[1] for row in locations_to_delete]
        print(f"Found {len(locations_to_delete)} locations to delete: {location_names}")
        
        # Delete the locations for this rack and section
        affected_rows = mssql_db.execute_query("""
            DELETE FROM [StorageLocation]
            WHERE [LocationName] LIKE ?
        """, (pattern,))
        
        if affected_rows == 0:
            return jsonify({
                'success': False,
                'error': f'No locations were deleted. Pattern: {pattern}'
            }), 400
        
        return jsonify({
            'success': True,
            'message': f'Section {section_num} on rack {rack_num} deleted ({affected_rows} locations)',
            'deleted_locations': location_names
        })
    except Exception as e:
        print(f"Error deleting section: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# Additional API routes would continue here...
# I'll create abbreviated versions of the remaining routes for brevity

@dashboard_mssql_bp.route('/api/storage/add-lab', methods=['POST'])
def add_storage_lab():
    try:
        data = request.json
        if not data.get('labName'):
            return jsonify({'success': False, 'error': 'Lab name is required'}), 400
        
        # Get last inserted ID using OUTPUT clause
        result = mssql_db.execute_query("""
            INSERT INTO [Lab] ([LabName])
            OUTPUT INSERTED.LabID
            VALUES (?)
        """, (data.get('labName'),), fetch_one=True)
        
        lab_id = result[0] if result else None
        
        return jsonify({
            'success': True,
            'labId': lab_id,
            'message': 'Lab created'
        })
    except Exception as e:
        print(f"Error creating lab: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@dashboard_mssql_bp.route('/api/storage/update-section-shelves', methods=['POST'])
def update_section_shelves():
    """MSSQL version - Update the number of shelves in a section"""
    try:
        data = request.json
        
        # Validate input
        if not data.get('rackNum') or not data.get('sectionNum'):
            return jsonify({'success': False, 'error': 'Rack and section number are required'}), 400
        
        if not data.get('shelfCount') or not isinstance(data.get('shelfCount'), int) or data.get('shelfCount') < 1:
            return jsonify({'success': False, 'error': 'Shelf count must be a positive integer'}), 400
        
        rack_num = str(data.get('rackNum'))
        section_num = str(data.get('sectionNum'))
        shelf_count = int(data.get('shelfCount'))
        
        # Get lab ID
        lab_result = mssql_db.execute_query("SELECT TOP 1 [LabID] FROM [lab]", fetch_one=True)
        lab_id = lab_result[0] if lab_result else 1
        
        # Check existing shelves
        existing_shelves = mssql_db.execute_query("""
            SELECT [LocationID], [LocationName], [Shelf] FROM [storagelocation]
            WHERE [LocationName] LIKE ?
            ORDER BY [Shelf]
        """, (f"{rack_num}.{section_num}.%",), fetch_all=True)
        
        existing_count = len(existing_shelves) if existing_shelves else 0
        
        # If we need to add shelves
        if shelf_count > existing_count:
            # Get the highest existing shelf number
            max_shelf = 0
            if existing_shelves:
                for shelf in existing_shelves:
                    shelf_num = shelf[2] if shelf[2] is not None else int(shelf[1].split('.')[-1])
                    max_shelf = max(max_shelf, shelf_num)
            
            # Add new shelves
            for shelf_num in range(max_shelf + 1, max_shelf + 1 + (shelf_count - existing_count)):
                location_name = f"{rack_num}.{section_num}.{shelf_num}"
                mssql_db.execute_query("""
                    INSERT INTO [storagelocation] ([LocationName], [LabID], [Rack], [Section], [Shelf])
                    VALUES (?, ?, ?, ?, ?)
                """, (location_name, lab_id, rack_num, section_num, shelf_num))
            
            message = f"Added {shelf_count - existing_count} new shelves to section {section_num} on rack {rack_num}"
        
        # If we need to remove shelves
        elif shelf_count < existing_count:
            # Sort shelves by shelf number descending to remove from the end
            shelves_to_remove = sorted(existing_shelves, 
                                     key=lambda x: x[2] if x[2] is not None else int(x[1].split('.')[-1]), 
                                     reverse=True)
            shelves_to_remove = shelves_to_remove[:existing_count - shelf_count]
            
            # Check if any shelves have samples
            for shelf in shelves_to_remove:
                location_id = shelf[0]
                count_result = mssql_db.execute_query("""
                    SELECT COUNT(*) FROM [samplestorage]
                    WHERE [LocationID] = ? AND [AmountRemaining] > 0
                """, (location_id,), fetch_one=True)
                
                count = count_result[0] if count_result else 0
                if count > 0:
                    return jsonify({
                        'success': False,
                        'error': f"Cannot remove shelf {shelf[1]} with {count} samples"
                    }), 400
            
            # Remove shelves
            for shelf in shelves_to_remove:
                location_id = shelf[0]
                mssql_db.execute_query("DELETE FROM [storagelocation] WHERE [LocationID] = ?", (location_id,))
            
            message = f"Removed {existing_count - shelf_count} shelves from section {section_num} on rack {rack_num}"
        else:
            message = f"No changes needed, section {section_num} on rack {rack_num} already has {shelf_count} shelves"
        
        return jsonify({
            'success': True,
            'message': message
        })
    except Exception as e:
        print(f"Error updating section shelves: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@dashboard_mssql_bp.route('/api/storage/add-rack', methods=['POST'])
def add_storage_rack():
    """MSSQL version - Add a new storage rack with standard sections and shelves"""
    try:
        data = request.json
        
        # Validate input
        if not data.get('rackNum'):
            return jsonify({'success': False, 'error': 'Rack number is required'}), 400
        
        rack_num = data.get('rackNum')
        
        # Get lab ID - use the first available (as default)
        lab_result = mssql_db.execute_query("SELECT TOP 1 [LabID] FROM [lab]", fetch_one=True)
        lab_id = lab_result[0] if lab_result else 1
        
        # Create location records for each section and shelf
        for section in range(1, 3):  # 2 sections as standard
            for shelf in range(1, 6):  # 5 shelves per section
                location_name = f"{rack_num}.{section}.{shelf}"
                mssql_db.execute_query("""
                    INSERT INTO [storagelocation] ([LocationName], [LabID], [Rack], [Section], [Shelf])
                    VALUES (?, ?, ?, ?, ?)
                """, (location_name, lab_id, rack_num, section, shelf))
        
        return jsonify({
            'success': True,
            'message': f'Rack {rack_num} created with 2 sections and 10 slots'
        })
    except Exception as e:
        print(f"Error creating rack: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@dashboard_mssql_bp.route('/api/storage/update-description', methods=['POST'])
def update_storage_description():
    """MSSQL version - Update storage location description"""
    try:
        data = request.json
        
        # Validate input
        if not data.get('locationId'):
            return jsonify({'success': False, 'error': 'Location ID is required'}), 400
        
        location_id = data.get('locationId')
        description = data.get('description', '')
        
        # Update the description
        rows_affected = mssql_db.execute_query("""
            UPDATE [storagelocation] 
            SET [Description] = ? 
            WHERE [LocationID] = ?
        """, (description, location_id))
        
        if rows_affected == 0:
            return jsonify({'success': False, 'error': 'Location not found'}), 404
        
        return jsonify({
            'success': True,
            'message': 'Description updated successfully'
        })
        
    except Exception as e:
        print(f"Error updating storage description: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500