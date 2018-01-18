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
ocfAnything script corosync python
nécessite l'installation du module python-psutil
"""

import argparse, sys, os, syslog
from ocfscripts import ocfScript, ocfError
from ocfreturncodes import ocfReturnCodes

################################################################################
class ocfAnything(ocfScript):
    ########################################
    def __init__(self):
        try:
            super(ocfAnything, self).__init__('ocfAnything', \
                'This is the ocf script to manage any daemon', \
                'manage any daemon.', \
                None, \
                None, \
                pidfile_is_required=1, \
                ocf_write_pidfile_is_ra_opt=True, \
                user_cmd_is_ra_opt=True, \
                change_workdir_is_ra_opt=True, \
                status_check_ppid_is_ra_opt=True, \
                status_check_pidfile_is_ra_opt=True)
        except:
            raise
        
        # Options supplémentaires
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

    ########################################
    def validate(self):
        self.ocf_log('ocfAnything.validate', msglevel=5)
        try:
            self.validate_ocf_default_options()
            # TODO status_socket
            self.validate_opt_bool('default_status_socket_return')
            self.validate_opt_number('status_socket_timeout', nbrtype=float, min=1.0)
            self.validate_opt_number('status_socket_obsolete_data', min=1)
            self.validate_opt_bool('status_socket_need_all_on_error')
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
    def status_monitor(self, clean_dirty_pidfile=False, with_status_inherit=True):
        self.ocf_log('ocfAnything.status_monitor with clean_dirty_pidfile={}'.format(clean_dirty_pidfile), msglevel=5)
        sret = super(ocfAnything, self).status_monitor(clean_dirty_pidfile=clean_dirty_pidfile)
        if sret == self.ocfretcodes['OCF_SUCCESS'] and self.get_option('status_socket'):
            self.ocf_log('ocfAnything.status_monitor status_socket', msglevel=4)
            if not self.read_all_status_sockets(self.get_option('status_socket'), default_return=self.get_option('default_status_socket_return'), stimeout=self.get_option('status_socket_timeout'), need_all_false=self.get_option('status_socket_need_all_on_error'), obsolete_data=self.get_option('status_socket_obsolete_data')):
                return self.status_error('ocfAnything.status_monitor, status sockets return a failed state.')
        return sret

################################################################################
def main():
    try:
        s = ocfAnything()
    except ocfError as oe:
        syslog.syslog(syslog.LOG_ERR, oe.strerror)
        sys.exit(oe.err)
    except:
        sys.exit(ocfReturnCodes()['OCF_ERR_GENERIC'])
    else:
        parser = argparse.ArgumentParser (description='Ocf script anything.')
        parser.add_argument ('type', help='Option to launch the ocf script.', action='store', choices=s.choices)
        args = parser.parse_args()
        
        sys.exit(s.run(args.type))

################################################################################
if __name__ == '__main__':
    main()
    