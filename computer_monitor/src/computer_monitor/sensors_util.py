#!/usr/bin/env python

PKG = 'computer_monitor'
import roslib; roslib.load_manifest(PKG)

import rospy
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue

import subprocess
import math
import re
from StringIO import StringIO

class Sensor(object):
    def __init__(self, line):
        line = line.lstrip()
        [name, reading] = line.split(":")
        [self.name, self.type] = name.rsplit(" ",1)
        
        if self.name == "Core":
            self.name = name
            self.type = "Temperature"
        
        [reading, params] = reading.lstrip().split("(")
        
        self.alarm = False
        if line.find("ALARM") != -1:
            self.alarm = True

        self.input = None
        self.critical = None
        self.min = None
        self.max = None
        self.high = None
        
        if reading.find("\xc2\xb0C") == -1:
            self.input = float(reading.split()[0])
        else:
            self.input = float(reading.split("\xc2\xb0C")[0])
        
        params = params.split(",")
        for param in params:
            m = re.search("[0-9]+.[0-9]*", param)
            if param.find("min") != -1:
                self.min = float(m.group(0))
            elif param.find("max") != -1:
                self.max = float(m.group(0))
            elif param.find("high") != -1:
                self.high = float(m.group(0))
            elif param.find("crit") != -1:
                self.critical = float(m.group(0))  
    
    def getCrit(self):
        return self.critical
    
    def getMin(self):
        return self.min
    
    def getMax(self):
        return self.max
    
    def getInput(self):
        return self.input
    
    def getName(self):
        return self.name
    
    def getType(self):
        return self.type
    
    def getHigh(self):
        return self.high
    
    def getAlarm(self):
        return self.alarm
    
    def __str__(self):
        lines = []
        lines.append(str(self.name))
        lines.append("\t" + "Type:  " + str(self.type))
        if self.input:
            lines.append("\t" + "Input: " + str(self.input))
        if self.min:
            lines.append("\t" + "Min:   " + str(self.min))
        if self.max:
            lines.append("\t" + "Max:   " + str(self.max))
        if self.high:
            lines.append("\t" + "High:  " + str(self.high))
        if self.critical:
            lines.append("\t" + "Crit:  " + str(self.critical))
        lines.append("\t" + "Alarm: " + str(self.alarm))
        return "\n".join(lines)

def _rads_to_rpm(rads):
    return rads / (2 * math.pi) * 60

def _rpm_to_rads(rpm):
    return rpm * (2 * math.pi) / 60

def parse_sensors_output(output):
    out = StringIO(output)
    
    sensorList = []
    for line in out.readlines():
        # Check for a colon
        if line.find(":") != -1 and line.find("Adapter") == -1:
            sensorList.append(Sensor(line))
    return sensorList

def sensor_status_to_diag(sensorList, hostname='localhost', ignore_fans=False):
    stat = DiagnosticStatus()
    stat.name = '%s Sensor Status'%hostname
    stat.message = 'OK'
    stat.level = DiagnosticStatus.OK
    stat.hardware_id = hostname
    
    for sensor in sensorList:
        if sensor.getType() == "Temperature":
            if sensor.getInput() > sensor.getCrit():
                stat.level = max(stat.level, DiagnosticStatus.ERROR)
                stat.message = "Critical Temperature"
            elif sensor.getInput() > sensor.getHigh():
                stat.level = max(stat.level, DiagnosticStatus.WARN)
                stat.message = "High Temperature"
            stat.values.append(KeyValue(key=" ".join([sensor.getName(), sensor.getType()]), 
                                                     value=str(sensor.getInput())))
        elif sensor.getType() == "Voltage":
            if sensor.getInput() < sensor.getMin():
                stat.level = max(stat.level, DiagnosticStatus.ERROR)
                stat.message = "Low Voltage"
            elif sensor.getInput() > sensor.getMax():
                stat.level = max(stat.level, DiagnosticStatus.ERROR)
                stat.message = "High Voltage"
            stat.values.append(KeyValue(key=" ".join([sensor.getName(), sensor.getType()]), 
                                                     value=str(sensor.getInput())))
        elif sensor.getType() == "Speed":
            if not ignore_fans:
                if sensor.getInput() < sensor.getMin():
                    stat.level = max(stat.level, DiagnosticStatus.ERROR)
                    stat.message = "No Fan Speed"
            stat.values.append(KeyValue(key=" ".join([sensor.getName(), sensor.getType()]), 
                                                     value=str(sensor.getInput())))
            
    return stat 
 
def get_sensors():
    p = subprocess.Popen('sensors', stdout = subprocess.PIPE,
                         stderr = subprocess.PIPE, shell = True)
    (o,e) = p.communicate()
    if not p.returncode == 0:
        return ''
    if not o:
        return ''
    return o

if __name__ == '__main__':
    output = get_sensors()
    sensorsList = parse_sensors_output(output)
    sensor_status_to_diag(sensorsList)
    