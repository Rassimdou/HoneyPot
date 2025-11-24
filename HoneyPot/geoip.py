from geoip2.database import Reader
import os 


class GeoIP:
    def __init__(self):
        self.city_db_path ="geoip/GeoLite-City.mmdb"
        self.asn_db_path = "geoip/GeoLite2-ASN.mmdb"

        self.city_reader = None
        self.asn_reader = None
        self.load_databases()

    def load_database(self):
        if os.path.exists(self.city_db_path):
            self.city_reader = Reader(self.city_db_path)
        else: 
            print("[GeoIP] WARNING: City database missing.")

        if os.path.exists(self.asn_db_path):
            self.adn_reader = Render(self.asn_db_path)
        else:
               print("[GeoIP] WARNING: ASN database missing.")

    def lookup(self, ip):
        data ={"country":"Unknown", "city":"Unknown", "asn": None, "org": None}

        try:
            if self.city_reader:
                resp = self.city_reader.city(ip)
                data["city"] = resp.city.name or "Unknown"
                data["country"] = resp.country.name or "Unknown"
        except:
            pass

        try:
            if self.asn_reader:
                resp = self.asn_reader(ip)
                data["asn"] = resp.automous_system_number
                data["org"] = resp.automous_system_organization
        except:
            pass


        return data