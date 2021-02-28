# -*- coding: utf-8 -*-
"""
Created on Mon Mar 19 16:16:47 2018

@author: fhp7
"""
# Import standard Python packages
import pandas as pd
import numpy as np
import pickle
import os

# Import parts of the Bokeh library for plotting
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, Whisker
from bokeh.layouts import row, column

def out_loc(output_name, run_name):
    """Gives the output file path for a virtual battery output.
    
    Args:
        output_name: string denoting the type of output to be saved to this
                        filepath which must include the file type
                        (e.g. "result_df.csv")
        run_name: string denoting the name of the model run/scenario that this
                    output is for (e.g. "simple_peak")
                    
    Returns:
        out_path: string denoting the absolute filepath in this system for the
                    file
    """
    
    data_file_name = run_name + "_" + output_name
    out_path = os.path.join(os.pardir, 'Output_Files', data_file_name)
    return out_path

def read_back_file(output_name, run_name):
    """Reads back a previously saved virtual battery output file that was in
            serialized (in Python-speak "pickled") format. This function relies
            on the fact that virtual battery output files are saved using file
            names given by the out_loc function.
    
        Args:
            output_name: string denoting the type of output to be retrieved from
                            this filepath which must include the file type
                            (e.g. "result_df.p")
            run_name: string denoting the name of the model run/scenario that this
                        output file is from (e.g. "simple_peak")
                    
        Returns:
            obj: the Python object that had been saved in serialized format, now
                    ready for immediate use in Python code.
    """
    data_file_name = run_name + "_" + output_name
    in_path = os.path.join(os.pardir, 'Output_Files', data_file_name)
    obj = pickle.load(open(in_path, "rb"))
    return obj

def summary_stats(result_df, peak_hours, hours_per_month):
    """Reads back a previously saved virtual battery output file that was in
        serialized (in Python-speak "pickled") format.
    
        Args:
            result_df: pandas dataframe with datetime indexing. Many columns with
                        very specific names are required, so read the code in
                        this function carefully and copy/paste names if you
                        are having trouble.
            peak_hours: list of hours of the day in 0, 1, 2,..., 23 format which
                            are considered "peak" hours by this run of the
                            virtual battery simulation.
            hours_per_month: float number representing the assumed number of
                                hours per month. Used for calculating monthly
                                summary values.
                    
        Returns:
            d: dictionary of summary statistics for this run of the virtual
                battery simulation. The dictionary is organized with (key, value)
                pairs meaning ("statistic name", statistic value).
    """
    # Initialize the dictionary in which all the summary statistics will be stored
    d = {}
    
    # Calculate the number of hours in the study period, for use in time conversions
    n_hours = result_df.shape[0]
    
    # Make a separate dataframe containing only the records for peak hours
    peak_hours_df = result_df[(result_df.index.hour >= peak_hours[0]) & (result_df.index.hour <= peak_hours[-1])]
    
    # Scenario: without battery
        # Total Cost
        # Peak ratio: Electricity purchased during peak/Total Electricity Purchased
    d['total_cost_no_battery'] = np.dot(result_df["Usage (kWh)"], result_df["Apparent Price ($/kWh)"])
    d['total_electricity_purchases_no_battery'] = result_df["Usage (kWh)"].sum()
    d['peak_electricity_purchases_no_battery'] = peak_hours_df["Usage (kWh)"].sum()
    d['peak_ratio_no_battery'] = d['peak_electricity_purchases_no_battery']/d['total_electricity_purchases_no_battery']
    
    # Scenario: with battery
        # Total Cost
        # Peak ratio: Electricity purchased during peak/Total Electricity Purchased
    d['total_cost_with_battery'] = np.dot(result_df["Net Electricity Purchased (kWh)"], result_df["Apparent Price ($/kWh)"])
    d['total_electricity_purchases_with_battery'] = result_df["Net Electricity Purchased (kWh)"].sum()
    d['peak_electricity_purchases_with_battery'] = peak_hours_df["Net Electricity Purchased (kWh)"].sum()
    d['peak_ratio_with_battery'] = d['peak_electricity_purchases_with_battery']/d['total_electricity_purchases_with_battery']
    
    # Comparing Scenarios: Absolute Metrics
    d['total_cost_diff'] = d['total_cost_no_battery'] - d['total_cost_with_battery']
    d['total_electricity_purchases_diff'] = d['total_electricity_purchases_with_battery'] - d['total_electricity_purchases_no_battery']
    d['peak_electricity_purchases_diff'] = d['peak_electricity_purchases_with_battery'] - d['peak_electricity_purchases_no_battery']
    
    # Comparing Scenarios: Monthly Metrics
    d['monthly_cost_diff_$'] = d['total_cost_diff']/n_hours*hours_per_month
    d['monthly_electricity_purchases_diff'] = d['total_electricity_purchases_diff']/n_hours*hours_per_month
    d['monthly_peak_electricity_purchases_diff'] = d['peak_electricity_purchases_diff']/n_hours*hours_per_month
    d['peak_ratio_diff'] = d['peak_ratio_with_battery'] - d['peak_ratio_no_battery']
    
    return d
    

