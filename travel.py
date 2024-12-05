import os
import sys
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QTableWidget, QTableWidgetItem, QLabel, 
                           QComboBox, QTabWidget, QHeaderView, QPushButton,
                           QScrollArea, QTextEdit, QSplitter, QSizePolicy,
                           QDialog, QLineEdit, QSpinBox, QProgressDialog, QMessageBox,
                           QFormLayout, QDialogButtonBox, QGroupBox)
from PyQt6.QtCore import Qt, QUrl, pyqtSlot, QObject
from PyQt6.QtGui import QColor
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage
from PyQt6.QtWebChannel import QWebChannel
from config import GOOGLE_MAPS_API_KEY, DEFAULT_CENTER, DEFAULT_ZOOM
import logging
from utils import LocationGenerator

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GenerateLocationsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Generate Locations")
        self.setModal(True)
        self.setup_ui()

    def setup_ui(self):
        layout = QFormLayout(self)
        
        # Create form fields
        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("e.g., Mumbai, India")
        
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("e.g., romantic, adventure, family")
        
        self.distance_input = QSpinBox()
        self.distance_input.setRange(1, 500)
        self.distance_input.setValue(50)
        self.distance_input.setSuffix(" km")
        
        self.results_input = QSpinBox()
        self.results_input.setRange(1, 20)
        self.results_input.setValue(10)
        
        # Add fields to form
        layout.addRow("Main Location:", self.location_input)
        layout.addRow("Focus Keyword:", self.keyword_input)
        layout.addRow("Search Radius:", self.distance_input)
        layout.addRow("Number of Results:", self.results_input)
        
        # Add buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)

    def get_values(self):
        return {
            'location': self.location_input.text().strip(),
            'keyword': self.keyword_input.text().strip(),
            'distance': self.distance_input.value(),
            'results': self.results_input.value()
        }

class LocationViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Travel Location Viewer")
        self.setGeometry(100, 100, 1000, 1200)
        
        # Initialize data storage and paths
        self.app_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.app_dir, 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        logger.debug(f"Initialized data directory at: {self.data_dir}")
        
        # Initialize data storage
        self.data = {}
        self.current_country = None
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(10)
        
        # Create all UI elements first
        self.create_ui(layout)
        
        # Then populate country selector and load initial data
        self.populate_country_selector()
        
        # Load initial country if available
        if self.country_selector.count() > 0:
            initial_country = self.country_selector.itemText(0)
            self.load_country_data(initial_country)
        else:
            # Initialize with empty data structure
            self.data = {
                'scores': {},
                'summary': {},
                'recommended_locations': []
            }
            self.update_display()
        
        # Add LocationGenerator instance
        self.location_generator = LocationGenerator()
        
    def create_ui(self, layout):
        """Create all UI elements"""
        # Set main layout properties
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Create a vertical splitter for all sections
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Top section with country selector
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)
        control_layout.setContentsMargins(0, 0, 0, 0)
        
        country_label = QLabel("Country:")
        self.country_selector = QComboBox()
        self.country_selector.currentTextChanged.connect(self.load_country_data)
        
        generate_button = QPushButton("Generate Locations")
        generate_button.clicked.connect(self.show_generate_dialog)
        
        control_layout.addWidget(country_label)
        control_layout.addWidget(self.country_selector)
        control_layout.addStretch()
        control_layout.addWidget(generate_button)
        
        # Map and Street View section
        map_section = QWidget()
        map_layout = QVBoxLayout(map_section)
        map_layout.setContentsMargins(0, 0, 0, 0)
        map_layout.setSpacing(0)
        
        # Map container
        map_container = QWidget()
        map_container.setMinimumHeight(200)
        map_container_layout = QVBoxLayout(map_container)
        map_container_layout.setContentsMargins(0, 0, 0, 0)
        map_container_layout.setSpacing(0)
        
        self.web_view = QWebEngineView()
        self.web_view.setPage(CustomWebEnginePage(self.web_view))
        self.web_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Initialize WebEngine settings
        try:
            settings = self.web_view.page().settings()
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.ShowScrollBars, True)
            logger.info("WebEngine settings initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize WebEngine settings: {e}")
        
        map_container_layout.addWidget(self.web_view)
        map_layout.addWidget(map_container)
        
        # Data section
        data_section = QWidget()
        data_layout = QVBoxLayout(data_section)
        data_layout.setContentsMargins(0, 0, 0, 0)
        data_layout.setSpacing(10)
        
        # Create tab widget for organizing data
        data_tabs = QTabWidget()
        data_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #444444;
                background: #2c2c2c;
                border-radius: 3px;
            }
            QTabBar::tab {
                padding: 8px 12px;
                margin: 2px;
                background: #1e1e1e;
                color: #ffffff;
            }
            QTabBar::tab:selected {
                background: #0d47a1;
                color: white;
            }
        """)
        
        # Country Overview Tab
        overview_tab = QWidget()
        overview_layout = QVBoxLayout(overview_tab)
        
        # Summary section
        summary_group = QGroupBox("Country Summary")
        summary_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                border: 1px solid #444444;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
                color: #ffffff;
            }
        """)
        summary_layout = QVBoxLayout(summary_group)
        
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setStyleSheet("""
            QTextEdit {
                background-color: #2c2c2c;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        summary_layout.addWidget(self.summary_text)
        
        # Strengths and Weaknesses
        sw_layout = QHBoxLayout()
        
        # Strengths
        strengths_group = QGroupBox("Strengths")
        strengths_layout = QVBoxLayout(strengths_group)
        self.strengths_list = QTextEdit()
        self.strengths_list.setReadOnly(True)
        strengths_layout.addWidget(self.strengths_list)
        
        # Weaknesses
        weaknesses_group = QGroupBox("Areas to Consider")
        weaknesses_layout = QVBoxLayout(weaknesses_group)
        self.weaknesses_list = QTextEdit()
        self.weaknesses_list.setReadOnly(True)
        weaknesses_layout.addWidget(self.weaknesses_list)
        
        sw_layout.addWidget(strengths_group)
        sw_layout.addWidget(weaknesses_group)
        
        overview_layout.addWidget(summary_group)
        overview_layout.addLayout(sw_layout)
        
        # Scores Tab
        scores_tab = self.create_detailed_scores_tab()
        
        # Locations Tab
        locations_tab = QWidget()
        locations_layout = QVBoxLayout(locations_tab)
        
        # Split view for locations
        locations_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Locations table
        self.locations_table = QTableWidget()
        self.locations_table.setColumnCount(4)
        self.locations_table.setHorizontalHeaderLabels(['Location', 'Region', 'Rating', 'Status'])
        self.locations_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.locations_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.locations_table.itemClicked.connect(self.on_location_selected)
        
        # Location details panel
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        
        self.location_detail_panel = QTextEdit()
        self.location_detail_panel.setReadOnly(True)
        self.location_detail_panel.setStyleSheet("""
            QTextEdit {
                background-color: #2c2c2c;
                color: #ffffff;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        
        details_layout.addWidget(self.location_detail_panel)
        
        # Add widgets to splitter
        locations_splitter.addWidget(self.locations_table)
        locations_splitter.addWidget(details_widget)
        locations_splitter.setSizes([300, 200])
        
        locations_layout.addWidget(locations_splitter)
        
        # Add tabs
        data_tabs.addTab(overview_tab, "Country Overview")
        data_tabs.addTab(scores_tab, "Detailed Scores")
        data_tabs.addTab(locations_tab, "Locations")
        
        data_layout.addWidget(data_tabs)
        
        # Add all sections to main splitter
        main_splitter.addWidget(control_panel)
        main_splitter.addWidget(map_section)
        main_splitter.addWidget(data_section)
        
        # Set initial splitter sizes
        main_splitter.setSizes([50, 800, 800])  # Adjust these values as needed
        
        # Add main splitter to layout
        layout.addWidget(main_splitter)
        
    def populate_country_selector(self):
        """Scan data directory for country files and populate selector"""
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        
        # Create data directory if it doesn't exist
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        # Get list of country files
        country_files = set()  # Use set to avoid duplicates
        
        if os.path.exists(data_dir):
            for file in os.listdir(data_dir):
                if file.startswith('country') and file.endswith('.json'):
                    # Extract country name from filename
                    country_name = file[7:-5]  # Remove 'country' prefix and '.json' suffix
                    if country_name.startswith('_') or country_name.startswith('-'):
                        country_name = country_name[1:]  # Remove the separator
                    
                    # Clean up the name
                    country_name = country_name.replace('_', ' ').replace('-', ' ').strip()
                    
                    # Don't add template files
                    if 'template' not in country_name.lower():
                        country_files.add(country_name.title())
        
        # Sort countries alphabetically
        country_files = sorted(list(country_files))
        
        # Add to selector
        self.country_selector.clear()
        for country in country_files:
            self.country_selector.addItem(country)
        
    def load_country_data(self, country_name):
        """Load country and location data for selected country"""
        if not country_name:
            return
        
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        
        # Convert display name to file name format (handle multi-part names)
        file_name_base = country_name.lower().strip()
        
        # Try different possible filename formats
        possible_country_filenames = [
            f"country_{file_name_base.replace(' ', '_')}.json",
            f"country-{file_name_base.replace(' ', '-')}.json",
            f"country_{file_name_base.replace(' ', '-')}.json",
            f"country-{file_name_base.replace(' ', '_')}.json"
        ]
        
        possible_location_filenames = [
            f"locations_{file_name_base.replace(' ', '_')}.json",
            f"locations-{file_name_base.replace(' ', '-')}.json",
            f"locations_{file_name_base.replace(' ', '-')}.json",
            f"locations-{file_name_base.replace(' ', '_')}.json"
        ]
        
        possible_ratings_filenames = [
            f"ratings_{file_name_base.replace(' ', '_')}.json",
            f"ratings-{file_name_base.replace(' ', '-')}.json",
            f"ratings_{file_name_base.replace(' ', '-')}.json",
            f"ratings-{file_name_base.replace(' ', '_')}.json"
        ]
        
        country_data = None
        locations_data = None
        ratings_data = None
        
        # Try to find country data file
        for filename in possible_country_filenames:
            file_path = os.path.join(data_dir, filename)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        country_data = json.load(f)
                        print(f"Found country data: {filename}")
                        break
                except json.JSONDecodeError as e:
                    print(f"Error parsing {filename}: {e}")
        
        # Try to find locations data file
        for filename in possible_location_filenames:
            file_path = os.path.join(data_dir, filename)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        locations_data = json.load(f)
                        print(f"Found locations data: {filename}")
                        break
                except json.JSONDecodeError as e:
                    print(f"Error parsing {filename}: {e}")
        
        # Try to find ratings data file
        for filename in possible_ratings_filenames:
            file_path = os.path.join(data_dir, filename)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        ratings_data = json.load(f)
                        print(f"Found ratings data: {filename}")
                        break
                except json.JSONDecodeError as e:
                    print(f"Error parsing {filename}: {e}")
        
        if country_data and locations_data:
            # Combine data
            self.data = {
                'scores': ratings_data['scores'] if ratings_data else country_data.get('scores', {}),
                'summary': country_data['summary'],
                'recommended_locations': locations_data['recommended_locations']
            }
            
            self.current_country = country_name
            
            # Update display
            self.update_display()
            self.create_map()
        else:
            error_message = []
            if not country_data:
                error_message.append(f"Country data file not found for {country_name}")
            if not locations_data:
                error_message.append(f"Locations data file not found for {country_name}")
            
            print("Error loading data:", ", ".join(error_message))
            print("Tried country files:", possible_country_filenames)
            print("Tried location files:", possible_location_filenames)
            print("Tried ratings files:", possible_ratings_filenames)
            
            self.data = {
                'scores': {},
                'summary': {},
                'recommended_locations': []
            }
        
    def update_display(self):
        """Update all display elements with current data"""
        self.update_overview()
        self.update_locations()
        self.update_detailed_scores()
    
    def update_overview(self):
        """Update the overview tab with country summary data"""
        if not self.data.get('summary'):
            return
            
        # Create basic scores section
        basic_scores_html = """
            <div style='margin-top: 15px; padding: 10px; background-color: #1e1e1e; border-radius: 4px;'>
                <h3 style='color: #4fc3f7; margin-bottom: 10px;'>Basic Scores</h3>
                <table style='width: 100%; color: #ffffff;'>
                    <tr>
                        <th style='text-align: left; padding: 5px;'>Category</th>
                        <th style='text-align: center; padding: 5px;'>Rating</th>
                    </tr>
        """
        
        # Handle both old and new score formats
        scores = self.data.get('scores', {})
        for category, value in scores.items():
            if isinstance(value, dict):
                # New format - get overall_score from dict
                score = value.get('overall_score', 0)
            else:
                # Old format - direct score value
                score = value
            
            basic_scores_html += f"""
                <tr>
                    <td style='padding: 5px;'>{category.replace('_', ' ').title()}</td>
                    <td style='text-align: center; padding: 5px; color: #4fc3f7;'>{score}/10</td>
                </tr>
            """
        
        basic_scores_html += "</table></div>"
            
        # Update summary text with dark theme colors and include basic scores
        self.summary_text.setHtml(f"""
            <div style='font-family: Arial; padding: 10px; color: #ffffff;'>
                <h3 style='color: #ffffff; margin-bottom: 10px;'>
                    {self.current_country}
                </h3>
                <p style='line-height: 1.5;'>
                    {self.data['summary'].get('overall_notes', '')}
                </p>
                <p style='color: #4fc3f7; font-weight: bold;'>
                    Overall Score: {self.data['summary'].get('total_score', 'N/A')} / {len(scores) * 10}
                </p>
                {basic_scores_html}
            </div>
        """)
        
        # Update strengths with dark theme colors
        strengths = self.data['summary'].get('strengths', [])
        strengths_html = "<ul style='margin: 5px; color: #ffffff;'>"
        for strength in strengths:
            strengths_html += f"<li style='margin-bottom: 8px;'>{strength}</li>"
        strengths_html += "</ul>"
        self.strengths_list.setHtml(strengths_html)
        
        # Update weaknesses with dark theme colors
        weaknesses = self.data['summary'].get('weaknesses', [])
        weaknesses_html = "<ul style='margin: 5px; color: #ffffff;'>"
        for weakness in weaknesses:
            weaknesses_html += f"<li style='margin-bottom: 8px;'>{weakness}</li>"
        weaknesses_html += "</ul>"
        self.weaknesses_list.setHtml(weaknesses_html)

    def update_locations(self):
        """Update the locations table with all locations"""
        self.locations_table.setRowCount(0)
        
        if not self.data.get('recommended_locations'):
            return
        
        for location in self.data['recommended_locations']:
            row = self.locations_table.rowCount()
            self.locations_table.insertRow(row)
            
            # Location name
            name_item = QTableWidgetItem(location['name'])
            
            # Region
            region_item = QTableWidgetItem(location['region'])
            
            # Rating - with better handling of None values
            rating = location.get('rating')
            if rating is not None:
                try:
                    rating_text = f"★ {float(rating):.1f}"
                    if location.get('user_ratings_total'):
                        rating_text += f" ({location['user_ratings_total']} reviews)"
                except (ValueError, TypeError):
                    rating_text = "Invalid rating"
            else:
                rating_text = "No ratings"
            rating_item = QTableWidgetItem(rating_text)
            
            # Status - with better handling of None values
            status = location.get('business_status')
            if status:
                status_text = status.title()
            else:
                status_text = 'N/A'
            status_item = QTableWidgetItem(status_text)
            
            # Set items
            self.locations_table.setItem(row, 0, name_item)
            self.locations_table.setItem(row, 1, region_item)
            self.locations_table.setItem(row, 2, rating_item)
            self.locations_table.setItem(row, 3, status_item)
            
        self.locations_table.resizeColumnsToContents()

    def on_location_selected(self, item):
        """Handle location selection and update detail panel"""
        row = item.row()
        location_name = self.locations_table.item(row, 0).text()
        
        # Find the selected location data
        location = next(
            (loc for loc in self.data['recommended_locations'] 
             if loc['name'] == location_name), 
            None
        )
        
        if location:
            # Create HTML content for location details
            html_content = f"""
                <div style='font-family: Arial; padding: 10px; color: #ffffff;'>
                    <h2 style='color: #4fc3f7; margin-bottom: 10px;'>{location['name']}</h2>
                    <p><strong>Region:</strong> {location['region']}</p>
                    <p><strong>Address:</strong> {location.get('formatted_address', 'N/A')}</p>
                    
                    <div style='margin: 10px 0;'>
                        <strong>Rating:</strong> {location.get('rating', 'N/A')}
                        {f" ({location.get('user_ratings_total', 0)} reviews)" if location.get('rating') else ""}
                    </div>
                    
                    <div style='margin: 10px 0;'>
                        <strong>Status:</strong> 
                        <span style='color: {"#4fc3f7" if location.get("business_status") == "OPERATIONAL" else "#ef5350"}'>
                            {location.get('business_status', 'N/A').title()}
                        </span>
                    </div>
                    
                    <div style='margin: 10px 0;'>
                        <strong>Description:</strong><br>
                        {location.get('brief', 'No description available.')}
                    </div>
                    
                    <div style='margin: 10px 0;'>
                        <strong>Coordinates:</strong><br>
                        Lat: {location['coords']['lat']}<br>
                        Lng: {location['coords']['lng']}
                    </div>
                </div>
            """
            self.location_detail_panel.setHtml(html_content)

    def change_view(self, view_name):
        if view_name == "Overview":
            self.main_display.setCurrentIndex(0)
        elif view_name == "Detailed Scores":
            self.main_display.setCurrentIndex(1)
        else:
            self.main_display.setCurrentIndex(2)
            
    def show_location_details(self, location):
        """Update the location details panel with the selected location"""
        # Update locations table
        self.locations_table.clearContents()
        self.locations_table.setRowCount(1)
        
        # Set location data in table
        self.locations_table.setItem(0, 0, QTableWidgetItem(location['name']))
        self.locations_table.setItem(0, 1, QTableWidgetItem(location['region']))
        self.locations_table.setItem(0, 2, QTableWidgetItem(str(location.get('score', 'N/A'))))
        
        # Update detail panel
        detail_text = f"""
        <div style="padding: 10px;">
            <h2 style="color: #2c3e50;">{location['name']}</h2>
            <p><strong>Region:</strong> {location['region']}</p>
            <p><strong>Score:</strong> {location.get('score', 'N/A')}</p>
            <div style="margin-top: 15px;">
                <h3 style="color: #34495e;">Description</h3>
                <p>{location['brief']}</p>
            </div>
        </div>
        """
        self.detail_panel.setHtml(detail_text)
        
    def create_map(self):
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Travel Locations Map</title>
            <meta name="viewport" content="initial-scale=1.0">
            <meta charset="utf-8">
            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
            <style>
                #map {{
                    height: 100%;
                    width: 100%;
                }}
                html, body {{
                    height: 100%;
                    margin: 0;
                    padding: 0;
                }}
                #street-view {{
                    height: 100%;
                    width: 100%;
                    position: absolute;
                    top: 0;
                    left: 0;
                    z-index: 2;
                    display: none;
                }}
                .info-window {{
                    max-width: 300px;
                    font-family: Arial, sans-serif;
                }}
                .info-window img {{
                    width: 100%;
                    max-height: 200px;
                    object-fit: cover;
                    margin-bottom: 10px;
                    border-radius: 4px;
                }}
                .info-window h3 {{
                    margin: 0 0 8px 0;
                    color: #1B4F72;
                }}
                .info-window p {{
                    margin: 0 0 8px 0;
                    font-size: 14px;
                }}
                .rating {{
                    color: #f8c51c;
                    margin-bottom: 5px;
                }}
                .business-status {{
                    display: inline-block;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-size: 12px;
                    margin-bottom: 5px;
                }}
                .status-operational {{
                    background-color: #e8f5e9;
                    color: #2e7d32;
                }}
                .status-closed {{
                    background-color: #ffebee;
                    color: #c62828;
                }}
            </style>
        </head>
        <body>
            <div id="map"></div>
            <div id="street-view"></div>
            <script>
                let map;
                let panorama;
                let markers = [];
                let activeInfoWindow = null;
                let channel;

                function showStreetView(lat, lng) {{
                    const position = new google.maps.LatLng(lat, lng);
                    panorama.setPosition(position);
                    panorama.setVisible(true);
                    document.getElementById('street-view').style.display = 'block';
                }}

                // Initialize WebChannel
                new QWebChannel(qt.webChannelTransport, function(ch) {{
                    channel = ch;
                    console.log("WebChannel initialized");
                    loadGoogleMaps();
                }});

                function loadGoogleMaps() {{
                    try {{
                        const script = document.createElement('script');
                        script.src = "https://maps.googleapis.com/maps/api/js?key={GOOGLE_MAPS_API_KEY}&libraries=places&callback=initialize";
                        script.async = true;
                        script.defer = true;
                        document.head.appendChild(script);
                        console.log("Google Maps script added to head");
                    }} catch (error) {{
                        console.error("Error loading Google Maps:", error);
                    }}
                }}

                async function initialize() {{
                    try {{
                        console.log("Initializing map...");
                        
                        // Initialize map
                        map = new google.maps.Map(document.getElementById('map'), {{
                            zoom: {DEFAULT_ZOOM},
                            center: {{ lat: {DEFAULT_CENTER['lat']}, lng: {DEFAULT_CENTER['lng']} }},
                            streetViewControl: true,
                            gestureHandling: "greedy"
                        }});

                        // Initialize Street View
                        panorama = new google.maps.StreetViewPanorama(
                            document.getElementById('street-view'),
                            {{
                                visible: false,
                                motionTracking: false,
                                motionTrackingControl: true,
                                fullscreenControl: true,
                                addressControl: true,
                                linksControl: true,
                                panControl: true,
                                enableCloseButton: true,
                                zoomControl: true,
                                pov: {{
                                    heading: 0,
                                    pitch: 0,
                                    zoom: 1
                                }}
                            }}
                        );
                        
                        map.setStreetView(panorama);
                        console.log("Map and Street View initialized");

                        // Add markers for locations
                        const locations = {json.dumps(self.data.get('recommended_locations', []))};
                        const bounds = new google.maps.LatLngBounds();
                        
                        console.log("Adding markers for locations:", locations);

                        for (const location of locations) {{
                            const position = {{ 
                                lat: location.coords.lat, 
                                lng: location.coords.lng 
                            }};
                            
                            // Create marker
                            const marker = new google.maps.Marker({{
                                position: position,
                                map: map,
                                title: location.name,
                                label: {{
                                    text: location.name,
                                    className: 'marker-label',
                                    fontSize: '12px',
                                    fontWeight: 'bold'
                                }},
                                animation: google.maps.Animation.DROP
                            }});
                            
                            bounds.extend(position);
                            markers.push(marker);

                            function createInfoWindowContent(location) {{
                                const ratingStars = '★'.repeat(Math.round(location.rating || 0)) + 
                                                  '☆'.repeat(5 - Math.round(location.rating || 0));
                                
                                const statusClass = location.business_status === 'OPERATIONAL' ? 
                                    'status-operational' : 'status-closed';
                                
                                const statusText = location.business_status === 'OPERATIONAL' ? 
                                    'Open' : 'Closed';

                                let content = '<div class="info-window">';
                                
                                // Add photo if available
                                if (location.photo_url) {{
                                    content += '<img src="' + location.photo_url + '" alt="' + location.name + '">';
                                }}
                                
                                // Add name
                                content += '<h3>' + location.name + '</h3>';
                                
                                // Add rating if available
                                if (location.rating) {{
                                    content += '<div class="rating">' + 
                                              ratingStars + ' (' + (location.user_ratings_total || 0) + ' reviews)' +
                                              '</div>';
                                }}
                                
                                // Add business status if available
                                if (location.business_status) {{
                                    content += '<div class="business-status ' + statusClass + '">' +
                                              statusText +
                                              '</div>';
                                }}
                                
                                // Add description and address
                                content += '<p>' + location.brief + '</p>' +
                                           '<p><small>' + location.formatted_address + '</small></p>';
                                
                                // Add Street View button
                                content += '<button onclick="showStreetView(' + 
                                           location.coords.lat + ', ' + 
                                           location.coords.lng + ')" ' +
                                           'style="background: #1B4F72; color: white; border: none; ' +
                                           'padding: 5px 10px; border-radius: 3px; cursor: pointer;">' +
                                           'Show Street View' +
                                           '</button>';
                                
                                content += '</div>';
                                
                                return content;
                            }}

                            // Update the marker click handler
                            marker.addListener('click', () => {{
                                if (activeInfoWindow) {{
                                    activeInfoWindow.close();
                                }}

                                const infoWindow = new google.maps.InfoWindow({{
                                    content: createInfoWindowContent(location)
                                }});
                                
                                infoWindow.open({{
                                    anchor: marker,
                                    map
                                }});
                                
                                activeInfoWindow = infoWindow;

                                if (channel && channel.objects.handler) {{
                                    channel.objects.handler.handleMarkerClick(JSON.stringify(location));
                                }}
                            }});
                        }}

                        // Fit map to show all markers
                        if (markers.length > 0) {{
                            map.fitBounds(bounds);
                        }}

                        // Add Street View visibility listener
                        panorama.addListener('visible_changed', () => {{
                            const isVisible = panorama.getVisible();
                            document.getElementById('street-view').style.display = isVisible ? 'block' : 'none';
                            
                            if (isVisible && panorama.getPosition()) {{
                                const pos = panorama.getPosition();
                                if (channel && channel.objects.handler) {{
                                    channel.objects.handler.handleStreetViewEvent(JSON.stringify({{
                                        event: 'visible_changed',
                                        details: {{ lat: pos.lat(), lng: pos.lng() }}
                                    }}));
                                }}
                            }}
                        }});

                        // ... rest of the initialize function ...
                    }} catch (error) {{
                        console.error("Initialization error:", error);
                    }}
                }}
                
                // ... rest of the JavaScript ...
            </script>
        </body>
        </html>
        """

        # Add logging for map creation
        logger.debug("Creating map with HTML content")
        
        try:
            # Create map channel
            map_channel = QWebChannel(self.web_view.page())
            self.web_view.page().setWebChannel(map_channel)
            logger.debug("WebChannel created successfully")
            
            # Add error handling to Handler class
            class Handler(QObject):
                @pyqtSlot(str)
                def handleMarkerClick(self, location_data):
                    try:
                        self.parent().show_location_details(json.loads(location_data))
                    except Exception as e:
                        logger.error(f"Error handling marker click: {e}")

                @pyqtSlot(str)
                def handleStreetViewEvent(self, event_data):
                    try:
                        event = json.loads(event_data)
                        logger.info(f"Street View Event: {event['event']}")
                        logger.debug(f"Event Details: {event['details']}")
                    except Exception as e:
                        logger.error(f"Error handling street view event: {e}")

                @pyqtSlot(str)
                def handleError(self, error_data):
                    logger.error(f"JavaScript error: {error_data}")

            self.handler = Handler()
            self.handler.setParent(self)
            map_channel.registerObject('handler', self.handler)
            logger.debug("Handler registered with WebChannel")

            # Set the HTML content
            self.web_view.setHtml(html_content, QUrl("https://maps.googleapis.com/"))
            logger.info("Map initialized successfully")
            
        except Exception as e:
            logger.error(f"Error creating map: {e}")

    def show_generate_dialog(self):
        """Show the generate locations dialog"""
        dialog = GenerateLocationsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            values = dialog.get_values()
            
            # Validate inputs
            if not values['location'] or not values['keyword']:
                QMessageBox.warning(
                    self,
                    "Invalid Input",
                    "Please enter both a location and a focus keyword."
                )
                return
            
            # Create a more informative progress dialog
            progress = QProgressDialog(
                f"Analyzing {values['location']} for {values['keyword']}...\n\n"
                "Step 1: Gathering location information...", 
                "Cancel", 0, 0, self
            )
            progress.setWindowTitle("Generating Locations")
            progress.setMinimumWidth(400)  # Make dialog wider for better readability
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()
            
            try:
                # Generate locations with callback for progress updates
                def progress_callback(stage, data=None):
                    if stage == "country_data":
                        # Format the country data nicely for display
                        summary = data.get('summary', {})
                        strengths = "\n• " + "\n• ".join(summary.get('strengths', []))
                        weaknesses = "\n• " + "\n• ".join(summary.get('weaknesses', []))
                        
                        progress_text = (
                            f"Analysis of {values['location']} complete!\n\n"
                            f"Overall Score: {summary.get('total_score', 'N/A')}\n\n"
                            f"Key Strengths:{strengths}\n\n"
                            f"Areas to Consider:{weaknesses}\n\n"
                            f"Step 2: Finding specific locations..."
                        )
                        progress.setLabelText(progress_text)
                    elif stage == "locations_data":
                        progress.setLabelText(
                            "Step 3: Finalizing location details...\n\n"
                            f"Found {len(data.get('recommended_locations', []))} locations!"
                        )

                # Generate locations
                country_file, locations_file = self.location_generator.generate_locations(
                    values['location'],
                    values['keyword'],
                    values['distance'],
                    values['results'],
                    progress_callback  # Pass the callback
                )
                
                # Close progress dialog
                progress.close()
                
                # Show success message
                QMessageBox.information(
                    self,
                    "Success",
                    f"Generated {values['results']} locations around {values['location']}!"
                )
                
                # Refresh country selector
                self.populate_country_selector()
                
                # Create the display name that matches how it will appear in the selector
                display_name = f"{values['location']} {values['keyword']}".title()
                
                # Find and select the new entry
                index = self.country_selector.findText(display_name)
                if index >= 0:
                    self.country_selector.setCurrentIndex(index)
                    # Force a refresh of the map and data
                    self.load_country_data(display_name)
                
            except Exception as e:
                progress.close()
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to generate locations: {str(e)}"
                )

    def create_detailed_scores_tab(self):
        """Create the detailed scores tab with comprehensive rating system"""
        scores_tab = QWidget()
        scores_layout = QVBoxLayout(scores_tab)
        
        # Add header section with Rate button
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        
        # Add explanatory label
        header_label = QLabel("Generate detailed ratings analysis for this location:")
        header_label.setStyleSheet("color: #ffffff;")
        header_layout.addWidget(header_label)
        
        # Add Rate This Location button
        rate_button = QPushButton("Generate Detailed Ratings")
        rate_button.clicked.connect(self.generate_ratings)
        rate_button.setStyleSheet("""
            QPushButton {
                background-color: #4fc3f7;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                max-width: 200px;
            }
            QPushButton:hover {
                background-color: #0d47a1;
            }
        """)
        header_layout.addWidget(rate_button)
        header_layout.addStretch()
        
        scores_layout.addWidget(header_widget)
        
        # Create scroll area for scores
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # Add content placeholder
        self.detailed_scores_content = QVBoxLayout()
        scroll_layout.addLayout(self.detailed_scores_content)
        
        scroll_content.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_content)
        scores_layout.addWidget(scroll_area)
        
        return scores_tab

    def update_detailed_scores(self):
        """Update the detailed scores display"""
        # Clear existing content
        while self.detailed_scores_content.count():
            item = self.detailed_scores_content.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Check if we have detailed scores
        if not isinstance(self.data.get('scores', {}), dict):
            no_scores_label = QLabel("No detailed ratings available. Click 'Generate Detailed Ratings' to analyze this location.")
            no_scores_label.setStyleSheet("color: #ffffff; padding: 20px;")
            no_scores_label.setWordWrap(True)
            self.detailed_scores_content.addWidget(no_scores_label)
            return
        
        for category, data in self.data['scores'].items():
            if isinstance(data, dict) and 'subcategories' in data:
                # Create category group
                category_group = QGroupBox(category.replace('_', ' ').title())
                category_group.setStyleSheet("""
                    QGroupBox {
                        color: #ffffff;
                        border: 1px solid #444444;
                        border-radius: 4px;
                        margin-top: 12px;
                        padding: 15px;
                    }
                    QGroupBox::title {
                        color: #4fc3f7;
                        subcontrol-origin: margin;
                        left: 10px;
                    }
                """)
                
                group_layout = QVBoxLayout()
                
                # Overall score for category - Changed to numerical display
                overall_score = data.get('overall_score', 0)
                overall_label = QLabel(f"Overall Score: {overall_score}/10")
                overall_label.setStyleSheet("color: #4fc3f7; margin-bottom: 10px;")
                group_layout.addWidget(overall_label)
                
                # Add subcategories table
                subcategories_table = QTableWidget()
                subcategories_table.setColumnCount(3)
                subcategories_table.setHorizontalHeaderLabels(['Subcategory', 'Score', 'Description'])
                subcategories_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
                subcategories_table.setStyleSheet("""
                    QTableWidget {
                        background-color: #2c2c2c;
                        color: #ffffff;
                        gridline-color: #444444;
                        border: none;
                    }
                    QTableWidget::item {
                        padding: 5px;
                    }
                    QHeaderView::section {
                        background-color: #1e1e1e;
                        color: #ffffff;
                        padding: 5px;
                        border: 1px solid #444444;
                    }
                """)
                
                for subcat, subdata in data['subcategories'].items():
                    row = subcategories_table.rowCount()
                    subcategories_table.insertRow(row)
                    
                    name_item = QTableWidgetItem(subcat.replace('_', ' ').title())
                    score = subdata.get('score', 0)
                    # Changed to numerical score display
                    score_item = QTableWidgetItem(f"{score}/10")
                    desc_item = QTableWidgetItem(subdata.get('description', ''))
                    
                    subcategories_table.setItem(row, 0, name_item)
                    subcategories_table.setItem(row, 1, score_item)
                    subcategories_table.setItem(row, 2, desc_item)
                
                group_layout.addWidget(subcategories_table)
                
                # Add notes if available
                if 'notes' in data:
                    notes_label = QLabel(f"Notes: {data['notes']}")
                    notes_label.setWordWrap(True)
                    notes_label.setStyleSheet("color: #ffffff; margin-top: 10px;")
                    group_layout.addWidget(notes_label)
                
                category_group.setLayout(group_layout)
                self.detailed_scores_content.addWidget(category_group)
        
        # Add stretch at the end
        self.detailed_scores_content.addStretch()

    def generate_ratings(self):
        """Generate detailed ratings using Anthropic API"""
        if not self.current_country:
            QMessageBox.warning(self, "Error", "Please select a country first")
            return
        
        progress = None
        try:
            progress = QProgressDialog(
                "Generating detailed ratings analysis...\n\n"
                "This may take a minute as we thoroughly analyze all aspects.",
                "Cancel", 0, 0, self
            )
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()
            
            logger.debug(f"Starting ratings generation for {self.current_country}")
            
            # Generate ratings using LocationGenerator
            ratings = self.location_generator.generate_ratings(
                self.current_country,
                self.data.get('summary', {}).get('overall_notes', '')
            )
            
            if not ratings:
                raise ValueError("No ratings data received from API")
            
            logger.debug(f"Received ratings data: {json.dumps(ratings, indent=2)}")
            
            # Save ratings to file
            clean_name = self.current_country.lower().replace(' ', '_')
            ratings_file = f"ratings_{clean_name}.json"
            file_path = os.path.join(self.data_dir, ratings_file)
            
            logger.debug(f"Saving ratings to: {file_path}")
            
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(ratings, f, indent=2)
                logger.debug(f"Successfully saved ratings to {file_path}")
            except Exception as save_error:
                logger.error(f"Error saving ratings file: {save_error}")
                raise
            
            # Update the display
            if 'scores' in ratings:
                self.data['scores'] = ratings['scores']
                self.update_detailed_scores()
                logger.debug("Updated display with new ratings")
            else:
                raise ValueError("Ratings data missing 'scores' section")
            
            if progress:
                progress.close()
            
            QMessageBox.information(
                self,
                "Success",
                f"Generated detailed ratings analysis for {self.current_country}"
            )
            
        except Exception as e:
            logger.error(f"Error in generate_ratings: {str(e)}")
            if progress:
                progress.close()
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to generate ratings: {str(e)}\n\nCheck the logs for more details."
            )

class CustomWebEnginePage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        level_str = {
            QWebEnginePage.JavaScriptConsoleMessageLevel.InfoMessageLevel: "INFO",
            QWebEnginePage.JavaScriptConsoleMessageLevel.WarningMessageLevel: "WARNING",
            QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel: "ERROR"
        }.get(level, "DEBUG")
        
        logger.log(
            logging.INFO if level_str == "INFO" else 
            logging.WARNING if level_str == "WARNING" else 
            logging.ERROR if level_str == "ERROR" else 
            logging.DEBUG,
            f"JavaScript {level_str}: {message} (line: {lineNumber}, source: {sourceID})"
        )

def main():
    # Set up dictionary path before creating QApplication
    try:
        from PyQt6.QtCore import QLibraryInfo
        dict_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.DataPath)
        dict_dir = os.path.join(dict_path, "qtwebengine_dictionaries")
        
        # Create directory if it doesn't exist
        os.makedirs(dict_dir, exist_ok=True)
        
        os.environ["QTWEBENGINE_DICTIONARIES_PATH"] = dict_dir
        logger.debug(f"Set dictionary path to: {dict_dir}")
    except Exception as e:
        logger.warning(f"Failed to set dictionary path: {e}")
        # Set a fallback path in the user's home directory
        fallback_path = os.path.expanduser("~/.qtwebengine_dictionaries")
        os.makedirs(fallback_path, exist_ok=True)
        os.environ["QTWEBENGINE_DICTIONARIES_PATH"] = fallback_path
        logger.debug(f"Using fallback dictionary path: {fallback_path}")

    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    viewer = LocationViewer()
    viewer.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()