import os
from dotenv import load_dotenv
import sys

# Get the directory containing the script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Debug: Print current directory and .env path
print(f"Current directory: {script_dir}")
print(f"Looking for .env file at: {os.path.join(script_dir, '.env')}")

# Load environment variables from .env file
load_dotenv(os.path.join(script_dir, '.env'))

# Get API key with error checking
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
if not GOOGLE_MAPS_API_KEY:
    print("Error: GOOGLE_MAPS_API_KEY not found in .env file")
    sys.exit(1)

print(f"Loaded API key: {GOOGLE_MAPS_API_KEY}")  # Debug print

# Map configuration
DEFAULT_CENTER = {
    'lat': 7.8731,
    'lng': 80.7718
}
DEFAULT_ZOOM = 8 