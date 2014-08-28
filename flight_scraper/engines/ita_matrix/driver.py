import json
import logging
import datetime
import re
import requests
from abc import abstractmethod
from flight_scraper.solution_model import ItaSolution, Flight, Itinerary, CalendarSolution, TripMinimumPrice

logging.basicConfig(level=logging.INFO)

class AbstractItaMatrixDriver(object):
    
    _logger = logging.getLogger(__name__)
    engine = "ITA Matrix"
    _base_url = "http://matrix.itasoftware.com"
    _request_uri = "/xhr/shop/search?"
    _http_header = {
        'Host': 'matrix.itasoftware.com',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cache-Control': 'no-cache',
        'Content-Length': '0'
    }
    
    def __init__(self, origin, destination, depart_date, return_date, max_stops, airlines):
        self.origin = origin
        self.destination = destination
        self.depart_date = depart_date
        self.return_date = return_date
        self.max_stops = max_stops
        self.airlines = airlines
    
    @property
    def origin(self):
        return self._json_request['slices'][0]['origins'][0]

    @origin.setter
    def origin(self, origin):
        self._json_request['slices'][0]['origins'][0] = origin
        self._json_request['slices'][1]['destinations'][0] = origin

    @property
    def destination(self):
        return self._json_request['slices'][0]['destinations'][0]

    @destination.setter
    def destination(self, destination):
        self._json_request['slices'][0]['destinations'][0] = destination
        self._json_request['slices'][1]['origins'][0] = destination
        
    @property
    def max_stops(self):
        return self._json_request['maxStopCount']
    
    @max_stops.setter
    def max_stops(self, stops):
        if stops is None:
            stops = 2
        self._json_request['maxStopCount'] =   stops
        
    @property
    def airlines(self):
        return self._json_request['slices'][0]['routeLanguage']
    
    @airlines.setter
    def airlines(self, airlines):
        if airlines is not None:
            self._json_request['slices'][0]['routeLanguage'] = airlines
            self._json_request['slices'][1]['routeLanguage'] = airlines
            
    def build_request_url(self):
        data = self._base_request + json.dumps(self._json_request)
        request_url = self._base_url + self._request_uri + data
        print 'Request URl: %s' % (request_url)
        return request_url

    def build_solutions(self):    
        request_url = self.build_request_url()

        self._logger.info('Making request to ITA Matrix: %s', (request_url))
        response = requests.post(request_url, headers=self._http_header)
        response_json = json.loads(response.text[4:])

        print response_json
        self._logger.info('Creating objects to insert to database')
        return self._parse_solutions(response_json)
        
    @abstractmethod
    def _parse_solutions(self):
        raise NotImplementedError('Subclasses must implement _parse_solutions')  
    
class Slice(object):
    def __init__(self, origin, destination, depart_date, airlines=None):
        self._json_request = json.loads('{"origins":["PDX"],"originPreferCity":false,"commandLine":"airlines AA DL AS UA",\
                               "destinations":["SEA"],"destinationPreferCity":false,"date":"2013-06-07","isArrivalDate":false,\
                                "dateModifier":{"minus":0,"plus":0}}')
        self.origin = origin
        self.destination = destination
        self.depart_date = depart_date
        self._airlines = None
        self.airlines = airlines

    @property
    def origin(self):
        return self._json_request['origins'][0]

    @origin.setter
    def origin(self, origin):
        self._json_request['origins'][0] = origin
        
    @property
    def destination(self):
        return self._json_request['destinations'][0]

    @destination.setter
    def destination(self, destination):
        self._json_request['destinations'][0] = destination
            
    @property
    def depart_date(self):
        return datetime.datetime.strptime(self._json_request['date'], "%Y-%m-%d")

    @depart_date.setter
    def depart_date(self, depart_date):
        self._json_request['date'] = depart_date.strftime('%Y-%m-%d')
    
    @property
    def airlines(self):
        return ' '.join(self._airlines)
        
        # return self._airlines
        # return self._json_request['commandLine']
    
    @airlines.setter
    def airlines(self, airlines):
        if airlines is None:
            self._airlines = list()
            return
        
        self._airlines = [x.strip() for x in re.split('[ ,]', airlines) if x.strip()]
        
        if airlines is None:
            self._json_request['commandLine'] = ""
        else:
            self._json_request['commandLine'] = "airlines %s" % airlines
            
    def _build_command_line(self):
        route_lang = ""
        if (len(self._airlines) > 0):
            route_lang = "%s airlines %s" % (route_lang, self.airlines)
            
        self._json_request['commandLine'] = route_lang
        
        
