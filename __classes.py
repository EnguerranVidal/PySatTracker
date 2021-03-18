# PROJECT SEPTEMBRE 2020-FEBRUARY 2021
# NORAD BASED SATELLITE TRACKER / CLASSES
# By Enguerran VIDAL

# This file contains all the classes used in the project.

###############################################################
#                           IMPORTS                           #
###############################################################


#-----------------MODULES
import numpy as np
import matplotlib.pyplot as plt
import time
import calendar
import datetime
from mpl_toolkits.mplot3d import Axes3D

import cartopy.crs as ccrs
import cartopy.feature as cfeature

import os
import sys
#-----------------PYTHON FILES
from __functions import*


###############################################################
#                      NORAD DATABASE                         #
###############################################################

class NORAD_TLE_Database():
    ''' This class will fetch the NORAD database structured in a TLE format such as :

            OSCAR 10
            1 14129U          88230.56274695 0.00000042           10000-3 0  3478
            2 14129  27.2218 308.9614 6028281 329.3891   6.4794  2.05877164 10960
            GPS-0008
            1 14189U          88230.24001475 0.00000013                   0  5423
            2 14189  63.0801 108.8864 0128028 212.9347 146.3600  2.00555575 37348

        The database can be found on https://www.amsat.org/tle/current/nasabare.txt
        and is updated every few days.
        Parameters :
        - filename : name of the NORAD filename where the data will be stored
        - load_online : (Boolean) if True --> load NORAD data from a websiteand write it
                        down in the mentionned "filename".
        '''
    def __init__(self,filename,load_online=True):
        self.source_url='https://www.amsat.org/tle/current/nasabare.txt'
        self.current_dir=os.path.dirname(os.path.abspath(__file__))
        self.filename=filename
        if load_online==True:
            import requests
            r = requests.get(self.source_url,allow_redirects=True)
            open(filename,'wb').write(r.content)
            print("NORAD File : "+filename)
        self.data=[]
        self.labels=['name','number','epoch_year','epoch','inclination','right_ascension_of_the_ascending_node'
                     ,'eccentricity','argument_of_perigee','mean_anomaly','mean_motion']
        self.load_data(filename)

    def load_data(self,filename):
        ''' Formats the data from "filename" ( .txt file ) and returns the
            desired outputs ( moslty Keplerian Parameters)'''
        path=self.current_dir+"\\norad\\"+filename
        assert os.path.exists(path)==True,"ERROR : File "+filename+" cannot be found in "+self.current_dir+"\\norad\\"+" directory, try a different name."
        with open(path,"r") as file:
            lines=file.readlines()
            file.close()
        n=len(lines)
        satellite_names=[]
        satellite_numbers=[]
        epoch_years=[]
        epoch_days=[]
        inclinations=[]
        ascensions=[]
        eccentricities=[]
        arguments=[]
        mean_anomalies=[]
        mean_motions=[]
        self.n_satellites=int(n/3)
        for i in range(int(n/3)):
            line1=lines[i*3]
            line2=lines[i*3+1]
            line3=lines[i*3+2]
            satellite_names.append(line1)
            #print(line2[18:20])
            satellite_numbers.append(int(line2[2:7]))
            if int(line2[18:20])>=57:
                epoch_years.append(int("19"+line2[18:20]))
            else:
                epoch_years.append(int("20"+line2[18:20]))
            epoch_days.append(float(line2[20:32]))
            inclinations.append(float(line3[8:16])*2*np.pi/360)
            ascensions.append(float(line3[17:25])*2*np.pi/360)
            eccentricities.append(float("0."+line3[26:33]))
            arguments.append(float(line3[34:42])*2*np.pi/360)
            mean_anomalies.append(float(line3[34:42])*2*np.pi/360)
            mean_motions.append(float(line3[52:63])*7.272205216643*10**(-5))
        self.data.append(satellite_names)
        self.data.append(satellite_numbers)
        self.data.append(epoch_years)
        self.data.append(epoch_days)
        self.data.append(inclinations)
        self.data.append(ascensions)
        self.data.append(eccentricities)
        self.data.append(arguments)
        self.data.append(mean_anomalies)
        self.data.append(mean_motions)

    def search_index(self,name):
        ''' Returns the index of an object in the NORAD database cretaed by the class.
            Parameters :
            - name : str type, can be an object name or object official number.'''
        n=len(self.data[0])
        name=name.lower()
        for i in range(n):
            index_name=self.data[0][i].lower()
            index_name=index_name[:-1]
            index_number=str(self.data[1][i]).lower()
            if name==index_name or name==index_number:
                return i
        return False

