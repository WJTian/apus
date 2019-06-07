#!/usr/bin/env python

import threading
import ConfigParser
import re
import argparse
import sys
import logging
import os
import subprocess
from signal import signal
# tom add 2014-12-23
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
# end tom add 2014-12-23

def getMsmrDefaultOptions():
	default = {}
	return default

def getConfigFullPath(config_file):
	try:
		with open(config_file) as f: pass
	except IOError as e:
		logging.warning("'%s' does not exist" % config_file)
		return None
	return os.path.abspath(config_file)

def readConfigFile(config_file):
	try:
		newConfig = ConfigParser.ConfigParser({"REPEATS":"1",
						       "TEST_ID":"1",
						       "EXPORT":"",
						       "TEST_NAME":"",
						       "TEST_FILE":"",
						       "NO":"",
						       "PROXY_MODE":"WITH_PROXY",
						       "DEBUG_MODE":"WITHOUT_DEBUG",
						       "PLOT_MODE":"WITHOUT_PLOT",
						       "LOG_SUFFIX":".log",
						       "SLEEP_TIME":"5",
						       "SECONDARIES_SIZE":"0",
						       "SERVER_COUNT":"1",
						       "SERVER_START_PORT":"7000",
						       "SERVER_INPUT":"",
						       "SERVER_KILL":"",
						       "SYSTEM_CONFIG":"$MSMR_ROOT/libevent_paxos/target/nodes.cfg",
						       "CLIENT_COUNT":"1",
						       "CLIENT_PROGRAM":"",
						       "CLIENT_INPUT":"",
						       "CLIENT_SLEEP_TIME":"1",
						       "CLIENT_IP":"127.0.0.1",
						       "CLIENT_PORT":"9000",
						       "CLIENT_REPEAT":"1",
						       "EVALUATION":""})
		ret = newConfig.read(config_file)
	except ConfigParser.MissingSectionHeaderError as e:
		logging.error(str(e))
	except ConfigParser.ParsingError as e:
		logging.error(str(e))
	except ConfigParser.Error as e:
		logging.critical("strange error? " + str(e))
	else:
		if ret:	
			return newConfig

def getGitInfo():
    import commands
    git_show = 'cd '+MSMR_ROOT+' && git show '
    githash = commands.getoutput(git_show+'| head -1 | sed -e "s/commit //"')
    git_diff = 'cd '+MSMR_ROOT+' && git diff --quiet'
    diff = commands.getoutput('cd ' +MSMR_ROOT+ ' && git diff')
    if diff:
        gitstatus = '_dirty'
    else:
        gitstatus = ''
    commit_date = commands.getoutput( git_show+
            '| head -4 | grep "Date:" | sed -e "s/Date:[ \t]*//"' )
    date_tz  = re.compile(r'^.* ([+-]\d\d\d\d)$').match(commit_date).group(1)
    date_fmt = ('%%a %%b %%d %%H:%%M:%%S %%Y %s') % date_tz
    import datetime
    gitcommitdate = str(datetime.datetime.strptime(commit_date, date_fmt))
    logging.debug( "git 6 digits hash code: " + githash[0:6] )
    logging.debug( "git reposotory status: " + gitstatus)
    logging.debug( "git commit date: " + gitcommitdate)
    return [githash[0:6], gitstatus, gitcommitdate, diff]

#make directory
def mkdir_p(path):
	try:
		os.makedirs(path)
	except OSError as exc: 
		if exc.errno == errno.EEXIST and os.path.isdir(path):
			logging.warning("%s already exists" % path)
			pass
		else: raise

def genRunDir(config_file, git_info):
	dir_name = ""
	from os.path import basename
	config_name = os.path.splitext(basename(config_file))[0]
	from time import strftime
	dir_name += config_name + strftime("%Y%b%d_%H%M%S") + '_' + git_info[0] +git_info[1]
	mkdir_p(dir_name)
	logging.debug("creating %s" % dir_name)
	return os.path.abspath(dir_name)

