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

''' This the python version of the file script ocf-returncodes '''

################################################################################
class ocfReturnCodes(object):
    ########################################
    def __init__(self):
        # Non-standard values.
        #
        # OCF does not include the concept of master/slave resources so we
        #   need to extend it so we can discover a resource's complete state.
        #
        # self.ocfretcodes['OCF_RUNNING_MASTER']:
        #    The resource is in "master" mode and fully operational
        # self.ocfretcodes['OCF_FAILED_MASTER']:
        #    The resource is in "master" mode but in a failed state
        #
        # The extra two values should only be used during a probe.
        #
        # Probes are used to discover resources that were started outside of
        #    the CRM and/or left behind if the LRM fails.
        #
        # They can be identified in RA scripts by checking for:
        #   [ "${__OCF_ACTION}" = "monitor" -a "${OCF_RESKEY_CRM_meta_interval}" = "0" ]
        #
        # Failed "slaves" should continue to use: self.ocfretcodes['OCF_ERR_GENERIC']
        # Fully operational "slaves" should continue to use: self.ocfretcodes['OCF_SUCCESS']
        self.ocfretcodes = { \
            'OCF_SUCCESS':0, \
            'OCF_ERR_GENERIC':1, \
            'OCF_ERR_ARGS':2, \
            'OCF_ERR_UNIMPLEMENTED':3, \
            'OCF_ERR_PERM':4, \
            'OCF_ERR_INSTALLED':5, \
            'OCF_ERR_CONFIGURED':6, \
            'OCF_NOT_RUNNING':7, \
            'OCF_RUNNING_MASTER':8,\
            'OCF_FAILED_MASTER':9 }
        
    ########################################
    def __getitem__(self, code):
        return self.ocfretcodes[code]
    
