#!/usr/bin/env python
# encoding: utf-8
'''
optional_modules.py

@author:     Stefan Schlenker

@copyright:  2016 CERN

@license:
Copyright (c) 2016, CERN, Universidad de Oviedo.
All rights reserved.
Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

@contact:    Stefan Schlenker
'''

import os
import subprocess
import platform
from glob import glob
from distutils.version import StrictVersion
from shutil import copy, rmtree

moduleInfo = {}


#def stringR

def getEnabledModules():
	"""Get all enabled module metadata"""
	baseDirectory = os.getcwd()
	os.chdir(baseDirectory + os.path.sep + "FrameworkInternals")
	if os.path.exists("EnabledModules"): os.chdir("EnabledModules")
	else:
		print "No enabled modules."
		return
	moduleUrls = glob("*.url")
	enabledModules = {}
	for moduleUrl in moduleUrls:
		module = moduleUrl.replace(".url","")
		minVersion = None
		tag = None
		try:
			minVersion = open(module+".minVersion").readline().rstrip()
			tag = open(module+".tag").readline().rstrip()
		except Exception, ex:
			print ex
		if not minVersion:
			print "Error reading min version info for module "+module
			return None
		if not tag:
			print "Error reading tag info for module "+module
			return None
		enabledModules[module] = {"tag":tag, "minVersion":minVersion}
	os.chdir(baseDirectory)
	return enabledModules

def listEnabledModules():
	"""List registered module URLs"""
	enabledModules = getEnabledModules()
	print "Enabled optional modules and their required quasar versions: "
	for module in enabledModules.keys():
		print module, enabledModules[module]["tag"], "(requires quasar", enabledModules[module]["minVersion"]+")"

def getModuleInfo(serverString="", forceFetch=False):
	"""Downloads list of modules from git and initializes global module list."""

	if not serverString: serverString = "https:://github.com"
	else: forceFetch = True

	baseDirectory = os.getcwd()
	os.chdir(baseDirectory + os.path.sep + "FrameworkInternals")
	#print("Changing directory to: " + baseDirectory + os.path.sep + "FrameworkInternals")
	if not os.path.exists("quasar-modules"): os.mkdir("quasar-modules")
	if forceFetch:
		rmtree("quasar-modules")
		os.mkdir("quasar-modules")
	os.chdir("quasar-modules")
	print("Checking out module list from "+serverString)
	if os.path.exists(".git") and not forceFetch:
		try:
			subprocess.call("git pull origin master" , shell=True)
		except Exception, ex:
			print "Error trying to fetch optional module list from git:", ex
			return False
	else:
		try:
			subprocess.call("git init" , shell=True)
			subprocess.call("git remote add origin "+serverString+"/quasar-team/quasar-modules.git" , shell=True)
			subprocess.call("git remote set-url --push origin push-disabled" , shell=True)
			subprocess.call("git pull origin master" , shell=True)
		except Exception, ex:
			print "Error trying to fetch optional module list from git:", ex
			return False

	moduleUrls = glob("*.url")
	#print moduleUrls
	for moduleUrl in moduleUrls:
		module = moduleUrl.replace(".url","")
		minVersion = None
		try:
			minVersion = open(module+".minVersion").readline().rstrip()
		except Exception, ex:
			print ex
		if not minVersion:
			print "Error reading version info for module "+module
			return False
		moduleInfo[module] = minVersion
	print "List of existing optional modules and their required quasar versions: ", moduleInfo
	os.chdir(baseDirectory)
	return True