class ItaMatrixDriverMulti(AbstractItaMatrixDriver):
    _base_request = "name=specificDates&summarizers=carrierStopMatrix"\
                    "%2CcurrencyNotice%2CsolutionList%2CitineraryPriceSlider%2C"\
                    "itineraryCarrierList%2CitineraryDepartureTimeRanges%2CitineraryArrivalTimeRanges"\
                    "%2CdurationSliderItinerary%2CitineraryOrigins%2CitineraryDestinations%2C"\
                    "itineraryStopCountList%2CwarningsItinerary&format=JSON&inputs="
                    
    _json_request = json.loads('{"slices":[],"pax":{"adults":1},"cabin":"COACH","maxStopCount":0,\
                                "changeOfAirport":false,"checkAvailability":true,"page":{"size":2000},"sorts":"default"}')
    def __init__(self, max_stops):
        self.slices = list()
        self.max_stops = max_stops
    
    def add_slice(self, slice):
        self.slices.append(slice)
        
    def add_slice_params(self, origin, destination, depart_date, airlines=None):
        self.slices.append(Slice(origin, destination, depart_date, airlines))
        
    # TODO: These isn't needed anymore. It's just a hack to get the _parse_solutions method working.
    @property
    def depart_date(self):
        return datetime.datetime.strptime(self._json_request['slices'][0]['date'], "%Y-%m-%d")
    # TODO: These isn't needed anymore. It's just a hack to get the _parse_solutions method working.
    @property
    def return_date(self):
        return datetime.datetime.strptime(self._json_request['slices'][-1]['date'], "%Y-%m-%d")
    
    @property
    def max_stops(self):
        return self._json_request['maxStopCount']
    
    @max_stops.setter
    def max_stops(self, stops):
        if stops is None:
            stops = 2
        self._json_request['maxStopCount'] = stops
    
    def combine_slices(self):
        self._json_request['slices'] = []
        for slice in self.slices:
            slice._build_command_line()
            self._json_request['slices'].append(slice._json_request)
        
    def build_solutions(self):
        self.combine_slices()
        super(ItaMatrixDriverMulti, self).build_solutions()
           
    def _parse_solutions(self, response_json):
        """
            Builds search solution. Adds to MongoDB and returns the Solution object.
        """
        solution = ItaSolution(engine=self.engine, origin=self.slices[0].origin, destination=self.slices[0].destination, depart_date=self.depart_date, return_date=self.return_date)
        solution.min_price = response_json['result']['solutionList']['minPrice']
 
        for sol in response_json['result']['solutionList']['solutions']:
            flight_list = list()
            for slice in sol['itinerary']['slices']:
                flight_airline = slice['flights'][0][:2]
                flight_number = int(slice['flights'][0][2:])
                dep_time = datetime.datetime.strptime(slice['departure'][:-6], "%Y-%m-%dT%H:%M")
                arr_time = datetime.datetime.strptime(slice['arrival'][:-6], "%Y-%m-%dT%H:%M")
                arr_city = slice['destination']['code']
                dep_city = slice['origin']['code']
     
                slice_flight = Flight(airline=flight_airline, fno=flight_number, dep_city=dep_city, arr_city=arr_city, dep_time=dep_time, arr_time=arr_time)
                #slice_flight.save()
                
                flight_list.append(slice_flight)
 
            price = sol['displayTotal']
            itinerary = Itinerary(flights=flight_list, price=price)
            solution.itineraries.append(itinerary)
 
        solution.save()
 
        return solution
    
