# -*- coding: utf-8 -*-
"""
Created on Wed Mar  7 13:48:39 2018

@author: fhp7
"""
#%% User data entry and model assumptions
# The name of this run, used in naming saved results files
run_name = "default_run_name"

### Pricing Assumptions, see the ESC Rate Design Collaborative Presentation for details.
###   Currently assuming SC No.1 Residential Service Class
monthly_customer_charge = 15.92 # dollars
delivery_charge_peak = 0.12420 # dollars/kWh, applies 4PM-6PM on weekdays
delivery_charge_offpeak = 0.03011 # dollars/kWh, applies at all other hours
peak_price_hours = [16,17] # The integer representations of hours of the day, in 0, 1, 2, ..., 23 format

### Battery Parameters, currently assuming Tesla Powerwall 2
battery_model_name = "Tesla Powerwall 2"
battery_max_capacity = 14
battery_max_charge_rate = 3.3
battery_initial_state_of_charge = 0
battery_round_trip_efficiency = 0.90

### Controller to be used, see battery_controller.py to understand the options
controller_type = "daily_threshold" # 2 types are currently available: "daily_threshold", and "simple_peak"
# For daily_threshold controller
thresh_high_quant = 0.85
thresh_low_quant = 0.15
# For simple_peak controller
peak_hours = [16, 17]
trough_hour = 2

# Assumptions for results calculations
hours_per_month = 730 # From 8760/12