###############################################################
#                        ORBIT CLASS                          #
###############################################################

class Orbit():
    ''' Class creating an object capable of space mecanics calculations such as analytical propagation
        of satellites' trajectories from ephemeride or Norad data.
        A "Foyer" needs to be given : parent massive body ( moslty Earth )'''
    def __init__(self,Foyer):
        self.Foyer=Foyer
        self.G=6.6740831*10**(-11)
        self.mu=self.G*self.Foyer.mass
        self.time_manager=Time_Manager()

    def __str__(self):
        ''' prints the orbit's main characteristics '''
        assert type(self.draconitic_period)!=type(None),"Orbit not defined, cannot display info."
        print("Orbit around "+self.Foyer.object_name)
        print("######################################")
        print("Semi-Major Axis : ",self.semi_axis/(10**3)," km")
        print("Inclination : ",radians2degrees(self.inclination)," °")
        print("Longitude of Ascending Node : ",radians2degrees(self.ascending_node)," °")
        print("Periapsis argument : ",radians2degrees(self.argument_periapsis)," °")
        print("Eccentricity : ",self.eccentricity)
        print("######################################")
        print("Anomalistic Period : ",self.anomalistic_period/60," min")
        print("Draconitic Period : ",self.draconitic_period/60," min")
        print("Nodal Precession : ",radians2degrees(self.nodal_precession)*86400," °/day")
        print("Apsidal Precession : ",radians2degrees(self.apsidal_precession)*86400," °/day")
        print(self.time_manager.seconds_unix_str(self.defined_epoch))
        return "######################################"
        
    def true_anomaly(self,epoch):
        ''' Returns the true anomaly of a satellite form "epoch" : UNIX timestamp given by
            functions such as time.time() from the time module. It uses a Newton's method to
            solve the Kepler anomaly equation for the eccentric anomaly from the mean anomaly
            and calculates the corresponding true anomaly'''
        M=self.keplerian_mean_motion*(epoch-self.periapsis_epoch)
        e=self.eccentricity
        E=np.full_like(M,np.pi) # We initialize the eccentric anomaly with the mean anomaly value
        while np.all(np.absolute(E-e*np.sin(E)-M)>0.0000000001):
            E=E-(E-e*np.sin(E)-M)/(1-e*np.cos(E))
        nu=2*np.arctan(np.sqrt((1+e)/(1-e))*np.tan(E/2))
        return nu

    def kepler_equation(self,E):
        '''Returns the mean anomaly from eccentricity and eccentric anomaly.'''
        return E-self.eccentricity*np.sin(E)

    def true_to_excentric(self,nu):
        '''Transforms true anomaly into eccentric anomaly'''
        e=self.eccentricity
        return 2*np.arctan(np.sqrt((1-e)/(1+e))*np.tan(nu/2))

    def satellite_distance(self,theta):
        '''Calculates the distance between the foyer centre and the satellite
            from theta (true anomaly)'''
        a=self.semi_axis
        e=self.eccentricity
        return a*(1-e**2)/(1+e*np.cos(theta))

    def semi_rectus(self,a,e):
        ''' Calculates the semi rectus from : a (semi-major axis) and e (eccentricity) '''
        return a*(1-e**2)

    def potential_perturbations(self,a):
        ''' Returns the Keplerian parameters's main perturbations fromthe influence of J2, J2^2 and J4
            ( on the mean motion, longitude of the ascending node and periapsis argument )'''
        J2=self.Foyer.J[2]
        J4=self.Foyer.J[4]
        e=self.eccentricity
        i=self.inclination
        s=np.sin(i)
        de=np.sqrt(1-e**2)
        semi_rectus=self.semi_rectus(a,e)
        zeta=self.Foyer.equatorial_radius/semi_rectus
        d_Omega=(J2*zeta**2*np.cos(i)*(-3/2)
                 +J2**2*zeta**4*np.cos(i)*((-45/8+(3*e**2)/4+(9*e**4)/32)+(57/8-(69*e**2)/32-(27*e**4)/64)*s**2)
                 +J4*zeta**4*np.cos(i)*(15/4-(105*s**2)/16)*(1+(3*e**2)/2))
        d_w=(J2*zeta**2*(3-15*s**2/4)
             +J2**2*zeta**4*((27/2-15*e**2/16-9*e**4/16)+(-507/16+171*e**2/31+99*e**4/64)*s**2+(1185/64-675*e**2/128+99*e**4/64)*s**4)
             +J4*zeta**4*((-3/8+15*s**2/8-105*s**4/64)*(10+15*e**2/2)+(-15/4+165/16*s**2-105/16*s**4)*(1+3*e**2/2)))
        D_n=(J2*zeta**2*de*(3/4)*(2-3*s**2)*(1+J2*zeta**2*(1/8)*(10+5*e**2+8*de-(65/6-25*e**2/12+12*de)*s**2))
             -J2**2*zeta**4*de*(5/64)*(2-e**2)*s**2
             -J4*zeta**4*de*(45/128)*e**2*(8-40*s**2+35*s**4))
        return [d_Omega,d_w,D_n]

    def define_TLE(self,i,e,omega,w,M,n,epoch):
        ''' Defines the orbit's parameters from TLE based data of a specific object.'''
        self.inclination=i
        self.eccentricity=e
        self.argument_periapsis=w
        self.ascending_node=omega
        # Finding the semi-major axis by an iteration process
        self.semi_axis=np.cbrt(self.mu/n**2)
        self.keplerian_period=np.sqrt(self.semi_axis**3*4*np.pi**2/self.mu)
        self.keplerian_mean_motion=n
        # Defined epochs
        self.periapsis_epoch=epoch-M/n
        self.defined_epoch=epoch
        E_node=self.true_to_excentric(self.argument_periapsis)
        M_node=self.kepler_equation(E_node)
        self.node_epoch=epoch-(M-M_node)*0
        # Calculating perturbations
        [dO,dw,dn]=self.potential_perturbations(self.semi_axis)
        self.nodal_precession=dO*n
        self.apsidal_precession=dw*n
        # Defining the different periods
        self.anomalistic_period=(1-dn)*self.keplerian_period
        self.draconitic_period=self.anomalistic_period/(1+dw)

    def position_inertial_reference(self,epoch):
        ''' Input parameter (epoch) : UNIX based timestamp given by functions such as time.time() for example.
            Returns np.array type as np.array([X,Y,Z]) : object's cartesian position in the geocentric inertial reference frame'''
        Omega=self.ascending_node
        dOmega=self.nodal_precession
        OmegaGt=self.Foyer.GMST(self.defined_epoch)
        dOmegaT=self.Foyer.rotation_rate0
        i=self.inclination
        e=self.eccentricity
        a=self.semi_axis
        tNA=self.node_epoch
        w=self.argument_periapsis+self.apsidal_precession*(epoch-self.defined_epoch)
        nu=self.true_anomaly(epoch)
        R=self.satellite_distance(nu)
        # Euler Angles
        alpha1=(Omega-OmegaGt)+(dOmega-dOmegaT)*(epoch-tNA)
        alpha2=i
        alpha3=w+nu
        matrix=np.array([np.cos(alpha1)*np.cos(alpha3)-np.sin(alpha1)*np.sin(alpha3)*np.cos(alpha2),
                         np.sin(alpha1)*np.cos(alpha3)+np.cos(alpha1)*np.sin(alpha3)*np.cos(alpha2),
                         np.sin(alpha3)*np.sin(alpha2)])
        return R*matrix

    def position_fixed_reference(self,epoch):
        ''' Input parameter (epoch) : UNIX based timestamp given by functions such as time.time() for example.
            Returns np.array type as np.array([X,Y,Z]) : object's cartesian position in the geocentric fixed reference frame'''
        Omega=self.ascending_node
        dOmega=self.nodal_precession
        OmegaGt=self.Foyer.GMST(self.defined_epoch)
        dOmegaT=self.Foyer.rotation_rate0
        i=self.inclination
        tNA=self.node_epoch
        w=self.argument_periapsis+self.apsidal_precession*(epoch-tNA)
        nu=self.true_anomaly(epoch)
        R=self.satellite_distance(nu)
        X=np.array([R*np.cos(nu),R*np.sin(nu),0], dtype="object")
        # Euler Angles
        alpha1=Omega+(dOmega)*(epoch-self.defined_epoch)
        alpha2=i
        alpha3=w+nu
        matrix=np.array([np.cos(alpha1)*np.cos(alpha3)-np.sin(alpha1)*np.sin(alpha3)*np.cos(alpha2),
                         np.sin(alpha1)*np.cos(alpha3)+np.cos(alpha1)*np.sin(alpha3)*np.cos(alpha2),
                         np.sin(alpha3)*np.sin(alpha2)])
        return R*matrix

