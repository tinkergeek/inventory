#!/usr/bin/python

'''
The Postgres database should be running locally. Create a user called inventory and a database named inventory.

Then create a table called servers:
create table servers (hostname varchar(256), ipaddress inet, facts jsonb, checkin date, UNIQUE(hostname, ipaddress));

You need to install Python3 CherryPy SimpleJSON and psycopg2 modules.
'''

import cherrypy
import simplejson
import psycopg2
import html
import datetime

def connect(thread_index):
    cherrypy.thread_data.db = psycopg2.connect("host='localhost' dbname='inventory' user='inventory'")

cherrypy.engine.subscribe('start_thread', connect)

class Servers:
    pageheader = """
<p>
<a href="/">Home</a> <a href="/hosts">Host List</a> <a href="/inventory">Detailed Inventory</a> 
</p>
"""
    pagebegin = """
<html><body>
"""
    pageend = """
</html></body>
"""

# This function generates an HTML table from search results, automatically linking fqdn's
#gentable(cursor_result_dict, ['Header 1', 'Header 2'])
    def gentable(data, header):
        output = "<table style=\"width:50%\">"
        output = output + "<tr>"
        for label in header:
            output = output + "<th>" + str(label) + "</th>"
        output = output + "</tr>"
        for row in data:
            output = output + "<tr>"
            for item in row:
                output = output + "<td><a href=\"/host?host=" + str(item) + "\">" + str(item) + "</a></td>"
            output = output + "</tr>"
        output = output + "</table>"
        return output

# This function generates an HTML table from search results, automatically linking fqdn's and
# keys into the search page
# genkeyvaluetable(cursor_result_dict, ['Header 1', 'Header 2'], 'facter key')
# Values with spaces get the space replaced with %20
    def genkeyvaluetable(data, header, key):
        output = "<table style=\"width:50%\">"
        output = output + "<tr>"
        for label in header:
            output = output + "<th>" + str(label) + "</th>"
        output = output + "</tr>"
        for row in data:
            output = output + "<tr>"
            for item in row:
                output = output + "<td><a href=\"/host?host=" + str(item) + "\">" + str(item) + "</a></td>"
            output = output + "</tr>"
        output = output + "</table>"
        return output

    def index(self):
        c = cherrypy.thread_data.db.cursor()
        c.execute('SELECT COUNT(*) FROM servers')
        res = c.fetchone()
        c.close()
        output = Servers.pagebegin + Servers.pageheader
        output = output + "<p>There are %s servers registered.</p>" % res[0]
        output = output + Servers.pageend
        return output
    index.exposed = True

    def hosts(self):
        c = cherrypy.thread_data.db.cursor()
        c.execute("SELECT hostname FROM servers ORDER BY hostname")
        res = c.fetchall()
        c.close()
        output = Servers.pagebegin + Servers.pageheader
        output = output + Servers.gentable(res, ['Hostname'])
        output = output + Servers.pageend
        return output
    hosts.exposed = True

    def inventory(self):
        c = cherrypy.thread_data.db.cursor()
        c.execute("SELECT hostname, facts->'kernel'->'release', facts->'chassis'->'serialnumber' FROM servers ORDER BY hostname")
        res = c.fetchall()
        c.close()
        output = Servers.pagebegin + Servers.pageheader
        output = output + Servers.gentable(res, ['Hostname', 'Kernel', 'Serial Number'])
        output = output + Servers.pageend
        return output
    inventory.exposed = True

    def search(self,key="help",value="blah"):
        if key == "help":
            output = "<html><body>" + Servers.pageheader + "<br />"
            output = output + "<p>Please use search?key=\"insert the name of a facter fact here\"<br />"
            output = output + "or Please use search?key=\"fact name\"&value=\"thing\"</p>"
            output = output + "</body</html>"
            return output

        if value == "blah":
            c = cherrypy.thread_data.db.cursor()
            search = "SELECT hostname, facts->'" + key + "' FROM servers ORDER BY hostname"
            c.execute(search)
            res = c.fetchall()
            c.close()
            c = cherrypy.thread_data.db.cursor()
            search = "SELECT DISTINCT facts->'" + key + "' FROM servers ORDER BY facts->'" + key + "'"
            c.execute(search)
            res2 = c.fetchall()
            c.close()
            output = Servers.pagebegin + Servers.pageheader
            output = output + Servers.genkeyvaluetable(res2, ['Unique Values'], key)
            output = output + Servers.gentable(res, ['Hostname', 'Key Value'])
            output = output + Servers.pageend
            return output
        else:
            c = cherrypy.thread_data.db.cursor()
            search = "SELECT hostname FROM servers WHERE facts->'" + key + "' ? '" + value + "' ORDER BY hostname"
            c.execute(search)
            res = c.fetchall()
            c.close()
            output = Servers.pagebegin + Servers.pageheader
            output = output + key + " = " + value + ":<br /><br />"
            output = output + Servers.gentable(res, ['Hostname'])
            output = output + Servers.pageend
            return output
    search.exposed = True

    def host(self,host="help"):
        if host == "help":
            output = "<html><body>" + Servers.pageheader + "<br />"
            output = output + "<p>Please use host?host=\"hostname\"<br />"
            output = output + "</body</html>"
            return output

        c = cherrypy.thread_data.db.cursor()
        search = "SELECT facts FROM servers WHERE hostname = '" + host + "'"
        c.execute(search)
        res = c.fetchone()
        c.close()
        result = simplejson.loads(simplejson.dumps(res[0]))
        output = "<html><body>" + Servers.pageheader + "<br />"
        output = output + host + ":<br />"
        for key in result:
            value = result[key]
            output = output + "<b><a style=\"color:black\" href=/search?key=" + str(key) + ">" + str(key) + "</a> = </b>" + str(value) + "<br />"
        output = output + "</body></html>"
        return output
    host.exposed = True

    @cherrypy.tools.accept(media='application/json')
    def update(self, hostname):
        now = datetime.datetime.now()
        cl = cherrypy.request.headers['Content-Length']
        rawbody = cherrypy.request.body.read(int(cl))
        facts = simplejson.loads(rawbody)
        c = cherrypy.thread_data.db.cursor()
        c.execute("INSERT INTO servers (hostname, ipaddress, facts, checkin) VALUES (%s, %s, %s, %s) ON CONFLICT (hostname, ipaddress) DO UPDATE SET (facts, checkin) = (excluded.facts, excluded.checkin)", (hostname, cherrypy.request.remote.ip, simplejson.dumps(facts), now.isoformat()))
        cherrypy.thread_data.db.commit()
        c.close()
    update.exposed = True

cherrypy.config.update({'server.socket_host': '0.0.0.0',
                        'server.socket_port': 8080,
                        'server.thread_pool': 50})
cherrypy.quickstart(Servers())


