# -*- coding: utf-8 -*-

from twisted.internet import reactor

from autobahn.twisted.wamp import ApplicationSession


class Component(ApplicationSession):
    config_push = {}
    task = None

    @staticmethod
    def init(config, task):
        Component.config_push = config
        Component.task = task

    def onJoin(self, details):
        print("session attached")
        topic = "%s.%s" % (Component.config_push["prefix"],
                Component.config_push["topic_build"])
        self.publish(topic, Component.task)
        print(topic, Component.task)
        self.leave()

    def onDisconnect(self):
        print("disconnected")
        reactor.stop()


def run(config_info, task):
    config_push = config_info["push_server"]
    Component.init(config_push, task)
    from autobahn.twisted.wamp import ApplicationRunner
    runner = ApplicationRunner(config_push["url"], config_push["realm"])
    runner.run(Component)