###############################################################
#                        EARTH CLASS                          #
###############################################################

class Earth():
    ''' This class takes care of observers position, satellite ground traces and overhead passings.'''
    def __init__(self):
        self.object_name='Earth'
        self.mass=5.9722*10**24 #kg
        self.equatorial_radius=6378000 #m
        self.polar_radius=6356000 #m
        self.rotation_rate0=7.2921155*10**(-5) #rad/sec
        self.rotation_rate1=1.00273790934 #turn/day
        # Time Manager for the class
        self.time_manager=Time_Manager()
        # Geopotential Harmonic Coefficients
        self.J=[1,0,1082.62622070*10**(-6),
                -2.53615069*10**(-6),-1.61936355*10**(-6),
                -0.22310138*10**(-6),0.54028952*10**(-6),
                -0.36026016*10**(-6),-0.20776704*10**(-6),
                -0.14456739*10**(-6),-0.23380081*10**(-6)]
        self.geodesic_eccentricity=np.sqrt(1-(self.polar_radius/self.equatorial_radius)**2)

    def GMST(self,epoch):
        ''' Returns the Greenwich Mean Sidereal Time in radians at the given UNIX timestamp ( epoch )'''
        DJ=self.time_manager.day_fraction(epoch)
        du=self.time_manager.julian_date(epoch)-2451545.0-DJ
        Tu=du/36525
        qG00=(24110.54841+8640184.812866*Tu+9.3104*10**(-2)*Tu**2-6.2*10**(-6)*Tu**3)%86400
        qGt=(qG00+86400*self.rotation_rate1*DJ)%86400
        OmegaGt=degrees2radians(qGt/240)
        return OmegaGt

    def geodesic_latitude(self,lat):
        '''Gets the geodesic latitude from the geocentric latitude'''
        return np.arctan(np.tan(lat)/(1-self.geodesic_eccentricity**2))

    def geocentric_latitude(self,lat):
        '''Gets the geocentric latitude from the geodesic latitude'''
        return np.arctan(np.tan(lat)*(1-self.geodesic_eccentricity**2))

    def lat_to_radius(self,lat):
        ''' Returns the Earth ellipsoid radius from geodesic latitude. '''
        r1=self.equatorial_radius
        r2=self.polar_radius
        num=(r1**2*np.cos(lat))**2+(r2**2*np.sin(lat))**2
        denom=(r1*np.cos(lat))**2+(r2*np.sin(lat))**2
        R=np.sqrt(num/denom)
        return R

    def cartesian_tolonglat(self,Positions):
        '''Returns the Long,Lat geodesic ( geographic ) coordinates of the subpoints
           of given cartesian Positions given in a geocentric inertial reference frame.'''
        X=Positions[0]
        Y=Positions[1]
        Z=Positions[2]
        R=np.sqrt(X**2+Y**2+Z**2)
        X=X/R
        Y=Y/R
        Z=Z/R
        centric_Lats=np.arcsin(Z)
        Longs=np.sign(Y)*np.arccos(X/np.cos(centric_Lats))
        geodesic_Lats=self.geodesic_latitude(centric_Lats)
        return Longs,centric_Lats

    def define_topocentric_ref(self,longitude,latitude,elevation):
        ''' Defines the topocentric reference frame of the observer for overhead-passings
            prediction'''
        self.ground_longitude=longitude
        self.ground_latitude=latitude
        self.ground_elevation=elevation
        radius=self.lat_to_radius(latitude)
        centric_lat=self.geocentric_latitude(latitude)
        self.ground_position=np.array([(radius+elevation)*np.cos(centric_lat)*np.cos(longitude),
                                       (radius+elevation)*np.cos(centric_lat)*np.sin(longitude),
                                       (radius+elevation)*np.sin(centric_lat)])
        u=self.ground_position/np.linalg.norm(self.ground_position)
        n=np.array([(radius+elevation)*np.cos(centric_lat-np.pi/2)*np.cos(longitude),
                                       (radius+elevation)*np.cos(centric_lat-np.pi/2)*np.sin(longitude),
                                       (radius+elevation)*np.sin(centric_lat-np.pi/2)])
        n=n/np.linalg.norm(n)
        e=np.cross(n,u)
        self.n=n
        self.e=e
        self.u=u

    def topocentric_position(self,Positions):
        ''' Returns the topocentric coordinates of an object from cartesian Positions given in a Geocentric
            Inertial Reference frame. These coordinates comprise of the object's Azimuth and its Elevation.'''
        p=(Positions-self.ground_position[:,np.newaxis])/vector_norm(Positions-self.ground_position[:,np.newaxis])
        Elevations=np.zeros(shape=(p.shape[1]))
        Azimuths=np.zeros(shape=(p.shape[1]))
        for i in range(Elevations.shape[0]):
            Elevations[i]=np.arcsin(np.dot(p[:,i],self.u))
            Azimuths[i]=np.arctan(np.dot(p[:,i],self.e)/np.dot(p[:,i],self.n))
        return Azimuths,Elevations