def extract_apps_exec(config, bench, apps_dir=""):
	bench = bench.partition('"')[0].partition("'")[0]
	apps = bench.split()
	if apps.__len__() < 1:
		raise Exception("cannot parse executible file name")
	elif apps.__len__() == 1:
		return apps[0], os.path.abspath(apps_dir + '/eval/current/' +apps[0])
	else:
		return apps[0], os.path.abspath(apps_dir + '/eval/current/' +apps[0]+'_'+apps[1].replace('/','')+'/'+bench.replace(' ','').replace('/','').replace('<port>',''))

def generate_local_options(config, bench):
	config_options = config.options(bench)
	output = ""
	for option in default_options:
		if option in config_options:
			entry = option + '=' + config.get(bench, option)
		else:
			entry = option + '=' + default_options[option]
		output += '%s\n' % entry
	with open("local.options", "w") as option_file:
		option_file.write(output)

def checkExist(file, flags=os.X_OK):
	if not os.path.exists(file) or not os.path.isfile(file) or not os.access(file, flags):
		return False
	return True

def copy_file(src, dst):
	import shutil
	shutil.copy(src, dst)

def which(name, flags=os.X_OK):
	result = []
	path = os.environ.get('PATH', None)
	if path is None:
		return []
	for p in os.environ.get('PATH', '').split(os.pathsep):
		p = os.path.join(p, name)
		if os.access(p, flags):
			result.append(p)
	return result

#def write_stats(time1, time2, repeats, first, last, lengths, origin_time1, origin_time2, origin_time3, isPlot, concensusmap, responsemap):
#tom add 2015-01-23
def write_stats(time1, time2, repeats, first, last, lengths, origin_time1, origin_time2, origin_time3, isPlot, concensusmap, responsemap, bench, config):
#end tom add 2015-01-23
	try:
		import numpy
	except ImportError:
		logging.error("please install 'numpy' module")
	try: 
		import matplotlib.pyplot as plt
	except ImportError:
		logging.error("Cannot draw plot! Please install 'matplotlib' module")
	if isPlot:
		x = range(len(origin_time1))
		plt.scatter(x, origin_time1)
		
		x = range(len(origin_time2))
		plt.scatter(x, origin_time2)

		x = range(len(origin_time3))
		plt.scatter(x, origin_time3)
		plt.savefig('origintime3.png')
		plt.clf()
		
		x = range(len(time1))
		plt.scatter(x, time1)

		x = range(len(time2))
		plt.scatter(x, time2)
		plt.savefig('time2.png')
		plt.clf()

	time1_avg = numpy.average(time1)
	time1_std = numpy.std(time1)
	time2_avg = numpy.average(time2)
	time2_std = numpy.std(time2)
	if len(lengths) > 0:
		length_avg = numpy.average(lengths)
		length_std = numpy.std(lengths)
	import math
	with open("stats.txt", "w") as stats:
		# tom add 20150126
		if Perf_Test_Flag == 1:
			stats.write('Concensus Time('+str(len(time1))+'):\n')
			stats.write('\tmean:{0} us\n'.format(time1_avg))
			stats.write('\tstd:{0}\n'.format(time1_std))
			for t in concensusmap:
				stats.write('\t{0}({1}):\n'.format(t, len(concensusmap[t])))
				stats.write('\t\tmean:{0} us\n'.format(numpy.average(concensusmap[t])))
				stats.write('\t\tstd:{0}\n'.format(numpy.std(concensusmap[t])))
			stats.write('Response Time('+str(len(time2))+'):\n')
			stats.write('\tmean:{0} us\n'.format(time2_avg))
			stats.write('\tstd:{0}\n'.format(time2_std))
			for t in responsemap:
				stats.write('\t{0}({1}):\n'.format(t, len(responsemap[t])))
				stats.write('\t\tmean:{0} us\n'.format(numpy.average(responsemap[t])))
				stats.write('\t\tstd:{0}\n'.format(numpy.std(responsemap[t])))
			# tom add 20150126
			stats.write('Throughput (from timestamps in libevent_paxos):\n')
			stats.write('\t{0} operations/s\n'.format(len(time1)/(last-first)))
			# end tom add 20150126
			if len(lengths) > 0:
				stats.write('Queue Length:\n')
				stats.write('\tmean:{0}\n'.format(length_avg))
				stats.write('\tstd:{0}'.format(length_std))
		# end tom add 20150126
		# tom add 2015-01-23
		#if bench.split(" ")[0]=="apache":
		stats.write('==============================\n')
		stats.write('Throughput (from ab log):\n')
		TP = []
		for i in range(int(config.get(bench,'CLIENT_COUNT'))):
			client_dir_name = 'client'+str(i+1)
			client_output_log_file_name = MSMR_ROOT+'/eval/current/'+client_dir_name+'/client'+str(i+1)+'output.log'
			if not os.path.isfile(client_output_log_file_name):
				break
			lines = (open(client_output_log_file_name, 'r').readlines())
			for line in lines:
				if line.startswith('Requests per second'):
					TP += [float(line.split(':')[1].translate(None, ' [#/sec] (mean)\n'))]
					#stats.write(line.split(':')[1].translate(None, ' [#/sec] (mean)\n'))
		stats.write('\t{0} req/s\n'.format(numpy.average(TP)))
		stats.write('==============================\n')
		# end tom add 2015-01-23
	os.system('cat stats.txt')

