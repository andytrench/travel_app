import os
import json
import logging
from typing import Dict, Tuple
import anthropic
import requests
from dotenv import load_dotenv
import re
import googlemaps

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')

class LocationGenerator:
    def __init__(self):
        logger.debug("Initializing LocationGenerator")
        self.template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
        self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        
        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        logger.debug(f"Initialized data directory at: {self.data_dir}")
        
        # Load templates with error handling
        self.score_template = {}
        self.locations_template = {}
        
        try:
            # Try to load score template
            score_template_path = os.path.join(self.template_dir, 'score_template.json')
            if os.path.exists(score_template_path):
                with open(score_template_path) as f:
                    self.score_template = json.load(f)
            else:
                logger.warning(f"Score template not found at {score_template_path}")
                # Create default score template
                self.score_template = {
                    "location": {"name": "", "region": "", "country": ""},
                    "scores": {},
                    "summary": {"total_score": 0, "strengths": [], "weaknesses": [], "overall_notes": ""}
                }
        except Exception as e:
            logger.error(f"Error loading score template: {e}")
            
        try:
            # Try to load locations template
            locations_template_path = os.path.join(self.template_dir, 'locations_template.json')
            if os.path.exists(locations_template_path):
                with open(locations_template_path) as f:
                    self.locations_template = json.load(f)
            else:
                logger.warning(f"Locations template not found at {locations_template_path}")
                # Create default locations template
                self.locations_template = {
                    "recommended_locations": [
                        {
                            "name": "Example Location",
                            "region": "Example Region",
                            "coords": {"lat": 0.0, "lng": 0.0},
                            "brief": "Example description",
                            "formatted_address": "",
                            "place_id": "",
                            "photo_url": None,
                            "rating": None,
                            "user_ratings_total": None,
                            "business_status": None,
                            "price_level": None
                        }
                    ]
                }
        except Exception as e:
            logger.error(f"Error loading locations template: {e}")

        # Initialize the clients
        self.anthropic_client = anthropic.Client(api_key=ANTHROPIC_API_KEY)
        self.perplexity_headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json",
        }
        self.perplexity_url = "https://api.perplexity.ai/chat/completions"

        # Initialize Google Maps client
        self.gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

    def _get_perplexity_response(self, prompt: str) -> str:
        logger.debug("Sending prompt to Perplexity")
        try:
            payload = {
                "model": "llama-3.1-sonar-small-128k-online",  # Updated to use sonar model
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a location research expert. Provide accurate, real-world information about locations, including exact coordinates and verified details. Format responses as JSON when requested."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.1,  # Keep low temperature for factual responses
                "max_tokens": 4000
            }

            response = requests.post(
                self.perplexity_url,
                headers=self.perplexity_headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            logger.debug(f"Perplexity response: {result}")
            
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                logger.debug(f"Extracted content: {content}")
                return content
            else:
                raise ValueError("No content in Perplexity response")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Perplexity API request failed: {str(e)}")
            logger.error(f"Response content: {e.response.content if hasattr(e, 'response') else 'No response content'}")
            raise
        except Exception as e:
            logger.error(f"Error getting Perplexity response: {e}")
            raise

    def _get_claude_response(self, prompt: str) -> str:
        logger.debug("Sending prompt to Claude")
        try:
            response = self.anthropic_client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=4000,
                temperature=0.7,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            logger.debug(f"Claude response: {response.content[0].text}")
            return response.content[0].text
        except Exception as e:
            logger.error(f"Error getting Claude response: {e}")
            raise

    def _get_location_coordinates(self, location_name: str, region: str) -> Dict:
        """Get accurate coordinates and details using Google Places API"""
        logger.debug(f"Getting coordinates and details for {location_name} in {region}")
        try:
            # Use Text Search with more specific parameters
            text_search_url = "https://places.googleapis.com/v1/places:searchText"
            
            payload = {
                "textQuery": f"{location_name}, {region}",
                "languageCode": "en",
                "maxResultCount": 1,
                "locationBias": {
                    "circle": {
                        "center": {
                            "latitude": 0,
                            "longitude": 0
                        },
                        "radius": 20000.0
                    }
                }
            }
            
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
                "X-Goog-FieldMask": (
                    "places.id,places.displayName,places.formattedAddress,"
                    "places.location,places.types,places.photos,"
                    "places.rating,places.userRatingCount,places.businessStatus,places.priceLevel"
                )
            }
            
            response = requests.post(
                text_search_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('places'):
                place = result['places'][0]
                
                # Get additional details including photos
                place_id = place['id']
                details_url = f"https://places.googleapis.com/v1/places/{place_id}"
                
                details_response = requests.get(
                    details_url,
                    headers={
                        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
                        "X-Goog-FieldMask": (
                            "id,formattedAddress,location,types,displayName,"
                            "photos,rating,userRatingCount,businessStatus,priceLevel"
                        )
                    }
                )
                details_response.raise_for_status()
                place_details = details_response.json()
                
                # Get photo if available
                photo_url = None
                if place_details.get('photos'):
                    photo = place_details['photos'][0]
                    photo_url = (
                        f"https://places.googleapis.com/v1/{photo['name']}/media"
                        f"?key={GOOGLE_MAPS_API_KEY}&maxHeightPx=400"
                    )
                
                return {
                    "lat": place_details['location']['latitude'],
                    "lng": place_details['location']['longitude'],
                    "formatted_address": place_details['formattedAddress'],
                    "place_id": place_details['id'],
                    "name": place_details['displayName']['text'],
                    "types": place_details.get('types', []),
                    "photo_url": photo_url,
                    "rating": place_details.get('rating'),
                    "user_ratings_total": place_details.get('userRatingCount'),
                    "business_status": place_details.get('businessStatus'),
                    "price_level": place_details.get('priceLevel')
                }
            else:
                logger.warning(f"No results found for {location_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting details for {location_name}: {e}")
            logger.error(f"Response content: {e.response.content if hasattr(e, 'response') else 'No response content'}")
            return None

    def _process_locations_data(self, locations_data: Dict) -> Dict:
        """Process locations data to add accurate coordinates and details"""
        processed_locations = {"recommended_locations": []}
        
        for location in locations_data.get("recommended_locations", []):
            # Get accurate coordinates and details from Google
            details = self._get_location_coordinates(location['name'], location['region'])
            
            if details:
                location.update({
                    'coords': {
                        "lat": details['lat'],
                        "lng": details['lng']
                    },
                    'formatted_address': details['formatted_address'],
                    'place_id': details['place_id'],
                    'photo_url': details['photo_url'],
                    'rating': details['rating'],
                    'user_ratings_total': details['user_ratings_total'],
                    'business_status': details['business_status'],
                    'price_level': details['price_level']
                })
                
                processed_locations['recommended_locations'].append(location)
            else:
                logger.warning(f"Skipping location {location['name']} - details not found")

        return processed_locations

    def _get_basic_location_info(self, 
                                main_location: str, 
                                focus_keyword: str, 
                                distance_km: int, 
                                num_results: int) -> Dict:
        logger.debug(f"Getting basic location info for {main_location}")
        
        # Update prompts to emphasize real-world data
        country_prompt = f"""
        Create a country profile for {main_location} focusing on {focus_keyword}.
        Use only verified, real-world information.
        Include actual businesses, locations, and accurate coordinates.
        Follow this exact JSON structure:
        {{
            "location": {{
                "name": "{main_location}",
                "region": "<verified region>",
                "country": "<verified country>"
            }},
            "scores": {{
                "freedom": <1-5>,
                "environment": <1-5>,
                "culture": <1-5>,
                "healthcare": <1-5>,
                "education": <1-5>,
                "living_costs": <1-5>,
                "safety": <1-5>,
                "taxation": <1-5>,
                "internet_access": <1-5>,
                "tolerance": <1-5>,
                "outdoors": <1-5>
            }},
            "summary": {{
                "total_score": <sum of all scores>,
                "strengths": [
                    "<verified strength 1>",
                    "<verified strength 2>",
                    "<verified strength 3>",
                    "<verified strength 4>"
                ],
                "weaknesses": [
                    "<verified weakness 1>",
                    "<verified weakness 2>"
                ],
                "overall_notes": "<factual summary paragraph>"
            }}
        }}
        Format as ```json```.
        """

        locations_prompt = f"""
        List {num_results} verified, real-world locations within {distance_km}km of {main_location} that are great for {focus_keyword}.
        Only include locations that actually exist with accurate coordinates.
        Follow this exact JSON structure:
        {{
            "recommended_locations": [
                {{
                    "name": "<verified location name>",
                    "region": "<verified region name>",
                    "coords": {{
                        "lat": <exact latitude>,
                        "lng": <exact longitude>
                    }},
                    "brief": "<factual description>"
                }}
            ]
        }}
        Ensure all coordinates and details are accurate. Format as ```json```.
        """

        try:
            # Get country data from Perplexity
            country_response = self._get_perplexity_response(country_prompt)
            country_match = re.search(r'```json(.*?)```', country_response, re.DOTALL)
            if country_match:
                country_data = json.loads(country_match.group(1).strip())
            else:
                raise ValueError("Could not extract JSON from country response")

            # Get locations from Perplexity
            locations_response = self._get_perplexity_response(locations_prompt)
            locations_match = re.search(r'```json(.*?)```', locations_response, re.DOTALL)
            if locations_match:
                raw_locations_data = json.loads(locations_match.group(1).strip())
                # Process locations to get accurate coordinates
                locations_data = self._process_locations_data(raw_locations_data)
            else:
                raise ValueError("Could not extract JSON from locations response")

            return {
                "country_data": country_data,
                "locations_data": locations_data
            }

        except Exception as e:
            logger.error(f"Error in _get_basic_location_info: {e}")
            raise

    def _save_basic_info(self, basic_info: Dict, main_location: str, focus_keyword: str) -> Tuple[str, str]:
        logger.debug("Saving basic location info to files")
        # Clean up filenames by replacing spaces with underscores
        clean_location = main_location.lower().replace(' ', '_')
        clean_keyword = focus_keyword.lower().replace(' ', '_')
        
        country_filename = f"country_{clean_location}_{clean_keyword}.json"
        locations_filename = f"locations_{clean_location}_{clean_keyword}.json"
        
        with open(os.path.join(self.data_dir, country_filename), 'w') as f:
            json.dump(basic_info['country_data'], f, indent=2)
        
        with open(os.path.join(self.data_dir, locations_filename), 'w') as f:
            json.dump(basic_info['locations_data'], f, indent=2)
        
        logger.debug(f"Saved country data to {country_filename} and locations data to {locations_filename}")
        return country_filename, locations_filename

    def _get_detailed_info(self, basic_info: Dict) -> Dict:
        logger.debug("Getting detailed scores and descriptions for locations")
        # Simply return the basic_info since it already contains all necessary data
        # and is properly formatted
        return basic_info

    def _update_files_with_details(self, detailed_info: Dict, country_filename: str, locations_filename: str):
        logger.debug("Updating files with detailed information")
        with open(os.path.join(self.data_dir, country_filename), 'w') as f:
            json.dump(detailed_info['country_data'], f, indent=2)
        
        with open(os.path.join(self.data_dir, locations_filename), 'w') as f:
            json.dump(detailed_info['locations_data'], f, indent=2)
        logger.debug("Files updated successfully")

    def generate_locations(self, 
                         main_location: str, 
                         focus_keyword: str, 
                         distance_km: int, 
                         num_results: int,
                         progress_callback=None) -> tuple[str, str]:
        logger.info(f"Generating locations for {main_location} with focus on {focus_keyword}")
        try:
            # Step 1: Identify locations
            logger.info("Step 1: Identifying locations and coordinates...")
            basic_info = self._get_basic_location_info(
                main_location, focus_keyword, distance_km, num_results
            )
            
            # Update progress with country data
            if progress_callback:
                progress_callback("country_data", basic_info["country_data"])
            
            # Step 2: Save basic info and update map
            logger.info("Step 2: Saving basic info and updating map...")
            country_filename, locations_filename = self._save_basic_info(
                basic_info, main_location, focus_keyword
            )
            
            # Update progress with locations data
            if progress_callback:
                progress_callback("locations_data", basic_info["locations_data"])
            
            # Step 3: Add scores and details
            logger.info("Step 3: Adding scores and additional details...")
            detailed_info = self._get_detailed_info(basic_info)
            
            # Step 4: Update tables with details
            logger.info("Step 4: Updating tables with detailed information...")
            self._update_files_with_details(
                detailed_info, country_filename, locations_filename
            )
            
            logger.info("Location generation completed successfully")
            return country_filename, locations_filename
            
        except Exception as e:
            logger.error(f"Error generating locations: {e}")
            raise

    def generate_ratings(self, location_name: str, summary: str) -> Dict:
        """Generate detailed ratings using the template structure"""
        logger.debug(f"Generating ratings for {location_name}")
        
        try:
            # Load score template for reference
            if not self.score_template:
                raise ValueError("Score template not loaded")
            
            prompt = f"""
            Generate detailed ratings for {location_name} based on this summary:
            {summary}
            
            Follow the exact structure of this template, but generate appropriate scores and descriptions:
            {json.dumps(self.score_template, indent=2)}
            
            Ensure all scores are realistic and justified by available data.
            Format response as ```json```.
            """
            
            logger.debug("Sending prompt to Claude")
            response = self._get_claude_response(prompt)
            logger.debug(f"Received response from Claude: {response[:200]}...")  # Log first 200 chars
            
            ratings_match = re.search(r'```json(.*?)```', response, re.DOTALL)
            
            if ratings_match:
                ratings_text = ratings_match.group(1).strip()
                logger.debug(f"Extracted JSON text: {ratings_text[:200]}...")  # Log first 200 chars
                
                try:
                    ratings_data = json.loads(ratings_text)
                    logger.debug("Successfully parsed JSON data")
                    
                    # Validate the structure
                    if not isinstance(ratings_data, dict):
                        raise ValueError("Ratings data is not a dictionary")
                    if 'scores' not in ratings_data:
                        raise ValueError("Ratings data missing 'scores' section")
                    
                    return ratings_data
                    
                except json.JSONDecodeError as json_error:
                    logger.error(f"JSON parsing error: {json_error}")
                    logger.error(f"Problematic JSON text: {ratings_text}")
                    raise ValueError(f"Failed to parse ratings JSON: {json_error}")
            else:
                logger.error("Could not find JSON in Claude's response")
                logger.error(f"Full response: {response}")
                raise ValueError("Could not extract JSON from ratings response")
                
        except Exception as e:
            logger.error(f"Error generating ratings: {e}")
            raise