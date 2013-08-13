import time

from scraper_utils import *

import gviz_api

def graph_prices(origin, dest, dept_date, return_date):

	description = {"query_date" : ("string", "Query Date"),
				"min_price" : ("number", "Min Price")}

	dates = list()
	dates.append(dept_date)
	dates.append(return_date)

	result = get_all_prices_for_date_pair(origin, dest, dates)
	data = list()
	for r in result:
		for p in result[r]:
			v = {"query_date" : r, "min_price" : float(p)}
			data.append(v)

	data_table = gviz_api.DataTable(description)
	data_table.LoadData(data)

	return data_table.ToJSon(columns_order=("query_date", "min_price"), order_by="query_date")

