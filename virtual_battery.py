# -*- coding: utf-8 -*-
"""
Created on Wed Feb 14 23:23:59 2018

@author: fhp7
"""
###Module imports
# General Python modules
import os
import pandas as pd
import numpy as np
from bokeh.io import output_file, show, save

# virtual battery-specific packages
import data_import
import battery_model
import battery_controller
import model_output as out


def acquire_data(data_file_name, reading_freq='H', time_zone='America/New_York',
                 nyiso_data_type='damlbmp', nyiso_zone='CENTRL'):
    """Sets up the data from a CSV of NYSEG Smart Meter data and downloads the
        matching NYISO pricing data from online. Uses data_import.py heavily.
    
    Args:
        data_file_name: string denoting the filename of the CSV to be used as
                            electricity usage data for virtual_battery. Should
                            be in the format "file_name.csv" Thsi file must be
                            located in the Meter_Data_Files folder, which must
                            be on the same level as the virtual-battery project
                            folder.
        reading_freq: pandas frequency code in string form. See pandas documentation
                        on frequencies of timestamp and period objects for further
                        information. The default 'H' stands for hourly frequency.
        time_zone: string denoting the time zone to be used for time calculations.
                    This is especially important for dealing with Daylight Savings
                    Time.
        nyiso_data_type: string denoting the type of data to be downloaded from NYISO,
                            For example, 'damlbmp' stands for 'day ahead market location
                            based marginal price'. Find other appropriate strings by going
                            to the NYISO data portal (see example URL in documentation
                            for download_nyiso_data function), and looking at the entry
                            in the url right after .../csv/
        nyiso_zone: string denoting the NYISO zone of the requested data
            
    Returns:
        model_df: pandas dataframe with columns representing the electricity
                    usage data as well as the NYISO day ahead location based
                    marginal prices.
    """     
    # Find file path of desired meter data file and read it in 
    #       using meter_reader module
    data_folder_path = os.path.join(os.pardir, 'Meter_Data_Files', data_file_name)
    model_df = data_import.read_meter_data(filepath = data_folder_path, 
                                           reading_freq = reading_freq, 
                                           time_zone = time_zone)
    
    # Read NYISO day-ahead prices into the dataframe
    model_df = data_import.add_nyiso_data(model_df, 
                                          data_type = nyiso_data_type,
                                          zone = nyiso_zone,
                                          time_zone = time_zone)
    return model_df


def set_params(**kwargs):
    """Set the parameters for the virtual_battery simulation.
    
    Args:
        kwargs: arguments sharing the exact name of the model parameters whose
                    defaults are set in user_input.py. Each properly named argument
                    passed this function will replace the default value of that
                    parameter from user_input.py with the value that was passed
                    to this function.
    Returns:
        ui_dict: a dictionary of the named parameters used for future
                    virtual_battery simulation runs.
    """
    # Read default user input variables from user_input.py
    import user_input as ui
    ui_dict = {k:v for (k,v) in ui.__dict__.items() if not("__" in k)}
    
    # Overwrite variables from user_input.py with values that the user passed
    #   to this function, if desired.
    for key, value in kwargs.items():
        if key in ui_dict:
            ui_dict[key] = value
    
    return ui_dict



