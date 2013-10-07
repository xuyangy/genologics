"""Fabfile to manage workflow for genologics package
"""

from fabric.api import *
import ConfigParser

CONFIG = ConigParser.SafeConfigParser()
conf_file = CONFIG.read('.fabfilerc')
CONFIG.readfp(open(conf_file))

def get_setting(v):
    return CONFIG.get('settings',v).rstrip()

STAGE = get_setting('STAGE')
PRODUCTION = get_setting('PRODUCTION')
USER = get_setting('USER')
CENTRAL = get_setting('CENTRAL')
REPO = get_setting('REPO')


def merge():
    pass

def workon():
    pass

def install_on(venv):
    pass

def pull():
    pass

def generate_docs():
    pass

def commit(checkout=None):
    pass

def push():
    pass

def prepare_for_stage(branch):
    """ Prepare on local machine for deployment on remote stage """
    assert hostname not in (STAGE, PRODUCTION)
    checkout(branch)

    # sync with user remote git repo
    pull(USER, branch)
    push(USER, branch)
    
    # Check out the branch used for scripts ready to be tested
    checkout('test_scripts')
    pull(USER, 'test_scripts')

    merge(branch)

    # Regenerate documentation
    install_on('genologics-lims')
    generate_docs()
    commit(checkout=['version.py'])
    push(USER, 'test_scripts')

def deploy_to_stage():
    """ Deploys branch to stage by merging it to test_scripts branch"""
    assert hostname==STAGE
    assert local_user == 'glsai'

    checkout('test_scripts')
    pull(USER, 'test_scripts')

    # Install on virtualenv validate_scripts
    install_on('validate_scripts')

def prepare_for_production(branch):
    """ Prepare pull request for production by merging it to master branch"""
    assert hostname not in (STAGE, PRODUCTION)
    checkout(branch)
    pull(USER, 'master')
    merge(branch, 'master')
    raise NotImplementedError

def deploy_to_production(branch):
    """ Deploys branch to production by merging it to master branch"""
    assert hostname == PRODUCTION
    assert(local_user == 'glsai')
    pull(CENTRAL, 'master')
    merge(branch, 'master')
    install_on('epp_master')
    raise NotImplementedError
