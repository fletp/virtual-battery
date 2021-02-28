# -*- coding: utf-8 -*-
"""
Created on Thu Mar 29 19:36:28 2018

@author: fhp7
"""

import virtual_battery as virbat
import numpy as np
from bokeh.plotting import figure
from bokeh.io import output_file, show

import model_output as out

#%% Example of running the model once straight through
model_df = virbat.acquire_data("Cowen_Green_Button_20180403.csv")
ui_dict = virbat.set_params()
result_dict, result_df = virbat.simulate(ui_dict, model_df)
virbat.visualize(ui_dict, result_dict, result_df, display=False)
virbat.save_results(ui_dict, result_dict, result_df, save_model_df=True)


#%% Example of running the model with two different sets of parameters
###     Note how using the appropriate ui_dict is very important.
model_df = virbat.acquire_data("Cowen_Green_Button_20180403.csv")

ui_dict_A = virbat.set_params(run_name="daily_thresh_20180522",
                              controller_type="daily_threshold")
ui_dict_B = virbat.set_params(run_name="simple_peak_20180522",
                              controller_type="simple_peak")

result_dict_A, result_df_A = virbat.simulate(ui_dict_A, model_df)
result_dict_B, result_df_B = virbat.simulate(ui_dict_B, model_df)

virbat.visualize(ui_dict_A, result_dict_A, result_df_A)
virbat.visualize(ui_dict_B, result_dict_B, result_df_B)

virbat.save_results(ui_dict_A, result_dict_A, result_df_A, save_model_df=True)
virbat.save_results(ui_dict_B, result_dict_B, result_df_B, save_model_df=True)


#%% Example of running the simulation multiple times to create a graph
model_df = virbat.acquire_data("Cowen_Green_Button_20180403.csv")
bat_cap = list(np.arange(7,13.5,0.5))
bat_val = []
for max_cap in bat_cap:
    ui_dict = virbat.set_params(battery_max_capacity=max_cap)
    result_dict, result_df = virbat.simulate(ui_dict, model_df)
    bat_val.append(result_dict['monthly_cost_diff_$'])

output_file(filename=out.out_loc("Varying_Battery_Max_Cap.html", "Multi-Run"))
val_plot = figure(plot_width=600,
                  x_axis_label='Battery Capacity (kWh)',
                  y_axis_label='Avg. Battery Monthly Value')
val_plot.line(x=bat_cap,
              y=bat_val)
show(val_plot)
