# -*- coding: utf-8 -*-

from __future__ import print_function
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

from autobahn.twisted.wamp import ApplicationSession

from twisted.internet.protocol import ReconnectingClientFactory
from autobahn.websocket.protocol import parseWsUrl
from autobahn.twisted import wamp, websocket
from autobahn.wamp import types


class Component(ApplicationSession):
    instance_id = 0
    config_push = {}
    build_controller = None

    @staticmethod
    def init(config, controller):
        Component.config_push = config
        Component.build_controller = controller

    @inlineCallbacks
    def onJoin(self, details):
        print("session attached")
        self.build_controller.pusher = self

        def on_update(i):
            print("Got event on update: {}".format(i))
            Component.build_controller.on_update(i)

        topic = "%s.%s" % (
            Component.config_push["prefix"],
            Component.config_push["topic_repo_update"])
        yield self.subscribe(on_update, topic)

        def on_build(i):
            print("Got event on build: {}".format(i))
            Component.build_controller.on_build(i)

        topic = "%s.%s" % (
            Component.config_push["prefix"],
            Component.config_push["topic_build"])
        yield self.subscribe(on_build, topic)

        if Component.instance_id == 0:
            Component.instance_id += 1
            while True:
                try:
                    yield Component.build_controller.watch()
                except Exception as e:
                    print("unexception error:", e)

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


def run(config_info, build_controller):
    config_push = config_info["push_server"]
    Component.init(config_push, build_controller)

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
