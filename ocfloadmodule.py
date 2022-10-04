#! /usr/bin/env python
# -*- coding: utf-8 -*-

'''
Ces fichiers PyOcfScripts ont été édéveloppés pour réaliser des scripts ocf pour pacemaker

PyOcfScripts Copyright © 2022  PNE Annuaire et Messagerie/MEDDE

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
ocfLoadModule script corosync python
nécessite l'installation du module python-psutil
"""

import argparse
import sys
import os
import syslog
import subprocess
import re
import time
from ocfscripts import ocfScript, ocfError
from ocfreturncodes import ocfReturnCodes

################################################################################
class ocfLoadModule(ocfScript):
    ########################################
    def __init__(self):
        try:
            super(ocfLoadModule, self).__init__('ocfLoadModule', \
                'This is the ocf script to load and unload kernel module.', \
                'Load and unload kernel module.', \
                None, \
                None, \
                binfile_is_ra_opt=False, \
                pidfile_is_ra_opt=False, \
                piddir_owner_is_ra_opt=False, \
                piddir_group_is_ra_opt=False,  \
                piddir_mod_is_ra_opt=False, \
                binfileoptions_is_ra_opt=False, \
                maxnbprocess_is_ra_opt=False, \
                commande_line_searched_is_ra_opt=False, \
                fixdirs_is_ra_opt=False, \
                default_kill3=False, \
                kill3_is_ra_opt=False, \
                kill9_is_ra_opt=False, \
                kill15_ratio_is_ra_opt=False, \
                kill3_ratio_is_ra_opt=False, \
                kill9_ratio_is_ra_opt=False, \
                default_sleepafterstart=10, \
                default_sleepafterstop=10, \
                sleepaftersigquit_is_ra_opt=False, \
                sleepaftersigkill_is_ra_opt=False, \
                default_ocf_write_pidfile=False, \
                ocf_write_pidfile_is_ra_opt=False, \
                default_monitor_clean_dirty_pidfile=False, \
                monitor_clean_dirty_pidfile_is_ra_opt=False, \
                starttimeoutratio_is_ra_opt=False, \
                start_force_stop_timeout_is_ra_opt=False, \
                process_file_ulimit_is_ra_opt=False, \
                status_check_ppid_is_ra_opt=False, \
                status_check_pidfile_is_ra_opt=False)
        except:
            raise

        # Options supplémentaires
        self.init_from_env('module_name', \
            'module name to load and unload the kernel module', \
            'module name to load and unload the kernel module', \
            required=1)
        self.init_from_env('module_options', \
            'options for the module', \
            'options for the module', \
            default='')
        self.init_from_env('cmd_load_module', \
            'Command used to load the kernel module', \
            'Command used to load the kernel module', \
            default='/sbin/modprobe')
        self.init_from_env('cmd_unload_module', \
            'Command used to load the kernel module', \
            'Command used to load the kernel module', \
            default='/sbin/rmmod --force')
        self.init_from_env('cmd_monitor_module', \
            'Command used to load the kernel module', \
            'Command used to load the kernel module', \
            default='/sbin/lsmod')
        self.init_from_env('pre_start_cmd', \
            'Command to be executed before loading the module', \
            'Command to be executed before loading the module', \
            default=None)
        self.init_from_env('post_start_cmd', \
            'Command to be executed after loading the module', \
            'Command to be executed after loading the module', \
            default=None)
        self.init_from_env('pre_stop_cmd', \
            'Command to be executed before unloading the module', \
            'Command to be executed before unloading the module', \
            default=None)
        self.init_from_env('post_stop_cmd', \
            'Command to be executed after unloading the module', \
            'Command to be executed after unloading the module', \
            default=None)
        self.init_from_env('sleep_after_pre_start_cmd', \
            'time in seconds to sleep after pre-start command', \
            'time in seconds to sleep after pre-start command', \
            default=1, \
            convertfct=self.convert_to_int)
        self.init_from_env('sleep_after_post_start_cmd', \
            'time in seconds to sleep after post-start command', \
            'time in seconds to sleep after post-start command', \
            default=1, \
            convertfct=self.convert_to_int)
        self.init_from_env('sleep_after_pre_stop_cmd', \
            'time in seconds to sleep after pre-stop command', \
            'time in seconds to sleep after pre-stop command', \
            default=1, \
            convertfct=self.convert_to_int)
        self.init_from_env('sleep_after_post_stop_cmd', \
            'time in seconds to sleep after post-stop command', \
            'time in seconds to sleep after post-stop command', \
            default=1, \
            convertfct=self.convert_to_int)

        self.re_find_module = re.compile("^{}".format(self.get_option('module_name')))

    ########################################
    def initialize(self):
        self.ocf_log('ocfLoadModule.initialize', msglevel=5)            
        try:
            self.infonotify()
        except:
            msg='Error during ocfscript initialize (see previous error log)'
            self.ocf_log_err(msg)
            raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)


    ########################################
    def status(self, clean_dirty_pidfile=False, check_pidfile=False, check_ppid=False):
        self.ocf_log('ocfLoadModule.status', msglevel=5)
        try:
            startopts = self.get_option('cmd_monitor_module').split()
            process =  subprocess.Popen(startopts, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            for line in process.stdout:
                res = self.re_find_module.search(line)
                if res:
                    self.ocf_log('ocfLoadModule.status kernel module {} loaded'.format(self.get_option('module_name')), msglevel=3)
                    return self.ocfretcodes['OCF_SUCCESS']
            else:
                self.ocf_log('ocfLoadModule.status kernel module {} not loaded'.format(self.get_option('module_name')), msglevel=3)
        except:
            raise
        return self.ocfretcodes['OCF_NOT_RUNNING']

    ########################################
    def exec_action(self, action_name, cmd, sleep_time):
        self.ocf_log('ocfLoadModule.exec_action {} with {}'.format(action_name, cmd), msglevel=2)
        try:
            startopts = cmd.split()
            devnull = open(os.devnull, 'wb') # TODO try/except ?
            process = subprocess.Popen(startopts, stdout=devnull, stderr=subprocess.STDOUT)
            devnull.close()
            self.ocf_log('ocfLoadModule.exec_action {} waiting {} seconds...'.format(action_name, sleep_time), msglevel=3)
            time.sleep(sleep_time)
        except OSError as ose:
            self.ocf_log_err('{} could not be executed: {}'.format(cmd, ose.strerror))
            raise
        except:
            self.ocf_log_err('{} could not be executed'.format(cmd))
            raise

    ########################################
    def action(self, action_name, action_cmd, sleep_action, pre_action_cmd, sleep_pre_action, post_action_cmd, sleep_post_action):
        self.ocf_log('ocfLoadModule.action {}'.format(action_name), msglevel=5)
        try:
            # Pre action
            if pre_action_cmd is not None:
                self.exec_action("Pre {}".format(action_name), pre_action_cmd, sleep_pre_action)
            # Action
            self.exec_action(action_name, action_cmd, sleep_action)    
            # Post action
            if post_action_cmd is not None:
                self.exec_action("Post {}".format(action_name), post_action_cmd, sleep_post_action)
            return self.status()
        except:
            self.ocf_log_raise('ocfLoadModule.action: error during {}'.format(action_name))
            return self.ocfretcodes['OCF_ERR_GENERIC']
        else:
            self.ocf_log('ocfLoadModule.action: {} sucessfully'.format(action_name))
            return self.ocfretcodes['OCF_SUCCESS']

    ########################################
    def start(self):
        self.ocf_log('ocfLoadModule.start', msglevel=5)
        try:
            self.initialize()
            if self.status() == self.ocfretcodes['OCF_SUCCESS']:
                self.ocf_log('ocfLoadModule.start {}: alwready loaded'.format(self.get_option('module_name')), msglevel=0)
                return self.ocfretcodes['OCF_SUCCESS']
            else:
                ret = self.action(  'start', \
                                    '{} {} {}'.format(self.get_option('cmd_load_module'), self.get_option('module_name'), self.get_option('module_options')), \
                                    self.get_option('sleepafterstart'), \
                                    self.get_option('pre_start_cmd'), \
                                    self.get_option('sleep_after_pre_start_cmd'), \
                                    self.get_option('post_start_cmd'), \
                                    self.get_option('sleep_after_post_start_cmd'))
                if ret == self.ocfretcodes['OCF_SUCCESS']:
                    self.ocf_log('ocfLoadModule.start {}: loaded sucessfully'.format(self.get_option('module_name')), msglevel=0)
                else:
                    self.ocf_log('ocfLoadModule.start {}: cannot be loaded'.format(self.get_option('module_name')), msglevel=0)
                return ret
        except:
            self.ocf_log_raise('ocfLoadModule.start: error during start')
            return self.ocfretcodes['OCF_ERR_GENERIC']

    ########################################
    def stop(self):
        self.ocf_log('ocfLoadModule.stop', msglevel=5)
        try:
            self.initialize()
            if self.status() == self.ocfretcodes['OCF_NOT_RUNNING']:
                self.ocf_log('ocfLoadModule.stop {}: alwready unloaded'.format(self.get_option('module_name')), msglevel=2)
                return self.ocfretcodes['OCF_NOT_RUNNING']
            else:
                ret = self.action(  'stop', \
                                    '{} {}'.format(self.get_option('cmd_unload_module'), self.get_option('module_name')), \
                                    self.get_option('sleepafterstop'), \
                                    self.get_option('pre_stop_cmd'), \
                                    self.get_option('sleep_after_pre_stop_cmd'), \
                                    self.get_option('post_stop_cmd'), \
                                    self.get_option('sleep_after_post_stop_cmd'))
                if ret == self.ocfretcodes['OCF_NOT_RUNNING']:
                    self.ocf_log('ocfLoadModule.stop {}: unloaded sucessfully'.format(self.get_option('module_name')), msglevel=0)
                else:
                    self.ocf_log('ocfLoadModule.stop {}: cannot be unloaded'.format(self.get_option('module_name')), msglevel=0)
                    return self.ocfretcodes['OCF_ERR_GENERIC']
        except:
            self.ocf_log_raise('ocfLoadModule.stop: error during stop')
            return self.ocfretcodes['OCF_ERR_GENERIC']
        return self.ocfretcodes['OCF_SUCCESS']

    #######################################
    def monitor(self):
        self.ocf_log('ocfLoadModule.monitor', msglevel=5)
        try:
            self.initialize()
            return self.status()
        except Exception:
            self.ocf_log_raise('ocfLoadModule.monitor: error during monitor')
            return self.ocfretcodes['OCF_ERR_GENERIC']

################################################################################
def main():
    try:
        s = ocfLoadModule()
    except ocfError as oe:
        syslog.syslog(syslog.LOG_ERR, oe.strerror)
        sys.exit(oe.err)
    except:
        sys.exit(ocfReturnCodes()['OCF_ERR_GENERIC'])
    else:
        parser = argparse.ArgumentParser (description='Ocf script load kernel module.')
        parser.add_argument ('type', help='Option to launch the ocf script.', action='store', choices=s.choices)
        args = parser.parse_args()
        
        sys.exit(s.run(args.type))

################################################################################
if __name__ == '__main__':
    main()