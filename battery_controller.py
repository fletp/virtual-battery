# -*- coding: utf-8 -*-
"""
Created on Mon Mar 12 12:52:00 2018

@author: fhp7
"""
import pandas as pd

def make_controller(controller_type, **kwargs):
    """Selects which specific controller will be used and constructs it.
    
    Args:
        controller_type: string denoting the controller class to be used
                            all other arguments are simply passed through to 
                            the specific controller.
    Returns:
        obj: controller object of the type denoted by controller_type
    """
    if controller_type == "daily_threshold":
        obj = controller_dailythresh(df = kwargs['df'],
                                     thresh_high_quant = kwargs['thresh_high_quant'], 
                                     thresh_low_quant = kwargs['thresh_low_quant'])
    elif controller_type == "simple_peak":
        obj = controller_peaksimple(peak_hours = kwargs['peak_hours'],
                                    trough_hour = kwargs['trough_hour'])
    
    return obj

#%% Simple Peak Controller
    
class controller_peaksimple(object):
    """Describes a simple peak battery controller and maintains pre-calculated variables.
    
    Attributes:
        peak_hours: list of hour numbers in 0,1,2...23 format that correspond
                        to peak demand times when the battery should be discharged.
        trough_hour: hour number in 0,1,2...23 format that corresponds to a trough 
                        demand time after which the battery should be charged until full.
    """
    peak_hours = []
    trough_hour = 0
    
    def __init__(self, peak_hours, trough_hour):
        """Initializes a controller object
    
        Args:
            peak_hours: list of hour numbers in 0,1,2...23 format that correspond
                            to peak demand times when the battery should be discharged.
            trough_hour: hour number in 0,1,2...23 format that corresponds to a 
                            trough demand time after which the battery should be
                            charged until full.
        """
        self.peak_hours = peak_hours
        self.trough_hour = trough_hour

    def decide(self, df, cur_datetime, battery_obj):
        """Decides how much to charge or discharge the battery based on the time
            of day.
        
        Args:
            df: pandas dataframe of price data with datetime indexing
            cur_datetime: pandas datetime object giving the time for which this
                            charge decision is being made.
            battery_obj: battery object holding the current state of the battery, as
                            well as the physical constraints of the battery.
            
        Returns:
            request: the change in charge requested of the battery for 
                        the next hour [kWh]
        """       
        # Discharge if current time is during peak hours
        if cur_datetime.hour in self.peak_hours and cur_datetime.dayofweek <= 4:
            request = -1*min(battery_obj.max_charge_rate, 
                             battery_obj.available_to_discharge,
                             df['Usage (kWh)'].loc[cur_datetime])
        # Charge if current time is during trough hours
        elif cur_datetime.hour >= self.trough_hour:
            request = min(battery_obj.max_charge_rate, 
                          battery_obj.available_store_cap)
        # Otherwise, maintain the current charge
        else:
            request = 0
        
        return request

#%% Daily threshold controller
        
class controller_dailythresh(object):
    """Describes a daily threshold battery controller and maintains pre-calculated variables.
    
    Attributes:
        thresh_high_price: float, the high threshold price, above which the battery 
                        discharges itself
        thresh_low_price: float, the low threshold price, below which the battery 
                        charges itself
    """
    thresh_high_quant = 1
    thresh_low_quant = 0
    thresh_high_price = 1
    thresh_low_price = 0
    
    def __init__(self, df, thresh_high_quant, thresh_low_quant):
        """Initializes a controller object
    
        Args:
            thresh_high_quant: float, describes price quantile above which to
                                    discharge the battery.
            thresh_low_quant: float, describes price quantile below which to 
                                    charge the battery.
            df: pandas dataframe with DateTimeIndex giving the electricity usage
                and pricing data for the time interval of interest.
        """
        self.thresh_high_quant = thresh_high_quant
        self.thresh_low_quant = thresh_low_quant
        self.update_thresh(df)

        
    def update_thresh(self, df):
        """Pre-calculates threshold values for the controller to use in each decision.
    
        Args:
            df: pandas dataframe with DateTimeIndex giving the electricity usage
                and pricing data for the time interval of interest.
        Returns:
            None
        """
        self.thresh_high_price = df["Apparent Price ($/kWh)"].quantile(self.thresh_high_quant)
        self.thresh_low_price = df["Apparent Price ($/kWh)"].quantile(self.thresh_low_quant)
        

    def decide(self, df, cur_datetime, battery_obj):
        """Decides how much to charge or discharge the battery based on threshold
            high and low prices.
        
        Args:
            df: dataframe of price data with datetime indexing
            cur_datetime: pandas datetime object giving the time for which this charge
                            decision is being made.
            battery_obj: battery object holding the current state of the battery, as
                            well as the physical constraints of the battery.
            
        Returns:
            request: the change in charge requested of the battery for the next hour [kWh]
        """
        if cur_datetime.hour == 0:
            cur_timestring = str(cur_datetime.year)+ "-" + str(cur_datetime.month) + "-" + str(cur_datetime.day)
            self.update_thresh(df.loc[cur_timestring])
        
        cur_price = df["Apparent Price ($/kWh)"].loc[cur_datetime]
        
        # Discharge if current price is above the high threshold
        if cur_price > self.thresh_high_price:
            request = -1*min(battery_obj.max_charge_rate, 
                             battery_obj.available_to_discharge,
                             df['Usage (kWh)'].loc[cur_datetime])
        # Charge if current price is below the low threshold
        elif cur_price < self.thresh_low_price:
            request = min(battery_obj.max_charge_rate, 
                          battery_obj.available_store_cap)
        # Otherwise, maintain the current charge
        else:
            request = 0
        
        return request