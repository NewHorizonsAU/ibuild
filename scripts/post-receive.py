#!/usr/bin/env python
# -*- coding: utf-8 -*-

from twisted.internet import reactor

from autobahn.twisted.wamp import ApplicationSession

import os
import sys

# config the wamp server url
PUSH_URL = "ws://ws.server:8080/ws"
PUSH_REALM = "realm1"
PUSH_PREFIX = "ibuild"
PUSH_UPDATE = "update.repo"


class Component(ApplicationSession):
    def onJoin(self, details):
        print("session attached")

        (old, new, remote_ref) = sys.stdin.read().split()
        branch = remote_ref.split('/')[-1]
        repo = os.path.basename(os.getcwd()).split('.')[0]
        event = {"repo": repo, "branch": branch, "old": old, "new": new}

        topic = "%s.%s" % (PUSH_PREFIX, PUSH_UPDATE)
        self.publish(topic, event)
        print("update repo: %s, branche %s" % (repo, branch))
        self.leave()

    def onDisconnect(self):
        # print("disconnected")
        reactor.stop()


if __name__ == '__main__':
    from autobahn.twisted.wamp import ApplicationRunner
    runner = ApplicationRunner(PUSH_URL, PUSH_REALM)

    runner.run(Component)
