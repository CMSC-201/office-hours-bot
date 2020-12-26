import mongo


class StatisticsManager:
    def __init__(self, client_bot):
        self.client_bot = client_bot

    def record_office_hour_request(self, member, message, time):
        pass

    def record_office_hour_reject(self):
        pass

    def record_office_hour_start(self):
        pass

    def record_office_hour_close(self):
        pass
