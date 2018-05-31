#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Program entry point"""

from __future__ import print_function

import argparse
import sys

from IBuild import metadata
import json
from build_controller import BuildController

reload(sys)
sys.setdefaultencoding('utf8')


def main(argv):
    """Program entry point.

    :param argv: command-line arguments
    :type argv: :class:`list`
    """
    author_strings = []
    for name, email in zip(metadata.authors, metadata.emails):
        author_strings.append('Author: {0} <{1}>'.format(name, email))

    epilog = '''
{project} {version}

{authors}
URL: <{url}>
'''.format(
        project=metadata.project,
        version=metadata.version,
        authors='\n'.join(author_strings),
        url=metadata.url)

    arg_parser = argparse.ArgumentParser(
        prog=argv[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=metadata.description,
        epilog=epilog)
    arg_parser.add_argument(
        '--config', type=argparse.FileType('r'),
        help='config file')
    arg_parser.add_argument(
        'command',
        choices=['watch', 'build', 'clean', 'init', 'web', 'i5app'], nargs='?',
        help='the command to run')
    arg_parser.add_argument(
        'task', nargs='?',
        help='the build/clean/init task(ibuild, nut, ...)')
    arg_parser.add_argument(
        '-V', '--version',
        action='version',
        version='{0} {1}'.format(metadata.project, metadata.version))

    args = arg_parser.parse_args(args=argv[1:])

    if (args.config):
        config_info = json.load(args.config)
        build_controller = BuildController(config_info)
    else:
        print(epilog)
        return 0

    if args.command == "build":
        import task_build
        task_build.run(config_info, args.task)
    elif args.command == "clean":
        build_controller.task_clean(args.task)
    elif args.command == "init":
        build_controller.task_init(args.task)
    elif args.command == "watch":
        import task_watch
        task_watch.run(config_info, build_controller)
    elif args.command == "i5app":
        import task_i5app
        task_i5app.run(config_info)
    elif args.command == "web":
        import flask_app
        flask_app.run(config_info)
    else:
        print(epilog)

    return 0


def entry_point():
    """Zero-argument entry point for use with setuptools/distribute."""
    raise SystemExit(main(sys.argv))


if __name__ == '__main__':
    entry_point()