def preSetting(config, bench, apps_name):
	os.system("sed -e 's/group_size = [0-9]\+/group_size = "+config.get(bench, 'SERVER_COUNT')+"/g' $MSMR_ROOT/libevent_paxos/target/nodes.cfg > nodes.cfg")
	for i in range(int(config.get(bench,'SERVER_COUNT'))):
		mkdir_p('../server'+str(7000+i))
	for i in range(int(config.get(bench,'CLIENT_COUNT'))):
		mkdir_p('../client'+str(int(i)+1))

	#if(config.get(bench, 'DEBUG_MODE')=='WITH_DEBUG'):

	#handle the config and mk stuff
	if bench.split(" ")[0]=="apache":
		for i in range(7000, 7000+int(config.get(bench,'SERVER_COUNT'))):
			os.system("cp $MSMR_ROOT/apps/apache/install/conf/httpd.conf ../server"+str(i)+"/httpd.conf")
			os.system("sed -e \"s/Listen [0-9]\+/Listen "+str(i)+"/g\" ../server"+str(i)+"/httpd.conf > ../server"+str(i)+"/httpd"+str(i)+".conf")
	elif bench.split(" ")[0]=="lighttpd":
		for i in range(7000, 7000+int(config.get(bench,'SERVER_COUNT'))):
			os.system("cp $MSMR_ROOT/apps/lighttpd/install/lighttpd.conf ../server"+str(i)+"/lighttpd.conf")
			os.system("sed -e 's/server.port = [0-9]\+/server.port = "+str(i)+"/g' ../server"+str(i)+"/lighttpd.conf > ../server"+str(i)+"/lighttpd"+str(i)+".conf")
	elif bench.split(' ')[0]=="ssdb":
		for i in range(7000, 7000+int(config.get(bench,'SERVER_COUNT'))):
			os.system("cp $MSMR_ROOT/apps/ssdb/ssdb-master/ssdb.conf ../server"+str(i)+"/")
			os.system("sed -e 's/port: [0-9]\+/port: "+str(i)+"/g' ../server"+str(i)+"/ssdb.conf > ../server"+str(i)+"/ssdb1.conf")
			os.system("sed -e 's/dir = \.\/var/dir = "+os.environ["MSMR_ROOT"].replace('/','\/')+"\/apps\/ssdb\/ssdb-master\/var"+str(i)+"/g' ../server"+str(i)+"/ssdb1.conf > ../server"+str(i)+"/ssdb2.conf")
			os.system("sed -e 's/pidfile = \.\/var\/ssdb/pidfile = "+os.environ["MSMR_ROOT"].replace('/','\/')+"\/apps\/ssdb\/ssdb-master\/var\/ssdb"+str(i)+"/g' ../server"+str(i)+"/ssdb2.conf > ../server"+str(i)+"/ssdb"+str(i)+".conf")
			os.system("rm $MSMR_ROOT/apps/ssdb/ssdb-master/var/ssdb"+str(i)+".pid")
			os.system("mkdir $MSMR_ROOT/apps/ssdb/ssdb-master/var"+str(i))
	elif bench.split(' ')[0]=='mongodb':
		for i in range(7000, 7000+int(config.get(bench, "SERVER_COUNT"))):
			os.system("mkdir $MSMR_ROOT/apps/mongodb/install/data"+str(i))
		os.system("cp $MSMR_ROOT/apps/mongodb/ycsb-0.1.4/mongodb-binding -r ../")
		os.system("cp $MSMR_ROOT/apps/mongodb/ycsb-0.1.4/core -r ../")
		os.system("cp $MSMR_ROOT/apps/mongodb/ycsb-0.1.4/CHANGELOG ../")
	elif bench.split(' ')[0]=='pgsql':
		for i in range(7000, 7000+int(config.get(bench,'SERVER_COUNT'))):
			if(not(os.path.isfile(os.environ['MSMR_ROOT']+'/apps/pgsql/'+str(i)+'/install/bin/pg_ctl'))):
				print 'Please cd to $MSMR_ROOT/apps/pgsql and \"./mk_single '+str(i)+'\" first.'
				exit(1)
	elif bench.split(' ')[0]=='proftpd':
		for i in range(7000, 7000+int(config.get(bench,'SERVER_COUNT'))):
			os.system("cp $MSMR_ROOT/apps/proftpd/install/etc/proftpd.conf ../server"+str(i)+"/")
			os.system("sed -e 's/Port [0-9]\+/Port "+str(i)+"/g' ../server"+str(i)+"/proftpd.conf > ../server"+str(i)+"/proftpd2.conf")
			os.system("sed -e 's/\.pid/"+str(i)+"\.pid/g' ../server"+str(i)+"/proftpd2.conf > ../server"+str(i)+"/proftpd3.conf")
			os.system("sed -e 's/data/data"+str(i)+"/g' ../server"+str(i)+"/proftpd3.conf > ../server"+str(i)+"/proftpd"+str(i)+".conf")
			os.system("mkdir $MSMR_ROOT/apps/proftpd/install/data"+str(i))
			os.system("cp $MSMR_ROOT/apps/proftpd/install/data/* $MSMR_ROOT/apps/proftpd/install/data"+str(i)+"/")
	#handle test file
	if config.get(bench, 'TEST_FILE') != "":
		if bench.split(" ")[0]=="apache":
			os.system("cp "+config.get(bench, 'TEST_FILE')+" $MSMR_ROOT/apps/apache/install/htdocs/")
		else: 
			for i in range(7000, 7000+int(config.get(bench,'SERVER_COUNT'))):
				os.system("cp "+config.get(bench, 'TEST_FILE')+" ../server"+str(i)+"/")
	if config.get(bench, 'CLIENT_PROGRAM') != "":
		for i in range(int(config.get(bench,'CLIENT_COUNT'))):
			os.system("cp "+config.get(bench,'CLIENT_PROGRAM')+' ../client'+str(int(i)+1)+'/client')
	testname = bench.replace(' ','').replace('<port>','').replace('/','')

	with open(testname, "w") as testscript:
		testscript.write('#! /bin/bash\n'+
	'TEST_NAME='+testname+'\n'+
	config.get(bench, 'SERVER_KILL')+'\n'+
	'killall -9 client\n'+
	'killall -15 server.out\n'+
	'NO=${1}\n'+
	'LOG_SUFFIX='+config.get(bench,'LOG_SUFFIX')+'\n'+
	'SLEEP_TIME='+config.get(bench,'SLEEP_TIME')+'\n'+
	'SECONDARIES_SIZE='+str(int(config.get(bench,'SERVER_COUNT'))-1)+'\n'+
	'if [ ! -d ./log ];then\n'+
	'\tmkdir ./log\n'+
	'fi\n'+
	'exec 2>./log/${TEST_NAME}_err_${NO}\n'+
	'export LD_LIBRARY_PATH=$MSMR_ROOT/libevent_paxos/.local/lib\n'+
	'SERVER_PROGRAM=$MSMR_ROOT/libevent_paxos/target/server.out\n')
		testscript.write('CONFIG_FILE=nodes.cfg\n')
		testscript.write('rm -rf $MSMR_ROOT/libevent_paxos/.db\n')
		testscript.write('rm -rf .db\n')
		for i in range(int(config.get(bench,'SERVER_COUNT'))):
			port = str(int(config.get(bench,'SERVER_START_PORT'))+i)
			testscript.write('\n# Start the application server\n')
			testscript.write('if [ $MY_XTERN"X" = "1X" ]; then\n')
			testscript.write('LD_PRELOAD=$XTERN_ROOT/dync_hook/interpose.so \\\n')

			testscript.write('$MSMR_ROOT/apps/'+bench.split(' ')[0]+bench.split(' ')[1].replace('<port>',port)+' '+config.get(bench, 'SERVER_INPUT').replace('<port>', port)+' &> ../server'+port+'/${TEST_NAME}_0_${NO}_s${LOG_SUFFIX} &\nREAL_SERVER_PID_'+str(i)+'=$!\n')
			testscript.write('else\n')
			testscript.write('$MSMR_ROOT/apps/'+bench.split(' ')[0]+bench.split(' ')[1].replace('<port>',port)+' '+config.get(bench, 'SERVER_INPUT').replace('<port>', port)+' &> ../server'+port+'/${TEST_NAME}_0_${NO}_s${LOG_SUFFIX} &\nREAL_SERVER_PID_'+str(i)+'=$!\n')
			testscript.write('fi\n\n')
			testscript.write('echo "sleep some time"\n'+'sleep ${SLEEP_TIME}\n')
		if config.get(bench,'PROXY_MODE').startswith('WITH_PROXY'):
			testscript.write('\n# Start our proxy\n')
			testscript.write('if [ $MY_PROXY"X" = "1X" ]; then\n')
			testscript.write('${SERVER_PROGRAM} -n 0 -r -m s -c ${CONFIG_FILE} -l ./log 1>./log/node_0_${NO}_stdout 2>./log/node_0_${NO}_stderr &\n')
			testscript.write('fi\n\n'+
	'PRIMARY_PID=$!\n'+
	'for i in $(seq ${SECONDARIES_SIZE});do\n'+
	'\t${SERVER_PROGRAM} -n ${i} -r -m r -c ${CONFIG_FILE} -l ./log 1>./log/node_${i}_${NO}_stdout 2>./log/node_${i}_${NO}_stderr &\n'+
	'declare NODE_${i}=$!\n'+
	'done\n')
		testscript.write('echo "sleep some time"\n'+
	'sleep ${SLEEP_TIME}\n')
		
		#preparation for client
		if(bench.split(' ')[0] == 'pgsql'):
			testscript.write('LD_PRELOAD=$MSMR_ROOT/libevent_paxos/client-ld-preload/libclilib.so '+'../client'+str(int(i)+1)+'/client -i '+config.get(bench, 'CLIENT_INPUT')+' &')
		for i in range(int(config.get(bench,'CLIENT_COUNT'))):
			if config.get(bench,'PROXY_MODE').startswith('WITH_PROXY'):
				testscript.write('if [ $MY_PROXY"X" = "1X" ]; then\n')
				testscript.write('LD_PRELOAD=$MSMR_ROOT/libevent_paxos/client-ld-preload/libclilib.so '+'../client'+str(int(i)+1)+'/client '+config.get(bench,'CLIENT_INPUT')+' &')
				testscript.write('> ../client'+str(i+1)+'/client'+str(i+1)+'output${LOG_SUFFIX}')
				testscript.write('\nelse\n')
				testscript.write('../client'+str(int(i)+1)+'/client '+config.get(bench,'CLIENT_INPUT').replace('9000','7000')+' &')
				testscript.write('> ../client'+str(i+1)+'/client'+str(i+1)+'output${LOG_SUFFIX}')
				testscript.write('\nfi\n')
			else:
				testscript.write('../client'+str(int(i)+1)+'/client '+config.get(bench,'CLIENT_INPUT').replace('9000','7000')+' &')
				testscript.write('> ../client'+str(i+1)+'/client'+str(i+1)+'output${LOG_SUFFIX}')
			testscript.write('\n')
		testscript.write('echo "sleep another time"\nsleep ${SLEEP_TIME}\n'+
	'kill -15 ${PRIMARY_PID} &>/dev/null\n'+
	'for i in $(echo ${!NODE*});do\n'+
	'\tkill -15 ${!i} &>/dev/null\n'+
	'done\n'+
	'for i in $(echo ${!SERVER*});do\n'+
	'\tkill -9 ${!i} &>/dev/null\n'+
	'killall -15 server.out\n'+
	'killall -9 client\n'+
	'done\n')
		for i in range(1,int(config.get(bench,'SERVER_COUNT'))+1):
			testscript.write('kill -9 ${REAL_SERVER_PID_'+str(i)+'} &>/dev/null\n')
			if config.get(bench, 'SERVER_KILL') != "":
				testscript.write(config.get(bench,'SERVER_KILL').replace('<port>',str(i+int(config.get(bench,'SERVER_START_PORT'))))+'\n')
	os.system('chmod +x '+testname)
	return

