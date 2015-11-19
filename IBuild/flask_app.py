# -*- coding: utf-8 -*-
from flask import Flask, request, render_template
import os
import sys

reload(sys)
sys.setdefaultencoding('utf8')

app = Flask(__name__, static_folder='static', static_url_path='')

workspaces = {}
logfile = ""
config_task = {}
config_repo = {}


@app.route('/')
def index():
    log_info = open(logfile).read()
    return render_template(
        'index.html', title="Index", log_info=log_info)


@app.route('/task', methods=["Get", "POST"])
def task():
    task = request.args.get('name')
    if task not in config_task:
        return
    build_info = ""
    change_log = ""
    workspace = config_task[task]["workspace"]
    if os.path.isfile(workspace+"/build.txt"):
        build_info = open(workspace+"/build.txt").read()
    if os.path.isfile(workspace+"/changelog.txt"):
        change_log = open(workspace+"/changelog.txt").read()
    repo_lists = config_task[task]["repo_list"]
    return render_template(
        'task.html', title=task, build_info=build_info,
        change_log=change_log, task=task, repo_lists=repo_lists)


@app.route('/repo', methods=["Get", "POST"])
def repo():
    repo = request.args.get('name')
    if repo not in config_repo:
        return
    task_lists = config_repo[repo]
    return render_template(
        'repo.html', title=repo, task_lists=task_lists)


def load_config(config):
    global config_task, config_repo, logfile
    logfile = config["logfile"]
    app.config["push_server"] = config["push_server"]
    app.config["tasks"] = []
    for _config_task in config["task"]:
        task_name = _config_task["name"]
        config_task[task_name] = _config_task
        app.config["tasks"].append(task_name)
        for repo_name, branch in _config_task["repo_list"]:
            if repo_name not in config_repo:
                config_repo[repo_name] = []
            config_repo[repo_name].append([task_name, branch])


def run(config):
    load_config(config)
    app.run(debug=True, port=5000, host='0.0.0.0')