def describe_nyseg_prices(result_df):
    """Generates a graph of NYSEG prices for each hour of the day.
    
    Args:
        result_df: pandas dataframe with datetime indexing. Many columns with
                        very specific names are required, so read the code in
                        this function carefully and copy/paste names if you
                        are having trouble.
    Returns:
        mean_price_plot: a Bokeh figure object customized to show the NYSEG
                            prices for each hour of the day over the time period
                            given by the datetime index of result_df. See the
                            outputs of the virtual battery model for examples
                            (e.g. "simple_peak_hourly_nyseg_price.html")
    """
    ### Data Preparation
    
    # TODO: Remove this weekday-only setting if necessary later
    result_df = result_df[result_df.index.weekday <= 4]
    
    # Generate the data series necessary for making this plot, all of which are
    #   grouped by hour of the day. For example, all the 3PMs in the whole data
    #   series passed to this function are summarized together. Statistics
    #   calculated include the mean, standard deviation, max, and min.
    hourly_mean_price_series = result_df['Apparent Price ($/kWh)'].groupby(result_df.index.hour).mean()
    hourly_std_price_series = result_df['Apparent Price ($/kWh)'].groupby(result_df.index.hour).std()
    hourly_max_price_series = result_df['Apparent Price ($/kWh)'].groupby(result_df.index.hour).max()
    hourly_min_price_series = result_df['Apparent Price ($/kWh)'].groupby(result_df.index.hour).min()
    hourly_deliv_price_series = result_df['NYSEG Delivery Charge ($/kWh)'].groupby(result_df.index.hour).mean()
    
    # Currently unused, these generate some of the data series above, but
    #   split the months into individually identifiable records as well as the
    #   hours. For example. The series shown above include all 3PMs in the
    #   result_df dataframe. This series would split February 3PMs to be separate
    #   from January 3PMs, etc.
    mon_hourly_mean_price_series = result_df['Apparent Price ($/kWh)'].groupby([result_df.index.hour, result_df.index.month]).mean()
    mon_hourly_std_price_series = result_df['Apparent Price ($/kWh)'].groupby([result_df.index.hour, result_df.index.month]).std()
    
    # Make a pandas dataframe from the series calculated above, then calculate
    #   some new columns necessary for plotting.
    hourly_price_df = pd.concat([hourly_mean_price_series, 
                                 hourly_std_price_series, 
                                 hourly_deliv_price_series,
                                 hourly_max_price_series,
                                 hourly_min_price_series], axis = 1)
    hourly_price_df.columns = ['Avg. Apparent Price ($/kWh)', 
                               'Std. Apparent Price ($/kWh)', 
                               'NYSEG Delivery Charge ($/kWh)',
                               'Max. Apparent Price ($/kWh)',
                               'Min. Apparent Price ($/kWh)']
    hourly_price_df['Upper ($/kWh)'] = hourly_price_df['Avg. Apparent Price ($/kWh)'] + hourly_price_df['Std. Apparent Price ($/kWh)']
    hourly_price_df['Lower ($/kWh)'] = hourly_price_df['Avg. Apparent Price ($/kWh)'] - hourly_price_df['Std. Apparent Price ($/kWh)']
    hourly_price_df['x_loc_plot'] = hourly_price_df.index + 0.5
    
    # Calculate the maximum y-axis value needed to display the plot nicely.
    plot_y_max = hourly_price_df['Max. Apparent Price ($/kWh)'].max()*1.05
    
    # Convert the dataframe into a Bokeh-specific data type, the ColumnDataSource
    hourly_gph_src = ColumnDataSource(hourly_price_df)
    
    ### Building the graph
    # Generate a plot shell
    mean_price_plot = figure(plot_width=600,
                             x_axis_label='Hour of the Day',
                             y_axis_label='Avg. Apparent Price ($/kWh)',
                             x_range=[0,24],
                             y_range=[0,plot_y_max])
    # Add vertical bars
    mean_price_plot.vbar(x='x_loc_plot', 
                         width=1, 
                         top='Avg. Apparent Price ($/kWh)',
                         source=hourly_gph_src,
                         fill_color='deepskyblue',
                         line_color='black', 
                         fill_alpha=0.5,
                         legend=' Avg. Apparent Price ($/kWh)') # Leading space is important for legend interpretation
    mean_price_plot.vbar(x='x_loc_plot',
                         width=1,
                         top='NYSEG Delivery Charge ($/kWh)',
                         source=hourly_gph_src,
                         fill_color='steelblue',
                         line_color='black',
                         fill_alpha=1,
                         legend=' NYSEG Delivery Charge ($/kWh)') # Leading space is important for legend interpretation
    # Add error bars
    mean_price_plot.add_layout(Whisker(source=hourly_gph_src,
                                       base='x_loc_plot', 
                                       upper='Max. Apparent Price ($/kWh)', 
                                       lower='Min. Apparent Price ($/kWh)'))
    # Add a legend
    mean_price_plot.legend.location = 'top_left'
    return mean_price_plot
    
    
