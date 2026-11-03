# -*- coding: utf-8 -*-
"""
Created on Sat Aug  2 12:13:52 2025

author: Kenneth W. Crossley

This app defines a GUI for entering and organizing metadata for 
electrochemistry and synchrotron experiments.

Debugging and user warning is pretty good, but if you manage to break it, 
please let me know: kenneth.crossley@psi.ch or crossley.kenneth@gmail.com

The resulting .yaml/.json file contains all the metadata in a single document, 
in a machine readable format. You are encouraged to extensively use the Notes
field and include appropriate linked files for easier tracing in the future.

It is also possible to build Excell-like master data csv files with user-selected
parameters (i.e. what is interesting to you) in a human readible format.

Some notes on variable naming and structure:
    frm = Frame
    lbl = Label
    str = StringVar
    ent = tkinter entry widget with an associated StringVar
    clicked = indicates user variable choice from dropdown menu
    drop = OptionMenu, with an associated clicked StringVar
    
    fc = flow cell # used to distinguish unique variables and functions
    
    Each tab (RDE vs. Flow cell) has its own variables/names so that there is 
    no namespace pollution if the user switches between tabs (z.b. multiple 
    labmates running different kinds of tests with the same computer). 
    This definitely makes the program longer, but tracable. A better top-down
    programmer could simplify it. 
    

"""
#%% 1: import libraries/modules
from __future__ import annotations
from typing import Callable

import os
from pathlib import Path

import pandas as pd
import scipy.constants as sc
from numpy import arange

import tkinter as tk
from tkinter import ttk
## for file loading
from tkinter import filedialog as fd 
## erros and display
from tkinter import messagebox

## for file saving
from datetime import datetime
import yaml
import json

import time
from dataclasses import dataclass, field
from typing import Optional


#%% 2: functions for file handling , RDE ink calculation, RDE GUI inputs

def browseInks():
    """
    Open a file dialog to select a CSV ink recipe book and load it into the GUI.

    On file selection, updates the recipe label, loads the CSV into the global
    ``recipes`` DataFrame, refreshes the ink dropdown with recipe names from the
    first column, and repopulates the component/unit labels to match the new
    recipe's columns. Does nothing if the dialog is cancelled.

    Globals:
        clicked (bool): Set to ``True`` to indicate a file has been loaded.
        recipes (pd.DataFrame): Populated with the contents of the selected CSV.
        ink_drop_options (list): Updated with ink names from the first column.
        drop_inks: Ink dropdown widget, refreshed via ``update_ink_dropdown_menu()``.
        clicked_ink: Tkinter StringVar for the currently selected ink.

    Returns:
        None
    """
    global clicked, recipes, ink_drop_options, drop_inks, clicked_ink
    clicked = True
    filenames = fd.askopenfilename(
        title='Select an Ink Recipe File',
        filetypes=[('ink recipe files', '*.csv'), ('All files', '*.*')]
    )
    
    # Only proceed if a file was selected
    if filenames:
        # Change opened files label contents
        lbl_browser_files_to_open.configure(text='Recipe Book: ' + filenames)
        
        ## Dataframe loading
        recipes = pd.read_csv(filenames)
        
        ## Update ink dropdown menu options 
        # global ink_drop_options
        ink_drop_options = recipes[recipes.columns[0]].values.tolist()
        
        ## Update the existing OptionMenu with new options
        update_ink_dropdown_menu()
        
        ## Populate component/unit labels for ink calculation based on recipe columns
        populate_unit_labels()
        
def update_ink_dropdown_menu():
    """Update the dropdown menu with new options according to the ink 
    recipe book selected."""
    global drop_inks, clicked_ink, ink_drop_options
    
    # Clear the current selection
    clicked_ink.set('')
    
    # Delete the current menu
    menu = drop_inks['menu']
    menu.delete(0, 'end')
    
    # Add new options to the menu
    for option in ink_drop_options:
        menu.add_command(label=option, command=tk._setit(clicked_ink, option))
    
    # Set the first option as default if available
    # if ink_drop_options:
        # clicked_ink.set(ink_drop_options[0])
        
        
def populate_unit_labels():
    """Populate and grid the component labels based on the recipe file columns.
    This function reads the column headers from the recipes dataframe and 
    updates the component labels accordingly."""
    global recipes, component_unit_lbls
    
    # Clear all existing component labels first
    for lbl in component_unit_lbls:
        lbl.configure(text='')
        lbl.grid_remove()  # Remove from grid but don't destroy
    
    if 'recipes' in globals() and recipes is not None:
        # Get all column headers except the first two (ink_id, conc.)
        component_columns = recipes.columns[2:].tolist()
        
        # Populate labels up to the available components or max 10 labels
        num_components = min(len(component_columns), len(component_unit_lbls))
        
        for i in range(num_components):
            # Update label text with component name
            component_unit_lbls[i].configure(text=component_columns[i],
                                             font='Helvetica 10 bold')
            
            # Grid the label in row 0, column starting from 2 (after catalyst columns)
            component_unit_lbls[i].grid(row=3, column=i+1, padx=5, pady=2, sticky='w')
       
        

            
            
def calculate_ink_components():
    """
    Calculate and display per-component amounts in the GUI based on the selected
    ink recipe and catalyst mass.

    Clears all component labels, then — if a recipe is loaded, an ink is selected,
    and a catalyst mass is entered — looks up the ink row in the global ``recipes``
    DataFrame and computes each component mass as ``catalyst_mass × ratio``.
    Updates ``str_ink_conc`` and ``lbl_recipe_conc`` with the ink's nominal
    concentration, and re-grids each component value label with the result
    rounded to 3 decimal places. Silently ignores invalid (non-numeric) mass input.

    Globals:
        recipes: DataFrame of ink recipes loaded from the recipe book.
        clicked_ink: Tkinter StringVar holding the selected ink name.
        str_ink_mass: Tkinter StringVar holding the catalyst mass in mg.
        str_ink_conc: Tkinter StringVar updated with the ink's nominal concentration.
        component_value_lbls: List of CTkLabel widgets for displaying component amounts.

    Returns:
        None
    """
    global recipes, clicked_ink, str_ink_mass, component_value_lbls, str_ink_conc
    
    # Clear all component value labels first
    for lbl in component_value_lbls:
        lbl.configure(text='')
        lbl.grid_remove()
    
    # Check if we have all necessary data
    if ('recipes' in globals() and recipes is not None and 
        clicked_ink.get() and str_ink_mass.get()):
        
        try:
            catalyst_mass = float(str_ink_mass.get())
            selected_ink = clicked_ink.get()
            
            # Find the row for the selected ink
            ink_row = recipes[recipes.iloc[:, 0] == selected_ink]
            
            # set concentration lablel 
            concentration = str(ink_row.iloc[0, 1])
            str_ink_conc.set(concentration)
            lbl_recipe_conc.configure(text=str_ink_conc.get())
            
            if not ink_row.empty:
                # Get component ratios (all columns except first)
                component_ratios = ink_row.iloc[0, 2:].values
                
                # Calculate component masses
                for i, ratio in enumerate(component_ratios):
                    if i < len(component_value_lbls) and pd.notna(ratio):
                        component_value = catalyst_mass * float(ratio)
                        
                        # Update value label
                        component_value_lbls[i].configure(text=f'{component_value:.3f}')
                        
                        # Grid the value label in row 1, same column as component label
                        component_value_lbls[i].grid(row=4, column=i+1, padx=5, pady=2, sticky='w')
                        
        except ValueError:
            # Handle invalid catalyst mass input
            pass
        
def calculate_with_validation():
    """Wrapper function that validates inputs before calculating components."""
    global recipes, clicked_ink, str_ink_mass
    
    # Check if recipe book is loaded
    if 'recipes' not in globals() or recipes is None:
        tk.messagebox.showerror("Error", "Please read a recipe book first!")
        return
    
    # Check if ink is selected
    if not clicked_ink.get() or clicked_ink.get() == '':
        tk.messagebox.showerror("Error", "Please select an ink recipe!")
        return
    
    # Check if catalyst mass is entered and valid
    try:
        catalyst_mass = float(str_ink_mass.get())
        if catalyst_mass <= 0:
            tk.messagebox.showerror("Error", "Catalyst mass must be a positive number!")
            return
    except ValueError:
        tk.messagebox.showerror("Error", "Please enter a valid catalyst mass!")
        return
    
    # If all validations pass, calculate components
    calculate_ink_components()
    
    
def toggle_exp_type_entry(selected_value=None):
    """Show/hide user input entry based on experiment type selection"""
    global ent_user_exp_type, drop_exp_type
    
    # Get the current selection (handle both direct calls and OptionMenu callbacks)
    current_selection = selected_value if selected_value else clicked_exp_type.get()
    
    if current_selection == 'user input':
        # Show the user input entry below the dropdown
        ent_user_exp_type.grid(row=3, column=3, padx=5, pady=(0, 5), sticky='ew')
        # Clear any existing text
        str_user_exp_type.set('')
        # Focus on the entry for immediate typing
        ent_user_exp_type.focus_set()
    else:
        # Hide the user input entry
        ent_user_exp_type.grid_remove()

def get_effective_exp_type():
    """Get the effective experiment type (either from dropdown or user input)"""
    if clicked_exp_type.get() == 'user input':
        return str_user_exp_type.get() or 'custom'  # Return user input or 'custom' if empty
    else:
        return clicked_exp_type.get()
    

def convert_to_rhe(string_ref_potential, low, high, step, results_frame):
    """
    Convert applied potentials to RHE scale and populate the results frame.
    
    The conversion formula is:
    E_RHE = E_applied + E_ref
    
    Rearranging to find required applied potential:
    E_applied = E_RHE - E_ref
    
    Args:
        str_ref_potential: StringVar containing the user input 
                            reference potential value in mv
                            
        results_frame: Frame widget to populate with results
    """
    try:
        low_flt = float(low.get())
        high_flt = float(high.get())
        step_flt = float(step.get())
    
    except ValueError:
        for widget in results_frame.winfo_children():
            widget.destroy()
        ttk.Label(results_frame, text="Error: Please enter a valid sweep range (low/high/step)",
                  foreground="red").grid(row=0, column=0, columnspan=2, padx=10, pady=20)
        return
    
    potentials_array = arange(start=low_flt, stop=high_flt, step=step_flt)
    
    
    try:
        # Get reference potential value
        ref_potential = float(str_ref_potential.get())
    except ValueError:
            # Clear results and show error
            for widget in results_frame.winfo_children():
                widget.destroy()
            error_label = ttk.Label(results_frame, text="Error: Please enter a valid ref. potential value", 
                                  foreground="red")
            error_label.grid(row=0, column=0, columnspan=2, padx=10, pady=20)
            return
        
    # Clear existing results
    for widget in results_frame.winfo_children():
            widget.destroy()
        
    # Create headers
    ttk.Label(results_frame, text="Erhe \n(V vs RHE)", font=('Helvetica', 10, 'bold')).grid(
        row=0, column=0, padx=7, pady=5, sticky=tk.W)
    ttk.Label(results_frame, text="Ewe\n(V vs Ref)", font=('Helvetica', 10, 'bold')).grid(
        row=0, column=1, padx=7, pady=5, sticky=tk.W)
    
    # Add separator
    ttk.Separator(results_frame, orient='horizontal').grid(
        row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
    # Calculate and display conversion table
    row = 2
        
    for i in range(len(potentials_array)):  
        e_rhe = potentials_array[i]
        # Calculate required applied potential: E_applied = E_RHE - E_ref
        e_applied = e_rhe - ref_potential/1000
        
        # Create labels for each row
        rhe_label = ttk.Label(results_frame, text=f"{e_rhe:.3f}", 
                                  font='Helvetica 10')
        rhe_label.grid(row=row, column=0, padx=10, pady=2, sticky=tk.W)
            
        applied_label = ttk.Label(results_frame, text=f"{e_applied:.3f}",
                                      font='Helvetica 10')
        applied_label.grid(row=row, column=1, padx=10, pady=2, sticky=tk.W)
            
        row += 1
        
    # Add reference information
    info_text = "Ewe = Erhe - Eref"
    ttk.Label(results_frame, text=info_text, font=('Helvetica', 10)).grid(
        row=row, column=0, columnspan=2, pady=(10, 0), sticky=tk.W)
        
    

    
#%% 2.1: dynamic filename functions

def toggle_filename_mode():
    """Toggle between standardized and user input filename modes"""
    global filename_mode, ent_user_filename, lbl_generated_filename, btn_update_filename
    
    if filename_mode.get() == 'user_input':
        """Generated filename: |e: displayed, but clear box."""
        # Hide generated filename label and update button
        lbl_generated_filename.grid_remove()
        btn_update_filename.grid_remove()
        
        # Show user input entry
        ent_user_filename.grid(row=3, column=0, columnspan=4, padx=10, pady=2, sticky='ew')
        
        # Update display label
        # lbl_filename_display.configure(text='Enter Custom Filename:')
        
    else:  # standardized mode
        # Hide user input entry
        ent_user_filename.grid_remove()
        
        # Show generated filename label and update button
        lbl_generated_filename.grid(row=3, column=0, columnspan=4, padx=10, pady=2, sticky='ew')
        btn_update_filename.grid(row=4, column=0, columnspan=2, pady=5, padx=10, sticky='ew')
        
        # Update display label
        # lbl_filename_display.configure(text='Generated Filename')
        
        # Generate filename if parameters are available
        generate_standardized_filename()
        
def decimal_replace(input_string, replacement='p'):
    """
    convert various input types to filename-safe string with replacement 
    character (default 'p') instead of decimal with validation.
    
    Args:
        input_string (str): String containing decimal number(s)
        replacement (str): Character to replace decimal point (default: 'p')
        
    Returns:
        str: String with decimal points replaced
        
    Examples:
        decimal_replace("0.85", 'p') -> "0p85"
        ("1.2.3", 'dot') -> "1dot2dot3"
    """
    if not isinstance(input_string, str):
        input_string = str(input_string)
    
    return input_string.replace('.', replacement)

def generate_standardized_filename():
    """
    Build a standardized experiment filename from current GUI field values and
    write it to ``str_generated_filename``.

    Assembles fields in the format::

        YYYYMMDD_{MaterialID}_{conc}M{electrolyte}_{mV}mVrhe{ref}_{exp_type}[_{ink_id}][_{trial_id}]

    ``ink_id`` and ``trial_id`` are appended only when non-empty. Decimal points
    in any component are replaced with ``'p'`` for filesystem safety via
    ``decimal_replace()``. If ``exp_type`` is ``'user input'``, the custom type
    field is substituted instead.

    Returns:
        None: Updates ``str_generated_filename`` in place. On failure, sets it
        to an error message string rather than raising.

    Example output:
        ``20250510_PtC_0p1MHClO4_200mVrheRHE_CV_ink3_t2``
    """
    try:
        # Get current date in YYYYMMDD format
        current_date = datetime.now().strftime('%Y%m%d')
        
        # Get values from form fields
        material_id = str_material_id.get() or 'MaterialID'
        electrolyte_conc = str_electrolyte_conc.get() 
        electrolyte_chem = str_electrolyte_chem.get() 
        ref_potential = str_ref_potential.get()
        experiment_type = clicked_exp_type.get() or 'test'
        ink_id = str_ink_id.get()
        trial_id = str_trial_id.get()
        
        # varlist = [material_id, electrolyte_conc, electrolyte_chem, 
        #            ref_potential, experiment_type, ink_id, trial_id]
        
        # for var in varlist:
        #     var = decimal_replace(var)
            
        # Match reference type to simple string
        ref_type = clicked_ref_type.get()
        ref_code = get_ref_code_from_type(ref_type)
        
        # Handle user input experiment type
        if experiment_type == 'user input':
            experiment_type = decimal_replace(str_user_exp_type.get())
        
        # Create electrolyte and reference strings 
        electrolyte_string = f"{electrolyte_conc}M{electrolyte_chem}"
        ref_string = f"{ref_potential}mVrhe{ref_code}"
        
        # Generate standardized filename
        # Format: YYYYMMDD_{MaterialID}_{Electrolyte}-{Ref. pot}_{experiment_type}_{inkID}_{trialID}
        standardized_filename = ''
        base_filename = f"{current_date}_RDE_{material_id}_{electrolyte_string}_{ref_string}_{experiment_type}"
        
        # Avoids adding useless info if user has a different notation system
        if (ink_id != '') & (trial_id == ''):
            standardized_filename = f'{base_filename}_{ink_id}'
        elif (ink_id == '') & (trial_id != ''):
            standardized_filename = f'{base_filename}_{trial_id}'
        elif (ink_id != '') & (trial_id != ''):
            standardized_filename = f'{base_filename}_{ink_id}_{trial_id}'
        else:
            standardized_filename = base_filename
        
        ## replace decimals with p for filename safety
        standardized_filename = decimal_replace(standardized_filename)
        
        # Update the display
        str_generated_filename.set(standardized_filename)
        
    except Exception as e:
        str_generated_filename.set(f"Error generating filename: {str(e)}")

def get_current_filename():
    """Get the current filename based on the selected mode"""
    if filename_mode.get() == 'user_input':
        return str_user_filename.get()
    else:
        return str_generated_filename.get()
    
def copy_filename_to_clipboard_silent():
    """Copy filename to clipboard without showing popup messages"""
    try:
        current_filename = get_current_filename()
        
        if current_filename and not current_filename.startswith("Please fill") and not current_filename.startswith("Error"):
            window.clipboard_clear()
            window.clipboard_append(current_filename)
            window.update()
            
            # Optional: Change button color briefly to indicate success
            btn_copy.configure(bg='lightgreen')
            window.after(500, lambda: btn_copy.configure(bg='lightblue'))  # Reset color after 500ms
            
    except Exception as e:
        print(f"Failed to copy filename: {str(e)}")  # Silent error handling

#%% 2.2: .yaml metadata file creation and saving functions

def safe_float(widget_var):
    "deals with empty variable float ValueErrors"
    val = widget_var.get()
    return float(val) if val != '' else None

def collect_all_data():
    """
    Collect all GUI input variables into a structured dictionary for experiment logging.

    Reads current values from all Tkinter widget variables (entries, dropdowns, labels)
    and organizes them into a nested dictionary covering four domains: file metadata,
    ink recipe, calculated ink components, and experiment parameters.

    Returns
    -------
    dict
        A nested dictionary with the following top-level keys:

        - **file_metadata** *(dict)*: File authorship and naming information.
            - `creator` *(str)*: Author name from input field.
            - `created_date` *(str)*: Auto-generated timestamp (``'YYYY-MM-DD HH:MM:SS'``).
            - `filename_mode` *(str)*: Selected filename generation mode.
            - `generated_filename` *(str)*: Current filename as produced by ``get_current_filename()``.
            - `linked_files` *(str)*: Paths to any associated files.

        - **ink_recipe** *(dict)*: Ink preparation and identification details.
            - `recipe_book_path` *(str)*: Filesystem path to the recipe book, parsed from label text.
            - `selected_ink_recipe` *(str)*: Name of the chosen ink recipe.
            - `material_id` *(str)*: Catalyst material identifier.
            - `catalyst_mass_mg` *(float)*: Catalyst mass in milligrams.
            - `ink_id` *(str)*: Unique ink batch identifier.

        - **calculated_ink_components** *(dict | None)*: Per-component mass/volume
          breakdown returned by ``get_component_calculations()``. May be ``None``
          or empty if no recipe is loaded.

        - **experiment_parameters** *(dict)*: Full experimental configuration.
            - `reaction` *(str)*: Target electrochemical reaction.
            - `exp_purpose` *(str)*: Stated purpose of the experiment.
            - `trial_id` *(str)*: Trial identifier string.
            - `catalyst_loading` *(dict)*:
                - `ink_vol_uL` *(float)*: Ink volume in microlitres.
                - `mass_loading_ug` *(float)*: Catalyst mass loading in micrograms
                  (computed as concentration × volume).
            - `electrolyte` *(dict)*:
                - `concentration_M` *(float)*: Electrolyte molar concentration.
                - `composition` *(str)*: Chemical composition string.
                - `known_impurities_ppm` *(float)*: Impurity level in parts per million.
                - `gas_flowed_mLpermin` *(str)*: Purge/flow gas and flow rate.
            - `reference_electrode` *(dict)*:
                - `ref_type` *(str)*: Reference electrode type.
                - `mV_vs_rhe` *(float)*: Electrode potential in mV vs. RHE.
            - `experiment_info` *(dict)*:
                - `exp_type` *(str)*: Experiment type selected from dropdown.
                - `custom_type` *(str | None)*: User-defined type if ``exp_type`` is
                  ``'user input'``, otherwise ``None``.
                - `rotation_rpm` *(float)*: Electrode rotation speed in RPM.
                - `counter_elect` *(str)*: Counter electrode type.
                - `electrode_tip_config` *(str)*: Working electrode tip configuration.
                - `cell_config` *(str)*: Combined cell type and material (``'<type>_<material>'``).

        - **notes** *(str)*: Free-text notes retrieved from the notes text widget.

    Notes
    -----
    - All numeric fields are cast to ``float`` at collection time; invalid or empty
      widget values will raise a ``ValueError``.
    - The timestamp is generated at call time, so it reflects when data collection
      occurred, not when the GUI session started.
    - This function has side effects: it reads directly from module-level Tkinter
      widget variables and calls ``get_component_calculations()`` and
      ``get_current_filename()``.
    """
    # Get current timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    data = {
        # Metadata
        'file_metadata': {
            'creator': str_author.get(),
            'created_date': timestamp,
            'filename_mode': filename_mode.get(),
            'generated_filename': get_current_filename(),
            'linked_files': str_Links.get()
        },
        
        # Ink Recipe Information
        'ink_recipe': {
            'recipe_book_path': lbl_browser_files_to_open.cget('text').replace('Recipe Book: ', '') if 'Recipe Book:' in lbl_browser_files_to_open.cget('text') else '',
            'selected_ink_recipe': clicked_ink.get(),
            'material_id': str_material_id.get(),
            'catalyst_mass_mg': safe_float(str_ink_mass),
            'ink_id': str_ink_id.get()
        },
        
        # Component Calculations (if available)
        'calculated_ink_components': get_component_calculations(),
        
        # Experiment Parameters
        'experiment_parameters': {
            'exp_purpose': str_purpose.get(),
            'reaction': str_reaction.get(),
            'trial_id': str_trial_id.get(),
            'catalyst_loading': {
                'ink_vol_uL': safe_float(str_ink_vol) ,
                'mass_loading_ug': safe_float(str_ink_conc)*safe_float(str_ink_vol) #ug/uL * uL
            },
            'electrolyte': {
                'concentration_M': str_electrolyte_conc.get() ,
                'composition': str_electrolyte_chem.get(),
                'known_impurities_ppm': str_impurity.get(),
                'gas_bubbled_mLpermin': str_gas.get()
                
            },
            'reference_electrode': {
                'ref_type': clicked_ref_type.get(),
                'mV_vs_rhe': safe_float(str_ref_potential) 
            },
            'experiment_info': {
                'exp_type': clicked_exp_type.get(),
                'custom_type': str_user_exp_type.get() if clicked_exp_type.get() == 'user input' else None,
                'rotation_rpm': safe_float(str_rotation) ,
                'counter_elect': clicked_counter_elctrd_type.get(),
                'electrode_tip_config': clicked_elctrd_type.get(),
                'working_area_geo_cm2': safe_float(str_area),
                'cell_config': f"{clicked_cell_type.get()}_{clicked_cell_mat_type.get()}"
            },
            
        },
        
        # Notes
        'notes': ent_notes.get(1.0, 'end')
    }
    
    return data

