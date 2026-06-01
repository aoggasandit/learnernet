# LearnerNet

A simple social learning app built with Streamlit and OpenAI. LearnerNet lets users share study posts, recommend resources, and ask an AI assistant for research help.

## Setup

1. Create a virtual environment and activate it.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set your OpenAI API key in the environment:
   - Windows PowerShell:
     ```powershell
     $env:OPENAI_API_KEY = "YOUR_KEY"
     ```
   - macOS/Linux:
     ```bash
     export OPENAI_API_KEY="YOUR_KEY"
     ```
4. Run the app:
   ```bash
   streamlit run app.py
   ```

## Features

- Register and sign in with a secure password
- Create posts, comments, and learning resources
- Like posts and track discussion activity
- AI research assistant for summaries and study guidance
- Profile page showing your contributions and activity

## Email & Password Reset Setup

The app supports password reset emails via two methods:

### Option 1: Gmail SMTP (Simpler, Recommended for Testing)

1. Enable 2-Step Verification on your Google Account: https://myaccount.google.com/security
2. Generate an App Password:
   - Go to https://myaccount.google.com/apppasswords
   - Select "Mail" and "Windows Computer" (or your device)
   - Google will show a 16-character password
3. Add to your `.env` file:
   ```
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your_email@gmail.com
   SMTP_PASSWORD=your_16_char_app_password
   ```
4. Restart the app. Password resets will now send emails via Gmail SMTP.

### Option 2: Gmail OAuth2 (More Secure, No Password Storage)

If SMTP credentials are not provided, the app will attempt to use Google OAuth2 to send emails. This requires a one-time setup:

#### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click the project dropdown at the top and select **New Project**
3. Enter a name (e.g., "LearnerNet") and click **Create**
4. Wait for the project to be created, then select it

#### Step 2: Enable the Gmail API

1. In the Cloud Console, go to **APIs & Services** > **Library**
2. Search for "Gmail API"
3. Click it and then click **Enable**

#### Step 3: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **OAuth client ID**
3. If prompted, click **Configure Consent Screen**:
   - Choose **External** for User Type
   - Fill in required fields (App name, User support email, Developer contact)
   - Under **Scopes**, add `https://www.googleapis.com/auth/gmail.send` (click **Add or remove scopes** > search "send" > check it)
   - Click **Save and Continue** through remaining screens
4. Back on the Credentials page, click **Create Credentials** > **OAuth client ID**
5. Select **Desktop app** and click **Create**
6. A dialog will show your **Client ID** and **Client Secret**. Copy both.

#### Step 4: Get a Refresh Token

You need to authorize the app once to get a refresh token:

1. Create a temporary token-fetch script in the project folder (`get_refresh_token.py`):
   ```python
   import os
   from google.auth.oauthlib.flow import InstalledAppFlow
   
   SCOPES = ['https://www.googleapis.com/auth/gmail.send']
   CLIENT_ID = 'YOUR_CLIENT_ID'
   CLIENT_SECRET = 'YOUR_CLIENT_SECRET'
   
   # Create the OAuth2 flow
   flow = InstalledAppFlow.from_client_config(
       {
           "installed": {
               "client_id": CLIENT_ID,
               "client_secret": CLIENT_SECRET,
               "auth_uri": "https://accounts.google.com/o/oauth2/auth",
               "token_uri": "https://oauth2.googleapis.com/token",
           }
       },
       SCOPES,
   )
   
   # This will open a browser for you to authorize
   creds = flow.run_local_server(port=0)
   
   # Print the refresh token
   print(f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}")
   print(f"GOOGLE_CLIENT_ID={CLIENT_ID}")
   print(f"GOOGLE_CLIENT_SECRET={CLIENT_SECRET}")
   print(f"GOOGLE_OAUTH_USER=your_email@gmail.com")
   ```

2. Replace `YOUR_CLIENT_ID`, `YOUR_CLIENT_SECRET`, and ask for the email:
   ```bash
   python get_refresh_token.py
   ```

3. A browser window will open. Sign in with your Google account and grant permission.

4. The script will print your `GOOGLE_REFRESH_TOKEN` and other values. Copy them.

#### Step 5: Add to `.env`

```
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REFRESH_TOKEN=your_refresh_token
GOOGLE_OAUTH_USER=your_email@gmail.com
```

5. Restart the app. Password resets will now send via Gmail API using OAuth2.

#### Cleanup

After getting the refresh token, you can delete `get_refresh_token.py`:
```bash
rm get_refresh_token.py
```

---

## Features

- Register and sign in with a secure password
- Create posts, comments, and learning resources
- Like posts and track discussion activity
- AI research assistant for summaries and study guidance
- Profile page showing your contributions and activity
- Password reset via email (SMTP or Gmail OAuth)
- Admin panel to view registered users

## Notes

- The app stores data in `social_learning.db` using SQLite.
- Replace `YOUR_KEY` with a valid OpenAI API key for the AI assistant.
- Password reset tokens are logged server-side in `password_reset_tokens.log` (not shown to users).
- Admins can view active reset tokens in the Admin panel by checking "Show password reset tokens (sensitive)".
