python -m venv venv
.\venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium
echo "Virtual environment setup complete. Activate it with '.\venv\Scripts\activate'"
