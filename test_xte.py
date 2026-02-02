#!/usr/bin/env python3
"""
Simple XTE Test Script
Run this to test the Cross-Track Error calculation with sample coordinates.
"""

import math

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # Radius of Earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi/2)**2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def calculate_bearing(lat1, lon1, lat2, lon2):
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)
    
    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - \
        math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    
    theta = math.atan2(y, x)
    bearing = (math.degrees(theta) + 360) % 360
    return bearing

def get_cross_track_error(start_lat, start_lng, end_lat, end_lng, curr_lat, curr_lng):
    """
    Calculates Cross-Track Error (distance from the line start->end).
    Returns distance in meters. Positive = Right of line, Negative = Left.
    """
    # Distance from Start to Current
    dist_13 = haversine_distance(start_lat, start_lng, curr_lat, curr_lng)
    
    # Bearing from Start to End (Path Bearing)
    bearing_12 = calculate_bearing(start_lat, start_lng, end_lat, end_lng)
    
    # Bearing from Start to Current
    bearing_13 = calculate_bearing(start_lat, start_lng, curr_lat, curr_lng)
    
    # Angle Difference
    diff = math.radians(bearing_13 - bearing_12)
    
    # XTE Formula
    return dist_13 * math.sin(diff)

# Test Case: Straight Road (North-South)
print("=" * 50)
print("TEST: Straight Road (North)")
print("=" * 50)

# Define a straight road going North
start = (12.9716, 77.5946)  # Bangalore coordinates (example)
end = (12.9726, 77.5946)    # 100m North (same longitude)

# Car is exactly on the line
current = (12.9721, 77.5946)  # Midpoint
xte = get_cross_track_error(start[0], start[1], end[0], end[1], current[0], current[1])
print(f"Car ON the line: XTE = {xte:.2f}m (should be ~0)")

# Car is 2m to the right (East)
current_right = (12.9721, 77.59462)  # Slightly East
xte_right = get_cross_track_error(start[0], start[1], end[0], end[1], current_right[0], current_right[1])
print(f"Car 2m RIGHT: XTE = {xte_right:.2f}m (should be ~2)")

# Car is 2m to the left (West)
current_left = (12.9721, 77.59458)  # Slightly West
xte_left = get_cross_track_error(start[0], start[1], end[0], end[1], current_left[0], current_left[1])
print(f"Car 2m LEFT: XTE = {xte_left:.2f}m (should be ~-2)")

print("\n" + "=" * 50)
print("If XTE < 4.0m, steering should be LOCKED at 0")
print("=" * 50)
