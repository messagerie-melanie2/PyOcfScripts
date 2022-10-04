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
                kill9_all_fork_is_ra_opt=True, \
                ocf_write_pidfile_is_ra_opt=True, \
                user_cmd_is_ra_opt=True, \
                change_workdir_is_ra_opt=True, \
                status_check_ppid_is_ra_opt=True, \
                status_check_pidfile_is_ra_opt=True, \
                status_socket_is_ra_opt=True, \
                default_status_socket_return_is_ra_opt=True, \
                status_socket_timeout_is_ra_opt=True, \
                status_socket_obsolete_data_is_ra_opt=True, \
                status_socket_need_all_on_error_is_ra_opt=True)
        except:
            raise


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
    
