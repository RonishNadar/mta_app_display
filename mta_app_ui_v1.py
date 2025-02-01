#!/usr/bin/python
# -*- coding: UTF-8 -*-
#import chardet

import requests
from google.transit import gtfs_realtime_pb2
from datetime import datetime, timedelta
import time
import csv
import os
import sys 
import logging
import st7796
import ft6336u
from PIL import Image, ImageDraw, ImageFont

image = Image.new("RGB", (480, 320), "#000000")
disp = st7796.st7796()
touch = ft6336u.ft6336u()

# Load stop, route, and trip mappings
def load_stop_mapping(file_path="stops.txt"):
    stop_mapping = {}
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            stop_mapping[row["stop_id"]] = row["stop_name"]
    return stop_mapping


def load_route_mapping(file_path="routes.txt"):
    route_mapping = {}
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            route_mapping[row["route_id"]] = row["route_long_name"]
    return route_mapping


def load_trip_mapping(file_path="trips.txt"):
    trip_mapping = {}
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            trip_mapping[row["trip_id"]] = row["trip_headsign"]
    return trip_mapping

# Fetch GTFS data
def fetch_gtfs_data(api_url, api_key):
    headers = {"x-api-key": api_key}
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"Error fetching GTFS data: {response.status_code} - {response.text}")

# Extract short trip ID
def extract_n_pattern_by_index_range(trip_id):
    return trip_id[7:11]

# Get destination for short trip ID
def get_destination_for_short_trip_id(short_trip_id, trip_mapping):
    trip_id_small = extract_n_pattern_by_index_range(short_trip_id)
    for long_trip_id, trip_headsign in trip_mapping.items():
        if trip_id_small in long_trip_id:
            return trip_headsign
    return "Unknown Destination"

# Parse GTFS data
def parse_gtfs_data(gtfs_data, stop_id_filter, stop_mapping, route_mapping, trip_mapping, max_trains_per_station=2):
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(gtfs_data)

    filtered_data = []
    current_time = datetime.now()
    destination_counts = {}

    for entity in feed.entity:
        if entity.trip_update:
            trip_id = entity.trip_update.trip.trip_id
            route_id = entity.trip_update.trip.route_id
            for stop_time_update in entity.trip_update.stop_time_update:
                stop_id = stop_time_update.stop_id
                if stop_id_filter in stop_id:
                    arrival_time = datetime.fromtimestamp(stop_time_update.arrival.time) if stop_time_update.arrival.time else None
                    
                    if arrival_time and arrival_time > current_time:
                        time_remaining = arrival_time - current_time
                        station_name = stop_mapping.get(stop_id, "Unknown Station")
                        route_name = route_mapping.get(route_id, "Unknown Route")
                        destination = get_destination_for_short_trip_id(trip_id, trip_mapping)

                        if destination_counts.get(destination, 0) < max_trains_per_station:
                            filtered_data.append({
                                "trip_id": trip_id,
                                "route_id": route_id,
                                "station_name": station_name,
                                "time_remaining": time_remaining,
                                "route_name": route_name,
                                "destination": destination
                            })
                            destination_counts[destination] = destination_counts.get(destination, 0) + 1

    filtered_data.sort(key=lambda x: (x['destination'], x['time_remaining']))
    
    return filtered_data

# Create MTA display image
def create_mta_page(draw, line_type, end_up, time_up, time_dn, ind, font_40, font_30):
    draw.rounded_rectangle([(5, (8 + (ind * 155))), (75, (78 + (ind * 155)))], fill="#FFFFFF", radius=10)
    color_map = {"N": "#FCCC0A", "D": "#FF6319"}
    text_color = "#000000" if line_type == "N" else "#FFFFFF"

    draw.ellipse([(10, (14 + (ind * 155))), (70, (74 + (ind * 155)))], fill=color_map.get(line_type, "#000000"))
    draw.text(((60 // 2) + 11, (60 // 2) + (13 + (ind * 155))), line_type, fill=text_color, font=font_40, anchor="mm")

    draw.rounded_rectangle([(80, (8 + (ind * 155))), (475, (78 + (ind * 155)))], fill="#D9D9D9", radius=10)
    draw.text(((395 // 2) + 80, (70 // 2) + (8 + (ind * 155))), end_up, fill="#000000", font=font_30, anchor="mm")

    draw.rounded_rectangle([(5, (83 + (ind * 155))), (232, (158 + (ind * 155)))], fill="#000000", radius=10)
    draw.text(((227 // 2) + 5, (75 // 2) + (83 + (ind * 155))), time_up, fill="#FFFFFF", font=font_30, anchor="mm")

    draw.rounded_rectangle([(237, (83 + (ind * 155))), (475, (158 + (ind * 155)))], fill="#000000", radius=10)
    draw.text(((227 // 2) + 237, (75 // 2) + (83 + (ind * 155))), time_dn, fill="#FFFFFF", font=font_30, anchor="mm")

def format_time_remaining(seconds):
    """Formats time remaining into 'X hr Y min' or 'X min'."""
    minutes = round(seconds / 60)
    hours = minutes // 60
    return f"{minutes} min" if hours == 0 else f"{hours} hr {minutes % 60} min"

def display_schedule_on_image(train_schedule):
    """Displays train schedule on an image."""
    draw = ImageDraw.Draw(image)
    draw.rectangle([(0, 0), (480, 320)], fill="#303030")    
    font_40 = ImageFont.truetype("OpenSans-Bold.ttf", 40)
    font_30 = ImageFont.truetype("OpenSans-Bold.ttf", 30)

    for i in range(0, min(len(train_schedule), 4), 2):  # Process in pairs
        trains = train_schedule[i:i+2]  # Get up to 2 trains
        times = [format_time_remaining(train['time_remaining'].seconds) for train in trains]

        create_mta_page(
            draw, trains[0]['route_id'], trains[0]['destination'],
            times[0], times[1] if len(times) > 1 else "", i // 2, font_40, font_30
        )
    image = image.rotate(0)
    disp.show_image(image)

# Main function
def main():
    API_KEY = "your_mta_api_key"
    URL = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw"
    stop_id_filter = "N03"
    # URL = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm"
    # stop_id_filter = "B17"    
    disp.clear()

    stop_mapping = load_stop_mapping("stops.txt")
    route_mapping = load_route_mapping("routes.txt")
    trip_mapping = load_trip_mapping("trips.txt")

    while True:
        try:
            gtfs_data = fetch_gtfs_data(URL, API_KEY)
            train_schedule = parse_gtfs_data(gtfs_data, stop_id_filter, stop_mapping, route_mapping, trip_mapping)
            display_schedule_on_image(train_schedule)
        except Exception as e:
            print(f"An error occurred: {e}")
        
        time.sleep(5)

if __name__ == "__main__":
    main()