###############################################################
#                         TIME CLASS                          #
###############################################################

class Time_Manager():
    ''' This class takes care of time managing tasks and conversions'''
    def __init__(self):
        self.julian_leap=[31,29,31,30,31,30,31,31,30,31,30,31]
        self.julian_common=[31,28,31,30,31,30,31,31,30,31,30,31]
        self.week_days=['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
        self.months=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

    def is_leap(self,year):
        ''' Gives true depending on if the mentionned year is a leap year or not.'''
        if year%4==0 and year%100!=0:
            return True    
        elif year%400==0:
            return True
        else:
            return False

    def date_julian(self,year,dayfraction):
        ''' Returns a UNIX timestamp from a year and a dayfraction : fraction of days since
            beginning of the year mentionned'''
        YEAR=datetime.datetime(year,1,1,0)
        year=YEAR.replace(tzinfo=datetime.timezone.utc).timestamp()
        epoch=year+(dayfraction-1)*86400
        return epoch

    def seconds_unix_str(self,epoch):
        '''Returns a string corresponding to the "epoch" UNIX timestamp'''
        struct=time.gmtime(epoch)
        string=time.asctime(struct)
        return string 

    def day_of_year(self,epoch):
        '''gives the day of the year correpsonding to "epoch" as an UNIX timestamp'''
        struct=time.gmtime(epoch)
        n_days=struct.tm_yday
        return n_days

    def time_range(self,str1,str2,N):
        ''' Returns a time row matrix between str1 and str2 containing N time values'''
        time1=self.str_seconds_unix(str1)
        time2=self.str_seconds_unix(str2)
        T=np.linspace(time1,time2, num=N)
        return T

    def day_fraction(self,epoch):
        ''' Returns the day fraction at "epoch" as an UNIX timestamp'''
        struct=time.localtime(epoch)
        years=struct.tm_year
        months=struct.tm_mon
        days=struct.tm_mday
        DATE=datetime.datetime(years,months,days,0)
        date=DATE.replace(tzinfo=datetime.timezone.utc).timestamp()
        fraction=(epoch-date)/86400
        return fraction

    def julian_date(self,epoch):
        ''' Return the Julian date from a UNIX timestamp "epoch" '''
        JULIAN_EPOCH=datetime.datetime(2000,1,1,12)
        JULIAN_EPOCH=JULIAN_EPOCH.replace(tzinfo=datetime.timezone.utc).timestamp()
        julian_day=epoch-JULIAN_EPOCH+2451545.0*86400
        return julian_day/86400

###############################################################
#                      TRACKER CLASS                          #
###############################################################

class Tracker():
    ''' The Tracker Database is the main class of this project. It permits its user to track a satellite
        or random target available throughout the NORAD database and access its trajectory as well as its
        ground track.'''
    def __init__(self,load_online=True,filename='NORAD.txt'):
        self.current_dir=os.path.dirname(os.path.abspath(__file__))
        self.time_manager=Time_Manager()
        self.earth=Earth()
        self.database=NORAD_TLE_Database(filename,load_online)

    def ground_station(self,position):
        ''' Defines the on-ground tracking station'''
        longitude,latitude,elevation=geo_coordinates(position)
        print("Ground Station at : ",radians2degrees(longitude),"° long ",radians2degrees(latitude),"° lat ")
        self.earth.define_topocentric_ref(longitude,latitude,elevation)        

    def focus(self,object_name):
        ''' Focuses the Tracker oject on a target searched throughout the available NORAD data.'''
        index=self.database.search_index(object_name)
        assert type(index)==type(1),str(object_name)+" cannot be found inside the database provided."
        n=len(self.database.labels)
        data=[]
        for i in range(n):
            data.append(self.database.data[i][index])
        self.tracked_object=data[0]
        epoch=self.time_manager.date_julian(data[2],data[3])
        self.orbit=Orbit(self.earth)
        self.orbit.define_TLE(data[4],data[6],data[5],data[7],data[8],data[9],epoch)

    def immediate_sub_point(self):
        ''' Prints the immediate target's sub-point '''
        epoch=time.time()
        Positions=self.orbit.position_inertial_reference(epoch)
        longitude,latitude=self.earth.cartesian_tolonglat(Positions)
        print("Longitude : ",radians2degrees(longitude),"° ; Latitude : ",radians2degrees(latitude),"°")

    def object_position(self,epoch):
        ''' Gets the traget's position in the Geocentric Inertial Reference Frame'''
        Positions=self.orbit.position_inertial_reference(epoch)
        longitude,latitude=self.earth.cartesian_tolonglat(Positions)
        return longitude,latitude

    def draw3D_period(self,reference='inertial',n=1,moment='immediate'):
        ''' Plots the target's trajectory over "n" orbital periods in a 3D plot'''
        fig=plt.figure()
        ax=fig.gca(projection='3d')
        ax.set_title(self.tracked_object)
        ax.set_xlim3d(-50000000,50000000)
        ax.set_ylim3d(-50000000,50000000)
        ax.set_zlim3d(-50000000,50000000)
        xLabel=ax.set_xlabel('\nX [ m ]',linespacing=3.2)
        yLabel=ax.set_ylabel('\nY [ m ]',linespacing=3.1)
        zLabel=ax.set_zlabel('\nZ [ m ]',linespacing=3.4)
        if moment=='immediate':
            t0=time.time()
        if moment=='first':
            t0=self.orbit.defined_epoch
        T=n*self.orbit.anomalistic_period
        epoch=np.linspace(t0,t0+T,int(n*200))
        if reference=='inertial':
            Positions=self.orbit.position_inertial_reference(epoch)
        else:
            Positions=self.orbit.position_fixed_reference(epoch)
        ax.plot(Positions[0],Positions[1],Positions[2],c='b')
        frame_xs,frame_ys,frame_zs=WireframeSphere(radius=self.earth.equatorial_radius)
        #sphere = ax.plot_wireframe(frame_xs,frame_ys,frame_zs,color="r",alpha=0.5)
        plt.show()

    def true_anomaly(self,n=1,moment='immediate'):
        ''' Plots the true anomaly over "n" orbital periods'''
        if moment=='immediate':
            t0=time.time()
        if moment=='first':
            t0=self.orbit.defined_epoch
        T=n*self.orbit.anomalistic_period
        epoch=np.linspace(t0,t0+T,int(n*200))
        true_anomaly=self.orbit.true_anomaly(epoch)
        epoch=epoch-t0
        plt.title(self.tracked_object+" t0 : "+self.time_manager.seconds_unix_str(t0))
        plt.plot(epoch,true_anomaly)
        plt.show()

    def draw2D_period(self,n=1,moment='immediate'):
        ''' Draws the ground track over the Earth's surface for "n" orbital periods '''
        if moment=='immediate':
            t0=time.time()
        if moment=='first':
            t0=self.orbit.defined_epoch
        T=n*self.orbit.anomalistic_period
        epoch=np.linspace(t0,t0+T,int(n*200))
        Long,Lat=self.object_position(epoch)
        Lat=radians2degrees(Lat)
        Long=radians2degrees(Long)
        ax = plt.axes(projection=ccrs.PlateCarree())
        track=ax.plot(Long,Lat,transform=ccrs.PlateCarree())
        ax.set_extent([-180,180,-90,90])
        ax.add_feature(cfeature.COASTLINE)
        ax.add_feature(cfeature.OCEAN, facecolor='#CCFEFF')
        ax.add_feature(cfeature.LAND, facecolor='#FFE9B5')
        ax.gridlines(draw_labels=False, linewidth=1, color='blue', alpha=0.3, linestyle='--')
        plt.show()

    def live_tracking(self):
        ''' NOT OPERATIONAL - Plots a live tracking of the target object with its ground track'''
        # Initial position and ground track
        t0=time.time()
        T=self.orbit.anomalistic_period
        epoch=np.linspace(t0,t0+T)
        Long,Lat=self.object_position(epoch)
        # Initializing plot
        plt.title(self.time_manager.seconds_unix_str(t0))
        ax = plt.axes(projection=ccrs.PlateCarree())
        ax.set_extent([-180,180,-90,90])
        ax.add_feature(cfeature.COASTLINE)
        ax.add_feature(cfeature.OCEAN, facecolor='#CCFEFF')
        ax.add_feature(cfeature.LAND, facecolor='#FFE9B5')
        ax.gridlines(draw_labels=False, linewidth=1, color='blue', alpha=0.3, linestyle='--')
        track=ax.plot(Long,Lat,transform=ccrs.PlateCarree())
        satellite=ax.scatter(Long[0],Lat[0],s=2)
        continuing=1
        while continuing==1:
            return 0


    def above_passings(self,time_range='24h',save=True,plot=True):
        ''' NOT OPERATIONAL - Returns the overhead passings of the target object in a time range beginning t the instance of lauch.
            Available time ranges : 6h ; 12h ; 24h ; day ; 48h ; week'''
        time_ranges=["6h","12h","24h","day","48h","week","1 period"]
        lengths=[21600,43200,86400,86400,172800,604800,self.orbit.anomalistic_period]
        assert time_range in time_ranges,"Time range iven not considered, try a different one."
        T=lengths[time_ranges.index(time_range)]
        t0=time.time()
        epochs=np.linspace(t0,t0+T,num=T)
        print("Calculating above-head passings of "+self.tracked_object+" between "
              +self.time_manager.seconds_unix_str(t0)+" and "+self.time_manager.seconds_unix_str(t0+T))
        Positions=self.orbit.position_inertial_reference(epochs)
        Azimuths,Elevations=self.earth.topocentric_position(Positions)
        print(radians2degrees(Azimuths))
        print(radians2degrees(Elevations))
        Azimuths,Elevations=radians2degrees(Azimuths),radians2degrees(Elevations)
        Elevations=np.maximum(Elevations,np.zeros_like(Elevations))
        if plot==True:
            fig=plt.figure()
            ax=fig.gca(projection='polar')
            ax.plot(Azimuths,Elevations)
            ax.set_xticklabels(['S', '', 'E', '', 'N', '', 'W', ''])
            plt.show()
