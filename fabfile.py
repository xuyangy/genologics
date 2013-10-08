"""Fabfile to manage workflow for genologics package
"""

from fabric.api import local, prefix, hosts, run
from fabric.context_managers import lcd

from git import Repo
from contextlib import contextmanager
import ConfigParser

CONFIG = ConfigParser.SafeConfigParser()
conf_file = '.fabfilerc'
CONFIG.readfp(open(conf_file))

def get_setting(v):
    return CONFIG.get('settings',v).rstrip()

STAGE = get_setting('STAGE')
STAGE_USER = get_setting('STAGE_USER')
PRODUCTION = get_setting('PRODUCTION')
PRODUCTION_USER = get_setting('PRODUCTION_USER')
USER_GR = get_setting('USER_GIT_REMOTE_NAME')
CENTRAL = get_setting('CENTRAL')
REPO = get_setting('REPO')
LOCAL_REPO_PATH = get_setting('LOCAL_REPO_PATH')

@contextmanager
def checkout(branch, path=LOCAL_REPO_PATH, run_method=local):
    ob = get_repo(path).head.reference.name     # Save current branch
    if ob == branch:
        print "{0} already checked out".format(branch)
        yield
    else:
        with lcd(path):
            run_method("git checkout {0}".format(branch))
            yield
            run_method("git checkout {0}".format(ob))

def merge(branch, run_method=local):
    run_method("git merge {0}".format(branch))

def install_on(venv, run_method=local):
    with lcd(LOCAL_REPO_PATH):
        with prefix('source ~/.virtualenvs/{0}/bin/activate'.format(venv)):
            run_method("python setup.py install")

def pull(remote, branch, run_method=local):
    run_method("git pull {0} {1}".format(remote, branch))

def push(remote, branch, run_method=local):
    run_method("git push {0} {1}".format(remote, branch))

def generate_docs(run_method=local):
    run_method("python scripts/generate_script_docs.py")

def commit_all(ignore_version=False, msg=None, run_method=local):
    assert msg is not None

    if ignore_version:
        run_method("git checkout {0}".format("version.py"))

    run_method('git commit -am "{0}"'.format(msg))
        

def get_repo(path=LOCAL_REPO_PATH):
    return Repo(path)


def prepare_for_stage(branch):
    """ Prepare on local machine for deployment on remote stage """
    assert not get_repo().is_dirty()
    with checkout(branch, run_method=local):

        # sync with user remote git repo
        pull(USER_GR, branch, run_method=local)
        push(USER_GR, branch, run_method=local)

    with checkout('test_scripts', run_method=local):
        pull(USER_GR, 'test_scripts', run_method=local)
        merge(branch, run_method=local)
        install_on('genologics-lims', run_method=local)

        # Needed for proper doc generation on readthedocs
        generate_docs(run_method=local)
        commit_all(ignore_version=True, 
                   msg=("Auto: Regenerated doc templates after merging {0} "
                        "to test_scripts").format(branch),
                   run_method=local)
        push(USER_GR, 'test_scripts', run_method=local)

@hosts(STAGE)
def deploy_to_stage():
    """ Deploys branch to stage by merging it to test_scripts branch"""
    raise NotImplementedError
    assert local_user == 'glsai'

    checkout('test_scripts')
    pull(USER, 'test_scripts')

    # Install on virtualenv validate_scripts
    install_on('validate_scripts')

def prepare_for_production(branch):
    """ Prepare pull request for production by merging it to master branch"""
    raise NotImplementedError
    assert hostname not in (STAGE, PRODUCTION)
    checkout(branch)
    pull(USER, 'master')
    merge(branch, 'master')

def deploy_to_production(branch):
    """ Deploys branch to production by merging it to master branch"""
    raise NotImplementedError
    assert hostname == PRODUCTION
    assert(local_user == 'glsai')
    pull(CENTRAL, 'master')
    merge(branch, 'master')
    install_on('epp_master')