def get_ref_code_from_type(ref_type):
    """Extract reference code from reference type (same as in filename generation)"""
    
    ['Hg|HgO', 'Ag|AgCl', 'Hg|Hg2Cl2', 'Hg|HgSO4', 'Pt|H2', 'PdHx']
    match ref_type:
        case 'Hg|HgO':
            return 'HgO'
        case 'Ag|AgCl':
            return 'AgCl'
        case 'Hg|Hg2Cl2':
            return 'Hg2Cl2'
        case 'Hg|HgSO4':
            return 'HgSO4'
        case 'Pt|H2':
            return 'RHE'
        case 'PdHx':
            return 'PdHx'
        case _:
            return 'REF'
        

def get_component_calculations():
    """
    Calculate ink component amounts from the selected recipe and catalyst mass.

    Looks up the selected ink in the global ``recipes`` DataFrame and multiplies
    each component's per-mg ratio by the current catalyst mass. The first column
    is treated as a nominal concentration rather than a ratio.

    Returns
    -------
    dict
        Keyed by component name. Each value is a dict containing:

        - **First component**: ``{'nominal_conc_mg/mL': float}``
        - **All other components**: ``{'per_mg_catalyst_ratio': float, 'calculated_amount': float}``

        Returns an empty dict if no recipe/ink is selected or catalyst mass is blank.
        Returns ``{'error': str}`` if an exception occurs during calculation.
    """
    components = {}
    
    try:
        if 'recipes' in globals() and recipes is not None and clicked_ink.get():
            # Get component names from recipe headers
            component_names = recipes.columns[1:].tolist()
            
            # Get catalyst mass
            if str_ink_mass.get():
                catalyst_mass = float(str_ink_mass.get())
                
                # Find the selected ink row
                ink_row = recipes[recipes.iloc[:, 0] == clicked_ink.get()]
                
                if not ink_row.empty:
                    component_ratios = ink_row.iloc[0, 1:].values
                    
                    for i, (name, ratio) in enumerate(zip(component_names, component_ratios)):
                        if pd.notna(ratio):
                            # making sensical input for 1st column concentration
                            if i==0:
                                components[name] = {
                                    'nominal_conc_mg/mL': float(ratio),
                                    }
                            else:
                                component_ammount = catalyst_mass * float(ratio)
                                components[name] = {
                                    'per_mg_catlyst_ratio': float(ratio),
                                    'calculated_ammount': round(component_ammount, 3)
                            }
    except Exception as e:
        components['error'] = f"Could not calculate components: {str(e)}"
    
    return components

# Original save functions retained in case of future failue of complex one

# def save_yaml_file():
#     """Save all data to a YAML file with save dialog"""
#     try:
#         # Collect all data
#         data = collect_all_data()
        
#         # Get the current filename (without extension)
#         base_filename = get_current_filename()
        
#         # Validate filename
#         if not base_filename or base_filename.startswith("Please fill") or base_filename.startswith("Error"):
#             messagebox.showerror("Error", "Please generate a valid filename before saving!")
#             return
        
#         # Prepare default filename with .yaml extension
#         default_filename = f"{base_filename}.yaml"
        
#         # Open save dialog
#         file_path = fd.asksaveasfilename(
#             title="Save Meta Data",
#             defaultextension=".yaml",
#             filetypes=[
#                 ("YAML files", "*.yaml"),
#                 ("YAML files", "*.yml"),
#                 ("All files", "*.*")
#             ],
#             initialfile=default_filename
#         )
        
#         # Check if user cancelled the save dialog
#         if not file_path:
#             return
        
#         # Ensure the file has a .yaml extension
#         if not file_path.lower().endswith(('.yaml', '.yml')):
#             file_path += '.yaml'
        
#         # Save the YAML file
#         with open(file_path, 'w', encoding='utf-8') as yaml_file:
#             yaml.dump(data, yaml_file, default_flow_style=False, indent=2, sort_keys=False)
        
#         # Show success message
#         messagebox.showinfo("Success", f"Experiment metadata saved successfully!\n\nFile: {os.path.basename(file_path)}\nLocation: {os.path.dirname(file_path)}")
        
#     except Exception as e:
#         messagebox.showerror("Error", f"Failed to save YAML file:\n{str(e)}")

# def save_yaml_with_validation():
#     """Save YAML file with data validation"""
#     # Validate data first
#     errors = validate_data_before_save()
    
#     if errors:
#         error_message = "Please fix the following issues before saving:\n\n" + "\n".join(f"• {error}" for error in errors)
#         messagebox.showerror("Validation Error", error_message)
#         return
    
#     # If validation passes, proceed with save
#     save_yaml_file()
        

def save_metadata_file(save_type="yaml"):
    """
    Serialize all experiment metadata to a file via a save dialog.

    Collects current GUI data with ``collect_all_data()``, prompts the user
    for a save path, and writes the output in the specified format. A valid
    generated filename must exist before saving. Shows a success or error
    messagebox on completion.

    Args:
        save_type (str): Output format — ``'yaml'`` or ``'json'``. Defaults to ``'yaml'``.
        save_type should be passed from clicked_filetype.get().

    Returns:
        None: Returns early without saving if the format is unsupported,
        the filename is invalid, or the user cancels the dialog.
    """

    # --- Format configuration ---
    FORMAT_CONFIG = {
        "yaml": {
            "extensions": (".yaml", ".yml"),
            "default_ext": ".yaml",
            "filetypes": [("YAML files", "*.yaml"), ("YAML files", "*.yml"), ("All files", "*.*")],
        },
        "json": {
            "extensions": (".json",),
            "default_ext": ".json",
            "filetypes": [("JSON files", "*.json"), ("All files", "*.*")],
        },
    }
    
    if save_type not in FORMAT_CONFIG:
        messagebox.showerror("Error", f"Unsupported save type '{save_type}'. Choose 'yaml', 'json'.")
        return
    
    config = FORMAT_CONFIG[save_type]
    
    try:
        data = collect_all_data()
        base_filename = get_current_filename()
        
        if not base_filename or base_filename.startswith("Please fill") or base_filename.startswith("Error"):
            messagebox.showerror("Error", "Please generate a valid filename before saving!")
            return
        
        default_filename = f"{base_filename}{config['default_ext']}"
        
        file_path = fd.asksaveasfilename(
            title="Save Meta Data",
            defaultextension=config["default_ext"],
            filetypes=config["filetypes"],
            initialfile=default_filename,
        )
        
        if not file_path:
            return  # User cancelled
        
        # Ensure correct extension
        if not file_path.lower().endswith(config["extensions"]):
            file_path += config["default_ext"]
        
        # --- Write file ---
        if save_type == "yaml":
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, indent=2, sort_keys=False)
        
        elif save_type == "json":
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        
        messagebox.showinfo(
            "Success",
            f"Experiment metadata saved successfully!\n\n"
            f"File: {os.path.basename(file_path)}\n"
            f"Location: {os.path.dirname(file_path)}"
        )
    
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save {save_type.upper()} file:\n{str(e)}")


def validate_data_before_save():
    """Validate that essential data is present before saving"""
    errors = []
    
    # Check essential fields
    if not str_author.get():
        errors.append('Scientist name is required')
        
    if not str_material_id.get():
        errors.append("Material ID is required")
    
    if not clicked_ink.get() or clicked_ink.get() == 'load recipie book first':
        errors.append("Please select an ink recipe")
    
    if not str_ink_mass.get():
        errors.append("Catalyst mass is required")
        
    if not str_ink_vol.get():
        errors.append("Ink volume is required")
        
    if not str_purpose.get():
        errors.append('Experiment purpose is required')
    
    if clicked_exp_type.get() == 'user input' and not str_user_exp_type.get():
        errors.append("Please enter a custom experiment type")
    
    return errors


def save_metadata_with_validation(save_type):
    """Save metadata file with data validation. 
    save_type should be passed from clicked_filetype.get()."""
    # Validate data first
    errors = validate_data_before_save()
    
    if errors:
        error_message = "Please fix the following issues before saving:\n\n" + "\n".join(f"• {error}" for error in errors)
        messagebox.showerror("Validation Error", error_message)
        return
    
    # If validation passes, proceed with save
    save_metadata_file(save_type)
    
#%% 2.3: Flow cell functions

def browseInks_flow():
    """selects the .csv recipe book file from which the ink recipe will be 
    selected. The selected ink ratios will be extracted by later functions."""
    global clicked, recipes_fc, ink_drop_options_fc, drop_inks_fc, clicked_ink_fc
    clicked = True
    filename = fd.askopenfilename(
        title='Select an Ink Recipe File',
        filetypes=[('ink recipe files', '*.csv'), ('All files', '*.*')]
    )

    # Only proceed if a file was selected
    if filename:
        # Change opened files label contents
        stem = Path(filename).stem
        lbl_browser_files_to_open_fc.configure(text='Recipe Book: ' + stem )
        
        ## Dataframe loading
        recipes = pd.read_csv(filename)
        
        ## Update ink dropdown menu options 
        ink_drop_options_fc = recipes[recipes.columns[0]].values.tolist()
        
        ## Update the existing OptionMenu with new options
        update_fc_ink_dropdown_menu()
        
        
def update_fc_ink_dropdown_menu():
    """Update the dropdown menu with new options according to the ink 
    recipe book selected."""
    global drop_inks_fc, clicked_ink_fc, ink_drop_options_fc
    
    # Clear the current selection
    clicked_ink_fc.set('')
    
    # Delete the current menu
    menu = drop_inks_fc['menu']
    menu.delete(0, 'end')
    
    # Add new options to the menu
    for option in ink_drop_options_fc:
        menu.add_command(label=option, command=tk._setit(clicked_ink_fc, option))

        
def fc_toggle_filename_mode():
    """Toggle between standardized and user-input filename modes for the FC tab."""
    if filename_fc_mode.get() == 'user_input': 
        # Hide generated filename label and update button
        lbl_fc_generated_filename.grid_remove()
        btn_fc_update_filename.grid_remove()

        # Show user input entry
        ent_fc_user_filename.grid(
            row=3, column=0, columnspan=4, padx=10, pady=2, sticky='ew'
        )

    else:  # standardized mode
        # Hide user input entry
        ent_fc_user_filename.grid_remove()

        # Show generated filename label and update button
        lbl_fc_generated_filename.grid(
            row=3, column=0, columnspan=4, padx=10, pady=2, sticky='ew'
        )
        btn_fc_update_filename.grid(
            row=4, column=0, columnspan=2, pady=5, padx=10, sticky='ew'
        )

        # Generate filename now that parameters may be available
        fc_generate_standardized_filename()

def fc_toggle_exp_type_entry(selected_value=None):
    """Show/hide user input entry based on experiment type selection"""
    global ent_user_exp_type, drop_exp_type
    
    # Get the current selection (handle both direct calls and OptionMenu callbacks)
    current_selection = selected_value if selected_value else fc_clicked_exp_type.get()
    
    if current_selection == 'user input':
        # Show the user input entry below the dropdown
        ent_fc_user_exp_type.grid(row=5, column=1, padx=5, pady=(0, 5), sticky='ew')
        # Clear any existing text
        str_fc_user_exp_type.set('')
        # Focus on the entry for immediate typing
        ent_fc_user_exp_type.focus_set()
    else:
        # Hide the user input entry
        ent_fc_user_exp_type.grid_remove()

        
def fc_generate_standardized_filename():
    """
    Build a standardized experiment filename from current FC GUI field values
    and write it to ``str_fc_generated_filename``.

    Assembles fields in the format::

        YYYYMMDD_FC_{MaterialID}_{conc}M{electrolyte}_{mV}mVrhe{ref}_{purpose}
        [_{ink}][_{trial_id}][_beamtime_{modality}_{beamline}]

    The beamtime suffix (modality + beamline) is appended only when the
    experiment mode radio button is set to ``'beamtime'``.  ``clicked_ink_fc``
    and ``str_fc_trial_id`` are appended only when non-empty.  Decimal points
    are replaced with ``'p'`` for filesystem safety via ``decimal_replace()``.

    Returns:
        None: Updates ``str_fc_generated_filename`` in place; on failure writes
        an error string rather than raising.

    Example output:
        ``20250510_FC_NiFe_0p1MKOH_200mVrheHgO_OER_ink3_t2``
    """
    try:
        current_date = datetime.now().strftime('%Y%m%d')

        # ── Core experiment fields ────────────────────────────────────────────
        material_id       = str_fc_material_id.get()
        WE_id             = str_fc_electrode_id.get()
        electrolyte_conc  = str_fc_electrolyte_conc.get()
        electrolyte_chem  = str_fc_electrolyte_chem.get()
        #Empty ref field gives NoneType error here
        ref_potential     = (safe_float(str_fc_ref_potential1) or 0)+ (safe_float(str_fc_ref_potential2) or 0)
        # ref_potential     = safe_float(str_fc_ref_potential1) + safe_float(str_fc_ref_potential2)
        trial_id          = str_fc_trial_id.get()

        # ── Assemble electrolyte / reference substrings ───────────────────────
        electrolyte_string = f"{electrolyte_conc}M{electrolyte_chem}"
        ref_string         = f"{ref_potential}mVrhe"

        # ── Base filename ─────────────────────────────────────────────────────
        if fc_mode.get() == 'beamtime':
            base_filename = (
                f"{current_date}_FC-beamtime_{material_id}_{WE_id}_"
                f"{electrolyte_string}_{ref_string}"
                )

        else:
            base_filename = (
            f"{current_date}_FC_{material_id}_{WE_id}_"
            f"{electrolyte_string}_{ref_string}"
            )

        # ── Optional ink / trial suffixes ─────────────────────────────────────
        if trial_id:
            standardized_filename = f"{base_filename}_{trial_id}"
        else:
            standardized_filename = base_filename

        # ── Replace decimal points for filesystem safety ──────────────────────
        standardized_filename = decimal_replace(standardized_filename)

        str_fc_generated_filename.set(standardized_filename)

    except Exception as e:
        str_fc_generated_filename.set(f"Error generating filename: {str(e)}")


    
def fc_get_current_filename():
    """Return the active filename for the FC tab based on the selected mode.

    Returns:
        str: Contents of ``str_fc_user_filename`` when mode is ``'user_input'``,
        otherwise contents of ``str_fc_generated_filename``.
    """
    if filename_fc_mode.get() == 'user_input':
        return str_fc_user_filename.get()
    return str_fc_generated_filename.get()
    
def fc_copy_filename_to_clipboard_silent():
    """Copy the current FC filename to the clipboard without showing a popup.

    Briefly turns ``btn_fc_copy`` green to confirm success.  Errors are printed
    to stdout rather than raised.
    """
    try:
        current_filename = fc_get_current_filename()

        if (
            current_filename
            and not current_filename.startswith("Please fill")
            and not current_filename.startswith("Error")
        ):
            window.clipboard_clear()
            window.clipboard_append(current_filename)
            window.update()

            # Brief colour flash to signal success
            btn_fc_copy.configure(bg='lightgreen')
            window.after(500, lambda: btn_fc_copy.configure(bg='lightblue'))

    except Exception as e:
        print(f"Failed to copy FC filename: {str(e)}")



