import datetime
from discord import utils

from dateutil.relativedelta import relativedelta


# def conv(t):
#     return t.replace(tzinfo=datetime.timezone.utc)

def date(target):
    return target.strftime("%d %B %Y")

def date_time(target, include_seconds=True):
    if include_seconds is False:
        return target.strftime("%d %B %Y, %H:%M")
    return target.strftime("%d %B %Y, %H:%M:%S")

def time(target, include_seconds=True):
    if include_seconds is False:
        return target.strftime("%H:%M")
    return target.strftime("%H:%M:%S")

def timesince(dt: datetime.datetime, add_suffix=True, add_prefix=True):
    prefix = ''
    suffix = ''
    now = utils.utcnow()
    now.replace(microsecond=0)
    dt.replace(microsecond=0)
    if now < dt:
        delta = relativedelta(dt, now)
        if add_prefix:
            prefix = 'In '
    else:
        delta = relativedelta(now, dt)
        if add_suffix:
            suffix = ' ago'
    output = []
    units = ('year', 'month', 'day', 'hour', 'minute', 'second')
    for unit in units:
        elem = getattr(delta, unit + 's')
        if not elem:
            continue
        if unit == 'day':
            weeks = delta.weeks
            if weeks:
                elem -= weeks * 7
                output.append('{} week{}'.format(weeks, 's' if weeks > 1 else ''))
        output.append('{} {}{}'.format(elem, unit, 's' if elem > 1 else ''))
    output = output[:3]
    return prefix + ', '.join(output) + suffix
