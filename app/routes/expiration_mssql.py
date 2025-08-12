from flask import Blueprint, jsonify, request, render_template
from app.utils.mssql_db import mssql_db
from datetime import datetime, timedelta

expiration_mssql_bp = Blueprint('expiration_mssql', __name__)

@expiration_mssql_bp.route('/expiry')
def expiry_page():
    try:
        # Get current user
        user_id = 1  # TODO: Implement proper user authentication
        
        return render_template('sections/expiry.html')
        
    except Exception as e:
        print(f"Error loading expiry page: {e}")
        return render_template('sections/expiry.html')

@expiration_mssql_bp.route('/api/samples/expired', methods=['GET'])
def get_expired_samples():
    """
    Get list of expired samples - MSSQL version.
    """
    try:
        user_id = 1  # TODO: Implement proper user authentication
        my_samples_only = request.args.get('my_samples_only', 'false').lower() == 'true'
        
        # Build WHERE clause
        where_conditions = ["s.[Status] = 'In Storage'", "ss.[ExpireDate] < GETDATE()"]
        params = []
        
        if my_samples_only:
            where_conditions.append("r.[UserID] = ?")
            params.append(user_id)
        
        query = """
            SELECT DISTINCT
                s.[SampleID],
                s.[Description],
                s.[PartNumber],
                s.[Barcode],
                ss.[ExpireDate],
                DATEDIFF(day, ss.[ExpireDate], GETDATE()) as DaysOverdue,
                u.[Name] as RegisteredBy,
                sl.[LocationName] as Location
            FROM [sample] s
            LEFT JOIN [samplestorage] ss ON s.[SampleID] = ss.[SampleID]
            LEFT JOIN [reception] r ON s.[ReceptionID] = r.[ReceptionID]
            LEFT JOIN [user] u ON r.[UserID] = u.[UserID]
            LEFT JOIN [storagelocation] sl ON ss.[LocationID] = sl.[LocationID]
            WHERE {}
            ORDER BY ss.[ExpireDate] ASC
        """.format(" AND ".join(where_conditions))
        
        results = mssql_db.execute_query(query, params, fetch_all=True)
        
        expired_samples = []
        for row in results:
            expired_samples.append({
                'sample_id': row[0],
                'description': row[1] or 'N/A',
                'part_number': row[2] or 'N/A',
                'barcode': row[3] or 'N/A',
                'expire_date': row[4].strftime('%Y-%m-%d') if row[4] else 'N/A',
                'days_overdue': row[5] or 0,
                'registered_by': row[6] or 'Unknown',
                'location': row[7] or 'Unknown'
            })
        
        return jsonify({
            'status': 'success',
            'expired_samples': expired_samples,
            'count': len(expired_samples)
        })
        
    except Exception as e:
        print(f"Error getting expired samples: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get expired samples: {str(e)}'
        }), 500

@expiration_mssql_bp.route('/api/samples/expiring-soon', methods=['GET'])
def get_expiring_soon_samples():
    """
    Get list of samples expiring soon - MSSQL version.
    """
    try:
        user_id = 1  # TODO: Implement proper user authentication
        my_samples_only = request.args.get('my_samples_only', 'false').lower() == 'true'
        days_ahead = int(request.args.get('days_ahead', 7))
        
        # Build WHERE clause
        where_conditions = [
            "s.[Status] = 'In Storage'",
            "ss.[ExpireDate] >= GETDATE()",
            f"ss.[ExpireDate] <= DATEADD(day, {days_ahead}, GETDATE())"
        ]
        params = []
        
        if my_samples_only:
            where_conditions.append("r.[UserID] = ?")
            params.append(user_id)
        
        query = """
            SELECT DISTINCT
                s.[SampleID],
                s.[Description],
                s.[PartNumber],
                s.[Barcode],
                ss.[ExpireDate],
                DATEDIFF(day, GETDATE(), ss.[ExpireDate]) as DaysUntilExpiry,
                u.[Name] as RegisteredBy,
                sl.[LocationName] as Location
            FROM [sample] s
            LEFT JOIN [samplestorage] ss ON s.[SampleID] = ss.[SampleID]
            LEFT JOIN [reception] r ON s.[ReceptionID] = r.[ReceptionID]
            LEFT JOIN [user] u ON r.[UserID] = u.[UserID]
            LEFT JOIN [storagelocation] sl ON ss.[LocationID] = sl.[LocationID]
            WHERE {}
            ORDER BY ss.[ExpireDate] ASC
        """.format(" AND ".join(where_conditions))
        
        results = mssql_db.execute_query(query, params, fetch_all=True)
        
        expiring_samples = []
        for row in results:
            expiring_samples.append({
                'sample_id': row[0],
                'description': row[1] or 'N/A',
                'part_number': row[2] or 'N/A',
                'barcode': row[3] or 'N/A',
                'expire_date': row[4].strftime('%Y-%m-%d') if row[4] else 'N/A',
                'days_until_expiry': row[5] or 0,
                'registered_by': row[6] or 'Unknown',
                'location': row[7] or 'Unknown'
            })
        
        return jsonify({
            'status': 'success',
            'expiring_samples': expiring_samples,
            'count': len(expiring_samples)
        })
        
    except Exception as e:
        print(f"Error getting expiring soon samples: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get expiring soon samples: {str(e)}'
        }), 500