def fc_collect_all_data(): 
    """Collect all FC tab input variables into a structured dictionary.

    Reads current values from all FC Tkinter widget variables and organises
    them into a nested dictionary.  When the experiment mode is ``'beamtime'``,
    a ``beamtime_parameters`` block is added whose sub-keys depend on the
    modality selected via ``beamtime_selection`` (``'XAS'``, ``'XRD'``, or
    ``'XAS + XRD'``).

    Returns:
        dict: Nested dictionary with the following top-level keys:

        - **file_metadata** *(dict)*: Authorship and naming details.
        - **ink_recipe** *(dict)*: Ink selection and material ID.
        - **calculated_ink_components** *(dict | None)*: From
          ``get_component_calculations()``; may be ``None``.
        - **experiment_parameters** *(dict)*: Full FC experimental
          configuration including working electrode, counter electrode,
          two reference electrodes, electrolyte, and flowcell assembly.
        - **beamtime_parameters** *(dict, conditional)*: Present only when
          ``fc_mode == 'beamtime'``; contains common beamline fields plus
          XAS and/or XRD sub-dicts as appropriate.
        - **notes** *(str)*: Free-text notes.

    Notes:
        Numeric fields are cast with ``safe_float()``; invalid/empty widget
        values will propagate a ``ValueError`` from that helper.
        Several XAS/XRD StringVars (e.g. ``str_fc_enrgymin``) are initialised
        with ``tk.StringVar().set('')``, which returns ``None`` — accessing
        ``.get()`` on those will raise at runtime until the vars section is
        corrected.
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    data = {
        # ── File metadata ─────────────────────────────────────────────────────
        'file_metadata': {
            'creator':            str_fc_author.get(),
            'created_date':       timestamp,
            'filename_mode':      filename_fc_mode.get(),
            'generated_filename': fc_get_current_filename(),
            'linked_files':       str_fc_Links.get(),
        },

        # ── Ink recipe ────────────────────────────────────────────────────────
        'ink_recipe': {
            'recipe_book': lbl_browser_files_to_open_fc.cget('text').replace('Recipe Book: ', '') if 'Recipe Book:' in lbl_browser_files_to_open_fc.cget('text') else '',
            'selected_ink_recipe': clicked_ink_fc.get(),
            'material_id':         str_fc_material_id.get(),
        },

        # ── Experiment parameters ─────────────────────────────────────────────
        'experiment_parameters': {
            'exp_purpose': str_fc_purpose.get(),
            'reaction':    str_fc_reaction.get(),
            'trial_id':    str_fc_trial_id.get(),
            'exp_type':    fc_clicked_exp_type.get(),

            'working_electrode': {
                'material_id':        str_fc_material_id.get(),
                'electrode_id':       str_fc_electrode_id.get(),
                'electrode_mass_mg':  safe_float(str_fc_electrode_mass),
                'electrode_area_cm2': safe_float(str_fc_electrode_area),
            },

            'counter_electrode': {
                'CE_id':     str_fc_CE_id.get(),
                'CE_mass_mg': safe_float(str_fc_CE_mass),
                'CE_type':   clicked_fc_counter_elctrd_type.get(),
            },

            'electrolyte': {
                'concentration_M':       str_fc_electrolyte_conc.get(),
                'composition':           str_fc_electrolyte_chem.get(),
                'known_impurities_ppm':  str_fc_impurity.get(),
                'liquid_flowrate_mLpermin': str_fc_flowrate.get(),
                'gas_flowrate_mLpermin':    str_fc_gasflowrate.get(),
            },

            'reference_electrode_1': {
                'ref_type':  clicked_fc_ref_type1.get(),
                'mV_vs_rhe': safe_float(str_fc_ref_potential1),
            },

            'reference_electrode_2': {
                'ref_type':  clicked_fc_ref_type2.get(),
                'mV_vs_rhe': safe_float(str_fc_ref_potential2),
            },

            'flowcell_details': {
                'gasket_membrane':          str_fc_gasketmembrane.get(),
                'torque_Nm':                safe_float(str_fc_torque),
                'electrolyte_thickness_mm': safe_float(str_fc_electThick),
                'cell_id':                  str_fc_cell_id.get(),
                'cell_material':            fc_clicked_cell_mat_type.get()
            },
        },

        # ── Notes ─────────────────────────────────────────────────────────────
        'notes': ent_fc_notes.get(1.0, 'end')
    }

    # ── Beamtime parameters (only when beamtime mode is active) ───────────────
    if fc_mode.get() == 'beamtime': 
        modality = beamtime_selection.get()

        beamtime_data = {
            'beamtime_exp_id':     str_fc_beamline_expid.get(),
            'tecnique':   modality,
            'beamline':   str_fc_beamline.get(),
            'optics':     str_fc_optics.get(),
            'monochromator': str_fc_mono.get(),
            'filter':     str_fc_filter.get(),
            'I0':         str_fc_I0.get(),
            'beamspot':   str_fc_beamspot.get(),
            'beamtime_notes': beamline_notes.get(1.0, 'end')
        }
        
            

        # XAS sub-block 
        if modality in ('XAS', 'XAS + XRD'):
            beamtime_data['xas_parameters'] = {
                'energy_min_eV':    safe_float(str_fc_enrgymin),
                'energy_max_eV':    safe_float(str_fc_enrgymax),
                'steps':            safe_float(str_fc_steps),
                'frequency':        safe_float(str_fc_freq),
                'detector':         str_fc_detector1.get(),
                'detection_mode':   str_fc_detectmode.get(),
            }

        # XRD sub-block 
        if modality in ('XRD', 'XAS + XRD'):
            photonunit =''
            if fc_clicked_photon.get()=='Wavelength (ang)':
                photonunit = 'Angstrom'
            else:
                photonunit = 'eV'
                
            beamtime_data['xrd_parameters'] = {
                'photon_value':         safe_float(int_fc_photoninput),
                'photon_units':         photonunit,
                '2theta_min_deg':       safe_float(str_fc_2thetamin),
                '2theta_max_deg':       safe_float(str_fc_2thetamax),
                'detector':             str_fc_detector2.get(),
                'detector_distance_mm': safe_float(str_fc_detector2dist),
                'detection_mode':       str_fc_xrddetectmode.get(),
            }

        data['beamtime_parameters'] = beamtime_data
        
        
    return data
        

def fc_save_metadata_file(save_type="yaml"):
    """Serialize all FC experiment metadata to a file via a save dialog.

    Mirrors ``save_metadata_file()`` from the RDE tab.  Collects data with
    ``fc_collect_all_data()``, prompts the user for a save path, and writes
    the output in the requested format.  A valid generated filename must exist
    before saving.  Displays a success or error messagebox on completion.

    Args:
        save_type (str): Output format — ``'yaml'`` or ``'json'``.
            Should be passed as ``clicked_fc_filetype.get()``.

    Returns:
        None: Returns early without saving if the format is unsupported,
        the filename is invalid, or the user cancels the dialog.
    """
    # ── Format configuration (mirrors reference save_metadata_file) ───────────
    FORMAT_CONFIG = {
        "yaml": {
            "extensions":   (".yaml", ".yml"),
            "default_ext":  ".yaml",
            "filetypes":    [
                ("YAML files", "*.yaml"),
                ("YAML files", "*.yml"),
                ("All files",  "*.*"),
            ],
        },
        "json": {
            "extensions":  (".json",),
            "default_ext": ".json",
            "filetypes":   [
                ("JSON files", "*.json"),
                ("All files",  "*.*"),
            ],
        },
    }

    if save_type not in FORMAT_CONFIG:
        messagebox.showerror(
            "Error",
            f"Unsupported save type '{save_type}'. Choose 'yaml' or 'json'."
        )
        return

    config = FORMAT_CONFIG[save_type]

    try:
        data          = fc_collect_all_data()
        base_filename = fc_get_current_filename()

        if (
            not base_filename
            or base_filename.startswith("Please fill")
            or base_filename.startswith("Error")
        ):
            messagebox.showerror(
                "Error",
                "Please generate a valid filename before saving!"
            )
            return

        default_filename = f"{base_filename}{config['default_ext']}"

        file_path = fd.asksaveasfilename(
            title="Save Flowcell Metadata",
            defaultextension=config["default_ext"],
            filetypes=config["filetypes"],
            initialfile=default_filename,
        )

        if not file_path:
            return  # User cancelled

        # Ensure the path carries the correct extension
        if not file_path.lower().endswith(config["extensions"]):
            file_path += config["default_ext"]

        # ── Write file ────────────────────────────────────────────────────────
        if save_type == "yaml":
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, indent=2,
                          sort_keys=False)

        elif save_type == "json":
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        messagebox.showinfo(
            "Success",
            f"FC experiment metadata saved successfully!\n\n"
            f"File: {os.path.basename(file_path)}\n"
            f"Location: {os.path.dirname(file_path)}"
        )

    except Exception as e:
        messagebox.showerror(
            "Error",
            f"Failed to save {save_type.upper()} file:\n{str(e)}"
        )




def fc_validate_data_before_save():
    """Return a list of validation error strings for the FC tab.

    Checks that all essential fields carry non-empty values before a save
    is attempted.

    Returns:
        list[str]: Empty if validation passes; otherwise one message per
        missing or invalid field.
    """
    errors = []

    if not str_fc_author.get():
        errors.append("Scientist name is required")

    if not str_fc_material_id.get():
        errors.append("Material ID is required")

    if not clicked_ink_fc.get():
        errors.append("Please select an ink recipe")

    if not str_fc_purpose.get():
        errors.append("Experiment purpose is required")
    
    if not str_fc_reaction.get():
        errors.append("Reaction is required")

    if not str_fc_electrolyte_conc.get():
        errors.append("Electrolyte concentration is required")
        
    if not str_fc_electrolyte_chem.get():
        errors.append("Electrolyte composition is required")

    if not str_fc_ref_potential1.get():
        errors.append("Reference electrode potential is required")
        
    if not str_fc_electThick.get():
        errors.append("Electrolyte thickness is required")
    
    if not str_fc_flowrate.get():
        errors.append("Electrolyte flowrate is required")

    return errors

def fc_save_metadata_with_validation(save_type):
    """Validate FC inputs then save metadata; mirrors ``save_metadata_with_validation``.

    Args:
        save_type (str): Output format (``'yaml'`` or ``'json'``).
            Should be passed as ``clicked_fc_filetype.get()``.

    Returns:
        None: Shows a validation-error dialog and returns early if any
        required fields are missing; otherwise delegates to
        ``fc_save_metadata_file()``.
    """
    errors = fc_validate_data_before_save()

    if errors:
        error_message = (
            "Please fix the following issues before saving:\n\n"
            + "\n".join(f"• {e}" for e in errors)
        )
        messagebox.showerror("Validation Error", error_message)
        return

    fc_save_metadata_file(save_type)

#%% 2.4 : Flowcell/Beamline setup funcitons

def toggle_fc_mode():
    """Toggle between lab and beamtime modes"""
    if fc_mode.get() == 'beamtime':
        # Show beamtime frame
        frm_fc_beamtimechoice.grid(row=2, column=1, rowspan=3, 
                                   padx=10, pady=5, sticky='ew')
        # Initialize beamtime frames when first shown
        setup_beamtime_frames()
    else:
        # Hide beamtime frame
        frm_fc_beamtimechoice.grid_remove()



def setup_beamtime_frames():
    """Setup the beamtime analysis frames with radio button control"""
    global xas_beamtime_frame, xrd_beamtime_frame, combined_beamtime_frame
    
    # Configure grid weights for beamtime choice frame
    frm_fc_beamtimechoice.columnconfigure(0, weight=1)
    frm_fc_beamtimechoice.columnconfigure(1, weight=1)
    frm_fc_beamtimechoice.columnconfigure(2, weight=1)
    frm_fc_beamtimechoice.rowconfigure(1, weight=1)
    
    # Create radio buttons frame
    radio_frame.grid(row=0, column=0, columnspan=3, sticky='ew', pady=(0, 10))
    
    # Create radio buttons in a row
    rb_xas.grid(row=0, column=0, padx=(0, 10))
    rb_xrd.grid(row=0, column=1, padx=(0, 10))
    rb_combined.grid(row=0, column=2)
    
    # place beamline frame
    frm_fc_beamline.grid(row=1, column=0, padx=(0, 10))
    
    # Initially show the XAS frame
    show_xas_beamtime_frame()

def hide_all_beamtime_frames():
    """Hide all beamtime analysis frames"""
    try:
        xas_beamtime_frame.grid_remove()
        xrd_beamtime_frame.grid_remove()
        combined_beamtime_frame.grid_remove()
    except NameError:
        # Frames haven't been created yet
        pass

def show_xas_beamtime_frame():
    """Show XAS beamtime frame and hide others"""
    hide_all_beamtime_frames()
    xas_beamtime_frame.grid(row=2, column=0, columnspan=3, sticky='nsew', padx=10, pady=10)

def show_xrd_beamtime_frame():
    """Show XRD beamtime frame and hide others"""
    hide_all_beamtime_frames()
    xrd_beamtime_frame.grid(row=2, column=0, columnspan=3, sticky='nsew', padx=10, pady=10)

def show_combined_beamtime_frame():
    """Show combined beamtime frame and hide others"""
    hide_all_beamtime_frames()
    xas_beamtime_frame.grid(row=2, column=0, columnspan=3, sticky='nsew', padx=10, pady=10)
    xrd_beamtime_frame.grid(row=3, column=0, columnspan=3, sticky='nsew', padx=10, pady=10)

def on_beamtime_selection_change():
    """Handle beamtime radio button selection changes"""
    selection = beamtime_selection.get()
    
    if selection == "XAS":
        show_xas_beamtime_frame()
    elif selection == "XRD":
        show_xrd_beamtime_frame()
    elif selection == "XAS + XRD":
        show_combined_beamtime_frame()
        
        
def fc_convert_to_rhe(string_ref_potential1, string_ref_potential2, low, high, step, results_frame):
    """
    Convert applied potentials to RHE scale and populate the results frame.
    
    The conversion formula is:
    E_RHE = E_applied + E_ref
    
    Rearranging to find required applied potential:
    E_applied = E_RHE - E_ref
    
    Args:
        str_ref_potential1: StringVar containing the user input 
                            reference potential value IN THE FLOWCELL in mv
        str_ref_potential2: StringVar containing the user input MASTER 
                            reference potential value PREVIOUSLY CALIBRATED
                            vs. RHE in mv
                            
        results_frame: Frame widget to populate with results
    """
    try:
        low_flt = float(low.get())
        high_flt = float(high.get())
        step_flt = float(step.get())
    
    except ValueError:
        for widget in results_frame.winfo_children():
            widget.destroy()
        ttk.Label(results_frame, text="Error: Please enter a valid sweep range (low/high/step)",
                  foreground="red").grid(row=0, column=0, columnspan=2, padx=10, pady=20)
        return

    try:
        ref_potential1 = float(string_ref_potential1.get())
        ref_potential2 = float(string_ref_potential2.get())
    except ValueError:
        for widget in results_frame.winfo_children():
            widget.destroy()
        ttk.Label(results_frame, text="Error: Please enter valid reference potential values",
                  foreground="red").grid(row=0, column=0, columnspan=2, padx=10, pady=20)
        return

    ref_potential = ref_potential1 + ref_potential2
    potentials_array = arange(start=low_flt, stop=high_flt, step=step_flt)
        
    
    # Clear existing results
    for widget in results_frame.winfo_children():
        widget.destroy()
        
    # Create headers
    ttk.Label(results_frame, text="Erhe (V vs. RHE)", font=('Helvetica', 10, 'bold')).grid(
        row=0, column=0, padx=7, pady=5, sticky=tk.W)
    ttk.Label(results_frame, text="Ewe (V vs. Ref)", font=('Helvetica', 10, 'bold')).grid(
        row=2, column=0, padx=7, pady=5, sticky=tk.W)
        
    # Add separator
    ttk.Separator(results_frame, orient='horizontal').grid(
        row=1, column=0, columnspan=30, sticky=(tk.W, tk.E), pady=5)
        
        
        
    # Calculate and display conversion table
    row=0
    col = 1
        
    for i in range(len(potentials_array)):  
        e_rhe = potentials_array[i]
        # Calculate required applied potential: E_applied = E_RHE - E_ref
        e_applied = e_rhe - ref_potential/1000
        
        # Create labels for each row
        rhe_label = ttk.Label(results_frame, text=f"{e_rhe:.2f}", 
                                  font='Helvetica 10')
        rhe_label.grid(row=row, column=col, padx=10, pady=2, sticky=tk.W)
            
        applied_label = ttk.Label(results_frame, text=f"{e_applied:.3f}",
                                      font='Helvetica 10')
        applied_label.grid(row=row+2, column=col, padx=10, pady=2, sticky=tk.W)
            
        col += 1
        
    # Add reference information
    info_text = "Ewe = Erhe - Eref"
    ttk.Label(results_frame, text=info_text, font=('Helvetica', 10)).grid(
        row=row+3, column=0, columnspan=2, pady=(10, 0), sticky=tk.W)
        
    # except ValueError:
    #     # Clear results and show error
    #     for widget in results_frame.winfo_children():
    #         widget.destroy()
    #     error_label = ttk.Label(results_frame, text="Error: Please enter valid reference potential values", 
    #                           foreground="red")
    #     error_label.grid(row=0, column=0, columnspan=2, padx=10, pady=20)
        
## section for photon energy/wavelength conversion        
h = sc.Planck #J.s
c = sc.c #m/s
ang_to_m = 1E-10 #m/ang
J_per_eV = sc.physical_constants['electron volt'][0]
eV_per_J = 1/J_per_eV

def photon_converter(str_init_unit, value_to_convert, strvar_to_set):
    """Convert between photon energy (eV) and wavelength (Å) and update a StringVar."""
    if str_init_unit == 'Energy (eV)':
        converted_value = (h * c / (float(value_to_convert) * J_per_eV)) / ang_to_m
        strvar_to_set.set(f'λ = {converted_value:.5f} (Å)')
    elif str_init_unit == 'Wavelength (ang)':
        converted_value = (h * c / (float(value_to_convert) * ang_to_m)) * eV_per_J
        strvar_to_set.set(f'E = {converted_value:.5f} (eV)')
    else:
        raise ValueError("Incorrect photon input units. Use 'Energy (eV)' or 'Wavelength (ang)'.")



#%% 2.5 : Variable registry viewer
"""
Help-tab UI for displaying live variable registries (RDE / Flow Cell).
 
Adds two buttons to the help tab. Each button calls the shared
``VariableRegistryViewer`` with a different registry-builder function
(``build_rde_var_registry`` / ``build_fc_var_registry``), so both buttons
render into the same scrollable, read-only text widget rather than each
spawning a duplicate frame.
"""

class VariableRegistryViewer:
    """Lazily-built, reusable pane for rendering a variable registry.
 
    Owns a single frame containing a scrollable, read-only ``tk.Text``
    widget. Repeated calls to :meth:`show` clear and re-render into the
    same widget instead of creating new ones, so multiple "show registry"
    buttons can share one display area.
 
    Attributes:
        parent: The container widget the display frame is packed into.
        frame: The lazily-created ``tk.Frame`` holding the text widget
            and its scrollbar. ``None`` until first use.
        text_widget: The lazily-created, read-only ``tk.Text`` widget
            that the registry is rendered into. ``None`` until first use.
    """
 
    def __init__(self, parent: "tk.Widget", *, text_height: int = 20) -> None:
        """Initialise the viewer without building any widgets yet.
 
        Args:
            parent: Container (e.g. ``frm_help_view_vars``) to pack the
                display frame into on first use.
            text_height: Height, in text lines, of the Text widget.
        """
        self.parent = parent
        self.text_height = text_height
        self.frame: "tk.Frame | None" = None
        self.text_widget: "tk.Text | None" = None
 
    def _ensure_built(self) -> None:
        """Create and grid the frame/text/scrollbar on first use only.
 
        Builds the frame, scrollbar, and text widget in local variables
        first and only assigns them to ``self`` once every step has
        succeeded. This keeps construction atomic: if any step raises
        (e.g. a geometry-manager conflict), ``self.frame`` and
        ``self.text_widget`` are left as they were (both ``None`` on a
        first failed attempt) instead of ending up half-built — which
        would otherwise make a later call skip rebuilding while
        ``self.text_widget`` is still ``None``.
        """
        if self.frame is not None:
            return
 
        frame = tk.Frame(self.parent)
        # grid (not pack): frm_help_view_vars's other children (the
        # buttons) are placed with .grid(), and Tkinter does not allow
        # mixing geometry managers for children of the same parent.
        frame.grid(row=2, column=0, columnspan=1, padx=10, pady=5,
                   sticky='nsew')
 
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
 
        text_widget = tk.Text(
            frame,
            height=self.text_height,
            wrap=tk.NONE,
            yscrollcommand=scrollbar.set,
        )
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text_widget.yview)
 
        text_widget.configure(state='disabled')
 
        # Only now, after every step above has succeeded, publish state.
        self.frame = frame
        self.text_widget = text_widget
 
    @staticmethod
    def _read_widget_value(widget: object) -> str:
        """Read the current value from a registry entry's live widget.
 
        Mirrors the type check used in ``_collect_log_row_rde()``: a
        ``tk.Text`` is read via ``get('1.0', 'end-1c')``; anything else
        (``StringVar``, OptionMenu-backed ``StringVar``, etc.) via
        ``.get()``.
 
        Args:
            widget: The live widget/variable stored in the registry.
 
        Returns:
            str: The widget's current value.
        """
        if isinstance(widget, tk.Text):
            return widget.get('1.0', 'end-1c')
        return widget.get()
 
    def show(self, registry_builder: Callable[[], dict[str, object]]) -> None:
        """Build a registry and render it into the shared display widget.
 
        Strategy pattern: the caller supplies *which* registry to render
        (``build_rde_var_registry`` or ``build_fc_var_registry``) without
        this method needing to know about either.
 
        Args:
            registry_builder: A zero-arg callable returning a
                ``{variable_name: live_widget}`` mapping, e.g.
                ``build_rde_var_registry`` or ``build_fc_var_registry``.
 
        Returns:
            None; updates ``self.text_widget`` in place.
        """
        self._ensure_built()
        registry = registry_builder()
 
        self.text_widget.configure(state='normal')
        self.text_widget.delete('1.0', tk.END)
 
        for var_name, widget in registry.items():
            value = self._read_widget_value(widget)
            self.text_widget.insert(tk.END, f"{var_name!r}: {value!r}\n")
 
        self.text_widget.configure(state='disabled')
        

#%% 2.6 : updated master log funcitons

"""
master_log_common.py
=====================
Shared helpers for experiment master-log sessions (RDE, Flowcell, ...).

Previously these lived only in ``rde_master_log.py`` and were reused by
``flowcell_master_log.py`` implicitly, by relying on both files executing
as cells in one shared script namespace. That's fragile: if the files are
ever imported independently, or the cell execution order changes, the
Flowcell functions calling ``_load_and_validate_config`` /
``_append_row_to_log`` raise ``NameError``. Both experiment modules should
now do::

    from master_log_common import (
        LogSession, load_and_validate_config, append_row_to_log,
        collect_log_row,
    )
