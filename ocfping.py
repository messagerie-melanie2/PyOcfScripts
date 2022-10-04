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
This script is a python version of the shell script ping OCF RA written by Andrew Beekhof
ocfPing script corosync python
"""

import argparse, os, sys, subprocess, re, syslog, traceback
from ocfscripts import ocfScript, ocfError
from ocfreturncodes import ocfReturnCodes

################################################################################
class ocfPing(ocfScript):
    ########################################
    def __init__(self):
        try:
            super(ocfPing, self).__init__('ocfPing', \
                'This is the ocf script to ping list of hosts.', \
                'Pinging list of hosts.', \
                'ping', \
                '/var/run/ocfping', \
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
                default_ocf_write_pidfile=False, \
                ocf_write_pidfile_is_ra_opt=False, \
                default_monitor_clean_dirty_pidfile=False, \
                monitor_clean_dirty_pidfile_is_ra_opt=False, \
                sleepafterstart_is_ra_opt=False, \
                sleepafterstop_is_ra_opt=False, \
                starttimeoutratio_is_ra_opt=False, \
                start_force_stop_timeout_is_ra_opt=False, \
                process_file_ulimit_is_ra_opt=False, \
                default_status_check_ppid=False, \
                status_check_ppid_is_ra_opt=False, \
                default_status_check_pidfile=False, \
                status_check_pidfile_is_ra_opt=False)
        except:
            raise
        
        # Options supplémentaires
        self.init_from_env('dampen', \
            'The time to wait (dampening) further changes occur. default=5s', \
            'Dampening interval.', \
            default='5s')
        self.init_from_env('name', \
            'The name of the attributes to set.  This is the name to be used in the constraints.', \
            'Attribute name', \
            default='ocfpingd')
        self.init_from_env('multiplier', \
            'The number by which to multiply the number of connected ping nodes by.', \
            'Value multiplier.', \
            default=1, \
            convertfct=self.convert_to_int)
        self.init_from_env('host_list', \
            'The list of ping nodes to count (separated by coma).', \
            'Host list', \
            required=1, \
            convertfct=self.convert_to_list)
        self.init_from_env('attempts', \
            'Number of ping attempts, per host, before declaring it dead.', \
            'Number of ping attemps', \
            default=6, \
            convertfct=self.convert_to_int)
        self.init_from_env('timesend', \
            'Time between ping attempts in seconds.', \
            'time between ping attempts.', \
            default=10, \
            convertfct=self.convert_to_int)
        self.init_from_env('timeout', \
            'How long, in seconds, to wait before declaring a ping lost.', \
            'ping timeout in seconds', \
            default=5, \
            convertfct=self.convert_to_int)
        self.init_from_env('failed', \
            'Number of ping failed to declare ping in error (default=attemps)', \
            'Number of ping failed', \
            default=self.get_option('attempts'), \
            convertfct=self.convert_to_int)
        self.init_from_env('options', \
            'A catch all for any other options that need to be passed to ping', \
            'Extra ping Options', \
            default='')

    ########################################
    def start(self):
        self.ocf_log('ocfPing.start', msglevel=5)
        try:
            self.initialize()
            if self.status() == self.ocfretcodes['OCF_SUCCESS']:
                os.mknod(self.get_option('pidfile'))
        except:
            self.ocf_log_raise('ocfPing.start: error during start')
            return self.ocfretcodes['OCF_ERR_GENERIC']
        else:
            self.ocf_log('ocfPing.start: start sucessfully')
            return self.ocfretcodes['OCF_SUCCESS']
    
    ########################################
    def stop(self):
        self.ocf_log('ocfPing.stop', msglevel=5)
        try:
            self.initialize()
            self.remove_pidfile()
            # TODO attrd_updater
            self.ocf_log('ocfPing.stop: informing cluster with attrd_updater', msglevel=5)
            attrd_updater = subprocess.check_call(["attrd_updater", "-D", "-n", self.get_option('name'), "-d", self.get_option('dampen'), "-q"])
        except subprocess.CalledProcessError as cpe:
            self.ocf_log_raise('ocfPing.status error:{}, command line = {},'.format(cpe.returncode,cpe.cmd))
            return self.ocfretcodes['OCF_ERR_GENERIC']
        except OSError as ose:
            self.ocf_log_raise('ocfPing.status error: {}'.format(ose.strerror))
            return self.ocfretcodes['OCF_ERR_GENERIC']
        except:
            self.ocf_log_raise('ocfPing.stop: error during stop')   
            return self.ocfretcodes['OCF_ERR_GENERIC']
        else:
            self.ocf_log('ocfPing.stop: stop sucessfully')
            return self.ocfretcodes['OCF_SUCCESS']

    ########################################
    def status(self):
        self.ocf_log('ocfPing.status', msglevel=5)
        try:
            re_unreach = re.compile("Destination Host Unreachable")
            re_noanswer = re.compile("no answer yet for icmp_seq")
            ping_args = [self.get_option('binfile'), "-c", "{}".format(self.get_option('attempts')), "-i", "{}".format(self.get_option('timesend')), "-W", "{}".format(self.get_option('timeout')), "-O" ]
            pings = {}
            
            for ip in self.get_option('host_list'):
                try:
                    pargs = list(ping_args)
                    if ":" in ip: pa.append("-6")
                    pargs.append(ip)
                    self.ocf_log('ocfPing.status: pinging {} with {}'.format(ip, pargs), msglevel=5)
                    pings[ip] = subprocess.Popen(pargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                except:
                    self.ocf_log_raise('ocfPing.status: error during ping')
                    raise
            
            self.ocf_log('ocfPing.status: reading pings results', msglevel=5)
            outs = {}
            errs = {}
            active = 0
            for ip in self.get_option('host_list'):
                try:
                    subactive=0
                    pingattempts=0
                    outs[ip], errs[ip] = pings[ip].communicate()
                    lines = outs[ip].split('\n')
                    retline="ping result for {}: ".format(ip)
                    re_resultline = re.compile("bytes from {}".format(ip))
                    re_pingtime = re.compile("\d*? bytes from {}: icmp_seq=\d*? ttl=\d*? time=(.*?) ms".format(ip))
                    for line in lines:
                        if re_unreach.search(line):
                            retline = "{}{}".format("" if not retline else "{} ".format(retline), "-")
                            pingattempts+=1
                        elif re_resultline.search(line):
                            pingattempts+=1
                            pt = re_pingtime.match(line)
                            if pt:
                                retline = "{}{}".format("" if not retline else "{} ".format(retline), pt.group(1))
                                subactive+=1
                            else:
                                self.ocf_log_err('ocfPing.status: unexcepected ping line: {}'.format(line))
                                retline = "{}{}".format("" if not retline else "{} ".format(retline), "?")
                        elif re_noanswer.search(line):
                            retline = "{}{}".format("" if not retline else "{} ".format(retline), "-") 
                            pingattempts+=1
                    else:
                        if pingattempts < self.get_option('attempts'):
                            if pingattempts ==  self.get_option('attempts')-1:
                                retline = "{}{}".format("" if not retline else "{} ".format(retline), "-")
                            else:
                                self.ocf_log_err('ocfPing.status: unexcepected case for ping result: {} attemps with no return'.format(self.get_option('attempts')-pingattempts))
                                for i in range(self.get_option('attempts')-pingattempts):
                                    retline = "{}{}".format("" if not retline else "{} ".format(retline), "!") 
                            
                    if subactive > self.get_option('attempts') - self.get_option('failed'):
                        active+=1
                    self.ocf_log('ocfPing.status: {}'.format(retline), msglevel=1)
                except:
                    self.ocf_log_raise('ocfPing.status: error during reading results')
                    raise
                    
            score = active * self.get_option('multiplier')
            self.ocf_log('ocfPing.status: return score = {}'.format(score), msglevel=3)
            attrd_updater = subprocess.check_call(["attrd_updater", "-n", self.get_option('name'), "-v", "{}".format(score), "-d", self.get_option('dampen'), "-q"])
        except subprocess.CalledProcessError as cpe:
            self.ocf_log_raise('ocfPing.status error:{}, command line = {},'.format(cpe.returncode,cpe.cmd))
            raise
        except OSError as ose:
            self.ocf_log_raise('ocfPing.status error: {}'.format(ose.strerror))
            raise
        except:
            self.ocf_log_raise('ocfPing.status: error during ping.')
            raise
        else:
            return self.ocfretcodes['OCF_SUCCESS']
    
    ########################################
    def monitor(self):
        self.ocf_log('ocfPing.monitor', msglevel=5)
        try:
            self.initialize()
            if os.path.isfile(self.get_option('pidfile')):
                return self.status()
            else:
                return self.ocfretcodes['OCF_NOT_RUNNING']
        except Exception:
            self.ocf_log_raise('ocfChangeRoute.monitor: error during monitor')
            return self.ocfretcodes['OCF_ERR_GENERIC']
    
    ########################################
    def validate(self):
        self.ocf_log('ocfPing.validate', msglevel=5)
        
        try:
            self.configure_pidfile()
            self.validate_ocf_default_options()
            self.validate_opt_number('multiplier', min=1)
            self.validate_opt_number('attempts', min=1)
            self.validate_opt_number('timesend', min=1)
            self.validate_opt_number('timeout', min=1)
            self.validate_opt_number('failed', min=1, max=self.get_option('attempts'))
        except ocfError as oe:
            self.ocf_log_err('Error during validate: {}'.format(oe.strerr))
            ret = oe.err
        else:
            if self.get_option('monlr_nbsearchfail') > self.get_option('monlr_nbsearchrequest'):
                ret = self.ocfretcodes['OCF_ERR_CONFIGURED']
            ret = self.ocfretcodes['OCF_SUCCESS']
            
        return ret

################################################################################
def main():
    try:
        s = ocfPing()
    except ocfError as oe:
        syslog.syslog(syslog.LOG_ERR, oe.strerror)
        sys.exit(oe.err)
    except:
        sys.exit(ocfReturnCodes()['OCF_ERR_GENERIC'])
    else:
        parser = argparse.ArgumentParser (description='Ocf script ping.')
        parser.add_argument ('type', help='Option to launch the ocf script.', action='store', choices=s.choices)
        args = parser.parse_args()
        
        sys.exit(s.run(args.type))

################################################################################
if __name__ == '__main__':
    main()