def execBench(cmd, repeats, out_dir,
	      client_cmd="", client_terminate_server=False,
	      init_env_cmd=""):
	mkdir_p(out_dir.replace('<port>',''))
	for i in range(int(repeats)):
		print cmd
		sys.stderr.write("        PROGRESS: %5d/%d\r" % (i+1, int(repeats)))
		with open('%s/output.%d' % (out_dir, i), 'w', 102400) as log_file:
			if init_env_cmd:
				os.system(init_env_cmd)
			proc = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT, shell=True, executable=bash_path, bufsize=102400)
			if client_cmd:
				time.sleep(1)
				with open('%s/client.%d' % (out_dir, i), 'w', 102400) as client_log_file:
					client_proc = subprocess.Popen(client_cmd, stdout=client_log_file, stderr=subprocess.STDOUT, shell=True, executable=bash_path, bufsize=102400)
					client_proc.wait()
				if client_terminate_server:
					os.killpg(proc.pid, signal.SIGTERM)
				proc.wait()
				time.sleep(2)
			else:
				try:
					proc.wait()
				except KeyboardInterrupt as k:
					try:
						os.killpg(proc.pid, signal.SIGTERM)
					except:
						pass
					raise k
		try:
			os.renames('out', '%s/out.%d' % (out_dir, i))
		except OSError:
			pass