"""

TIMESTAMP_FORMAT: str = '%Y-%m-%d %H:%M:%S'
CONFIG_REQUIRED_COLUMNS: tuple[str, ...] = ('variable_name', 'column_label')

WRITE_RETRIES: int = 3
WRITE_RETRY_DELAY_S: float = 0.1


# ──────────────────────────────────────────────────────────────────────────
# Session state (generic — one instance per experiment tab)
# ──────────────────────────────────────────────────────────────────────────

@dataclass
class LogSession:
    """Holds the paths chosen during setup so file dialogs run only once."""
    config_path: Optional[Path] = field(default=None)
    master_path: Optional[Path] = field(default=None)

    @property
    def is_ready(self) -> bool:
        """True when both paths have been set."""
        return self.config_path is not None and self.master_path is not None

    def reset(self) -> None:
        """Clear all stored paths."""
        self.config_path = None
        self.master_path = None


# ──────────────────────────────────────────────────────────────────────────
# Config validation
# ──────────────────────────────────────────────────────────────────────────

def load_and_validate_config(config_path: Path) -> pd.DataFrame:
    """Load the log config CSV and verify it has the required columns.

    Args:
        config_path: Absolute path to the config CSV file.

    Returns:
        pd.DataFrame with at least ``variable_name`` and ``column_label``.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If required columns are absent or the file is empty.
    """
    config = pd.read_csv(config_path)

    if config.empty:
        raise ValueError("Config file is empty.")

    missing = [c for c in CONFIG_REQUIRED_COLUMNS if c not in config.columns]
    if missing:
        raise ValueError(
            f"Config file is missing required column(s): {missing}\n"
            f"Expected : {list(CONFIG_REQUIRED_COLUMNS)}\n"
            f"Found    : {list(config.columns)}"
        )

    return config


# ──────────────────────────────────────────────────────────────────────────
# Row collection
# ──────────────────────────────────────────────────────────────────────────

def collect_log_row(
    config: pd.DataFrame,
    registry: dict[str, object],
) -> tuple[dict[str, str], list[str], list[str]]:
    """Read current widget values for each config entry.

    Handles ``tk.Text`` widgets separately from StringVar / OptionMenu
    variables. Any widget that is ``None`` (e.g. a StringVar that was
    accidentally overwritten by chaining ``tk.StringVar().set('')``,
    which returns ``None``) is reported instead of raising deep inside
    ``.get()`` — an uncaught exception here, if this function is ever
    called outside a try/except, fails *silently* from the GUI's
    perspective because Tkinter swallows callback exceptions to stderr.

    Args:
        config: Validated config DataFrame.
        registry: Mapping produced by a ``build_*_var_registry()`` call.

    Returns:
        A tuple of:
        - ``row_data``: Column label -> current value, with a leading
          ``'Timestamp'`` entry.
        - ``unknown``: variable_names in the config absent from the
          registry.
        - ``broken``: variable_names present in the registry but whose
          widget is ``None`` (mis-initialized) or otherwise unreadable.
    """
    row_data: dict[str, str] = {
        'Timestamp': datetime.now().strftime(TIMESTAMP_FORMAT)
    }
    unknown: list[str] = []
    broken: list[str] = []

    for var_name, col_label in zip(
        config['variable_name'], config['column_label']
    ):
        if var_name not in registry:
            unknown.append(var_name)
            continue

        widget = registry[var_name]

        if widget is None:
            # Most likely cause: `var = tk.StringVar(); var.set('')` was
            # written as `var = tk.StringVar().set('')`, which assigns
            # None to var instead of the StringVar.
            broken.append(var_name)
            continue

        try:
            if isinstance(widget, tk.Text):
                row_data[col_label] = widget.get(1.0, 'end').strip()
            else:
                row_data[col_label] = widget.get()
        except Exception:
            broken.append(var_name)

    return row_data, unknown, broken


# ──────────────────────────────────────────────────────────────────────────
# Writing the log
# ──────────────────────────────────────────────────────────────────────────

def _normalized(headers: list[str]) -> list[str]:
    """Trim whitespace so trivial formatting differences don't false-fail
    the column-mismatch guard."""
    return [h.strip() for h in headers]


def append_row_to_log(master_path: Path, row_data: dict[str, str]) -> None:
    """Append one data row to the master CSV, writing headers if new.

    Hardened against the ways a "new or renamed" log file previously
    failed to save:
      - the path is forced to end in ``.csv`` (some OS save dialogs don't
        always append ``defaultextension`` for a freshly typed filename);
      - the parent directory is created if it doesn't exist yet;
      - a pre-existing but *empty* file (e.g. a placeholder created by
        renaming/touching a file in Explorer/Finder before pointing the
        dialog at it) is treated as headerless rather than raising
        ``pandas.errors.EmptyDataError`` out of ``pd.read_csv``;
      - after writing, the file is re-read and the row count is verified
        to have actually increased, so callers never report success on
        a write that silently didn't land (e.g. a locked/synced file).

    Args:
        master_path: Absolute path to the master log CSV.
        row_data: Ordered dict of ``{column_label: value}`` including
            ``'Timestamp'``.

    Raises:
        ValueError: If ``row_data`` columns do not match the existing
            file's header.
        OSError: If the file cannot be written after all retries, or if
            the write could not be verified on disk.
    """
    if master_path.suffix.lower() != '.csv':
        master_path = master_path.with_suffix('.csv')

    master_path.parent.mkdir(parents=True, exist_ok=True)

    file_exists = master_path.exists()
    file_has_header = file_exists and master_path.stat().st_size > 0
    incoming_header = list(row_data.keys())

    rows_before = 0
    if file_has_header:
        existing_header = pd.read_csv(master_path, nrows=0).columns.tolist()
        if _normalized(existing_header) != _normalized(incoming_header):
            raise ValueError(
                "Config columns do not match the existing master log.\n\n"
                f"Expected : {existing_header}\n"
                f"Incoming : {incoming_header}\n\n"
                "Use the original config file, or choose a new master "
                "log path."
            )
        with open(master_path, 'r', encoding='utf-8') as f:
            rows_before = sum(1 for _ in f) - 1  # minus header

    df = pd.DataFrame([row_data])
    last_error: Optional[Exception] = None

    for _ in range(WRITE_RETRIES):
        try:
            df.to_csv(
                master_path,
                mode='a',
                index=False,
                header=not file_has_header,
            )
            break
        except OSError as exc:
            last_error = exc
            time.sleep(WRITE_RETRY_DELAY_S)
    else:
        raise OSError(
            f"Failed to write to log after {WRITE_RETRIES} attempts."
        ) from last_error

    # ── Verify the write actually landed ────────────────────────────────
    try:
        with open(master_path, 'r', encoding='utf-8') as f:
            rows_after = sum(1 for _ in f) - 1
    except OSError as exc:
        raise OSError(
            f"Wrote to {master_path.name} but could not verify the "
            f"row was saved: {exc}"
        ) from exc

    if rows_after != rows_before + 1:
        raise OSError(
            f"Append did not take effect: expected {rows_before + 1} "
            f"data row(s) in {master_path.name}, found {rows_after}. "
            "The file may be locked or synced by another program."
        )

################### RDE master log contents ##################################
"""
modified rde_master_log.py
=================
RDE experiment master-log helpers.

Public API
----------
rde_setup_log()              -- select config + master log paths once per session
rde_clear_log_session()      -- reset session state (e.g. on tab reset)
rde_append_to_master_log()   -- append one row; requires setup to have run first
build_rde_var_registry()     -- build the variable registry from live StringVars

Usage
-----
Call ``rde_setup_log()`` from a "Setup Log" button once.
Call ``rde_append_to_master_log()`` from the "Append to Log" button thereafter.

Notes
-----
``ent_notes`` is a ``tk.Text`` widget (not a StringVar) and requires
``.get(1.0, 'end')`` to read its contents.  It is stored directly in the
registry as a widget object; ``collect_log_row()`` (in ``master_log_common``)
detects it via ``isinstance(widget, tk.Text)`` and calls the correct method
automatically. Any additional ``tk.Text`` widgets can be added to the
registry without further changes to the collector.
"""

# ──────────────────────────────────────────────────────────────────────────────
# Session state — one session per tab, explicitly typed via the shared class
# ──────────────────────────────────────────────────────────────────────────────

_session1 = LogSession()


# ──────────────────────────────────────────────────────────────────────────────
# Variable registry
# ──────────────────────────────────────────────────────────────────────────────

def build_rde_var_registry() -> dict[str, object]:
    """Build the loggable-variable registry from live RDE Tkinter widgets.

    Both StringVar/OptionMenu variables and ``tk.Text`` widgets are stored
    directly as their live widget objects.  ``collect_log_row()`` detects
    the type at collection time via ``isinstance(widget, tk.Text)`` and
    calls the appropriate read method — no sentinel or special-casing
    needed here.

    Returns:
        dict[str, object]: Mapping of config-file ``variable_name`` strings
        to their live widget objects.

    Note:
        Call this *after* all widgets have been initialised.
    """
    return {
        # ── Identification ────────────────────────────────────────────────────
        'str_author':                   str_author,
        'str_material_id':              str_material_id,
        'str_ink_id':                   str_ink_id,
        'clicked_ink':                  clicked_ink,
        'str_trial_id':                 str_trial_id,
        # ── Filename ──────────────────────────────────────────────────────────
        'filename_mode':                filename_mode,
        'str_user_filename':            str_user_filename,
        'str_generated_filename':       str_generated_filename,
        'str_Links':                    str_Links,
        # ── Ink / catalyst ────────────────────────────────────────────────────
        'str_ink_mass':                 str_ink_mass,
        'str_ink_vol':                  str_ink_vol,
        'str_ink_conc':                 str_ink_conc,
        # ── Experiment intent ─────────────────────────────────────────────────
        'str_purpose':                  str_purpose,
        'str_reaction':                 str_reaction,
        'clicked_exp_type':             clicked_exp_type,
        'str_user_exp_type':            str_user_exp_type,
        # ── Electrolyte ───────────────────────────────────────────────────────
        'str_electrolyte_conc':         str_electrolyte_conc,
        'str_electrolyte_chem':         str_electrolyte_chem,
        'str_impurity':                 str_impurity,
        # ── Reference electrode ───────────────────────────────────────────────
        'clicked_ref_type':             clicked_ref_type,
        'str_ref_potential':            str_ref_potential,
        # ── Electrode / cell configuration ────────────────────────────────────
        'str_rotation':                 str_rotation,
        'clicked_counter_elctrd_type':  clicked_counter_elctrd_type,
        'clicked_elctrd_type':          clicked_elctrd_type,
        'str_area':                     str_area,
        'clicked_cell_type':            clicked_cell_type,
        'clicked_cell_mat_type':        clicked_cell_mat_type,
        # ── Notes — tk.Text widget; read via isinstance check in collector ──────
        'ent_notes':                    ent_notes,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def rde_setup_log() -> None:
    """Select the config file and master log path for this RDE session.

    Should be called once via the "Setup Log" button.  Subsequent calls to
    ``rde_append_to_master_log()`` reuse these paths without prompting.
    Calling ``rde_setup_log()`` again resets and re-prompts.

    Returns:
        None: Updates ``_session1`` in place.  Shows an info dialog confirming
        the selected paths, or does nothing if the user cancels either dialog.
    """
    # ── Config file ───────────────────────────────────────────────────────────
    config_str = fd.askopenfilename(
        title='Select RDE Log Config CSV',
        filetypes=[('CSV files', '*.csv'), ('All files', '*.*')]
    )
    if not config_str:
        return
    config_path = Path(config_str)

    try:
        load_and_validate_config(config_path)
    except Exception as exc:
        messagebox.showerror("Invalid Config File", str(exc))
        return

    # ── Master log file ───────────────────────────────────────────────────────
    master_str = fd.asksaveasfilename(
        title='Select or Create RDE Master Log CSV',
        defaultextension='.csv',
        filetypes=[('CSV files', '*.csv'), ('All files', '*.*')],
        initialfile='rde_master_log.csv',
        initialdir=str(config_path.parent),
    )
    if not master_str:
        return

    _session1.reset()
    _session1.config_path = config_path
    master_path = Path(master_str)
    if master_path.suffix.lower() != '.csv':
        master_path = master_path.with_suffix('.csv')
    _session1.master_path = master_path

    _update_rde_log_button_states()

    messagebox.showinfo(
        "RDE Log Session Ready",
        f"Config : {_session1.config_path.name}\n"
        f"Log    : {_session1.master_path.name}\n\n"
        "Click 'Append to Log' to record a row."
    )


def rde_clear_log_session() -> None:
    """Reset the RDE log session, requiring ``rde_setup_log()`` to run again.

    Useful when switching experiments or config files mid-session.

    Returns:
        None
    """
    _session1.reset()
    _update_rde_log_button_states()


def rde_append_to_master_log() -> None:
    """Append one row of current RDE widget values to the master log CSV.

    Requires ``rde_setup_log()`` to have been called first.  On every call
    the current widget values are read fresh, so incrementing ``str_trial_id``
    or any other field between calls is reflected automatically.

    Aborts with a clear error dialog if:

    - The session has not been set up.
    - The config file has missing or invalid columns.
    - Any ``variable_name`` in the config is absent from the registry, or
      maps to a mis-initialized (``None``) widget.
    - The incoming columns do not match an existing master log.
    - The file cannot be written or the write cannot be verified.

    Returns:
        None
    """
    # ── Guard: session must be ready ──────────────────────────────────────────
    if not _session1.is_ready:
        messagebox.showerror(
            "Log Not Set Up",
            "Please click 'Setup Log' before appending rows."
        )
        return

    registry = build_rde_var_registry()

    # ── Load and validate config ──────────────────────────────────────────────
    try:
        config = load_and_validate_config(_session1.config_path)
    except Exception as exc:
        messagebox.showerror("Config Error", str(exc))
        return

    # ── Collect row values ────────────────────────────────────────────────────
    try:
        row_data, unknown, broken = collect_log_row(config, registry)
    except Exception as exc:
        messagebox.showerror("Unexpected Error Reading Fields", str(exc))
        return

    if unknown:
        messagebox.showerror(
            "Unknown Variables in Config",
            "The following variable name(s) were not found in the registry.\n"
            "Fix the config file and try again:\n\n"
            + "\n".join(f"  • {v}" for v in unknown)
        )
        return

    if broken:
        messagebox.showerror(
            "Unreadable Fields",
            "The following variable(s) are registered but could not be "
            "read (likely mis-initialized as None instead of a live "
            "StringVar/Text widget):\n\n"
            + "\n".join(f"  • {v}" for v in broken)
        )
        return

    # ── Append to log ─────────────────────────────────────────────────────────
    try:
        append_row_to_log(_session1.master_path, row_data)
    except ValueError as exc:
        messagebox.showerror("Column Mismatch", str(exc))
        return
    except OSError as exc:
        messagebox.showerror("Write Error", str(exc))
        return

    messagebox.showinfo(
        "Row Logged",
        f"Row appended to:\n{_session1.master_path}"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Button state helper
# ──────────────────────────────────────────────────────────────────────────────

def _update_rde_log_button_states() -> None:
    """Enable or disable RDE log buttons to reflect current session state."""
    if _session1.is_ready:
        btn_rde_append_log.configure(state='normal')
        btn_rde_clear_log.configure(state='normal')
        btn_rde_setup_log.configure(
            text=f'Log: {_session1.master_path.stem}',
            bg='lightgreen'
        )
    else:
        btn_rde_append_log.configure(state='disabled')
        btn_rde_clear_log.configure(state='disabled')
        btn_rde_setup_log.configure(text='Setup Log Session', bg='lightyellow')

"""
modified fc_master_log.py
================
Flowcell experiment master-log helpers.

Public API
----------
fc_setup_log()              -- select config + master log paths once per session
fc_clear_log_session()      -- reset session state (e.g. on tab reset)
fc_append_to_master_log()   -- append one row; requires setup to have run first
build_fc_var_registry()     -- build the variable registry from live StringVars

