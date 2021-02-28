# -*- coding: utf-8 -*-
"""
Created on Wed Feb 14 22:33:28 2018

@author: fhp7
"""
import math

class Battery(object):
    """Describes a battery and manages its state
    
    Attributes:
        model_name: name of the battery model (e.g. "Tesla Powerwall 2")
        max_capacity: maximum capacity of the battery [kWh]
        max_charge_rate: maximum continuous discharge current [kW]
        state_of_charge: current number of kWh stored [kWh]
        round_trip_efficiency: maximum kWh available from battery for every
                                kWh charged into the battery
        charge_efficiency: assuming that the charge and discharge efficiencies
                            are equal and together result in the final round-trip
                            efficiency, this is the charge and discharge efficiency
                            which is applied to every charge and discharge operation
                            of the battery.
        available_to_discharge: amount of useful energy that the battery can
                                discharge, given its current state of charge. This
                                is less than the current state of charge because 
                                of discharge losses.
        available_store_cap: amount of useful energy required to increase the 
                                state of charge to the maximum. This is greater
                                than the difference between the maximum state
                                of charge and the current state of charge because
                                of charging losses.
    """
    model_name = ""
    max_capacity = 0
    max_charge_rate = 0
    state_of_charge = 0
    round_trip_efficiency = 1
    charge_efficiency = 1
    available_to_discharge = 0
    available_store_cap = 1
    
    def __init__(self, model_name, max_capacity, max_charge_rate, 
                 initial_state_of_charge, round_trip_efficiency):
        self.model_name = model_name
        self.max_capacity = max_capacity
        self.max_charge_rate = max_charge_rate
        self.round_trip_efficiency = round_trip_efficiency
        self.charge_efficiency = math.sqrt(round_trip_efficiency)
        self._update_charge_values(initial_state_of_charge)
        
        
    def charge(self, request):
        """Adds or subtracts charge from a battery object
        
        Maintains valid state of the battery by preventing total charge and
            rate of charge from exceeding their limits. Also enforces the 
            battery's round-trip efficiency.
        
        Args:
            request: amount of energy sent to the battery or delivered by
                            the battery, positive to send energy to the battery,
                            negative to deliver energy from the battery [kWh]
        Returns:
            None
        """
        assert (abs(request) <= self.max_charge_rate), "You tried to charge or discharge the battery faster than it is able to!"
            
        # Enforce charge and discharge losses
        if request >= 0:
            proposed_charge = self.state_of_charge + request*self.charge_efficiency
        else:
            proposed_charge = self.state_of_charge + request/self.charge_efficiency
        
        assert (proposed_charge >= 0), "You drained the battery, there is no juice left!"
        assert (proposed_charge <= self.max_capacity), "You can't fill the battery over its maximum capacity!"
        
        self._update_charge_values(proposed_charge)
        
        
    def _update_charge_values(self, proposed_charge):
        self.state_of_charge = proposed_charge
        self.available_to_discharge = self.state_of_charge*self.charge_efficiency
        self.available_store_cap = (self.max_capacity - self.state_of_charge)/self.charge_efficiency
