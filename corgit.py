import os
import re
import sys
import github

import logging
from logging import StreamHandler
from logging.handlers import WatchedFileHandler

log = logging.getLogger('corgit')


# Global configuration properties
config = None


HEADER = '### Referenced Issues:'

def update_pr_description(repo_name, pr_number):

    log.info('Updating PR description for %s PR %s' % (repo_name, pr_number))

    gh = github.Github(config['git.token'])
    repo = gh.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    title = pr.title
    body = pr.body

    issues = set(re.findall(r'\bgs-(\d+)', title + ' ' + body))

    links = '\n'.join('* [Issue %s](%sissues/%s)' % (issue, config['redmine.url'], issue)
                      for issue in issues)

    lines = [line.strip() for line in body.split('\n')]

    if HEADER in lines:
        log.info('Found existing list of issues, updating')
        # update existing list
        pos = lines.index(HEADER) + 1
        while pos < len(lines) and lines[pos].startswith('* '):
            del lines[pos]
        if links:
            lines.insert(pos, links)
        else:
            log.info('Removing existing list of issues')
            del lines[pos - 1]
    elif links:
        log.info('No existing list of issues found, creating')
        lines.append(HEADER)
        lines.append(links)

    updated_body = '\n'.join(lines)

    if updated_body != body:
        log.info('Committing new body')
        pr.edit(body=updated_body)
    else:
        log.info('Body unchanged, skipping commit')


if __name__ == "__main__":
    # Load configuration
    from configobj import ConfigObj
    config = os.path.join(os.path.dirname(__file__), 'server.cfg')
    config = ConfigObj(config, interpolation=False, file_error=True)

    # Set up our log level
    try:
        filename = config['server.logging_filename']
        handler = WatchedFileHandler(filename)
    except KeyError:
        handler = StreamHandler()
    handler.setFormatter(logging.Formatter(config['server.logging_format']))
    root_logger = logging.getLogger('')
    root_logger.setLevel(int(config['server.logging_level']))
    root_logger.addHandler(handler)

    try:
        repo_name = sys.argv[1]
        pr_number = int(sys.argv[2])
    except:
        print """Usage: %s user/repo prnumber

        Appends a list of links to referenced Redmine issues to the pull
        request description in Github.
        """ % sys.argv[0]
        sys.exit(1)

    update_pr_description(repo_name, pr_number)