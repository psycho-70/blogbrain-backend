# Create a file called download_db.py
import urllib.request
import tarfile
import os

print("📥 Downloading GeoLite2 Country database...")

# Download the database (you need to sign up for a free license key at maxmind.com)
# For testing, you can use this direct link (might be outdated)
url = "https://geolite.maxmind.com/download/geoip/database/GeoLite2-Country.tar.gz"
filename = "GeoLite2-Country.tar.gz"

try:
    # Download
    urllib.request.urlretrieve(url, filename)
    print("✅ Download complete!")
    
    # Extract
    with tarfile.open(filename, 'r:gz') as tar:
        tar.extractall()
    print("✅ Extraction complete!")
    
    # Find and rename the .mmdb file
    for item in os.listdir('.'):
        if item.startswith('GeoLite2-Country_') and os.path.isdir(item):
            db_file = os.path.join(item, 'GeoLite2-Country.mmdb')
            if os.path.exists(db_file):
                # Move to current directory
                os.rename(db_file, 'GeoLite2-Country.mmdb')
                # Remove extracted folder
                import shutil
                shutil.rmtree(item)
                break
    
    # Clean up
    os.remove(filename)
    print("✅ GeoLite2 database ready!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nPlease download manually from:")
    print("https://dev.maxmind.com/geoip/geolite2-free-geolocation-data")