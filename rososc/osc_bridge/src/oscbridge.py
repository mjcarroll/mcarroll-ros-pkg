import roslib; roslib.load_manifest('osc_bridge')
import rospy

import osc_msgs.msg
import osc_msgs.encoding

from std_msgs.msg import String

from pytouchosc.bonjour import Bonjour

from twisted.internet import reactor, threads
from txosc import osc
from txosc import dispatch
from txosc import async

from threading import Thread

class Node:
    def __init__(self, *args, **kwargs):
        rospy.init_node(*args, **kwargs)
        rospy.core.add_shutdown_hook(self._shutdown_by_ros)
        reactor.addSystemEventTrigger('after', 'shutdown', self._shutdown_by_reactor)
    
    def _shutdown_by_reactor(self):
        rospy.signal_shutdown("Reactor shutting down.")
        
    def _shutdown_by_ros(self, *args):
        reactor.fireSystemEvent('shutdown')

class OSCBridge:
    def __init__(self, name, port, regtype = '_osc._udp'):
        Node("osc_bridge")
        self.name = name
        self.port = port
        self.regtype = regtype
        self.pub = rospy.Publisher('chatter', String)
        #Bonjour Server
        self.bonjourServer = Bonjour(self.name, self.port, self.regtype,
                debug = rospy.logdebug,
                info = rospy.loginfo,
                error = rospy.logerr)
        reactor.callInThread(self.bonjourServer.run,daemon=True)
        #Twisted OSC receiver
        self._osc_receiver = dispatch.Receiver()
        self._osc_receiver_port = reactor.listenUDP(self.port, async.DatagramServerProtocol(self._osc_receiver))
        #Add OSC callbacks
        self._osc_receiver.addCallback("/ping", self.ping_handler)
        self._osc_receiver.addCallback("/quit", self.quit_handler)
        self._osc_receiver.fallback = self.fallback

    def ping_handler(self, message, address):
        rospy.loginfo("Got %s from %s" % (message, address))
        
    def quit_handler(self, message, address):
        rospy.loginfo("Got /quit, shutting down")
        reactor.stop()
        
    def fallback(self, message, address):
        rospy.loginfo(message)
        self.pub.publish(message)