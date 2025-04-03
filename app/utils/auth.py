def get_current_user(mysql=None):
    """
    Gets the current user from the database.
    In a real application, this would get the user from the session.
    """
    if not mysql:
        return {"UserID": 1, "Name": "BWM"}  # Fallback
    
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT UserID, Name FROM User WHERE Name = 'BWM' LIMIT 1")
        user = cursor.fetchone()
        cursor.close()
        
        if user:
            return {"UserID": user[0], "Name": user[1]}
        else:
            return {"UserID": 1, "Name": "BWM"}  # Fallback
    except:
        return {"UserID": 1, "Name": "BWM"}  # Fallback if there is an error