# This package will contain the spiders of your Scrapy project
#
# Please refer to the documentation for information on how to create and manage
# your spiders.

def get_and_norm(selector):
    return selector.extract_first().strip().replace(u'\xa0', u'')

