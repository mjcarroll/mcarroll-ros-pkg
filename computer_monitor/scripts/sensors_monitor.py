#!/usr/bin/env python

from __future__ import with_statement, division

PKG = 'computer_monitor'
import roslib; roslib.load_manifest(PKG)
import rospy
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus
import computer_monitor

import socket

class SensorsMonitor(object):
    def __init__(self, hostname):
        self._pub = rospy.Publisher('/diagnostics', DiagnosticArray)
        self.hostname = hostname
        self.ignore_fans = rospy.get_param('~ignore_fans', False)
        rospy.loginfo("Ignore fanspeed warnings: %s"%self.ignore_fans)
        
    def pub_status(self):
        try:
            sensors_out = computer_monitor.get_sensors()
            sensorsList = computer_monitor.parse_sensors_output(sensors_out)
            stat = computer_monitor.sensor_status_to_diag(sensorsList,self.hostname, self.ignore_fans)
        except Exception, e:
            import traceback
            rospy.logerr('Unable to process lm-sensors data')
            rospy.logerr(traceback.format_exc())
        
        array = DiagnosticArray()
        array.header.stamp = rospy.Time.now()
        
        array.status = [stat]
        self._pub.publish(array)
        
if __name__ == '__main__':
    hostname = socket.gethostname()
    try:
        rospy.init_node('sensors_monitor_%s'%hostname)
    except rospy.ROSInitException:
        print >> sys.stderr, 'Unable to initialize node. Master may not be running'
        sys.exit(0)
    
    monitor = SensorsMonitor(hostname)
    my_rate = rospy.Rate(1.0)
    while not rospy.is_shutdown():
        monitor.pub_status()
        my_rate.sleep()
