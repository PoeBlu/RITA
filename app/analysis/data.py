import json
from elasticsearch import Elasticsearch
from field_names import *

class ESServer(object):
	def __init__(self, server=[]):
		if len(server) > 0:
			self.es = Elasticsearch(server)
		else:
			self.es = Elasticsearch()
		return


	def build_query ( self, constraints, ignore ):
		# Initialize the body of the query
		response = {'query': {'filtered':{'filter':{'bool':{}},'query':{'match_all':{}}}}}
		
		# Add any constraints (match specific terms in search)
		if constraints:
			response['query']['filtered']['filter']['bool']['must'] = []
			for term in constraints:
				response['query']['filtered']['filter']['bool']['must'].append( {'term': term} )

		# Add NOT constraints (match items that do not have specific term)
		if ignore:
			response['query']['filtered']['filter']['bool']['must_not'] = []
			for term in ignore:
				response['query']['filtered']['filter']['bool']['must_not'].append( {'term': term} )
		
		if not ignore and not constraints:
			del response['query']['filtered']['filter']

		# return the query
		return response

	def get_data( self, customer, doc_type, fields, constraints, ignore, scroll_id, scroll_len, sort = ""):
		# If this is the first call, build a query
		if scroll_id == "":
			# make a query
			query = self.build_query( constraints, ignore )

			# Initialize the page (Representation of the query that you want to search)
			page = self.es.search(
				index = customer, 
				doc_type = doc_type,            
				fields = fields,        # Comma-separated list of fields to return as part of a hit 
				scroll = '1m',          # How long the server will keep data for the next scroll event
				#search_type = 'scan',  # Scan search type disables sorting and just scans everything
				size = scroll_len,      # Number of search results to return (default: 10)
				sort = sort,            # Sort the returned information
				body = query)           # Your query (clientip:... = search for specific ip)
		else:
			# Get chunk of data!
			page = self.es.scroll( scroll_id = scroll_id, scroll = '1m')

		# Update the scroll id to keep track of where you are in your results
		scroll_id = page['_scroll_id']

		# Get total # of results on page and set scroll size to that number
		scroll_size = page['hits']['total']

		# Return the current page hits and updated scroll id
		return page['hits']['hits'], scroll_id, scroll_size


	def write_data( self, data, customer, result_type, refresh_index = False):
		# Label results with type of analysis performed
		data['result_type'] = result_type
		
		# Write results to elasticsearch
		try:
			self.es.index(index = customer, doc_type="results", body=data, refresh = refresh_index )
		except:
			print("Error writing to elasticsearch")

	def delete_results(self, customer, result_type):
		fields = []

		# restrict results to specified customer
		constraints = [{'result_type':result_type}]
		
		# anything we want to filter out
		ignore = []

		scroll_id = ""
		scroll_len = 1000

		scrolling = True

		query = ""

		# Get elasticsearch results sorted by duration time, and keep top percentage as set by THRESHOLD
		while scrolling:
			# Retrieve data
			hits, scroll_id, scroll_size = self.get_data(customer,'results',fields, constraints, ignore, scroll_id, scroll_len)

			for h in hits:
				query = query + '{ "delete" : { "_index" : "' + customer + '", "_type" : "' + 'results' + '", "_id" : "' + str(h['_id']) + '" } }\n'
			
			if len(hits) < 1:
				scrolling = False
			
			# print query
			try:
				self.es.bulk(query)
			except:
				continue

