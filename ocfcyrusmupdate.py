#! /usr/bin/env python
# -*- coding: utf-8 -*-

'''
Ces fichiers PyOcfScripts ont été développés pour réaliser des scripts ocf pour pacemaker

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
ocfCyrus script corosync python
nécessite l'installation du module python-psutil
"""

import argparse, sys, os, syslog, sys, shutil
from ocfscripts import ocfScript, ocfError
from ocfreturncodes import ocfReturnCodes

################################################################################
class ocfCyrusMupdate(ocfScript):
    ########################################
    def __init__(self):
        try:
            super(ocfCyrusMupdate, self).__init__('ocfcyrusmupdate', \
                'This is the ocf script to manage cyrus daemon. It can be used to manage a mupdate cluster to master/slave.', \
                'manage any daemon.', \
                '/usr/sbin/cyrmaster', \
                '/var/run/cyrmaster.pid', \
                msfileld='file that active/unactivate cyrus is in master or slave mode (for mupdate)\n/var/run/heartbeat/cyrus.master could be a good choice.', \
                default_binfileoptions='-d -p /var/run/cyrmaster.pid', \
                default_ocf_write_pidfile=False, \
                msfile_is_ra_opt=True, \
                default_kill9=True, \
                maxnbprocess_is_ra_opt=False, \
                piddir_owner_is_ra_opt=False, \
                piddir_group_is_ra_opt=False, \
                piddir_mod_is_ra_opt=False, \
                commande_line_searched_is_ra_opt=False, \
                status_socket_is_ra_opt=True, \
                default_status_socket_return_is_ra_opt=True, \
                status_socket_timeout_is_ra_opt=True, \
                status_socket_obsolete_data_is_ra_opt=True, \
                status_socket_need_all_on_error_is_ra_opt=True, \
                autoaction=False)
        except:
            raise
        else:
            self.add_runoption ('start', self.start)
            self.add_runoption ('stop', self.stop)
            self.add_runoption ('restart', self.restart)
            self.add_runoption ('promote', self.promote)
            self.add_runoption ('demote', self.demote)
            self.add_runoption ('meta-data', self.meta, timeout=5)
            self.add_runoption ('metadata', self.meta, timeout=5)
            self.add_runoption ('meta_data', self.meta, timeout=5)
            self.add_runoption ('monitor', self.monitor, timeout=20, interval=10, depth=0, role='Slave')
            self.add_runoption ('monitor', self.monitor, timeout=19, interval=10, depth=0, role='Master')
            self.add_runoption ('monitor', self.monitor, timeout=19, interval=10, depth=0)
            self.add_runoption ('notify', self.notify, timeout=20)
            self.add_runoption ('validate-all', self.validate, timeout=5)
    
        # Options supplémentaires
        self.init_from_env('cyrus_conf_path', \
            'path to file cyrus.conf', \
            'path to file cyrus.conf', \
            default='/etc/cyrus.conf')
        self.init_from_env('slave_cyrus_conf_path', \
            'path to slave file cyrus.conf', \
            'path to slave file cyrus.conf', \
            default='/etc/cyrus-slave.conf')
        self.init_from_env('master_cyrus_conf_path', \
            'path to master file cyrus.conf', \
            'path to master file cyrus.conf', \
            default='/etc/cyrus-master.conf')
        self.init_from_env('imapd_conf_path', \
            'path to file imapd.conf', \
            'path to file imapd.conf', \
            default='/etc/imapd.conf')
        self.init_from_env('slave_imapd_conf_path', \
            'path to slave file imapd.conf', \
            'path to slave file imapd.conf', \
            default='/etc/imapd-slave.conf')
        self.init_from_env('master_imapd_conf_path', \
            'path to master file imapd.conf', \
            'path to master file imapd.conf', \
            default='/etc/imapd-master.conf')
    
    ########################################
    def reconfigure_mupdate(self, conf_master=False):
        self.ocf_log('ocfCyrusMupdate.reconfigure_mupdate', msglevel=5)
        try:
            #for line in fileinput.input(files=(self.get_option('cyrus_conf_path')), inplace=True):
                #sys.stdout.write(re.sub(pattern, replacestr, line))
            pass # TODO shutil.copy
            if conf_master:
                self.ocf_log('ocfCyrusMupdate.reconfigure_mupdate : copying {}'.format(self.get_option('master_cyrus_conf_path')), msglevel=5)
                shutil.copy(self.get_option('master_cyrus_conf_path'), self.get_option('cyrus_conf_path'))
                self.ocf_log('ocfCyrusMupdate.reconfigure_mupdate : copying {}'.format(self.get_option('master_imapd_conf_path')), msglevel=5)
                shutil.copy(self.get_option('master_imapd_conf_path'), self.get_option('imapd_conf_path'))
            else:
                self.ocf_log('ocfCyrusMupdate.reconfigure_mupdate : copying {}'.format(self.get_option('slave_cyrus_conf_path')), msglevel=5)
                shutil.copy(self.get_option('slave_cyrus_conf_path'), self.get_option('cyrus_conf_path'))
                self.ocf_log('ocfCyrusMupdate.reconfigure_mupdate : copying {}'.format(self.get_option('slave_imapd_conf_path')), msglevel=5)
                shutil.copy(self.get_option('slave_imapd_conf_path'), self.get_option('imapd_conf_path'))
        except:
            self.ocf_log('ocfCyrusMupdate.reconfigure_mupdate: {}'.format(sys.exc_info()), msglevel=0)
    
    ########################################
    def start(self, reset_to_slave=True):
        self.ocf_log('ocfCyrusMupdate.start', msglevel=5)
        if reset_to_slave and self.get_option('msfile'):
            try:
                self.reconfigure_mupdate(conf_master=False)
            except:
                return self.ocfretcodes['OCF_ERR_GENERIC']
        return super(ocfCyrusMupdate, self).start()
    
    ########################################
    def stop(self, reset_to_slave=True):
        self.ocf_log('ocfCyrusMupdate.stop', msglevel=5)
        if reset_to_slave and self.get_option('msfile'):
            try:
                self.reconfigure_mupdate(conf_master=False)
            except:
                return self.ocfretcodes['OCF_ERR_GENERIC']
        return super(ocfCyrusMupdate, self).stop()
    
    ########################################
    def promote(self):
        self.ocf_log('ocfCyrusMupdate.promote', msglevel=5)
        try:
            ret = self.ocfretcodes['OCF_SUCCESS']
            self.initialize()
            msret = self.read_msfile()
            if msret == self.slave:
                ret = self.stop(reset_to_slave=False)
                if ret == self.ocfretcodes['OCF_SUCCESS']:
                    self.reconfigure_mupdate(conf_master=True)
                    ret = self.start(reset_to_slave=False)
                    if ret == self.ocfretcodes['OCF_SUCCESS']:
                        ret = super(ocfCyrusMupdate, self).promote()
        except ocfError as oe:
            return oe.err
        except:
            self.ocf_log('ocfCyrusMupdate.promote: {}'.format(sys.exc_info()), msglevel=0)
            return self.ocfretcodes['OCF_ERR_GENERIC']
        else:
            return ret

    ########################################
    def demote(self):
        self.ocf_log('ocfCyrusMupdate.demote', msglevel=5) 
        try:
            ret = self.ocfretcodes['OCF_SUCCESS']
            self.initialize()
            msret = self.read_msfile()
            if msret == self.master:
                ret = self.stop(reset_to_slave=False)
                if ret == self.ocfretcodes['OCF_SUCCESS']:
                    self.reconfigure_mupdate(conf_master=False)
                    ret = self.start(reset_to_slave=False)
                    if ret == self.ocfretcodes['OCF_SUCCESS']:
                        ret = super(ocfCyrusMupdate, self).demote()
        except ocfError as oe:
            return oe.err
        except:
            self.ocf_log('ocfCyrusMupdate.demote: {}'.format(sys.exc_info()), msglevel=0)
            return self.ocfretcodes['OCF_ERR_GENERIC']
        else:
            return ret
    
################################################################################
def main():
    try:
        s = ocfCyrusMupdate()
    except ocfError as oe:
        syslog.syslog(syslog.LOG_ERR, oe.strerror)
        sys.exit(oe.err)
    except:
        sys.exit(ocfReturnCodes()['OCF_ERR_GENERIC'])
    else:
        parser = argparse.ArgumentParser (description='Ocf script cyrus mupdate.')
        parser.add_argument ('type', help='Option to launch the ocf script.', action='store', choices=s.choices)
        args = parser.parse_args()
        
        sys.exit(s.run(args.type))

################################################################################
if __name__ == '__main__':
    main()