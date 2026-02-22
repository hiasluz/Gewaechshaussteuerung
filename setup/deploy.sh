#!/bin/bash
# Deployment Script für Per-Gate Auto Mode

# Konfiguration
SERVER="gewaechshaus.luzernenhof.de"
USER="your_ssh_user"  # Anpassen!
API_PATH="/path/to/api"  # Anpassen!
WEB_PATH="/path/to/web"  # Anpassen!
PI_USER="luz"
PI_HOST="luzPi"
PI_PATH="/home/luz/greenhouse"  # Anpassen falls anders

echo "=========================================="
echo "🚀 Deploying Per-Gate Auto Mode"
echo "=========================================="

# 1. API-Dateien auf Server hochladen
echo ""
echo "📤 Uploading API files to server..."
scp api/index.php ${USER}@${SERVER}:${API_PATH}/

# Schema wurde bereits ausgeführt, daher auskommentiert
# scp api/schema_auto_mode.sql ${USER}@${SERVER}:${API_PATH}/

echo "✅ API files uploaded"

# 2. Web-Dateien auf Server hochladen
echo ""
echo "📤 Uploading web files to server..."
scp web/index.html ${USER}@${SERVER}:${WEB_PATH}/
scp web/assets/auto-toggle-styles.css ${USER}@${SERVER}:${WEB_PATH}/assets/
scp web/assets/gate-auto-toggle.js ${USER}@${SERVER}:${WEB_PATH}/assets/
scp web/assets/app.js ${USER}@${SERVER}:${WEB_PATH}/assets/

echo "✅ Web files uploaded"

# 3. Pi-Client Dateien auf Raspberry Pi hochladen
echo ""
echo "📤 Uploading Pi client files..."
scp greenhouse_web.py ${PI_USER}@${PI_HOST}:${PI_PATH}/
scp greenhouse_api_client.py ${PI_USER}@${PI_HOST}:${PI_PATH}/

echo "✅ Pi client files uploaded"

# 4. Pi-Client neu starten
echo ""
echo "🔄 Restarting Pi client..."
ssh ${PI_USER}@${PI_HOST} "sudo systemctl restart greenhouse-client"

echo "✅ Pi client restarted"

echo ""
echo "=========================================="
echo "✅ Deployment completed!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Test frontend toggles"
echo "2. Test API endpoints"
echo "3. Monitor Pi client logs: ssh ${PI_USER}@${PI_HOST} 'sudo journalctl -u greenhouse-client -f'"
