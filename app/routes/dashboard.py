from flask import Blueprint, render_template, jsonify, request

dashboard_bp = Blueprint('dashboard', __name__)

def _get_storage_locations(mysql):
    """Retrieves storage locations from the database"""
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT 
            sl.LocationID,
            sl.LocationName,
            sl.Description,
            COUNT(ss.StorageID) as count,
            CASE WHEN COUNT(ss.StorageID) > 0 THEN 'occupied' ELSE 'available' END as status,
            IFNULL(l.LabName, 'Unknown') as LabName,
            sl.Rack,
            sl.Section,
            sl.Shelf
        FROM storagelocation sl
        LEFT JOIN lab l ON sl.LabID = l.LabID
        LEFT JOIN samplestorage ss ON sl.LocationID = ss.LocationID AND ss.AmountRemaining > 0
        GROUP BY sl.LocationID, sl.LocationName, sl.Description, l.LabName, sl.Rack, sl.Section, sl.Shelf
        ORDER BY 
            COALESCE(sl.Rack, 999),
            COALESCE(sl.Section, 999),
            COALESCE(sl.Shelf, 999)
    """)
    
    columns = [col[0] for col in cursor.description]
    locations = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    # For locations where Rack, Section, Shelf are NULL, extract them from LocationName
    for loc in locations:
        if loc.get('Rack') is None or loc.get('Section') is None or loc.get('Shelf') is None:
            parts = loc.get('LocationName', '').split('.')
            if len(parts) == 3:
                loc['Rack'] = int(parts[0]) if parts[0].isdigit() else None
                loc['Section'] = int(parts[1]) if parts[1].isdigit() else None
                loc['Shelf'] = int(parts[2]) if parts[2].isdigit() else None
    
    cursor.close()
    return locations

def init_dashboard(blueprint, mysql):
    @blueprint.route('/')
    @blueprint.route('/dashboard')
    def dashboard():
        try:
            # Get number of samples in storage
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM sample WHERE Status = 'In Storage'")
            sample_count = cursor.fetchone()[0] or 0
            
            # Get samples expiring soon (within 14 days)
            cursor.execute("""
                SELECT COUNT(*) FROM samplestorage ss
                JOIN sample s ON ss.SampleID = s.SampleID
                WHERE ss.ExpireDate <= DATE_ADD(CURRENT_DATE(), INTERVAL 14 DAY)
                AND s.Status = 'In Storage'
                AND ss.AmountRemaining > 0
            """)
            expiring_count = cursor.fetchone()[0] or 0
            
            # Get new samples today
            cursor.execute("""
                SELECT COUNT(*) FROM reception
                WHERE DATE(ReceivedDate) = CURRENT_DATE()
            """)
            new_today = cursor.fetchone()[0] or 0
            
            # Get number of active tests (In Progress or Created status)
            cursor.execute("""
                SELECT COUNT(*) FROM test t
                WHERE t.Status IN ('In Progress', 'Created')
            """)
            active_tests_count = cursor.fetchone()[0] or 0
            
            # Get recent history
            cursor.execute("""
                SELECT 
                    h.LogID, 
                    h.ActionType, 
                    h.Notes,
                    IFNULL(s.Description, 'N/A') as SampleDesc,
                    u.Name as UserName,
                    DATE_FORMAT(h.Timestamp, '%d-%m-%Y %H:%i') as Timestamp
                FROM history h
                LEFT JOIN sample s ON h.SampleID = s.SampleID
                LEFT JOIN user u ON h.UserID = u.UserID
                ORDER BY h.Timestamp DESC
                LIMIT 5
            """)
            
            columns = [col[0] for col in cursor.description]
            history_items = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            cursor.close()
            
            # Get storage locations using the helper function
            locations = _get_storage_locations(mysql)
            
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
    
    @blueprint.route('/api/storage-locations')
    def api_storage_locations():
        try:
            locations = _get_storage_locations(mysql)
            
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
            
    @blueprint.route('/history')
    def history():
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("""
                SELECT 
                    h.LogID,
                    DATE_FORMAT(h.Timestamp, '%d %b %Y %H:%i') as FormattedDate,
                    h.ActionType,
                    u.Name as UserName,
                    CASE 
                        WHEN h.SampleID IS NOT NULL THEN s.SampleID
                        WHEN h.TestID IS NOT NULL THEN t.TestNo
                        ELSE 'N/A'
                    END as ItemID,
                    h.Notes,
                    r.ReceptionID,
                    s.Description as SampleDescription,
                    s.PartNumber as SamplePartNumber,
                    h.SampleID as RawSampleID
                FROM history h
                LEFT JOIN user u ON h.UserID = u.UserID
                LEFT JOIN sample s ON h.SampleID = s.SampleID
                LEFT JOIN test t ON h.TestID = t.TestID
                LEFT JOIN reception r ON s.ReceptionID = r.ReceptionID
                ORDER BY h.Timestamp DESC
                LIMIT 100
            """)
            history_data = cursor.fetchall()
            
            # Get distinct action types for filter dropdown
            cursor.execute("SELECT DISTINCT ActionType FROM history ORDER BY ActionType")
            action_types = [row[0] for row in cursor.fetchall()]
            
            cursor.close()
            
            history_items = []
            for item in history_data:
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
            
    @blueprint.route('/api/history', methods=['GET'])
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
                    DATE_FORMAT(h.Timestamp, '%d %b %Y %H:%i') as FormattedDate,
                    h.ActionType,
                    u.Name as UserName,
                    CASE 
                        WHEN h.SampleID IS NOT NULL THEN s.SampleID
                        WHEN h.TestID IS NOT NULL THEN t.TestNo
                        ELSE 'N/A'
                    END as ItemID,
                    h.Notes,
                    r.ReceptionID
                FROM history h
                LEFT JOIN user u ON h.UserID = u.UserID
                LEFT JOIN sample s ON h.SampleID = s.SampleID
                LEFT JOIN test t ON h.TestID = t.TestID
                LEFT JOIN reception r ON s.ReceptionID = r.ReceptionID
                WHERE 1=1
            """
            params = []
            
            # Add filters to the query
            if search:
                query += " AND (COALESCE(s.SampleID, t.TestNo, '') LIKE %s OR h.Notes LIKE %s)"
                params.extend([f"%{search}%", f"%{search}%"])
            
            if action_type:
                query += " AND h.ActionType = %s"
                params.append(action_type)
            
            if user:
                query += " AND u.Name = %s"
                params.append(user)
            
            if date_from:
                query += " AND DATE(h.Timestamp) >= %s"
                params.append(date_from)
            
            if date_to:
                query += " AND DATE(h.Timestamp) <= %s"
                params.append(date_to)
            
            if notes:
                query += " AND h.Notes LIKE %s"
                params.append(f"%{notes}%")
            
            # Add ordering and pagination
            query += " ORDER BY h.Timestamp DESC LIMIT %s OFFSET %s"
            params.append(per_page)
            params.append((page - 1) * per_page)
            
            # Execute the query
            cursor = mysql.connection.cursor()
            cursor.execute(query, params)
            history_data = cursor.fetchall()
            cursor.close()
            
            # Format the results
            history_items = []
            for item in history_data:
                # Format ItemID based on type
                item_id = item[4]
                if item_id and item_id != 'N/A':
                    if item_id.startswith('T'):  # Test number
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
    
    @blueprint.route('/api/history/details/<int:log_id>', methods=['GET'])
    def api_history_details(log_id):
        """API endpoint to get detailed information about a specific history record"""
        try:
            cursor = mysql.connection.cursor()
            
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
                FROM history h
                WHERE h.LogID = %s
            """
            
            cursor.execute(basic_query, (log_id,))
            log_data = cursor.fetchone()
            
            if not log_data:
                cursor.close()
                return jsonify({
                    'success': False,
                    'error': 'History record not found'
                }), 404
            
            # Get user name separately to avoid join issues
            user_name = 'Unknown User'
            if log_data[6]:  # UserID
                try:
                    cursor.execute("SELECT Name FROM user WHERE UserID = %s", (log_data[6],))
                    user_result = cursor.fetchone()
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
            
            # Try to get sample info if SampleID exists
            sample_info = None
            sample_history = []
            if log_data[4]:
                try:
                    cursor.execute("SELECT SampleID, Description, Status, PartNumber FROM sample WHERE SampleID = %s", (log_data[4],))
                    sample_data = cursor.fetchone()
                    if sample_data:
                        sample_info = {
                            "SampleID": sample_data[0],
                            "Description": sample_data[1] or 'No description',
                            "Status": sample_data[2] or 'Unknown',
                            "PartNumber": sample_data[3] or 'No part number',
                            "Location": 'Unknown location'  # Simplified - no complex location lookup
                        }
                        
                        # Get basic sample history
                        try:
                            history_query = """
                                SELECT 
                                    DATE_FORMAT(h.Timestamp, '%d %b %Y %H:%i') as FormattedDate,
                                    h.ActionType,
                                    h.Notes
                                FROM history h
                                WHERE h.SampleID = %s
                                ORDER BY h.Timestamp DESC
                                LIMIT 5
                            """
                            cursor.execute(history_query, (log_data[4],))
                            for history_row in cursor.fetchall():
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
            
            cursor.close()
            
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
    
    @blueprint.route('/api/history/export', methods=['GET'])
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
                    DATE_FORMAT(h.Timestamp, '%Y-%m-%d %H:%i:%s') as FormattedDate,
                    h.ActionType,
                    u.Name as UserName,
                    CASE 
                        WHEN h.SampleID IS NOT NULL THEN s.SampleID
                        WHEN h.TestID IS NOT NULL THEN t.TestNo
                        ELSE 'N/A'
                    END as ItemID,
                    COALESCE(s.Description, 'N/A') as SampleDescription,
                    h.Notes,
                    COALESCE(sl.LocationName, 'N/A') as Location
                FROM history h
                LEFT JOIN user u ON h.UserID = u.UserID
                LEFT JOIN sample s ON h.SampleID = s.SampleID
                LEFT JOIN test t ON h.TestID = t.TestID
                LEFT JOIN samplestorage ss ON s.SampleID = ss.SampleID AND ss.AmountRemaining > 0
                LEFT JOIN storagelocation sl ON ss.LocationID = sl.LocationID
                WHERE 1=1
            """
            params = []
            
            # Add filters to the query (same as in api_get_history)
            if search:
                query += " AND (COALESCE(s.SampleID, t.TestNo, '') LIKE %s OR h.Notes LIKE %s)"
                params.extend([f"%{search}%", f"%{search}%"])
            
            if action_type:
                query += " AND h.ActionType = %s"
                params.append(action_type)
            
            if user:
                query += " AND u.Name = %s"
                params.append(user)
            
            if date_from:
                query += " AND DATE(h.Timestamp) >= %s"
                params.append(date_from)
            
            if date_to:
                query += " AND DATE(h.Timestamp) <= %s"
                params.append(date_to)
            
            if notes:
                query += " AND h.Notes LIKE %s"
                params.append(f"%{notes}%")
            
            # Add ordering but no limit for export
            query += " ORDER BY h.Timestamp DESC"
            
            # Execute the query
            cursor = mysql.connection.cursor()
            cursor.execute(query, params)
            history_data = cursor.fetchall()
            cursor.close()
            
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
    
    @blueprint.route('/api/storage-locations')
    def get_storage_locations():
        try:
            # Use the helper function to get locations
            locations = _get_storage_locations(mysql)
            return jsonify({'locations': locations})
        except Exception as e:
            print(f"API error when fetching storage locations: {e}")
            return jsonify({'error': str(e)}), 500
            
    # Add new routes here inside the init_dashboard function
    @blueprint.route('/api/storage/add-section', methods=['POST'])
    def add_storage_section():
        try:
            data = request.json
            # Validate input
            if not data.get('rackNum') or not data.get('sectionNum'):
                return jsonify({'success': False, 'error': 'Rack and section number are required'}), 400
            
            # Get lab ID
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT LabID FROM Lab LIMIT 1")
            lab_result = cursor.fetchone()
            lab_id = lab_result[0] if lab_result else 1
            
            rack_num = data.get('rackNum')
            section_num = data.get('sectionNum')
            
            # Create 5 shelves for this section
            for shelf in range(1, 6):
                location_name = f"{rack_num}.{section_num}.{shelf}"
                cursor.execute("""
                    INSERT INTO StorageLocation (LocationName, LabID)
                    VALUES (%s, %s)
                """, (
                    location_name, 
                    lab_id
                ))
            
            mysql.connection.commit()
            cursor.close()
            
            return jsonify({
                'success': True, 
                'message': f'Section {section_num} created for rack {rack_num}'
            })
        except Exception as e:
            print(f"Error creating section: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @blueprint.route('/api/storage/remove-section', methods=['POST'])
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
            cursor = mysql.connection.cursor()
            pattern = f"{rack_num}.{section_num}.%"
            print(f"Using pattern for deletion: {pattern}")
            
            cursor.execute("""
                SELECT COUNT(*) FROM SampleStorage ss
                JOIN StorageLocation sl ON ss.LocationID = sl.LocationID
                WHERE sl.LocationName LIKE %s
                AND ss.AmountRemaining > 0
            """, (pattern,))
            
            count = cursor.fetchone()[0]
            if count > 0:
                return jsonify({
                    'success': False, 
                    'error': f'Cannot delete section with {count} samples'
                }), 400
            
            # Get the locations before deleting them (for the response)
            cursor.execute("""
                SELECT LocationID, LocationName FROM StorageLocation
                WHERE LocationName LIKE %s
            """, (pattern,))
            locations_to_delete = cursor.fetchall()
            
            if not locations_to_delete:
                return jsonify({
                    'success': False,
                    'error': f'No locations found matching pattern {pattern}'
                }), 404
            
            # Print debug info
            location_ids = [row[0] for row in locations_to_delete]
            location_names = [row[1] for row in locations_to_delete]
            print(f"Found {len(location_ids)} locations to delete: {location_names}")
            
            # Delete the locations for this rack and section
            cursor.execute("""
                DELETE FROM StorageLocation
                WHERE LocationName LIKE %s
            """, (pattern,))
            
            mysql.connection.commit()
            affected_rows = cursor.rowcount
            cursor.close()
            
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
        
    @blueprint.route('/api/storage/update-section-shelves', methods=['POST'])
    def update_section_shelves():
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
            
            cursor = mysql.connection.cursor()
            
            # Get lab ID
            cursor.execute("SELECT LabID FROM Lab LIMIT 1")
            lab_result = cursor.fetchone()
            lab_id = lab_result[0] if lab_result else 1
            
            # Check existing shelves
            cursor.execute("""
                SELECT LocationID, LocationName, Shelf FROM StorageLocation
                WHERE LocationName LIKE %s
                ORDER BY Shelf
            """, (f"{rack_num}.{section_num}.%",))
            
            existing_shelves = cursor.fetchall()
            existing_count = len(existing_shelves)
            
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
                    cursor.execute("""
                        INSERT INTO StorageLocation (LocationName, LabID, Rack, Section, Shelf)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (location_name, lab_id, rack_num, section_num, shelf_num))
                
                message = f"Added {shelf_count - existing_count} new shelves to section {section_num} on rack {rack_num}"
            
            # If we need to remove shelves
            elif shelf_count < existing_count:
                # Sort shelves by shelf number descending to remove from the end
                shelves_to_remove = sorted(existing_shelves, key=lambda x: x[2] if x[2] is not None else int(x[1].split('.')[-1]), reverse=True)
                shelves_to_remove = shelves_to_remove[:existing_count - shelf_count]
                
                # Check if any shelves have samples
                for shelf in shelves_to_remove:
                    location_id = shelf[0]
                    cursor.execute("""
                        SELECT COUNT(*) FROM SampleStorage
                        WHERE LocationID = %s AND AmountRemaining > 0
                    """, (location_id,))
                    
                    count = cursor.fetchone()[0]
                    if count > 0:
                        return jsonify({
                            'success': False,
                            'error': f"Cannot remove shelf {shelf[1]} with {count} samples"
                        }), 400
                
                # Remove shelves
                for shelf in shelves_to_remove:
                    location_id = shelf[0]
                    cursor.execute("DELETE FROM StorageLocation WHERE LocationID = %s", (location_id,))
                
                message = f"Removed {existing_count - shelf_count} shelves from section {section_num} on rack {rack_num}"
            else:
                message = f"No changes needed, section {section_num} on rack {rack_num} already has {shelf_count} shelves"
            
            mysql.connection.commit()
            cursor.close()
            
            return jsonify({
                'success': True,
                'message': message
            })
        except Exception as e:
            print(f"Error updating section shelves: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
            
    @blueprint.route('/api/storage/add-lab', methods=['POST'])
    def add_storage_lab():
        try:
            data = request.json
            
            # Validate input
            if not data.get('labName'):
                return jsonify({'success': False, 'error': 'Lab name is required'}), 400
            
            # Create new lab
            cursor = mysql.connection.cursor()
            cursor.execute("""
                INSERT INTO Lab (LabName)
                VALUES (%s)
            """, (data.get('labName'),))
            
            mysql.connection.commit()
            lab_id = cursor.lastrowid
            cursor.close()
            
            return jsonify({
                'success': True,
                'labId': lab_id,
                'message': 'Lab created'
            })
        except Exception as e:
            print(f"Error creating lab: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @blueprint.route('/api/storage/add-rack', methods=['POST'])
    def add_storage_rack():
        try:
            data = request.json
            
            # Validate input
            if not data.get('rackNum'):
                return jsonify({'success': False, 'error': 'Rack number is required'}), 400
            
            rack_num = data.get('rackNum')
            
            # Create 2 standard sections for this rack (with 5 shelves each)
            cursor = mysql.connection.cursor()
            
            # Get lab ID - use the first available (as default)
            cursor.execute("SELECT LabID FROM Lab LIMIT 1")
            lab_result = cursor.fetchone()
            lab_id = lab_result[0] if lab_result else 1
            
            # Create location records for each section and shelf
            for section in range(1, 3):  # 2 sections as standard
                for shelf in range(1, 6):  # 5 shelves per section
                    location_name = f"{rack_num}.{section}.{shelf}"
                    cursor.execute("""
                        INSERT INTO StorageLocation (LocationName, LabID, Rack, Section, Shelf)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (location_name, lab_id, rack_num, section, shelf))
            
            mysql.connection.commit()
            cursor.close()
            
            return jsonify({
                'success': True,
                'message': f'Rack {rack_num} created with 2 sections and 10 slots'
            })
        except Exception as e:
            print(f"Error creating rack: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @blueprint.route('/api/storage/update-description', methods=['POST'])
    def update_storage_description():
        try:
            data = request.json
            
            # Validate input
            if not data.get('locationId'):
                return jsonify({'success': False, 'error': 'Location ID is required'}), 400
            
            location_id = data.get('locationId')
            description = data.get('description', '')
            
            cursor = mysql.connection.cursor()
            
            # Update the description
            cursor.execute("""
                UPDATE StorageLocation 
                SET Description = %s 
                WHERE LocationID = %s
            """, (description, location_id))
            
            mysql.connection.commit()
            
            if cursor.rowcount == 0:
                cursor.close()
                return jsonify({'success': False, 'error': 'Location not found'}), 404
            
            cursor.close()
            
            return jsonify({
                'success': True,
                'message': 'Description updated successfully'
            })
        except Exception as e:
            print(f"Error updating description: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500