class ItaMatrixDriver(AbstractItaMatrixDriver):

    _base_request = "name=specificDates&summarizers=carrierStopMatrix"\
                    "%2CcurrencyNotice%2CsolutionList%2CitineraryPriceSlider%2C"\
                    "itineraryCarrierList%2CitineraryDepartureTimeRanges%2CitineraryArrivalTimeRanges"\
                    "%2CdurationSliderItinerary%2CitineraryOrigins%2CitineraryDestinations%2C"\
                    "itineraryStopCountList%2CwarningsItinerary&format=JSON&inputs="

    _json_request = json.loads('{"slices":[{"origins":["PDX"],"originPreferCity":false,"commandLine":"airlines AA DL AS UA",\
                               "destinations":["SEA"],"destinationPreferCity":false,"date":"2013-06-07","isArrivalDate":false,\
                                "dateModifier":{"minus":0,"plus":0}},{"destinations":["PDX"],"destinationPreferCity":false,\
                                "origins":["SEA"],"originPreferCity":false,"commandLine":"airlines AA DL AS","date":"2013-06-09",\
                                "isArrivalDate":false,"dateModifier":{"minus":0,"plus":0}}],"pax":{"adults":1},"cabin":"COACH","maxStopCount":0,\
                                "changeOfAirport":false,"checkAvailability":true,"page":{"size":2000},"sorts":"default"}')

    def __init__(self, origin, destination, depart_date, return_date, max_stops=None, airlines=None):
        super(ItaMatrixDriver, self).__init__(origin, destination, depart_date, return_date, max_stops, airlines)

    @property
    def depart_date(self):
        return datetime.datetime.strptime(self._json_request['slices'][0]['date'], "%Y-%m-%d")

    @depart_date.setter
    def depart_date(self, depart_date):
        self._json_request['slices'][0]['date'] = depart_date.strftime('%Y-%m-%d')

    @property
    def return_date(self):
        return datetime.datetime.strptime(self._json_request['slices'][1]['date'], "%Y-%m-%d")

    @return_date.setter
    def return_date(self, return_date):
        self._json_request['slices'][1]['date'] = return_date.strftime('%Y-%m-%d')
        
    @property
    def airlines(self):
        return self._json_request['slices'][0]['commandLine']
    
    @airlines.setter
    def airlines(self, airlines):
        if airlines is None:
            self._json_request['commandLine'] = ""
        else:
            self._json_request['slices'][0]['commandLine'] = "airlines %s" % airlines
            self._json_request['slices'][1]['commandLine'] = "airlines %s" % airlines

    def _parse_solutions(self, response_json):
        """
            Builds search solution. Adds to MongoDB and returns the Solution object.
        """
        solution = ItaSolution(engine=self.engine, origin=self.origin, destination=self.destination, depart_date=self.depart_date, return_date=self.return_date)
        solution.min_price = response_json['result']['solutionList']['minPrice']
 
        for sol in response_json['result']['solutionList']['solutions']:
            origin_flight_airline = sol['itinerary']['slices'][0]['flights'][0][:2]
            origin_flight_number = int(sol['itinerary']['slices'][0]['flights'][0][2:])
            dep_time = datetime.datetime.strptime(sol['itinerary']['slices'][0]['departure'][:-6], "%Y-%m-%dT%H:%M")
            arr_time = datetime.datetime.strptime(sol['itinerary']['slices'][0]['arrival'][:-6], "%Y-%m-%dT%H:%M")
            arr_city = sol['itinerary']['slices'][0]['destination']['code']
            dep_city = sol['itinerary']['slices'][0]['origin']['code']
 
            origin_flight = Flight(airline=origin_flight_airline, fno=origin_flight_number, dep_city=dep_city, arr_city=arr_city, dep_time=dep_time, arr_time=arr_time)
            #origin_flight.save()
 
            return_flight_airline = sol['itinerary']['slices'][1]['flights'][0][:2]
            return_flight_number = int(sol['itinerary']['slices'][1]['flights'][0][2:])
            dep_time = datetime.datetime.strptime(sol['itinerary']['slices'][1]['departure'][:-6], "%Y-%m-%dT%H:%M")
            arr_time = datetime.datetime.strptime(sol['itinerary']['slices'][1]['arrival'][:-6], "%Y-%m-%dT%H:%M")
            arr_city = sol['itinerary']['slices'][1]['destination']['code']
            dep_city = sol['itinerary']['slices'][1]['origin']['code']
 
            return_flight = Flight(airline=return_flight_airline, fno=return_flight_number, dep_city=dep_city, arr_city=arr_city, dep_time=dep_time, arr_time=arr_time)
            #return_flight.save()
 
            flight_list = [origin_flight, return_flight]
            price = sol['displayTotal']
            itinerary = Itinerary(flights=flight_list, price=price)
            solution.itineraries.append(itinerary)
 
        solution.save()
 
        return solution