def processBench(config, bench):
		
	logging.debug("processing: " + bench)
	specified_evaluation = config.get(bench, 'EVALUATION')
	apps_name, exec_file = extract_apps_exec(config, bench, APPS)
	logging.debug("app = %s" % apps_name)
	logging.debug("executible file = %s" % exec_file)
	
	segs = re.sub(r'(\")|(\.)|/|\'', '', bench).split()
	dir_name = ""
	dir_name += '_'.join(segs)
	dir_name = dir_name.replace('<port>','')
	mkdir_p(dir_name)
	os.chdir(dir_name)
	
	generate_local_options(config, bench)
	inputs = config.get(bench, 'TEST_ID')
	repeats = config.get(bench, 'repeats')
	
	if specified_evaluation:
		specified = __import__(specified_evaluation, globals(), locals(), [], -1)
		specified.evaluation(int(repeats))
		return
	
	preSetting(config, bench, apps_name)
	
	export = config.get(bench, 'EXPORT')
	if export:
		logging.debug("export %s", export)

	# generate command for MSMR [time LD_PRELOAD=... exec args...]
	msmr_command = ' '.join([export, exec_file] + inputs.split())
	logging.info("executing '%s'" % msmr_command)
	execBench(msmr_command.replace('<port>',''), repeats, 'msmr')
		
	# get stats
	origin_time1 = []
	origin_time2 = []
	origin_time3 = []
	time1 = []
	time2 = []
	lengths = []
	types = []
	concensusmap = {}
	responsemap = {}
	# tom add 20150126
	op_index = []
	# end tom add 20150126
	for i in range(int(repeats)):
		log_file_name = MSMR_ROOT+'/eval/current/'+dir_name+'/log/node-0-proxy-req.log'
		print log_file_name
		if not os.path.isfile(log_file_name):
			break
		lines = (open(log_file_name, 'r').readlines())
		first = 0
		for line in lines:
			match = re.search(r"([0-9]+\.[0-9]+),([0-9]+\.[0-9]+),([0-9]+\.[0-9]+),([0-9]+\.[0-9]+)",line)
			if match:
				if first == 0:
					first = float(match.group(1)) # used for calculating tp, the first operation's received time
				time2 += [(-float(match.group(1))+float(match.group(4)))*1000000]
				last = float(match.group(4)) # used for tp, the last operation's end time
				origin_time1 += [float(match.group(1))]
				origin_time3 += [float(match.group(3))]
			# tom add 20150126
			# used for grabbing the operation which costs too much time, so we need to locate it by its index
			if line.startswith('Request'):
				op_index += [line.split(':')[1]]		
			# end tom add 20150126
			if line.startswith('Operation'):
				types += [line.split(' ')[1].translate(None, '.\n')]
		log_file_name = MSMR_ROOT+'/eval/current/'+dir_name+'/log/node-0-consensus-sys.log'
		print log_file_name
		lines = (open(log_file_name, 'r').readlines())
		for line in lines:
			origin_time2 += [float(line.split(':')[0])]
		# tom add 2014-12-23
		if Perf_Test_Flag == 1:
			per_Xoperation_response_time = [] # to store each X operation's response time which comes from proxy-req.log
			Xoperation = 'Sends' # 1)Sends 2)Connects 3)Closes
			with open("Performance.txt", "w") as perfo:
			# end tom add 2014-12-23
				for i in range(len(origin_time1)):
					tmpTime = [(origin_time2[i]-origin_time1[i])*1000000]
					time1 += tmpTime
					if types[i] not in concensusmap:
						concensusmap[types[i]] = tmpTime
						# tom add 2015-01-22
						if cmp(types[i], Xoperation) == 0:
							per_Xoperation_response_time +=  [time2[i]]
						# end tom add 2015-01-22
						responsemap[types[i]] = [time2[i]]
					else:
						concensusmap[types[i]] += tmpTime
						# tom add 2014-12-21-20:50
						if cmp(types[i], Xoperation) == 0:
							per_Xoperation_response_time +=  [time2[i]]
							# the following codes are used for grabbing the operation which costs too much time
							if time2[i] > 10000:  # 10000us is just an abnormally high value, and you can set a value higher than it
								#print("Abnormal OP: %s, response time: %f, index: %s" % (types[i], time2[i], op_index[i]))
	                						perfo.write("Abnormal OP: %s, response time: %f, index: %s\n" % (types[i], time2[i], op_index[i]))
						# end tom add 2014-12-21-20:50
						responsemap[types[i]] += [time2[i]]
			# tom add 2014-12-23
			plt.plot(per_Xoperation_response_time)
			plt.title('each X operation response time')
			plt.show()
			plt.savefig('matplot_performance_test.png')
			# end tom add 2014-12-23
		else:
			for i in range(len(origin_time1)):
				tmpTime = [(origin_time2[i]-origin_time1[i])*1000000]
				time1 += tmpTime
				if types[i] not in concensusmap:
					concensusmap[types[i]] = tmpTime
					responsemap[types[i]] = [time2[i]]
				else:
					concensusmap[types[i]] += tmpTime
					responsemap[types[i]] += [time2[i]]
	#print types
	#print lengths
	isPlot = False
	if(config.get(bench, "PLOT_MODE")=="WITH_PLOT"):
		isPlot = True
	if len(time1) > 0:
		#write_stats(time1, time2, int(repeats), first, last, lengths, origin_time1, origin_time2, origin_time3, isPlot, concensusmap, responsemap)
		#tom add 2015-01-23
		write_stats(time1, time2, int(repeats), first, last, lengths, origin_time1, origin_time2, origin_time3, isPlot, concensusmap, responsemap, bench, config)
		#end tom add 2015-01-23
	# copy exec file
	#copy_file(os.path.realpath(exec_file), os.path.basename(exec_file))
	
