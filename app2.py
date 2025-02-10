import sys
import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from PyQt5.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget
from PyQt5.QtCore import QTimer, QTime, Qt

# Spotify API credentials (Replace with yours)
SPOTIPY_CLIENT_ID = "your_client_id"
SPOTIPY_CLIENT_SECRET = "your_client_secret"
SPOTIPY_REDIRECT_URI = "http://localhost:8888/callback"

# Weather API (Replace with your API key)
WEATHER_API_KEY = "your_openweather_api_key"
CITY = "New York"  # Change to your city

# Initialize Spotify API
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                                               client_secret=SPOTIPY_CLIENT_SECRET,
                                               redirect_uri=SPOTIPY_REDIRECT_URI,
                                               scope="user-read-playback-state,user-modify-playback-state"))

class SmartDisplay(QWidget):
    def __init__(self):
        super().__init__()

        # UI Elements
        self.time_label = QLabel(self)
        self.weather_label = QLabel(self)
        self.song_label = QLabel(self)

        self.prev_button = QPushButton("⏮", self)
        self.play_button = QPushButton("▶", self)
        self.next_button = QPushButton("⏭", self)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.time_label, alignment=Qt.AlignCenter)
        layout.addWidget(self.weather_label, alignment=Qt.AlignCenter)
        layout.addWidget(self.song_label, alignment=Qt.AlignCenter)

        layout.addWidget(self.prev_button, alignment=Qt.AlignCenter)
        layout.addWidget(self.play_button, alignment=Qt.AlignCenter)
        layout.addWidget(self.next_button, alignment=Qt.AlignCenter)

        self.setLayout(layout)

        # Timers
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)  # Update every second

        self.weather_timer = QTimer(self)
        self.weather_timer.timeout.connect(self.update_weather)
        self.weather_timer.start(600000)  # Update every 10 minutes

        self.spotify_timer = QTimer(self)
        self.spotify_timer.timeout.connect(self.update_spotify)
        self.spotify_timer.start(5000)  # Update every 5 seconds

        # Button Click Events
        self.prev_button.clicked.connect(self.previous_track)
        self.play_button.clicked.connect(self.play_pause)
        self.next_button.clicked.connect(self.next_track)

        self.update_time()
        self.update_weather()
        self.update_spotify()

    def update_time(self):
        current_time = QTime.currentTime().toString("hh:mm:ss")
        self.time_label.setText(f"🕒 {current_time}")

    def update_weather(self):
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={WEATHER_API_KEY}&units=metric"
            response = requests.get(url)
            data = response.json()
            temp = data["main"]["temp"]
            condition = data["weather"][0]["description"]
            self.weather_label.setText(f"🌡 {temp}°C | {condition}")
        except Exception as e:
            self.weather_label.setText("Weather error")

    def update_spotify(self):
        try:
            track = sp.current_playback()
            if track and track["is_playing"]:
                song = track["item"]["name"]
                artist = track["item"]["artists"][0]["name"]
                self.song_label.setText(f"🎵 {song} - {artist}")
            else:
                self.song_label.setText("🎵 No music playing")
        except Exception as e:
            self.song_label.setText("Spotify error")

    def previous_track(self):
        sp.previous_track()

    def play_pause(self):
        track = sp.current_playback()
        if track and track["is_playing"]:
            sp.pause_playback()
        else:
            sp.start_playback()

    def next_track(self):
        sp.next_track()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SmartDisplay()
    window.setWindowTitle("Smart Display")
    window.resize(320, 480)
    window.showFullScreen()  # Use show() if testing on a monitor
    sys.exit(app.exec_())