class CalendarItaMatrixDriver(AbstractItaMatrixDriver):
    
    _base_request = "name=calendar&summarizers=currencyNotice%2CovernightFlightsCalendar"\
                    "%2CitineraryStopCountList%2CitineraryCarrierList%2Ccalendar&format=JSON&inputs="
    
    _json_request = json.loads('{"slices":[{"origins":["BWI"],"originPreferCity":false,"routeLanguage":"C:DL","destinations":["MSP"],\
                               "destinationPreferCity":false},{"destinations":["BWI"],"destinationPreferCity":false,"origins":["MSP"],\
                               "originPreferCity":false,"routeLanguage":"C:DL"}],"startDate":"2014-07-01","layover":{"max":5,"min":4},\
                               "pax":{"adults":1},"cabin":"COACH","maxStopCount":0,"changeOfAirport":false,"checkAvailability":true,\
                               "firstDayOfWeek":"SUNDAY","endDate":"2014-08-01"}')
    
    def __init__(self, origin, destination, depart_date, return_date, day_range, max_stops=None, airlines=None):
        super(CalendarItaMatrixDriver, self).__init__(origin, destination, depart_date, return_date, max_stops, airlines)
        self.day_range  = day_range
    
    @property
    def depart_date(self):
        return datetime.datetime.strptime(self._json_request['startDate'], "%Y-%m-%d")

    @depart_date.setter
    def depart_date(self, depart_date):
        self._json_request['startDate'] = depart_date.strftime('%Y-%m-%d')

    @property
    def return_date(self):
        return datetime.datetime.strptime(self._json_request['endDate'], "%Y-%m-%d")

    @return_date.setter
    def return_date(self, return_date):
        self._json_request['endDate'] = return_date.strftime('%Y-%m-%d')
        
    @property
    def day_range(self):
        return self._json_request['layover']
    
    @day_range.setter
    def day_range(self, days):
        self._json_request['layover'] = {'min': days[0], 'max': days[1]}
        
    def _parse_solutions(self, response_json):         
        self._logger.info('Creating objects to insert to database')
        solution = CalendarSolution(engine=self.engine, origin=self.origin, destination=self.destination, 
                                    depart_date=self.depart_date, return_date=self.return_date)
 
        prices = []
        for month in response_json['result']['calendar']['months']:
            for week in month['weeks']:
                for day in week['days']:
                    if day['solutionCount'] == 0:
                        continue
                    for sol in day['tripDuration']['options']:
                        
                        dep_time = datetime.datetime.strptime(sol['solution']['slices'][0]['departure'][:10], "%Y-%m-%d").date()
                        arr_time = datetime.datetime.strptime(sol['solution']['slices'][1]['departure'][:10], "%Y-%m-%d").date()
                        price = sol['minPrice']
                        trip  = TripMinimumPrice(dep_city=self.origin, arr_city=self.destination, dep_time=dep_time, arr_time=arr_time, price=price)
                        prices.append(float(price.replace('USD', ''))) #FIXME: Can't assume USD
                        
                        solution.trip_prices.append(trip)
 
        solution.min_price = str(min(prices))
        solution.save()
        
        return solution

class ViewItineraryDriver(object):
    _logger = logging.getLogger(__name__)
    engine = "ITA Matrix"
    _base_url = "http://matrix.itasoftware.com"
    _request_uri = "/xhr/shop/search?"
    _http_header = {
        'Host': 'matrix.itasoftware.com',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cache-Control': 'no-cache',
        'Content-Length': '0'
    }
    
    def __init__(self, itinerary):
        pass