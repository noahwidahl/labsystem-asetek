from flask import Blueprint, request, jsonify, current_app
from app.utils.mssql_db import mssql_db

printer_mssql_bp = Blueprint('printer_mssql', __name__)

print("DEBUG: MSSQL Printer blueprint created successfully")

@printer_mssql_bp.route('/api/print/sample/<int:sample_id>', methods=['POST'])
def print_sample_label_endpoint(sample_id):
    """
    MSSQL version - Endpoint to print sample label for a specific sample.
    """
    try:
        data = request.get_json() or {}
        auto_print = data.get('auto_print', True)
        
        # Get sample details
        sample_result = mssql_db.execute_query("""
            SELECT 
                s.SampleID,
                s.Description,
                s.PartNumber,
                s.Barcode,
                s.Amount,
                s.Type,
                s.ExpireDate,
                u.UnitName,
                sl.LocationName,
                t.TaskName
            FROM [sample] s
            LEFT JOIN [unit] u ON s.UnitID = u.UnitID
            LEFT JOIN [samplestorage] ss ON s.SampleID = ss.SampleID
            LEFT JOIN [storagelocation] sl ON ss.LocationID = sl.LocationID
            LEFT JOIN [task] t ON s.TaskID = t.TaskID
            WHERE s.SampleID = ?
        """, (sample_id,), fetch_one=True)
        
        if not sample_result:
            return jsonify({
                'status': 'error',
                'message': f'Sample {sample_id} not found'
            }), 404
        
        # Prepare sample data for label
        sample_data = {
            'SampleID': sample_result[0],
            'SampleIDFormatted': f'SMP-{sample_result[0]}',
            'Description': sample_result[1] or '',
            'PartNumber': sample_result[2] or '',
            'Barcode': sample_result[3] or '',
            'Amount': sample_result[4] or 1,
            'Type': sample_result[5] or 'Standard',
            'ExpireDate': sample_result[6].strftime('%d-%m-%Y') if sample_result[6] else '',
            'UnitName': 'pcs' if (sample_result[7] or '').lower() == 'stk' else (sample_result[7] or 'pcs'),
            'LocationName': sample_result[8] or '',
            'TaskName': sample_result[9] or 'None'
        }
        
        # Import the actual print function from printer.py
        from app.routes.printer import print_sample_label
        result = print_sample_label(sample_data, auto_print)
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Sample label print endpoint error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Sample label print error: {str(e)}'
        }), 500