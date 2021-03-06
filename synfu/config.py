# encoding: utf-8
#
# config.py 
# 
# Copyright (c) 2009-2010 René Köcher <shirk@bitspin.org>
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modifica-
# tion, are permitted provided that the following conditions are met:
# 
#   1.  Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
# 
#   2.  Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ''AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MER-
# CHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO
# EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPE-
# CIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTH-
# ERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
# OF THE POSSIBILITY OF SUCH DAMAGE.
# 
# Created by René Köcher on 2009-12-19.
#

"""
.. module:: config
    :platform: Unix, MacOS, Windows
    :synopsis: Shared settings manager.

.. moduleauthor:: René Köcher <shirk@bitspin.org>

"""

try:
    import re
except:
    import sre as re

import sys, os, socket, optparse, yaml

class _FUCoreConfig(yaml.YAMLObject):

    def __init__(self, **kwargs):
        self.verbose = False
        self.verbosity = 0
        self.settings = {}
        self.log_facility = 'syslog'
        self.log_filename = '/var/log/synfu.log'
        self.log_when = 'D'
        self.log_interval = 1
        self.log_keep = 14
        self.log_traceback = None
        self.blacklist_filename = None
        self.settings = {}

    def configure(self):
        self.verbose = self.settings.get('verbose', False)
        self.verbosity = self.settings.get('verbosity', 0)
        self.log_facility = self.settings.get('log_facility', 'syslog')
        self.log_filename = self.settings.get('log_filename', '/var/log/synfu.log')
        self.log_traceback = self.settings.get('log_traceback', None)
        self.log_when = self.settings.get('log_when', 'D')
        self.log_interval = self.settings.get('log_interval', 1)
        self.log_keep = self.settings.get('log_keep', 14)
        self.blacklist_filename = self.settings.get('blacklist_filename', None)

class _ReactorConfig(_FUCoreConfig):
    yaml_tag = u'tag:news.piratenpartei.de,2009:synfu/reactor'
    
    def __init__(self, **kwargs):
        super(_ReactorConfig, self).__init__(**kwargs)
        
    def __repr__(self):
        return '{0}{{ outlook_hacks: {1}, complex_footer: {2}, verbose: {3} }}'.format(
                self.__class__.__name__,
                self.outlook_hacks,
                self.complex_footer,
                self.verbose)

    def configure(self):
        super(_ReactorConfig, self).configure()
        self.outlook_hacks  = self.settings.get('outlook_hacks', False)
        self.complex_footer = self.settings.get('complex_footer', False)
        self.strip_notes    = self.settings.get('strip_notes', False)
        self.fix_dateline   = self.settings.get('fix_dateline', False)
        return self

class _PostfilterConfig(_FUCoreConfig):
    yaml_tag = u'tag:news.piratenpartei.de,2009:synfu/postfilter'
    
    def __init__(self, **kwargs):
        super(_PostfilterConfig, self).__init__(**kwargs)
    
    def __repr__(self):
        return '{0}{{ mail2news_cmd: "{1}", news2mail_cmd: "{2}", filters[{3}] }}'.format(
                self.__class__.__name__,
                self.mail2news_cmd,
                self.news2mail_cmd,
                len(self.filters))
    
    def configure(self):
        super(_PostfilterConfig, self).configure()
        self.mail2news_cmd   = self.settings.get('mail2news_cmd', '/bin/false').strip()
        self.news2mail_cmd   = self.settings.get('news2mail_cmd', '/bin/false').strip()
        self.inn_sm          = self.settings.get('inn_sm'       , '/bin/false').strip()
        self.inn_host        = self.settings.get('inn_host'     , '/bin/false').strip()
        self.default_sender  = self.settings.get('default_sender', None)
        self.log_mail2news   = self.settings.get('log_mail2news', self.log_filename)
        self.log_news2mail   = self.settings.get('log_news2mail', self.log_filename)
        self.use_path_marker = self.settings.get('use_path_marker', False)
        self.path_marker     = self.settings.get('path_marker', socket.gethostname()).strip()
        
        for e in self.filters:
            try:
                e['exp'] = re.compile('(?i){0}'.format(e['smtp']))
            except Exception,err:
                sys.stderr.write('Could not compile expression "{0[smtp]}": {1}\n'.format(e, err))
                pass

            if not 'approve' in e:
                e['approve'] = None
        
        return self

