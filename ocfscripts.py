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
ocf script function for corosync python
nécessite l'installation des module python-psutil
"""

import os, psutil, syslog, locale, subprocess, pwd, grp, time, stat, signal, socket, resource
from ocfreturncodes import ocfReturnCodes

################################################################################
class ocfError(Exception):
    def __init__(self, value, strval):
        self.err = value
        self.strerror = strval
    
################################################################################
class ocfOption():
    '''
    This class define a script option for ocf script
    '''
    ########################################
    def __init__(self, envname=None, value=None):
        self.envname = envname
        self.value = value
    
    ########################################
    def set(self, envname, value):
        self.envname = envname
        self.value = value
    
    ########################################
    def mod(self, value, envname=None):
        self.value = value
        if envname:
            self.envname = envname
            

################################################################################
class ocfNotifyInfo():
    '''
    This class define Information from Notify call
    '''
    ########################################
    def __init__(self):
        self.n_type = None
        self.n_op = None
        self.n_active = None
        self.n_stop = None
        self.n_start = None
        self.n_master = None
        self.n_promote = None
        self.n_demote = None

################################################################################
class ocfMetaParams():
    '''
    This class define parameter for ocf script meta section
    '''
    ########################################
    def __init__ (self, name, longdesc, shortdesc, required, unique, ldlang, sdlang, default ):
        self.name = name
        self.longdesc = longdesc
        self.shortdesc= shortdesc
        self.required = required
        self.unique = unique
        self.ldlang = ldlang
        self.sdlang = sdlang
        self.default = default


################################################################################
class ocfMetaAction():
    '''
    This class define  action for ocf script meta section
    '''
    ########################################
    def __init__ (self, name, timeout='20s', interval=None, depth=None, role=None):
        self.name = name
        self.timeout = timeout
        self.interval = interval
        self.depth = depth
        self.role = role


################################################################################
class ocfMeta():
    '''
    This class define a meta section for osc script
    '''
    ########################################
    def __init__(self, res, longdesc, shortdesc, version='1.0', ldlang='en', sdlang='en', actions=None):
        self.ra_name = res
        self.ra_longdesc = longdesc
        self.ra_shortdesc = shortdesc
        self.ra_version = version
        self.ra_ldlang = ldlang
        self.ra_sdlang= sdlang
        self.parameters = []
        self.actions = actions if actions else []
    
    ########################################
    def add_prameter(self, name, longdesc, shortdesc, required=0, unique=0, ldlang='en', sdlang='en', default=None):
        '''add a parameter to ocf script'''
        self.parameters.append(ocfMetaParams(name, longdesc, shortdesc, required, unique, ldlang, sdlang, default))
    
    ########################################
    def add_action(self, name, timeout=20, interval=None, depth=None, role=None):
        '''add an action to ocf script'''
        self.actions.append(ocfMetaAction(name, timeout, interval, depth, role))
    
    ########################################
    def gen_meta(self):
        '''generate meta section of an ocf script'''
        print ('<?xml version="1.0"?>\n\
<!DOCTYPE resource-agent SYSTEM "ra-api-1.dtd">\n\
<resource-agent name="{}">\n\
<version>{}</version>\n\
<longdesc lang="{}">\n\
{}\n\
</longdesc>\n\
<shortdesc lang="{}">{}</shortdesc>\n'.format(self.ra_name, self.ra_version, self.ra_ldlang, self.ra_longdesc, self.ra_sdlang, self.ra_shortdesc))

        print ('<parameters>\n')
        for param in self.parameters:
            print ('<parameter name="{}" required="{}" unique="{}">\n\
<longdesc lang="{}">\n\
{}\n\
</longdesc>\n\
<shortdesc lang="{}">{}</shortdesc>\n\
<content type="string"{}/>\n\
</parameter>\n'.format(param.name, param.required, param.unique, param.ldlang, param.longdesc, param.sdlang, param.shortdesc, ' default="{}"'.format(param.default if param.default else '')))
        print ('</parameters>\n')
        
        print ('<actions>\n')
        for act in self.actions:
            print ('<action name="{}" timeout="{}"{}{}{}/>'.format(act.name, act.timeout, \
                ' depth="{}"'.format(act.depth if act.depth else ''), \
                ' interval="{}"'.format(act.interval if act.interval else ''), \
                ' role="{}"'.format(act.role if act.role else '')))
        print ('</actions>\n')
        
        print ('</resource-agent>\n')


################################################################################
class ocfScript(ocfReturnCodes):
    '''
    This class is meta/generic class for ocfScript. It must be inheritate by another class
    '''
    ########################################
    def __init__(self, \
        resname, \
        longdesc, \
        shortdesc, \
        default_binfile, \
        default_pidfile, \
        version='1.0', \
        ldlang='en', \
        sdlang='en', \
        autoaction=True, \
        logfacility=syslog.LOG_DAEMON, \
        # binfile
        binfilesd='binary file to be executed', \
        binfileld='binary file to be executed', \
        binfile_is_ra_opt=True, \
        binfile_is_required=0, binfile_is_unique=0, \
        # pidfile
        pidfilesd='Path to the pid file', \
        pidfileld='Path to the pid file', \
        pidfile_is_ra_opt=True, \
        pidfile_is_required=0, \
        pidfile_is_unique=0, \
        # piddir_owner
        default_piddir_owner='root', \
        piddir_ownersd='owner of pidfile directory', \
        piddir_ownerld='owner of pidfile directory', \
        piddir_owner_is_ra_opt=True, \
        piddir_owner_is_required=0, \
        piddir_owner_is_unique=0, \
        # piddir_group
        default_piddir_group='root', \
        piddir_groupsd='group of pidfile directory', \
        piddir_groupld='group of pidfile directory', \
        piddir_group_is_ra_opt=True, \
        piddir_group_is_required=0, \
        piddir_group_is_unique=0, \
        # piddir_mod
        default_piddir_mod='755', \
        piddir_modsd='premission of pidfile directory', \
        piddir_modld='premission of pidfile directory', \
        piddir_mod_is_ra_opt=True, \
        piddir_mod_is_required=0, \
        piddir_mod_is_unique=0, \
        # binfileoptions
        default_binfileoptions=None, \
        binfileoptionssd='start options for binfile', \
        binfileoptionsld='start options for binfile', \
        binfileoptions_is_ra_opt=True, \
        binfileoption_is_required=0, \
        binfileoption_is_unique=0, \
        # maxnbprocess
        default_maxnbprocess=1, \
        maxnbprocsd='Maximum number of process depending of init', \
        maxnbprocld='Maximum number of process depending of init.\n-1 or 0 means no limit.', \
        maxnbprocess_is_ra_opt=True, \
        maxnbprocess_is_required=0, \
        maxnbprocess_is_unique=0, \
        # commande_line_searched
        default_commande_line_searched=None, \
        commande_line_searchedsd='Command line searched', \
        commande_line_searchedld='Command line has searched if the one stored in the /proc directory of the process does not match the one stored in binfile (this difference is visible with a grep).', \
        commande_line_searched_is_ra_opt=True, \
        commande_line_searched_is_required=0, \
        commande_line_searched_is_unique=0, \
        # msfile
        default_msfile=None, \
        msfilesd='file for master or slave mode', \
        msfileld='file for master or slave mode', \
        msfile_is_ra_opt=False, \
        msfile_is_required=0, \
        msfile_is_unique=0, \
        # fixdirs
        default_fixdirs=None, \
        fixdirssd='fixing perms for dirs specified in the list', \
        fixdirsld='fixing perms for dirs specified in the list. create dirs if dones not exist.\nThe format is :\nfixdirs=LIST_DIRS\nLIST_DIRS=DIR_CONF;DIR_CONF;...\nDIR_CONF=dir,user,group,mod', \
        fixdirs_is_ra_opt=True, \
        fixdirs_is_required=0, \
        fixdirs_in_unique=0, \
        # kill3
        default_kill3=True, \
        kill3sd='use kill -3 (SIGQUIT) for stopping program in ultimate case', \
        kill3ld='use kill -3 (SIGQUIT) for stopping program if -15 does not work\nvalue = True or False', \
        kill3_is_ra_opt=True, \
        kill3_is_required=0, \
        kill3_is_unique=0, \
        # kill 9
        default_kill9=False, \
        kill9sd='use kill -9 (SIGKILL) for stopping program in ultimate case', \
        kill9ld='use kill -9 (SIGKILL) for stopping program if -15 and -3 does not work\nvalue = True or False', \
        kill9_is_ra_opt=True, \
        kill9_is_required=0, \
        kill9_is_unique=0, \
        # ratio kill 15
        default_kill15_ratio=0.65, \
        kill15_ratiosd='ratio for the kill 15 (SIGTERM) to split the stop timeout.', \
        kill15_ratiold='ratio for the kill 15 (SIGTERM) to split the stop timeout. The value is between 0 and 1. The total kill15_ratios + kill3_ratio + kill9_ratio must be less than or equal to one. It is better to leave some time for the script at the end of the timeout to finish its execution keeping a total less than one.', \
        kill15_ratio_is_ra_opt=True, \
        kill15_ratio_is_required=0, \
        kill15_ratio_is_unique=0, \
        # ratio kill 3
        default_kill3_ratio=0.2, \
        kill3_ratiosd='ratio for the kill 3 (SIGQUIT) to split the stop timeout.', \
        kill3_ratiold='ratio for the kill 3 (SIGQUIT) to split the stop timeout. The value is between 0 and 1. The total kill15_ratios + kill3_ratio + kill9_ratio must be less than or equal to one. It is better to leave some time for the script at the end of the timeout to finish its execution keeping a total less than one.', \
        kill3_ratio_is_ra_opt=True, \
        kill3_ratio_is_required=0, \
        kill3_ratio_is_unique=0, \
        # ration kill 9
        default_kill9_ratio=0.05, \
        kill9_ratiosd='ratio for the kill 9 (SIGKILL) to split the stop timeout.', \
        kill9_ratiold='ratio for the kill 9 (SIGKILL) to split the stop timeout. The value is between 0 and 1. The total kill15_ratios + kill3_ratio + kill9_ratio must be less than or equal to one. It is better to leave some time for the script at the end of the timeout to finish its execution keeping a total less than one.', \
        kill9_ratio_is_ra_opt=True, \
        kill9_ratio_is_required=0, \
        kill9_ratio_is_unique=0, \
        # loglevel
        default_loglevel=0, \
        loglevelsd='log level', \
        loglevelld='log level\n0 to 5. 0 : only errors are logged, 1,2,3 : more log, 4,5 : degug', \
        loglevel_is_ra_opt=True, \
        loglevel_is_required=0, \
        loglevel_is_unique=0, \
        # sleepafterstart
        default_sleepafterstart=5, \
        sleepafterstartsd='sleep time before the first monitoring after the process start', \
        sleepafterstartld='sleep time before the first monitoring after the process start', \
        sleepafterstart_is_ra_opt=True, \
        sleepafterstart_is_required=0, \
        sleepafterstart_is_unique=0, \
        # starttimeoutratio
        default_starttimeoutratio=1.0, \
        starttimeoutratiosd='percent of start meta timeout while start testing are done', \
        starttimeoutratiold='percent of start meta timeout while start testing are done\n value is a float in 0 to 1', \
        starttimeoutratio_is_ra_opt=True, \
        starttimeoutratio_is_required=0, \
        starttimeoutratio_is_unique=0, \
        # sleepafterstop
        default_sleepafterstop=5, \
        sleepafterstopsd='sleep time before checking state after the process stop', \
        sleepafterstopld='sleep time before checking state after the process stop', \
        sleepafterstop_is_ra_opt=True, \
        sleepafterstop_is_required=0, \
        sleepafterstop_is_unique=0, \
        # sleepaftersigquit
        default_sleepaftersigquit=5, \
        sleepaftersigquitsd='sleep time before checking state after sigquit', \
        sleepaftersigquitld='sleep time before checking state after sigquit', \
        sleepaftersigquit_is_ra_opt=True, \
        sleepaftersigquit_is_required=0, \
        sleepaftersigquit_is_unique=0, \
        # sleepaftersigkill
        default_sleepaftersigkill=1, \
        sleepaftersigkillsd='sleep time before checking state after sigkill', \
        sleepaftersigkillld='sleep time before checking state after sigkill', \
        sleepaftersigkill_is_ra_opt=True, \
        sleepaftersigkill_is_required=0, \
        sleepaftersigkill_is_unique=0, \
        # ocf_write_pidfile
        default_ocf_write_pidfile=True, \
        ocf_write_pidfilesd='ocf script write pidfile or not', \
        ocf_write_pidfileld='ocf script write pidfile or not\nTrue: write pid file\nFalse: let binfile writing it himself', \
        ocf_write_pidfile_is_ra_opt=False, \
        ocf_write_pidfile_is_required=0, \
        ocf_write_pidfile_is_unique=0, \
        # monitor_clean_dirty_pidfile
        default_monitor_clean_dirty_pidfile=True, \
        monitor_clean_dirty_pidfilesd='cleaning dirty pidfile during monitor function', \
        monitor_clean_dirty_pidfileld='cleaning dirty pidfile during monitor function\nFor example : pidfile present but no process\nvalue = True or False, default = True', \
        monitor_clean_dirty_pidfile_is_ra_opt=True, \
        monitor_clean_dirty_pidfile_is_required=0, \
        monitor_clean_dirty_pidfile_is_unique=0, \
        # start_force_stop_timeout
        default_start_force_stop_timeout=None, \
        start_force_stop_timeoutsd='timeout in secondes. start force a timeout if start find binfile in a failed state', \
        start_force_stop_timeoutld='timeout in secondes. start force a timeout if start find binfile not in state OCF_SUCCESS, OCF_RUNNING_MASTER or OCF_NOT_RUNNING', \
        start_force_stop_timeout_is_ra_opt=True, \
        start_force_stop_timeout_is_required=0, \
        start_force_stop_timeout_is_unique=0, \
        # user_cmd
        default_user_cmd=None, \
        user_cmdsd='User to run the command as', \
        user_cmdld='User to run the command as', \
        user_cmd_is_ra_opt=False, \
        user_cmd_is_required=0, \
        user_cmd_is_unique=0, \
        # change_workdir
        default_change_workdir=None, \
        change_workdirsd='Full path name of the work directory', \
        change_workdirld='The path from where the binfile will be executed.', \
        change_workdir_is_ra_opt=False, \
        change_workdir_is_required=0, \
        change_workdir_is_unique=0, \
        # process_file_ulimit
        default_process_file_ulimit=1024, \
        process_file_ulimitsd='ulimit open file for process', \
        process_file_ulimitld='ulimit open file for process. minimum is 1024.', \
        process_file_ulimit_is_ra_opt=True, \
        process_file_ulimit_is_required=0, \
        process_file_ulimit_is_unique=0, \
        # status_check_ppid
        default_status_check_ppid=True, \
        status_check_ppidsd='status/monitor search if ppid=1', \
        status_check_ppidld='If True, status/monitor search the process depend from init\nValues are True, False, All, None or a combination of start, stop, and monitor separated by commas.', \
        status_check_ppid_is_ra_opt=False, \
        status_check_ppid_is_required=0, \
        status_check_ppid_is_unique=0, \
        # status_check_pidfile
        default_status_check_pidfile=True, \
        status_check_pidfilesd='Control between pidfile and pid', \
        status_check_pidfileld='Control if the pid in pidfile is the same as the pid found in the process list.\nIf it is different, the process has been relaunched: there has been a problem, the state of the process potentially unknown.\nValues are True, False, All, None or a combination of start, stop, and monitor separated by commas.', \
        status_check_pidfile_is_ra_opt=False, \
        status_check_pidfile_is_required=0, \
        status_check_pidfile_is_unique=0 ):
        super(ocfScript,self).__init__()
        syslog.openlog(logoption=syslog.LOG_PID, facility=logfacility)
        self.metadata = ocfMeta(resname, longdesc, shortdesc, version, ldlang, sdlang)
        self.master = 'master'
        self.slave = 'slave'
        self.nodename = os.uname()[1]
        self.choices = []
        self.runoptions = {}
        if autoaction:
            self.add_runoption('start', self.start)
            self.add_runoption('stop', self.stop)
            self.add_runoption('monitor', self.monitor, interval=10, depth=0)
            self.add_runoption('notify', self.notify)
            self.add_runoption('meta-data', self.meta, timeout=5)
            self.add_runoption('metadata', self.meta, timeout=5)
            self.add_runoption('meta_data', self.meta, timeout=5)
            self.add_runoption('validate-all', self.validate, timeout=5)
        
        self.options = {}
        try:
            self.init_option('binfile', \
                binfile_is_ra_opt, \
                binfileld, \
                binfilesd, \
                required=binfile_is_required, \
                unique=binfile_is_unique, \
                default=default_binfile)
            self.init_option('pidfile', \
                pidfile_is_ra_opt, \
                pidfileld, \
                pidfilesd, \
                required=pidfile_is_required, \
                unique=pidfile_is_unique, \
                default=default_pidfile)
            self.init_option('piddir_owner', \
                piddir_owner_is_ra_opt, \
                piddir_ownerld, \
                piddir_ownersd, \
                required=piddir_owner_is_required, \
                unique=piddir_owner_is_unique, \
                default=default_piddir_owner)
            self.init_option('piddir_group', \
                piddir_group_is_ra_opt, \
                piddir_groupld, \
                piddir_groupsd, \
                required=piddir_group_is_required, \
                unique=piddir_group_is_unique, \
                default=default_piddir_group)
            self.init_option('piddir_mod', \
                piddir_mod_is_ra_opt, \
                piddir_modld, \
                piddir_modsd, \
                required=piddir_mod_is_required, \
                unique=piddir_mod_is_unique, \
                default=default_piddir_mod)
            self.init_option('loglevel', \
                loglevel_is_ra_opt, \
                loglevelld, \
                loglevelsd, \
                required=loglevel_is_required, \
                unique=loglevel_is_unique, \
                default=default_loglevel, \
                convertfct=self.convert_to_int)
            self.init_option('binfileoptions', \
                binfileoptions_is_ra_opt, \
                binfileoptionsld, \
                binfileoptionssd, \
                required=binfileoption_is_required, \
                unique=binfileoption_is_unique, \
                default=default_binfileoptions)
            self.init_option('msfile', \
                msfile_is_ra_opt, \
                msfileld, \
                msfilesd, \
                required=msfile_is_required, \
                unique=msfile_is_unique, \
                default=default_msfile)
            self.init_option('maxnbprocess', \
                maxnbprocess_is_ra_opt, \
                maxnbprocld, \
                maxnbprocsd, \
                required=maxnbprocess_is_required, \
                unique=maxnbprocess_is_unique, \
                default=default_maxnbprocess, \
                convertfct=self.convert_to_int)
            self.init_option('commande_line_searched', \
                commande_line_searched_is_ra_opt, \
                commande_line_searchedld, \
                commande_line_searchedsd, \
                required=commande_line_searched_is_required, \
                unique=commande_line_searched_is_unique, \
                default=default_commande_line_searched if default_commande_line_searched else self.get_option('binfile'))
            self.init_option('fixdirs', \
                fixdirs_is_ra_opt, \
                fixdirsld, \
                fixdirssd, \
                required=fixdirs_is_required, \
                unique=fixdirs_in_unique, \
                default=default_fixdirs)
            self.init_option('kill3', \
                kill3_is_ra_opt, \
                kill3ld, \
                kill3sd, \
                required=kill3_is_required, \
                unique=kill3_is_unique, \
                default=default_kill3, \
                convertfct=self.convert_to_bool)
            self.init_option('kill9', \
                kill9_is_ra_opt, \
                kill9ld, \
                kill9sd, \
                required=kill9_is_required, \
                unique=kill9_is_unique, \
                default=default_kill9, \
                convertfct=self.convert_to_bool)
            self.init_option('kill15_ratio', \
                kill15_ratio_is_ra_opt, \
                kill15_ratiold, \
                kill15_ratiosd, \
                required=kill15_ratio_is_required, \
                unique=kill15_ratio_is_unique, \
                default=default_kill15_ratio, \
                convertfct=self.convert_to_float)
            self.init_option('kill3_ratio', \
                kill3_ratio_is_ra_opt, \
                kill3_ratiold, \
                kill3_ratiosd, \
                required=kill3_ratio_is_required, \
                unique=kill3_ratio_is_unique, \
                default=default_kill3_ratio, \
                convertfct=self.convert_to_float)
            self.init_option('kill9_ratio', \
                kill9_ratio_is_ra_opt, \
                kill9_ratiold, \
                kill9_ratiosd, \
                required=kill9_ratio_is_required, \
                unique=kill9_ratio_is_unique, \
                default=default_kill9_ratio, \
                convertfct=self.convert_to_float)
            self.init_option('sleepafterstart', \
                sleepafterstart_is_ra_opt, \
                sleepafterstartld, \
                sleepafterstartsd, \
                required=sleepafterstart_is_required, \
                unique=sleepafterstart_is_unique, \
                default=default_sleepafterstart, \
                convertfct=self.convert_to_int)
            self.init_option('starttimeoutratio', \
                starttimeoutratio_is_ra_opt, \
                starttimeoutratiold, \
                starttimeoutratiosd, \
                required=starttimeoutratio_is_required, \
                unique=starttimeoutratio_is_unique, \
                default=default_starttimeoutratio, \
                convertfct=self.convert_to_float)
            self.init_option('sleepafterstop', \
                sleepafterstop_is_ra_opt, \
                sleepafterstopld, \
                sleepafterstopsd, \
                required=sleepafterstop_is_required, \
                unique=sleepafterstop_is_unique, \
                default=default_sleepafterstop, \
                convertfct=self.convert_to_int)
            self.init_option('sleepaftersigquit', \
                sleepaftersigquit_is_ra_opt, \
                sleepaftersigquitld, \
                sleepaftersigquitsd, \
                required=sleepaftersigquit_is_required, \
                unique=sleepaftersigquit_is_unique, \
                default=default_sleepaftersigquit, \
                convertfct=self.convert_to_int)
            self.init_option('sleepaftersigkill', \
                sleepaftersigkill_is_ra_opt, \
                sleepaftersigkillld, \
                sleepaftersigkillsd, \
                required=sleepaftersigkill_is_required, \
                unique=sleepaftersigkill_is_unique, \
                default=default_sleepaftersigkill, \
                convertfct=self.convert_to_int)
            self.init_option('ocf_write_pidfile', \
                ocf_write_pidfile_is_ra_opt, \
                ocf_write_pidfileld, \
                ocf_write_pidfilesd, \
                required=ocf_write_pidfile_is_required, \
                unique=ocf_write_pidfile_is_unique, \
                default=default_ocf_write_pidfile, \
                convertfct=self.convert_to_bool)
            self.init_option('monitor_clean_dirty_pidfile', \
                monitor_clean_dirty_pidfile_is_ra_opt, \
                monitor_clean_dirty_pidfileld, \
                monitor_clean_dirty_pidfilesd, \
                required=monitor_clean_dirty_pidfile_is_required, \
                unique=monitor_clean_dirty_pidfile_is_unique, \
                default=default_monitor_clean_dirty_pidfile, \
                convertfct=self.convert_to_bool)
            self.init_option('start_force_stop_timeout', \
                start_force_stop_timeout_is_ra_opt, \
                start_force_stop_timeoutld, \
                start_force_stop_timeoutsd, \
                required=start_force_stop_timeout_is_required, \
                unique=start_force_stop_timeout_is_unique, \
                default=default_start_force_stop_timeout, \
                convertfct=self.convert_to_int)
            self.init_option('user_cmd', \
                user_cmd_is_ra_opt, \
                user_cmdld, \
                user_cmdsd, \
                required=user_cmd_is_required, \
                unique=user_cmd_is_unique, \
                default=default_user_cmd)
            self.init_option('change_workdir', \
                change_workdir_is_ra_opt, \
                change_workdirld, \
                change_workdirsd, \
                required=change_workdir_is_required, \
                unique=change_workdir_is_unique, \
                default=default_change_workdir)
            self.init_option('process_file_ulimit', \
                process_file_ulimit_is_ra_opt, \
                process_file_ulimitld, \
                process_file_ulimitsd, \
                required=process_file_ulimit_is_required, \
                unique=process_file_ulimit_is_unique, \
                default=default_process_file_ulimit, \
                convertfct=self.convert_to_int)
            self.init_option('status_check_ppid', \
                status_check_ppid_is_ra_opt, \
                status_check_ppidld, \
                status_check_ppidsd, \
                required=status_check_ppid_is_required, \
                unique=status_check_ppid_is_unique, \
                default=default_status_check_ppid)
            self.init_option('status_check_pidfile', \
                status_check_pidfile_is_ra_opt, \
                status_check_pidfileld, \
                status_check_pidfilesd, \
                required=status_check_pidfile_is_required, \
                unique=status_check_pidfile_is_unique, \
                default=default_status_check_pidfile)
            self.init_special_start_stop_mon_options('status_check_ppid', \
                {'start':'status_check_ppid_for_start', 'stop':'status_check_ppid_for_stop', 'monitor':'status_check_ppid_for_monitor'})
            self.init_special_start_stop_mon_options('status_check_pidfile', \
                {'start':'status_check_pidfile_for_start', 'stop':'status_check_pidfile_for_stop', 'monitor':'status_check_pidfile_for_monitor'})
        except:
            self.ocf_log_err('erreur lors de ocfscript.__init__')
            raise
        # Notify
        self.notify_infos = ocfNotifyInfo()
        self.ocf_log('ocfScript nodename={}'.format(self.nodename, msglevel=4))

    ########################################
    def __syslog_inherit_msg(self):
        syslog.syslog(syslog.LOG_ERR, 'This ocfScript function do nothing and must be overriden by the inherit class')

    ########################################
    def ocf_log(self, msg, msglevel=0, sysloglvl=syslog.LOG_INFO):
        # TODO : voir ocf_log /usr/lib/ocf/lib/heartbeat/ocf-shellfuncs
        if msglevel <= self.get_option('loglevel'):
            if self.get_option('binfile'):
                message = '{}:loglevel={}, {}'.format(self.get_option('binfile'), msglevel, msg)
            else:
                message = 'loglevel={}, {}'.format(msglevel, msg)
            
            if msglevel == 4 or msglevel == 5:
                sysloglvl=syslog.LOG_DEBUG
                
            syslog.syslog(sysloglvl, message) 
     
    ########################################
    def ocf_log_warn(self, msg):
        self.ocf_log(msg, msglevel=0, sysloglvl=syslog.LOG_WARNING)
    
    ########################################
    def ocf_log_err(self, msg):
        self.ocf_log(msg, msglevel=0, sysloglvl=syslog.LOG_ERR)
    
    ########################################
    def set_defaults(self, arg):
        '''set default value for environnement variable'''
        self.ocf_log('ocfScript.set_defaults', msglevel=5)
        locale.setlocale(locale.LC_ALL, 'C')
        
        if 'OCF_RESKEY_OCF_CHECK_LEVEL' in os.environ:
            os.environ['OCF_CHECK_LEVEL'] = os.environ['OCF_RESKEY_OCF_CHECK_LEVEL']
        else:
            os.environ['OCF_CHECK_LEVEL'] = '0'
        
        if not 'OCF_ROOT' in os.environ:
            msg = 'ERROR: OCF_ROOT not in environnement variables.'
            self.ocf_log_err(msg)
            raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
        elif not os.path.exists(os.environ['OCF_ROOT']):
            msg = 'ERROR: OCF_ROOT points to non-directory {}.'.format(os.environ['OCF_ROOT'])
            self.ocf_log_err(msg)
            raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
        
        if not 'OCF_RESOURCE_TYPE' in os.environ:
            os.environ['OCF_RESOURCE_TYPE'] = __file__
        
        if not 'OCF_RA_VERSION_MAJOR' in os.environ:
            os.environ['OCF_RESOURCE_INSTANCE'] = 'default'
            return self.ocfretcodes['OCF_SUCCESS']
        
        if arg in ['meta-data', 'metadata', 'meta_data']:
            os.environ['OCF_RESOURCE_INSTANCE'] = 'undef'
        
        if not 'OCF_RESOURCE_INSTANCE'in os.environ:
            msg = 'ERROR: Need to tell us our resource instance name.'
            ocf_log_err(msg)
            raise ocfError(self.ocfretcodes['OCF_ERR_ARGS'], msg)
        
        return self.ocfretcodes['OCF_SUCCESS']

    ########################################
    def add_runoption (self, opt, fctname, timeout=20, interval=None, depth=None, role=None):
        '''add script start option'''
        self.choices.append(opt)
        self.runoptions[opt] = fctname
        self.metadata.add_action(opt, timeout, interval, depth, role)
    
    ########################################
    def add_option(self, opt, env, value):
        '''add script option
        opt = option name
        env = environement variable name
        value = option value
        '''
        self.options[opt] = ocfOption(env, value)
        
    ########################################
    def mod_option(self, opt, value, env=None):
        '''modify script option
        opt = option name
        value = option value
        env = environement variable name
        '''
        if opt in self.options:
            self.options[opt].mod(value, envname=env)
        # TODO raise Error

    ########################################
    def get_option(self, opt):
        return self.options[opt].value if opt in self.options else None
        
    ########################################
    def get_opt_envname(self, opt):
        return self.option[opt].envname
    
    ########################################
    def raise_if_not_string(self, arg):
        if not isinstance(arg, str):
            raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], '{} is not a string'.format(arg))
    
    ########################################
    def convert_to_bool(self, arg):
        '''This function can be call in init_from_env. Can't use ocf_log : during init_from_env all ocf default options may not be defined'''
        try:
            self.raise_if_not_string(arg)
            if arg == 'True':
                return True
            elif arg == 'False':
                return False
            else:
                raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], '{} is not a boolean'.format(arg))
        except:
            raise
    
    ########################################
    def convert_to_int(self, arg):
        '''This function can be call in init_from_env. Can't use ocf_log : during init_from_env all ocf default options may not be defined'''
        try:
            self.raise_if_not_string(arg)
            nbr = int(arg)
        except ValueError:
            raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], '{} is not a number'.format(arg))
        except:
            raise
        else:
            return nbr
            
    ########################################
    def convert_to_octal(self, arg):
        '''This function can be call in init_from_env. Can't use ocf_log : during init_from_env all ocf default options may not be defined'''
        try:
            self.raise_if_not_string(arg)
            nbr = int(arg, 8)
        except ValueError:
            raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], '{} is not a number'.format(arg))
        except:
            raise
        else:
            return nbr 
    
    ########################################
    def convert_to_float(self, arg):
        '''This function can be call in init_from_env. Can't use ocf_log : during init_from_env all ocf default options may not be defined'''
        try:
            self.raise_if_not_string(arg)
            nbr = float(arg)
        except ValueError:
            raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], '{} is not a number'.format(arg))
        except:
            raise
        else:
            return nbr
    
    ########################################
    def convert_to_list(self, arg, seperator=','):
        '''This function can be call in init_from_env. Can't use ocf_log : during init_from_env all ocf default options may not be defined'''
        try:
            self.raise_if_not_string(arg)
            lst = arg.rstrip(',').split(',')
        except AttributeError:
            raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], '{} is not a list'.format(arg))
        except:
            raise
        else:
            return lst
    
    ########################################
    def init_from_env(self, opt, longdesc, shortdesc, var=None, required=0, unique=0, ldlang='en', sdlang='en', default=None, convertfct=None):
        '''
        Add script option taken from environement variable
        Can't use ocf_log : during init_from_env all ocf default options may not be defined
        '''
        ev_name= 'OCF_RESKEY_{}'.format(var if var else opt)
        ev = os.environ.get(ev_name)
        if convertfct:
            try:
                val = convertfct(ev) if ev else default
            except ocfError as oe:
                self.ocf_log_err('Erreur lors de init_from_env {} : {}'.format(opt, oe.strerror))
                raise
            except:
                self.ocf_log_err('Erreur lors de init_from_env {}'.format(opt))
                raise
        else:
            val =  ev if ev else default
        self.add_option(opt, ev_name, val)
        self.metadata.add_prameter(opt,  longdesc, shortdesc, required, unique, ldlang, sdlang, default)

    ########################################
    def init_option(self, opt, is_ra_opt, longdesc, shortdesc, var=None, required=0, unique=0, ldlang='en', sdlang='en', default=None, convertfct=None):
        try:
            if is_ra_opt: self.init_from_env(opt, longdesc, shortdesc, var=var, required=required, unique=unique, ldlang=ldlang, sdlang=sdlang, default=default, convertfct=convertfct)
            else: self.add_option(opt, None, default)
        except:
            raise

    ########################################
    def init_special_start_stop_mon_options(self, \
        opt, \
        new_opt_dic, \
        all_opt_list=['true','all'], \
        no_opt_list=['false', 'none', 'no'], \
        start_opt_list=['start'], \
        stop_opt_list=['stop'], \
        mon_opt_list=['mon', 'monitor'], \
        separator=','):
        '''
        Notes : 
        - all_opt_list et no_opt_list are exclusives. They can not be mixed with start|stop|mon_opt_list
        - *_opt_list are in lower case
        - new_opt_dic must have the three keys start, stop, monitor
        '''
        lov = str(self.get_option(opt)).lower()
        if lov in all_opt_list:
            start=stop=mon=True
        elif lov in no_opt_list:
            start=stop=mon=False
        else:
            lov_list = lov.rstrip(',').split(',')
            start=stop=mon=False
            for x in lov_list:
                if x in start_opt_list:
                   start=True
                elif x in stop_opt_list:
                    stop=True
                elif x in mon_opt_list:
                    mon=True
                else:
                    msg = 'init_special_start_stop_mon_options: for {} value {} is forbiden'.format(opt, x)
                    self.ocf_log_err(msg)
                    raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], msg)
        self.add_option(new_opt_dic['start'], None, start)
        self.add_option(new_opt_dic['stop'], None, stop)
        self.add_option(new_opt_dic['monitor'], None, mon)
        self.ocf_log('ocfScript.init_special_start_stop_mon_options: {}:{}, {}:{}, {}:{}'.format(new_opt_dic['start'], start, new_opt_dic['stop'], stop, new_opt_dic['monitor'], mon), msglevel=5)

    ########################################
    def __init_dir(self, dir, uid, gid, mod):
        '''raise ocfError'''
        self.ocf_log('ocfScript.__init_dir with uid=\"{}\" gid=\"{}\" mod=\"{:o}\"'.format(uid, gid, mod), msglevel=5)
        if not os.path.isdir(dir):
            try:
                self.ocf_log('Creating directory {}'.format(dir))
                os.makedirs(dir, 0o755)
            except OSError as ose:
                msg = '__init_dir : Can\'t create {}: '.format(dir, ose.strerror)
                self.ocf_log_err(msg)
                raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
            except:
                msg = '__init_dir : {}'.format(sys.exc_info())
                self.ocf_log_err(msg)
                raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
        else:
            self.ocf_log('ocfScript.__init_dir {} exist'.format(dir), msglevel=5)
    
        oss = os.stat(dir)
        if oss.st_uid != uid or oss.st_gid != gid or oss.st_mode&0o7777 != mod:
            try:
                self.ocf_log('Changing owner, group and permissions on directory {} with uid=\"{}\" gid=\"{}\" mod=\"{:o}\"'.format(dir, uid, gid, mod))
                os.chown(dir, uid, gid)
                os.chmod(dir, mod)
            except OSError as ose:
                msg = '__init_dir : Can\'t chown with or chmod : {}'.format(ose.streerror)
                self.ocf_log_err(msg)
                raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
            except:
                msg = '__init_dir : {}'.format(sys.exc_info())
                self.ocf_log_err(msg)
                raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
        else:
            self.ocf_log('ocfScript.__init_dir {} owner, group, and permissions ok'.format(dir), msglevel=5)
            
    ########################################
    def init_dir(self, dir, user='root', group='root', mod='755'):
        '''raise ocfError'''
        self.ocf_log('ocfScript.init_dir with user=\"{}\" group=\"{}\" mod=\"{}\"'.format(user, group, mod), msglevel=5)
        try:
            uid = pwd.getpwnam(user).pw_uid
            gid = grp.getgrnam(group).gr_gid
        except KeyError as ke:
            msg = 'init_dir : Can\'t get uid for user {} or gid for group {} : {}'.format(user, group, ke)
            self.ocf_log_err(msg)
            raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
        except:
            msg = 'init_dir : {}'.format(sys.exc_info())
            self.ocf_log_err(msg)
            raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
            
        try:
            omod = self.convert_to_octal(mod)
        except ocfError as oe:
            self.ocf_log_err('init_dir : Error when converting {} to octal : {}'.format(mod, oe.strerror))
            raise

        try:
            self.__init_dir(dir, uid, gid, omod)
        except:
            self.ocf_log_err('init_dir : Error during init_dir dir=\"{}\" uid=\"{}\" gid=\"{}\" mod=\"{}\" omod=\"{:o}\"'.format(dir, uid, gid, mod, omod))
            raise


    ########################################
    def init_pidfile(self):
        '''raise ocfError'''
        self.ocf_log('ocfScript.init_pidfile, with piddir user=\"{}\" group=\"{}\" mod=\"{}\"'.format(self.get_option('piddir_owner'), self.get_option('piddir_group'), self.get_option('piddir_mod')), msglevel=5)
        if not self.get_option('pidfile'):
            msg = 'The pidfile has not been specified, exiting.'
            self.ocf_log_err(msg)
            raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)

        piddir = os.path.dirname(self.get_option('pidfile'))
        self.ocf_log('pidfile is {}, piddir is {}'.format(self.get_option('pidfile'), piddir), msglevel=4)
        try:
            self.init_dir(piddir, user=self.get_option('piddir_owner'), group=self.get_option('piddir_group'), mod=self.get_option('piddir_mod'))
        except:
            raise

    ########################################
    def maxnbprocess_unlimited(self):
        #self.ocf_log('ocfScript.maxnbprocess_unlimited', msglevel=5)
        if self.get_option('maxnbprocess') in [0,-1]:
            self.ocf_log('ocfScript.maxnbprocess_unlimited: maxnbprocess is unlimited', msglevel=5)
            return True
        else:
            self.ocf_log('ocfScript.maxnbprocess_unlimited: maxnbprocess is limited to {}'.format(self.get_option('maxnbprocess')), msglevel=5)
            return False

    ########################################
    def get_first_pids(self, check_ppid=True):
        '''get pid of binfile with ppid = init'''
        self.ocf_log('ocfScript.get_first_pids: searching {} with check_ppid={}'.format(self.get_option('commande_line_searched'), check_ppid), msglevel=5)
        ret = []
        for proc in psutil.process_iter():
            try:
                if check_ppid:
                    if psutil.pid_exists(proc.pid) and self.get_option('commande_line_searched') in proc.cmdline()[:2] and proc.ppid() == 1:
                        ret.append(proc.pid)
                else:
                    if psutil.pid_exists(proc.pid) and self.get_option('commande_line_searched') in proc.cmdline()[:2]:
                        ret.append(proc.pid)
            except psutil.NoSuchProcess as err:
                self.ocf_log('ocfScript.get_first_pids exception: {}'.format(err), msglevel=5)
        
        self.ocf_log('ocfScript.get_first_pids pids={}'.format(ret), msglevel=5)
        return ret

    ########################################
    def get_pids_from_pidfile(self):
        '''
        raise OSError
        raise ocfError
        '''
        self.ocf_log('ocfScript.get_pids_from_pidfile', msglevel=5)
        if not self.get_option('pidfile'):
            msg = 'The pidfile has not been specified, exiting.'
            self.ocf_log_err(msg)
            raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
        
        if not os.path.isfile(self.get_option('pidfile')):
            msg = 'pidfile {} does not exist'.format(self.get_option('pidfile'))
            self.ocf_log_err(msg)
            raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
            
        try:
            f = open(self.get_option('pidfile'), 'r')
        except:
            msg = 'Can\'t open pidfile {}'.format(self.get_option('pidfile'))
            self.ocf_log_err(msg)
            raise
        
        linelist = f.read().splitlines()
        lll = len(linelist)
        if lll == 0:
            msg = '{} is empty'.format(self.get_option('pidfile'))
            self.ocf_log_err(msg)
            raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
        elif not self.maxnbprocess_unlimited() and lll > self.get_option('maxnbprocess'):
            msg = '{} contain more than {} pid'.format(self.get_option('pidfile'), self.get_option('maxnbprocess'))
            self.ocf_log_err(msg)
            raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
        else:
            ret = []
            for l in linelist:
                try:
                    ret.append(int(l))
                except:
                    msg = 'Can\'t convert line {} to int in {} '.format(l, self.get_option('pidfile'))
                    self.ocf_log_err(msg)
                    f.close()
                    raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
        f.close()
        return ret
        
    ########################################
    def write_pids_in_pidfile(self, pids):
        self.ocf_log('ocfScript.write_pids_in_pidfile', msglevel=5)
        if not self.get_option('pidfile'):
            msg = 'The pidfile has not been specified, exiting.'
            self.ocf_log_err(msg)
            raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
        
        try:
            f = open(self.get_option('pidfile'), 'w')
        except:
            msg = 'Can\'t open pidfile {}'.format(self.get_option('pidfile'))
            self.ocf_log_err()
            raise ocfError (self.ocfretcodes['OCF_ERR_GENERIC'], msg)
        
        for p in pids:
            self.ocf_log('ocfScript.write_pids_in_pidfile writing pid : {}'.format(p), msglevel=3)
            f.write('{}\n'.format(p))
            
        f.close()
        return True
    
    ########################################
    def remove_pidfile(self):
        '''
        raise OSError
        '''
        self.ocf_log('ocfScript.remove_pidfile', msglevel=5)
        if not self.get_option('pidfile'):
            msg = 'The pidfile has not been specified, exiting.'
            self.ocf_log_err(msg)
            raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
        if os.path.exists(self.get_option('pidfile')):
            try:
                self.ocf_log('ocfScript.remove_pidfile removing pidfile {}'.format(self.get_option('pidfile')), msglevel=3)
                os.remove(self.get_option('pidfile'))
            except:
                ocf_log_err('Can\'t remove {}'.format(self.get_option('pidfile')))
                raise
    
    ########################################
    def read_msfile(self):
        self.ocf_log('ocfScript.read_msfile', msglevel=5)
        try:
            f = open(self.get_option('msfile'), 'r')
        except:
            msg = 'ocfScript.read_ms_file : can \'t open {}'.format(self.get_option('msfile'))
            self.ocf_log_err(msg)
            raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
        
        try:
            self.ocf_log('ocfScript.read_ms_file : reading {}'.format(self.get_option('msfile')), msglevel=3)
            linelist = f.readlines()
        except:
            msg = 'ocfScript.read_ms_file : can \'t read {}'.format(self.get_option('msfile'))
            self.ocf_log_err(msg)
            raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
        lll = len(linelist)
        if lll == 0:
            msg = '{} is empty'.format(self.get_option('msfile'))
            self.ocf_log_warn(msg)
            raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
        elif lll > 1:
            msg = '{} contain more than one line'.format(self.get_option('msfile'))
            self.ocf_log_err(msg)
            raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
        else: 
            ret = linelist[0].strip('\n')
        f.close()
        return ret
    
    ########################################
    def write_msfile(self, is_master=False):
        '''
        raise OSError
        '''
        self.ocf_log('ocfScript.write_msfile', msglevel=5)
        msf_data = self.master if is_master else self.slave
        try:
            f = open(self.get_option('msfile'), 'w')
        except:
            self.ocf_log_err('ocfScript.write_msfile : can \'t open {}'.format(self.get_option('msfile')))
            raise
        
        self.ocf_log('ocfScript.write_msfile writing file {}'.format(self.get_option('msfile')), msglevel=3)
        try:
            f.write(msf_data)
        except:
            self.ocf_log_err('ocfScript.write_msfile : can \'t write {}'.format(self.get_option('msfile')))
            raise
        finally:
            f.close()
            
        self.ocf_log('ocfScript.write_msfile : writing msfile {} success with value : {}'.format(self.get_option('msfile'), msf_data), msglevel=2)
        
    ########################################
    def delete_msfile(self):
        self.ocf_log('ocfScript.delete_msfile', msglevel=5)
        if os.path.exists(self.get_option('msfile')):
            try:
                os.remove(self.get_option('msfile'))
            except:
                self.ocf_log_err('ocfScript.delete_msfile : can \'t delete {}'.format(self.get_option('msfile')))
                raise
            
    ########################################
    def cleaning_dirty_pidfile(self, clean_dirty_pidfile):
        self.ocf_log('ocfScript.cleaning_dirty_pidfile', msglevel=5)
        if clean_dirty_pidfile:
            self.ocf_log('ocfScript.clean_dirty_pidfile : removing {}'.format(self.get_option('pidfile')), msglevel=2)
            self.remove_pidfile()
            # TODO : using raise of remove_pidfile()
    
    ########################################
    def fixdirs(self, fix=True):
        '''
        fixing perms for dirs specified in the list. The format is :
        fixdirs=LIST_DIRS
        LIST_DIRS=DIR_CONF;DIR_CONF;...
        DIR_CONF=file,user,group,mod
        
        raise KeyError if user or group does not exist
        raise ocfError if it does not correspond to ocfScript conditions
        raise OSError if fix are not working
        '''
        self.ocf_log('ocfScript.fixdirs', msglevel=5)
        
        if self.get_option('fixdirs'):
            fds = self.get_option('fixdirs').rstrip(';').split(';')
            
            for fd in fds:
                dirinfo = fd.split(',')
                self.ocf_log('ocfScript.fixdirs {}'.format(dirinfo), msglevel=4)
                
                # Validate
                if len(dirinfo) != 4:
                    msg = 'invalid fixdirs configuration : bad number of arguments in line \"{}\"'.format(fd)
                    self.ocf_log_err(msg)
                    raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], msg)
                
                if os.pardir in dirinfo[0]:
                    msg = 'invalid fixdirs configuration : path contain {}'.format(os.pardir)
                    self.ocf_log_err(msg)
                    raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], msg)
                
                if len(dirinfo[3]) < 3 or len(dirinfo[3]) > 4:
                    msg = 'invalid fixdirs configuration (chmod)'
                    self.ocf_log_err(msg)
                    raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], msg)
                
                try:
                    omod = self.convert_to_octal(dirinfo[3])
                except ocfError as oe:
                    self.ocf_log_err('Error when converting {} to octal : {}'.format(dirinfo[3], oe.strerror))
                    raise
                
                try: 
                    uid = pwd.getpwnam(dirinfo[1]).pw_uid
                    gid = grp.getgrnam(dirinfo[2]).gr_gid
                except KeyError as ke:
                    self.ocf_log_err('invalid fixdir configuration: {}'.format(ke))
                    raise
                
                #fix 
                if fix:
                    try:
                        self.__init_dir(dirinfo[0], uid, gid, omod)
                    except:
                        self.ocf_log_err('Error during fixing dir in fixdirs : {}'.format(dir))
                        raise

    ########################################
    def calc_timeout(self, ratio=1.0, default_timeout=0):
        self.ocf_log('ocfScript.calc_timeout', msglevel=5)
        try:
            ev = os.environ.get('OCF_RESKEY_CRM_meta_timeout')
            timeout = int(ev) * ratio
        except:
            self.ocf_log_warn('ocfScript.stop_sigterm : can not read OCF_RESKEY_CRM_meta_timeout')
            timeout = default_timeout
        return timeout

    ########################################
    def status_success(self):
        if self.get_option('msfile'):
            self.ocf_log('ocfScript.status_success action master/slave', msglevel=5)
            try:
                msret = self.read_msfile()
            except ocfError as oe:
                ret = oe.err
            else:
                if msret == self.master:
                    ret = self.ocfretcodes['OCF_RUNNING_MASTER']
                elif msret == self.slave:
                    ret = self.ocfretcodes['OCF_SUCCESS']
                else:
                    ret = self.ocfretcodes['OCF_ERR_GENERIC']
        else:
            ret = self.ocfretcodes['OCF_SUCCESS']
        return ret

    ########################################
    def status_error(self, msg):
        self.ocf_log_err(msg)
        ret = self.ocfretcodes['OCF_ERR_GENERIC']
        if self.get_option('msfile'):
            self.ocf_log('ocfScript.status_error action master/slave', msglevel=4)
            
            try:
                msret = self.read_msfile()
            except ocfError as oe:
                ret = oe.err
            else:
                if  msret == self.master:
                    ret = self.ocfretcodes['OCF_FAILED_MASTER']

        return ret
    
    ########################################
    def status(self, clean_dirty_pidfile=False, check_pidfile=True, check_ppid=True):
        self.ocf_log('ocfScript.status with clean_dirty_pidfile={}, check_pidfile={}, check_ppid={}'.format(clean_dirty_pidfile, check_pidfile, check_ppid), msglevel=5)
        
        processes = self.get_first_pids(check_ppid=check_ppid)
        if not self.maxnbprocess_unlimited() and len(processes) > self.get_option('maxnbprocess'):
            return self.status_error('Too much {} started ({} started).'.format(self.get_option('binfile'), len(processes)))

        if check_pidfile:
            if not self.get_option('pidfile'):
                return self.status_error('The pidfile has not been specified, exiting.')
            
            if os.path.isfile(self.get_option('pidfile')):
                self.ocf_log('ocfScript.status {} exist'.format(self.get_option('pidfile')), msglevel=3)
                try:
                    pids = self.get_pids_from_pidfile()
                except:
                    self.cleaning_dirty_pidfile(clean_dirty_pidfile)
                    return self.status_error('pidfile exist but i can\'t read it')
                if not pids: # no pid in pidfile
                    if not processes:
                        self.cleaning_dirty_pidfile(clean_dirty_pidfile)
                        # TODO : faut-il declarer un NOT_RUNNING
                        return self.status_error('pidfile exist and is empty while program seems stop')
                    else:
                        # Pas de cleaning_pidfile si le process tourne
                        return self.status_error('pidfile does not contain a pid but we have found this pid {}.'.format(processes))
                elif not processes: # no process found
                    self.cleaning_dirty_pidfile(clean_dirty_pidfile)
                    return self.status_error('pidfile is present but not the process.')
                elif len(pids) != len(processes):
                         return self.status_error('pidfile is present but does not give the same number of process : {} vs {}.'.format(pids, processes))
                else:
                    for p in processes:
                        if p not in pids:
                            return self.status_error('pidfile is present and give pid {} but we found this pid {}.'.format(pids, processes))
                        elif not psutil.pid_exists(p):
                             return self.status_error('pidfile is present and give pid {}, we found this pid {} but it does not existe yet (finish during status ?).'.format(pids, p))
                        elif psutil.pid_exists(p) and not psutil.Process(p).is_running():
                            return self.status_error('pidfile is present and give pid {}, we found this pid {} but it is taged not running.'.format(pids, p))
                    # program is running
                    self.ocf_log('ocfScript.status program is running', msglevel=3)
                    return self.status_success()
            else:
                self.ocf_log('{} does not exist'.format(self.get_option('pidfile')), msglevel=3)
                if len(processes) != 0:
                    return self.status_error('pidfile is not present but we found this pid {}'.format(processes))
                else:
                    self.ocf_log('Programm is not running', msglevel=3)
                    return self.ocfretcodes['OCF_NOT_RUNNING']
        else:
            if processes:
                return self.status_success()
            else:
                return self.ocfretcodes['OCF_NOT_RUNNING']
        
        return self.status_error('ocfScript.status unexpected case')
    
    ########################################
    def status_start(self, clean_dirty_pidfile=False, with_status_inherit=True):
        self.ocf_log('ocfScript.status_start with clean_dirty_pidfile={} and with_status_inherit={}'.format(clean_dirty_pidfile, with_status_inherit), msglevel=5)
        statusfct = self.status if with_status_inherit else super(self.__class__, self).status
        return statusfct(clean_dirty_pidfile=clean_dirty_pidfile, check_pidfile=self.get_option('status_check_pidfile_for_start'), check_ppid=self.get_option('status_check_ppid_for_start'))
    
    ########################################
    def status_stop(self, clean_dirty_pidfile=False, with_status_inherit=True):
        self.ocf_log('ocfScript.status_stop with clean_dirty_pidfile={} and with_status_inherit={}'.format(clean_dirty_pidfile, with_status_inherit), msglevel=5)
        statusfct = self.status if with_status_inherit else super(self.__class__, self).status
        return statusfct(clean_dirty_pidfile=clean_dirty_pidfile, check_pidfile=self.get_option('status_check_pidfile_for_stop'), check_ppid=self.get_option('status_check_ppid_for_stop'))
    
    ########################################
    def status_monitor(self, clean_dirty_pidfile=False, with_status_inherit=True):
        self.ocf_log('ocfScript.status_monitor with clean_dirty_pidfile={} and with_status_inherit={}'.format(clean_dirty_pidfile, with_status_inherit), msglevel=5)
        statusfct = self.status if with_status_inherit else super(self.__class__, self).status
        return statusfct(clean_dirty_pidfile=clean_dirty_pidfile, check_pidfile=self.get_option('status_check_pidfile_for_monitor'), check_ppid=self.get_option('status_check_ppid_for_monitor'))
    
    ########################################
    def is_process_just_start(self, start_delay, check_ppid=True):
        '''start_delai in seconds'''
        self.ocf_log('ocfScript.is_process_just_start', msglevel=5)
        
        pids = self.get_first_pids(check_ppid=check_ppid)
        if not pids:
            # must not append
            msg = 'ocfScript.is_process_just_start : Can\'t find pids'
            self.ocf_log_err(msg)
            raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
    
        self.ocf_log('ocfScript.is_process_just_start : verifying {}'.format(pids), msglevel=4)
        for pid in pids:
            self.ocf_log('ocfScript.is_process_just_start : verifying {}'.format(pid), msglevel=4)
            if psutil.pid_exists(pid):
                try:
                    p = psutil.Process(pid)
                except:
                    msg = 'ocfScript.is_process_just_start error : pid {} does not exits anymore... should never happen'.format(pid)
                    self.ocf_log_err(msg)
                    raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
                    
                if time.time() <= p.create_time() + start_delay:
                    return True
        else:
            return False
            
    ########################################
    def read_satuts_socket(self, spath, default_return=True, stimeout=5.0, msgend='status-end', obsolete_data=None):
        '''
        Protocol : 
            connect to the socket and send 'status'
            reveived only one line with status:time:msgend
            status is 0 (working) or 1 (not working)
        Return True if work, False if not, default_return if undfined
        '''
        self.ocf_log('ocfScript.read_satuts_socket {}'.format(spath), msglevel=5)
        ret = default_return
        
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.connect(spath)
            sock.settimeout(stimeout)
        except socket.error as msg:
            self.ocf_log_err('read_satuts_socket {}: {}'.format(spath, msg))
        else:
            msg='status'
            self.ocf_log('ocfScript.read_satuts_socket {}, sending message \"{}\"'.format(spath, msg), msglevel=4)
            try:
                sock.sendall(msg)
            except:
                self.ocf_log_warn('status socket {} sending data problem'.format(spath))
            else:
                data = ''
                try:
                    data = sock.recv(64)
                except socket.timeout:
                    self.ocf_log_warn('status socket {} received timeout'.format(spath))
                except:
                    self.ocf_log_warn('status socket {} unknown errors'.format(spath))
                else:
                    self.ocf_log('ocfScript.read_satuts_socket {}, data received : \"{}\"'.format(spath, data), msglevel=4)
                    etat = data.split(':')
                    #print(etat)
                    nowts = time.time()
                    if not obsolete_data or nowts < float(etat[1])+obsolete_data:
                        if etat[0] == '0' and etat[2] == msgend:
                            self.ocf_log('ocfScript.read_satuts_socket {}, status socket said that program is working'.format(spath), msglevel=2)
                            ret = True
                        elif etat[0] == '1' and etat[2] == msgend:
                            self.ocf_log('ocfScript.read_satuts_socket {}, status socket said that program is not working'.format(spath), msglevel=2)
                            ret = False
                        else:
                            self.ocf_log_warn('status socket {} send incorrect data'.format(spath))
                    else:
                        self.ocf_log_warn('status socket {}: data too old'.format(spath))
            finally:
                sock.close()
            
        return ret
    
    ########################################
    def read_all_status_sockets(self, sockets_path, default_return=True, stimeout=5.0, msgend='status-end', need_all_false=False, obsolete_data=None):
        self.ocf_log('ocfScript.read_all_status_socket', msglevel=5)
        asp = sockets_path.rstrip(';').split(';')
        
        if need_all_false:
            cpt_false = 0
        for sp in asp:
            if not self.read_satuts_socket(sp, default_return, stimeout=stimeout, msgend=msgend, obsolete_data=obsolete_data):
                if need_all_false:
                    cpt_false += 1
                else:
                    if not sp in asp[-1]:
                        self.ocf_log('ocfScript.read_all_status_socket : {} failed, skipping others tests'.format(sp), msglevel=5)
                    return False
        
        if need_all_false and cpt_false == len(asp):
            return False
        else:
            return True
    
    ########################################
    def read_suspend_monitor_socket(self, spath, stimeout=5.0, msgend='state-end', let_socket_open=False, msg_wait=None):
        '''
        Protocol : 
            connect to the socket and send 'state'
            reveived only one line with state:timestamp:suspended time:msgend
            state is 0 (suspend) or 1 (not suspend)
        Return ret=data or None and None if let_socket_open=False
        Return ret=data or None and sock if let_socket_open=True
        '''
        self.ocf_log('ocfScript.read_suspend_monitor_socket {}'.format(spath), msglevel=5)
        ret = None

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.connect(spath)
            sock.settimeout(stimeout)
        except socket.error as msg:
            self.ocf_log_err('read_suspend_monitor_socket {}: the remote program does not write information to the socket'.format(spath))
            if not let_socket_open: sock = None
            sock = None
        else:
            msg='state'
            self.ocf_log('ocfScript.read_suspend_monitor_socket {}, sending message \"{}\"'.format(spath, msg), msglevel=4)
            try:
                sock.sendall(msg)
            except:
                self.ocf_log_warn('suspend monitor socket {} sending data problem'.format(spath))
            else:
                data = ''
                try:
                    data = sock.recv(64)
                except socket.timeout:
                    self.ocf_log_warn('suspend monitor socket {} received timeout'.format(spath))
                except:
                    self.ocf_log_warn('suspend monitor socket {} unknown errors'.format(spath))
                else:
                    self.ocf_log('ocfScript.read_suspend_monitor_socket {}, data received : \"{}\"'.format(spath, data), msglevel=4)
                    ret = data
                    if let_socket_open:
                        msg = msg_wait
                    else:
                        msg = msgend
                    try:
                        sock.sendall(msg)
                    except:
                        self.ocf_log_warn('suspend monitor socket {} sending message waiting: problem'.format(spath))
            finally:
                if not let_socket_open:
                    sock.close()
                    sock = None

        return ret,sock
    
    ########################################
    def crm_master(self, is_master=False):
        self.ocf_log('ocfScript.crm_master', msglevel=5)
        val='10' if is_master else '5'
        try:
            subprocess.check_call(['crm_master', '-l', 'reboot', '-v', val])
        except subprocess.CalledProcessError as cpe:
            self.ocf_log_err('crm_master error:{}, command line = {},'.format(cpe.returncode,cpe.cmd))
            raise
        except OSError as ose:
            self.ocf_log_err('crm_master error: {}'.format(ose.strerror))
            raise
        except:
            self.ocf_log_err('crm_master error: unknown error')
            raise

    ########################################
    def meta(self):
        '''generic meta fuction'''
        self.metadata.gen_meta()
        return self.ocfretcodes['OCF_SUCCESS']
    
    ########################################
    def change_user(self):
        self.ocf_log('ocfScript.change_user', msglevel=5)
        if self.get_option('user_cmd'):
            try:
                uid = pwd.getpwnam(self.get_option('user_cmd')).pw_uid
                gid = grp.getpwnam(self.get_option('user_cmd')).pw_uid
            except KeyError as ke:
                msg = 'change_user : Can\'t get uid for user {}: {}'.format(self.get_option('user_cmd'), ke)
                self.ocf_log_err(msg)
                raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
            except:
                msg = 'change_user : {}'.format(sys.exc_info())
                self.ocf_log_err(msg)
                raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
            
            def set_ids():
                os.setgid(uid)
                os.setuid(gid)

            return set_ids
        else:
            return None
    
    ########################################
    def start_status_loop(self, statusfct, start_time, force_stop):
        self.ocf_log('ocfScript.start_status_loop', msglevel=5)
        start_timeout = self.calc_timeout(ratio=self.get_option('starttimeoutratio')/1000, default_timeout=285)
        if self.get_option('start_force_stop_timeout') and force_stop:
            tmp_timeout = start_timeout - self.get_option('start_force_stop_timeout')
            start_timeout = tmp_timeout if tmp_timeout > 0 else start_timeout
        self.ocf_log('ocfScript.start_status_loop  : start timeout is {}'.format(start_timeout), msglevel=4)
        while time.time() - start_time < start_timeout:
            self.ocf_log('ocfScript.start_status_loop waiting {} seconds...'.format(self.get_option('sleepafterstart')), msglevel=3)
            time.sleep(self.get_option('sleepafterstart'))
            if statusfct() == self.ocfretcodes['OCF_SUCCESS']:
                self.ocf_log('started successfully.')
                return self.ocfretcodes['OCF_SUCCESS']
        else:
            self.ocf_log_err('Could not be started.')
            return self.ocfretcodes['OCF_ERR_GENERIC']
    
    ########################################
    def start(self, otheropts=[], with_status_inherit=True, without_loop=False):
        '''gereric start function'''
        self.ocf_log('ocfScript.start', msglevel=5)
        start_time = time.time()
        force_stop=False
        try:
            self.initialize()
        except ocfError as oe:
            return oe.err
            
        statusfct = self.status_start if with_status_inherit else super(self.__class__, self).status_start
        status = statusfct(clean_dirty_pidfile=self.get_option('monitor_clean_dirty_pidfile'))
        if status == self.ocfretcodes['OCF_SUCCESS'] or status == self.ocfretcodes['OCF_RUNNING_MASTER']:
            # If already running, consider start successful
            self.ocf_log('program is already running')
            return self.ocfretcodes['OCF_SUCCESS']
        elif not status == self.ocfretcodes['OCF_NOT_RUNNING']:
            self.ocf_log('status error, cleaning process by KILL and deleting pidfile.')
            force_stop=True
            if not self.stop(force_timeout=self.get_option('start_force_stop_timeout')) == self.ocfretcodes['OCF_SUCCESS']:
                return self.ocfretcodes['OCF_ERR_GENERIC']
        
        if self.get_option('msfile'):
            try: 
                self.write_msfile(is_master=False)
            except:
                self.ocf_log_err('problem for writing msfile.')
                return self.ocfretcodes['OCF_ERR_GENERIC']
                
            try:
                self.crm_master(is_master=False)
            except:
                self.ocf_log_err('problem during crm master command')
                return self.ocfretcodes['OCF_ERR_GENERIC']
                
                        
        # modify ulimit
        self.ocf_log('ocfScript.start ulimit={}'.format(self.get_option('process_file_ulimit')), msglevel=2)
        limit = self.get_option('process_file_ulimit')
        resource.setrlimit(resource.RLIMIT_NOFILE, (limit, limit))
                
        startopts = [self.get_option('binfile')]
        if self.get_option('binfileoptions'): startopts += self.get_option('binfileoptions').split(' ') 
        if otheropts: startopts += otheropts
        
        devnull = open(os.devnull, 'wb') # TODO try/except ?
        self.ocf_log('ocfScript.start starting process with options {}'.format(startopts), msglevel=2)
        try:
            process = subprocess.Popen(startopts, stdout=devnull, stderr=subprocess.STDOUT, preexec_fn=self.change_user(), cwd=self.get_option('change_workdir'))
            devnull.close()
        except OSError as ose:
            self.ocf_log_err('Could not be started : {}'.format(ose.strerror))
            return self.ocfretcodes['OCF_ERR_GENERIC']
        except:
            self.ocf_log_err('Could not be started')
            return self.ocfretcodes['OCF_ERR_GENERIC']
        if self.get_option('ocf_write_pidfile'):
            try:
                self.write_pids_in_pidfile([process.pid]) # TODO prevoir le cas du lancement de plusieurs instances
            except:
                return self.ocfretcodes['OCF_ERR_GENERIC']
        
        if without_loop:
            self.ocf_log('ocfScript.start  : start without loop', msglevel=4)
            return self.ocfretcodes['OCF_SUCCESS']
        else:
            return self.start_status_loop(statusfct, start_time, force_stop)
    
    ########################################
    def kill_pids(self, pids, sig):
        self.ocf_log('ocfScript.kill_pids', msglevel=5)
        for p in pids:
            try:
                os.kill(p, sig)
            except:
                self.ocf_log_warn('Error during kill of {}'.format(p))
                raise

    ########################################
    def stop_sig(self, sig, statusfct, timeout_ratio, sleep_after_sig, force_timeout=None):
        '''stop with kill sig'''
        self.ocf_log('ocfScript.stop_sig : kill{} step'.format(sig), msglevel=5)
        if force_timeout:
            stop_timeout = force_timeout
            stop_loop_timeout = stop_timeout - sleep_after_sig
        else:
            # Allow kill_ratio of the action timeout for the orderly shutdown
            # (The origin unit is ms, hence the conversion)
            # which meens kill_ratio/1000
            stop_timeout = self.calc_timeout(ratio=timeout_ratio/1000, default_timeout=240)
            stop_loop_timeout = stop_timeout - sleep_after_sig
        self.ocf_log('ocfScript.stop_sig : kill{} step, stop timeout is {}'.format(sig, stop_timeout), msglevel=4)
        
        # Use directly get_first_pids which will be the good pid
        pids = self.get_first_pids(check_ppid=self.get_option('status_check_ppid_for_stop'))
        
        if pids:
            try:
                self.kill_pids(pids, sig)
            except:
                self.ocf_log('ocfScript.stop_sig : self.kill_pids error for signal {}'.format(sig), msglevel=4)
                raise
            else:
                self.ocf_log('ocfScript.stop_sig for kill {} waiting {} seconds...'.format(sig, sleep_after_sig), msglevel=3)
                time.sleep(sleep_after_sig)
            
            # Deleting pidfile if binfile does not. Let's binfile who does deal with it
            if self.get_option('ocf_write_pidfile'):
                try:
                    self.remove_pidfile()
                except:
                    raise
                
            start_time = time.time()
            while time.time() - start_time < stop_loop_timeout:
                statusret = statusfct(clean_dirty_pidfile=self.get_option('monitor_clean_dirty_pidfile'))
                if statusret == self.ocfretcodes['OCF_NOT_RUNNING']:
                    break;
                # If binfile should deal with pidfile but have a problem, deleting pidfile. Could be redundant in certain case of monitor_clean_dirty_pidfile
                if not self.get_option('ocf_write_pidfile') and statusret not in [self.ocfretcodes['OCF_SUCCESS'],self.ocfretcodes['OCF_RUNNING_MASTER']]:
                    try:
                        self.ocf_log_warn('Deleting pidfile {} during stop due to a problem return by status fonction'.format(self.get_option('pidfile')))
                        self.remove_pidfile()
                    except:
                        raise
                self.ocf_log('ocfScript.stop_sig :  for signal {}, stop in progress.'.format(sig), msglevel=3)
                time.sleep(1)
            else:
                msg = 'Does not stop correctly in {}'.format(stop_timeout)
                self.ocf_log_warn(msg)
                raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
        else:
            msg = 'Can not get pid during signal {} step'.format(sig)
            self.ocf_log_warn( msg)
            raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
    
    ########################################
    def stop(self, with_status_inherit=True, force_timeout=None):
        '''generic stop function'''
        self.ocf_log('ocfScript.stop with force_timeout={}'.format(force_timeout), msglevel=5)
        try:
            self.initialize()
        except ocfError as oe:
            return oe.err
        
        statusfct = self.status_stop if with_status_inherit else super(self.__class__, self).status_stop
        status = statusfct(clean_dirty_pidfile=self.get_option('monitor_clean_dirty_pidfile'))
        if  status == self.ocfretcodes['OCF_NOT_RUNNING']:
            self.ocf_log('Program is already stop')
        else:
            try:
                self.stop_sig(signal.SIGTERM, statusfct, self.get_option('kill15_ratio'), self.get_option('sleepafterstop'),force_timeout=force_timeout)
            except:
                self.ocf_log_err('Error during SIGTERM (kill -15)')
            
        if statusfct(clean_dirty_pidfile=self.get_option('monitor_clean_dirty_pidfile')) == self.ocfretcodes['OCF_NOT_RUNNING']:
            self.ocf_log('Stop correctly')
        else:
            if self.get_option('kill3'):
                self.ocf_log_err('Error during SIGTERM (kill -15), using SIGQUIT (kill -3)')
                # Delete pidfile if it is still present. Should not happen : if pidfile is present here, somthing has restart binfile 
                try:
                    self.remove_pidfile()
                except:
                    return self.ocfretcodes['OCF_ERR_GENERIC']
        
                try:
                    self.stop_sig(signal.SIGQUIT, statusfct, self.get_option('kill3_ratio'), self.get_option('sleepaftersigquit'))
                except:
                    self.ocf_log_err('Error during SIGQUIT (kill -3)')
                    
                if statusfct(clean_dirty_pidfile=self.get_option('monitor_clean_dirty_pidfile')) == self.ocfretcodes['OCF_NOT_RUNNING']:
                    self.ocf_log('SIGQUIT (kill -3) did the job.')
                else:
                    if self.get_option('kill9'):
                        self.ocf_log_warn('Failed to stop with SIGQUIT (kill -3), using SIGKILL (kill -9)')
                        try:
                            self.stop_sig(signal.SIGKILL, statusfct, self.get_option('kill9_ratio'), self.get_option('sleepaftersigkill'))
                        except:
                            self.ocf_log_err('Error during SIGKILL')
                            
                        if statusfct(clean_dirty_pidfile=self.get_option('monitor_clean_dirty_pidfile')) == self.ocfretcodes['OCF_NOT_RUNNING']:
                            self.ocf_log('SIGKILL (kill -9) did the job.')
                        else:
                            self.ocf_log_err('Impossible to stop program with SIGKILL (kill -9)')
                            return self.ocfretcodes['OCF_ERR_GENERIC']
                    else:
                        self.ocf_log_err('Impossible to stop program with SIGQUIT (kill -3)')
                        return self.ocfretcodes['OCF_ERR_GENERIC']
            else:
                self.ocf_log_err('Impossible to stop program with SIGTERM (kill -15)')
                return self.ocfretcodes['OCF_ERR_GENERIC']

        if self.get_option('msfile'):
            self.ocf_log('ocfScript.stop : delete MS file {}'.format(self.get_option('msfile')), msglevel=4)
            try:
                self.delete_msfile()
            except:
                return self.ocfretcodes['OCF_ERR_GENERIC']

        return self.ocfretcodes['OCF_SUCCESS']
    
    ########################################
    def restart(self):
        '''generic restart function'''
        self.ocf_log('ocfScript.restart', msglevel=5)
        rs = self.stop()
        if rs == self.ocfretcodes['OCF_SUCCESS']:
            rs = self.start()
        return rs
    
    ########################################
    def promote(self):
        '''generic promote function'''
        self.ocf_log('ocfScript.promote', msglevel=5)
        try:
            self.initialize()
            msret = self.read_msfile()
        except ocfError as oe:
            return oe.err
        
        if msret == self.slave:
            try: 
                self.write_msfile(is_master=True)
            except:
                self.ocf_log_err('problem for writing msfile.')
                return self.ocfretcodes['OCF_ERR_GENERIC']
            
            try:
                self.crm_master(is_master=True)
            except:
                self.ocf_log_err('problem crm master command')
                return self.ocfretcodes['OCF_ERR_GENERIC']
        
        self.ocf_log('Node {} was promote successfully'.format(self.nodename))
        return self.ocfretcodes['OCF_SUCCESS']
    
    ########################################
    def demote(self):
        '''generic demote function'''
        self.ocf_log('ocfScript.demote', msglevel=5)
        try:
            self.initialize()
            msret = self.read_msfile()
        except ocfError as oe:
            return oe.err
        
        if msret == self.master:
            try: 
                self.write_msfile(is_master=False)
            except:
                self.ocf_log_err('problem for writing msfile.')
                return self.ocfretcodes['OCF_ERR_GENERIC']
            
            try:
                self.crm_master(is_master=False)
            except:
                self.ocf_log_err('problem crm master command')
                return self.ocfretcodes['OCF_ERR_GENERIC']
        
        self.ocf_log('Node {} was demote successfully'.format(self.nodename))
        return self.ocfretcodes['OCF_SUCCESS']
    
    ########################################
    def monitor(self):
        '''generic monitor function'''
        self.ocf_log('ocfScript.monitor', msglevel=5)
        try:
            self.initialize()
        except ocfError as oe:
            return oe.err
            
        ret = self.status_monitor(clean_dirty_pidfile=self.get_option('monitor_clean_dirty_pidfile'))
        if ret == self.ocfretcodes['OCF_SUCCESS']:
            self.ocf_log('{} is running'.format(self.get_option('binfile')), msglevel=1)
        elif ret == self.ocfretcodes['OCF_RUNNING_MASTER']:
            self.ocf_log('{} is running and is master'.format(self.get_option('binfile')), msglevel=1)
        elif ret == self.ocfretcodes['OCF_NOT_RUNNING']:
            self.ocf_log('{} is not running'.format(self.get_option('binfile')), msglevel=1)
        
        return ret

    ########################################
    def __validate_opt_noneisok(self, opt, noneisok):
        '''
        raise ocfError if None is not ok
        '''
        if not self.get_option(opt) and not noneisok:
            msg = '{} must be defined'.format(opt, self.get_option(opt))
            self.ocf_log_err(msg)
            raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], msg)
    
    ########################################
    def validate_opt_number(self, opt, min=None, max=None, nbrtype=int, noneisok=False):
        '''
        raise ocfError if it does not correspond to ocfScript conditions
        '''
        try:
            self.__validate_opt_noneisok(opt, noneisok)
        except:
            raise
        else:
            if not  isinstance(self.get_option(opt), nbrtype):
                msg = 'In {}, {} is not a number'.format(opt, self.get_option(opt))
                self.ocf_log_err(msg)
                raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], msg)
            if min and self.get_option(opt) < min:
                msg = 'For {}, number={} : minimum is {}'.format(opt, self.get_option(opt), min)
                self.ocf_log_err(msg)
                raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], msg)
            if max and self.get_option(opt) > max:
                msg = 'For {}, number={} : maximum is {}'.format(opt, self.get_option(opt), max)
                self.ocf_log_err(msg)
                raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], msg)
            
    ########################################
    def validate_opt_user(self, opt, noneisok=False):
        '''raise KeyError if user does not exist'''
        try:
            self.__validate_opt_noneisok(opt, noneisok)
        except:
            raise
        else:
            try: 
                pwd.getpwnam(self.get_option(opt)).pw_uid
            except:
                self.ocf_log_err('In {}, user {} does not exist '.format(opt, self.get_option(opt)))
                raise
    
    ########################################
    def validate_opt_group(self, opt, noneisok=False):
        '''raise KeyError is group does not exist'''
        try:
            self.__validate_opt_noneisok(opt, noneisok)
        except:
            raise
        else:
            try:
                grp.getgrnam(self.get_option(opt)).gr_gid
            except:
                self.ocf_log_err('In {}, group {} does not exist '.format(opt, self.get_option(opt)))
                raise
            
    ########################################
    def validate_opt_bool(self, opt, noneisok=False):
        '''
        raise ocfError if it does not correspond to a boolean
        '''
        try:
            self.__validate_opt_noneisok(opt, noneisok)
        except:
            raise
        else:
            if not  isinstance(self.get_option(opt), bool):
                msg = 'In {}, {} is not a boolean'.format(opt, self.get_option(opt))
                self.ocf_log_err(msg)
                raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], msg)

        
    ########################################
    def validate_opt_list(self, opt, validopts, noneisok=False, nbvaluesmax=None):
        try:
            self.__validate_opt_noneisok(opt, noneisok)
        except:
            raise
        else:
            if not  isinstance(self.get_option(opt), list):
                msg = 'In {}, {} is not a list'.format(opt, self.get_option(opt))
                self.ocf_log_err(msg)
                raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], msg)
            if nbvaluesmax and len(self.get_option(opt)) > nbvaluesmax:
                msg = 'In {}, only {} value(s) is(are) allowed.'.format(opt, self.get_option(opt), nbvaluesmax)
                self.ocf_log_err(msg)
                raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], msg)
            if not set(validopts) >= set(self.get_option(opt)):
                msg = 'In {}, somme values {} are not in the valid list options {}'.format(opt, self.get_option(opt), validopts)
                self.ocf_log_err(msg)
                raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], msg)

    ########################################
    def validate_read_access(self, path, user, group):
        '''
        raise KeyError if user or group does not exist
        raise ocfError if it does not correspond to ocfScript conditions
        '''
        if not os.path.exists(path):
            msg = '{} does not exist '.format(path)
            self.ocf_log_err(msg)
            raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], msg)
            
        try:
            st = os.stat(path)
            uid = pwd.getpwnam(user).pw_uid
            gid = grp.getgrnam(group).gr_gid
        except OSError:
            self.ocf_log_err('can\'t do stat on {}'.format(path))
            raise
        except KeyError:
            self.ocf_log_err('can\'t find uid or gid for {} and {}'.format(user, group))
            raise
        except:
            msg = 'validate_read_access unexpected error'
            self.ocf_log_err(msg)
            raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], msg)
            
        if  not(st.st_uid == uid and bool(st.st_mode & stat.S_IRUSR) or st.st_gid == gid and bool(st.st_mode & stat.S_IRGRP)):
            msg = '{} is not readable by user {} with uid {} or group {} with gid {}'.format(path, user, uid, group, gid)
            self.ocf_log_err(msg)
            raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], msg)

    ########################################
    def validate_kill_ratio(self):
        try:
            # kill15_ratio
            self.validate_opt_number('kill15_ratio', min=0, max=1.0, type=float)
            # kill3_ratio
            self.validate_opt_number('kill3_ratio', min=0, max=1.0, type=float)
            # kill9_ratio
            self.validate_opt_number('kill9_ratio', min=0, max=1.0, type=float)
            if self.get_option('kill15_ratio')+self.get_option('kill3_ratio')+self.get_option('kill9_ratio') > 1:
                msg = 'kill ratio error: kill3_ratio({})+kill15_ratio({})+kill9_ratio({})>1'.format(self.get_option('kill15_ratio'), self.get_option('kill3_ratio'), self.get_option('kill9_ratio'))
                self.ocf_log_err(msg)
                raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], msg)
        except:
            raise

    ########################################
    def validate_ocf_default_options(self):
        '''raise ocfError'''
        # binfile
        if not os.path.isfile(self.get_option('binfile')) or (os.path.isfile(self.get_option('binfile')) and not os.access(self.get_option('binfile'), os.X_OK)):
            msg = 'does not exist or is not executable'
            self.ocf_log_err(msg)
            raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], msg)

        try:
            # loglevel
            self.validate_opt_number('loglevel', min=0, max=5)
            # maxnbprocess
            self.validate_opt_number('maxnbprocess', min=-1)
            # sleepafterstart
            self.validate_opt_number('sleepafterstart', min=0)
            # starttimeoutratio
            self.validate_opt_number('starttimeoutratio', min=0, max=1.0, type=float)
            # sleepafterstop
            self.validate_opt_number('sleepafterstop', min=0)
            # sleepaftersigquit
            self.validate_opt_number('sleepaftersigquit', min=0)
            # sleepaftersigkill
            self.validate_opt_number('sleepaftersigkill', min=0)
            # kill3
            self.validate_opt_bool('kill3')
            # kill9 first part
            self.validate_opt_bool('kill9')
            # kill*_ratio
            self.validate_kill_ratio()
            # monitor_clean_dirty_pidfile
            self.validate_opt_bool('monitor_clean_dirty_pidfile')
            # start_force_stop_timeout
            self.validate_opt_number('start_force_stop_timeout', min=0, noneisok=True)
            # status_check_ppid
            #self.validate_opt_bool('status_check_ppid')
            # status_check_pidfile
            #self.validate_opt_bool('status_check_pidfile')
            # fixdirs
            self.fixdirs(fix=False)
            # process_file_ulimit
            self.validate_opt_number('process_file_ulimit', min=1024)
        except:
            raise
        else:
            # kill9 second part
            if self.get_option('kill9') == 'True' and self.get_option('kill3') == 'False':
                msg = 'kill9 configuration error : can not be true is kill3=false'
                self.ocf_log_err(msg)
                raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], msg)
            
            
    ########################################
    def infonotify(self):
        '''gerenic notify function'''

        self.ocf_log('ocfScript.infonotify', msglevel=5)
        
        try: self.notify_infos.n_type = os.environ.get('OCF_RESKEY_CRM_meta_notify_type')
        except: self.notify_infos.n_type = None
        
        try: self.notify_infos.n_op = os.environ.get('OCF_RESKEY_CRM_meta_notify_operation')
        except: self.notify_infos.n_op = None
        
        try: self.notify_infos.n_active = os.environ.get('OCF_RESKEY_CRM_meta_notify_active_uname').split()
        except: self.notify_infos.n_active  = None
        
        try: self.notify_infos.n_stop = os.environ.get('OCF_RESKEY_CRM_meta_notify_stop_uname').split()
        except: self.notify_infos.n_stop = None
        
        try: self.notify_infos.n_start = os.environ.get('OCF_RESKEY_CRM_meta_notify_start_uname').split()
        except: self.notify_infos.n_start = None
        
        try: self.notify_infos.n_master = os.environ.get('OCF_RESKEY_CRM_meta_notify_master_uname').split()
        except: self.notify_infos.n_master = None
        
        try: self.notify_infos.n_promote = os.environ.get('OCF_RESKEY_CRM_meta_notify_promote_uname').split()
        except: self.notify_infos.n_promote = None
        
        try: self.notify_infos.n_demote = os.environ.get('OCF_RESKEY_CRM_meta_notify_demote_uname').split()
        except: self.notify_infos.n_demote = None
        
        self.ocf_log('ocfScript.infonotify : n_type={}, n_op={}, n_active={}, n_stop={}, n_start={}, n_master={}, n_promote={}, n_demote={}'.format(self.notify_infos.n_type, self.notify_infos.n_op, self.notify_infos.n_active, self.notify_infos.n_stop, self.notify_infos.n_start, self.notify_infos.n_master, self.notify_infos.n_promote, self.notify_infos.n_demote), msglevel=4)
            
        return self.ocfretcodes['OCF_SUCCESS']

    ########################################
    def notify(self):
        '''gerenic notify function'''
        self.ocf_log('ocfScript.notify', msglevel=5)
        try:
            self.initialize()
            self.ocf_log('Notify : n_type={}, n_op={}, n_active={}, n_stop={}, n_start={}, n_master={}, n_promote={}, n_demote={}'.format(self.notify_infos.n_type, self.notify_infos.n_op, self.notify_infos.n_active, self.notify_infos.n_stop, self.notify_infos.n_start, self.notify_infos.n_master, self.notify_infos.n_promote, self.notify_infos.n_demote), msglevel=3)
        except ocfError as oe:
            return oe.err
        
        return self.ocfretcodes['OCF_SUCCESS']
 
    ########################################
    def validate(self):
        '''generic validate function'''
        self.ocf_log('ocfScript.validate', msglevel=5)
        
        try:
            self.validate_ocf_default_options()
        except ocfError as oe:
            self.ocf_log_err('Error during validate: {}'.format(oe.strerr))
            ret = oe.err
        else:
            ret = self.ocfretcodes['OCF_SUCCESS']

        return ret

    ########################################
    def initialize(self):
        self.ocf_log('ocfScript.initialize', msglevel=5)
        try:
            self.fixdirs()
            self.init_pidfile()
            if self.get_option('msfile'): self.init_dir(os.path.dirname(self.get_option('msfile')))
            self.infonotify()
        except :
            msg='Error during ocfscript initialize (see previous error log)'
            self.ocf_log_err(msg)
            raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)

    ########################################
    def run(self, arg):
        '''run the script in fonction of arg'''
        self.ocf_log('ocfScript.run {}'.format(arg), msglevel=3)
        try:
            self.set_defaults(arg)
        except ocfError as oe:
            return oe.err
      
        if arg in self.runoptions:
            return self.runoptions[arg]()
        else:
            return self.ocfretcodes['OCF_ERR_GENERIC']
