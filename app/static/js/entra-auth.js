// Entra ID Authentication Manager
class EntraAuth {
    constructor() {
        this.msalConfig = {
            auth: {
                clientId: this.getClientId(),
                authority: `https://login.microsoftonline.com/${this.getTenantId()}`,
                redirectUri: window.location.origin + '/auth/callback'
            },
            cache: {
                cacheLocation: "localStorage",
                storeAuthStateInCookie: false,
            }
        };

        this.msalInstance = null;
        this.loginRequest = {
            scopes: ["User.Read"]
        };
        
        this.init();
    }

    // Get client ID from meta tag or localStorage
    getClientId() {
        const meta = document.querySelector('meta[name="azure-client-id"]');
        return meta ? meta.getAttribute('content') : '';
    }

    // Get tenant ID from meta tag or localStorage
    getTenantId() {
        const meta = document.querySelector('meta[name="azure-tenant-id"]');
        return meta ? meta.getAttribute('content') : '';
    }

    async init() {
        try {
            // Load MSAL if not already loaded
            if (typeof msal === 'undefined') {
                await this.loadMSAL();
            }

            this.msalInstance = new msal.PublicClientApplication(this.msalConfig);
            await this.msalInstance.initialize();
            
            // Check authentication status
            await this.checkAuthStatus();
        } catch (error) {
            console.error('EntraAuth initialization failed:', error);
        }
    }

    async loadMSAL() {
        return new Promise((resolve, reject) => {
            if (typeof msal !== 'undefined') {
                resolve();
                return;
            }

            const script = document.createElement('script');
            script.src = 'https://alcdn.msauth.net/browser/2.38.2/js/msal-browser.min.js';
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    async checkAuthStatus() {
        // Don't check auth on login page
        if (window.location.pathname === '/login' || window.location.pathname === '/auth/callback') {
            return;
        }

        const storedToken = localStorage.getItem('access_token');
        
        // Development mode check
        if (storedToken === 'development-token') {
            console.log('Development mode: Using development token');
            this.setupRequestInterceptor();
            return;
        }

        const accounts = this.msalInstance.getAllAccounts();

        if (accounts.length === 0 && !storedToken) {
            // No account and no token - redirect to login
            this.redirectToLogin();
            return;
        }

        // Try to get a fresh token silently
        if (accounts.length > 0) {
            try {
                const silentRequest = {
                    ...this.loginRequest,
                    account: accounts[0]
                };
                const tokenResponse = await this.msalInstance.acquireTokenSilent(silentRequest);
                
                this.setAccessToken(tokenResponse.accessToken);
                this.setupRequestInterceptor();
            } catch (error) {
                console.warn('Silent token acquisition failed:', error);
                
                // If we have a stored token, try to use it
                if (storedToken) {
                    this.setupRequestInterceptor();
                } else {
                    this.redirectToLogin();
                }
            }
        } else if (storedToken) {
            // No MSAL account but we have a stored token
            this.setupRequestInterceptor();
        }
    }

    setAccessToken(token) {
        localStorage.setItem('access_token', token);
    }

    getAccessToken() {
        return localStorage.getItem('access_token');
    }

    setupRequestInterceptor() {
        const originalFetch = window.fetch;
        const token = this.getAccessToken();

        if (!token) {
            this.redirectToLogin();
            return;
        }

        // Intercept all fetch requests to add Authorization header
        window.fetch = async (url, options = {}) => {
            // Don't add auth header for external URLs or auth endpoints
            if (typeof url === 'string' && 
                (url.startsWith('http') && !url.startsWith(window.location.origin))) {
                return originalFetch(url, options);
            }

            options.headers = options.headers || {};
            options.headers['Authorization'] = `Bearer ${token}`;

            try {
                const response = await originalFetch(url, options);
                
                // If we get 401, token might be expired
                if (response.status === 401) {
                    console.warn('Received 401, token may be expired');
                    await this.handleTokenExpired();
                    return response;
                }
                
                return response;
            } catch (error) {
                console.error('Fetch error:', error);
                throw error;
            }
        };

        // Also intercept jQuery AJAX if available
        if (typeof $ !== 'undefined' && $.ajaxSetup) {
            $.ajaxSetup({
                beforeSend: function(xhr) {
                    xhr.setRequestHeader('Authorization', `Bearer ${token}`);
                },
                error: function(xhr) {
                    if (xhr.status === 401) {
                        console.warn('jQuery AJAX received 401, token may be expired');
                        window.entraAuth.handleTokenExpired();
                    }
                }
            });
        }
    }

    async handleTokenExpired() {
        const accounts = this.msalInstance.getAllAccounts();
        
        if (accounts.length > 0) {
            try {
                // Try to refresh token silently
                const silentRequest = {
                    ...this.loginRequest,
                    account: accounts[0]
                };
                const tokenResponse = await this.msalInstance.acquireTokenSilent(silentRequest);
                
                this.setAccessToken(tokenResponse.accessToken);
                
                // Reload the page to retry with new token
                window.location.reload();
            } catch (error) {
                console.error('Token refresh failed:', error);
                this.redirectToLogin();
            }
        } else {
            this.redirectToLogin();
        }
    }

    redirectToLogin() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user_info');
        window.location.href = '/login';
    }

    async logout() {
        try {
            const accounts = this.msalInstance.getAllAccounts();
            
            if (accounts.length > 0) {
                await this.msalInstance.logoutPopup({
                    account: accounts[0],
                    mainWindowRedirectUri: window.location.origin + '/login'
                });
            }
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            localStorage.removeItem('access_token');
            localStorage.removeItem('user_info');
            window.location.href = '/login';
        }
    }

    async getCurrentUser() {
        const token = this.getAccessToken();
        if (!token) {
            return null;
        }

        try {
            const response = await fetch('/auth/user-info', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                return data.user;
            } else {
                console.error('Failed to get user info:', response.status);
                return null;
            }
        } catch (error) {
            console.error('Error getting current user:', error);
            return null;
        }
    }
}

// Initialize global authentication manager
window.entraAuth = new EntraAuth();

// Add logout functionality to any logout buttons
document.addEventListener('DOMContentLoaded', function() {
    const logoutButtons = document.querySelectorAll('[data-logout]');
    logoutButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            window.entraAuth.logout();
        });
    });
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EntraAuth;
}