class _ImpConfig(_FUCoreConfig):
    yaml_tag = u'tag:news.piratenpartei.de,2010:synfu/imp'

    def __init__(self, **kwargs):
        super(_FuseConfig, self).__init__(**kwargs)
    
    def __repr__(self):
        return '{0}{{ plugins: "{3}" }}'.format(
               self.__class__.__name__,
               self.plugin_dir)
    
    def configure(self):
        super(_ImpConfig, self).configure()
        self.plugin_dir  = self.settings.get('plugin_dir' , '/var/lib/synfu/imp/')

        return self
    
class Config(object):
    """SynFU global config"""
    
    _sharedConfig = None
    _parser       = None
    
    @classmethod
    def add_option(cls, *args, **kwargs):
        """
        .. versionadded:: 0.4.10
        Add a new option to the global set of parameters.
        
        After a call to :meth:`Config.get` the parsed options and arguments will
        be accessible as :attr:`Config.option` and :attr:`Config.optargs`.
        
        :param: \*args: positional arguments to passed to :meth:`optparse.OptionParser.add_option`
        :param: \**keywords: keyword arguments to passed to :meth:`optpars.OptionParser.add_option`
        :returns: None
        """
        
        if Config._parser == None:
            Config._parser = optparse.OptionParser()
            
        if args:
            Config._parser.add_option(*args, **kwargs)

    @classmethod
    def get(cls, *args):
        """
        Return the shared Config instance (initalizing it as needed).
        For the config syntax in use see `_synfu-config-syntax`.
        
        :param \*args: optional paths to search for synfu.conf
        :type \*args:  list of strings or None
        :rtype:        :class:`synfu.config.Config`
        :returns:      an initialized :class:`synfu.config.Config` instance
        """
        
        if Config._sharedConfig:
            return Config._sharedConfig
        
        Config.add_option('-c', '--config',
                          dest    = 'config_path',
                          action  = 'store',
                          default = None,
                          help    = 'Path to config file')
        
        paths = ['.', '/etc', '/usr/local/etc']
        paths.insert(0, os.path.join(os.getenv('HOME','/'),'.config'))
        
        if args:
            paths = list(args) + paths
        
        
        (opts, args) = Config._parser.parse_args(sys.argv[1:])
        if opts.config_path:
            paths.insert(0, opts.config_path)
        
        for path in paths:
            try:
                if not path.endswith('synfu.conf'):
                    conf_path = os.path.join(path, 'synfu.conf')
                else:
                    conf_path = path
                
                Config._sharedConfig = Config(conf_path, opts, args)
                
                return Config._sharedConfig
                
            except IOError,e:
                pass
        
        raise RuntimeError('Failed to load synfu.conf')
    
    def __init__(self, path, options, *optargs):
        super(Config, self).__init__()

        self.postfilter = None
        self.reactor    = None
        self.imp        = None
        self.options    = options
        self.optargs    = optargs
        
        with open(path, 'r') as data:
            for k in yaml.load_all(data.read()):
                if type(k) == _PostfilterConfig:
                    self.postfilter = k.configure()
                    
                elif type(k) == _ReactorConfig:
                    self.reactor = k.configure()
                    
                elif type(k) == _ImpConfig:
                    self.imp = k.configure()
                    
                else:
                    print('What is type(k) == {0} ?'.format(type(k)))
                    
        if not self.postfilter:
            raise RuntimeError('Mandatory postfilter config missing.')
            
        if not self.reactor:
            raise RuntimeError('Mandatory reactor config missing.')
            
        if not self.imp:
            raise RuntimeError('Mandatory imp config missing.')
    

