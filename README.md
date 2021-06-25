baikal-birthday-calendar
========================

Python script to automatically create birthday calendar entries for a baikal server (http://baikal-server.com).
Tested with baikal 0.2.7 and python 2.7.5 on CentOS 7. Works only with MySQL backend.

Installation
========================
- Copy script to /opt/birthdayCron
- Modify the script and change the following parameters: sql user (sqluser), password (sqlpwd), database name (sqldb), file path to store a datafile (datafile), name of the birthday calendar (calendaruri) and displayed name of the birthday calendar (calendarname).
- Add the script as cron (e.g. 00 * * * * mcwolle /opt/birthdayCron/birthdayCron.py)

Credits
========================
funkfux : https://github.com/fruux/Baikal/issues/38
