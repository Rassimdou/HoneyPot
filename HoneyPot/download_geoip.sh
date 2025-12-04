#!/bin/bash

echo "[*] === GeoIP Auto Installer ==="

# Create folder if missing
mkdir -p geoip

# MaxMind license key assignment (FIXED: No spaces around =)
# NOTE: Your actual key is used here.
LICENSE_KEY=""

# --- REMOVED THE FAULTY IF CHECK ---

# Downloading GeoLite2 City
echo "[*] Downloading GeoLite2 City..."
# -O: Save to a specific file name
wget -O geoip/GeoLite2-City.tar.gz \
"https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-City&license_key=$LICENSE_KEY&suffix=tar.gz"

# Downloading GeoLite2 ASN (FIXED: Added LICENSE_KEY parameter)
echo "[*] Downloading GeoLite2 ASN..."
wget -O geoip/GeoLite2-ASN.tar.gz \
"https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-ASN&license_key=$LICENSE_KEY&suffix=tar.gz"

echo "[*] Extracting City DB..."
# Extract to the geoip directory
tar -xzf geoip/GeoLite2-City.tar.gz -C geoip
# Move the GeoLite2-City.mmdb file out of the temporary folder and into geoip/
mv geoip/GeoLite2-City_*/GeoLite2-City.mmdb geoip/ 2>/dev/null

echo "[*] Extracting ASN DB..."
tar -xzf geoip/GeoLite2-ASN.tar.gz -C geoip
mv geoip/GeoLite2-ASN_*/GeoLite2-ASN.mmdb geoip/ 2>/dev/null

# Cleanup (FIXED: Corrected typo from 'goip' to 'geoip')
rm -rf geoip/*_*/ geoip/*.tar.gz

echo "[+] GeoIP Databases Installed Successfully!"
echo "[+] Files created:"
echo "   - geoip/GeoLite2-City.mmdb"
echo "   - geoip/GeoLite2-ASN.mmdb"