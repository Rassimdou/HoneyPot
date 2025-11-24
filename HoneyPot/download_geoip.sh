#!/bin/bash

echo "[*] === GeoIP Auto Installer ==="
#Create folder if missing
mkdir -p geoip

# maxMind license key 
LICENSE_KEY = "HERE"

if ["$LICENSE_KEY"="here also" ]; then
    echo "[!] ERROR: you must set your MaxMind LICENSE_KEY in downlaod_geoip.sh"
    exit 1
fi


echo "[*] Downloading GeoLite2 City..."
wget -o geoip/GeoLite2-City.tar.gz \
"https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-City&license_key=$LICENSE_KEY&suffix=tar.gz"

echo "[*] Downlaoding GeoLite2 ASN..."
wget -O geoip/GeoLite2-ASN.tar.gz \
"https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-ASN&license_key=$LICENSE_KEY&suffix=tar.gz"

echo "[*] Extracting City DB..."
tar -xzf geoip/GeoLite2-City.tar.gz -C geoip
mv geoip/GeoLite2-City_*/GeoLite2-City.mmdb geoip/ 2>/dev/null

echo "[*] Extracting ASN DB..."
tar -xzf geoip/GeoLite2-ASN.tar.gz -C geoip
mv geoip/GeoLite2-ASN_*/GeoLite2-ASN.mmdb geoip/ 2>/dev/null

#cleanup 
rm -rf goip/*_*/ geoip/*.tar.gz

echo "[+] GeoIP Databases Installed Successfully!"
echo "[+] Files created:"
echo "   - geoip/GeoLite2-City.mmdb"
echo "   - geoip/GeoLite2-ASN.mmdb"