def simulate(ui_dict, model_df): 
    """Run the hourly simulation of battery charge decisions.
    
    In summary, this function takes the following steps:
    1) It takes electricity usage and pricing data from model_df
    2) It creates battery and controller objects from the parameters held in
        ui_dict.
    3) It iterates through each hour in the model_df, making charge decisions 
        based on the data held in each hour
    See comments throughout for a more detailed description of the steps 
    carried out in this function.
    
    Args:
        ui_dict: dictionary generated by set_params function
        model_df: pandas dataframe with columns representing the electricity
                    usage data as well as the NYISO day ahead location based
                    marginal prices.
            
    Returns:
        tuple of result_dict and result_df
        result_dict: dictionary of summary statistics for a virtual battery
                        simulation run
        result_df: pandas dataframe representing the hourly state of the battery
                    through the simulation, as well as charging decisions
                    made by the controller and the pricing information the 
                    controller used. This dataframe stores beginning of the
                    hour data.
    """       
    result_df = model_df.copy()
    
    ### Add pricing columns to dataframe
    # Convert NYISO LBMP to $/kWh
    result_df["LBMP ($/kWh)"] = result_df["LBMP ($/MWHr)"].apply(lambda x: x/1000)
    
    # Add NYSEG time-dependent delivery charge column
    peak_hours = np.all([result_df.index.hour >= ui_dict['peak_price_hours'][0], 
                         result_df.index.hour <= ui_dict['peak_price_hours'][-1],
                         result_df.index.weekday <= 4], 
                        axis = 0)
    result_df.loc[np.logical_not(peak_hours), "NYSEG Delivery Charge ($/kWh)"] = ui_dict['delivery_charge_offpeak']
    result_df.loc[peak_hours, "NYSEG Delivery Charge ($/kWh)"] = ui_dict['delivery_charge_peak']
    
    # Calculate apparent $/kWh charge to customer
    result_df["Apparent Price ($/kWh)"] = result_df["LBMP ($/kWh)"] + result_df["NYSEG Delivery Charge ($/kWh)"]
    
    ### Instantiate Battery and Controller objects
    # Initialize a Battery object to be charged and discharged
    battery = battery_model.Battery(model_name = ui_dict['battery_model_name'], 
                                    max_capacity = ui_dict['battery_max_capacity'],
                                    max_charge_rate = ui_dict['battery_max_charge_rate'],
                                    initial_state_of_charge = ui_dict['battery_initial_state_of_charge'],
                                    round_trip_efficiency = ui_dict['battery_round_trip_efficiency'])
    
    # Set up the controller, using the make_controller function, which 
    #   intakes all the possible input values for all possible controllers,
    #   then selects which ones it needs based on the given controller_type.
    controller = battery_controller.make_controller(controller_type=ui_dict['controller_type'],
                                                    df = result_df,
                                                    peak_hours=ui_dict['peak_hours'],
                                                    trough_hour=ui_dict['trough_hour'],
                                                    thresh_high_quant=ui_dict['thresh_high_quant'],
                                                    thresh_low_quant=ui_dict['thresh_low_quant'])
    
    # Initialize new columns to hold beginning-of-hour battery states
    result_df['Charge Decision (kWh)'] = np.nan
    result_df['State of Charge (kWh)'] = np.nan
    result_df['Available to Discharge (kWh)'] = np.nan
    result_df['Available Storage Capacity (kWh)'] = np.nan
    
    ### Run simulation by stepping through the dataframe
    # Define a battery state updating function
    def step_result_df(bat_df, row, battery, controller):
        # Record beginning of hour battery state
        row['State of Charge (kWh)'] = battery.state_of_charge
        row['Available to Discharge (kWh)'] = battery.available_to_discharge
        row['Available Storage Capacity (kWh)'] = battery.available_store_cap
        
        # Make a charging decision using the controller, then record 
        #   and implement it
        charge_decision = controller.decide(df = bat_df,
                                            cur_datetime = row.name, 
                                            battery_obj = battery)
        battery.charge(charge_decision)
        row["Charge Decision (kWh)"] = charge_decision
    
    # Apply the battery state updating function to every row in the dataframe
    result_df.apply(lambda row: step_result_df(result_df, row, battery, controller), axis=1)
    
    # Generate the net electricity purchased column
    result_df["Net Electricity Purchased (kWh)"] = result_df['Usage (kWh)'] + \
                                                    result_df["Charge Decision (kWh)"]
    
    ### Generate numeric results and make a dictionary of them
    result_dict = out.summary_stats(result_df,
                                    ui_dict['peak_price_hours'],
                                    ui_dict['hours_per_month'])
    return (result_dict, result_df)
    

