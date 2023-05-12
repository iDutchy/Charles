import builtins
import os
import json
import contextvars
from .cache import CacheManager as cm

DEFAULT_LOCALE = "en"
LOCALE_DIR = "db/languages"

locales = os.listdir(LOCALE_DIR)

def get_string(string):
    lang = locale.get()
    if lang == DEFAULT_LOCALE:
        return string
    try:
        text = cm.get('i18n', lang, string)
    except:
        return string
    else:
        return text

# def load_locale_cache():
#     for folder in locales:
#         strings = {}
#         for file in os.listdir(LOCALE_DIR + "/" + folder):
#             with open(f"{LOCALE_DIR}/{folder}/{file}") as f:
#                 data = json.load(f)
#             strings.update(data)

#         cm.update('i18n', folder, strings)

locale = contextvars.ContextVar('i18n')
builtins._ = get_string

def set_locale(lang=DEFAULT_LOCALE):
    locale.set(lang)

set_locale()