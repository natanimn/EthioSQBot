import time
from datetime import datetime
import re


class Convertor:
    def __init__(self, default: str):
        self.default = default

    @property
    def convert(self):
        year = datetime.today().year
        month = datetime.today().month
        day = datetime.today().day
        hour = datetime.today().hour
        minute = datetime.today().minute
        second = datetime.today().second
        
        regex = re.search('(^\d+)\s+(year|month|hour|day|min|sec)s?', self.default)
        if regex:
            value, postfix = regex.groups()
            value = int(value)
            if postfix == 'sec':
                second += value
                self.second = second
            elif postfix == 'min':
                minute += value
                self.second = value * 60
            elif postfix == 'hour':
                hour += value
                self.second = 3600 * value
            elif postfix == 'day':
                day += value
                self.second = 3600 * 24 * value
            elif postfix == 'month':
                month += value
                self.second = 3600 * 24 * 30 * value
            else:
                year += value
                self.second = 3600 * 24 * 30 * 12 * value
            
            if second > 60:
                minute += second//60
                while second > 60:second -= 60
            if minute > 60:
                hour += minute//60
                while minute > 60:minute -= 60
            if hour >= 24:
                day += hour//24
                while hour >= 24: hour -= 24

            if day >= 30:
                month += day//30
                while day > 30:day -= 30
            if month > 12:
                year += month//12
                while month > 12: month -= 12

        new = datetime.today().replace(year=year, month=month, day=day, hour=hour, minute=minute, second=second)
        return new.ctime()


def time_parse(time_) -> str:
    time_ = time_ or 0
    tp = round(time.time() - time_)
    year = round(tp/60/60/24/7/30/365)
    month = round(tp/60/60/24/7/30)
    week = round(tp/60/60/24/7)
    day = round(tp/60/60/24)
    hour = round(tp/60/60)
    minute = round(tp/60)
    second = tp
    if year >= 1:
        return str(year)+" years ago" if year > 1 else str(year) + " year ago"
    elif month >= 1:
        return str(month)+" months ago" if month > 1 else str(month) + " month ago"
    elif week >= 1:
        return str(week)+" weeks ago" if week > 1 else str(week) + " week ago"
    elif day >= 1:
        return str(day)+" days ago" if day > 1 else str(day) + " day ago"
    elif hour >= 1:
        return str(hour)+" hours ago" if hour > 1 else str(hour) + " hour ago"
    elif minute >= 1:
        return str(minute)+" minutes ago" if minute > 1 else str(minute) + " minute ago"
    elif second >= 2:
        return str(second)+" seconds ago" if second > 1 else str(second) + " second ago"
    else:
        return 'Just now'