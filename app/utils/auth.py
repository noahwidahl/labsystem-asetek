import os

def get_current_user(mysql=None):
    """
    Gets the current user from the database.
    In a real application, this would get the user from the session.
    
    For now, we try to get the Windows username and check if it's in the database.
    """
    # Default admin user as fallback
    default_user = {"UserID": 1, "Name": "System Admin", "IsAdmin": True}
    
    if not mysql:
        return default_user
    
    try:
        # Try to get Windows username (or other environment username)
        username = os.environ.get('USERNAME') or os.environ.get('USER')
        
        cursor = mysql.connection.cursor()
        
        if username:
            # First try to find the actual username in database
            cursor.execute("SELECT UserID, Name, IsAdmin FROM User WHERE Name = %s LIMIT 1", (username,))
            user = cursor.fetchone()
            
            # If found, return that user
            if user:
                cursor.close()
                return {"UserID": user[0], "Name": user[1], "IsAdmin": bool(user[2])}
        
        # Otherwise, fall back to first admin user
        cursor.execute("SELECT UserID, Name, IsAdmin FROM User WHERE IsAdmin = 1 LIMIT 1")
        user = cursor.fetchone()
        cursor.close()
        
        if user:
            return {"UserID": user[0], "Name": user[1], "IsAdmin": bool(user[2])}
        else:
            return default_user
    except Exception as e:
        print(f"Error in get_current_user: {e}")
        return default_user

def check_domain_access(domain=None):
    """
    Checks if the user's domain allows access.
    Will be used for domain-based authorization in the future.
    """
    # Placeholder for future implementation
    # Would check the user's Windows domain against allowed domains
    return True

def is_admin(user=None):
    """
    Checks if a user is an admin.
    """
    if not user:
        user = get_current_user()
    
    return user.get("IsAdmin", False)