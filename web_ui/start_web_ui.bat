@echo off
echo ========================================
echo  Starting Sales Agent Web UI Server
echo ========================================
echo.
echo Installing dependencies...
pip install Flask flask-cors --quiet
echo.
echo Starting Flask server...
echo Server will be available at: http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.
python api_server.py
