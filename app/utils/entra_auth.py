import os
import jwt
import requests
import msal
import logging
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from flask import session, request

logger = logging.getLogger(__name__)

class EntraIDAuth:
    def __init__(self, client_id=None, client_secret=None, tenant_id=None):
        self.client_id = client_id or os.environ.get('AZURE_CLIENT_ID')
        self.client_secret = client_secret or os.environ.get('AZURE_CLIENT_SECRET')
        self.tenant_id = tenant_id or os.environ.get('AZURE_TENANT_ID')
        
        # Development mode check
        self.is_development = (
            not all([self.client_id, self.client_secret, self.tenant_id]) or
            any(val.startswith('dummy') for val in [self.client_id, self.client_secret, self.tenant_id] if val)
        )
        
        if self.is_development:
            logger.warning("Running in development mode without valid Azure credentials. Authentication will not work.")
            self.authority = None
            self.scopes = ["User.Read"]
            self.msal_app = None
            self._jwt_keys_cache = None
            self._jwt_keys_expires = None
            return
        
        if not all([self.client_id, self.client_secret, self.tenant_id]):
            raise ValueError("Missing Azure/Entra ID configuration. Set AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, and AZURE_TENANT_ID environment variables.")
        
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self.scopes = ["User.Read"]
        
        # MSAL instance for server-side token validation
        try:
            self.msal_app = msal.ConfidentialClientApplication(
                self.client_id,
                authority=self.authority,
                client_credential=self.client_secret,
            )
        except Exception as e:
            logger.error(f"Failed to initialize MSAL: {e}")
            self.is_development = True
            self.msal_app = None
        
        # Cache for JWT signing keys
        self._jwt_keys_cache = None
        self._jwt_keys_expires = None
    
    def get_jwt_signing_keys(self):
        """Get JWT signing keys from Microsoft's JWKS endpoint"""
        if (self._jwt_keys_cache and self._jwt_keys_expires and 
            datetime.now() < self._jwt_keys_expires):
            return self._jwt_keys_cache
        
        try:
            jwks_url = f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"
            response = requests.get(jwks_url)
            response.raise_for_status()
            
            self._jwt_keys_cache = response.json()
            self._jwt_keys_expires = datetime.now() + timedelta(hours=24)
            
            return self._jwt_keys_cache
        except Exception as e:
            logger.error(f"Failed to fetch JWT signing keys: {e}")
            return None
    
    def validate_token(self, access_token):
        """Validate JWT token from Microsoft Entra ID"""
        if self.is_development:
            logger.warning("Development mode: Skipping token validation")
            return None
            
        try:
            # Decode token header to get key ID
            header = jwt.get_unverified_header(access_token)
            kid = header.get('kid')
            
            if not kid:
                logger.error("No key ID in token header")
                return None
            
            # Get signing keys
            jwks = self.get_jwt_signing_keys()
            if not jwks:
                logger.error("Failed to get JWT signing keys")
                return None
            
            # Find the correct key
            public_key = None
            for key in jwks.get('keys', []):
                if key.get('kid') == kid:
                    # Convert JWK to PEM format
                    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                    break
            
            if not public_key:
                logger.error(f"Public key not found for kid: {kid}")
                return None
            
            # Validate token
            decoded_token = jwt.decode(
                access_token,
                public_key,
                algorithms=['RS256'],
                audience=self.client_id,
                issuer=f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"
            )
            
            return decoded_token
            
        except jwt.ExpiredSignatureError:
            logger.error("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return None
    
    def get_user_info_from_token(self, access_token):
        """Extract user information from validated token"""
        decoded_token = self.validate_token(access_token)
        
        if not decoded_token:
            return None
        
        return {
            'user_id': decoded_token.get('oid'),  # Object ID
            'email': decoded_token.get('email') or decoded_token.get('preferred_username'),
            'name': decoded_token.get('name'),
            'tenant_id': decoded_token.get('tid'),
            'upn': decoded_token.get('upn'),  # User Principal Name
        }
    
    def get_user_from_microsoft_graph(self, access_token):
        """Get additional user info from Microsoft Graph API"""
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get('https://graph.microsoft.com/v1.0/me', headers=headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get user from Graph API: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error calling Microsoft Graph: {e}")
            return None

# Global instance
entra_auth = EntraIDAuth()

def get_current_user_entra(mssql_db=None, access_token=None):
    """
    Gets the current user from Entra ID token and database.
    Compatible with existing get_current_user function signature.
    """
    default_user = {"UserID": 1, "Name": "Development User", "WindowsLogin": "dev@localhost", "Role": "Admin"}
    
    # Development mode fallback
    if entra_auth.is_development:
        logger.info("Development mode: Using default user")
        return default_user
    
    try:
        # Get access token from request headers or parameter
        if not access_token:
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                access_token = auth_header[7:]
            else:
                logger.warning("No access token provided")
                return default_user
        
        # Get user info from token
        user_info = entra_auth.get_user_info_from_token(access_token)
        if not user_info:
            logger.warning("Failed to get user info from token")
            return default_user
        
        user_email = user_info.get('email')
        user_name = user_info.get('name', user_email)
        
        if not user_email:
            logger.warning("No email found in token")
            return default_user
        
        # Look up or create user in database
        if mssql_db:
            return get_or_create_entra_user(mssql_db, user_email, user_name, user_info)
        else:
            # Return user info without database lookup
            return {
                "UserID": None,
                "Name": user_name,
                "WindowsLogin": user_email,
                "Role": "Admin",
                "IsAdmin": True,
                "EntraID": user_info.get('user_id')
            }
            
    except Exception as e:
        logger.error(f"Error in get_current_user_entra: {e}")
        return default_user

def get_or_create_entra_user(mssql_db, user_email, user_name, user_info):
    """Get or create user in MSSQL database based on Entra ID info"""
    try:
        # First try to find user by email (WindowsLogin field)
        query = "SELECT TOP 1 [UserID], [Name], [WindowsLogin], [Role] FROM [user] WHERE [WindowsLogin] = ?"
        user = mssql_db.execute_query(query, (user_email,), fetch_one=True)
        
        if user:
            logger.info(f"Found existing Entra ID user: {user[1]} ({user[2]})")
            return {
                "UserID": user[0], 
                "Name": user[1], 
                "WindowsLogin": user[2],
                "Role": user[3] or "Admin",
                "IsAdmin": True,
                "EntraID": user_info.get('user_id')
            }
        
        # User doesn't exist, create them
        logger.info(f"Creating new Entra ID user: {user_name} ({user_email})")
        
        # Insert new user
        insert_query = """
            INSERT INTO [user] ([Name], [WindowsLogin], [Role]) 
            VALUES (?, ?, ?)
        """
        mssql_db.execute_query(insert_query, (user_name, user_email, 'Admin'))
        
        # Get the new user
        user = mssql_db.execute_query(query, (user_email,), fetch_one=True)
        
        if user:
            logger.info(f"Created new Entra ID user with ID: {user[0]}")
            return {
                "UserID": user[0],
                "Name": user[1],
                "WindowsLogin": user[2],
                "Role": user[3] or "Admin",
                "IsAdmin": True,
                "EntraID": user_info.get('user_id')
            }
        else:
            logger.error("Failed to retrieve newly created Entra ID user")
            return {"UserID": 1, "Name": "System Admin", "WindowsLogin": "SYSTEM", "Role": "Admin"}
            
    except Exception as e:
        logger.error(f"Error in get_or_create_entra_user: {e}")
        return {"UserID": 1, "Name": "System Admin", "WindowsLogin": "SYSTEM", "Role": "Admin"}