# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html


class HungarianElectionResults2018Pipeline(object):

    def process_item(self, item, spider):
        # Normalize page generated text
        if 'page_generated_at' in item:
            item['page_generated_at'] = item['page_generated_at'].replace('Frissitve:', '').replace(u'\xa0', u' ').strip()

        if 'oevk' in item:
            item['oevk'] = item['oevk'].replace('.számú egyéni választókerületi szavazás', '').replace(u'\xa0', u' ').strip()

        return item
