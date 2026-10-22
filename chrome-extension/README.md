# AI Advisor Job Agent – Chrome MV3 Extension

## Install (developer mode)

1. Open `chrome://extensions`
2. Enable **Developer mode**
3. **Load unpacked** → select this `chrome-extension` folder
4. Pin the extension
5. Open the popup → set your Agent URL (default `http://localhost:8000`)
6. On any job page, click the extension → **Open import in Job Agent**

You must be logged into the web app. The extension opens `/jobs/clip` with title, URL, and page text pre-filled.

## Permissions

- `activeTab` / scripting: read the current job page title and text
- `storage`: remember your Agent URL
- Host access: your Job Agent instance + job boards

## Production

Point Agent URL at your deployed host, e.g. `https://jobs.yourdomain.com`.
