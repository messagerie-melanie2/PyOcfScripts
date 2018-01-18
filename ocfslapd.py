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
ocfSlapd script corosync python
nécessite l'installation des module python-ldap, python-psutil
"""

import argparse, sys, os, re, ldap, time, syslog, psutil, signal
from ocfscripts import ocfScript, ocfError
from ocfreturncodes import ocfReturnCodes

################################################################################
class ocfSlapd(ocfScript):
    ########################################
    def __init__(self):
        try:
            super(ocfSlapd, self).__init__('ocfSlapd', \
                'This is the ocf script to manage openldap daemon named slapd', \
                'manage slapd daemon.', \
                '/usr/sbin/slapd', \
                None,\
                binfilesd='Full name of the slapd binary to be executed.', \
                binfileld='The full name of the slapd binary to be executed.', \
                binfileoptionssd='other start options for slapd', \
                binfileoptionsld='other start options for slapd', \
                pidfile_is_ra_opt=False, \
                maxnbprocess_is_ra_opt=False, \
                piddir_owner_is_ra_opt=False, \
                piddir_group_is_ra_opt=False, \
                piddir_mod_is_ra_opt=False, \
                commande_line_searched_is_ra_opt=False, \
                msfileld='file that active/unactivate slapd is in master or slave mode\n/var/run/heartbeat/slapd.master could be a good choice.', \
                msfile_is_ra_opt=True, \
                default_sleepafterstart=10, \
                sleepafterstartld='sleep time before the first monitoring after the process start.\nWarning : 5 seconds seems to be too short for a restart with a stop with a SIGQUIT', \
                default_starttimeoutratio=0.95, \
                default_ocf_write_pidfile=False, \
                default_start_force_stop_timeout=15, \
                default_process_file_ulimit=10000, \
                process_file_ulimitsd='ulimit open file for slapd', \
                process_file_ulimitld='ulimit open file for slapd. minimum is 1024.', \
                autoaction=False)
        except:
            raise
        else:
            self.add_runoption ('start', self.start, timeout=300)
            self.add_runoption ('stop', self.stop, timeout=300)
            self.add_runoption ('restart', self.restart, timeout=600)
            self.add_runoption ('promote', self.promote, timeout=20)
            self.add_runoption ('demote', self.demote, timeout=300)
            self.add_runoption ('meta-data', self.meta, timeout=5)
            self.add_runoption ('metadata', self.meta, timeout=5)
            self.add_runoption ('meta_data', self.meta, timeout=5)
            self.add_runoption ('monitor', self.monitor, timeout=20, interval=10, depth=0, role='Slave')
            self.add_runoption ('monitor', self.monitor, timeout=19, interval=10, depth=0, role='Master')
            self.add_runoption ('monitor', self.monitor, timeout=19, interval=10, depth=0)
            self.add_runoption ('notify', self.notify, timeout=20)
            self.add_runoption ('validate-all', self.validate, timeout=5)
        
        #self.suspend_adv_mon_types = ['none', 'search', 'replic', 'all']
        
        # Options supplémentaires
        self.init_from_env('slapdconf', \
            'configuration file or dir for slapd. For exemples :\n- /etc/ldap/slapd.conf for the old slapd.conf conf style\n- /etc/ldap/slapd.d for the new slapd.d conf style', \
            'configuration file or dir for slapd', \
            default='/etc/ldap/slapd.conf')
        self.init_from_env('slapd_user', 'System account to run the slapd server under', 'System account to run the slapd server under.', default='openldap')
        self.mod_option('piddir_owner', self.get_option('slapd_user'))
        self.init_from_env('slapd_group', 'System group to run the slapd server under.', 'System group to run the slapd server under.', default='openldap')
        self.mod_option('piddir_group', self.get_option('slapd_group'))
        self.init_from_env('slapd_services', \
            'slapd normally serves ldap only on all TCP-ports 389. slapd can also service requests on TCP-port 636 (ldaps) and requests via unix sockets (ldapi).', \
            'slapd listen ports', \
            default='ldap:/// ldaps:///')
        self.init_from_env('start_ldaprequest', \
            'search ldap request to check the start of slapd\nfilter:"filter";base:"search base";scope:"one|base|sub";deref:"always|never|search|find";attrs:"attrs return"\nthe search response must return only one answer.', \
            'search ldap request to check the start of slapd')
        self.init_from_env('startlr_timelimit', \
            'timelimit in seconds for ldap request. minimum is 5 seconds', \
            'timelimit for ldap request', \
            default=20, \
            convertfct=self.convert_to_int)
        self.init_from_env('startlr_timeout', \
            'timeout in seconds for ldap request. minimum is 5 seconds', \
            'timeout for ldap request', \
            default=20, \
            convertfct=self.convert_to_int)
        self.init_from_env('startlr_nettimeout', \
            'network timeout in seconds for ldap request. minimum is 5 seconds', \
            'network timeout for ldap request', \
            default=20, \
            convertfct=self.convert_to_int)
        self.init_from_env('startlr_end', \
            'timeout aflter while start_ldaprequest is replace by mon_ldaprequest\nminimum is 10 secondes', \
            'timeout aflter while start_ldaprequest is replace by mon_ldaprequest', \
            default=270, \
            convertfct=self.convert_to_int)
        self.init_from_env('startlr_checkreturn', \
            'check if an object was found by the request. In other word, if startlr_checkreturn is true and no value was found the request is considered as failed. default=true', \
            'check if an object was found by the request.', \
            default=True, \
            convertfct=self.convert_to_bool)
        self.init_from_env('mon_ldaprequest', \
            'search ldap request to monitor slapd\nfilter:"filter";base:"search base";scope:"one|base|sub";deref:"always|never|search|find";attrs:"attrs return"\nthe search response must return only one answer.', \
            'search ldap request to monitor slapd')
        self.init_from_env('monlr_timelimit', \
            'timelimit in seconds for ldap request. minimum is 5 seconds', \
            'timelimit for ldap request', \
            default=20, \
            convertfct=self.convert_to_int)
        self.init_from_env('monlr_timeout', \
            'timeout in seconds for ldap request. minimum is 5 seconds', \
            'timeout for ldap request', \
            default=20, \
            convertfct=self.convert_to_int)
        self.init_from_env('monlr_nettimeout', \
            'nettimeout in seconds for ldap request. minimum is 5 seconds', \
            'nettimeout for ldap request', \
            default=20, \
            convertfct=self.convert_to_int)
        self.init_from_env('monlr_nbsearchrequest', \
            'number of ldap search request for a single monitoring.\nminimum is 1', \
            'number of ldap search request for a single monitoring', \
            default=10, \
            convertfct=self.convert_to_int)
        self.init_from_env('monlr_nbsearchfail', \
            'number of failed ldap search request for returning an error.\nminimum is 1\nMust be less or equal than monlr_nbsearchrequest', \
            'number of failed ldap search request for returning an error', \
            default=5, \
            convertfct=self.convert_to_int)
        self.init_from_env('monlr_wait', \
            'time in miliseconds to wait between two search request.', \
            'time in miliseconds to wait between two search request.', \
            default=0, \
            convertfct=self.convert_to_int)
        self.init_from_env('monlr_checkreturn', \
            'check if an object was found by the request. In other word, if startlr_checkreturn is true and no value was found the request is considered as failed. default=true', \
            'check if an object was found by the request.', \
            default=True, \
            convertfct=self.convert_to_bool)
        self.init_from_env('status_socket', \
            'path to a status socket. This socket received status information from a program who is doing monitoring that can not be done by the cluster program (for example monitoring load average during several minutes).\n The format is :\nstatus_socket=LIST_SOCKETS\nLIST_DIRS=socket path;socket path;...', \
            'path to a status socket.')
        self.init_from_env('default_status_socket_return', \
            'Value return by status_socket if a problem occure during reading socket. With True, the status will not fail if a probleme occure during reading socket. With False, the status will fail.', \
            'Value return by status_socket if a problem occure during reading socket', \
            default=True, \
            convertfct=self.convert_to_bool)
        self.init_from_env('status_socket_timeout', \
            'timeout for status socket.', \
            'timeout for status socket.', \
            default= 5.0, \
            convertfct=self.convert_to_float)
        self.init_from_env('status_socket_obsolete_data', \
            'time in seconds after which data sent in status socket are obsolete.', \
            'time in seconds after which data sent in status socket are obsolete.', \
            default=150, \
            convertfct=self.convert_to_int)
        self.init_from_env('status_socket_need_all_on_error', \
            'If true, all status_socket must be in error to declare the status in error. If false, a socket in error allows to declare the status in error.', \
            'If true, all status_socket must be in error to declare the status in error.', \
            default=False, \
            convertfct=self.convert_to_bool)
        self.init_from_env('suspend_advanced_mon_socket', \
            'path to a suspend advanced monitoring socket. This socket received suspend advanced monitoring information from a program who want to do some actions not compatible with advanced monitoring actions (search, replication, ...) (for examples : config update, massive ldap update).\n The format is :\nstatus_socket=socket path.', \
            'path to a suspend advanced monitoring socket.')
        self.init_from_env('suspend_advanced_mon_socket_timeout', \
            'timeout for suspend advanced monitoring socket.', \
            'timeout for suspend advanced monitoring socket.', \
            default= 5.0, \
            convertfct=self.convert_to_float)
        self.init_from_env('suspend_advanced_mon_socket_obsolete_data', \
            'time in seconds after which data sent in suspend advance monitoring socket are obsolete.', \
            'time in seconds after which data sent in suspend advance monitoring socket are obsolete.', \
            default=150, \
            convertfct=self.convert_to_int)
        self.init_from_env('suspend_advanced_mon_max_duration', \
            'maximum time in seconds for suspending advanced monitoring. Default is 1800 seconds (30 minutes).', \
            'maximum time in seconds for suspending advanced monitoring.', \
            default=1800, \
            convertfct=self.convert_to_int)
        self.init_from_env('suspend_advanced_mon_file', \
            'path to file to store start timestamp of a suspend advanced monitoring.', \
            'path to file to store start timestamp of a suspend advanced monitoring.', \
            default='/var/run/heartbeat/slapd.suspendavancedmon')
        self.init_from_env('suspend_advanced_mon_type', \
            'advanced type of monitoring that needs to be suspended: TYPE,TYPE. TYPE are "search" for search monitoring and "status" for status socket.', \
            'advanced type of monitoring that needs to be suspended.', \
            default=['search','status'],\
            convertfct=self.convert_to_list)
        self.init_from_env('suspend_advanced_mon_file_error_action', \
            'What to do when file as error:  with True, use information from socket (if any); with False, don\'t use suspend_advanced_mon_*.', \
            'What to do when file as error', \
            default=False, \
            convertfct=self.convert_to_bool)
        self.init_from_env('suspend_advanced_mon_socket_error_action', \
            'What to do when socket as error:  with True, use information from file (if any); with False, don\'t use suspend_advanced_mon_*.', \
            'What to do when socket as error', \
            default=True, \
            convertfct=self.convert_to_bool)
        self.init_from_env('suspend_advanced_mon_stop_clean_file', \
            'Clean the file when slapd is stop.', \
            'Clean the file when slapd is stop.', \
            default=False, \
            convertfct=self.convert_to_bool)
        self.init_from_env('suspend_advanced_mon_inform_remote_program', \
            'If True, inform the remote program the results of the monitoring suspension action.', \
            'If True, inform the remote program the results of the monitoring suspension action.', \
            default=False, \
            convertfct=self.convert_to_bool)
        self.init_from_env('cpu_dead_lock_workaround', \
            'If True, activate a workaround for a cpu dead_lock. During the stop, to determine if the deadlock problem is present, an ldap query with mon_ldaprequest directives is performed.', \
            'If True, activate a workaround for a cpu dead_lock.', \
            default=True, \
            convertfct=self.convert_to_bool)
        self.init_from_env('cdlw_variation_percent', \
            'cdlw_variation_percent: cpu variation percent between two monitoring after the start search monitor. for determining if the workaround must be used.', \
            'cdlw_variation_percent: cpu variation percent.', \
            default=1.5, \
            convertfct=self.convert_to_float)
        self.init_from_env('cdlw_number_of_cpu_tests', \
            'cdlw_number_of_cpu_tests: number of cpu values tested.', \
            'cdlw_number_of_cpu_tests: number of cpu values tested.', \
            default=10, \
            convertfct=self.convert_to_int)
        self.init_from_env('cdlw_wait', \
            'cdlw_wait: time in miliseconds to wait between two cpu test. The values are floats between 0.1 and 1 seconds', \
            'cdlw_wait: time in miliseconds to wait between two cpu test.', \
            default=0.1, \
            convertfct=self.convert_to_float)
        self.init_from_env('cdlw_number_of_values_too_close', \
            'cdlw_number_of_values_too_close: Number of values cpu too close which implies to stop slapd.', \
            'cdlw_number_of_values_too_close: Number of values cpu too close.', \
            default=8, \
            convertfct=self.convert_to_int)
        self.init_from_env('cdlw_min_cpu_average', \
            'cdlw_min_cpu_average: Minimum cpu average to validate the test.', \
            'cdlw_min_cpu_average: Minimum cpu average to validate the test.', \
            default=800, \
            convertfct=self.convert_to_int)
        
    ########################################
    def __parse_pidfile_in_slapdconf(self, file, restr):
        '''
        return first value pidfile find in slapd.conf
        raise ocfError
        '''
        self.ocf_log('ocfSlapd __parse_pidfile_in_slapdconf', msglevel=5)
        try:
            f = open(file, 'r')
        except:
            msg = 'Can\'t read file \"{}\"'.format(file)
            self.ocf_log_err(msg)
            raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], msg)
            
        for line in f:
            if re.match(restr, line):
                strval = re.sub(restr, r'\1', line)
                self.ocf_log('ocfSlapd __parse_pidfile_in_slapdconf : found pidfile {} in slapd configuration'.format(strval), msglevel=4)
                self.mod_option('pidfile', strval)
                break
        else:
            msg = 'Pidfile not found. Pidfile must be define slapd configuration file'
            self.ocf_log_err(msg)
            raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], msg)
        f.close()
        
    ########################################
    def configure_pidfile(self):
        self.ocf_log('ocfSlapd configure_pidfile', msglevel=5)
        
        try:
            # search in slapd configuration for pidfile option
            if os.path.isfile(self.get_option('slapdconf')):
                self.__parse_pidfile_in_slapdconf(self.get_option('slapdconf'), r'^pidfile\s+(.+)\n$')
            elif os.path.isdir(self.get_option('slapdconf')):
                self.__parse_pidfile_in_slapdconf('{}/cn=config.ldif'.format(self.get_option('slapdconf')), r'^olcPidFile:\s+(.+)\s*\n$')
        except:
            raise
  
        try:
            self.init_pidfile()
        except:
            raise
    
    ########################################
    def __searchparams(self, strval):
        '''
        strval = search ldap request to check for monitoring slapd
        search ldap request to monitor slapd
        filter:"filter";base:"search base";scope:"one|base|sub";deref:"always|never|search|find";attrs:"attrs return"
        the search response must return only one answer.
        '''
        #TODO verifier les valeurs des reponses
        self.ocf_log('ocfSlapd.__searchparams', msglevel=5)
        sp = {}
        params = strval.split(';')
        for param in params:
            p = param.split(':')
            self.ocf_log('ocfSlapd.__searchparams {} : {}'.format(p[0], p[1]), msglevel=5)
            if p[0] in ('filter', 'base'):
                sp[p[0]] = p[1]
            elif p[0] == 'scope':
                if p[1] == 'base': sp[p[0]] = ldap.SCOPE_BASE
                elif p[1] == 'one': sp[p[0]] = ldap.SCOPE_ONELEVEL
                elif p[1] == 'sub': sp[p[0]] = ldap.SCOPE_SUBTREE
                else:
                    msg = 'scope {} in {} does not exist '.format(p[1], param)
                    self.ocf_log_err(msg)
                    raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], msg)
            elif p[0] == 'deref':
                if p[1] == 'always': sp[p[0]] = ldap.DEREF_ALWAYS
                elif p[1] == 'search': sp[p[0]] = ldap.DEREF_SEARCHING
                elif p[1] == 'find': sp[p[0]] = ldap.DEREF_FINDING
                elif p[1] == 'never': sp[p[0]] = ldap.DEREF_NEVER
                else:
                    msg = 'deref {} in {} does not exist '.format(p[1], param)
                    self.ocf_log_err(msg)
                    raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], msg)
            elif p[0] == 'attrs':
                 sp[p[0]] = p[1].split(' ')
            else:
                msg = 'Configuration Error : {} option does not exist '.format(p[0])
                self.ocf_log_err(msg)
                raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], msg)
        
        hk = sp.keys()
        for i in ('filter', 'base', 'scope', 'deref'):
            if i not in hk:
                msg = 'searchparams {} does not have {} '.format(params, i)
                self.ocf_log_err(msg)
                raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], msg)
        
        self.ocf_log('ocfSlapd.__searchparams : base:\"{}\" scope:\"{}\" filter:\"{}\" attrs:\"{}\" deref:\"{}\"'.format(sp['base'], sp['scope'], sp['filter'], sp['attrs'], sp['deref']), msglevel=4)
        return sp

    ########################################
    def __validate_searchparams(self, strval):
        self.ocf_log('ocfSlapd.__validate_searchparams', msglevel=5)
        try:
            self.__searchparams(strval)
        except:
            raise

    ########################################
    def __slapd_search_monitor(self, strval, timelimit=20, timeout=20, nettimeout=20, checkreturn=True):
        self.ocf_log('ocfSlapd.__slapd_search_monitor', msglevel=5)
        try:
            sp = self.__searchparams(strval)
        except ocfError as oe:
            self.ocf_log_err('bad ldap request options {}'.format(oe.strerr))
            raise
        
        self.ocf_log('ocfSlapd.__slapd_search_monitor : initialize and bind to ldap', msglevel=4)
        try:
            l = ldap.initialize('ldap://127.0.0.1')
            l.protocol_version = ldap.VERSION3
            l.set_option(ldap.OPT_TIMELIMIT, timelimit)
            l.set_option(ldap.OPT_TIMEOUT, timeout)
            l.set_option(ldap.OPT_NETWORK_TIMEOUT, nettimeout)
            l.set_option(ldap.OPT_DEREF, sp['deref'])
            l.simple_bind()
        except ldap.LDAPError, e:
            self.ocf_log_err('Can\'t connect ldap server : {}'.format(e.message['desc']))
            raise
        
        self.ocf_log('ocfSlapd.__slapd_search_monitor : search with base:\"{}\" scope:\"{}\" filter:\"{}\" attrs:\"{}\" deref:\"{}\"{}'.format(sp['base'], sp['scope'], sp['filter'], sp['attrs'], sp['deref'], ' with timelimit={}'.format(timelimit) if timelimit else ''), msglevel=4)
        try:
            res = l.search_s(sp['base'], sp['scope'], sp['filter'], sp['attrs'])
        except ldap.LDAPError, e:
            self.ocf_log_err('ldap search error : {}'.format(e.message['desc']))
            raise
        else:
            if checkreturn and len(res) == 0:
                msg = 'No entry found for base:\"{}\" scope:\"{}\" filter:\"{}\" attrs:\"{}\" deref:\"{}\"{}'.format(sp['base'], sp['scope'], sp['filter'], sp['attrs'], sp['deref'], ' with timelimit={}'.format(timelimit) if timelimit else '')
                self.ocf_log_err(msg)
                raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
        finally:
            l.unbind_s()
        
        # TODO : verify search response (description of for search en response in an ldif file ?)

    ########################################
    def is_suspend_advanced_mon_time_over(self, nowts, startts, suspendtime):
        # suspendtime is in secondes
        return True if nowts >= (startts+suspendtime) else False
    
    ########################################
    def suspend_advanced_mon_convert_values(self, valfrom, tab, msgend, fail_on_duration_err=False):
        dic = {}
        try:
            dic['state'] = int(tab[0])
            dic['timestamp'] = float(tab[1])
            if tab[2]: dic['duration'] = int(tab[2])
            else: dic['duration'] = 0
            dic['type'] = tab[3].rstrip(',').split(',')
            dic['msgend'] = tab[4]
        except:
            self.ocf_log_warn('suspend advanced monitoring: {} as incorrect value for state, timestamp or duration: {}.'.format(valfrom, tab))
            dic = {}
        else:
            if dic['state'] not in [0,1]:
                self.ocf_log_warn('suspend advanced monitoring: {} as incorrect value for state: {}.'.format(valfrom, dic['state']))
                dic = {}
            elif dic['state'] == 0 and not set(self.get_option('suspend_advanced_mon_type')) >= set(dic['type']):
                self.ocf_log_warn('suspend monitor socket: {} as incorrect value for type {} vs {}.'.format(valfrom, dic['type'], self.get_option('suspend_advanced_mon_type')))
                dic = {}
            elif dic['msgend'] != msgend:
                self.ocf_log_warn('suspend monitor socket: {} as incorrect value for msgend {}.'.format(valfrom, dic['msgend']))
                dic = {}
            elif dic['duration'] > self.get_option('suspend_advanced_mon_max_duration'):
                if fail_on_duration_err:
                    self.ocf_log_warn('suspend monitor socket: suspended time too large ({})'.format(dic['duration']))
                    dic = {}
                else:
                    self.ocf_log_warn('suspend monitor socket: suspended time too large ({}), setting it to {}'.format(dic['duration'], self.get_option('suspend_advanced_mon_max_duration')))
                    dic['duration'] = self.get_option('suspend_advanced_mon_max_duration')

        return dic

    ########################################
    def suspend_advanced_mon_send_result_remote_program(self, sock, actionres, msgend):
        if self.get_option('suspend_advanced_mon_inform_remote_program'):
            msg='{}:{}'.format(actionres, msgend)
            self.ocf_log('ocfSldapd.suspend_advanced_mon_send_result_remote_program, sending message \"{}\"'.format(msg), msglevel=4)
            try:
                sock.sendall(msg)
            except:
                self.ocf_log_warn('suspend monitor socket problem sending action result data')
            finally:
                sock.close()
        return None

    ########################################
    def read_suspend_advanced_mon(self):
        '''
        data line is state(0):timestamp(1):suspended time duration(2):suspend_advanced_mon_type(3):msgend(4)
        suspended time is in seconds
        state=0 : suspending
        state=1 : activating
        '''
        # TODO try/catch sur float() et int()
        self.ocf_log('ocfSlapd.read_suspend_advanced_mon', msglevel=5)
        suspend_advanced_mon = []
        msgend = 'state-end'
        if self.get_option('suspend_advanced_mon_socket'):
            self.ocf_log('ocfSlapd.read_suspend_advanced_mon suspend_advanced_mon_socket: {}'.format(self.get_option('suspend_advanced_mon_socket')), msglevel=4)
            # reads the "socket" for the calling program does not remain pending.
            sdata,sock = self.read_suspend_monitor_socket(self.get_option('suspend_advanced_mon_socket'), stimeout=self.get_option('suspend_advanced_mon_socket_timeout'), msgend=msgend, let_socket_open=self.get_option('suspend_advanced_mon_inform_remote_program'), msg_wait='wait-result')
            nowts = time.time()
            
            # file
            fdic = {}
            if os.path.exists(self.get_option('suspend_advanced_mon_file')):
                self.ocf_log('ocfSlapd.read_suspend_advanced_mon opening file: {}'.format(self.get_option('suspend_advanced_mon_file')), msglevel=5)
                with open(self.get_option('suspend_advanced_mon_file'), 'r') as sf:
                    flines = sf.readlines()
                    if len(flines) == 1:
                        fdic = self.suspend_advanced_mon_convert_values(self.get_option('suspend_advanced_mon_file'), flines[0].split(':'), msgend, fail_on_duration_err=True)
                    else:
                        self.ocf_log_warn('suspend advanced monitoring: {} as incorrect number of line {}.'.format(self.get_option('suspend_advanced_mon_file'), len(flines)))
                        
                if not fdic or len(flines) != 1:
                    self.ocf_log_warn('suspend advanced monitoring: {} is incorrect : removing it.'.format(self.get_option('suspend_advanced_mon_file')))
                    os.remove(self.get_option('suspend_advanced_mon_file'))
                    if not self.get_option('suspend_advanced_mon_file_error_action'):
                        self.ocf_log('ocfSlapd.read_suspend_advanced_mon, aborting suspend advanced monitoring.', msglevel=2)
                        if sock: self.suspend_advanced_mon_send_result_remote_program(sock, False, msgend)
                        return suspend_advanced_mon
                    
                if self.is_suspend_advanced_mon_time_over(nowts, fdic['timestamp'], fdic['duration']):
                    self.ocf_log('ocfSlapd.read_suspend_advanced_mon {}, time {} from file {} is over. Removing file.'.format(self.get_option('suspend_advanced_mon_socket'), fdic['duration'], self.get_option('suspend_advanced_mon_file')), msglevel=4)
                    os.remove(self.get_option('suspend_advanced_mon_file'))
                    if fdic['duration'] == self.get_option('suspend_advanced_mon_max_duration'):
                        self.ocf_log('ocfSlapd.read_suspend_advanced_mon {}, max time {} is reach. Adding time is not allowed. '.format(self.get_option('suspend_advanced_mon_socket'), self.get_option('suspend_advanced_mon_max_duration')), msglevel=4)
                        if sock: self.suspend_advanced_mon_send_result_remote_program(sock, False, msgend)
                        return suspend_advanced_mon
                else:
                    self.ocf_log('ocfSlapd.read_suspend_advanced_mon file {} give: {}'.format(self.get_option('suspend_advanced_mon_file'), fdic), msglevel=5)
                    suspend_advanced_mon = fdic['type']
            
            # socket
            if sdata:
                sdic = self.suspend_advanced_mon_convert_values(self.get_option('suspend_advanced_mon_socket'), sdata.split(':'), msgend)
                if sdic:
                    if not self.get_option('suspend_advanced_mon_socket_obsolete_data') or nowts < sdic['timestamp']+self.get_option('suspend_advanced_mon_socket_obsolete_data'):
                        if sdic['state'] == 0:
                            self.ocf_log('ocfSlapd.read_suspend_advanced_mon {}, suspend monitor socket said that monitoring must be suspended'.format(self.get_option('suspend_advanced_mon_socket')), msglevel=2)
                            if not fdic:
                                # if there is no file information
                                startts = sdic['timestamp']
                                suspend_advanced_mon = sdic['type']
                                suspend_time = sdic['duration']
                            else:
                                # if file information exist
                                startts = fdic['timestamp']
                                suspend_advanced_mon = list(set(fdic['type'])|set(sdic['type'])) # take union of two
                                if fdic['duration']+sdic['duration'] > self.get_option('suspend_advanced_mon_max_duration'):
                                    suspend_time = self.get_option('suspend_advanced_mon_max_duration')
                                    self.ocf_log('ocfSlapd.read_suspend_advanced_mon {}: suspended time too large ({}+{}), adding {}'.format(self.get_option('suspend_advanced_mon_socket'), fdic['duration'], sdic['duration'], self.get_option('suspend_advanced_mon_max_duration')-fdic['duration']), msglevel=2)
                                else:
                                    suspend_time = fdic['duration']+sdic['duration']
                                    self.ocf_log('ocfSlapd.read_suspend_advanced_mon {}: adding {} for a total duration of {}'.format(self.get_option('suspend_advanced_mon_socket'), sdic['duration'], suspend_time), msglevel=2)
                            with open(self.get_option('suspend_advanced_mon_file'), 'w') as sf:
                                sf.write('0:{}:{}:{}:{}'.format(startts, suspend_time, ','.join(suspend_advanced_mon), msgend))
                                # TODO write try/catch ?
                        elif sdic['state'] == 1:
                            self.ocf_log('ocfSlapd.read_suspend_advanced_mon {}, suspend monitor socket said that monitoring must be reactivated'.format(self.get_option('suspend_advanced_mon_socket')), msglevel=2)
                            suspend_advanced_mon = []
                            if os.path.exists(self.get_option('suspend_advanced_mon_file')):
                                self.ocf_log('ocfSlapd.read_suspend_advanced_mon {}, removing file {}'.format(self.get_option('suspend_advanced_mon_socket'), self.get_option('suspend_advanced_mon_file')), msglevel=4)
                                os.remove(self.get_option('suspend_advanced_mon_file'))
                        else:
                            self.ocf_log_warn('suspend advanced monitoring {} send incorrect data'.format(self.get_option('suspend_advanced_mon_socket')))
                            if sock: sock=self.suspend_advanced_mon_send_result_remote_program(sock, False, msgend)
                    else:
                        self.ocf_log_warn('suspend monitor socket {}: data too old'.format(self.get_option('suspend_advanced_mon_socket')))
                        if sock: sock=self.suspend_advanced_mon_send_result_remote_program(sock, False, msgend)
                else:
                    self.ocf_log_warn('suspend monitor socket {} send incorrect data'.format(self.get_option('suspend_advanced_mon_socket')))
                    if sock: sock=self.suspend_advanced_mon_send_result_remote_program(sock, False, msgend)
                    if not self.get_option('suspend_advanced_mon_socket_error_action'):
                        self.ocf_log('ocfSlapd.read_suspend_advanced_mon, aborting suspend advanced monitoring.', msglevel=2)
                        suspend_advanced_mon = []
            
            if sock: self.suspend_advanced_mon_send_result_remote_program(sock, True, msgend)

        return suspend_advanced_mon

    ########################################
    def workaround_cpu_dead_lock(self):
        self.ocf_log('ocfSlapd.workaround_start_cpu_dead_lock', msglevel=5)
        try:
            slapdproc = None
            for proc in psutil.process_iter():
                if psutil.pid_exists(proc.pid) and self.get_option('binfile') in proc.cmdline()[:2] and proc.ppid() == 1:
                    if slapdproc:
                        msg = 'Two slapd process founf at pid {} and pid {}.'.format(slapdproc.pid, proc.pid)
                        self.ocf_log_err(msg)
                        raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
                    else:
                        # slapd pid is found
                        slapdproc = proc
                        cputests = []
                        slapdproc.cpu_percent() # The first run cpu_percent return always 0.0. Need a run to initialized it.
                        time.sleep(self.get_option('cdlw_wait'))
                        # geting cpu values
                        for i in range(self.get_option('cdlw_number_of_cpu_tests')):
                            if psutil.pid_exists(slapdproc.pid):
                                cputests.append(slapdproc.cpu_percent())
                            else:
                                msg = 'slapd pid {} is dead during workaround.'.format(slapdproc.pid)
                                self.ocf_log_err(msg)
                                raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
                            time.sleep(self.get_option('cdlw_wait'))
                        # verifying who many values are too close from the cpu average
                        cpuaverage = sum(cputests)/self.get_option('cdlw_number_of_cpu_tests')
                        if cpuaverage > self.get_option('cdlw_min_cpu_average'):
                            cpumax = cpuaverage*(100+self.get_option('cdlw_variation_percent'))/100
                            cpumin = cpuaverage*(100-self.get_option('cdlw_variation_percent'))/100
                            nbcloseaverage = 0
                            for ct in cputests:
                                if ct > cpumin and ct < cpumax:
                                    nbcloseaverage += 1
                            self.ocf_log('ocfSlapd.workaround_start_cpu_dead_lock: {} values close to average on {} needed to fail and {} tested values'.format(nbcloseaverage, self.get_option('cdlw_number_of_values_too_close'), self.get_option('cdlw_number_of_cpu_tests')), msglevel=1)
                            if nbcloseaverage >= self.get_option('cdlw_number_of_values_too_close'):
                                return self.ocfretcodes['OCF_ERR_GENERIC']
                        else:
                            self.ocf_log('ocfSlapd.workaround_start_cpu_dead_lock: cpu average {} is under {}'.format(cpuaverage, self.get_option('cdlw_min_cpu_average')), msglevel=5)
        except psutil.NoSuchProcess as err:
            self.ocf_log('ocfSlapd.workaround_start_cpu_dead_lock: {}'.format(err), msglevel=5)
            raise
        except:
            self.ocf_log('ocfSlapd.workaround_start_cpu_dead_lock: {}'.format(sys.exc_info()), msglevel=5)
            raise
        return self.ocfretcodes['OCF_SUCCESS']

    ########################################
    def status_start(self, clean_dirty_pidfile=False, with_status_inherit=True):
        self.ocf_log('ocfSlapd.status_start with clean_dirty_pidfile={}'.format(clean_dirty_pidfile), msglevel=5)
        sret = super(ocfSlapd, self).status_start(clean_dirty_pidfile=clean_dirty_pidfile)
        if (sret == self.ocfretcodes['OCF_SUCCESS'] or sret == self.ocfretcodes['OCF_RUNNING_MASTER']) and self.get_option('start_ldaprequest'):
            try:
                ipjs = self.is_process_just_start(self.get_option('startlr_end'), check_ppid=self.get_option('status_check_ppid_for_start'))
            except:
                return self.status_error('ocfSlapd.status_start, error when verifing process launch time.')
            
            if ipjs:
                # only one iteration : start_ldaprequest is used by start and ocfscirpt.start do a loop
                self.ocf_log('ocfSlapd.status_start start_ldaprequest', msglevel=3)
                try:
                    self.__slapd_search_monitor(self.get_option('start_ldaprequest'), timelimit=self.get_option('startlr_timelimit'), timeout=self.get_option('startlr_timeout'), nettimeout=self.get_option('startlr_nettimeout'), checkreturn=self.get_option('startlr_checkreturn'))
                except:
                    return self.status_error('ocfSlapd.status_start, Test time {} of my_ldaprequest exceeded.'.format(self.get_option('startlr_end')))
                else:
                    self.ocf_log('ocfSlapd.status_start, search start monitoring request ok.', msglevel=2)
            else:
                return self.status_error('ocfSlapd.status_start, search monitor has failed.')
        return sret
    
    ########################################
    def status_stop(self, clean_dirty_pidfile=False, with_status_inherit=True):
        self.ocf_log('ocfSlapd.status_stop with clean_dirty_pidfile={}'.format(clean_dirty_pidfile), msglevel=5)
        sret = super(ocfSlapd, self).status_stop(clean_dirty_pidfile=clean_dirty_pidfile)
        if (sret == self.ocfretcodes['OCF_SUCCESS'] or sret == self.ocfretcodes['OCF_RUNNING_MASTER']) and self.get_option('cpu_dead_lock_workaround') and self.get_option('mon_ldaprequest'):
            # Only one iteration to check if slapd answers or not
            self.ocf_log('ocfSlapd.status_stop ldap request for cpu_dead_lock_workaround', msglevel=3)
            try: 
                self.__slapd_search_monitor(self.get_option('mon_ldaprequest'), timelimit=self.get_option('monlr_timelimit'), timeout=self.get_option('monlr_timeout'), nettimeout=self.get_option('monlr_nettimeout'), checkreturn=self.get_option('monlr_checkreturn'))
            except:
                return self.status_error('ocfSlapd.status_stop, search monitor has failed.')
            else:
                    self.ocf_log('ocfSlapd.status_stop, search stop monitoring request ok.', msglevel=2)
        return sret
    
    ########################################
    def status_monitor(self, clean_dirty_pidfile=False, with_status_inherit=True):
        self.ocf_log('ocfSlapd.status_monitor with clean_dirty_pidfile={}'.format(clean_dirty_pidfile), msglevel=5)
        sret = super(ocfSlapd, self).status_monitor(clean_dirty_pidfile=clean_dirty_pidfile)
        if (sret == self.ocfretcodes['OCF_SUCCESS'] or sret == self.ocfretcodes['OCF_RUNNING_MASTER']) and self.get_option('mon_ldaprequest'):
            suspend_advanced_mon = self.read_suspend_advanced_mon()
            if 'search' in suspend_advanced_mon:
                self.ocf_log('ocfSlapd.status_monitor: mon_ldaprequest is suspended by suspend_advanced_mon_socket', msglevel=2)
            else:
                self.ocf_log('ocfSlapd.status_monitor mon_ldaprequest : begining {} ldap request, error if {} fail'.format(self.get_option('monlr_nbsearchrequest'), self.get_option('monlr_nbsearchfail')), msglevel=3)
                nb_fail = 0
                for i in range(self.get_option('monlr_nbsearchrequest')):
                    self.ocf_log('ocfSlapd.status_monitor mon_ldaprequest : request number={}, number of failed={}'.format(i+1, nb_fail), msglevel=4)
                    try: 
                        self.__slapd_search_monitor(self.get_option('mon_ldaprequest'), timelimit=self.get_option('monlr_timelimit'), timeout=self.get_option('monlr_timeout'), nettimeout=self.get_option('monlr_nettimeout'), checkreturn=self.get_option('monlr_checkreturn'))
                    except:
                        nb_fail += 1
                        self.ocf_log('ocfSlapd.status_monitor mon_ldaprequest failed : request number={}, number of failed={}'.format(i+1, nb_fail), msglevel=3)
                        if nb_fail >= self.get_option('monlr_nbsearchfail'):
                            return self.status_error('ocfSlapd.status_monitor, search monitor has failed.')
                        elif self.get_option('cpu_dead_lock_workaround'):
                            if self.workaround_cpu_dead_lock() == self.ocfretcodes['OCF_ERR_GENERIC']:
                                return self.status_error('ocfSlapd.status_monitor, cpu_dead_lock_workaround returned an error.')
                    finally:
                        if self.get_option('monlr_wait') > 0 and i < self.get_option('monlr_nbsearchrequest')-1:
                            self.ocf_log('ocfSlapd.status_monitor mon_ldaprequest : waiting {} ms'.format(self.get_option('monlr_wait')), msglevel=4)
                            time.sleep(self.get_option('monlr_wait')/1000.0)
                else:
                    self.ocf_log('mon_ldaprequest success : on {} requests, {} have failed on {} needed for failure'.format(self.get_option('monlr_nbsearchrequest'), nb_fail, self.get_option('monlr_nbsearchfail')), msglevel=2)
            if 'status' in suspend_advanced_mon:
                self.ocf_log('ocfSlapd.status_monitor : status_socket is suspended by suspend_advanced_mon_socket', msglevel=2)
            else:
                if self.get_option('status_socket'):
                    self.ocf_log('ocfSlapd.status_monitor status_socket', msglevel=4)
                    if not self.read_all_status_sockets(self.get_option('status_socket'), default_return=self.get_option('default_status_socket_return'), stimeout=self.get_option('status_socket_timeout'), need_all_false=self.get_option('status_socket_need_all_on_error'), obsolete_data=self.get_option('status_socket_obsolete_data')):
                        return self.status_error('ocfSlapd.status_monitor, status sockets return a failed state.')
        return sret

    ########################################
    def start_status_loop(self, statusfct, start_time, force_stop):
        self.ocf_log('ocfSlapd.start_status_loop', msglevel=5)
        start_timeout = self.calc_timeout(ratio=self.get_option('starttimeoutratio')/1000, default_timeout=285)
        if self.get_option('start_force_stop_timeout') and force_stop:
            tmp_timeout = start_timeout - self.get_option('start_force_stop_timeout')
            start_timeout = tmp_timeout if tmp_timeout > 0 else start_timeout
        self.ocf_log('ocfScript.start_status_loop  : start timeout is {}'.format(start_timeout), msglevel=4)
        while time.time() - start_time < start_timeout:
            self.ocf_log('ocfSlapd.start_status_loop waiting {} seconds...'.format(self.get_option('sleepafterstart')), msglevel=3)
            time.sleep(self.get_option('sleepafterstart'))
            if statusfct() == self.ocfretcodes['OCF_SUCCESS']:
                self.ocf_log('started successfully.')
                return self.ocfretcodes['OCF_SUCCESS']
            elif self.get_option('cpu_dead_lock_workaround'):
                if self.workaround_cpu_dead_lock() == self.ocfretcodes['OCF_ERR_GENERIC']:
                    self.ocf_log('ocfSlapd.start_status_loop, cpu_dead_lock_workaround returned an error.', msglevel=3)
                    return self.ocfretcodes['OCF_ERR_GENERIC']
        else:
            self.ocf_log_err('Could not be started.')
            return self.ocfretcodes['OCF_ERR_GENERIC']

    ########################################
    def start(self):
        self.ocf_log('ocfSlapd.start', msglevel=5)
        try:
            self.initialize()
        except ocfError as oe:
            return oe.err
        
        startopts= ['-h', self.get_option('slapd_services'), \
            '-g', self.get_option('slapd_group'), \
            '-u', self.get_option('slapd_user')]
        if os.path.isdir(self.get_option('slapdconf')):
            startopts.append('-F')
        else:
            startopts.append('-f')
        startopts.append(self.get_option('slapdconf'))
        
        return super(ocfSlapd, self).start(otheropts=startopts)
    
    ########################################
    def stop(self, force_timeout=None):
        self.ocf_log('ocfSlapd.stop with force_timeout={}'.format(force_timeout), msglevel=5)
        try:
            self.initialize()
        except ocfError as oe:
            return oe.err
        
        if self.get_option('suspend_advanced_mon_socket') and self.get_option('suspend_advanced_mon_stop_clean_file') and os.path.exists(self.get_option('suspend_advanced_mon_file')):
            self.ocf_log('ocfSlapd.stop, removing file {}'.format(self.get_option('suspend_advanced_mon_file')), msglevel=4)
            os.remove(self.get_option('suspend_advanced_mon_file'))
        if self.get_option('cpu_dead_lock_workaround'):
            sret = self.status_stop(clean_dirty_pidfile=self.get_option('monitor_clean_dirty_pidfile'))
            if not (sret == self.ocfretcodes['OCF_SUCCESS'] or sret == self.ocfretcodes['OCF_RUNNING_MASTER']):
                if self.workaround_cpu_dead_lock() == self.ocfretcodes['OCF_ERR_GENERIC']:
                    return super(ocfSlapd, self).stop(with_status_inherit=False, force_timeout=self.get_option('start_force_stop_timeout'))
        return super(ocfSlapd, self).stop(with_status_inherit=False, force_timeout=force_timeout)
    
    ########################################
    def demote(self):
        self.ocf_log('ocfSlapd.demote', msglevel=5)
        try:
            self.initialize()
            msret = self.read_msfile()
        except ocfError as oe:
            return oe.err
        
        if msret == self.master:
            super(ocfSlapd, self).demote()
            if self.notify_infos.n_demote and self.nodename in self.notify_infos.n_demote and self.notify_infos.n_promote:
                self.ocf_log('ocfSlapd.demote: demote before promote, stopping slapd', msglevel=1)
                return self.stop()

        return self.ocfretcodes['OCF_SUCCESS']
    
    ########################################
    def __validate_slapd_services(self):
        self.ocf_log('ocfSlapd.__validate_slapd_services', msglevel=5)
        
        type = ('ldap', 'ldaps', 'ldapi')
        services = self.get_option('slapd_services').split()
        for s in services:
            st = s[0].split('://', 1)
            if st not in type:
                msg = '{} slap service does not exist '.format(st)
                self.ocf_log_err(msg)
                raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], msg)
            
            #TODO control service construction
    
    ########################################
    def validate(self):
        self.ocf_log('ocfSlapd.validate', msglevel=5)
        
        try:
            self.configure_pidfile()
            self.validate_ocf_default_options()
            self.__validate_searchparams( self.get_option('start_ldaprequest'))
            self.__validate_searchparams( self.get_option('mon_ldaprequest'))
            self.__validate_slapd_services()
            self.validate_opt_user('slapd_user')
            self.validate_opt_group('slapd_group')
            self.validate_opt_number('startlr_end', min=10)
            self.validate_opt_number('startlr_timelimit', min=5)
            self.validate_opt_number('startlr_timeout', min=5)
            self.validate_opt_number('startlr_nettimeout', min=5)
            self.validate_opt_bool('startlr_checkreturn')
            self.validate_opt_number('monlr_timelimit', min=5)
            self.validate_opt_number('monlr_timeout', min=5)
            self.validate_opt_number('monlr_nettimeout', min=5)
            self.validate_opt_number('monlr_nbsearchrequest', min=1)
            self.validate_opt_number('monlr_nbsearchfail', min=1)
            self.validate_opt_number('monlr_wait', min=0)
            self.validate_opt_bool('monlr_checkreturn')
            self.validate_read_access(self.get_option('slapdconf'), self.get_option('slapd_user'), self.get_option('slapd_group'))
            # TODO status_socket
            self.validate_opt_bool('default_status_socket_return')
            self.validate_opt_number('status_socket_timeout', nbrtype=float, min=1.0)
            self.validate_opt_number('status_socket_obsolete_data', min=1)
            self.validate_opt_bool('status_socket_need_all_on_error')
            # TODO suspend_advanced_mon_socket
            self.validate_opt_number('suspend_advanced_mon_socket_timeout', nbrtype=float, min=1.0)
            self.validate_opt_number('suspend_advanced_mon_socket_obsolete_data', min=1)
            self.validate_opt_number('suspend_advanced_mon_max_duration', min=1)
            self.validate_opt_list('suspend_advanced_mon_type', ['search', 'status'])
            self.validate_opt_bool('suspend_advanced_mon_file_error_action')
            self.validate_opt_bool('suspend_advanced_mon_socket_error_action')
            self.validate_opt_bool('suspend_advanced_mon_stop_clean_file')
            self.validate_opt_bool('suspend_advanced_mon_inform_remote_program')
            self.validate_opt_bool('cpu_dead_lock_workaround')
            self.validate_opt_number('cdlw_variation_percent', nbrtype=float, min=0.0)
            self.validate_opt_number('cdlw_number_of_cpu_tests', min=1)
            self.validate_opt_number('cdlw_wait', nbrtype=float, min=0.1, max=1.0)
            self.validate_opt_number('cdlw_number_of_values_too_close', min=1)
            self.validate_opt_number('cdlw_min_cpu_average', min=100)
            
        except ocfError as oe:
            self.ocf_log_err('Error during validate: {}'.format(oe.strerr))
            ret = oe.err
        except KeyError as ke:
            self.ocf_log_err('Error during validate: {}'.format(ke))
            ret = self.ocfretcodes['OCF_ERR_CONFIGURED']
        except ValueError as ve:
            self.ocf_log_err('Error during validate: {}'.format(ve))
            ret = self.ocfretcodes['OCF_ERR_CONFIGURED']
        else:
            if self.get_option('monlr_nbsearchfail') > self.get_option('monlr_nbsearchrequest'):
                ret = self.ocfretcodes['OCF_ERR_CONFIGURED']
            ret = self.ocfretcodes['OCF_SUCCESS']
        
        return ret

    ########################################
    def initialize(self):
        '''
        surcharge de la fonction initialize de ocfscripts à cause de la nécessité d'appeller configure_pidfile qui appel init_pidfile
        '''
        self.ocf_log('ocfSlapd.initialize', msglevel=5)
        try:
            self.configure_pidfile()
            self.fixdirs()
            if self.get_option('msfile'): self.init_dir(os.path.dirname(self.get_option('msfile')))
            self.infonotify()
        except:
            msg = 'Error during ocfSlapd initialize (see previous error log)'
            self.ocf_log_err(msg)
            raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)

    ########################################
    def notify(self):
        self.ocf_log('ocfSlapd.notify', msglevel=5)
        super(ocfSlapd, self).notify()

        if self.notify_infos.n_type and self.notify_infos.n_type =='pre' and self.notify_infos.n_op and self.notify_infos.n_op == 'promote' and self.status() == self.ocfretcodes['OCF_NOT_RUNNING']:
            self.ocf_log('ocfSlapd.notify pre promote action : starting slapd', msglevel=1)
            return self.start()
        
        return self.ocfretcodes['OCF_SUCCESS']

################################################################################
def main():
    try:
        s = ocfSlapd()
    except ocfError as oe:
        syslog.syslog(syslog.LOG_ERR, oe.strerror)
        sys.exit(oe.err)
    except:
        sys.exit(ocfReturnCodes()['OCF_ERR_GENERIC'])
    else:
        parser = argparse.ArgumentParser (description='script ocf openldap')
        parser.add_argument ('type', help='Option to launch the ocf script.', action='store', choices=s.choices)
        args = parser.parse_args()
        
        sys.exit(s.run(args.type))

################################################################################
if __name__ == '__main__':
    main()
