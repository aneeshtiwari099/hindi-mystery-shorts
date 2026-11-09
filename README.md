# Automated Daily Hindi Mystery YouTube Shorts (100% Free)

This project autonomously creates, narrates, renders, and uploads a daily serialized Hindi mystery Short to YouTube using GitHub Actions.

It uses:
- **Google Gemini API** (100% Free via Google AI Studio) for story generation.
- **Edge-TTS** (100% Free neural voiceover in Hindi: `hi-IN-MadhurNeural`).
- **MoviePy & Pillow** for automated rendering & subtitles.
- **YouTube Data API v3** for automated upload.

---

## 1. Get Free Google Gemini API Key

1. Go to **[aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)**.
2. Sign in with any Google account.
3. Click **"Create API key"** and copy it.

---

## 2. Setup YouTube Data API & OAuth Credentials

1. Go to **[Google Cloud Console](https://console.cloud.google.com/)** and create a project.
2. Enable **YouTube Data API v3**.
3. Under **APIs & Services > OAuth consent screen**, select **External**, add your email under **Test Users**.
4. Under **APIs & Services > Credentials > Create Credentials > OAuth client ID**, select **Desktop app**.
5. Copy your **Client ID** and **Client Secret**.

---

## 3. GitHub Secrets Needed

Add these to your repo secrets at:
`https://github.com/aneeshtiwari099/hindi-mystery-shorts/settings/secrets/actions`

| Secret Name | Description |
|---|---|
| `GEMINI_API_KEY` | Free Google Gemini API Key |
| `YT_CLIENT_ID` | Google OAuth Client ID |
| `YT_CLIENT_SECRET` | Google OAuth Client Secret |
| `YT_REFRESH_TOKEN` | YouTube OAuth Refresh Token |
