import tkinter as tk
import tkinter.messagebox
import tkinter.font
import tkinter.ttk

import os
import sys

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import numpy as np
from sat_tracker.tracker import *
from sat_tracker.database import *


class PySat_GUI(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title("PySat")
        self.protocol('WM_DELETE_WINDOW', self.on_close)
        ##################  PARAMETERS  ###################
        ##################  MENU  ##################
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        orbit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Orbit", menu=orbit_menu)
        propagate_menu = tk.Menu(orbit_menu, tearoff=0)
        orbit_menu.add_cascade(label="Propagated Recently", menu=propagate_menu)
        orbit_menu.add_separator()
        orbit_menu.add_command(label="New Orbit", command=self.new_orbit)
        orbit_menu.add_command(label="Open Orbit", command=self.open_orbit)
        orbit_menu.add_command(label="Save Orbit", command=self.save_orbit)
        orbit_menu.add_command(label="Save Orbit As", command=self.save_orbit_as)

        track_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tracker", menu=track_menu)
        tracked_menu = tk.Menu(orbit_menu, tearoff=0)
        track_menu.add_cascade(label="Tracked Recently", menu=tracked_menu)
        track_menu.add_separator()
        track_menu.add_command(label="Import TLE File", command=self.import_tle)
        track_menu.add_command(label="Preferences", command=self.tracker_preferences_open)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)

        ##################  VARIABLES  ##################
        # ENGINE
        self.database = None
        self.database_toggle = []
        self.database_categories = []
        self.database_sources = []
        self.database_supp = []
        self.trackable_names = None
        self.trackable_numbers = None
        self.tracker = None
        # COLORS
        self.main_color = "#282828"
        self.secondary_color = "#484848"
        self.text_color = "white"
        self.config(bg=self.main_color)
        # WINDOWS
        # Tracker Preferences
        self.tracker_pref_window = None
        self.previous_configuration = None
        self.tracker_pref_default_label = None
        self.tracker_pref_default_frame = None
        self.tracker_pref_active = None
        self.tracker_pref_molniya = None
        self.tracker_pref_iridium = None
        self.tracker_pref_cosmos = None
        self.tracker_pref_fengyun = None
        self.tracker_pref_indian_asat = None
        self.tracker_pref_russian_asat = None
        self.supp_data_var = None
        self.tracker_pref_entry = None
        self.tracker_pref_buttons = None
        self.tracker_pref_accept = None
        self.tracker_pref_cancel = None
        # WIDGETS
        # Search Bar
        self.search_frame = None
        self.search_var = None
        self.search_entry = None
        self.search_list_box = None
        self.select_button = None
        self.search_results = []
        # Selection Bar
        self.selected_frame = None
        self.tracked_satellites = []
        self.selected_numbers = []
        self.selected_list_box = None
        self.delete_button = None
        # Notebooks
        self.frame_notebook = None
        # Tracking Tab
        self.tracking_tab = None
        self.tracking_figure = None
        self.tracking_ax = None
        self.night_shade = None
        self.tracking_canvas = None
        self.tracking_lines = []
        self.tracking_points = []
        # 3D View Tab
        self.view_3D_tab = None
        self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        ##################  INITIALIZATION  ##################
        self.initialize_UI()
        ################# REFRESHING LOOP ##################
        self.refresh()

    def initialize_UI(self):
        self.load_configuration()
        #### SATELLITES DATABASE ####
        toggles_default = [i.get() for i in self.database_toggle]
        self.database = TLE_Database(self.data_dir, self.database_sources, toggles_default, load_online=True)
        self.tracker = Tracker(self.database)

        #### MAIN TABS ####
        self.frame_notebook = tk.ttk.Notebook(self, width=1000, height=500)
        self.tracking_tab = tk.Frame(self.frame_notebook, bg=self.main_color)
        self.view_3D_tab = tk.Frame(self.frame_notebook, bg=self.main_color)
        self.frame_notebook.add(self.tracking_tab, text="Live Tracking")
        self.frame_notebook.add(self.view_3D_tab, text="3D View")
        self.frame_notebook.grid(column=0, row=0, rowspan=2)

        #### SEARCH BAR ####
        self.search_frame = tk.Frame(self)
        names = self.database.deconstructed_data[0]
        numbers = self.database.deconstructed_data[1]
        names, numbers = (list(t) for t in zip(*sorted(zip(names, numbers))))
        self.trackable_names = names
        self.trackable_numbers = numbers
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.update_search_list)
        self.search_entry = tk.Entry(self.search_frame, textvariable=self.search_var, width=30)
        self.search_list_box = tk.Listbox(self.search_frame, selectmode=tk.MULTIPLE, width=40, height=12)
        self.search_entry.grid(row=0, column=0, padx=10, pady=3)
        self.search_list_box.grid(row=1, column=0, padx=10, columnspan=2)
        self.select_button = tk.Button(self.search_frame, text="+", command=self.search_select, width=3)
        self.select_button.grid(column=1, row=0, sticky="w")
        self.update_search_list()
        self.search_frame.grid(column=1, row=0, sticky="ne")

        #### SELECTED BAR ####
        self.selected_frame = tk.Frame(self)
        self.tracked_satellites = []
        self.selected_list_box = tk.Listbox(self.selected_frame, selectmode=tk.MULTIPLE, width=40, height=12)
        self.selected_list_box.bind("<<ListboxSelect>>", self.satellite_selected)
        self.delete_button = tk.Button(self.selected_frame, text="-", command=self.selection_list_delete, width=3)
        self.selected_list_box.grid(row=1, column=0)
        self.delete_button.grid(row=0, column=0)
        self.update_selection_list()
        self.selected_frame.grid(column=1, row=1, sticky="new")

        #### LIVE TRACKING TAB ####
        self.tracking_figure = Figure(dpi=100)
        self.tracking_figure.patch.set_facecolor(self.main_color)
        self.tracking_ax = self.tracking_figure.add_subplot(111, projection=ccrs.PlateCarree())
        self.tracking_ax.set_extent([-180, 180, -90, 90])
        self.tracking_ax.stock_img()
        self.tracking_ax.coastlines()
        current_time = datetime.datetime.utcnow()
        self.night_shade = self.tracking_ax.add_feature(Nightshade(current_time, alpha=0.4))
        self.tracking_ax.gridlines(draw_labels=False, linewidth=1, color='blue', alpha=0.3, linestyle='--')
        self.live_tracking_plot()
        self.tracking_canvas = FigureCanvasTkAgg(self.tracking_figure, master=self.tracking_tab)
        self.tracking_canvas.draw()
        self.tracking_canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew", rowspan=2)

        #### 3D VIEW TAB ####

        #### COLUMN CONFIGURATION ####
        self.grid_columnconfigure(0, weight=1)
        self.tracking_tab.grid_columnconfigure(0, weight=1)

        #### ROW CONFIGURATION ####
        self.grid_rowconfigure(0, weight=1)
        self.tracking_tab.grid_rowconfigure(0, weight=1)

    def load_configuration(self):
        with open("configuration", "r") as file:
            lines = file.readlines()
        # DATABASE = LINE 1
        self.database_toggle = []
        self.database_categories = []
        line_1 = lines[0].replace("{", " ").replace("}", " ").split()[1].split(";")
        for i in range(len(line_1)):
            self.database_toggle.append(tk.BooleanVar(self, bool(int(line_1[i][-1]))))
            line_1[i] = line_1[i].split("=")
            self.database_categories.append(line_1[i][0].replace("_", " "))
        # LINKS = LINE 2
        line_2 = lines[1].replace("{", " ").replace("}", " ").split()[1].split(";")
        self.database_sources = [None] * len(self.database_categories)
        for i in range(len(self.database_sources)):
            self.database_sources[i] = line_2[i]
        # SUPP LINKS = LINE 3
        self.database_supp = []
        line_3 = lines[2].replace("{", " ").replace("}", " ").split()
        if len(line_3) != 1:
            line_3 = line_3[1].split(";")
            for i in range(len(line_3)):
                self.database_supp.append(line_3[i].split("="))

    def save_configuration(self):
        with open("configuration", "r") as file:
            lines = file.readlines()
        file = open("configuration", "w")
        # UPDATING DATABASE TOGGLE
        file.write("DEFAULT_TOGGLE{")
        name = self.database_categories[0]
        file.write(name + "=" + str(int(self.database_toggle[0].get())))
        for i in range(1, len(self.database_toggle)):
            name = self.database_categories[i].replace(" ", "_")
            file.write(";" + name + "=" + str(int(self.database_toggle[i].get())))
        file.write("}\n")
        # NOT CHANGING DEFAULT LINKS
        file.write(lines[1])
        # UPDATING SUPPLEMENTARY SOURCES
        file.write("SUPP_SOURCES{")
        if len(self.database_supp) != 0:
            name = self.database_supp[0][0]
            link = self.database_supp[0][1]
            file.write(name + "=" + link)
            for i in range(len(self.database_supp) - 1):
                name = self.database_supp[i][0]
                link = self.database_supp[i][1]
                file.write(";" + name + "=" + link)
        file.write("}\n")
        # CLOSING FILE
        file.close()

    def live_tracking_plot(self):
        # Removing past Nightshade and adding current
        self.night_shade.remove()
        current_time = datetime.datetime.utcnow()
        self.night_shade = self.tracking_ax.add_feature(Nightshade(current_time, alpha=0.4))
        # Removing past Ground-Tracks
        if len(self.tracking_lines) != 0:
            for i in self.tracking_lines:
                self.tracking_ax.lines.pop(0)
            self.tracking_lines = []
        # Removing past Nadirs
        if len(self.tracking_points) != 0:
            for i in self.tracking_points:
                i.remove()
            self.tracking_points = []
        # Getting Estimations from Tracker
        t0 = time.time()
        N = 241
        times = np.linspace(t0 - 3600, t0 + 3600, num=241)
        if len(self.tracked_satellites) != 0:
            Long, Lat, H = self.tracker.sub_points(times)
            Long = np.degrees(Long)
            Lat = np.degrees(Lat)
        # Plotting Ground Tracks and current Nadir Positions
        selection = self.selected_list_box.curselection()
        middle = int(N/2)
        for i in range(len(self.tracked_satellites)):
            if i in selection:
                line = self.tracking_ax.plot(Long[i, :], Lat[i, :], transform=ccrs.Geodetic(), color="red", zorder=1)
                point = self.tracking_ax.scatter(Long[i, middle], Lat[i, middle], color="white", s=25,
                                                 alpha=1, transform=ccrs.PlateCarree(), zorder=2, edgecolors='black')
                self.tracking_lines.append(line)
            else:
                point = self.tracking_ax.scatter(Long[i, middle], Lat[i, middle], color="white", s=25,
                                                 alpha=1, transform=ccrs.PlateCarree(), zorder=2, edgecolors='black')
            self.tracking_points.append(point)

    def update_search_list(self, *args):
        search_term = self.search_var.get()
        self.search_list_box.delete(0, tk.END)
        self.search_results = []
        for i in range(len(self.trackable_names)):
            sat_name = self.trackable_names[i]
            sat_number = self.trackable_numbers[i]
            if search_term.lower() in sat_name.lower() or search_term in str(sat_number):
                self.search_list_box.insert(tk.END, sat_name)
                self.search_results.append(sat_number)

    def search_select(self):
        selection = self.search_list_box.curselection()
        names = self.tracked_satellites
        numbers = self.selected_numbers
        for i in selection:
            number = self.search_results[i]
            entered = self.search_list_box.get(i)
            if number not in self.selected_numbers:
                numbers.append(number)
                names.append(entered)
        names, numbers = (list(t) for t in zip(*sorted(zip(names, numbers))))
        self.tracked_satellites, self.selected_numbers = names, numbers
        self.update_selection_list()
        # Updating Tracker
        self.tracker.update_objects(self.selected_numbers)
        # Updating Plots
        self.update_plots()

    def update_selection_list(self, *args):
        self.selected_list_box.delete(0, tk.END)
        for item in self.tracked_satellites:
            self.selected_list_box.insert(tk.END, item)

    def satellite_selected(self, *args):
        self.update_plots()

    def delete_all(self, *args):
        self.tracked_satellites = []
        self.update_selection_list()
        # Updating Tracker
        self.tracker.update_objects(self.selected_numbers)
        # Updating Plots
        self.update_plots()

    def selection_list_delete(self):
        selection = self.selected_list_box.curselection()
        selection = list(selection)
        for i in selection[::-1]:
            self.tracked_satellites.pop(i)
            self.selected_numbers.pop(i)
        self.update_selection_list()
        # Updating Tracker
        self.tracker.update_objects(self.selected_numbers)
        # Updating Plots
        self.update_plots()

    def find_current_tab(self, *args):
        name = self.frame_notebook.tab(self.frame_notebook.select(), "text")
        return name

    def update_plots(self):
        if self.find_current_tab() == "Live Tracking":
            self.live_tracking_plot()
            self.tracking_canvas.draw()
        if self.find_current_tab() == "3D View":
            pass

    def refresh(self):
        self.update_plots()
        self.after(500, self.refresh)

    def new_orbit(self):
        pass

    def save_orbit(self):
        pass

    def open_orbit(self):
        pass

    def save_orbit_as(self):
        pass

    def import_tle(self):
        pass

    def tracker_preferences_open(self):
        # Main Window
        self.tracker_pref_window = tk.Toplevel(self)
        self.previous_configuration = self.database_toggle
        self.tracker_pref_window.grab_set()
        self.tracker_pref_window.title("Tracker Preferences")
        # self.tracker_pref_window.geometry("250x250")
        # Default Database Frame
        self.tracker_pref_default_label = tk.Label(self.tracker_pref_window, text="Default Databases")
        self.tracker_pref_default_label.grid(row=0, column=0, padx=10)
        self.tracker_pref_default_frame = tk.Frame(self.tracker_pref_window,
                                                   highlightbackground="gray", highlightthickness=2)
        self.tracker_pref_default_frame.grid(row=1, column=0, padx=10)
        self.tracker_pref_active = tk.Checkbutton(self.tracker_pref_default_frame, text="Active Satellites",
                                                  variable=self.database_toggle[0])
        self.tracker_pref_active.grid(row=1, column=0, sticky="w")
        self.tracker_pref_molniya = tk.Checkbutton(self.tracker_pref_default_frame, text="Molniya",
                                                   variable=self.database_toggle[1])
        self.tracker_pref_molniya.grid(row=2, column=0, sticky="w")
        self.tracker_pref_iridium = tk.Checkbutton(self.tracker_pref_default_frame, text="Iridium 33 Debris",
                                                   variable=self.database_toggle[2])
        self.tracker_pref_iridium.grid(row=3, column=0, sticky="w")
        self.tracker_pref_cosmos = tk.Checkbutton(self.tracker_pref_default_frame, text="Cosmos 2251 Debris",
                                                  variable=self.database_toggle[3])
        self.tracker_pref_cosmos.grid(row=4, column=0, sticky="w")
        self.tracker_pref_fengyun = tk.Checkbutton(self.tracker_pref_default_frame, text="Fengyun 1C Debris",
                                                   variable=self.database_toggle[4])
        self.tracker_pref_fengyun.grid(row=5, column=0, sticky="w")
        self.tracker_pref_indian_asat = tk.Checkbutton(self.tracker_pref_default_frame, text="Indian ASAT Test Debris",
                                                       variable=self.database_toggle[5])
        self.tracker_pref_indian_asat.grid(row=6, column=0, sticky="w")
        self.tracker_pref_russian_asat = tk.Checkbutton(self.tracker_pref_default_frame, text="Russian ASAT Test Debris",
                                                        variable=self.database_toggle[6])
        self.tracker_pref_russian_asat.grid(row=7, column=0, sticky="w")
        # Supplementary Databases
        self.tracker_pref_default_label = tk.Label(self.tracker_pref_window, text="Extra Databases")
        self.tracker_pref_default_label.grid(row=2, column=0, sticky="w", padx=10)
        self.supp_data_var = tk.StringVar()
        if len(self.database_supp) == 0:
            self.supp_data_var.set("")
        else:
            self.supp_data_var.set(self.database_supp.join(";"))
        self.tracker_pref_entry = tk.Entry(self.tracker_pref_window, textvariable=self.supp_data_var, width=30)
        self.tracker_pref_entry.grid(row=3, column=0, padx=10)
        # Buttons
        self.tracker_pref_buttons = tk.Frame(self.tracker_pref_window)
        self.tracker_pref_buttons.grid(row=4, column=0, padx=10, pady=10)
        self.tracker_pref_accept = tk.Button(self.tracker_pref_buttons, text="Accept",
                                             command=self.tracker_preferences_accept, width=10)
        self.tracker_pref_accept.grid(row=0, column=0, padx=10)
        self.tracker_pref_cancel = tk.Button(self.tracker_pref_buttons, text="Cancel",
                                             command=self.tracker_preferences_cancel, width=10)
        self.tracker_pref_cancel.grid(row=0, column=1, padx=10)

    def tracker_preferences_accept(self):
        #### CHANGING CONFIGURATION FILE ####
        if len(self.supp_data_var.get()) != 0:
            self.database_supp = self.supp_data_var.get().split(";")
        else:
            self.database_supp = []
        self.save_configuration()
        #### RELOADING DATABASE ####
        # Reloading Database
        toggles_default = [i.get() for i in self.database_toggle]
        self.database = TLE_Database(self.data_dir, self.database_sources, toggles_default,
                                     self.database_supp, load_online=True)
        self.tracker = Tracker(self.database)
        # Getting trackable names and numbers for search list
        names = self.database.deconstructed_data[0]
        numbers = self.database.deconstructed_data[1]
        names, numbers = (list(t) for t in zip(*sorted(zip(names, numbers))))
        self.trackable_names = names
        self.trackable_numbers = numbers
        #### DESTROYING WINDOW ####
        self.tracker_pref_window.destroy()
        self.update_search_list()

    def tracker_preferences_cancel(self):
        self.database_toggle = self.previous_configuration
        self.tracker_pref_window.destroy()

    def on_close(self):  # Is called when we want to exit the application
        # Creation of a message choice box
        response = tkinter.messagebox.askyesno('Exit', 'Are you sure you want to exit?')
        if response:
            self.destroy()

    def toggleFullScreen(self):  # Is called when we want to change into fullscreen or remove it.
        self.attributes("-fullscreen", not self.attributes("-fullscreen"))
