# -*- coding: utf-8 -*-

from __future__ import print_function
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

from autobahn.twisted.wamp import ApplicationSession

from twisted.internet.protocol import ReconnectingClientFactory
from autobahn.websocket.protocol import parseWsUrl
from autobahn.twisted import wamp, websocket
from autobahn.wamp import types
from autobahn.twisted.util import sleep

import subprocess


class Component(ApplicationSession):
    instance_id = 0
    config_push = {}

    @staticmethod
    def init(config):
        Component.config_push = config

    @inlineCallbacks
    def onJoin(self, details):
        print("session attached")

        def on_update(_i):
            # print("Got event on update: {}".format(_i))
            cmd = '/home/alt/workspace/ibuild-i5/i5os/build.py'
            subprocess.Popen(
                'python3 %s build %s %s %s' % (
                    cmd, _i['repo'].lower(), _i['branch'], _i['new']),
                shell=True)

        topic = "%s.%s" % (
            Component.config_push["prefix"],
            Component.config_push["topic_repo_update"])
        yield self.subscribe(on_update, topic)

        if Component.instance_id == 0:
            Component.instance_id += 1
            while True:
                yield sleep(1)

    def onDisconnect(self):
        print("disconnected")


class MyClientFactory(websocket.WampWebSocketClientFactory,
                      ReconnectingClientFactory):
    maxDelay = 30

    def clientConnectionFailed(self, connector, reason):
        # print "reason:", reason
        ReconnectingClientFactory.clientConnectionFailed(
            self, connector, reason)

    def clientConnectionLost(self, connector, reason):
        print("Connection Lost")
        # print "reason:", reason
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)


def run(config_info):
    config_push = config_info["push_server"]
    Component.init(config_push)

    # 1) create a WAMP application session factory
    component_config = types.ComponentConfig(realm=config_push["realm"])
    session_factory = wamp.ApplicationSessionFactory(config=component_config)
    session_factory.session = Component

    # 2) create a WAMP-over-WebSocket transport client factory
    url = config_push["url"]
    transport_factory = MyClientFactory(session_factory, url=url, debug=False)

    # 3) start the client from a Twisted endpoint
    isSecure, host, port, resource, path, params = parseWsUrl(url)
    transport_factory.host = host
    transport_factory.port = port
    websocket.connectWS(transport_factory)

    # 4) now enter the Twisted reactor loop
    reactor.run()