def describe_battery_charge(result_df, ui_dict):
    """Generates several plots, presented together, which describe the battery's
            state of charge trends.
            
    Args:
        result_df: pandas dataframe with datetime indexing. Many columns with
                        very specific names are required, so read the code in
                        this function carefully and copy/paste names if you
                        are having trouble.
        battery: dictionary containing the simulation parameters, particularly
                    the 'battery_max_capacity'
    
    Returns:
        layout: a Bokeh figure object customized to show the battery state
                    trends (max daily charge, min daily charge, daily cycle depth)
                    over the time period given by the datetime index of result_df.
                    See the outputs of the virtual battery model for examples
                    (e.g. "simple_peak_battery_charge_graphs.html")
    
    """
    ### Data Preparation
    # Calculate numerical values for daily minimum charge, maximum charge
    #   and duty cycle depth.
    daily_min_series = result_df['State of Charge (kWh)'].resample('D').min()
    daily_max_series = result_df['State of Charge (kWh)'].resample('D').max()
    daily_charge_df = pd.concat([daily_min_series, daily_max_series], axis = 1)
    daily_charge_df.columns = ["Min State of Charge (kWh)", "Max State of Charge (kWh)"]
    daily_charge_df['Cycle Depth (kWh)'] = daily_charge_df['Max State of Charge (kWh)']-daily_charge_df['Min State of Charge (kWh)']
    
    ### Building the graphs
    # Since three almost identical histograms are required, another helper
    #   function is defined here. This makes it so that all the graphs change
    #   together if a formatting change needs to be made.
    def chg_hist(column, x_lab):
        # Use the numpy histogram function to generate histogram data
        #   "column" is the name of the column in the daily_charge_df to be
        #   used when making the histogram.
        hist, edges = np.histogram(daily_charge_df[column], range=[0,ui_dict['battery_max_capacity']])
        
        bin_width = edges[1]-edges[0]
        
        # Normalize the histogram so column heights add to 1
        hist = hist/len(daily_charge_df)
        
        # Generate a Bokeh plot using the histogram data generated above
        #   Note the use of the argument x_lab to define the x-axis label
        #   for the histogram.
        plot = figure(plot_width=600,
                      plot_height=250,
                      x_axis_label=x_lab,
                      y_axis_label="Normalized Frequency")
        plot.vbar(x=edges[:-1]+bin_width/2,
                  width=bin_width,
                  top=hist,
                  line_color='black', 
                  fill_alpha=0.5)
        return plot
    
    # Generate specific histograms
    max_chg_hist = chg_hist("Max State of Charge (kWh)",
                            "Daily Maximum Charge (kWh)")
    min_chg_hist = chg_hist("Min State of Charge (kWh)",
                            "Daily Minimum Charge (kWh)")
    cycle_hist = chg_hist("Cycle Depth (kWh)", 
                          "Daily Cycle Depth (kWh)")
    
    # Place histograms in a layout and display them
    layout = column(max_chg_hist, min_chg_hist, cycle_hist)
    return layout
    

def describe_energy_usage(result_df):
    """Generates several plots, presented together, which describe the meter
        data for this run of the virtual battery simulation.
            
    Args:
        result_df: pandas dataframe with datetime indexing. Many columns with
                        very specific names are required, so read the code in
                        this function carefully and copy/paste names if you
                        are having trouble.
    
    Returns:
        layout: a Bokeh figure object customized to show the electricity usage
                    from smart meter data over the time period given by the 
                    datetime index of result_df. See the outputs of the virtual
                    battery model for examples.
                    (e.g. "simple_peak_battery_charge_graphs.html")
    
    """
    ### Data Preparation
    # Calculate a range of x-axis values which will be displayed for all plots
    x_range = [min(result_df["Net Electricity Purchased (kWh)"]), max(result_df["Net Electricity Purchased (kWh)"])]
    
    ### Building the graphs
    # Since two almost identical histograms are required, another helper
    #   function is defined here. This makes it so that all the graphs change
    #   together if a formatting change needs to be made.
    def use_hist(column, x_lab):
        # Calculate histogram data using numpy's histogram function
        hist, edges = np.histogram(result_df[column], range=x_range)
        bin_width = edges[1]-edges[0]
        
        # Normalize the histogram so column heights add to 1. len(result_df) is
        #   equal to the total number of observations made in the virtual
        #   battery simulation run.
        hist = hist/len(result_df)
        
        # Generate a Bokeh figure object and add vertical bars.
        plot = figure(plot_width=600,
                      plot_height=300,
                      x_axis_label=x_lab,
                      y_axis_label="Normalized Frequency")
        plot.vbar(x=edges[:-1]+bin_width/2,
                  width=bin_width,
                  top=hist,
                  line_color='black', 
                  fill_alpha=0.5)
        return plot
    
    # Generate specific plots
    usage_hist = use_hist("Usage (kWh)", 
                          "Hourly Household Electricity Demand (kWh)")
    purch_hist = use_hist("Net Electricity Purchased (kWh)",
                          "Hourly Net Electricity Purchased (kWh)")
    
    # Group plots together in a layout and return
    layout = column(usage_hist, purch_hist)
    return layout