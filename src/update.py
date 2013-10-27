
import json
import logging
import os.path
import shutil
import tempfile
import urllib2

import settings


_BITBUCKET_ROOT_URL = 'https://bitbucket.org'
_BITBUCKET_DOWNLOAD_URL = '%(root)s/%(owner)s/%(repo)s/get/%(version)s.tar.gz'
_BITBUCKET_LIST_TAGS_URL = '%(root)s/api/1.0/repositories/%(owner)s/%(repo)s/tags'

_UPDATE_PATHS = ['src', 'static', 'templates', 'motioneye.py']


# versions

def get_version():
    import motioneye
    
    return motioneye.VERSION


def get_all_versions(stable=False):
    url = _BITBUCKET_LIST_TAGS_URL % {
            'root': _BITBUCKET_ROOT_URL,
            'owner': settings.REPO[0],
            'repo': settings.REPO[1]}
    
    try:
        response = urllib2.urlopen(url, timeout=settings.REMOTE_REQUEST_TIMEOUT)
        response = json.load(response)
        versions = response.keys()
        
        # stable versions are those of form x.y
        # unstable versions are of form x.y.z
        if stable:
            versions = [v for v in versions if v.count('.') == 1]

        return versions

    except Exception as e:
        logging.error('could not get versions: %(msg)s' % {'msg': unicode(e)})
        
    return []


def compare_versions(version1, version2):
    version1 = [int(n) for n in version1.split('.')]
    version2 = [int(n) for n in version2.split('.')]
    
    len1 = len(version1)
    len2 = len(version2)
    length = min(len1, len2)
    for i in xrange(length):
        p1 = version1[i]
        p2 = version2[i]
        
        if p1 < p2:
            return -1
        
        elif p1 > p2:
            return 1
    
    if len1 < len2:
        return -1
    
    elif len1 > len2:
        return 1
    
    else:
        return 0


# updating

def download(version):
    url = _BITBUCKET_DOWNLOAD_URL % {
            'root': _BITBUCKET_ROOT_URL,
            'owner': settings.REPO[0],
            'repo': settings.REPO[1],
            'version': version}
    
    try:
        response = urllib2.urlopen(url, timeout=settings.REMOTE_REQUEST_TIMEOUT)
        data = response.read()

    except Exception as e:
        logging.error('could download update: %(msg)s' % {'msg': unicode(e)})
        
        raise
    
    path = tempfile.mkdtemp()
    path = os.path.join(path, version + '.tar.gz')
    
    try:
        with open(path, 'w') as f:
            f.write(data)
        
    except Exception as e:
        logging.error('could download update: %(msg)s' % {'msg': unicode(e)})
        
        raise
    
    return path


def cleanup(path):
    try:
        os.remove(path)
    
    except Exception as e:
        logging.error('could cleanup update directory: %(msg)s' % {'msg': unicode(e)})


def is_updatable():
    # the parent directory of the project directory
    # needs to be writable in order for the updating to be possible
    
    parent = os.path.dirname(settings.PROJECT_PATH)

    return os.access(parent, os.W_OK)


def perform_update(version):
    try:
        # download the archive
        archive = download(version)
        temp_path = os.path.dirname(archive)
        
        # extract the archive
        if os.system('tar zxf %(archive)s -C %(path)s' % {
                'archive': archive, 'path': temp_path}):
            
            raise Exception('archive extraction failed')
        
        # determine the root path of the extracted archive
        root_path = [f for f in os.listdir(temp_path) if os.path.isdir(f)][0]
        
        for p in _UPDATE_PATHS:
            src = os.path.join(root_path, p)
            dst = os.path.join(settings.PROJECT_PATH, p)
            
            if os.path.isdir(dst):
                os.remove(dst)
            
            shutil.copytree(src, dst)

        # remove the temporary update directory
        cleanup(temp_path)
        
        return True
    
    except Exception as e:
        logging.error('could not perform update: %(msg)s' % {'msg': unicode(e)})
        
        return False
