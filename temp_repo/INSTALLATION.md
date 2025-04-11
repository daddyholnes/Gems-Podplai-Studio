# 🚀 Installation Guide for AI Chat Studio

This guide provides detailed instructions for setting up and running the AI Chat Studio application with ease.

## 💻 One-Click Installation on Replit

The fastest way to get AI Chat Studio running is through Replit:

1. **Click the Run on Replit button:**  
   [![Run on Replit](https://replit.com/badge/github/daddyholnes/Gems-Podplai-Studio)](https://replit.com/github/daddyholnes/Gems-Podplai-Studio)

2. **Set up API keys as Replit Secrets:**
   - Click on "Secrets" in the tools panel
   - Add the following keys (only add the ones you plan to use):
     ```
     OPENAI_API_KEY=your_openai_api_key
     ANTHROPIC_API_KEY=your_anthropic_api_key
     GEMINI_API_KEY=your_gemini_api_key
     PERPLEXITY_API_KEY=your_perplexity_api_key
     ```

3. **Run the application:**
   - Click the "Run" button
   - Replit will automatically install all required dependencies
   - Your AI Chat Studio will be accessible at the provided URL

## 🖥️ Local Installation

### Prerequisites

- Python 3.11 or higher
- Audio capabilities require:
  - Windows: No additional steps
  - macOS: PortAudio (`brew install portaudio`)
  - Linux: Python development files and PortAudio (`sudo apt-get install python3-dev portaudio19-dev`)

### Step 1: Clone the Repository

```bash
git clone https://github.com/daddyholnes/Gems-Podplai-Studio.git
cd Gems-Podplai-Studio
```

### Step 2: Set Up a Virtual Environment

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
# Install all required packages
pip install -r requirements-github.txt
```

### Step 4: Set Up Environment Variables

Create a `.env` file in the root directory:

```
# Required API Keys (only add the ones you plan to use)
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
GEMINI_API_KEY=your_gemini_api_key
PERPLEXITY_API_KEY=your_perplexity_api_key

# PostgreSQL Database (Optional - will fall back to JSON if not configured)
DATABASE_URL=postgresql://username:password@hostname:port/database
```

### Step 5: Create Streamlit Configuration

Create a `.streamlit` directory and add a `config.toml` file:

```bash
mkdir -p .streamlit
```

Add the following content to `.streamlit/config.toml`:

```toml
[server]
headless = true
address = "0.0.0.0"
port = 5000

[theme]
primaryColor = "#7B39E9"  # Amazon Q Purple theme
backgroundColor = "#1E1E1E"
secondaryBackgroundColor = "#272727"
textColor = "#FFFFFF"
```

### Step 6: Service Account for Vertex AI (Optional)

If you want to use Google Vertex AI features:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Enable the Vertex AI API
4. Create a service account with Vertex AI User role
5. Create and download a JSON key for the service account
6. Save the key as `service-account-key.json` in the project root directory

### Step 7: Run the Application

```bash
streamlit run app.py
```

The application will be accessible at `http://localhost:5000`

## 📱 Mobile Device Setup

For the best experience on mobile devices:

1. Follow the local installation steps above
2. When running the application, use your local network IP:
   ```bash
   streamlit run app.py --server.address=0.0.0.0 --server.port=5000
   ```
3. Access the application from your mobile device by navigating to `http://your-computer-ip:5000`

## 🔧 Using PostgreSQL for Chat Persistence

The application will automatically use PostgreSQL if environment variables are available:

1. Install PostgreSQL on your system
2. Create a new database for the application
3. Set up the environment variables in your `.env` file:
   ```
   DATABASE_URL=postgresql://username:password@hostname:port/database
   # Or individual parameters:
   PGUSER=username
   PGPASSWORD=password
   PGHOST=hostname
   PGPORT=5432
   PGDATABASE=database_name
   ```

If PostgreSQL is not available, the application will automatically fall back to JSON file storage.

## 🔊 Voice Command Setup

Voice commands are available out of the box if your system has a working microphone:

1. Enable voice commands in the application UI
2. Allow microphone access when prompted by your browser
3. Use voice commands such as "start new chat" or "clear conversation"

## 🛠️ Troubleshooting

### Audio Recording Issues

- **Windows**: Install the latest version of Visual C++ Redistributable
- **macOS**: Install PortAudio with `brew install portaudio`
- **Linux**: Install required packages with `sudo apt-get install python3-dev portaudio19-dev`

### API Connection Issues

- Verify your API keys are correct and active
- Check for any usage limits or restrictions on your API accounts
- Ensure your environment variables are properly configured

### Database Connection Issues

- Check that your PostgreSQL server is running
- Verify connection credentials and database existence
- Ensure the database user has appropriate permissions

## 🔒 Authentication Setup

The application supports Google OAuth authentication to protect your chat interface:

### Setting Up Google OAuth

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Go to "APIs & Services" > "OAuth consent screen"
   - Set user type (External or Internal)
   - Fill in app name, support email, and developer contact info
   - Add scopes for "userinfo.email" and "userinfo.profile"
   - Add your test users (can include your own email)
4. Go to "Credentials" > "Create Credentials" > "OAuth client ID"
   - Application type: Web application
   - Name: "AI Chat Studio" (or your preferred name)
   - Authorized JavaScript origins: Leave empty
   - Authorized redirect URIs: 
     - `https://dartopia.uk`
     - `https://podplay.replit.app` 
     - `http://localhost:5000` (if needed for development)
5. Save your Client ID and Client Secret

### Configure Authentication in Your App

Add the following to your `.env` file or Replit Secrets:

```
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
OAUTH_REDIRECT_URI=https://dartopia.uk
APPROVED_EMAILS=your_email@example.com,another_email@example.com
ADMIN_EMAILS=your_admin_email@example.com
```

### Authentication Development Bypass

For development purposes, you can bypass authentication by setting:

```bash
# Run with authentication bypass for development
BYPASS_AUTH=true streamlit run app.py
```

### Debugging OAuth Issues

If you encounter OAuth authentication issues:

1. Access the built-in debug page at `/debug_oauth`
2. Test different redirect URIs to identify the correct configuration
3. Verify your Google Cloud Console settings match your application settings
4. Check the detailed error messages on the debug page

## 🔐 Security Best Practices

- Never commit sensitive files like `.env` or service account keys to Git
- Use environment variables or secrets management for API keys
- Regularly rotate API keys and other credentials
- Keep dependencies updated to patch security vulnerabilities
- Always use Google OAuth in production for account protection
- Restrict access to approved email addresses only

## 🌐 Deployment Options

### Replit (Recommended)

- Automatically handles dependencies and provides a public URL
- Built-in secrets management for API keys
- Easy scaling and sharing

### Streamlit Cloud

- Visit [Streamlit Sharing](https://streamlit.io/cloud)
- Connect your GitHub repository
- Configure secrets in the Streamlit Cloud dashboard

### Heroku

- Install the Heroku CLI
- Create a `Procfile` with: `web: streamlit run app.py --server.port=$PORT`
- Deploy with `heroku create` and `git push heroku main`

## 🎉 Start Chatting!

After installation:

1. Select your desired AI model from the dropdown
2. Choose your preferred theme
3. Start chatting with state-of-the-art AI models
4. Explore multimodal features like image upload and audio recording

Enjoy your AI Chat Studio experience!