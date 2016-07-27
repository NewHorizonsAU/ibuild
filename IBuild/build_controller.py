# -*- coding: utf-8 -*-

from __future__ import print_function
import subprocess
import os
import glob
import shutil
import time
from distutils.dir_util import mkpath
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep


class BuildController(object):
    def __init__(self, config):
        self.config = config
        self.task_repo = {}
        self.repo_task = {}
        self.config_task = {}
        self.update = {}
        repo_url = config["repo_list"]
        self.pusher = None

        for config_task in config["task"]:
            task_name = config_task["name"]
            self.task_repo[task_name] = {}
            for repo_name, branch in config_task["repo_list"]:
                config_repo = {}
                config_repo["name"] = repo_name
                config_repo["branch"] = branch
                config_repo["url"] = repo_url[repo_name]
                config_repo["dir"] = config_task["workspace"] + "/" + repo_name
                repo_branch = repo_name + '.' + branch
                if repo_branch not in self.repo_task:
                    self.repo_task[repo_branch] = {}
                self.task_repo[task_name][repo_branch] = config_repo
                self.repo_task[repo_branch][task_name] = config_task
            self.config_task[task_name] = config_task
        self.init_flag()
        self.logfile = config["logfile"]

    def MyPublish(self, topic, event):
        if self.pusher is None:
            return
        _topic = "%s.%s" % (self.config["push_server"]["prefix"], topic)
        self.pusher.publish(_topic, event)

    def init_flag(self):
        self.flag_repo = {}
        self.flag_task = {}
        self.repo_history = {}
        for repo in self.repo_task:
            self.flag_repo[repo] = False
            self.repo_history[repo] = []
        for task in self.task_repo:
            self.flag_task[task] = False
            self.update[task] = []

    def on_update(self, update_info):
        # update_info: {"repo":repo, "branch": branch}
        repo = update_info["repo"].lower()
        branch = update_info["branch"].lower()
        repo_branch = repo + '.' + branch
        if repo_branch in self.flag_repo:
            self.flag_repo[repo_branch] = True
            self.repo_history[repo_branch].append(
                [update_info["old"], update_info["new"]])

    def on_build(self, task):
        if task in self.flag_task:
            self.flag_task[task] = True
            for repo in self.task_repo[task]:
                self.update[task].append(self.task_repo[task][repo]["name"])

    @inlineCallbacks
    def watch(self):
        for repo in self.flag_repo:
            if not self.flag_repo[repo]:
                continue
            self.flag_repo[repo] = False
            for task in self.repo_task[repo]:
                _config = self.task_repo[task][repo]
                self._task_update_repo(_config)
                self.flag_task[task] = True
                self.update[task].append(self.task_repo[task][repo]["name"])
            self.repo_history[repo] = []

        for task in self.flag_task:
            if not self.flag_task[task]:
                continue
            print("build task %s begin" % task)
            self.flag_task[task] = False
            yield self.task_build(task)
            print("build task %s finish" % task)
        yield sleep(1)

    def release_bin(self, task, directory):
        files = glob.glob("%s/*.bin" % directory) \
            + glob.glob("%s/*.tgz" % directory)
        if not files:
            return

        dir_dest = "%s/%s" % (self.config["bin_dir"], task)
        if not os.path.isdir(dir_dest):
            mkpath(dir_dest)
            mkpath(dir_dest + "/history")
        files2 = glob.glob("%s/*.bin" % dir_dest) \
            + glob.glob("%s/*.tgz" % dir_dest)
        for afile in files2:
            try:
                shutil.move(afile, dir_dest+"/history")
            except Exception:
                shutil.copy2(afile, dir_dest+"/history")
                os.remove(afile)

        for afile in files:
            shutil.move(afile, dir_dest)

    def setBuildError(self, workspace):
        print("%s/.build_error" % workspace)
        os.mknod("%s/.build_error" % workspace)

    def isBuildError(self, workspace):
        return os.path.isfile("%s/.build_error" % workspace)

    def clearBuildError(self, workspace):
        if self.isBuildError(workspace):
            os.remove("%s/.build_error" % workspace)

    @inlineCallbacks
    def _task_cmd(self, cmd, config_task):
        if cmd == "cmd_build":
            p = subprocess.Popen(
                'cd %s; %s' % (config_task["workspace"], config_task[cmd]),
                shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            output = open("%s/build.txt" % config_task["workspace"], "w")
            output.write(("time: %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"))))
            while True:
                line = p.stdout.readline()
                if not line:
                    break
                # print(line, end='')
                output.write(line)
                self.MyPublish("build.%s" % config_task["name"], line)
                yield sleep(0.0001)
            if p.wait() != 0:
                self.setBuildError(config_task["workspace"])

            self.release_bin(config_task["name"], config_task["workspace"])
        else:
            subprocess.call(
                'cd %s; %s' % (config_task["workspace"], config_task[cmd]),
                shell=True)

    def _task_update_repo(self, config_repo):
        DEVNULL = open(os.devnull, 'wb')
        subprocess.call(
            'cd %s;git stash;git fetch;git checkout -f %s;git pull -f;sync' % (
                config_repo["dir"], config_repo["branch"]),
            shell=True, stdout=DEVNULL, stderr=DEVNULL)

        changelog = "%s/../changelog.txt" % config_repo["dir"]
        pre_context = "\n"
        if os.path.isfile(changelog):
            f = open(changelog, 'r')
            pre_context += f.read()
            f.close()
        f = open(changelog, 'w')
        f.write("==== project :%s, branch: %s ====\n" % (
            config_repo["name"], config_repo["branch"]))
        f.flush()

        repo_branch = config_repo["name"] + '.' + config_repo["branch"]
        for commit in reversed(self.repo_history[repo_branch]):
            subprocess.call(
                'cd %s; git log --stat %s..%s' % (
                    config_repo["dir"], commit[0], commit[1]),
                shell=True, stdout=f)
        f.write(pre_context)
        f.close()

    @inlineCallbacks
    def task_cmd(self, cmd, task):
        if task is None:
            for task in self.config_task:
                yield self._task_cmd(cmd, self.config_task[task])
            return

        if task not in self.config_task:
            print("can't find task ", task)
            return

        yield self._task_cmd(cmd, self.config_task[task])

    def insert_to_file(self, filename, text):
        pre_context = ""
        if os.path.isfile(filename):
            f = open(filename, 'r')
            pre_context += f.read()
            f.close()
        f = open(filename, 'w')
        f.write(text)
        f.write(pre_context)
        f.close()

    @inlineCallbacks
    def task_build(self, task):
        msg = ("[%s] build task %s\n" % (time.strftime("%Y%m%d %H:%M"), task))
        self.insert_to_file(self.logfile, msg)
        self.MyPublish("logfile", msg)

        if self.isBuildError(self.config_task[task]["workspace"]):
            # if build failed last time, we need to rebuild every repos
            for repo in self.task_repo[task]:
                self.update[task].append(
                    self.task_repo[task][repo]["name"])
            self.clearBuildError(self.config_task[task]["workspace"])

        os.environ['TASK_NAME'] = task
        os.environ['UPDATE_REPO'] = ' '.join(self.update[task])
        yield self.task_cmd("cmd_build", task)
        self.update[task] = []

    @inlineCallbacks
    def task_clean(self, task):
        msg = ("[%s] clean task %s\n" % (time.strftime("%Y%m%d %H:%M"), task))
        self.insert_to_file(self.logfile, msg)
        self.MyPublish("logfile", msg)
        yield self.task_cmd("cmd_clean", task)

    def task_init(self, task):
        if task not in self.config_task:
            print("can't find task ", task)
            return

        workspace = self.config_task[task]["workspace"]
        if not os.path.isdir(workspace):
            mkpath(workspace)

        for repo in self.task_repo[task]:
            _config = self.task_repo[task][repo]
            if not os.path.isdir(_config["dir"]):
                subprocess.call(
                    'cd %s; git clone %s %s; cd %s; git checkout %s' % (
                        workspace, _config["url"], _config["name"],
                        _config["dir"], _config["branch"]), shell=True)
            else:
                self._task_update_repo(_config)