Usage
-----
Call ``fc_setup_log()`` from a "Setup Log" button once.
Call ``fc_append_to_master_log()`` from the "Append to Log" button thereafter.
"""


# ──────────────────────────────────────────────────────────────────────────────
# Session state — one session per tab, explicitly typed via the shared class
# ──────────────────────────────────────────────────────────────────────────────

_session = LogSession()


# ──────────────────────────────────────────────────────────────────────────────
# Variable registry
# ──────────────────────────────────────────────────────────────────────────────

def build_fc_var_registry() -> dict[str, object]:
    """Build the loggable-variable registry from live Tkinter StringVars.

    Returns:
        dict[str, tk.StringVar]: Mapping of config-file ``variable_name``
        strings to their live ``StringVar`` objects.

    Note:
        Call this *after* all StringVars have been initialised (i.e. not at
        import time).  Several XAS/XRD vars (e.g. ``str_fc_enrgymin``) are/were
        initialised with ``tk.StringVar().set('')``, which returns ``None``
        (``.set()`` has no return value) instead of the StringVar itself.
        ``collect_log_row()`` now detects a ``None`` entry here and reports
        it by name via a dialog rather than raising deep inside ``.get()``,
        but the initialization itself should still be fixed wherever these
        vars are defined, e.g.::

            str_fc_enrgymin = tk.StringVar()
            str_fc_enrgymin.set('')
    """

    return {
        # ── Identification ────────────────────────────────────────────────────
        'str_fc_author':                  str_fc_author,
        'str_fc_material_id':             str_fc_material_id,
        'str_fc_electrode_id':            str_fc_electrode_id,
        'clicked_ink_fc':                 clicked_ink_fc,
        'str_fc_trial_id':                str_fc_trial_id,
        # ── Experiment intent ─────────────────────────────────────────────────
        'str_fc_purpose':                 str_fc_purpose,
        'str_fc_reaction':                str_fc_reaction,
        'fc_clicked_exp_type':            fc_clicked_exp_type,
        # ── Working electrode ─────────────────────────────────────────────────
        'str_fc_electrode_mass':          str_fc_electrode_mass,
        'str_fc_electrode_area':          str_fc_electrode_area,
        # ── Counter electrode ─────────────────────────────────────────────────
        'str_fc_CE_id':                   str_fc_CE_id,
        'str_fc_CE_mass':                 str_fc_CE_mass,
        'clicked_fc_counter_elctrd_type': clicked_fc_counter_elctrd_type,
        # ── Electrolyte ───────────────────────────────────────────────────────
        'str_fc_electrolyte_conc':        str_fc_electrolyte_conc,
        'str_fc_electrolyte_chem':        str_fc_electrolyte_chem,
        'str_fc_impurity':                str_fc_impurity,
        'str_fc_flowrate':                str_fc_flowrate,
        'str_fc_gasflowrate':             str_fc_gasflowrate,
        # ── Reference electrodes ──────────────────────────────────────────────
        'clicked_fc_ref_type1':           clicked_fc_ref_type1,
        'str_fc_ref_potential1':          str_fc_ref_potential1,
        'clicked_fc_ref_type2':           clicked_fc_ref_type2,
        'str_fc_ref_potential2':          str_fc_ref_potential2,
        # ── Flowcell assembly ─────────────────────────────────────────────────
        'str_fc_gasketmembrane':          str_fc_gasketmembrane,
        'str_fc_torque':                  str_fc_torque,
        'str_fc_electThick':              str_fc_electThick,
        'str_fc_cell_id':                 str_fc_cell_id,
        'fc_clicked_cell_mat_type':       fc_clicked_cell_mat_type,
        # ── Beamtime — common ─────────────────────────────────────────────────
        'str_fc_beamline_expid':          str_fc_beamline_expid,
        'str_fc_beamline':                str_fc_beamline,
        'str_fc_optics':                  str_fc_optics,
        'str_fc_mono':                    str_fc_mono,
        'str_fc_filter':                  str_fc_filter,
        'str_fc_I0':                      str_fc_I0,
        'str_fc_beamspot':                str_fc_beamspot,
        # ── Beamtime — XAS ───────────────────────────────────────────────────
        'str_fc_enrgymin':                str_fc_enrgymin,
        'str_fc_enrgymax':                str_fc_enrgymax,
        'str_fc_steps':                   str_fc_steps,
        'str_fc_freq':                    str_fc_freq,
        'str_fc_detector1':               str_fc_detector1,
        'str_fc_detectmode':              str_fc_detectmode,
        # ── Beamtime — XRD ───────────────────────────────────────────────────
        'fc_clicked_photon':              fc_clicked_photon,
        'str_fc_photonoutput':            str_fc_photonoutput,
        'str_fc_2thetamin':               str_fc_2thetamin,
        'str_fc_2thetamax':               str_fc_2thetamax,
        'str_fc_detector2':               str_fc_detector2,
        'str_fc_detector2dist':           str_fc_detector2dist,
        'str_fc_xrddetectmode':           str_fc_xrddetectmode,
        # ── Notes / links ─────────────────────────────────────────────────────
        'ent_fc_notes':                   ent_fc_notes,    # tk.Text widget
        'beamline_notes':                 beamline_notes,  # tk.Text widget
        'str_fc_Links':                   str_fc_Links,
        # ── Generated filename ────────────────────────────────────────────────
        'str_fc_generated_filename':      str_fc_generated_filename,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def fc_setup_log() -> None:
    """Select the config file and master log path for this session.

    Should be called once via a dedicated "Setup Log" button.  Subsequent
    calls to ``fc_append_to_master_log()`` reuse these paths without
    prompting the user again.  Calling ``fc_setup_log()`` again resets
    and re-prompts.

    Returns:
        None: Updates ``_session`` in place.  Shows an info dialog
        confirming the selected paths, or does nothing if the user cancels.
    """
    # ── Config file ───────────────────────────────────────────────────────────
    config_str = fd.askopenfilename(
        title='Select Log Config CSV',
        filetypes=[('CSV files', '*.csv'), ('All files', '*.*')]
    )
    if not config_str:
        return  # User cancelled — leave session unchanged
    config_path = Path(config_str)

    # Validate config immediately so the user gets feedback at setup time,
    # not silently at the first append.
    try:
        load_and_validate_config(config_path)
    except Exception as exc:
        messagebox.showerror("Invalid Config File", str(exc))
        return

    # ── Master log file ───────────────────────────────────────────────────────
    master_str = fd.asksaveasfilename(
        title='Select or Create Master Log CSV',
        defaultextension='.csv',
        filetypes=[('CSV files', '*.csv'), ('All files', '*.*')],
        initialfile='fc_master_log.csv',
        initialdir=str(config_path.parent),
    )
    if not master_str:
        return  # User cancelled

    _session.reset()
    _session.config_path = config_path
    master_path = Path(master_str)
    if master_path.suffix.lower() != '.csv':
        master_path = master_path.with_suffix('.csv')
    _session.master_path = master_path

    # Update button states to reflect ready session
    _update_log_button_states()

    messagebox.showinfo(
        "Log Session Ready",
        f"Config : {_session.config_path.name}\n"
        f"Log    : {_session.master_path.name}\n\n"
        "Click 'Append to Log' to record a row."
    )


def fc_clear_log_session() -> None:
    """Reset the log session, requiring ``fc_setup_log()`` to run again.

    Useful when switching experiments or config files mid-session.

    Returns:
        None
    """
    _session.reset()
    _update_log_button_states()


def fc_append_to_master_log() -> None:
    """Append one row of current FC widget values to the master log CSV.

    Requires ``fc_setup_log()`` to have been called first.  Aborts with a
    clear error dialog if:

    - The session has not been set up.
    - The config file has missing/invalid columns.
    - Any ``variable_name`` in the config is absent from the registry, or
      maps to a mis-initialized (``None``) widget.
    - The incoming columns do not match an existing master log.
    - The file cannot be written or the write cannot be verified.

    Returns:
        None
    """
    # ── Guard: session must be ready ──────────────────────────────────────────
    if not _session.is_ready:
        messagebox.showerror(
            "Log Not Set Up",
            "Please click 'Setup Log' before appending rows."
        )
        return

    registry = build_fc_var_registry()

    # ── Load and validate config ──────────────────────────────────────────────
    try:
        config = load_and_validate_config(_session.config_path)
    except Exception as exc:
        messagebox.showerror("Config Error", str(exc))
        return

    # ── Collect row values ────────────────────────────────────────────────────
    # This used to be uncaught: an AttributeError from a mis-initialized
    # widget (registry value of None) would raise here, and because this
    # runs inside a Tkinter button callback, Tkinter prints the traceback
    # to stderr and swallows it — the button appears to do nothing at all.
    try:
        row_data, unknown, broken = collect_log_row(config, registry)
    except Exception as exc:
        messagebox.showerror("Unexpected Error Reading Fields", str(exc))
        return

    if unknown:
        messagebox.showerror(
            "Unknown Variables in Config",
            "The following variable name(s) were not found in the registry.\n"
            "Fix the config file and try again:\n\n"
            + "\n".join(f"  • {v}" for v in unknown)
        )
        return

    if broken:
        messagebox.showerror(
            "Unreadable Fields",
            "The following variable(s) are registered but could not be "
            "read (likely mis-initialized as None instead of a live "
            "StringVar/Text widget):\n\n"
            + "\n".join(f"  • {v}" for v in broken)
        )
        return

    # ── Append to log ─────────────────────────────────────────────────────────
    try:
        append_row_to_log(_session.master_path, row_data)
    except ValueError as exc:
        messagebox.showerror("Column Mismatch", str(exc))
        return
    except OSError as exc:
        messagebox.showerror("Write Error", str(exc))
        return

    messagebox.showinfo(
        "Row Logged",
        f"Row appended to:\n{_session.master_path}"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Button state helper
# ──────────────────────────────────────────────────────────────────────────────

def _update_log_button_states() -> None:
    """Enable or disable log buttons to reflect the current session state.

    The append button is only active when the session is ready; the clear
    button is only active when there is a session to clear. The setup
    button label now reflects the master log filename (what a rename
    actually changes), not the config filename — previously it always
    showed the config name, so a successful rename gave no visible
    confirmation.
    """
    if _session.is_ready:
        btn_fc_append_log.configure(state='normal')
        btn_fc_clear_log.configure(state='normal')
        btn_fc_setup_log.configure(
            text=f'Log: {_session.master_path.stem}',
            bg='lightgreen'
        )
    else:
        btn_fc_append_log.configure(state='disabled')
        btn_fc_clear_log.configure(state='disabled')
        btn_fc_setup_log.configure(text='Setup Log', bg='lightyellow')



#%% 3.0: Window funcitons

# Update scroll region when content changes
def configure_scroll_region(event=None):
    canvas.configure(scrollregion=canvas.bbox("all"))

def configure_canvas_window(event=None):
    canvas_width = event.width
    canvas.itemconfig(canvas_window, width=canvas_width)

# Mouse wheel scrolling #BUG: horizontal scroll bar?????
## Gave up, have to graduate...
def _on_mousewheel(event):
    canvas.yview_scroll(int(-1*(event.delta/120)), "units")

#%% 3.1: window creation

#variable that prevents button commands from running prior to click
global clicked
clicked = False
 
#--------Master application window-----------
window = tk.Tk()
window.title('MetaMizer')
window.geometry('980x1200')#WxH
window.resizable(width=True, height=True)

# Create scrollable container
main_frame = tk.Frame(window)
main_frame.pack(fill=tk.BOTH, expand=1)

# Canvas for scrolling
canvas = tk.Canvas(main_frame, bg='white')
canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

# Scrollbars
v_scrollbar = tk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

h_scrollbar = tk.Scrollbar(window, orient=tk.HORIZONTAL, command=canvas.xview)
h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

# Configure canvas scrolling
canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

# Frame to hold all content
content_frame = tk.Frame(canvas)
canvas_window = canvas.create_window((0, 0), window=content_frame, anchor="nw")




content_frame.bind("<Configure>", configure_scroll_region)
canvas.bind("<Configure>", configure_canvas_window)



canvas.bind_all("<MouseWheel>", _on_mousewheel)

#--------Setting up tabs for different processes-----------
tabControler = ttk.Notebook(content_frame)  # Use content_frame instead of window
## no scrolling option
# tabControler = ttk.Notebook(window)

tab_rde = ttk.Frame(tabControler)
tab_flowcell = ttk.Frame(tabControler)
# tab_gde = ttk.Frame(tabControler)
# tab_ftir = ttk.Frame(tabControler)
tab_help = ttk.Frame(tabControler)

tabControler.add(tab_rde, text='RDE')
tabControler.add(tab_flowcell, text='Flow cell')
# tabControler.add(tab_gde, text='GDE')
# tabControler.add(tab_ftir, text='FTIR')
tabControler.add(tab_help, text='Help')

tabControler.pack(expand=1, fill='both') #populates window with tab contents


#%% 4.0: Setting up RDE tab
#--------Logic flow------------------------
lbl_logic = tk.Label(master=tab_rde, 
                     text='Logic: 1) Input metadata, 2) update/copy filename, 3) save metadata file, 4) setup/update master log [optional]', 
                    font='Helvetica 12 bold',  )
lbl_logic.grid(row=0, column=0, padx=10, pady=5, sticky='ew')

#--------Loading ink recipe data-----------
#Frame for ink structures
frm_loading = tk.Frame(master=tab_rde, 
                       highlightbackground='blue', highlightthickness=2,
                       bd=0)  # Remove fixed width/height

frm_loading.grid_columnconfigure(0, weight=1)
frm_loading.grid_columnconfigure(1, weight=1)
# frm_loading.grid_columnconfigure(2, weight=1)
frm_loading.grid(row=1, column=0, padx=10, pady=5, sticky='ew')

lbl_loading = tk.Label(master=frm_loading, text='Select Ink Recipe', 
                    font='Helvetica 14 bold',  fg='darkblue')
#grid relative within frame
lbl_loading.grid(row=0, column=0, columnspan=2, pady=2, sticky='n' )

#--------Browse Button-----------
btn_browse = tk.Button(master=frm_loading, text='Show me the inks!', 
                       font='Helvetica 10 bold',
                       command= lambda:browseInks() )
btn_browse.grid(row=1, column=0, pady=2)

#--------Ink choice-----------

##vinitial variables to modify with user fuctions
ink_drop_options = ['load recipe book first']

#Create dropdown menu for ink recipe selection 
clicked_ink = tk.StringVar()
clicked_ink.set('')

frm_ink_dropchoice = tk.Frame(master=frm_loading, )
lbl_inks = tk.Label(frm_ink_dropchoice, text='Ink to use?', font='Helvetica 10 bold')
drop_inks = tk.OptionMenu(frm_ink_dropchoice, clicked_ink , *ink_drop_options)

'''make separate frame and put frame in column 1?'''
lbl_inks.grid(row=0, column=0, padx=5, pady=7)
drop_inks.grid(row=0, column=1, padx=5, pady=7)
#place frame with ink choice menu
frm_ink_dropchoice.grid(row=1, column=1, pady=5)


#--------Display of loaded file-----------
lbl_browser_files_to_open = tk.Label(frm_loading, text = 'Recipe Book:',
                                     font='Helvetica 10 bold')
lbl_browser_files_to_open.grid(row=2, column=0, columnspan=2, pady=2)


#%% 4.1: RDE ink batch frame

#--------ink calculation and values variables -----------
#Frame for calculating ink component values
frm_ink_calc = tk.Frame(master=tab_rde, 
                       highlightbackground='blue', highlightthickness=2,
                       bd=0)  # Remove fixed width/height
frm_ink_calc.grid(row=2, column=0, padx=10, pady=5, sticky='ew')
for i in range(10):
    frm_ink_calc.grid_columnconfigure(i, weight=1)
    
# Frame title
lbl_ink_title = tk.Label(master=frm_ink_calc, text='Ink Batch', 
                         font='Helvetica 14 bold', fg='darkblue')
lbl_ink_title.grid(row=0, column=0,columnspan=12, pady=(0, 10), sticky='n')

#Catalyst mass input
str_ink_mass = tk.StringVar()
str_ink_mass.set('')
ent_ink_mass = tk.Entry(master=frm_ink_calc, textvariable=str_ink_mass, width=7)
lbl_catalyst = tk.Label(master=frm_ink_calc, text='Catalyst (mg)', font='Helvetica 10 bold')
lbl_cat_mg = tk.Label(master=frm_ink_calc, text='mg')

lbl_catalyst.grid(row=1, column=0, padx=5, sticky='w')
# lbl_cat_mg.grid(row=2, column=1, sticky='w')
ent_ink_mass.grid(row=2, column=0, padx=5, sticky='w')

# Material ID Entry
lbl_material_id = tk.Label(master=frm_ink_calc, text='Material ID', font='Helvetica 10 bold')
str_material_id = tk.StringVar()
str_material_id.set('')
ent_material_id = tk.Entry(master=frm_ink_calc, textvariable=str_material_id, width=15)
ent_material_id.grid(row=1, column=0, padx=5, pady=2, sticky='ew')

# ink ID Entry
lbl_ink_id = tk.Label(master=frm_ink_calc, text='Ink ID', font='Helvetica 10 bold')
str_ink_id = tk.StringVar()
str_ink_id.set('')
ent_ink_id = tk.Entry(master=frm_ink_calc, textvariable=str_ink_id, width=10)

# Calculate Ink components button with validation
btn_calculate = tk.Button(master=frm_ink_calc, 
                         text='Calculate Ink Components', 
                         command=calculate_with_validation,
                         bg='lightgreen',
                         fg='darkgreen',
                         font='Helvetica 10 bold',
                         relief='raised',
                         borderwidth=2)

# ink volume Entry
lbl_ink_vol = tk.Label(master=frm_ink_calc, text='Ink volume (uL)', font='Helvetica 10 bold')
str_ink_vol= tk.StringVar()
str_ink_vol.set('')
ent_ink_vol = tk.Entry(master=frm_ink_calc, textvariable=str_ink_vol, width=10)

#### upper frame placements
lbl_material_id.grid(row=1, column=1, padx=5, pady=2, sticky='ew')
ent_material_id.grid(row=2, column=1, padx=5, pady=2, sticky='ew')
lbl_ink_id.grid(row=1, column=2, padx=5, pady=2, sticky='ew')
ent_ink_id.grid(row=2, column=2, padx=5, pady=2, sticky='ew')

btn_calculate.grid(row=2, column=3, columnspan=2, rowspan=1, pady=2, padx=5, sticky='w')
lbl_ink_vol.grid(row=1, column=5, padx=5, pady=2, sticky='w')
ent_ink_vol.grid(row=2, column=5, columnspan=2, rowspan=1, pady=5, padx=5, sticky='w')

#--------ink concentration storage -----------
str_ink_conc = tk.StringVar()
str_ink_conc.set('0')
# ent_ink_conc = tk.Entry(master=frm_ink_calc, textvariable=str_ink_conc, width=7)
lbl_conc = tk.Label(master=frm_ink_calc, text='Conc. \n(mg/mL)', font='Helvetica 10 bold')
lbl_conc_mgmL = tk.Label(master=frm_ink_calc, text='mg/mL')

lbl_conc.grid(row=3, column=0, columnspan=2, sticky='w')

lbl_recipe_conc = tk.Label(master=frm_ink_calc, text=str_ink_conc.get(), )

# ent_ink_conc.grid(row=4, column=0, sticky='w')
lbl_recipe_conc.grid(row=4, column=0, sticky='w')
# lbl_conc_mgmL.grid(row=4, column=1, sticky='w')

'''these lists of variable names are to semi-dynamically create the 
proper number of component/unit labels and calculated values for a 
given ink recipe file with open ended, but finite, ie <10, components'''
lbl_comp1 = tk.Label(master=frm_ink_calc, text = '',)
lbl_comp1_value = tk.Label(master=frm_ink_calc, text = '',)
lbl_comp2 = tk.Label(master=frm_ink_calc, text = '',)
lbl_comp2_value = tk.Label(master=frm_ink_calc, text = '',)
lbl_comp3 = tk.Label(master=frm_ink_calc, text = '',)
lbl_comp3_value = tk.Label(master=frm_ink_calc, text = '',)
lbl_comp4 = tk.Label(master=frm_ink_calc, text = '',)
lbl_comp4_value = tk.Label(master=frm_ink_calc, text = '',)
lbl_comp5 = tk.Label(master=frm_ink_calc, text = '',)
lbl_comp5_value = tk.Label(master=frm_ink_calc, text = '',)
lbl_comp6 = tk.Label(master=frm_ink_calc, text = '',)
lbl_comp6_value = tk.Label(master=frm_ink_calc, text = '',)
lbl_comp7 = tk.Label(master=frm_ink_calc, text = '',)
lbl_comp7_value = tk.Label(master=frm_ink_calc, text = '',)
lbl_comp8 = tk.Label(master=frm_ink_calc, text = '',)
lbl_comp8_value = tk.Label(master=frm_ink_calc, text = '',)
lbl_comp9 = tk.Label(master=frm_ink_calc, text = '',)
lbl_comp9_value = tk.Label(master=frm_ink_calc, text = '',)
lbl_comp10 = tk.Label(master=frm_ink_calc, text = '',)
lbl_comp10_value = tk.Label(master=frm_ink_calc, text = '',)

component_unit_lbls = [ lbl_comp1, lbl_comp2, lbl_comp3, lbl_comp4, lbl_comp5,
                        lbl_comp6, lbl_comp7, lbl_comp8, lbl_comp9, lbl_comp10]

component_value_lbls = [lbl_comp1_value, lbl_comp2_value, lbl_comp3_value,
                        lbl_comp4_value, lbl_comp5_value, lbl_comp6_value,
                        lbl_comp7_value, lbl_comp8_value, lbl_comp9_value,
                        lbl_comp10_value]

#%% 4.2: RDE Experimental parameters frame

#--------Experiment Parameters Frame-----------
frm_exp_params = tk.Frame(master=tab_rde, 
                         highlightbackground='blue', highlightthickness=2,
                          bd=0) #width=200, height=200,
# Set up the layout within the window using the .grid() geometry manager
frm_exp_params.grid(row=3, column=0, padx=10, pady=5, sticky='ew')

#--------Add frame title-----------
lbl_exp_params_title = tk.Label(master=frm_exp_params, text='Experiment Parameters', 
                               font='Helvetica 14 bold', fg='darkblue')
lbl_exp_params_title.grid(row=0, column=0, columnspan=5, pady=(0, 10), sticky='n')

# Configure column weights for proper spacing
frm_exp_params.grid_columnconfigure(0, weight=1)
frm_exp_params.grid_columnconfigure(1, weight=1)
frm_exp_params.grid_columnconfigure(2, weight=1)
frm_exp_params.grid_columnconfigure(3, weight=1)
frm_exp_params.grid_columnconfigure(4, weight=1)

#--------Labels (Top Row)-----------
lbl_purpose = tk.Label(master=frm_exp_params, text='Purpose', font='Helvetica 10 bold')
lbl_trial_id = tk.Label(master=frm_exp_params, text='Trial ID', font='Helvetica 10 bold')
lbl_reaction = tk.Label(master=frm_exp_params, text='Reaction', font='Helvetica 10 bold')

lbl_electrolyte = tk.Label(master=frm_exp_params, text='Electrolyte\nComposition', font='Helvetica 10 bold')
lbl_ref_potential = tk.Label(master=frm_exp_params, text='Reference Potential\n(mV vs RHE)', font='Helvetica 10 bold')
lbl_ref_type = tk.Label(master=frm_exp_params, text='Reference Type', font='Helvetica 10 bold')
lbl_exp_type = tk.Label(master=frm_exp_params, text='Experiment Type', font='Helvetica 10 bold')

lbl_impur = tk.Label(master=frm_exp_params, text='Known Impurities \n(ppm)', font='Helvetica 10 bold')
lbl_gas = tk.Label(master=frm_exp_params, text='Gas bubbled / rate \n(mL/min)', font='Helvetica 10 bold')

lbl_rotation = tk.Label(master=frm_exp_params, text='Rotation \n(rpm)', font='Helvetica 10 bold')


#--------Input Fields and Dropdowns (Bottom Row)-----------
# Purpose entry
str_purpose = tk.StringVar()
str_purpose.set('')
ent_purpose = tk.Entry(master=frm_exp_params, textvariable=str_purpose, width=25)

# Trial ID Entry
str_trial_id = tk.StringVar()
str_trial_id.set('')
ent_trial_id = tk.Entry(master=frm_exp_params, textvariable=str_trial_id, width=15)
# ent_trial_id.grid(row=1, column=0, padx=5, pady=5, sticky='ew')

# Reaction Entry
str_reaction = tk.StringVar()
str_reaction.set('')
ent_reaction = tk.Entry(master=frm_exp_params, textvariable=str_reaction, width=15)
# ent_reaction.grid(row=1, column=0, padx=5, pady=5, sticky='ew')

# Electrolyte Concentration and Composition Entry
frm_electrolyte = tk.Frame(master=frm_exp_params)
str_electrolyte_conc = tk.StringVar()
str_electrolyte_conc.set('')
ent_electrolyte_conc = tk.Entry(master=frm_electrolyte, textvariable=str_electrolyte_conc, width=5)
ent_electrolyte_conc.grid(row=0, column=0, padx=5, pady=2, sticky='ew')

molar_options = ['M', 'mM','uM']
str_molar = tk.StringVar()
str_molar.set('M')
drop_conc_M = tk.OptionMenu(frm_electrolyte, str_molar, *molar_options)
drop_conc_M.grid(row=0, column=1, padx=5, pady=2, sticky='ew')

str_electrolyte_chem = tk.StringVar()
str_electrolyte_chem.set('')
ent_electrolyte_chem = tk.Entry(master=frm_electrolyte, textvariable=str_electrolyte_chem, width=10)
ent_electrolyte_chem.grid(row=0, column=2, padx=5, pady=2, sticky='ew')

str_impurity = tk.StringVar()
str_impurity.set('')
ent_impurity = tk.Entry(master=frm_exp_params, textvariable=str_impurity, width=20)



# Reference Potential Entry
str_ref_potential = tk.StringVar()
str_ref_potential.set('')
ent_ref_potential = tk.Entry(master=frm_exp_params, textvariable=str_ref_potential, width=10)


# Reference Type Dropdown
ref_type_options = ['Hg|HgO', 'Ag|AgCl', 'Hg|Hg2Cl2', 'Hg|HgSO4', 'Pt|H2', 'PdHx']
clicked_ref_type = tk.StringVar()
clicked_ref_type.set('Hg|HgO')  # Default selection
drop_ref_type = tk.OptionMenu(frm_exp_params, clicked_ref_type, *ref_type_options)
drop_ref_type.config(width=10)


# Experiment Type Dropdown
exp_type_options = ['test', 'Activation', 'Tafel', 'Cdl CV', 'Stability', 
                    'EIS', 'Mott-Schotky', 'user input']
clicked_exp_type = tk.StringVar()
clicked_exp_type.set('test')  # Default selection
drop_exp_type = tk.OptionMenu(frm_exp_params, clicked_exp_type, *exp_type_options,
                             command=toggle_exp_type_entry)
drop_exp_type.config(width=12)


# Create the conditional user input entry (initially hidden)
str_user_exp_type = tk.StringVar()
str_user_exp_type.set('')
ent_user_exp_type = tk.Entry(master=frm_exp_params, textvariable=str_user_exp_type, 
                            width=15, font='Helvetica 10')

# Rotation speed Entry
str_rotation = tk.StringVar()
str_rotation.set('')
ent_rotation = tk.Entry(master=frm_exp_params, textvariable=str_rotation, width=5)


# Bubbled gas Entry
str_gas = tk.StringVar()
str_gas.set('')
ent_gas = tk.Entry(master=frm_exp_params, textvariable=str_gas, width=10)

# frame for cell settings
frm_wececell = tk.Frame(master=frm_exp_params)

# Allow all 5 columns inside the subframe to expand equally
for col in range(5):
    frm_wececell.columnconfigure(col, weight=1)

lbl_area = tk.Label(master=frm_wececell, text='Working area \n(cm2)', font='Helvetica 10 bold')
lbl_electrode = tk.Label(master=frm_wececell, text='Working type', font='Helvetica 10 bold')
lbl_counter = tk.Label(master=frm_wececell, text='Counter', font='Helvetica 10 bold')
lbl_cell_type = tk.Label(master=frm_wececell, text='Cell Configuration', font='Helvetica 10 bold')

# Working Electrode area
str_area = tk.StringVar()
str_area.set('')
ent_area = tk.Entry(master=frm_wececell, textvariable=str_area, width=10)

# Working Electrode Type Dropdown
elctrd_options = ['GC/RDE', 'Au/RDE', 'Pt(poly)/RDE', 'Pt(sc)/RDE', 'GC/RRDE', 'Au/RRDE', 'Pt(poly)/RRDE', 'Pt(sc)/RRDE']
clicked_elctrd_type = tk.StringVar()
clicked_elctrd_type.set('GC/RDE')  # Default selection
drop_elctrd_type = tk.OptionMenu(frm_wececell, clicked_elctrd_type, *elctrd_options)
drop_elctrd_type.config(width=10)

# Counter Electrode Type Dropdown
counter_elctrd_options = ['GC', 'Au', 'Pt on C','Pt(poly)', 'Pt(sc)', 'graphite', 'C black pearl', 'Ag']
clicked_counter_elctrd_type = tk.StringVar()
clicked_counter_elctrd_type.set('Au')  # Default selection
drop_counter_elctrd_type = tk.OptionMenu(frm_wececell, clicked_counter_elctrd_type, *counter_elctrd_options)
drop_counter_elctrd_type.config(width=10)

# Cell Type Dropdowns
cell_options = ['4 electrode', '3 electrode', '2 electrode']
clicked_cell_type = tk.StringVar()
clicked_cell_type.set('3 electrode')  # Default selection
drop_cell_type = tk.OptionMenu(frm_wececell, clicked_cell_type, *cell_options)
drop_cell_type.config(width=10)


cell_mat_options = ['FEP', 'PTFE', 'PEEK', 'glass']
clicked_cell_mat_type = tk.StringVar()
clicked_cell_mat_type.set('FEP')  # Default selection
drop_cell_mat_type = tk.OptionMenu(frm_wececell, clicked_cell_mat_type, *cell_mat_options)
drop_cell_mat_type.config(width=10)

lbl_area.grid(row=0, column=0, padx=5, pady=5, sticky='ew')
lbl_electrode.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
lbl_counter.grid(row=0, column=2, padx=5, pady=5, sticky='ew')
lbl_cell_type.grid(row=0, column=3, columnspan=2, padx=5, pady=5, sticky='ew')

ent_area.grid(row=1, column=0, padx=5, pady=5, sticky='ew')
drop_elctrd_type.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
drop_counter_elctrd_type.grid(row=1, column=2, padx=5, pady=5, sticky='ew')
drop_cell_type.grid(row=1, column=3, padx=5, pady=5, sticky='ew')
drop_cell_mat_type.grid(row=1, column=4, padx=5, pady=5, sticky='ew')

#--------RHE conversion button and results frame creation and placement-----------
frm_RHE = tk.LabelFrame(master=tab_rde, text='Potentials', font='Helvetica 14 bold',
                        fg='darkblue')
frm_RHE.grid(row=0,column=1, rowspan=5)

frm_refrange = tk.Frame(master=frm_exp_params)
lbl_refrange = tk.Label(master=frm_exp_params, text='Low, high, step \n(V vs. RHE)', font='Helvetica 10 bold')
lbl_ref_to = tk.Label(master=frm_refrange, text='to', font='Helvetica 10')
lbl_ref_every = tk.Label(master=frm_refrange, text='every', font='Helvetica 10')
lbl_ref_V = tk.Label(master=frm_refrange, text='V', font='Helvetica 10')

str_ref_low = tk.StringVar()
str_ref_low.set('')
str_ref_high = tk.StringVar()
str_ref_high.set('')
str_ref_step = tk.StringVar()
str_ref_step.set('')
ent_ref_low = tk.Entry(master=frm_refrange , textvariable=str_ref_low, width=5)
ent_ref_high= tk.Entry(master=frm_refrange , textvariable=str_ref_high, width=5)
ent_ref_step = tk.Entry(master=frm_refrange , textvariable=str_ref_step, width=5)
ent_ref_low.grid(row=0,column=0, )
lbl_ref_to .grid(row=0,column=1, )
ent_ref_high.grid(row=0,column=2, )
lbl_ref_every.grid(row=0,column=3, )
ent_ref_step.grid(row=0,column=4,)
lbl_ref_V.grid(row=0,column=5, )

# Create the conversion button
convert_button = ttk.Button(frm_exp_params, text="Convert Ewe/Ref/RHE", 
                           command=lambda: convert_to_rhe(
                               str_ref_potential, 
                               str_ref_low, 
                               str_ref_high, 
                               str_ref_step,
                               frm_RHE
                               )
                           )




# Notes Entry
lbl_notes = tk.Label(master=frm_exp_params, text='Notes', font='Helvetica 10 bold')
str_notes = tk.StringVar()
str_notes.set('')
ent_notes = tk.Text(master=frm_exp_params , height=4,  font='Helvetica 10')#, textvariable=str_notes, )

# Linked Files Entry
lbl_Links = tk.Label(master=frm_exp_params, text='Linked files', font='Helvetica 10 bold')
str_Links = tk.StringVar()
str_Links.set('')
ent_Links = tk.Entry(master=frm_exp_params, textvariable=str_Links, )



# Grid labels and entries 
lbl_purpose.grid(row=1, column=0, padx=5, pady=5, sticky='ew')
ent_purpose.grid(row=1, column=1, columnspan=3, padx=5, pady=5, sticky='ew')

lbl_trial_id.grid(row=2, column=1, padx=5, pady=5, sticky='n') #
lbl_reaction.grid(row=2, column=0, padx=5, pady=5, sticky='n')
lbl_exp_type.grid(row=2, column=2, padx=5, pady=5, sticky='n')

ent_trial_id.grid(row=3, column=1, padx=5, pady=5, sticky='ew')
ent_reaction.grid(row=3, column=0, padx=5, pady=5, sticky='ew')
drop_exp_type.grid(row=3, column=2, padx=5, pady=5, sticky='ew')

## Electrolyte and ref potential
lbl_electrolyte.grid(row=4, column=0, padx=5, pady=5, sticky='n')
lbl_impur.grid(row=4, column=1, padx=5, pady=5, sticky='n')
lbl_gas.grid(row=4, column=2, padx=5, pady=5, sticky='n')
lbl_rotation.grid(row=4, column=3, padx=5, pady=5, sticky='n')

frm_electrolyte.grid(row=5, column=0,  padx=5, pady=5, sticky='ew')
ent_gas.grid(row=5, column=2,  padx=5, pady=5, sticky='ew')
ent_impurity.grid(row=5, column=1,  padx=5, pady=5, sticky='ew')
ent_rotation.grid(row=5, column=3,  padx=5, pady=5, sticky='ew')



## Cell configuretion
frm_wececell.grid(row=6, column=0, columnspan=6, padx=5, pady=5, sticky='ew')

lbl_ref_potential.grid(row=8, column=0, padx=5, pady=5, sticky='n')
lbl_ref_type.grid(row=8, column=1, padx=5, pady=5, sticky='n')
lbl_refrange.grid(row=8, column=2, padx=5, pady=5, sticky='n')

ent_ref_potential.grid(row=9, column=0, padx=5, pady=5, sticky='ew')
drop_ref_type.grid(row=9, column=1, padx=5, pady=5, sticky='ew')
frm_refrange.grid(row=9, column=2, padx=5, pady=5, sticky='ew')
convert_button.grid(row=9, column=3,   padx=5, pady=5, sticky='ew') #,

## Notes and linked files
lbl_notes.grid(row=10, column=0, padx=5, pady=5, sticky='n')
ent_notes.grid(row=10, column=1, columnspan=3,  padx=5, pady=5, sticky='ew') #rowspan=2,


lbl_Links.grid(row=11, column=0, padx=5, pady=5, sticky='n')
ent_Links.grid(row=11, column=1, columnspan=4, padx=5, pady=5, sticky='ew')



#%% 4.3: RDE File naming and saving frame

#--------Filename Frame-----------
frm_filename = tk.Frame(master=tab_rde, 
                       highlightbackground='blue', highlightthickness=2,
                        bd=0) #width=200, height=100,
frm_filename.grid(row=4, column=0, padx=10, pady=5, sticky='ew')

# Configure column weights for proper spacing
frm_filename.grid_columnconfigure(0, weight=0)
frm_filename.grid_columnconfigure(1, weight=1)
frm_filename.grid_columnconfigure(2, weight=0)

#--------Frame Title-----------
lbl_filename_title = tk.Label(master=frm_filename, text='File Naming and Saving', 
                             font='Helvetica 14 bold', fg='darkblue')
lbl_filename_title.grid(row=0, column=0, columnspan=4, pady=(5, 10), sticky='n')

#--------Filename Toggle Options-----------
filename_mode = tk.StringVar()
filename_mode.set('standardized')  # Default selection

# Radio buttons for filename mode selection
rb_standardized = tk.Radiobutton(master=frm_filename, text='Standardized', 
                                variable=filename_mode, value='standardized',
                                command=lambda: toggle_filename_mode(),
                                font='Helvetica 10 bold')

rb_user_input = tk.Radiobutton(master=frm_filename, text='User Input', 
                              variable=filename_mode, value='user_input',
                              command=lambda: toggle_filename_mode(),
                              font='Helvetica 10 bold')

frm_creator = tk.Frame(master=frm_filename)

# Author/scientist/creator entry
lbl_author = tk.Label(master=frm_creator, text='Scientist:', 
                      font='Helvetica 10 bold')
str_author = tk.StringVar()
ent_author = tk.Entry(master=frm_creator, 
                      textvariable=str_author,font='Helvetica 10' )

lbl_filetype = tk.Label(master=frm_creator, text='File type:', 
                      font='Helvetica 10 bold')
filetype_options = ['yaml', 'json']
clicked_filetype = tk.StringVar()
clicked_filetype.set('yaml')  # Default selection
drop_filetype = tk.OptionMenu(frm_creator, clicked_filetype, *filetype_options)
drop_filetype.config(width=10)

#intra fram positioning
lbl_author.grid(row=0, column=0, padx=10, pady=5, sticky='w')
ent_author.grid(row=0, column=1, padx=10, pady=5, sticky='w')
lbl_filetype.grid(row=0, column=2, padx=10, pady=5, sticky='e')
drop_filetype.grid(row=0, column=3, padx=10, pady=5, sticky='e')

rb_standardized.grid(row=1, column=0, padx=10, pady=5, sticky='w')
rb_user_input.grid(row=1, column=1, padx=10, pady=5, sticky='w')
frm_creator.grid(row=1, column=2, columnspan=2, padx=10, pady=5, sticky='e')



#--------Filename Display/Entry Area-----------
# Label for filename display

# lbl_filename_display = tk.Label(master=frm_filename, text='Generated Filename:', 
#                                font='Helvetica 10 bold')
# lbl_filename_display.grid(row=2, column=0, padx=10, pady=(10, 5), sticky='w')

# StringVar for user input filename
str_user_filename = tk.StringVar()
str_user_filename.set('')

# Entry for user input (initially hidden)
ent_user_filename = tk.Entry(master=frm_filename, textvariable=str_user_filename, 
                            width=60, font='Helvetica 10')

# Label for displaying standardized filename (initially visible)
str_generated_filename = tk.StringVar()
str_generated_filename.set('Please fill in experiment parameters before generating a filename.')
lbl_generated_filename = tk.Label(master=frm_filename, textvariable=str_generated_filename,
                                 width=60, relief='sunken', bd=1, bg='lightgray',
                                 font='Helvetica 10', anchor='w')

# Initially show the generated filename label
lbl_generated_filename.grid(row=3, column=0, columnspan=4, padx=10, pady=5, sticky='ew')

#--------Update Filename Button-----------
btn_update_filename = tk.Button(master=frm_filename, text='Update Filename', 
                               command=lambda: generate_standardized_filename(),
                               bg='lightblue', font='Helvetica 10 bold')

#--------Copy Filename Button-----------
btn_copy = tk.Button(master=frm_filename, text='Copy Filename', 
                    command=copy_filename_to_clipboard_silent,
                    bg='lightblue', fg='darkblue', 
                    font='Helvetica 10 bold',
                    relief='raised', borderwidth=2)

btn_save_yaml = tk.Button(master=frm_filename, text='Save metadata file!', 
                         command=lambda: save_metadata_with_validation(clicked_filetype.get()),
                         bg='lightgreen', fg='darkgreen',
                         font='Helvetica 12 bold',
                         relief='raised', borderwidth=2)


# ──────────────────────────────────────────────────────────────────────────────
# RDE Master Log Buttons
# ──────────────────────────────────────────────────────────────────────────────

btn_rde_setup_log = tk.Button(
    master=frm_filename,
    text='Setup Log Session',
    command=rde_setup_log,
    bg='lightyellow', fg='darkblue',
    font='Helvetica 10 bold',
    relief='raised', borderwidth=2,
)

btn_rde_append_log = tk.Button(
    master=frm_filename,
    text='Append Metadata to Master Log',
    command=rde_append_to_master_log,
    bg='lightyellow', fg='darkblue',
    font='Helvetica 10 bold',
    relief='raised', borderwidth=2,
    state='disabled',
)

btn_rde_clear_log = tk.Button(
    master=frm_filename,
    text='Clear/Change Log Session',
    command=rde_clear_log_session,
    bg='lightyellow', fg='darkred',
    font='Helvetica 10 bold',
    relief='raised', borderwidth=2,
    state='disabled',
)

# Save/log button placements
btn_update_filename.grid(row=4, column=0, columnspan=2, pady=5, padx=10, sticky='ew')
btn_copy.grid(row=4, column=3,  pady=5, padx=10, sticky='ew')#columnspan=2,
btn_save_yaml.grid(row=5, column=0, columnspan=4, pady=5, padx=10, sticky='ew')

btn_rde_setup_log.grid(row=6, column=0, columnspan=1, pady=5, padx=10, sticky='ew')
btn_rde_append_log.grid(row=6, column=1, columnspan=2, pady=5, padx=10, sticky='ew')
btn_rde_clear_log.grid(row=6, column=3, columnspan=1, pady=5, padx=10, sticky='ew')



# lbl_fc = tk.Label(master=tab_flowcell, text='Flow cell', 
#                                font='Helvetica 14 bold')
# lbl_fc.grid(row=0, column=0, padx=10, sticky='w')

frm_fc_expchoice = tk.Frame(master=tab_flowcell, highlightbackground='blue', highlightthickness=2,
                        bd=0) #width=200, height=100,
frm_fc_expchoice.grid(row=2, column=0, padx=10, pady=5, sticky='ew')

## defining beamtime frame + options
frm_fc_beamtimechoice = tk.Frame(master=tab_flowcell, highlightbackground='blue', highlightthickness=2,
                        bd=0)

fc_mode = tk.StringVar()
fc_mode.set('lab')


# Beamtime selection variable for radio buttons
beamtime_selection = tk.StringVar()
beamtime_selection.set('XAS')



#### Defining contents of beamtime adaptive frames

radio_frame = tk.Frame(frm_fc_beamtimechoice)

rb_xas = tk.Radiobutton(radio_frame, text="XAS", 
                       variable=beamtime_selection, value="XAS",
                       command=on_beamtime_selection_change,
                       font='Helvetica 10 bold')

rb_xrd = tk.Radiobutton(radio_frame, text="XRD", 
                        variable=beamtime_selection, value="XRD",
                        command=on_beamtime_selection_change,
                        font='Helvetica 10 bold')
 
rb_combined = tk.Radiobutton(radio_frame, text="XAS + XRD", 
                            variable=beamtime_selection, value="XAS + XRD",
                            command=on_beamtime_selection_change,
                            font='Helvetica 10 bold')





#-------- Beamline frame -----------
# beamline and optics entries to be packed by setup_beamtime_frames
frm_fc_beamline = tk.Frame(master=frm_fc_beamtimechoice )
lbl_fc_beamline = tk.Label(master=frm_fc_beamline, text="Beamline", 
                                   font='Helvetica 10 bold')
str_fc_beamline = tk.StringVar()
str_fc_beamline.set('')
ent_fc_beamline = tk.Entry(master=frm_fc_beamline, textvariable=str_fc_beamline, 
                        )

lbl_fc_optics = tk.Label(master=frm_fc_beamline, text="Optics", 
                                   font='Helvetica 10 bold')
str_fc_optics = tk.StringVar()
str_fc_optics.set('')
ent_fc_optics = tk.Entry(master=frm_fc_beamline, textvariable=str_fc_optics, 
                        )
lbl_fc_mono = tk.Label(master=frm_fc_beamline, text="Monochromator", 
                                   font='Helvetica 10 bold')
str_fc_mono = tk.StringVar()
str_fc_mono.set('')
ent_fc_mono = tk.Entry(master=frm_fc_beamline, textvariable=str_fc_mono, 
                        )

lbl_fc_filter = tk.Label(master=frm_fc_beamline, text="Filter", 
                                   font='Helvetica 10 bold')
str_fc_filter = tk.StringVar()
str_fc_filter.set('')
ent_fc_filter = tk.Entry(master=frm_fc_beamline, textvariable=str_fc_filter, )

lbl_fc_I0 = tk.Label(master=frm_fc_beamline, text="Io/flux", 
                                   font='Helvetica 10 bold')
str_fc_I0 = tk.StringVar()
str_fc_I0.set('')
ent_fc_I0 = tk.Entry(master=frm_fc_beamline, textvariable=str_fc_I0, )

lbl_fc_beamspot = tk.Label(master=frm_fc_beamline, text="Beamspot dimensions", 
                                   font='Helvetica 10 bold')
str_fc_beamspot = tk.StringVar()
str_fc_beamspot.set('')
ent_fc_beamspot = tk.Entry(master=frm_fc_beamline, textvariable=str_fc_beamspot, )


lbl_fc_beamline_expid = tk.Label(master=frm_fc_beamline, text="Beamtime Exp. ID", 
                                   font='Helvetica 10 bold')
str_fc_beamline_expid = tk.StringVar()
str_fc_beamline_expid.set('')
ent_fc_beamline_expid = tk.Entry(master=frm_fc_beamline, textvariable=str_fc_beamline_expid, )


#placing common beamline entries
lbl_fc_beamline.grid(row=0, column=0, padx=5, pady=2, sticky='w')
ent_fc_beamline.grid(row=0, column=1, padx=5, pady=2, sticky='w')
lbl_fc_optics.grid(row=1, column=0, padx=5, pady=2, sticky='w')
ent_fc_optics.grid(row=1, column=1, padx=5, pady=2, sticky='w')
lbl_fc_mono.grid(row=2, column=0, padx=5, pady=2, sticky='w')
ent_fc_mono.grid(row=2, column=1, padx=5, pady=2, sticky='w')
lbl_fc_filter.grid(row=3, column=0, padx=5, pady=2, sticky='w')
ent_fc_filter.grid(row=3, column=1, padx=5, pady=2, sticky='w')
lbl_fc_I0.grid(row=4, column=0, padx=5, pady=2, sticky='w')
ent_fc_I0.grid(row=4, column=1, padx=5, pady=2, sticky='w')
lbl_fc_beamspot.grid(row=5, column=0, padx=5, pady=2, sticky='w')
ent_fc_beamspot.grid(row=5, column=1, padx=5, pady=2, sticky='w')
lbl_fc_beamline_expid.grid(row=6, column=0, padx=5, pady=2, sticky='w')
ent_fc_beamline_expid.grid(row=6, column=1, padx=5, pady=2, sticky='w')

# Create the three beamtime settings frames
xas_beamtime_frame = tk.LabelFrame(frm_fc_beamtimechoice, text="XAS Beamtime Setup", 
                                   font='Helvetica 10 bold', fg='darkblue')
xrd_beamtime_frame = tk.LabelFrame(frm_fc_beamtimechoice, text="XRD Beamtime Setup", 
                                   font='Helvetica 10 bold', fg='darkblue')
combined_beamtime_frame = tk.LabelFrame(frm_fc_beamtimechoice, text="XAS + XRD Beamtime Setup", 
                                       font='Helvetica 10 bold', fg='darkblue')

#-------- XAS Beamline settings -----------
frm_fc_energyrange = tk.Frame(xas_beamtime_frame)
lbl_fc_energyrange = tk.Label(frm_fc_energyrange, text="Energy range", 
        font='Helvetica 10 bold', justify='left')

str_fc_enrgymin = tk.StringVar()
str_fc_enrgymin.set('')
str_fc_enrgymax = tk.StringVar()
str_fc_enrgymax.set('')
lbl_to = tk.Label(frm_fc_energyrange, text='to', font='Helvetica 10')
lbl_eV = tk.Label(frm_fc_energyrange, text='eV', font='Helvetica 10')
ent_fc_energymin = tk.Entry(frm_fc_energyrange, textvariable=str_fc_enrgymin,
                            width=10)
ent_fc_energymax = tk.Entry(frm_fc_energyrange, textvariable=str_fc_enrgymax, 
                            width=10)

lbl_fc_steps = tk.Label(xas_beamtime_frame, text='Step size (eV)',
                        font='Helvetica 10 bold')
str_fc_steps = tk.StringVar()
str_fc_steps.set('')
ent_fc_steps = tk.Entry(xas_beamtime_frame, textvariable=str_fc_steps, )

lbl_fc_freq = tk.Label(xas_beamtime_frame, text='Time/spectra (s)',
                        font='Helvetica 10 bold')
str_fc_freq = tk.StringVar()
str_fc_freq.set('')
ent_fc_freq = tk.Entry(xas_beamtime_frame, textvariable=str_fc_freq, )

lbl_fc_detector1 = tk.Label(xas_beamtime_frame, text='Detector',
                        font='Helvetica 10 bold')
str_fc_detector1 = tk.StringVar()
str_fc_detector1.set('')
ent_fc_detector1= tk.Entry(xas_beamtime_frame, textvariable=str_fc_detector1, )

lbl_fc_detectmode = tk.Label(xas_beamtime_frame, text='Mode',
                        font='Helvetica 10 bold')
str_fc_detectmode = tk.StringVar()
str_fc_detectmode.set('fluorescence')
detectmode_options = ['fluorescence', 'transmission']
drop_fc_detector1= tk.OptionMenu(xas_beamtime_frame, str_fc_detectmode, *detectmode_options )

# energy range frame
lbl_fc_energyrange.grid(row=0, column=0,columnspan=4, padx=5, pady=2, sticky='w')
ent_fc_energymin.grid(row=1, column=0, padx=5, pady=2, sticky='w')
lbl_to.grid(row=1, column=1, padx=5, pady=2, sticky='w')
ent_fc_energymax.grid(row=1, column=2, padx=5, pady=2, sticky='w')
lbl_eV.grid(row=1, column=3, padx=5, pady=2, sticky='w')

# xas frame placement
frm_fc_energyrange.grid(row=0, column=0, columnspan=5, padx=5, pady=2, sticky='w')
lbl_fc_steps.grid(row=1, column=0, padx=5, pady=2, sticky='w')
ent_fc_steps.grid(row=1, column=1, padx=5, pady=2, sticky='w')
lbl_fc_freq.grid(row=2, column=0, padx=5, pady=2, sticky='w')
ent_fc_freq.grid(row=2, column=1, padx=5, pady=2, sticky='w')
lbl_fc_detector1.grid(row=3, column=0, padx=5, pady=2, sticky='w')
ent_fc_detector1.grid(row=3, column=1, padx=5, pady=2, sticky='w')
lbl_fc_detectmode.grid(row=4, column=0, padx=5, pady=2, sticky='w')
drop_fc_detector1.grid(row=4, column=1, padx=5, pady=2, sticky='w')

#-------- XRD Beamline settings -----------

# --- Photon energy/wavelength widgets ---
lbl_fc_photon = tk.Label(xrd_beamtime_frame, text='Photon', font='Helvetica 10 bold')

fc_photon_options = ['Energy (eV)', 'Wavelength (ang)']
fc_clicked_photon = tk.StringVar()
fc_clicked_photon.set('Energy (eV)')
fc_drop_photon_type = tk.OptionMenu(xrd_beamtime_frame, fc_clicked_photon, *fc_photon_options)

int_fc_photoninput = tk.StringVar()          
int_fc_photoninput.set('')              
ent_fc_photoninput = tk.Entry(xrd_beamtime_frame, textvariable=int_fc_photoninput)

str_fc_photonoutput = tk.StringVar()      
str_fc_photonoutput.set('')

fc_photon_button = ttk.Button(
    xrd_beamtime_frame, text="Convert",
    command=lambda: photon_converter(
        fc_clicked_photon.get(),
        int_fc_photoninput.get(),
        str_fc_photonoutput         # BUG 1 FIX: pass the StringVar, not the Label
    )
)

lbl_fc_photonoutput = tk.Label(xrd_beamtime_frame, textvariable=str_fc_photonoutput, width=20)

# Grid layout (unchanged)
lbl_fc_photon.grid(row=0, column=0, columnspan=4, padx=5, pady=2, sticky='ew')
fc_drop_photon_type.grid(row=1, column=0, padx=5, pady=2, sticky='w')
ent_fc_photoninput.grid(row=1, column=1, padx=5, pady=2, sticky='w')
fc_photon_button.grid(row=2, column=0, padx=5, pady=2, sticky='w')
lbl_fc_photonoutput.grid(row=2, column=1, padx=5, pady=2, sticky='w')

# 2theta range, like erange
frm_fc_2Thetarange = tk.Frame(xrd_beamtime_frame)
lbl_fc_2Thetarange = tk.Label(frm_fc_2Thetarange, text="2theta range", 
        font='Helvetica 10 bold', justify='left')

str_fc_2thetamin = tk.StringVar()
str_fc_2thetamin.set('')
str_fc_2thetamax = tk.StringVar()
str_fc_2thetamax.set('')
lbl_to_2theta = tk.Label(frm_fc_2Thetarange, text='to', font='Helvetica 10') 
lbl_deg = tk.Label(frm_fc_2Thetarange, text='deg', font='Helvetica 10')
ent_fc_2thetamin = tk.Entry(frm_fc_2Thetarange, textvariable=str_fc_2thetamin,
                            width=10)
ent_fc_2thetamax = tk.Entry(frm_fc_2Thetarange, textvariable=str_fc_2thetamax, 
                            width=10)

lbl_fc_2Thetarange.grid(row=0, column=0,columnspan=4, padx=5, pady=2, sticky='ew')
ent_fc_2thetamin.grid(row=1, column=0, padx=5, pady=2, sticky='w')
lbl_to_2theta.grid(row=1, column=1, padx=5, pady=2, sticky='w')
ent_fc_2thetamax.grid(row=1, column=2, padx=5, pady=2, sticky='w')
lbl_deg.grid(row=1, column=3, padx=5, pady=2, sticky='w')

frm_fc_2Thetarange.grid(row=3, column=0, columnspan=4, padx=5, pady=2, sticky='w')

#Detector rows
lbl_fc_detector2 = tk.Label(xrd_beamtime_frame, text='Detector',
                        font='Helvetica 10 bold')
str_fc_detector2 = tk.StringVar()
str_fc_detector2.set('')
ent_fc_detector2= tk.Entry(xrd_beamtime_frame, textvariable=str_fc_detector2, )

lbl_fc_detector2dist = tk.Label(xrd_beamtime_frame, text='Distance (mm)',
                        font='Helvetica 10 bold')
str_fc_detector2dist = tk.StringVar()
str_fc_detector2dist.set('')
ent_fc_detector2dist = tk.Entry(xrd_beamtime_frame, textvariable=str_fc_detector2dist, )

lbl_fc_detectmode2 = tk.Label(xrd_beamtime_frame, text='Mode',
                        font='Helvetica 10 bold')
str_fc_xrddetectmode = tk.StringVar()
str_fc_xrddetectmode.set('Bragg-Brentano')
xrd_detectmode_options = ['Bragg-Brentano', 'Debye-Scherrer',]
drop_fc_detector2= tk.OptionMenu(xrd_beamtime_frame, str_fc_xrddetectmode, *xrd_detectmode_options )

lbl_fc_detector2.grid(row=4, column=0, padx=5, pady=2, sticky='w')
ent_fc_detector2.grid(row=4, column=1, padx=5, pady=2, sticky='w')
lbl_fc_detector2dist.grid(row=5, column=0, padx=5, pady=2, sticky='w')
ent_fc_detector2dist.grid(row=5, column=1, padx=5, pady=2, sticky='w')

lbl_fc_detectmode2.grid(row=6, column=0, padx=5, pady=2, sticky='w')
drop_fc_detector2.grid(row=6, column=1, padx=5, pady=2, sticky='w')


#-------- Beamline notes -----------
frm_beamline_notes = tk.LabelFrame(master=frm_fc_beamtimechoice, text="Beamtime notes", 
        font='Helvetica 10', )
frm_beamline_notes.grid(row=4, column=0, padx=10, pady=5, sticky='w')
beamline_notes = tk.Text(master=frm_beamline_notes, font='Helvetica 10' ,
                         height=6 , width=40)
beamline_notes.grid(row=0, column=0, padx=10, pady=5, sticky='w')

#%% 5.1: Flowcell/beamtime tab population
#--------Logic flow------------------------
lbl_fc_logic = tk.Label(master=tab_flowcell, 
                     text='Logic: 1) Input metadata, 2) update/copy filename, 3) save metadata file, 4) setup/update master log [optional]', 
                    font='Helvetica 12 bold',  )
lbl_fc_logic.grid(row=1, column=0, padx=10, pady=5, sticky='ew')


##vinitial variables to modify with user fuctions
ink_drop_options_fc = ['load recipe book first']


#-------- Mode selection radio buttons-----------
rb_fc_mode_lab = tk.Radiobutton(master=frm_fc_expchoice, text='Lab (pre)tests', 
                                variable=fc_mode, value='lab',
                                command=toggle_fc_mode,
                                font='Helvetica 10 bold')

rb_fc_mode_beamtime = tk.Radiobutton(master=frm_fc_expchoice, text='Beamtime!', 
                                     variable=fc_mode, value='beamtime',
                                     command=toggle_fc_mode,
                                     font='Helvetica 10 bold')

lbl_fc_mode = tk.Label(master=frm_fc_expchoice, text='Experiment type:', 
                               font='Helvetica 10 bold')
lbl_fc_mode.grid(row=1, column=0, padx=10, pady=2, sticky='w')
rb_fc_mode_lab.grid(row=1, column=1, padx=10, pady=2, sticky='w')
rb_fc_mode_beamtime.grid(row=1, column=2, padx=10, pady=2, sticky='w')


#--------FC Electrode Frame-----------
frm_fc_electrode = tk.LabelFrame(master=tab_flowcell, text='Electrode Parameters',
                         highlightbackground='blue', highlightthickness=2,
                          bd=0, font='Helvetica 14 bold',) 

frm_fc_electrode.grid(row=3, column=0, padx=10, pady=5, sticky='ew')

#--------Ink used sub Frame-----------
frm_fc_ink = tk.Frame(master=frm_fc_electrode)
#place frame with ink choice menu into electrode frame
frm_fc_ink.grid(row=0, column=0, columnspan=8, padx=5, pady=5)

btn_browse_fc = tk.Button(master=frm_fc_ink, text='Show me the inks!', 
                       font='Helvetica 10 bold',
                       command= lambda:browseInks_flow() )

#Create dropdown menu for ink recipe selection 
clicked_ink_fc = tk.StringVar()
clicked_ink_fc.set('')
lbl_inks_fc = tk.Label(frm_fc_ink, text='Ink used', font='Helvetica 10 bold')
drop_inks_fc = tk.OptionMenu(frm_fc_ink, clicked_ink_fc , *ink_drop_options_fc)

lbl_browser_files_to_open_fc = tk.Label(frm_fc_ink, text='Recipe Book:', font='Helvetica 10 bold')

# intra ink frame placements
btn_browse_fc.grid(row=0, column=0, padx=5, pady=5)
lbl_inks_fc.grid(row=0, column=1, padx=5, pady=5)
drop_inks_fc.grid(row=0, column=2, padx=5, pady=5)
lbl_browser_files_to_open_fc.grid(row=0, column=3, columnspan=4, padx=5, pady=5)

lbl_fc_material_id = tk.Label(master=frm_fc_electrode, text='Material ID', 
                              font='Helvetica 10 bold')
lbl_fc_electrode_id = tk.Label(master=frm_fc_electrode, text='Electrode ID', 
                               font='Helvetica 10 bold')
lbl_fc_electrode_mass = tk.Label(master=frm_fc_electrode, text='WE mass (mg)', 
                               font='Helvetica 10 bold')
lbl_fc_electrode_area = tk.Label(master=frm_fc_electrode, text='WE area (cm2)', 
                               font='Helvetica 10 bold')
lbl_fc_CE_id = tk.Label(master=frm_fc_electrode, text='CE ID', 
                               font='Helvetica 10 bold')
lbl_fc_CE_mass = tk.Label(master=frm_fc_electrode, text='CE mass (mg)', 
                               font='Helvetica 10 bold')
lbl_fc_CE_matr = tk.Label(master=frm_fc_electrode, text='CE material', 
                               font='Helvetica 10 bold')

lbl_fc_material_id.grid(row=2, column=0, padx=5, pady=2, sticky='n')
lbl_fc_electrode_id.grid(row=2, column=1, padx=5, pady=2, sticky='n')
lbl_fc_electrode_mass.grid(row=2, column=2, padx=5, pady=2, sticky='n')
lbl_fc_electrode_area.grid(row=2, column=3, padx=5, pady=2, sticky='n')
lbl_fc_CE_id.grid(row=2, column=4, padx=5, pady=2, sticky='n')
lbl_fc_CE_mass.grid(row=2, column=5, padx=5, pady=2, sticky='n')
lbl_fc_CE_matr.grid(row=2, column=6, padx=5, pady=2, sticky='n')

# Material ID Entry
str_fc_material_id = tk.StringVar()
str_fc_material_id.set('')
ent_fc_material_id = tk.Entry(master=frm_fc_electrode, 
                              textvariable=str_fc_material_id, width=15)

# working electrode ID entry
str_fc_electrode_id = tk.StringVar()
str_fc_electrode_id.set('')
ent_fc_electrode_id = tk.Entry(master=frm_fc_electrode, 
                               textvariable=str_fc_electrode_id, width=15)

# working electrode mass entry
str_fc_electrode_mass = tk.StringVar()
str_fc_electrode_mass.set('')
ent_fc_electrode_mass = tk.Entry(master=frm_fc_electrode, 
                               textvariable=str_fc_electrode_mass, width=15)

# working electrode area entry
str_fc_electrode_area = tk.StringVar()
str_fc_electrode_area.set('') 
ent_fc_electrode_area = tk.Entry(master=frm_fc_electrode, 
                               textvariable=str_fc_electrode_area, width=15)

# counter electrode id entry
str_fc_CE_id = tk.StringVar()
str_fc_CE_id.set('')
ent_fc_CE_id = tk.Entry(master=frm_fc_electrode, 
                               textvariable=str_fc_CE_id, width=15)

# counter electrode mass entry
str_fc_CE_mass = tk.StringVar()
str_fc_CE_mass.set('')
ent_fc_CE_mass = tk.Entry(master=frm_fc_electrode, 
                               textvariable=str_fc_CE_mass, width=15)

# counter elctrode material dropdown
clicked_fc_counter_elctrd_type = tk.StringVar()
clicked_fc_counter_elctrd_type.set('C black pearl')  # Default selection
drop_fc_counter_elctrd_type = tk.OptionMenu(frm_fc_electrode, clicked_fc_counter_elctrd_type, *counter_elctrd_options)
drop_fc_counter_elctrd_type.config(width=10)

ent_fc_material_id.grid(row=3, column=0, padx=5, pady=7, sticky='ew')
ent_fc_electrode_id.grid(row=3, column=1, padx=5, pady=7, sticky='ew')
ent_fc_electrode_mass.grid(row=3, column=2, padx=5, pady=7, sticky='ew')
ent_fc_electrode_area.grid(row=3, column=3, padx=5, pady=7, sticky='ew')
ent_fc_CE_id.grid(row=3, column=4, padx=5, pady=7, sticky='ew')
ent_fc_CE_mass.grid(row=3, column=5, padx=5, pady=7, sticky='ew')
drop_fc_counter_elctrd_type.grid(row=3, column=6, padx=5, pady=7, sticky='ew')

#%% 5.2: FC Experiment parameters frame
frm_fc_exp_params = tk.Frame(master=tab_flowcell, 
                         highlightbackground='blue', highlightthickness=2,
                          bd=0) #width=200, height=200,
# Set up the layout within the window using the .grid() geometry manager
frm_fc_exp_params.grid(row=4, column=0, padx=10, pady=5, sticky='ew')


lbl_fc_exp_params_title = tk.Label(master=frm_fc_exp_params, text='Flowcell and Experiment Parameters', 
                               font='Helvetica 14 bold', fg='darkblue')
lbl_fc_exp_params_title.grid(row=0, column=0, columnspan=5, pady=(0, 10), sticky='n')

# Configure column weights for proper spacing
frm_fc_exp_params.grid_columnconfigure(0, weight=1)
frm_fc_exp_params.grid_columnconfigure(1, weight=1)
frm_fc_exp_params.grid_columnconfigure(2, weight=1)
frm_fc_exp_params.grid_columnconfigure(3, weight=1)
frm_fc_exp_params.grid_columnconfigure(4, weight=1)

#--------Labels (Top Row)-----------
lbl_fc_reaction = tk.Label(master=frm_fc_exp_params, text='Reaction', font='Helvetica 10 bold')
lbl_fc_puropose = tk.Label(master=frm_fc_exp_params, text='Purpose', font='Helvetica 10 bold')
lbl_fc_trial_id = tk.Label(master=frm_fc_exp_params, text='Trial ID', font='Helvetica 10 bold')
lbl_fc_electrolyte = tk.Label(master=frm_fc_exp_params, text='Electrolyte\nComposition', font='Helvetica 10 bold')
lbl_fc_impurities = tk.Label(master=frm_fc_exp_params, text='Known Impurities \n(ppm)', font='Helvetica 10 bold')


lbl_fc_flowrate = tk.Label(master=frm_fc_exp_params, text='Flow rate \n(mL/min)', font='Helvetica 10 bold')
lbl_fc_gasflowrate = tk.Label(master=frm_fc_exp_params, text='Gas flowed / rate \n(mL/min)', font='Helvetica 10 bold')

lbl_fc_exptype = tk.Label(master=frm_fc_exp_params, text='Exp. type', font='Helvetica 10 bold')
lbl_fc_cell_id = tk.Label(master=frm_fc_exp_params, text='Cell ID', font='Helvetica 10 bold')
lbl_fc_cellmat = tk.Label(master=frm_fc_exp_params, text='Cell Material', font='Helvetica 10 bold')

#--------Input Fields and Dropdowns -----------
# Purpose entry
str_fc_purpose = tk.StringVar()
str_fc_purpose.set('')
ent_fc_purpose = tk.Entry(master=frm_fc_exp_params,
                           textvariable=str_fc_purpose, width=15)
# Reaction entry
str_fc_reaction = tk.StringVar()
str_fc_reaction.set('')
ent_fc_reaction = tk.Entry(master=frm_fc_exp_params,
                           textvariable=str_fc_reaction, width=15)
# Trial ID entry
str_fc_trial_id = tk.StringVar()
str_fc_trial_id.set('')
ent_fc_trial_id = tk.Entry(master=frm_fc_exp_params,
                           textvariable=str_fc_trial_id, width=15)

# Cell ID entry
str_fc_cell_id = tk.StringVar()
str_fc_cell_id.set('')
ent_fc_cell_id = tk.Entry(master=frm_fc_exp_params,
                           textvariable=str_fc_cell_id, width=15)

# Experiment Type Dropdown 
fc_clicked_exp_type = tk.StringVar()
fc_clicked_exp_type.set('test')  # Default selection
fc_drop_exp_type = tk.OptionMenu(frm_fc_exp_params, fc_clicked_exp_type, *exp_type_options,
                             command=fc_toggle_exp_type_entry)
fc_drop_exp_type.config(width=12)

# Create the conditional user input entry (initially hidden)
str_fc_user_exp_type = tk.StringVar()
str_fc_user_exp_type.set('')
ent_fc_user_exp_type = tk.Entry(master=frm_fc_exp_params, textvariable=str_fc_user_exp_type, 
                            width=15, font='Helvetica 10')

# cell material entry
fc_cell_mat_options = ['FEP', 'PTFE', 'PEEK', 'glass', 'Ti','steel']
fc_clicked_cell_mat_type = tk.StringVar()
fc_clicked_cell_mat_type.set('PEEK')  # Default selection
fc_drop_cell_mat_type = tk.OptionMenu(frm_fc_exp_params, fc_clicked_cell_mat_type, *fc_cell_mat_options)
fc_drop_cell_mat_type.config(width=10)

# Electrolyte Concentration and Composition Entry frame
frm_fc_electrolyte = tk.Frame(master=frm_fc_exp_params)
str_fc_electrolyte_conc = tk.StringVar()
str_fc_electrolyte_conc.set('')
ent_fc_electrolyte_conc = tk.Entry(master=frm_fc_electrolyte, 
                                   textvariable=str_fc_electrolyte_conc, width=10)
ent_fc_electrolyte_conc.grid(row=0, column=0, padx=5, pady=2, sticky='ew')

lbl_fc_conc_M = tk.Label(master=frm_fc_electrolyte, text='M' )
lbl_fc_conc_M.grid(row=0, column=1, padx=5, pady=2, sticky='ew')

str_fc_electrolyte_chem = tk.StringVar()
str_fc_electrolyte_chem.set('')
ent_fc_electrolyte_chem = tk.Entry(master=frm_fc_electrolyte, 
                                   textvariable=str_fc_electrolyte_chem, width=15)
ent_fc_electrolyte_chem.grid(row=0, column=2, padx=5, pady=2, sticky='ew')

# known impurities entry
str_fc_impurity = tk.StringVar()
str_fc_impurity.set('')
ent_fc_impurity = tk.Entry(master=frm_fc_exp_params, textvariable=str_fc_impurity, width=20)

# flow rate entry
str_fc_flowrate = tk.StringVar()
str_fc_flowrate.set('')
ent_fc_flowrate = tk.Entry(master=frm_fc_exp_params,
                           textvariable=str_fc_flowrate, width=15)

# flowed gas entry
str_fc_gasflowrate = tk.StringVar()
str_fc_gasflowrate.set('')
ent_fc_gasflowrate = tk.Entry(master=frm_fc_exp_params,
                           textvariable=str_fc_gasflowrate, width=15)

# Grid elements
lbl_fc_puropose.grid(row=1, column=0, columnspan=3, padx=5, pady=2, sticky='n')
lbl_fc_reaction.grid(row=1, column=3, padx=5, pady=2, sticky='n')
ent_fc_purpose.grid(row=2, column=0, columnspan=3, padx=5, pady=2, sticky='ew')
ent_fc_reaction.grid(row=2, column=3, padx=5, pady=2, sticky='ew')

lbl_fc_trial_id.grid(row=3, column=0, padx=5, pady=2, sticky='n')
lbl_fc_exptype.grid(row=3, column=1, padx=5, pady=2, sticky='n')
lbl_fc_cell_id.grid(row=3, column=2, padx=5, pady=2, sticky='n')
lbl_fc_cellmat.grid(row=3, column=3, padx=5, pady=2, sticky='n')

ent_fc_trial_id.grid(row=4, column=0, padx=5, pady=2, sticky='ew')
fc_drop_exp_type.grid(row=4, column=1, padx=5, pady=2, sticky='ew')
ent_fc_cell_id.grid(row=4, column=2, padx=5, pady=2, sticky='ew')
fc_drop_cell_mat_type.grid(row=4, column=3, padx=5, pady=2, sticky='ew')

lbl_fc_electrolyte.grid(row=8, column=0, padx=5, pady=2, sticky='n')
lbl_fc_impurities.grid(row=8, column=1, padx=5, pady=2, sticky='n')
lbl_fc_flowrate.grid(row=8, column=2, padx=5, pady=2, sticky='n')
lbl_fc_gasflowrate.grid(row=8, column=3, padx=5, pady=2, sticky='n')

# Grid electrolyte entries

frm_fc_electrolyte.grid(row=9, column=0, padx=5, pady=2, sticky='ew')
ent_fc_impurity.grid(row=9, column=1, padx=15, pady=2, sticky='ew')
ent_fc_flowrate.grid(row=9, column=2, padx=5, pady=2, sticky='ew')
ent_fc_gasflowrate.grid(row=9, column=3, padx=5, pady=2, sticky='ew')



## Cell parameters row
lbl_fc_gasketmembrane = tk.Label(master=frm_fc_exp_params, text='Gasket / Membrane', font='Helvetica 10 bold')
lbl_fc_torque = tk.Label(master=frm_fc_exp_params, text='Sealing Torque (N.m)', font='Helvetica 10 bold')
lbl_fc_electThick = tk.Label(master=frm_fc_exp_params, text='Elect. Thickness (mm)', font='Helvetica 10 bold')

lbl_fc_gasketmembrane.grid(row=6, column=0, columnspan=2, padx=5, pady=2, sticky='ew')
lbl_fc_torque.grid(row=6, column=2, padx=5, pady=2, sticky='ew')
lbl_fc_electThick.grid(row=6, column=3, padx=5, pady=2, sticky='ew')


# flow rate entry
str_fc_gasketmembrane = tk.StringVar()
str_fc_gasketmembrane.set('')
ent_fc_gasketmembrane = tk.Entry(master=frm_fc_exp_params,
                           textvariable=str_fc_gasketmembrane, width=15)
# torque entry
str_fc_torque = tk.StringVar()
str_fc_torque.set('')
ent_fc_torque = tk.Entry(master=frm_fc_exp_params,
                           textvariable=str_fc_torque, width=15)

# electrolyte thickness entry
str_fc_electThick = tk.StringVar()
str_fc_electThick.set('')
ent_fc_electThick = tk.Entry(master=frm_fc_exp_params,
                           textvariable=str_fc_electThick, width=15)


#griding cell parameters row

ent_fc_gasketmembrane.grid(row=7, column=0, columnspan=2, padx=5, pady=2, sticky='ew')
ent_fc_torque.grid(row=7, column=2, padx=5, pady=2, sticky='ew')
ent_fc_electThick.grid(row=7, column=3, padx=5, pady=2, sticky='ew')



#--------Ref. potential row -----------
lbl_fc_ref_potential = tk.Label(master=frm_fc_exp_params, text='Reference Potential(s)', font='Helvetica 10 bold')

frm_fc_refpotential = tk.Frame(master=frm_fc_exp_params)

# Reference Type Dropdown 1
clicked_fc_ref_type1 = tk.StringVar()
clicked_fc_ref_type1.set('Ag|AgCl2')  # Default selection
drop_fc_ref_type1 = tk.OptionMenu(frm_fc_refpotential, clicked_fc_ref_type1, *ref_type_options)
# drop_fc_ref_type1.config(width=10)

# Reference Potential Entry 1
str_fc_ref_potential1 = tk.StringVar()
str_fc_ref_potential1.set('')
ent_fc_ref_potential1 = tk.Entry(master=frm_fc_refpotential, 
                                textvariable=str_fc_ref_potential1, width=10)
# unit label 1
lbl_fc_ref_mV = tk.Label(master=frm_fc_refpotential, text='mV vs.', font='Helvetica 10')

# Reference Type Dropdown 2
clicked_fc_ref_type2 = tk.StringVar()
clicked_fc_ref_type2.set('Hg|HgO')  # Default selection
drop_fc_ref_type2 = tk.OptionMenu(frm_fc_refpotential, clicked_fc_ref_type2, *ref_type_options)
# drop_fc_ref_type2.config(width=10)
# drop_fc_ref_type.grid(row=1, column=3, padx=5, pady=2, sticky='ew')

# Reference Potential Entry 2
str_fc_ref_potential2 = tk.StringVar()
str_fc_ref_potential2.set('')
ent_fc_ref_potential2 = tk.Entry(master=frm_fc_refpotential, 
                                textvariable=str_fc_ref_potential2, width=10)
# unit label 2
lbl_fc_ref_mVrhe = tk.Label(master=frm_fc_refpotential, text='mV vs. RHE', font='Helvetica 10')

#--------RHE conversion button and results frame creation and placement-----------
# to populate with potential values
frm_fc_RHE = tk.LabelFrame(master=tab_flowcell, text='Potentials', font='Helvetica 14 bold',
                        fg='darkblue')
frm_fc_RHE.grid(row=10,column=0, columnspan=2)


frm_fc_refrange = tk.Frame(master=frm_fc_exp_params)
lbl_fc_refrange = tk.Label(master=frm_fc_exp_params, text='Low, high, step \n(V vs. RHE)', font='Helvetica 10 bold')
lbl_fc_ref_to = tk.Label(master=frm_fc_refrange, text='to', font='Helvetica 10')
lbl_fc_ref_every = tk.Label(master=frm_fc_refrange, text='every', font='Helvetica 10')
lbl_fc_ref_V = tk.Label(master=frm_fc_refrange, text='V', font='Helvetica 10')

str_fc_ref_low = tk.StringVar()
str_fc_ref_low.set('')
str_fc_ref_high = tk.StringVar()
str_fc_ref_high.set('')
str_fc_ref_step = tk.StringVar()
str_fc_ref_step.set('')
ent_fc_ref_low = tk.Entry(master=frm_fc_refrange , textvariable=str_fc_ref_low, width=5)
ent_fc_ref_high= tk.Entry(master=frm_fc_refrange , textvariable=str_fc_ref_high, width=5)
ent_fc_ref_step = tk.Entry(master=frm_fc_refrange , textvariable=str_fc_ref_step, width=5)
#intra sub-frame positioning
ent_fc_ref_low.grid(row=0,column=0, )
lbl_fc_ref_to .grid(row=0,column=1, )
ent_fc_ref_high.grid(row=0,column=2, )
lbl_fc_ref_every.grid(row=0,column=3, )
ent_fc_ref_step.grid(row=0,column=4,)
lbl_fc_ref_V.grid(row=0,column=5, )



# Create the button 
fc_convert_button = ttk.Button(frm_fc_exp_params, text="Convert Ewe/Ref/RHE in range", 
                           command=lambda: fc_convert_to_rhe(str_fc_ref_potential1, 
                                                             str_fc_ref_potential2,
                                                             str_fc_ref_low, 
                                                             str_fc_ref_high,
                                                             str_fc_ref_step,
                                                             frm_fc_RHE)
                           )


#intra ref frame position 
drop_fc_ref_type1.grid(row=0, column=0, padx=5, pady=2, sticky='ew')
ent_fc_ref_potential1.grid(row=0, column=1, padx=5, pady=2, sticky='ew')
lbl_fc_ref_mV.grid(row=0, column=2, padx=5, pady=2, sticky='e')
drop_fc_ref_type2.grid(row=0, column=3, padx=5, pady=2, sticky='ew')
ent_fc_ref_potential2.grid(row=0, column=4, padx=5, pady=2, sticky='ew')
lbl_fc_ref_mVrhe.grid(row=0, column=5, padx=5, pady=2, sticky='e')

# # configure ref pot rows
lbl_fc_ref_potential.grid(row=11, column=0,  padx=5, pady=2, sticky='ew') #columnspan=2,
frm_fc_refpotential.grid(row=11, column=1, columnspan=3, padx=5, pady=2, sticky='ew')
lbl_fc_refrange.grid(row=12, column=0,  padx=5, pady=2, sticky='ew')
frm_fc_refrange.grid(row=12, column=1,  padx=5, pady=2, sticky='ew')
fc_convert_button.grid(row=12, column=2, columnspan=2,  padx=5, pady=2, sticky='ew')

# Notes Entry
lbl_fc_notes = tk.Label(master=frm_fc_exp_params, text='Notes', font='Helvetica 10 bold')
str_fc_notes = tk.StringVar()
str_fc_notes.set('')
ent_fc_notes = tk.Text(master=frm_fc_exp_params , height=3,  font='Helvetica 10')

## Linked Files Entry
lbl_fc_Links = tk.Label(master=frm_fc_exp_params, text='Linked files', font='Helvetica 10 bold')
str_fc_Links = tk.StringVar()
str_fc_Links.set('')
ent_fc_Links = tk.Entry(master=frm_fc_exp_params, textvariable=str_Links, )

## 4th row
lbl_fc_notes.grid(row=13, column=0, padx=5, pady=2, sticky='n')
ent_fc_notes.grid(row=13, column=1, columnspan=3, rowspan=3, padx=5, pady=2, sticky='ew')

## 5th row
lbl_fc_Links.grid(row=16, column=0, padx=5, pady=2, sticky='n')
ent_fc_Links.grid(row=16, column=1, columnspan=4, padx=5, pady=2, sticky='ew')


#%% 5.3: FC File naming and saving frame

frm_fc_filename = tk.LabelFrame(master=tab_flowcell, text='File Naming and Saving',
                       font='Helvetica 14 bold', highlightbackground='blue', 
                       highlightthickness=2, bd=0) #width=200, height=100,
frm_fc_filename.grid(row=5, column=0, padx=10, pady=5, sticky='ew')

# Configure column weights for proper spacing
frm_fc_filename.grid_columnconfigure(0, weight=0)
frm_fc_filename.grid_columnconfigure(1, weight=1)
frm_fc_filename.grid_columnconfigure(2, weight=0)


#--------Filename Toggle Options-----------
filename_fc_mode = tk.StringVar()
filename_fc_mode.set('standardized')  # Default selection

# Radio buttons for filename mode selection 
rb_fc_standardized = tk.Radiobutton(master=frm_fc_filename, text='Standardized', 
                                variable=filename_fc_mode, value='standardized',
                                command=lambda: fc_toggle_filename_mode(),
                                font='Helvetica 10 bold')

rb_fc_user_input = tk.Radiobutton(master=frm_fc_filename, text='User Input', 
                              variable=filename_fc_mode, value='user_input',
                              command=lambda: fc_toggle_filename_mode(),
                              font='Helvetica 10 bold')


frm_fc_creator = tk.Frame(master=frm_fc_filename)

# Author/scientist/creator entry
lbl_fc_author = tk.Label(master=frm_fc_creator, text='Scientist:', 
                      font='Helvetica 10 bold')
str_fc_author = tk.StringVar()
ent_fc_author = tk.Entry(master=frm_fc_creator, 
                      textvariable=str_fc_author,font='Helvetica 10' )

lbl_fc_filetype = tk.Label(master=frm_fc_creator, text='File type:', 
                      font='Helvetica 10 bold')
clicked_fc_filetype = tk.StringVar()
clicked_fc_filetype.set('yaml')  # Default selection
drop_fc_filetype = tk.OptionMenu(frm_fc_creator, clicked_fc_filetype, *filetype_options)
drop_fc_filetype.config(width=10)

#intra fram positioning
lbl_fc_author.grid(row=0, column=0, padx=10, pady=2, sticky='w')
ent_fc_author.grid(row=0, column=1, padx=10, pady=2, sticky='w')
lbl_fc_filetype.grid(row=0, column=2, padx=10, pady=2, sticky='e')
drop_fc_filetype.grid(row=0, column=3, padx=10, pady=2, sticky='e')


# filename row positioning
rb_fc_standardized.grid(row=1, column=0, padx=10, pady=2, sticky='w')
rb_fc_user_input.grid(row=1, column=1, padx=10, pady=2, sticky='w')
frm_fc_creator.grid(row=1, column=2, columnspan=2, padx=10, pady=2, sticky='e')


#--------Filename Display/Entry Area-----------
# StringVar for user input filename
str_fc_user_filename = tk.StringVar()
str_fc_user_filename.set('')

# Entry for user input (initially hidden)
ent_fc_user_filename = tk.Entry(master=frm_fc_filename, textvariable=str_fc_user_filename, 
                            width=60, font='Helvetica 10')

# Label for displaying standardized filename (initially visible)
str_fc_generated_filename = tk.StringVar()
str_fc_generated_filename.set('Please fill in experiment parameters before generating a filename.')
lbl_fc_generated_filename = tk.Label(master=frm_fc_filename, textvariable=str_fc_generated_filename,
                                 width=60, relief='sunken', bd=1, bg='lightgray',
                                 font='Helvetica 10', anchor='w')

# Initially show the generated filename label
lbl_fc_generated_filename.grid(row=3, column=0, columnspan=4, padx=10, pady=2, sticky='ew')

#--------Update Filename Button-----------
btn_fc_update_filename = tk.Button(master=frm_fc_filename, text='Update Filename', 
                               command=lambda: fc_generate_standardized_filename(),
                               bg='lightblue', font='Helvetica 10 bold')

#--------Copy Filename Button-----------
btn_fc_copy = tk.Button(master=frm_fc_filename, text='Copy Filename', 
                    command=fc_copy_filename_to_clipboard_silent,
                    bg='lightblue', fg='darkblue', 
                    font='Helvetica 10 bold',
                    relief='raised', borderwidth=2)

btn_fc_save_yaml = tk.Button(master=frm_fc_filename, text='Save Metadata File!', 
                         command=lambda: fc_save_metadata_with_validation(clicked_fc_filetype.get()),
                         bg='lightgreen', fg='darkgreen',
                         font='Helvetica 12 bold',
                         relief='raised', borderwidth=2)


# ──────────────────────────────────────────────────────────────────────────────
# Flowcell Master Log Buttons
# ──────────────────────────────────────────────────────────────────────────────

#BUGS: update master log not correctly updating or validating.

btn_fc_setup_log = tk.Button(
    master=frm_fc_filename,
    text='Setup Log Session',
    command=fc_setup_log,
    bg='lightyellow', fg='darkblue',
    font='Helvetica 10 bold',
    relief='raised', borderwidth=2,
)

btn_fc_append_log = tk.Button(
    master=frm_fc_filename,
    text='Append Metadata to Master Log',
    command=fc_append_to_master_log,
    bg='lightyellow', fg='darkblue',
    font='Helvetica 10 bold',
    relief='raised', borderwidth=2,
    state='disabled',           # disabled until fc_setup_log() succeeds
)

btn_fc_clear_log = tk.Button(
    master=frm_fc_filename,
    text='Clear/Change Log Session',
    command=fc_clear_log_session,
    bg='lightyellow', fg='darkred',
    font='Helvetica 10 bold',
    relief='raised', borderwidth=2,
    state='disabled',           # disabled until a session exists
)


# Button placements
btn_fc_update_filename.grid(row=4, column=0, columnspan=2, pady=5, padx=10, sticky='ew')
btn_fc_copy.grid(row=4, column=3, columnspan=2, pady=5, padx=10, sticky='ew')
btn_fc_save_yaml.grid(row=5, column=0, columnspan=4, pady=5, padx=10, sticky='ew')

btn_fc_setup_log.grid(row=6, column=0, columnspan=1, pady=5, padx=10, sticky='ew')
btn_fc_append_log.grid(row=6, column=1, columnspan=2, pady=5, padx=10, sticky='ew')
btn_fc_clear_log.grid(row=6, column=3, columnspan=1, pady=5, padx=10, sticky='ew')

#%% 6.0: Help tab
lbl_help_title = tk.Label(master=tab_help, text='Confused? Not for long!', 
                               font='Helvetica 14 bold', justify='left',
                               anchor='w')
lbl_help_title.grid(row=0, column=0, padx=10, pady=5, sticky='w')


textA = 'This app was designed for minimal user effort to standardize and consolidate the \nmetadata that we collect around our electrochemistry and beamtime experiments.'
textB = '\n\nThe .yaml or .json file the program produces structures the metadata in an unified, \nmachine-readable format in accordance with the FAIR data principles.'
# textC = ''
textD = 'The main input to each experiment tab is a "recipe book" containing the data unique to each project. \nFor minimal user effort/expertise, the expected recipe book input format is a \ncomma separated values (*.csv) file.'
textE = '\nAs currently coded, the app can accomodate up to 10 component columns in the .csv file.'
textF = '\n\nIn the case of RDE experiments, this recipe book defines different possible \nink formulations and component ratios.'
textG = '\n\nThe .csv file should contain a first row of column headers (with units included!!).' 
textH = '\nFor proper code function, it is essential that the first column is the ink name/id \nand the second column is the concentration (mg/mL).'
textI = '\n\nThe following rows should contain an ink formulation name followed by \nratios of each component to the measured catalyst mass (in mg).'
textJ = '\nThe ratios should be calculated in the units chosen in the header. \nAll inks need to have values for each component/column.'
textJ2 = ' Enter 0 if not applicable for that recipe. \nUse periods for decimals; python was mostly coded by Americans. ' 
textK = '\n\nHere is an RDE recipe book example:\n\n'
textL = 'ink_id,Concentration (mg/mL),Black Pearl C (mg),MQ H20 (mL),IPA (mL),EtOH (mL),Na-exch. Nafion (uL) \nA: RDE,2,0,0.1,0.4,0,1.25 \nB: XPS,2,0.2,0.1,0.4,0,1.5 \nC: flow cell,34,0.5,0.2,0,0.3,5'

text0 = textA + textB 
text1=  textD + textE + textF + textG + textH + textI + textJ  + textJ2 + textK + textL

lbl_help_intro = tk.Label(master=tab_help, text=text0, 
                               font='Helvetica 11',
                               justify='left', anchor='w')
lbl_help_intro.grid(row=1, column=0, padx=10, sticky='w')

lbl_help_inks = tk.Label(master=tab_help, text='Inks/Recipe Books', 
                               font='Helvetica 12 bold',
                               justify='left', anchor='w')
lbl_help_inks.grid(row=2, column=0, padx=10,pady=5,  sticky='w')

lbl_help_ink_guts = tk.Label(master=tab_help, text=text1, 
                               font='Helvetica 11',
                               justify='left', anchor='w')
lbl_help_ink_guts.grid(row=3, column=0, padx=10, sticky='w')

lbl_help_log = tk.Label(master=tab_help, text='Master Log functions', 
                               font='Helvetica 12 bold',
                               justify='left', anchor='w')
lbl_help_log.grid(row=4, column=0, padx=10,pady=5,  sticky='w')

text2 = ('To use the master log functions, you need to first load a configuration'
        +' file .csv that maps the desired \nvariables to export with human-friendly'
        +' column labels to populate the output master_log.csv fileheader.'
        +'\n\nWhen you load the config.csv file, an attempt is made to verify'
        +' the variable names map correctly \nand that you are not overwriting the'
        +' existing logbook/header with new variables. \nOnce this test is passed, the other'
        +' log buttons become active \n\nIf you loaded the wrong file'
        +' or need to switch projects, you can use the "Clear/Change Log Sesssion"'
        +'\nbutton to reset the log session variables. The log is unchanged.'
        +'\n\nOnce the log session is initialized, you can chose an existing'
        +' log file or determine the name/location \nof a new one. Then the'
        +' "log session" is initialized and you can append as many rows of'
        +' experimental \nmetadata as you like.' 
        
        )
lbl_help_log_guts = tk.Label(master=tab_help, text=text2, 
                               font='Helvetica 11',
                               justify='left', anchor='w')
lbl_help_log_guts.grid(row=5, column=0, padx=10, sticky='w')

text3 = ('\nThe log configuration files allow you to select which metadata is '
         +' useful to you in your master document. \nBelow is an example config.csv for the RDE tab which maps python variable names to '
         +'the desired \nlog file column labels. Use the buttons to the right to see '
         +'the available \nvariable names to create your own config files.' 
         +'\nDo not worry about or include strings/quotes and do not include timestamp columns in the config files.\nThese are sorted by the mapping functions.'
         +'\n\nvariable_name,column_label'
         +'\nstr_author,Scientist'
         +'\nstr_material_id,Material ID'
         +'\nstr_electrolyte_chem,Electrolyte'
         +'\nstr_electrolyte_conc,Concentration (M)'
         +'\nstr_purpose,Purpose'
         +'\nstr_trial_id,Trial ID'
         +'\n\n After you load the configuration file with "Setup Log Session", '
         +' you will be prompted to load or \nname the log file. If you load an'
         +' existing one, select Yes to replace. The functions only append, not overwrite existing rows.'
         )

lbl_help_config = tk.Label(master=tab_help, text=text3, 
                               font='Helvetica 11',
                               justify='left', anchor='w')
lbl_help_config.grid(row=6, column=0, padx=10, sticky='w')

lbl_help_errata = tk.Label(master=tab_help, text='Errata', 
                               font='Helvetica 12 bold',
                               justify='left', anchor='w')
lbl_help_errata.grid(row=7, column=0, padx=10,pady=5,  sticky='w')

text4 = ('If you get a NoneType or Cannot convert "" to Float error, ' 
         +'you probably need to put a value in the \nCatalyst mass, Ink Volume,'
         +' Reference Potential, or Photon Energy entry field and try the button again.'
         +'\n\n'
    )

lbl_help_errata2 = tk.Label(master=tab_help, text=text4, 
                               font='Helvetica 11',
                               justify='left', anchor='w')
lbl_help_errata2.grid(row=8, column=0, padx=10,  sticky='w')

## Variable registry viewing

frm_help_view_vars = tk.Frame(master=tab_help)
frm_help_view_vars.grid(row=0, column=1, rowspan=15)


# ── Wiring: one shared viewer, two buttons feeding it different builders ───
registry_viewer = VariableRegistryViewer(frm_help_view_vars)

btn_show_rde_vars = tk.Button(
    frm_help_view_vars,
    text="Show RDE Variable Registry",
    command=lambda: registry_viewer.show(build_rde_var_registry),
)
btn_show_rde_vars.grid(row=0, column=0, padx=10, pady=5,  sticky='ew')


btn_show_fc_vars = tk.Button(
    frm_help_view_vars,
    text="Show Flow Cell Variable Registry",
    command=lambda: registry_viewer.show(build_fc_var_registry),
)
btn_show_fc_vars.grid(row=1, column=0, padx=10, pady=5,  sticky='ew')

#%% 7: execution
window.mainloop()
