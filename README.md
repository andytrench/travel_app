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

## Project Structure

- `travel.py`: Main application file
- `utils.py`: Utility functions and API integrations
- `config.py`: Configuration settings
- `templates/`: JSON template files
  - `country_template.json`: Template for country data
  - `locations_template.json`: Template for location data
  - `score_template.json`: Template for scoring data
- `data/`: Generated data directory (created on first run)