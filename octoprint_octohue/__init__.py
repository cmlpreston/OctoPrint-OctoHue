# coding=utf-8
from __future__ import absolute_import
from qhue import Bridge, QhueException
from colormath.color_objects import XYZColor, sRGBColor
from colormath.color_conversions import convert_color
import octoprint.plugin
import flask
from octoprint_octohue import HueXYtoCT
from octoprint_octohue.HueXYtoCT import calculate_PhillipsHueCT_withCCT

class OctohuePlugin(octoprint.plugin.StartupPlugin,
					octoprint.plugin.ShutdownPlugin,
					octoprint.plugin.SettingsPlugin,
					octoprint.plugin.SimpleApiPlugin,
                    octoprint.plugin.AssetPlugin,
                    octoprint.plugin.TemplatePlugin,
					octoprint.plugin.EventHandlerPlugin):

	# Hue Functions
	pbridge=''

	def build_state(self, red, green=None, blue=None, transitiontime=5, bri=255, ct=None):
		#self._logger.debug("ct is %d" % ct ) if ct is not None else self._logger.debug("ct is None")
		if ct is None:
			state = {"on": True, "xy": None, "transitiontime": transitiontime, "bri": bri}
			self._logger.debug("RGB Input - R:%s G:%s B:%s Bri:%s" % (red, green, blue, bri))
			if isinstance(red, str):
			# If Red is a string or unicode assume a hex string is passed and convert it to numberic 
				rstring = red
				red = int(rstring[1:3], 16)
				green = int(rstring[3:5], 16)
				blue = int(rstring[5:], 16)

			# We need to convert the RGB value to Yxz.
			redScale = float(red) / 255.0
			greenScale = float(green) / 255.0
			blueScale = float(blue) / 255.0
			
			rgb = sRGBColor(redScale, greenScale, blueScale)
			xyz = convert_color(rgb, XYZColor)

			x = xyz.get_value_tuple()[0]
			y = xyz.get_value_tuple()[1]
			z = xyz.get_value_tuple()[2]
			#To use only X and Y, we need to noralize using Z i.e value = value / ( X + Y + Z)
			normx = x / ( x + y + z)
			normy = y / ( x + y + z) 
			
			calc_ct = calculate_PhillipsHueCT_withCCT(HueXYtoCT.calculate_CCT_withHueXY(normx,normy))

			self._logger.debug("x:%f y:%f, ct is %f" % (normx,normy,calc_ct))

			# set state if ct is within 155 to 500 range
			if 155 <= calc_ct <= 200: 
				self._logger.debug("Adjusting state to use CT instead of XY")
				del state['xy']
				state['ct'] = int(calc_ct)
			else:
				state['xy'] = [normx, normy]

		else:
			#self._logger.debug("ct build_state state is %s" % self._state )
			state = {"on": True, "transitiontime": transitiontime, "bri": int(bri), "ct": int(ct) }
		
		if state is not None:
			self._logger.debug("build_state state is %s" % state )
		else: 
			self._logger.debug("build_state state is None")
		return self.set_state(state)

	def get_state(self):
		if self._settings.get(['lampisgroup']) == True:
			self._state = self.pbridge.groups[self._settings.get(['lampid'])]().get("action")['on']
		else:
			self._state = self.pbridge.lights[self._settings.get(['lampid'])]().get("state")['on']
		self._logger.debug("Get State is %s" % self._state )
		return self._state

	def set_state(self, state):
		self._logger.debug("Setting lampid: %s  Is Group: %s with State: %s" % (self._settings.get(['lampid']),self._settings.get(['lampisgroup']), state))
		if self._settings.get(['lampisgroup']) == True:
			self.pbridge.groups[self._settings.get(['lampid'])].action(**state)
		else:
			self._logger.debug("set_state state is %s" % state)
			l_id = self._settings.get(['lampid'])

			if l_id is not None: 
				self._logger.debug("l_id is %s" % l_id) 
			else: 
				self._logger.debug("l_id is None")
			self.pbridge.lights[l_id].state(**state)

	def toggle_state(self):
		if self.get_state():
			self.set_state({"on": False})
		else:
			self.set_state({"on": True})

	def on_after_startup(self):
		self._logger.info("Octohue is alive!")
		if self._settings.get(["statusDict"]) == '': 
				self._logger.info("Bootstrapping Octohue Status Defaults")
				self._settings.set(["statusDict"], {
					'Connected' : {
						'colour':'#FFFFFF',
						'ct':155,
						'brightness':255,
						'turnoff':False
					},
					'Disconnected': {
						'colour':'',
						'ct':155,
						'brightness':"",
						'turnoff':True
					},
					'PrintStarted' : {
						'colour':'#FFFFFF',
						'ct':155,
						'brightness':255,
						'turnoff':False
					},
					'PrintResumed' : {
						'colour':'#FFFFFF',
						'ct':155,
						'brightness':255,
						'turnoff':False
					},
					'PrintDone': {
						'colour':'#33FF36',
						'ct':155,
						'brightness':255,
						'turnoff':False
					},
					'PrintFailed':{
						'colour':'#FF0000',
						'ct':155,
						'brightness':255,
						'turnoff':False
					}
				})
				self._settings.save()

		self._logger.debug("Bridge Address is %s" % self._settings.get(['bridgeaddr']) if self._settings.get(['bridgeaddr']) else "Please set Bridge Address in settings")
		self._logger.debug("Hue Username is %s" % self._settings.get(['husername']) if self._settings.get(['husername']) else "Please set Hue Username in settings")
		self.pbridge = Bridge(self._settings.get(['bridgeaddr']), self._settings.get(['husername']))
		self._logger.debug("Bridge established at: %s" % self.pbridge.url)

	def on_shutdown(self):
		self._logger.info("Ladies and Gentlemen, thank you and goodnight!")
		if self._settings.get(['offonshutdown']) == True:
			self.set_state({"on": False})

	def get_api_commands(self):
		return dict(
			togglehue=[]
		)
	
	def on_api_command(self, command, data):
		if command == 'togglehue':
			self.toggle_state()

	# Trigger state on Status match
	def on_event(self, event, payload):
		self._logger.debug("Recieved Status: %s from Printer" % event)
		if event in self._settings.get(["statusDict"]):
			self._logger.info("Received Configured Status Event: %s" % event)
			if self._settings.get(['statusDict'])[event]['turnoff'] == False:
				brightness = self._settings.get(['statusDict'])[event]['brightness'] if self._settings.get(['statusDict'])[event]['brightness'] else self._settings.get(['defaultbri'])
				ct = self._settings.get(['statusDict'])[event]['ct'] if self._settings.get(['statusDict'])[event]['ct'] else None
				if ct is None:
						self._logger.debug("ct is None")
				else:
						self._logger.debug("ct is %s" % ct)
				# self._logger.info("ct is: %d" % int(ct)) if not None else self._logger.info("ct is None") 
				if self._settings.get(['statusDict'])[event]['colour'] is not None:
					self.build_state(self._settings.get(['statusDict'])[event]['colour'],bri=int(brightness),ct=ct)
				else:
					self.build_state(bri=int(brightness),ct=int(ct))

			else:
				self.set_state({"on": False})



	# General Octoprint Hooks Below

	def get_settings_defaults(self):
		return dict(
			bridgeaddr="",
			husername="",
			lampid="",
			lampisgroup="",
			defaultbri=255,
			defaultct=155, # colour temperature in mired
			offonshutdown=True,
			showhuetoggle=True,
			statusDict=""
		)

	def get_settings_restricted_paths(self):
		return dict(admin=[["bridgeaddr"],["husername"]])
	
	def on_settings_save(self, data):
		octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
		self._logger.debug("Saved Bridge Address: %s" % self._settings.get(['bridgeaddr']) if self._settings.get(['bridgeaddr']) else "Please set Bridge Address in settings")
		self._logger.debug("Saved Hue Username: %s" % self._settings.get(['husername']) if self._settings.get(['husername']) else "Please set Hue Username in settings")
		self.pbridge = Bridge(self._settings.get(['bridgeaddr']), self._settings.get(['husername']))
		self._logger.debug("New Bridge established at: %s" % self.pbridge.url)
		
	def get_template_vars(self):
		return dict(
			bridgeaddr=self._settings.get(["bridgeaddr"]),
			husername=self._settings.get(["husername"]),
			lampid=self._settings.get(["lampid"]),
			lampisgroup=self._settings.get(["lampisgroup"]),
			defaultbri=self._settings.get(["defaultbri"]),
			defaultct=self._settings.get(["defaultct"]),
			offonshutdown=self._settings.get(["offonshutdown"]),
			showhuetoggle=self._settings.get(["showhuetoggle"]),
			statusDict=self._settings.get(["statusDict"])
		)
	
	def get_template_configs(self):
		return [
			dict(type="settings", custom_bindings=True)
		]

	##~~ AssetPlugin mixin

	def get_assets(self):
		# Define your plugin's asset files to automatically include in the
		# core UI here.
		return dict(
			js=["js/OctoHue.js"],
			css=["css/OctoHue.css"],
			less=["less/OctoHue.less"]
		)

	##~~ Softwareupdate hook

	def get_update_information(self):
		# Define the configuration for your plugin to use with the Software Update
		# Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
		# for details.
		return dict(
			OctoHue=dict(
				displayName="OctohueCT Plugin",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="cmlpreston",
				repo="OctoPrint-OctoHue",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/cmlpreston/OctoPrint-OctoHue/archive/{target_version}.zip"
			)
		)

__plugin_name__ = "OctohueCT"
__plugin_pythoncompat__ = ">=2.7,<4" # Compatible with python 2 and 3

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = OctohuePlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}

