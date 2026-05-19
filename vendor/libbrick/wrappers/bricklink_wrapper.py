#!/usr/bin/env python3

# Standard Library
import os
import sys
import math
import time
import random
import statistics

# PIP3 modules
import yaml
import urllib3
import requests
import bricklink.api

# local repo modules
import libbrick.path_utils
import libbrick.wrappers.wrapper_base as wrapper_base

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#https://www.bricklink.com/v3/api.page

class BrickLink(wrapper_base.BaseWrapperClass):
	#============================
	#============================
	def __init__(self):
		self.debug = True
		self.api_data = None
		self.bricklink_api = None
		self.color_dict = None
		self.price_count = 0
		self.image_checks = 0
		self.image_url_checks = {}
		self.status_counts = {'success': 0, 'timeout': 0, 'fail': 0}
		self.data_caches = {
			'bricklink_category_cache': 		'yml',
			'bricklink_set_brick_weight_cache': 'yml',
			'bricklink_minifig_set_cache': 		'yml',
			'bricklink_minifig_category_cache': 'yml',
			'bricklink_minifig_superset_cache': 'yml',
			'bricklink_element_id_map_cache':	'yml',

			'bricklink_price_cache': 			'json',
			'bricklink_subset_cache': 			'json',
			'bricklink_minifig_cache': 			'json',
			'bricklink_part_cache': 			'json',
			'bricklink_set_cache': 				'json',
		}
		self.start()

	#============================
	#============================
	def _ensure_api_client(self):
		"""
		Lazily load OAuth1 credentials and build BrickLinkAPI client on first use.

		2026-05-19: Deferred credential loading for downstream FastAPI service;
		construction must succeed without bricklink_api_private.yml.

		Raises:
			FileNotFoundError: if no credential file resolved.
			KeyError: if file is missing a required field.
		"""
		if self.bricklink_api is not None:
			return
		key_file_name = 'bricklink_api_private.yml'
		env_path = os.environ.get('BRICKLINK_API_FILE')
		key_paths = []
		if env_path:
			key_paths.append(env_path)
		git_root = libbrick.path_utils.get_git_root()
		if git_root is not None:
			key_paths.append(os.path.join(git_root, key_file_name))
		key_paths.append(key_file_name)
		key_paths.append(os.path.join(os.path.dirname(__file__), key_file_name))
		for key_path in key_paths:
			if os.path.exists(key_path):
				with open(key_path, 'r') as f:
					self.api_data = yaml.safe_load(f)
				break
		if self.api_data is None:
			raise FileNotFoundError(f"BrickLink API key file not found in: {key_paths}")
		self.bricklink_api = bricklink.api.BrickLinkAPI(
			self.api_data['consumer_key'],
			self.api_data['consumer_secret'],
			self.api_data['token_value'],
			self.api_data['token_secret'],
		)

	#============================
	#============================
	def _bricklink_get(self, url):
		""" common function for all API calls """
		self._ensure_api_client()
		#random sleep of 0-1 seconds to help server load
		time.sleep(random.random()+random.random())
		status, headers, response = self.bricklink_api.get(url)
		self.api_calls += 1
		sys.stderr.write('#')
		#sys.stderr.flush()
		self.api_log.append(url)
		error_msg = False
		if response.get('data') is None or len(response.get('data')) == 0:
			error_msg = True
		if error_msg is True:
			self.save_cache()
			print('URL', url)
			print("STATUS", status)
			print("HEADERS", headers)
			print("RESPONSE", response)
			raise LookupError
		data = response['data']
		if isinstance(data, dict):
			data['time'] = int(time.time())
		if self.api_calls % 50 == 0:
			self.save_cache()
		return data

	#============================
	#============================
	def getColorList(self):
		colors_data = self._bricklink_get('colors')
		print("received data for {0} colors".format(len(colors_data)))
		self.color_dict = {0: {}, }
		for color_data in colors_data:
			#import pprint
			#pprint.pprint(color_data)
			if len(color_data.get('color_code', '')) == 6:
				color_data['color_code'] = '#' + color_data.get('color_code')
			color_id = color_data['color_id']
			self.color_dict[color_id] = color_data
		return

	#============================
	#============================
	def getColorDataFromColorID(self, colorID):
		if self.color_dict is None:
			self.getColorList()
		return self.color_dict[colorID]

	#============================
	#============================
	def getColorNameFromColorID(self, colorID):
		if self.color_dict is None:
			self.getColorList()
		return self.color_dict[colorID]['color_name']

	#============================
	#============================
	def getCategoryName(self, categoryID):
		""" get the category name from BrickLink """
		###################
		# expire does NOT apply to category names
		category_name = self.bricklink_category_cache.get(categoryID)
		if category_name is not None:
			return category_name
		###################
		category_data = self._bricklink_get('categories/{0}'.format(categoryID))
		###################
		#print(category_data)
		if category_data.get('parent_id') is not None and category_data.get('parent_id') > 1:
			parent_name = self.getCategoryName(category_data.get('parent_id'))
			if not category_data['category_name'].startswith(parent_name):
				category_name = parent_name + ' ' + category_data['category_name']
				category_name = self.decode_and_normalize(category_name)
				category_data['category_name'] = category_name
			else:
				category_name = category_data['category_name']
		else:
			category_name = category_data['category_name']
		self.bricklink_category_cache[categoryID] = category_name
		#print(category_name)
		return category_name

	#============================
	#============================
	def getCategoryNameFromMinifigID(self, minifigID):
		category_name = self.bricklink_minifig_category_cache.get(minifigID)
		if category_name is not None:
			return category_name
		superset_ids = self.getSupersetFromMinifigID(minifigID)
		if superset_ids is None or len(superset_ids) == 0:
			return None
		setID = superset_ids[0]
		set_data = self.getSetData(setID)
		category_name = self.getCategoryName(set_data['category_id'])
		category_name = self.decode_and_normalize(category_name)
		print('MINIFIG {0} -- {1} -- from BrickLink website'.format(minifigID, category_name))
		self.bricklink_minifig_category_cache[minifigID] = category_name
		return category_name

	#============================
	#============================
	def getSetData(self, setID, verbose=True):
		""" get the set data from BrickLink using the string setID """
		self._check_set_ID(setID)
		set_data = self.getSetDataDirect(setID, verbose)
		set_data['set_id'] = setID
		return set_data

	#============================
	#============================
	def getSetDataDetails(self, setID, verbose=True):
		""" get the set data from BrickLink using the string setID """
		self._check_set_ID(setID)
		set_data = self.getSetDataDirect(setID, verbose)
		price_data = self.getSetPriceData(setID)
		set_data.update(price_data)
		set_data['set_id'] = setID
		return set_data

	#============================
	#============================
	def getSetDataDirect(self, setID, verbose=True):
		""" get the set data from BrickLink using a setID with hyphen, e.g. 71515-2 """
		self._check_set_ID(setID)
		###################
		set_data = self.bricklink_set_cache.get(setID)
		if self._check_if_data_valid(set_data) is True:
			if verbose is True:
				print('SET {0} -- {1} ({2}) -- from cache'.format(
					set_data.get('no'), set_data.get('name'), set_data.get('year_released'),))
			# update connected data
			set_data['category_name'] = self.getCategoryName(set_data['category_id'])
			set_data['name'] = self.decode_and_normalize(set_data['name'])
			self.bricklink_set_cache[setID] = set_data
			return set_data
		###################
		set_data = self._bricklink_get('items/set/{0}'.format(setID))
		set_data['name'] = self.decode_and_normalize(set_data['name'])
		###################
		if verbose is True:
			print('SET {0} -- {1} ({2}) -- from BrickLink website'.format(
				set_data.get('no'), set_data.get('name'), set_data.get('year_released'),))
		set_data['category_name'] = self.getCategoryName(set_data['category_id'])
		self.bricklink_set_cache[setID] = set_data
		return set_data

	#============================
	#============================
	def getSupersetFromMinifigID(self, minifigID, verbose=True):
		""" get all sets that include minifig"""
		set_id_list = self.bricklink_minifig_superset_cache.get(minifigID)
		###################
		if set_id_list is not None and len(set_id_list) > 0:
			if verbose is True:
				print('SUPERSET MINIFIG {0} -- found {1} sets -- from cache'.format(
					minifigID, len(set_id_list), ))
			# update connected data
			return set_id_list
		###################
		result = self._bricklink_get('items/minifig/{0}/supersets'.format(minifigID))
		#import pprint
		#pprint.pprint(result)
		set_id_list = []
		supersets_tree = result[0]['entries']
		for entry in supersets_tree:
			#print(len(entry))
			#print(entry.keys())
			item = entry['item']
			#print(len(item))
			#print(item.keys())
			if item['type'] == 'SET' and len(item['no']) <= 7:
				setID = item['no']
				set_id_list.append(setID)
		###################
		if verbose is True:
			print('MINIFIG {0} -- {1} supersets -- from BrickLink website'.format(minifigID, len(set_id_list)))
		self.bricklink_minifig_superset_cache[minifigID] = set_id_list
		return set_id_list

	#============================
	#============================
	def getPartsFromSet(self, setID, verbose=True):
		""" get all the parts from a set from BrickLink using the string setID """
		self._check_set_ID(setID)
		###################
		subsets_tree = self._bricklink_get('items/set/{0}/subsets'.format(setID))
		###################
		if verbose is True:
			print('SET {0} -- {1} parts -- from BrickLink website'.format(setID, len(subsets_tree)))
		if self.debug is True:
			pass
			#self.bricklink_subsets_cache[setID] = subsets_tree
		return subsets_tree

	#============================
	#============================
	def getSetBrickWeight(self, setID, verbose=True):
		""" custom function to add up the weight of all the parts in a set """
		self._check_set_ID(setID)
		set_data = self.getSetData(setID, verbose=False)
		###################
		string_weight = self.bricklink_set_brick_weight_cache.get(setID)
		if string_weight is not None:
			if verbose is True:
				print('SET {0} -- {1} grams -- from set data'.format(setID, set_data['weight']))
				print('SET {0} -- {1} grams -- from cache'.format(setID, string_weight))
			return string_weight
		###################
		subsets_tree = self.getPartsFromSet(setID, verbose=False)
		total_weight = 0
		for part in subsets_tree:
			for entry in part['entries']:
				item = entry['item']
				if item['type'] == 'MINIFIG':
					continue
				if item['type'] == 'GEAR':
					print(item['type'], item['name'])
					continue
				if item['type'] != 'PART':
					self.save_cache()
					print(item)
					print(item['type'])
					sys.exit(1)
				item_plus = self.getPartData(item['no'], verbose=False)
				weight = float(item_plus['weight'])
				qty = int(entry['quantity'])
				if verbose is True:
					print("{0:d} items weighing {1:.3f} grams".format(qty, weight))
				item_weight = (weight * qty)
				#print(item_weight)
				total_weight += item_weight
		string_weight = '{0:.3f}'.format(total_weight)
		if verbose is True:
			print('SET {0} -- {1} grams -- from set data'.format(setID, set_data['weight']))
			print('SET {0} -- {1} grams -- from BrickLink website'.format(setID, string_weight))
		self.bricklink_set_brick_weight_cache[setID] = string_weight
		return string_weight

	#============================
	#============================
	def _lookUpPriceDataCache(self, item_id, color_id=None, verbose=True):
		""" common function for looking price data from cache """
		###################
		key = str(item_id)
		if color_id is not None:
			key = '{0}_{1}'.format(item_id, color_id)
		price_data = self.bricklink_price_cache.get(key)
		if self._check_if_data_valid(price_data) is True:
			if verbose is True:
				print('PRICE {0} -- ${1:.2f} -- ${2:.2f} -- ${3:.2f} -- ${4:.2f} -- from cache'.format(
					price_data.get('item_id'),
					float(price_data.get( 'new_median_sale_price'))/100.,
					float(price_data.get('used_median_sale_price'))/100.,
					float(price_data.get( 'new_median_list_price'))/100.,
					float(price_data.get('used_median_list_price'))/100.,
				))
			return price_data
		###################
		#print('price_data=', price_data)
		return None

	#============================
	#============================
	def _compilePriceData(self, item_id, new_price_sale_details, used_price_sale_details,
			new_price_list_details, used_price_list_details, min_qty=1, color_id=None, verbose=True):
		###################
		new_avg_sale_price 	= int(float(new_price_sale_details['avg_price'])*100)
		new_sale_qty 		= int(new_price_sale_details['total_quantity'])
		used_avg_sale_price = int(float(used_price_sale_details['avg_price'])*100)
		used_sale_qty 		= int(used_price_sale_details['total_quantity'])
		new_avg_list_price 	= int(float(new_price_list_details['avg_price'])*100)
		new_list_qty 		= int(new_price_list_details['total_quantity'])
		used_avg_list_price = int(float(used_price_list_details['avg_price'])*100)
		used_list_qty 		= int(used_price_list_details['total_quantity'])
		###################
		# New Sales
		minimum_prices_for_calc = 5
		new_median_sale_price = -1
		if new_sale_qty >= 1:
			new_sale_prices = []
			for item in new_price_sale_details['price_detail']:
				if int(item['quantity']) < min_qty:
					continue
				for i in range(int(item['quantity'])):
					new_sale_prices.append(int(float(item['unit_price'])*100))
			if len(new_sale_prices) > minimum_prices_for_calc:
				new_median_sale_price = int(statistics.median(new_sale_prices))
			del new_sale_prices
		###################
		# Used Sales
		used_median_sale_price = -1
		if used_sale_qty >= 1:
			used_sale_prices = []
			for item in used_price_sale_details['price_detail']:
				if int(item['quantity']) < min_qty:
					continue
				for i in range(int(item['quantity'])):
					used_sale_prices.append(int(float(item['unit_price'])*100))
			if len(used_sale_prices) > minimum_prices_for_calc:
				used_median_sale_price = int(statistics.median(used_sale_prices))
			del used_sale_prices
		###################
		# New Sales
		new_median_list_price = -1
		if new_list_qty >= 1:
			new_list_prices = []
			for item in new_price_list_details['price_detail']:
				if int(item['quantity']) < min_qty:
					continue
				for i in range(int(item['quantity'])):
					new_list_prices.append(int(float(item['unit_price'])*100))
			if len(new_list_prices) > minimum_prices_for_calc:
				new_median_list_price = int(statistics.median(new_list_prices))
				new_list_prices2 = []
				for listp in new_list_prices:
					if listp <= new_median_list_price:
						new_list_prices2.append(listp)
				new_median_list_price = int(statistics.median(new_list_prices2))
			del new_list_prices
		###################
		# Used Sales
		used_median_list_price = -1
		if used_list_qty >= 1:
			used_list_prices = []
			for item in used_price_list_details['price_detail']:
				if int(item['quantity']) < min_qty:
					continue
				for i in range(int(item['quantity'])):
					used_list_prices.append(int(float(item['unit_price'])*100))
			if len(used_list_prices) > minimum_prices_for_calc:
				used_median_list_price = int(statistics.median(used_list_prices))
				used_list_prices2 = []
				for listp in used_list_prices:
					if listp <= used_median_list_price:
						used_list_prices2.append(listp)
				print(len(used_list_prices2), len(used_list_prices))
				used_median_list_price = int(statistics.median(used_list_prices2))
			del used_list_prices
		###################
		price_data = {
			'item_id':					item_id,
			##=========
			'new_avg_sale_price': 		new_avg_sale_price,
			'new_median_sale_price': 	new_median_sale_price,
			'new_sale_qty': 			new_sale_qty,
			##=========
			'used_avg_sale_price': 		used_avg_sale_price,
			'used_median_sale_price': 	used_median_sale_price,
			'used_sale_qty': 			used_sale_qty,
			##=========
			'new_avg_list_price': 		new_avg_list_price,
			'new_median_list_price': 	new_median_list_price,
			'new_list_qty': 			new_list_qty,
			##=========
			'used_avg_list_price': 		used_avg_list_price,
			'used_median_list_price': 	used_median_list_price,
			'used_list_qty': 			used_list_qty,
			##=========
			'time':						int(time.time()),
		}
		if verbose is True:
			print('PRICE {0} -- ns ${1:.2f} -- nl ${3:.2f} -- us ${2:.2f} -- ul ${4:.2f} -- from BrickLink'.format(
				price_data.get('item_id'),
				float(price_data.get( 'new_median_sale_price'))/100.,
				float(price_data.get('used_median_sale_price'))/100.,
				float(price_data.get( 'new_median_list_price'))/100.,
				float(price_data.get('used_median_list_price'))/100.,
			))
			if color_id is not None:
				print('color_id={0}'.format(color_id))
		key = str(item_id)
		if color_id is not None:
			key = '{0}_{1}'.format(item_id, color_id)
		if min_qty == 1:
			self.bricklink_price_cache[key] = price_data
		self.price_count += 1
		if self.price_count % 10 == 0:
			self.save_cache(single_cache_name='bricklink_price_cache')
		return price_data

	#============================
	#============================
	def getPriceDetails(self, item_id, type, guide_type='sold', new_or_used='U',
			country_code='US', currency_code='USD', color_id=None):
		""" get price details from BrickLink using the string """
		url = 'items/{0}/{1}/price'.format(type, item_id)
		url += '?guide_type={0}'.format(guide_type)
		url += '&new_or_used={0}'.format(new_or_used)
		url += '&country_code={0}'.format(country_code)
		url += '&currency_code={0}'.format(currency_code)
		if color_id is not None:
			url += '&color_id={0}'.format(color_id)
		price_details = self._bricklink_get(url)
		return price_details

	#============================
	#============================
	def getSetPriceDetails(self, setID, guide_type='sold', new_or_used='U',
			country_code='US', currency_code='USD', verbose=True):
		""" get price details from BrickLink using the string setID """
		#https://www.bricklink.com/v3/api.page?page=get-price-guide
		self._check_set_ID(setID)
		###################
		price_details = self.getPriceDetails(setID, 'set', guide_type, new_or_used,
				country_code, currency_code)
		qty = price_details['total_quantity']
		###################
		if verbose is True and qty > 1:
			avg_price = float(price_details['avg_price'])
			print('SET {0} -- ${1:.2f} average price for {2} {3} {4} -- from BrickLink website'.format(
				setID, avg_price, qty, new_or_used, guide_type))
		return price_details

	#============================
	#============================
	def getSetPriceData(self, setID, min_qty=1, verbose=False):
		""" compile price data from BrickLink using the string setID """
		self._check_set_ID(setID)
		###################
		price_data = self._lookUpPriceDataCache(setID, verbose=verbose)
		if min_qty == 1 and price_data is not None:
			return price_data
		###################
		used_price_sale_details = self.getSetPriceDetails(setID, guide_type='sold', new_or_used='U', verbose=verbose)
		new_price_sale_details 	= self.getSetPriceDetails(setID, guide_type='sold', new_or_used='N', verbose=verbose)
		used_price_list_details = self.getSetPriceDetails(setID, guide_type='stock', new_or_used='U', verbose=verbose)
		new_price_list_details 	= self.getSetPriceDetails(setID, guide_type='stock', new_or_used='N', verbose=verbose)
		price_data = self._compilePriceData(setID,
			new_price_sale_details, used_price_sale_details,
			new_price_list_details, used_price_list_details, min_qty=min_qty)
		return price_data

	#============================
	#============================
	def getPartPriceDetails(self, partID, color_id=None, guide_type='sold', new_or_used='U',
			country_code='US', currency_code='USD', verbose=True):
		""" get price details from BrickLink using the string partID """
		#https://www.bricklink.com/v3/api.page?page=get-price-guide
		###################
		price_details = self.getPriceDetails(partID, 'part', guide_type, new_or_used,
				country_code, currency_code, color_id)
		qty = price_details['total_quantity']
		###################
		if verbose is True and qty > 1:
			avg_price = float(price_details['avg_price'])
			print('PART {0} -- ${1:.2f} average price for {2} {3} {4} -- from BrickLink website'.format(
				partID, avg_price, qty, new_or_used, guide_type))
		return price_details

	#============================
	#============================
	def getPartPriceData(self, partID, colorID=None, min_qty=1, verbose=False):
		""" compile price data from BrickLink using the string partID """
		###################
		price_data = self._lookUpPriceDataCache(partID, color_id=colorID, verbose=verbose)
		if min_qty == 1 and price_data is not None:
			return price_data
		###################
		used_price_sale_details = self.getPartPriceDetails(partID, colorID, guide_type='sold', new_or_used='U', verbose=verbose)
		new_price_sale_details 	= self.getPartPriceDetails(partID, colorID, guide_type='sold', new_or_used='N', verbose=verbose)
		used_price_list_details = self.getPartPriceDetails(partID, colorID, guide_type='stock', new_or_used='U', verbose=verbose)
		new_price_list_details 	= self.getPartPriceDetails(partID, colorID, guide_type='stock', new_or_used='N', verbose=verbose)
		price_data = self._compilePriceData(partID,
			new_price_sale_details, used_price_sale_details,
			new_price_list_details, used_price_list_details,
			color_id=colorID, min_qty=min_qty)
		return price_data

	#============================
	#============================
	def getMinifigPriceDetails(self, minifigID, guide_type='sold', new_or_used='U',
			country_code='US', currency_code='USD', verbose=True):
		""" get price details from BrickLink using an string minifigID """
		###################
		price_details = self.getPriceDetails(minifigID, 'minifig', guide_type, new_or_used,
				country_code, currency_code)
		###################
		avg_price = float(price_details['avg_price'])
		qty = price_details['total_quantity']
		if verbose is True and qty > 1:
			print('MINIFIG {0} -- ${1:.2f} average price for {2} {3} {4} -- from BrickLink website'.format(
				minifigID, avg_price, qty, new_or_used, guide_type))
		return price_details

	#============================
	#============================
	def getMinifigPriceData(self, minifigID, min_qty=1, verbose=False):
		""" compile price data from BrickLink using an string minifigID """
		price_data = self._lookUpPriceDataCache(minifigID, verbose=verbose)
		if min_qty == 1 and price_data is not None:
			return price_data
		used_price_sale_details = self.getMinifigPriceDetails(minifigID, guide_type='sold', new_or_used='U', verbose=verbose)
		new_price_sale_details 	= self.getMinifigPriceDetails(minifigID, guide_type='sold', new_or_used='N', verbose=verbose)
		used_price_list_details = self.getMinifigPriceDetails(minifigID, guide_type='stock', new_or_used='U', verbose=verbose)
		new_price_list_details 	= self.getMinifigPriceDetails(minifigID, guide_type='stock', new_or_used='N', verbose=verbose)
		price_data = self._compilePriceData(minifigID,
			new_price_sale_details, used_price_sale_details,
			new_price_list_details, used_price_list_details,
			min_qty=min_qty,
			)
		return price_data

	#============================
	#============================
	def getSetIDsFromSet(self, setID, verbose=True):
		""" get list of set data dicts from BrickLink using the string setID """
		self._check_set_ID(setID)
		###################
		set_id_tree = self.bricklink_subset_cache.get(setID)
		if set_id_tree is not None and isinstance(set_id_tree, list):
			if verbose is True:
				print('SET {0} -- {1} sub-sets -- from cache'.format(setID, len(set_id_tree)))
			return set_id_tree
		###################
		subsets_tree = self.getPartsFromSet(setID, verbose=False)
		set_id_tree = []
		for part in subsets_tree:
			for entry in part['entries']:
				item = entry['item']
				if item['type'] != 'SET':
					continue
				setID = item['no']
				#qty = entry.get('quantity', 1)
				qty = entry['quantity']
				for qi in range(qty):
					set_id_tree.append(setID)
		set_id_tree.sort()
		if verbose is True:
			print('SET {0} -- {1} sub-sets -- from BrickLink website'.format(setID, len(set_id_tree)))
		self.bricklink_subset_cache[setID] = set_id_tree
		return set_id_tree

	#============================
	#============================
	def getMinifigIDsFromSet(self, setID, verbose=True):
		""" get list of minifig data dicts from BrickLink using the string setID """
		self._check_set_ID(setID)
		###################
		minifig_id_tree = self.bricklink_minifig_set_cache.get(setID)
		if minifig_id_tree is not None and isinstance(minifig_id_tree, list):
			if verbose is True:
				print('SET {0} -- {1} minifigs -- from cache'.format(setID, len(minifig_id_tree)))
			return minifig_id_tree
		###################
		subsets_tree = self.getPartsFromSet(setID, verbose=False)
		minifig_id_tree = []
		for part in subsets_tree:
			for entry in part['entries']:
				item = entry['item']
				if item['type'] != 'MINIFIG':
					continue
				minifigID = item['no']
				#qty = entry.get('quantity', 1)
				qty = entry['quantity']
				for qi in range(qty):
					minifig_id_tree.append(minifigID)
		minifig_id_tree.sort()
		if verbose is True:
			print('SET {0} -- {1} minifigs -- from BrickLink website'.format(setID, len(minifig_id_tree)))
		self.bricklink_minifig_set_cache[setID] = minifig_id_tree
		return minifig_id_tree

	#============================
	#============================
	def getMinifigData(self, minifigID, verbose=True):
		""" get individual minifig data from BrickLink using an string minifigID """

		###################
		minifig_data = self.bricklink_minifig_cache.get(str(minifigID))
		if self._check_if_data_valid(minifig_data) is True:
			if verbose is True:
				print('MINIFIG {0} -- {1} ({2}) -- from cache'.format(
					minifig_data.get('no'), minifig_data.get('name')[:60], minifig_data.get('year_released'),))
			return minifig_data
		###################
		minifig_data = self._bricklink_get('items/minifig/{0}'.format(minifigID))
		minifig_data['name'] = self.decode_and_normalize(minifig_data['name'])
		###################
		#print(minifig_data)
		if verbose is True:
			print('MINIFIG {0} -- {1} ({2}) -- from BrickLink website'.format(
				minifigID, minifig_data.get('name')[:60], minifig_data.get('year_released'),))
		self.bricklink_minifig_cache[str(minifigID)] = minifig_data
		return minifig_data

	#============================
	#============================
	def getPartData(self, partID, verbose=True):
		""" get individual part data from BrickLink using an string minifigID """
		###################
		part_data = self.bricklink_part_cache.get(partID)
		if self._check_if_data_valid(part_data) is True:
			if verbose is True:
				print('PART {0} -- {1} ({2}) -- from cache'.format(
					part_data.get('no'), part_data.get('name'), part_data.get('year_released'),))
			return part_data
		###################
		part_data = self._bricklink_get('items/part/{0}'.format(partID))
		###################
		#print(part_data)
		if verbose is True:
			print('PART {0} -- {1} ({2}) -- from BrickLink website'.format(
				partID, part_data.get('name'),part_data.get('year_released'),))
		part_data['name'] = self.decode_and_normalize(part_data['name'])
		self.bricklink_part_cache[partID] = part_data
		return part_data

	#============================
	#============================
	def getWeightedAveragePrice(self, price_data, new_or_used='N', verbose=True):
		if new_or_used == 'U':
			prefix = 'used_'
		else:
			prefix = 'new_'

		mean_price = 0.15
		mean_qty = 100

		sale_mp = price_data.get(prefix+'median_sale_price')
		sale_ap = price_data.get(prefix+'avg_sale_price')
		sale_p = (sale_mp + sale_ap)/200.
		sale_q = price_data.get(prefix+'sale_qty')

		list_p = price_data.get(prefix+'median_list_price')/100.
		list_q = price_data.get(prefix+'list_qty')

		if sale_q <= 2 and list_q <= 200:
			return None

		weighted_sale_price = sale_q/(sale_q + mean_qty) * sale_p + mean_qty/(sale_q + mean_qty) * mean_price
		weighted_list_price = list_q/(list_q + mean_qty) * list_p + mean_qty/(list_q + mean_qty) * mean_price

		weighted_price = ( (weighted_sale_price * sale_q + weighted_list_price * math.sqrt(list_q) ) /
			( sale_q + math.sqrt(list_q) ))

		print('WEIGHTED PRICE ID ${0:.2f} -- {1}'.format(weighted_price, new_or_used))
		return weighted_price

	#============================
	#============================
	def elementIDtoPartIDandColorID(self, elementID, verbose=True):
		""" get part ID and color ID from BrickLink using a elementID number"""
		###################
		elementID = int(elementID)
		###################
		###################
		map_list = self.bricklink_element_id_map_cache.get(elementID)
		if map_list is not None and isinstance(map_list, list) and len(map_list) == 2:
			partID, colorID = map_list
			if verbose is True:
				print('ELEMENT ID {0} -- part {1} color {2} -- from cache'.format(elementID, partID, colorID))
			return [partID, colorID]
		try:
			map_data = self._bricklink_get('item_mapping/{0}'.format(elementID))
		except LookupError:
			print("UNKNOWN Element ID")
			return None
		#print(map_data)
		partID = str(map_data[0]['item']['no'])
		colorID = int(map_data[0]['color_id'])
		#sys.exit(1)
		###################
		#print(part_data)
		if verbose is True:
			print('ELEMENT ID {0} -- part {1} color {2} -- from BrickLink website'.format(
				elementID, partID, colorID))
		self.bricklink_element_id_map_cache[elementID] = [partID, colorID]
		key_str = "{0},{1}".format(partID, colorID)
		self.bricklink_element_id_map_cache[key_str] = elementID
		return [partID, colorID]

	#============================
	#============================
	# Helper function to check if the image exists at a given URL
	def image_exists(self, url, verbose=True):
		if self.image_url_checks.get(url, None) is not None:
			return self.image_url_checks[url]
		if verbose:
			print(f"check {url}")
		self.image_checks += 1
		if self.image_checks % 20 == 0:
			self.save_cache("bricklink_element_id_map_cache")
			print(self.status_counts)
		# Skip throttle for lego.com (large Akamai CDN); be polite to smaller CDNs.
		if 'www.lego.com' not in url:
			time.sleep(random.random())
		user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
		headers = {
			'User-Agent': user_agent,
			'Accept': 'image/webp,*/*',
			'Accept-Encoding': 'gzip, deflate, br',
			'Accept-Language': 'en-US,en;q=0.5',
		}
		try:
			response = requests.get(url, timeout=2, headers=headers)
		except requests.exceptions.ReadTimeout:
			if verbose:
				print("TIMEOUT")
			self.status_counts['timeout'] += 1
			return False
		if response.status_code == 200:
			if verbose:
				print("success")
			self.image_url_checks[url] = True
			self.status_counts['success'] += 1
			return True
		else:
			#print(response)
			#print(response.status_code)
			if verbose:
				print("FAIL")
			self.status_counts['fail'] += 1
			self.image_url_checks[url] = False
			return False

	#============================
	#============================
	# Helper function to check if the image exists at a given URL
	def elementID_image_exists(self, elementID):
		url = "https://www.lego.com/cdn/product-assets/"
		url += f"element.img.lod5photo.192x192/{elementID}.jpg"
		return self.image_exists(url)

	#============================
	#============================
	def partIDandColorIDtoElementID(self, partID, colorID, verbose=True):
		""" get part ID and color ID from BrickLink using a elementID number"""
		###################
		#partID = int(partID)
		colorID = int(colorID)
		###################
		###################
		key_str = "{0},{1}".format(partID, colorID)
		elementID = self.bricklink_element_id_map_cache.get(key_str)
		# Check if the elementID is already cached
		if elementID is not None:
			# Print the cached elementID if verbose is enabled
			if verbose:
				print('ELEMENT ID {0} -- part {1} color {2} -- from cache'.format(elementID, partID, colorID))
			# With a 99% chance, return the cached elementID without checking the image
			if random.random() > 0.01:
				return elementID
			# For the remaining 1%, return the cached elementID only if its associated image exists
			elif self.elementID_image_exists(elementID):
				return elementID
			#else find a new elementID below
		try:
			map_data = self._bricklink_get('item_mapping/PART/{0}?color_id={1}'.format(partID, colorID))
		except LookupError:
			print("UNKNOWN partID, colorID")
			return None
		element_id_list = []
		for data in reversed(map_data):
			elementID = int(data['element_id'])
			element_id_list.append(elementID)
		element_id_list.sort()

		print(f"Found {len(map_data)} element IDs for part {partID} and color {colorID}")
		# Loop through all elementIDs in the map_data
		for elementID in reversed(element_id_list):
			if self.elementID_image_exists(elementID):
				# Check if the image exists at the generated URL
				if verbose:
					print('ELEMENT ID {0} -- part {1} color {2} -- from BrickLink website'.format(
						elementID, partID, colorID))
				self.bricklink_element_id_map_cache[elementID] = [partID, colorID]
				key_str = "{0},{1}".format(partID, colorID)
				self.bricklink_element_id_map_cache[key_str] = elementID
				return str(elementID)
		# Return None if the loop completes without finding any images
		print("FAILED to find Element ID with a Lego CDN image")
		elementID = element_id_list[-1]
		if verbose:
			print('ELEMENT ID {0} -- part {1} color {2} -- from BrickLink website'.format(
					elementID, partID, colorID))
		return str(elementID)

if __name__ == "__main__":
	BL = BrickLink()
	price_data = BL.getSetPriceData(75151)
	import pprint
	pprint.pprint(price_data)
	BL.close()
