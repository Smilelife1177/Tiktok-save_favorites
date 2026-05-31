# 📱 TikTok Favorites Downloader (v1.0.0)

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A professional tool for automated downloading of your bookmarked videos ("Favorites") from TikTok. No more manual token manipulation — everything works via browser automation.

---

## ✨ Features

- **🚀 Smart Authorization:** Uses Playwright to save your session. Log in once and forget about it.
- **🔍 Automated Scanning:** The script automatically finds the "Favorites" tab, scrolls through it, and collects links.
- **🎬 High Quality:** Downloads via `yt-dlp` in the best available quality.
- **📂 Organization:** Videos are automatically organized into folders based on the creators' usernames.
- **🛡️ Security:** Your data (cookies and sessions) are stored locally and never shared with third parties.

---

## 🛠️ Installation and Setup

### 1. Preparation
Ensure you have **Python 3.8+** installed.

### 2. Automated Setup
We have prepared a script for Windows that handles everything for you:
```powershell
.\setup_venv.ps1
```
*This will create a virtual environment, install dependencies, and required Playwright components.*

### 3. Activate Environment
```powershell
.\venv\Scripts\activate
```

---

## 🚀 Usage

Run the application with the following command:
```powershell
python main.py your_nickname --count 50
```

### Workflow:
1. **First Run:** A browser window will open. If you are not authorized — log into your TikTok account.
2. **Data Collection:** The script will navigate to the "Favorites" page and start collecting links. If the automation doesn't trigger — simply click the "Favorites" tab manually and scroll down.
3. **Downloading:** After collecting the requested number of links, the browser will close, and video downloading will begin in the `downloads/` folder.

---

## 📂 Project Structure

```text
├── src/                # Source code
│   ├── scraper.py      # Playwright logic (link collection)
│   ├── downloader.py   # Download logic (yt-dlp)
│   └── main.py         # Main CLI interface
├── main.py             # Entry point
├── setup_venv.ps1      # Quick setup script
└── requirements.txt    # Dependencies
```

---

## ⚠️ Disclaimer

This project is created solely for personal use and educational purposes. The author is not responsible for any violation of TikTok's terms of service. Use this tool responsibly.

---

## 📄 License

This project is distributed under the MIT License. See the [LICENSE](LICENSE) file for details.

---
*Created with Gemini CLI*
