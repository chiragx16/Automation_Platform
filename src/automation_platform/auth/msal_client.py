from msal import ConfidentialClientApplication
from automation_platform.settings import settings

CLIENT_ID = settings.MS_CLIENT_ID
CLIENT_SECRET = settings.MS_CLIENT_SECRET
TENANT_ID = settings.MS_TENANT_ID

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
REDIRECT_URI = "http://localhost:5000/auth/callback"
SCOPES = ["User.Read"]

msal_app = ConfidentialClientApplication(
    CLIENT_ID,
    authority=AUTHORITY,
    client_credential=CLIENT_SECRET,
)
