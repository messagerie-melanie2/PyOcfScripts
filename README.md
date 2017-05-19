# PyOcfScripts
Ocf scripts for pacemaker

This scripts are made to be used with corosync/pacemaker.

To install them:
- create a directory on your file system (for example "/ opt / PyOcfScript")
- create a symbolic link from the ocf scripts directory (for example, under debian /usr/lib/ocf/resource.d/) to the directory of your ocf scripts

These scripts are written in python 2.7 and require the following python modules:
Psutil, ldap and pyroute2
