# -*- coding: utf-8 -*-
"""
Created on Tue May 22 11:13:00 2018

@author: fhp7
"""
import urllib.request
import zipfile
import pandas as pd

def read_meter_data(filepath, reading_freq, time_zone):
    """Read a smart meter data CSV file into a pandas dataframe
    
    Args:
        filepath: string denoting a filepath to a CSV file containing the
                    smart meter data. The format of this file must be very
                    specific for this function to work. See the Meter_Data_Files
                    folder that accompanies virtual-battery for examples.
        reading_freq: string denoting the frequency of readings. See documentation
                        on pandas period objects for all the options, but 'H'
                        is almost surely what will be used.
        time_zone: string denoting the time zone of the data. All points in
                    New York State should be using 'America/New_York' as is assumed
                    in user_input.py
        
    Returns:
        readings_df: pandas dataframe with datetimeindex containing columns for
                        electricity usage [kWh] and electricity price reported 
                        by NYSEG [$/kWh]
    """
    # Read in CSV file in Energy Manager format, and set up a datetime index
    readings_df = pd.read_csv(filepath)
    readings_df.index = pd.DatetimeIndex(readings_df['Date'],
                                         tz='Etc/GMT+5')
    readings_df = readings_df.asfreq(reading_freq)
    readings_df.index = readings_df.index.tz_convert(time_zone)
    
    # TODO: Remove this temporary fix once the time-zone data from Energy Manager
    #           is better understood. For now, this fills all NA's (probably due to
    #           Daylight Savings Time) with the previous non-NA value.
    readings_df = readings_df.fillna(method='ffill')
    
    # Select desired columns and rename
    readings_df = readings_df.drop(['Date'], axis=1)
    readings_df = readings_df.rename(columns = {'Quantity':'Usage (kWh)',
                                                'Cost':'Reported NYSEG Price ($/kWh)'})
    
    #TODO: remove this section, it is present for debugging purposes only
    #readings_df['Hourly Charge'] = readings_df['Usage (kWh)'] * readings_df['Reported NYSEG Price ($/kWh)']
    #monthly_bill = readings_df.groupby(readings_df.index.month).sum()
    #print(monthly_bill)
    
    assert (not(readings_df.isnull().values.any())), "Null values present in the readings dataframe in meter_reader!"
    
    return readings_df


def add_nyiso_data(df, data_type, zone, time_zone):
    """Adds NYISO data to a timestamp-indexed pandas data frame.
    
    Args:
        df: pandas dataframe with continuous timestamp index (no jumps)
        data_type: string denoting the type of data to be downloaded from NYISO,
                    For example, 'damlbmp' stands for 'day ahead market location
                    based marginal price'. Find other appropriate strings by going
                    to the NYISO data portal (see example URL in documentation
                    for download_nyiso_data function), and looking at the entry
                    in the url right after .../csv/
        zone: string denoting the NYISO zone of the requested data
        time_zone: string denoting the time zone of the data that is being requested
                        All NYISO data should use 'America/New_York'.
        
    Returns:
        df: the original df dataframe but with desired NYISO data added as new
            columns. The join is performed based on the datetime index of the 
            original df dataframe.
    """
    # Recover timestamp indices of first and last rows of df
    start_time = df.index[0]
    end_time = df.index[-1]
    
    # Convert start and end timestamps into pandas period objects for easy iteration
    start_per = start_time.to_period().asfreq(freq = 'M', how = 'start')
    end_per = end_time.to_period().asfreq(freq = 'M', how = 'start')
    
    # Download NYISO data for all months between start_time and end_time, inclusive.
    per = start_per
    nyiso_df = pd.DataFrame()
    while per <= end_per:
        nyiso_df = pd.concat([nyiso_df, 
                              download_nyiso_csv(per.to_timestamp(), data_type, zone)
                              ])
        per = per + 1

    # Select only the desired geographic zone of data, if data is grouped by zones
    if zone != None:
        nyiso_df = nyiso_df.loc[nyiso_df["Name"] == zone,]
        nyiso_df.drop(["Name", "PTID"], axis = 1, inplace = True)
    
    # Convert nyiso_df index to pandas timestamps
    nyiso_df["Time"] = nyiso_df["Time Stamp"].apply(pd.to_datetime, 
                                                    format = '%m/%d/%Y %H:%M')
    nyiso_df.drop("Time Stamp", axis = 1, inplace = True)
    nyiso_df.set_index("Time", drop = True, inplace = True)
    nyiso_df.index = nyiso_df.index.tz_localize(tz = time_zone, 
                                                ambiguous = 'infer')
    
    # Join nyiso_df and df based on their timestamp indices
    df = pd.concat([df, nyiso_df], axis = 1, join_axes = [df.index])
    
    return df


def download_nyiso_csv(month, data_type, zone = None):
    """Downloads a NYISO csv dataset for a specific data type, month, and zone.
    
    Args:
        month: string denoting the first day of the month to be downloaded in
                yyyymmdd format
        data_type: string denoting the type of NYISO data to retrieve,
                    examples include "damlbmp" which stands for "day ahead 
                    market location based marginal price" or "outSched" for 
                    "outage schedule"
        zone: string denoting the NYISO geographic zone of the data to be 
                    requested. This is required if data_type == "damlbmp"
        
    Returns:
        df: pandas dataframe of the NYISO csv file for the entire month requested
    """
    # Build the necessary url to access the NYISO data
    url = build_nyiso_url(month, data_type, zone)
    
    # Download the zip folder to a temporary file location, 
    #   then open the zip folder into the object zf
    zip_folder_path, headers = urllib.request.urlretrieve(url)
    zf = zipfile.ZipFile(zip_folder_path)
        
    #TODO: increase efficiency by only reading the files from NYISO that contain the desired days
    # For each file contained in zf, read the csv and concatenate it with 
    #   the other csvs for this month to create a month-long csv
    df = pd.DataFrame()
    for file in zf.filelist:
        temp_df = pd.read_csv(zf.open(file.filename))
        df = pd.concat([df,temp_df])

    return df


def build_nyiso_url(month, data_type, zone):
    """Builds a string that is the URL address for a NYISO data file.
    
    Args:
        month: pandas timestamp for the first day of the month of data requested
        data_type: string denoting the type of NYISO data to retrieve,
                    examples include "damlbmp" which stands for "day ahead 
                    market location based marginal price" or "outSched" for 
                    "outage schedule"
        zone: string denoting the NYISO geographic zone of the data to be 
                    requested. This is required if data_type == "damlbmp"
        
    Returns:
        url: string giving the URL address of a NYISO data file, similar to the
                following example URL:
                'http://mis.nyiso.com/public/csv/damlbmp/20180201damlbmp_zone_csv.zip'
    """    
    # Raise an error if the zone isn't defined when it needs to be.
    if data_type == 'damlbmp' and zone == None:
        raise RuntimeError("Zone must be specified when data_type == 'damlbmp'")
        
    def _to_yyyymmdd(timestamp):
        """Returns the yyyymmdd format date given a pandas timestamp object"""
        s = str(timestamp)
        r = s[0:4] + s[5:7] + s[8:10]
        return r
    
    url = "http://mis.nyiso.com/public/csv/"
    url = url + data_type + "/"
    url = url + _to_yyyymmdd(month) + data_type
    if zone != None:
        url = url + "_zone"
    url = url + "_csv.zip"
    
    return url