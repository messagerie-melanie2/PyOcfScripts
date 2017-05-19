#! /usr/bin/env python
# -*- coding: utf-8 -*-

'''
Ces fichiers PyOcfScripts ont été édéveloppés pour réaliser des scripts ocf pour pacemaker

PyOcfScripts Copyright © 2017  PNE Annuaire et Messagerie/MEDDE

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

"""
ocfNamed script corosync python
nécessite l'installation du module python-psutil
"""

import argparse, sys, os, syslog, subprocess
from ocfscripts import ocfScript, ocfError
from ocfreturncodes import ocfReturnCodes

################################################################################
class ocfNamed(ocfScript):
    ########################################
    def __init__(self):
        try:
            super(ocfNamed, self).__init__('ocfNamed', 'This is the ocf script to manage dns daemon named', 'manage named daemon.', \
                '/usr/sbin/named', '/var/run/named/named.pid',\
                binfilesd='Full name of the named binary to be executed.', binfileld='The full name of the named binary to be executed.', \
                binfileoptionssd='other start options for named', binfileoptionsld='other start options for named', \
                default_piddir_owner='root', \
                default_piddir_group='bind', \
                default_piddir_mod='775', \
                maxnbprocess_is_ra_opt=False, \
                commande_line_searched_is_ra_opt=False, \
                msfileld='file that active/unactivate named is in master or slave mode\n/var/run/heartbeat/named.master could be a good choice.', msfile_is_ra_opt=True, \
                default_sleepafterstart=10, sleepafterstartld='sleep time befor the first monitoring after the start of process.', \
                default_starttimeoutratio=0.95, \
                default_ocf_write_pidfile=False, \
                default_start_force_stop_timeout=15, \
                autoaction=False)
        except:
            raise
        else:
            self.add_runoption ('start', self.start, timeout='300s')
            self.add_runoption ('stop', self.stop, timeout='300s')
            self.add_runoption ('restart', self.restart, timeout='600s')
            self.add_runoption ('reload', self.reload, timeout='20s')
            self.add_runoption ('promote', self.promote, timeout='20s')
            self.add_runoption ('demote', self.demote, timeout='600s')
            self.add_runoption ('meta-data', self.meta, timeout='5s')
            self.add_runoption ('metadata', self.meta, timeout='5s')
            self.add_runoption ('meta_data', self.meta, timeout='5s')
            self.add_runoption ('monitor', self.monitor, timeout='20s', interval=10, depth=0, role='Slave')
            self.add_runoption ('monitor', self.monitor, timeout='19s', interval=10, depth=0, role='Master')
            self.add_runoption ('monitor', self.monitor, timeout='19s', interval=10, depth=0)
            self.add_runoption ('notify', self.notify, timeout='20s')
            self.add_runoption ('validate-all', self.validate, timeout='5s')
            
        # Options supplémentaires
        self.init_from_env('namedconf', \
            'configuration file for named. For exemples : /etc/bind/named.conf', \
            'configuration file for named', \
            default='/etc/bind/named.conf')
        self.init_from_env('named_user', 'System account to run the named server under', 'System account to run the named server under.', default='bind')
        self.init_from_env('reloadcmd', 'command for a reload', 'command for a reload', default='/usr/sbin/rndc')
        self.init_from_env('reloadopts', 'options for the reload command', 'options for the reload command', default='reload')

    ########################################
    def start(self):
        self.ocf_log('ocfSlapd.start', msglevel=5)
        
        try:
            if self.get_option('msfile'): self.init_dir(os.path.dirname(self.get_option('msfile')))
        except ocfError as oe:
            return oe.err
        else:
            startopts= [ '-u', self.get_option('named_user')]
            return super(ocfNamed, self).start(otheropts=startopts)

    ########################################
    def __do_named_reload(self):
        '''
        raise ocfError
        '''
        devnull = open(os.devnull, 'wb') # TODO try/except ?
        self.ocf_log('ocfNamed.__do_named_reload, reloading process with command : {} {}'.format(self.get_option('reloadcmd'), self.get_option('reloadopts')), msglevel=2)
        
        startopts = [self.get_option('reloadcmd')]
        if self.get_option('reloadopts'): startopts += self.get_option('reloadopts').split(' ')
        
        try:
            process = subprocess.Popen(startopts, stdout=devnull, stderr=subprocess.STDOUT)
            devnull.close()
        except OSError as ose:
            msg='Could not be reloaded : {}'.format(ose.strerror)
            self.ocf_log_err(msg)
            raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
        except:
            msg='Could not be reloaded'
            self.ocf_log_err(msg)
            raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)

    ########################################
    def reload(self):
        self.ocf_log('ocfNamed reload', msglevel=5)
        
        try:
            if self.get_option('msfile'): self.init_dir(os.path.dirname(self.get_option('msfile')))
            self.initialize()
        except ocfError as oe:
            return oe.err

        try:
            self.__do_named_reload()
        except ocfError as oe:
            return oe.err
        else:
            return self.ocfretcodes['OCF_SUCCESS']

    ########################################
    def promote(self):
        self.ocf_log('ocfNamed.promote', msglevel=5)
        
        ret = super(ocfNamed, self).promote()
        try:
            self.__do_named_reload()
        except ocfError as oe:
            return oe.err
        else:
            return ret

    ########################################
    def demote(self):
        self.ocf_log('ocfNamed.demote', msglevel=5) 
        
        ret = super(ocfNamed, self).demote()
        try:
            self.__do_named_reload()
        except ocfError as oe:
            return oe.err
        else:
            return ret

    ########################################
    def validate(self):
        self.ocf_log('ocfSlapd.validate', msglevel=5)
        
        if not os.path.isfile(self.get_option('reloadcmd')) or (os.path.isfile(self.get_option('reloadcmd')) and not os.access(self.get_option('reloadcmd'), os.X_OK)):
            msg = 'reloadcmd {} does not exist or is not executable'.format(self.get_option('reloadcmd'))
            self.ocf_log_err(msg)
            raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], msg)
        
        return super(ocfNamed, self).validate()

################################################################################
def main():
    try:
        s = ocfNamed()
    except ocfError as oe:
        syslog.syslog(syslog.LOG_ERR, oe.strerror)
        sys.exit(oe.err)
    except:
        sys.exit(ocfReturnCodes()['OCF_ERR_GENERIC'])
    else:
        parser = argparse.ArgumentParser (description='script ocf named.')
        parser.add_argument ('type', help='Option to launch the ocf script.', action='store', choices=s.choices)
        args = parser.parse_args()
        
        sys.exit(s.run(args.type))

################################################################################
if __name__ == '__main__':
    main()
    