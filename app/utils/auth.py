import os
import subprocess
import platform

def get_windows_username():
    """
    Get the full Windows username including domain.
    Returns format like DOMAIN\\username or username@domain.com
    """
    try:
        if platform.system() == 'Windows':
            # Try to get domain\username format
            userdomain = os.environ.get('USERDOMAIN', '')
            username = os.environ.get('USERNAME', '')
            
            if userdomain and username:
                # Return in DOMAIN\username format
                windows_login = f"{userdomain}\\{username}"
                print(f"DEBUG: Windows login detected: {windows_login}")
                return windows_login
            elif username:
                return username
        else:
            # For non-Windows systems, just get the username
            return os.environ.get('USER', '')
    except Exception as e:
        print(f"Error getting Windows username: {e}")
        return os.environ.get('USERNAME', os.environ.get('USER', ''))

def get_current_user(mysql=None):
    """
    Gets the current user from the database based on Windows authentication.
    Automatically creates users if they don't exist.
    """
    # Default admin user as fallback
    default_user = {"UserID": 1, "Name": "System Admin", "WindowsLogin": "SYSTEM", "Role": "Admin"}
    
    if not mysql:
        return default_user
    
    try:
        # Get Windows username with domain
        windows_login = get_windows_username()
        
        if not windows_login:
            print("DEBUG: No Windows login found, using default admin")
            return default_user
        
        cursor = mysql.connection.cursor()
        
        # First try to find user by WindowsLogin
        cursor.execute("SELECT UserID, Name, WindowsLogin, Role FROM user WHERE WindowsLogin = %s LIMIT 1", (windows_login,))
        user = cursor.fetchone()
        
        if user:
            # User exists, return their info
            cursor.close()
            print(f"DEBUG: Found existing user: {user[1]} ({user[2]})")
            return {
                "UserID": user[0], 
                "Name": user[1], 
                "WindowsLogin": user[2],
                "Role": user[3] or "Admin",
                "IsAdmin": True  # All users are admin for now
            }
        
        # User doesn't exist, let's create them
        print(f"DEBUG: Creating new user for Windows login: {windows_login}")
        
        # Extract just the username part for display name
        display_name = windows_login.split('\\')[-1].split('@')[0]
        
        # Insert new user (all users are admin by default)
        cursor.execute("""
            INSERT INTO user (Name, WindowsLogin, Role) 
            VALUES (%s, %s, %s)
        """, (display_name, windows_login, 'Admin'))
        
        user_id = cursor.lastrowid
        mysql.connection.commit()
        
        print(f"DEBUG: Created new user with ID: {user_id}")
        
        cursor.close()
        
        return {
            "UserID": user_id,
            "Name": display_name,
            "WindowsLogin": windows_login,
            "Role": "Admin",
            "IsAdmin": True
        }
        
    except Exception as e:
        print(f"Error in get_current_user: {e}")
        import traceback
        traceback.print_exc()
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