def enableModule(moduleName, tag="master", serverString=""):
	"""Enables optional module. Module URL and required quasar version is downloaded from github.
	   Module download is done later at cmake configure stage.
	
	Keyword arguments:
	moduleName   -- name of the optional module
	tag          -- tag to checkout, if not specified, master branch is used
	serverString -- default git server is "https://github.com", specify custom if necessary, e.g. "ssh://git@gitlab.cern.ch:7999"
	"""	
	print "Enabling module", moduleName, ", tag", tag

	if not getModuleInfo(serverString): return False

	print "Checking module to be compatible..."
	quasarVersion = None
	try:
		quasarVersion = open("Design/quasarVersion.txt").readline().rstrip()
	except Exception, ex:
		print ex
	if not quasarVersion:
		print "Error reading version info from Design/quasarVersion.txt"
		return False
	moduleMinVersion = moduleInfo[moduleName]
	if StrictVersion(quasarVersion) >= StrictVersion(moduleMinVersion):
		print "Module "+moduleName+" required version "+moduleMinVersion+" is compatible with installed quasar version "+quasarVersion
	else:
		print "Cannot enable module "+moduleName+". Minimum required version "+moduleMinVersion+" is newer than installed quasar version "+quasarVersion
		return False

	print("Copying module url file...")

	baseDirectory = os.getcwd()
	fwInternalsDir = baseDirectory + os.path.sep + "FrameworkInternals"
	os.chdir(fwInternalsDir)

	# Check first if module is maybe already present with different version
	#
	tagFileName = "EnabledModules/"+moduleName+".tag"
	oldTag = open(tagFileName).read()
	if oldTag!=tag:
		print "Old version of "+moduleName+" exists ("+oldTag+"). Removing it first..."
		os.chdir(baseDirectory)
		removeModule(moduleName)
		os.chdir(fwInternalsDir)

	# actually enable
	#
	if not os.path.isdir("EnabledModules"): os.mkdir("EnabledModules")
	# FIXME: check if previous tag exists and possibly needs update
	try:
		for file in glob("quasar-modules/"+moduleName+".*"):
			copy(file, "EnabledModules/")
		# change URL if non-default server is specified
		if serverString:
			urlFileName = "EnabledModules/"+moduleName+".url"
			url = open(urlFileName).read()
			serverBegin = url.find("://")+3
			serverEnd = url.find("/", serverBegin)
			print "current server="+url[:serverEnd]
			url = serverString+url[serverEnd:]
			print "new url="+url
			file = open(urlFileName, "w")
			file.write(url)
		# add tag
		if os.path.exists(tagFileName): os.remove(tagFileName)
		file = open(tagFileName, "w")
		file.write(tag)
	except Exception, ex:
		print "Failed to set up module files in FrameworkInternals/EnabledModules/ :", ex
		return False

	os.chdir(baseDirectory)

	print("Created module files.")

	return True

def replaceModuleGitServer(moduleName, serverString="github.com/"):
	"""Changes the module source URL replacing the configured git server with the specified one.
	
	Keyword arguments:
	moduleName -- name of the optional module
	serverString -- string containing [user]"
	"""	

def disableModule(moduleName):
	"""Disables optional module. Module files will be deleted.
	
	Keyword arguments:
	moduleName -- name of the optional module
	"""	

	if not os.path.exists("FrameworkInternals/EnabledModules/"+moduleName+".url"):
		print "Error, module "+moduleName+" seems not installed!"
		return False
	try:
		for file in glob("FrameworkInternals/EnabledModules/"+moduleName+".*"):
			os.remove(file)
	except Exception, ex:
		print "Failed to remove module file in FrameworkInternals/EnabledModules/ :", ex
		return False

	print("Removed url file of "+moduleName)
	print("Remove module code if existing...")
	removeModule(moduleName)

	return True

def removeModule(module):
	"""Removes optional module files without disabling it. Upon prepare_build or build the module will be freshly fetched.
	
	Keyword arguments:
	moduleName -- name of the optional module
	"""

	# first check whether module contains modified files
	#
	baseDirectory = os.getcwd()
	os.chdir(baseDirectory + os.path.sep + module)
	output = subprocess.Popen(['git', 'ls-files', '-m'], stdout=subprocess.PIPE).communicate()[0]
	## with python 2.7 use the following:
	## output = subprocess.call("git ls-files -m", shell=True)
	if output:
		print "Error, tracked modified files exist in "+module+". Please resolve this before removing the module. Modified files: "
		print output
		return
	os.chdir(baseDirectory)

	# actually remove dirs and files
	#
	dirs = glob(module+"*")
	dirs.extend(glob("FrameworkInternals/EnabledModules/"+module+"*/"))
	if dirs:
		print "Removing files of module", module
		for dir in dirs:
			print "Removing", dir
			try:
				rmtree(dir)
			except Exception, ex:
				print "Failed to remove dir", dir, ex
	else: print "Nothing to be removed for module", module

def removeModules():
	"""Remove all enabled modules"""
	enabledModules = getEnabledModules()
	print "Removing downloaded modules"
	for module in enabledModules.keys():
		removeModule(module)
