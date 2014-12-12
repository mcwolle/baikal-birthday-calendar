#!/usr/bin/env python
import MySQLdb
import MySQLdb.cursors
import vobject
from datetime import datetime, timedelta
import hashlib
import calendar
import os.path
import pickle

sqlhost = 'localhost'
sqluser = 'baikal'
sqlpwd  = 'MySQL Password'
sqldb   = 'baikal'

calendaruri  = 'birthdays'
calendarname = 'Geburtstage'

now = datetime.utcnow()
nowts = calendar.timegm(now.timetuple())

# Load stored pickle file if existing
datafile = '/opt/birthdayCron/birthdayCron.p'
if os.path.isfile(datafile):
    stored_addressbook_ctags = pickle.load(open(datafile, "rb"))
else:
    stored_addressbook_ctags = {}

db = MySQLdb.connect(host=sqlhost, user=sqluser, passwd=sqlpwd, db=sqldb)
read_cur  = db.cursor()
write_cur = db.cursor()

# Load ctags of addressbooks and consolidate into one entry per principal
current_addressbook_ctags = {}
read_cur.execute('SELECT principaluri, ctag FROM addressbooks ORDER BY id ASC')
for addressbook in read_cur.fetchall():
    if addressbook[0] not in current_addressbook_ctags:
        current_addressbook_ctags[addressbook[0]] = str(addressbook[1])
    else:
        current_addressbook_ctags[addressbook[0]] = current_addressbook_ctags[addressbook[0]]+str(addressbook[1])

# Get principals from DB
read_cur.execute('SELECT uri FROM principals')
for principal in read_cur.fetchall():
    # Set uri of principal
    uri = principal[0]

    if uri not in stored_addressbook_ctags or (uri in stored_addressbook_ctags and stored_addressbook_ctags[uri] != current_addressbook_ctags[uri]):
        # Get birthdays calendar from principal
        read_cur.execute('SELECT id FROM calendars WHERE principaluri = %s and uri = %s', [uri, calendaruri])
        row = read_cur.fetchone()
    
        if row == None:
            # Create birthdays calendar if not existing
            var = [uri, calendarname, calendaruri, 1, calendarname, 0, "", "", "VEVENT"]
            write_cur.execute('INSERT INTO calendars (principaluri, displayname, uri, ctag, description, calendarorder, calendarcolor, timezone, components) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)', var)
            calendarid = write_cur.lastrowid
        else:
            calendarid = row[0]

        # Clear calendar first
        write_cur.execute('DELETE FROM calendarobjects WHERE calendarid = %s', [calendarid])
            
        read_cur.execute('SELECT c.carddata, c.uri FROM cards as c JOIN addressbooks as a ON c.addressbookid = a.id WHERE a.principaluri = %s', [uri])
        for row in read_cur.fetchall():
            card = vobject.readOne(row[0])
            carduri = row[1]

            if hasattr(card, 'bday'):
                bday = datetime.strptime(card.bday.value, '%Y-%m-%d').date()
                ca = vobject.newFromBehavior('vcalendar')

                # Create event
                ev = ca.add('vevent')
                ev.add('summary').value = card.fn.value
                ev.add('dtstart').value = bday
                ev.add('dtend').value = bday+timedelta(days=1)
                ev.add('class').value = "public"
                ev.add('created').value = now
                ev.add('dtstamp').value = now
                ev.add('last-modified').value = now 
                ev.add('rrule').value = "FREQ=YEARLY;BYMONTHDAY="+str(bday.day)+";BYMONTH="+str(bday.month);
                ev.add('transp').value = "TRANSPARENT"
                ev.add('categories').value = ["Birthday"]
                ev.add('x-microsoft-cdo-alldayevent').value = "TRUE"

                # Create alarm
                al = ev.add('valarm')
                al.add('action').value = "Display"
                al.add('trigger;related=end').value = "-PT16H"

                data = ca.serialize();
                etag = hashlib.md5(data).hexdigest()
                size = len(data)
                newuri = str(carduri[:-4])+'.ics'

                # Insert data into DB
                var = [data, newuri, calendarid, nowts, etag, size, 'VEVENT', nowts, nowts+300000000]
                write_cur.execute('INSERT INTO calendarobjects (calendardata, uri,  calendarid, lastmodified, etag, size, componenttype, firstoccurence,lastoccurence) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)', var)

                # Debug Output
                # print "Inserted new entry with title "+card.fn.value+"."

        # Update ctag in birthday calendar (to indicate changes)
        write_cur.execute('UPDATE calendars SET ctag = ctag + 1 WHERE id = %s', [calendarid])

        # Store current ctags of addressbooks to disk
        pickle.dump(current_addressbook_ctags, open(datafile, "wb"))

db.commit()
read_cur.close()
write_cur.close()
db.close()