# def workers(semaphore, lock, configs, bench):
# 	from multiprocessing import Process
# 	with semaphore:
# 		p = Process(target=processBench, args=(configs, bench))
# 		with lock:
# 			logging.debug("STARTING %s" % bench)
# 			p.start()
# 		p.join()
# 		with lock:
# 			logging.debug("FINISH %s" % bench)

def workers(args):
    cmd = ''
    rcmd = 'parallel-ssh -v -p 3 -i -t 15 -h hostfile {command}'.format(command=cmd)

    # cmd = ""
    # rcmd = "parallel-ssh -v -p 1 -i -t 15 -h hostfile \"%s\"" % (cmd)

    p = subprocess.Popen(rcmd, shell=True, stdout=subprocess.PIPE)
    output, err = p.communicate()
    print output

if __name__ == "__main__":
	# tom add 20150126
	# add -v(verbose) to generate performance data: Performance.txt, matplot_performance_test.png
	Perf_Test_Flag = 0		
	# end tom add 20150126

	logger = logging.getLogger()
	formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s","%Y%b%d-%H:%M:%S")
	ch = logging.StreamHandler()
	ch.setFormatter(formatter)
	ch.setLevel(logging.DEBUG)
	logger.addHandler(ch)
	logger.setLevel(logging.DEBUG)

	try:
		MSMR_ROOT = os.environ["MSMR_ROOT"]
		logging.debug('MSMR_ROOT = ' + MSMR_ROOT)
	except KeyError as e:
		logging.error("Please set the environment variable " + str(e))
		sys.exit(1)

	APPS = os.path.abspath(MSMR_ROOT+"/")

	# parse input arguments
	parser = argparse.ArgumentParser(
		description = "Evaluate the performance of MSMR")
	parser.add_argument('filename', nargs='*',
		type=str,
		default = ["msmr.cfg"],
		help = "list of configuration files (default: msmr.cfg)")
	# tom add 20150126
	# verbose : performance data
	parser.add_argument('-v', action='store_true')
	# end tom add 20150126
	args = parser.parse_args()

	if args.filename.__len__() == 0:
		logging.critical(' no configuration file specified??')
		sys.exit(1)
	elif args.filename.__len__() == 1:
		logging.debug('config file: ' + ''.join(args.filename))
	else:
		logging.debug('config files: ' + ', '.join(args.filename))

	logging.debug("set timeformat to '\\nreal %E\\nuser %U\\nsys %S'")
	os.environ['TIMEFORMAT'] = "\nreal %E\nuser %U\nsys %S"

	# run command in shell
	bash_path = which('bash')
	if not bash_path:
		logging.critical("cannot find shell 'bash'")
		sys.exit(1)
	else:
		bash_path = bash_path[0]
		logging.debug("find 'bash' at %s" % bash_path)

	default_options = getMsmrDefaultOptions()
	git_info = getGitInfo()
	root_dir = os.getcwd() # Return a string representing the current working directory.
	# tom add 20150126
	if args.v == True:
		Perf_Test_Flag = 1
		logging.debug(Perf_Test_Flag)
	# end tom add 20150126
	for config_file in args.filename:
		logging.info("processing '" + config_file + "'")
		full_path = getConfigFullPath(config_file)
		
		local_config = readConfigFile(full_path)
		if not local_config:
			logging.warning("skip " + full_path)
			continue
		
		run_dir = genRunDir(full_path, git_info)
		try:
			os.unlink('current')
		except OSError:
			pass
		os.symlink(run_dir, 'current') # Create a symbolic link pointing to run_dir named current.
		if not run_dir:
			continue
		os.chdir(run_dir) # Change the current working directory to run_dir.
		if git_info[3]:
			with open("git_diff", "w") as diff:
				diff.write(git_info[3])

		benchmarks = local_config.sections()
		all_threads = []
		semaphore = threading.BoundedSemaphore(1)
		log_lock = threading.Lock()
		for benchmark in benchmarks:
			if benchmark == "default" or benchmark == "example":
				continue
			processBench(local_config, benchmark)

		os.chdir(root_dir)
