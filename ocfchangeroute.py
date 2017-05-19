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
ocfChangeRoute script for chaning network routes
Need python-psutil 2.1.1 and python-pyroute2 0.4.2

Configile format :
[DEFAULT]
# order for actions at start
startorder='ADD,DEL,MODIFY'
# order for actions at stop. In case of stop
# "DEL" means: execute the actions of the "DEL" block to reset the rules that were deleted at startup.
# "ADD" means: execute the actions of the "ADD" block to remove the add rules at startup.
stoporder='DEL,ADD,RESTORE'
# log routes configuration : True/False
logconfig=False

[ADD]
# routes to add at start and del at stop
route1=
route2=...
route3=...
...

[DEL]
# route to del at start and add at start
route1=
route2=...
route3=...
...

[MODIFY]
# route to modify at start
route1=
route2=...
route3=...
...

[RESTORE]
# route to restore at stop
route1=
route2=...
route3=...
...

The format ot a route is directly the dict of pyroute2 to avoid the necessity to describe a specifique configfile format.
An exception is the oid value. it could be pass as an index (like in pyroute dict) o with the interface's name which will be converted
"""

import argparse, configparser, sys, os, syslog, ast, time
from ocfscripts import ocfScript, ocfError
from ocfreturncodes import ocfReturnCodes
from pyroute2 import IPDB

################################################################################
class ocfRoutesAction(object):
    ########################################
    def __init__(self, action, function4start=None, function4stop=None, routesdesc=None):
        self.action = action
        self.function4start = function4start
        self.function4stop = function4stop
        self.routesdesc = [] if not routesdesc else list(routesdesc)
        
    ########################################
    def add_routedesc(self, routedict):
        self.routesdesc.append(dict(routedict))


################################################################################
class ocfChangeRoute(ocfScript):
    ########################################
    def __init__(self):
        try:
            super(ocfChangeRoute, self).__init__('ocfChangeRoute', 'This is the ocf script to manage any daemon', 'manage any daemon.', None, None, \
                binfile_is_ra_opt=False, pidfile_is_ra_opt=False, piddir_owner_is_ra_opt=False,  piddir_group_is_ra_opt=False,  piddir_mod_is_ra_opt=False, \
                binfileoptions_is_ra_opt=False, maxnbprocess_is_ra_opt=False, \
                commande_line_searched_is_ra_opt=False, fixdirs_is_ra_opt=False, \
                default_kill3=False, kill3_is_ra_opt=False, kill9_is_ra_opt=False, \
                default_ocf_write_pidfile=False, ocf_write_pidfile_is_ra_opt=False, \
                default_monitor_clean_dirty_pidfile=False, monitor_clean_dirty_pidfile_is_ra_opt=False, \
                default_sleepafterstart=1, default_sleepafterstop=1, starttimeoutratio_is_ra_opt=False, \
                start_force_stop_timeout_is_ra_opt=False, process_file_ulimit_is_ra_opt=False, status_check_ppid_is_ra_opt=False, status_check_pidfile_is_ra_opt=False)
        except:
            raise
        
        # Options supplémentaires
        self.init_from_env('configfile', 'path to configuration file.', 'path to configuration file.', required=1)
        
        self.actions4routes = { \
            'ADD': ocfRoutesAction('ADD', function4start=self.add_route, function4stop=self.del_route), \
            'DEL': ocfRoutesAction('DEL', function4start=self.del_route, function4stop=self.add_route), \
            'MODIFY': ocfRoutesAction('MODIFY', function4start=self.modify_route), \
            'RESTORE': ocfRoutesAction('RESTORE', function4stop=self.modify_route)
            }
        self.ipdb = IPDB()

    ########################################
    def __del__(self):
        self.ipdb.release()
    
    ########################################
    def ipdb_commit_and_reload(self):
        try: 
            self.ipdb.commit()
            self.ipdb.release()
            self.ipdb = IPDB()
        except:
            raise
    
    ########################################
    def get_routes(self, action):
        for x in self.actions4routes[action].routesdesc:
            yield x

    ########################################
    def log_configuration(self):
        self.ocf_log('ocfChangeRoute.log_configuration', msglevel=5)
        for action in self.actions4routes:
            for route in self.get_routes(action):
                self.ocf_log('ocfChangeRoute.log_configuration: {} {}'.format(self.actions4routes[action].action, route))
    
    ########################################
    def initialize(self):
        self.ocf_log('ocfChangeRoute.initialize', msglevel=5)
        try:
            confparser = configparser.ConfigParser()
            confparser.read(self.get_option('configfile'))
            
            self.actions_order_start = confparser.get('DEFAULT', 'startorder', fallback='ADD,DEL,MODIFY').rstrip(',').split(',')
            if not set(self.actions4routes) >= set(self.actions_order_start):
                msg = 'ocfChangeRoute.initialize: actions_order_start, forbiden action in {}'.format(self.actions_order_start)
                self.ocf_log(msg, msglevel=0)
                raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
            else:
                self.ocf_log('ocfChangeRoute.initialize: actions_order_start = {}'.format(self.actions_order_start), msglevel=4)
                
            self.actions_order_stop = confparser.get('DEFAULT', 'stoporder', fallback='DEL,ADD,RESTORE').rstrip(',').split(',')
            if not set(self.actions4routes) >= set(self.actions_order_stop):
                msg = 'ocfChangeRoute.initialize: actions_order_stop, forbiden action in {}'.format(self.actions_order_stop)
                self.ocf_log(msg, msglevel=0)
                raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
            else:
                self.ocf_log('ocfChangeRoute.initialize: actions_order_stop = {}'.format(self.actions_order_stop), msglevel=4)
            
            self.log_config = confparser.getboolean('DEFAULT', 'logconfig', fallback=False)
            self.ocf_log('ocfChangeRoute.initialize: log_config = {}'.format(self.log_config), msglevel=4)
            for x in self.actions4routes:
                self.read_configfile_rules_block(confparser, x)

            '''
            TODO mode FULL : give all routes configuration, 
            @star: save all actuals routes in a file, delete it, add all new routes
            @stop: delete all routes, restore all saved routes
            @monitor: search routes configured or routes saved
            [DEFAULT]
            mode_full=True/False
            [FULL]
            savepath=/foo/bar/myfile
            route1=...
            route2=...
            '''
        except:
            self.ocf_log('ocfChangeRoute.initialize: error during reading configfile', msglevel=5)
            raise
        else:
            if self.log_config: self.log_configuration()
            self.ocf_log('ocfChangeRoute.initialize: initilization success', msglevel=5)
    
    ########################################
    def read_configfile_rules_block(self, confparser, block):
        self.ocf_log('ocfChangeRoute.read_configfile_rules_block: {}'.format(block), msglevel=5)
        r=0
        while True:
            try:
                r+=1
                self.ocf_log('ocfChangeRoute.read_configfile_rules_block: trying to read route{} for {}'.format(r, block), msglevel=5)
                routeline = confparser.get(block, 'route{}'.format(r))
                routedict = ast.literal_eval(routeline)
                if routedict['oif'] in self.ipdb.interfaces:
                    if not isinstance(routedict['oif'], int):
                        # Oif is not an index, converting "interface" to index if interface is valid
                        routedict['oif'] = self.ipdb.interfaces[routedict['oif']].index
                    # TODO control
                    self.ocf_log('ocfChangeRoute.read_configfile_rules_block: for {} adding {}'.format(block, routedict), msglevel=5)
                    self.actions4routes[block].add_routedesc(routedict)
                else:
                    msg = 'ocfChangeRoute.read_configfile_rules_block: interface {} in route {} (in {}) does not exist'.format(routedict['oif'], routeline, block)
                    self.ocf_log(msg, msglevel=0)
                    raise ocfError(self.ocfretcodes['OCF_ERR_CONFIGURED'], msg)
            except SyntaxError:
                self.ocf_log('ocfChangeRoute.read_configfile_rules_block: invalid syntax for {} in {}'.format(routeline, block), msglevel=0)
                raise
            except configparser.NoOptionError:
                self.ocf_log('ocfChangeRoute.read_configfile_rules_block: no more routes for {}'.format(block), msglevel=5)
                break
            except configparser.NoSectionError:
                self.ocf_log('ocfChangeRoute.read_configfile_rules_block: no route for {}'.format(block), msglevel=5)
                break
            except Exception as err:
                self.ocf_log('ocfChangeRoute.read_configfile_rules_block: Error during file parsing: {}'.format(err), msglevel=0)
                raise
        
    ########################################
    def add_route(self, adddict):
        self.ocf_log('ocfChangeRoute.add_route: adding route {}'.format(adddict), msglevel=5)
        try:
            self.ipdb.routes.add(adddict)
        except Exception as err: 
            self.ocf_log('ocfChangeRoute.add_route Error: {}'.format(err), msglevel=0)
            raise
        
    ########################################
    def del_route(self, deldict):
        self.ocf_log('ocfChangeRoute.del_route: deleting route {}'.format(deldict), msglevel=5)
        try:
            self.ipdb.routes.remove(deldict['dst'])
        except Exception as err: 
            self.ocf_log('ocfChangeRoute.del_route Error: {}'.format(err), msglevel=0)
            raise
    
    ########################################
    def modify_route(self, modifydict):
        self.ocf_log('ocfChangeRoute.modify_route: modifying route {}'.format(modifydict), msglevel=5)
        try:
            for x in modifydict:
                self.ipdb.routes[modifydict['dst']][x] = modifydict[x]
        except Exception as err: 
            self.ocf_log('ocfChangeRoute.modify_route Error: {}'.format(err), msglevel=0)
            raise
     
     ########################################
    def list_routesdict(self, action):
        for x in self.actions4routes[action].routesdesc:
            yield x

    ########################################
    def routes_status(self, action):
        '''
        return OCF_SUCCESS if all routes are found
        return OCF_NOT_RUNNING if no routes are found
        return OCF_ERR_GENERIC if only some routes are found
        return OCF_ERR_UNIMPLEMENTED if no route
        raise if ipdb can be used
        '''
        nberr=0
        nbroutes=0
        try:
            for routedef in self.get_routes(action):
                nbroutes += 1
                if 'dst' in routedef:
                    if routedef['dst'] in self.ipdb.routes:
                        for x in routedef:
                            if x in self.ipdb.routes[routedef['dst']] and routedef[x] != self.ipdb.routes[routedef['dst']][x]:
                                nberr += 1
                                self.ocf_log('ocfChangeRoute.routes_status {0}: for route {1}, config {2}:{3}, real {2}:{4}'.format(action, routedef['dst'], x, routedef[x], self.ipdb.routes[routedef['dst']][x]), msglevel=5)
                                break
                        else:
                            self.ocf_log('ocfChangeRoute.routes_status {}: route {} found with the correct configuration'.format(action, routedef['dst']), msglevel=5)
                    else:
                        nberr += 1
                        self.ocf_log('ocfChangeRoute.routes_status {}: no route {} found'.format(action, routedef['dst']), msglevel=5)
                else:
                    msg = '"dst" not in {} in {}'.format(routedef, action)
                    self.ocf_log(msg, msglevel=0)
                    raise ocfError(self.ocfretcodes['OCF_ERR_GENERIC'], msg)
                
            if nbroutes == 0:
                return self.ocfretcodes['OCF_ERR_UNIMPLEMENTED']
            else:
                if nberr == 0:
                    return self.ocfretcodes['OCF_SUCCESS']
                elif nberr == nbroutes:
                    return self.ocfretcodes['OCF_NOT_RUNNING']
                else:
                    return self.ocfretcodes['OCF_ERR_GENERIC']
        except Exception as err:
            self.ocf_log('ocfChangeRoute.routes_status: {}'.format(err))
            raise
        

    ########################################
    def status(self):
        self.ocf_log('ocfChangeRoute.status', msglevel=5)
        try:
            add_ret = self.routes_status('ADD')
            del_ret = self.routes_status('DEL')
            modidy_ret = self.routes_status('MODIFY')
            restore_ret = self.routes_status('RESTORE')
            
            if add_ret in [self.ocfretcodes['OCF_NOT_RUNNING'], self.ocfretcodes['OCF_ERR_UNIMPLEMENTED']] and \
                del_ret in [self.ocfretcodes['OCF_SUCCESS'], self.ocfretcodes['OCF_ERR_UNIMPLEMENTED']] and \
                modidy_ret in [self.ocfretcodes['OCF_NOT_RUNNING'], self.ocfretcodes['OCF_ERR_UNIMPLEMENTED']] and \
                restore_ret in [self.ocfretcodes['OCF_SUCCESS'], self.ocfretcodes['OCF_ERR_UNIMPLEMENTED']]:
                self.ocf_log('ocfChangeRoute.status: routes are stopped', msglevel=5)
                return self.ocfretcodes['OCF_NOT_RUNNING']
            elif add_ret in [self.ocfretcodes['OCF_SUCCESS'], self.ocfretcodes['OCF_ERR_UNIMPLEMENTED']] and \
                del_ret in [self.ocfretcodes['OCF_NOT_RUNNING'], self.ocfretcodes['OCF_ERR_UNIMPLEMENTED']] and \
                modidy_ret in [self.ocfretcodes['OCF_SUCCESS'], self.ocfretcodes['OCF_ERR_UNIMPLEMENTED']] and \
                restore_ret in [self.ocfretcodes['OCF_NOT_RUNNING'], self.ocfretcodes['OCF_ERR_UNIMPLEMENTED']]:
                self.ocf_log('ocfChangeRoute.status: routes are started', msglevel=5)
                self.ocfretcodes['OCF_SUCCESS']
            else:
                self.ocf_log('ocfChangeRoute.status: routes error add={}, del={}, modify={}, restore={}'.format(add_ret, del_ret, modidy_ret, restore_ret), msglevel=4)
                return self.ocfretcodes['OCF_ERR_GENERIC']
        except Exception as err:
            raise

    ########################################
    def monitor(self):
        self.ocf_log('ocfChangeRoute.monitor', msglevel=5)
        try:
            self.initialize()
            return self.status()
        except Exception as err:
            self.ocf_log('ocfChangeRoute.monitor: error during monitor: {}'.format(err))
            return self.ocfretcodes['OCF_ERR_GENERIC']
    
    ########################################
    def start(self):
        self.ocf_log('ocfChangeRoute.start', msglevel=5)
        try:
            self.initialize()
            self.ocf_log('ocfChangeRoute.start: actions will be processed in this order: {}'.format(self.actions_order_stop), msglevel=5)
            for action in self.actions_order_start:
                self.ocf_log('ocfChangeRoute.start: Treatment of {}'.format(action), msglevel=5)
                for routedef in self.get_routes(action):
                    if self.actions4routes[action].function4start:
                        self.actions4routes[action].function4start(routedef)
            self.ocf_log('ocfChangeRoute.stop: commiting routes change', msglevel=5)
            self.ipdb_commit_and_reload()
            self.ocf_log('ocfChangeRoute.start: waiting {} seconds...'.format(self.get_option('sleepafterstart')), msglevel=3)
            time.sleep(self.get_option('sleepafterstart'))
            status = self.status()
            if status == self.ocfretcodes['OCF_NOT_RUNNING'] or status == self.ocfretcodes['OCF_ERR_GENERIC']:
                self.ocf_log('ocfChangeRoute.start: can not start new routes')
                return status
        except Exception as err:
            self.ocf_log('ocfChangeRoute.start: error during start: {}'.format(err))
            return self.ocfretcodes['OCF_ERR_GENERIC']
        else:
            self.ocf_log('ocfChangeRoute.start: start sucessfully')
            return self.ocfretcodes['OCF_SUCCESS']
    
    ########################################
    def stop(self):
        '''generic stop function'''
        self.ocf_log('ocfChangeRoute.stop', msglevel=5)
        try:
            self.initialize()
            self.ocf_log('ocfChangeRoute.stop: actions will be processed in this order: {}'.format(self.actions_order_stop), msglevel=5)
            for action in self.actions_order_stop:
                self.ocf_log('ocfChangeRoute.stop: Treatment of {}'.format(action), msglevel=5)
                for routedef in self.get_routes(action):
                    if self.actions4routes[action].function4stop:
                        self.actions4routes[action].function4stop(routedef)
            self.ocf_log('ocfChangeRoute.stop: commiting routes change', msglevel=5)
            self.ipdb_commit_and_reload()
            self.ocf_log('ocfChangeRoute.stop: waiting {} seconds...'.format(self.get_option('sleepafterstop')), msglevel=3)
            time.sleep(self.get_option('sleepafterstop'))
            status = self.status()
            if status == self.ocfretcodes['OCF_SUCCESS'] or status == self.ocfretcodes['OCF_ERR_GENERIC']:
                self.ocf_log('ocfChangeRoute.stop: can not stop routes')
                return status
        except Exception as err:
            self.ocf_log('ocfChangeRoute.stop: error during stop: {}'.format(err))
            return self.ocfretcodes['OCF_ERR_GENERIC']
        else:
            self.ocf_log('ocfChangeRoute.stop: stop sucessfully')
            return self.ocfretcodes['OCF_SUCCESS']
    
################################################################################
def main():
    try:
        s = ocfChangeRoute()
    except ocfError as oe:
        syslog.syslog(syslog.LOG_ERR, oe.strerror)
        sys.exit(oe.err)
    except:
        sys.exit(ocfReturnCodes()['OCF_ERR_GENERIC'])
    else:
        parser = argparse.ArgumentParser (description='Ocf script changeroute.')
        parser.add_argument ('type', help='Option to launch the ocf script.', action='store', choices=s.choices)
        args = parser.parse_args()
        
        sys.exit(s.run(args.type))

################################################################################
if __name__ == '__main__':
    main()