def visualize(ui_dict, result_dict, result_df, display=True):
    """Report results, including total electricity cost, graphs of usage, etc.
    
    Args:
        ui_dict: dictionary generated by set_params function
        result_dict: dictionary of summary statistics for a virtual battery
                        simulation run
        result_df: pandas dataframe representing the hourly state of the battery
                    through the simulation, as well as charging decisions
                    made by the controller and the pricing information the 
                    controller used.  This dataframe stores beginning of the
                    hour data.
        display: boolean, if true, Bokeh plots will be displayed as they are
                    created in a browser window. If false, the plots will
                    be saved without being shown.
                    
    Returns:
        None, but saves plots in the Output_Files folder and prints numerical
            results to the console.
    """    
    ### Generate Bokeh plots
    # Summarize the consumer's apparent prices
    nyseg_price_plot = out.describe_nyseg_prices(result_df)
    # Summarize the consumer's hourly household energy usage
    hourly_energy_usage_plot = out.describe_energy_usage(result_df)
    # Summarize daily maximum and minimum battery charges
    battery_charge_plot = out.describe_battery_charge(result_df, ui_dict)
    
    ### Display outputs
    print(result_dict)
    print(result_df.info())
    print(result_df.describe())
    output_file(filename=out.out_loc("nyseg_price_plot.html", ui_dict["run_name"]),
                title="Illustration of Hourly Pricing Scheme")
    if display:
        show(nyseg_price_plot)
    else:
        save(nyseg_price_plot)
    
    output_file(filename=out.out_loc("hourly_energy_usage_plot.html", ui_dict["run_name"]),
                title="Illustration of Hourly Energy Usage")
    if display:
        show(hourly_energy_usage_plot)
    else:
        save(hourly_energy_usage_plot)
        
    output_file(filename=out.out_loc("battery_charge_plot.html", ui_dict["run_name"]),
                title="Illustration of Battery Charge Behavior")
    if display:
        show(battery_charge_plot)
    else:
        save(battery_charge_plot)


def save_results(ui_dict, result_dict, result_df=None, save_model_df=False):
    """Save results to CSV files.
    
    Args:
        ui_dict: dictionary generated by set_params function
        result_dict: dictionary of summary statistics for a virtual battery
                        simulation run
        result_df: pandas dataframe representing the hourly state of the battery
                    through the simulation, as well as charging decisions
                    made by the controller and the pricing information the 
                    controller used. This dataframe stores beginning of the
                    hour data.
        save_model_df: boolean, if True, the columns of result_df which were
                        originally created as model_df in the acquire_data function
                        will be saved as a separate CSV for use in later model runs.
                        This is especially useful if loss of internet connection
                        is expected, because NYISO data is downloaded from the internet.
    Returns:
        None
    """
    # Write user inputs dictionary as a dataframe
    ui_dict_df = pd.DataFrame.from_dict(ui_dict,
                                        orient='index')
    ui_dict_df.rename(columns={0:'Values'}, inplace=True)
    
    # Write model outputs dictionary as a dataframe
    result_dict_df = pd.DataFrame.from_dict(result_dict,
                                            orient='index')
    result_dict_df.rename(columns={0:'Values'}, inplace=True)
    
    # Write header and separator rows for the dataframe
    head_df = pd.DataFrame.from_dict({"Model Outputs":"---------"},
                                     orient='index')
    sep_df = pd.DataFrame.from_dict({"User Inputs":"---------"},
                                    orient='index')
    
    # Concatenate dataframes together and write as a CSV
    result_dict_df = pd.concat([head_df, result_dict_df, sep_df, ui_dict_df])
    result_dict_df.to_csv(out.out_loc("result_dict.csv", ui_dict["run_name"]))   
    
    if result_df is not None:
        # Save the result dataframe for future reference
        result_df.to_csv(out.out_loc("result_df.csv", ui_dict["run_name"]))
        
    if save_model_df is True:
        model_df = result_df[['Usage (kWh)', 'Reported NYSEG Price ($/kWh)', 
                              'LBMP ($/MWHr)', 'Marginal Cost Losses ($/MWHr)',
                              'Marginal Cost Congestion ($/MWHr)']]
        model_df.to_csv(out.out_loc("model_df.csv", ui_dict["run_name"]))
