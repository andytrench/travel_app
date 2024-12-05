# Travel Location Analyzer

A Python application that helps analyze and visualize travel locations with detailed scoring and mapping capabilities.

## Features

- Interactive map visualization with Google Maps integration
- Detailed location scoring and analysis
- Support for multiple data sources (Claude AI, Perplexity, Google Places)
- Rich location details including ratings, photos, and business information
- Dark theme UI with PyQt6

## Prerequisites

- Python 3.8+
- PyQt6
- Google Maps API key
- Anthropic API key (for Claude AI)
- Perplexity API key

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/travel-location-analyzer.git
cd travel-location-analyzer
```

2. Create and activate a virtual environment:

```bash
# On macOS/Linux:
python -m venv venv
source venv/bin/activate

# On Windows:
python -m venv venv
venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set up your environment:
   - Copy `.env.template` to `.env`
   - Add your API keys to `.env`:

```bash
cp .env.template .env
```
Then edit `.env` with your API keys:
```
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
PERPLEXITY_API_KEY=your_perplexity_api_key_here
```

## Usage

1. Start the application:

```bash
python travel.py
```

2. Using the Interface:
   - **Country Selection**: Use the dropdown menu to select a location
   - **Generate Locations**: Click "Generate Locations" to analyze a new location
   - **View Details**: Navigate between tabs:
     - Country Overview: General information and basic scores
     - Detailed Scores: In-depth analysis of various categories
     - Locations: Specific recommended locations with details

3. Generating New Locations:
   - Click "Generate Locations"
   - Enter the main location (e.g., "Tokyo, Japan")
   - Specify a focus keyword (e.g., "digital nomad", "family friendly")
   - Set the search radius and number of results
   - Click OK to generate analysis

4. Map Features:
   - Click markers to view location details
   - Use Street View for immersive location exploration
   - Toggle between Map and Satellite views
   - Zoom and pan for better navigation

5. Detailed Ratings:
   - View comprehensive scores for various categories
   - See subcategory breakdowns with descriptions
   - Read detailed notes and recommendations
   - Generate new ratings analyses for locations

## Project Structure

- `travel.py`: Main application file
- `utils.py`: Utility functions and API integrations
- `config.py`: Configuration settings
- `templates/`: JSON template files
  - `country_template.json`: Template for country data
  - `locations_template.json`: Template for location data
  - `score_template.json`: Template for scoring data
- `data/`: Generated data directory (created on first run)

## API Usage Notes

1. Google Maps API:
   - Used for location data, coordinates, and map display
   - Requires billing account with Google Cloud
   - Enable Maps JavaScript API, Places API, and Street View API

2. Claude AI (Anthropic):
   - Used for detailed location analysis
   - Free tier available for testing
   - Rate limits apply based on your plan

3. Perplexity:
   - Used for real-time location information
   - Requires API access (currently in beta)
   - Rate limits apply

## Troubleshooting

Common issues and solutions:

1. Map not loading:
   - Verify Google Maps API key is correct
   - Check if billing is enabled on Google Cloud
   - Ensure required APIs are enabled

2. Generation fails:
   - Verify API keys are correct in .env
   - Check API rate limits
   - Look for error messages in console output

3. UI issues:
   - Ensure PyQt6 and WebEngine are installed correctly
   - Try reinstalling dependencies
   - Check system requirements for PyQt6

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Google Maps Platform for location services
- Anthropic's Claude AI for analysis
- Perplexity API for real-time data
- PyQt6 for the user interface