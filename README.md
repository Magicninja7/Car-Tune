Car Tune Project
This project aims to create a portable music chooser and player, inspired by an old-school GPS look, designed to integrate seamlessly with YouTube Music. It combines hardware components such as a Raspberry Pi Zero, touchscreen, speaker, and tactile buttons, with a software interface built using HTML, CSS, JavaScript, Python, Flask, and Jinja2.

Features
Artist and Album Sorting: Browse music by artist and view songs in each album.
Music Control: Play, pause, skip to the next, or go back to the previous song.
Volume Control: Use the hardware volume dial to adjust playback volume.
Portable and Interactive UI: The software interface is designed to mimic an old-school GPS for easy navigation on the 3.5" touchscreen.
Responsive Touchscreen Support: Optimized for touchscreen interactions and tactile feedback from buttons.
Software Overview
The software is organized into the following key components:

Frontend:

Built using HTML, CSS, and JavaScript.
Styled with responsive design for optimal use on a small touchscreen display.
Backend:

Developed with Python and Flask, with data managed using a songs.db database file.
Handles song organization, playback control, and API interactions.
Database (songs.db):

Stores song data, organized by artist and album for easy browsing.
API Integration:

Connects with the YouTube Music API to pull music data.
Allows for dynamic song management based on the user's music library.
Requirements
Hardware: Raspberry Pi Zero, TFT 3.5" Touchscreen (320x480px), Speaker, Tact Switch, Rotary Encoder, Battery
Software:
Python 3.x
Flask
SQLite3
Additional Python libraries:
Flask
Jinja2
YouTube Music API wrapper (for integrating with YouTube Music)
Installation
Clone the Repository:

bash
Copy code
git clone <repository-url>
cd car-tune-project
Install Python Dependencies:

bash
Copy code
pip install -r requirements.txt
Set up the Database:

Ensure songs.db is in the project directory.
Populate it with your song library or sync with YouTube Music.
Configure API Access:

Follow YouTube Music API documentation to set up an API key.
Add the API key in your environment or configuration file.
Run the Application:

bash
Copy code
flask run
Access the app on your local network using the touchscreen device's browser.
Usage
Browse Music:

Select an artist to view their albums.
Tap on an album to see available songs.
Play Controls:

Use the play, pause, next, and previous buttons to control playback.
Volume Adjustment:

Rotate the physical volume dial to adjust playback sound.
Power On/Off:

Use the tact switch to turn the device on or off safely.
Project Structure
plaintext
Copy code
car-tune-project/
├── templates/                # HTML templates for Flask
├── static/
│   ├── css/                  # Stylesheets
│   ├── js/                   # JavaScript files
├── app.py                    # Main Flask application
├── songs.db                  # SQLite database for song storage
├── config.py                 # API configuration
└── README.md
Future Enhancements
Offline Song Storage: Download and store songs for offline playback.
Improved UI: Additional style refinements for better user experience.
Enhanced Music Control: More options for shuffling and queuing songs.
Contributing
Contributions are welcome! Please fork the repository, create a new branch, and submit a pull request with a detailed description of your changes.

License
This project is open-source and available under the MIT License. See the LICENSE file for more details.

