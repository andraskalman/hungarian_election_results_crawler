# -*- coding: utf-8 -*-
import scrapy
import unicodedata
import copy
from urllib.parse import urljoin
from ..items import *
from . import get_and_norm


class District2014Spider(scrapy.Spider):
    name = 'districts_2014'
    allowed_domains = ['valasztas.hu']
    start_urls = ['http://valtor.valasztas.hu/valtort/jsp/mkiv.jsp?EA=33&URL=7']

    def __init__(self, county_filter=None, district_num_filter=None, *args, **kwargs):
        super(District2014Spider, self).__init__(*args, **kwargs)
        self.district_num_filter = district_num_filter
        self.county_filter = county_filter

    def parse(self, response):
        rows = response.xpath('body/div/center/table[1]/tr')
        for index, row in enumerate(rows):

            # first row has only headers
            if index > 0:

                dr = DistrictResult(
                    county=row.xpath('td[1]/a/text()').extract_first().strip()
                )

                if self.county_filter is None or self.county_filter.lower() == dr['county'].lower():
                    request = scrapy.Request(urljoin(response.url,
                                    unicodedata.normalize('NFKD', row.xpath('td[1]/a/@href').extract_first())), callback=self.parse_district_list_page)
                    request.meta['district_result'] = copy.deepcopy(dr)
                    yield request
                else:
                    continue

    def parse_district_list_page(self, response):
        self.logger.debug("processing district list page: %s" % response.url)
        dr = response.meta['district_result']

        rows = response.xpath('body/div/center/table[1]/tr')
        for index, row in enumerate(rows):

            # first row has only headers
            if index > 0:
                dr['num'] = row.xpath('td[1]/font/a/text()').extract_first().strip()
                dr['url'] = urljoin(response.url, unicodedata.normalize('NFKD', row.xpath('td[1]/font/a/@href').extract_first()))
                dr['location'] = row.xpath('td[2]/font/text()').extract_first().strip()
                dr['id'] = "%s-%s" % (dr['county'], dr['num'])

                if self.district_num_filter is None or self.district_num_filter == dr['num']:
                    request = scrapy.Request(dr['url'], callback=self.parse_district_page)
                    request.meta['district_result'] = copy.deepcopy(dr)
                    yield request
                else:
                    continue

    def parse_district_page(self, response):
        self.logger.debug("processing district page: %s" % response.url)
        dr = response.meta['district_result']

        dr['register_stats'] = RegisterStats()
        dr['participant_stats'] = ParticipantStats()
        dr['result_stats'] = ResultStats()

        register_stat_row = response.xpath('body/div/center/table[1]/tr[3]')
        dr['register_stats']['local_voters'] = get_and_norm(register_stat_row.xpath('td[1]/text()'))  # AE
        dr['register_stats']['cross_registered_voters'] = get_and_norm(register_stat_row.xpath('td[2]/text()'))  # BE
        dr['register_stats']['consulate_voters'] = get_and_norm(register_stat_row.xpath('td[3]/text()'))  # CE
        dr['register_stats']['total'] = get_and_norm(register_stat_row.xpath('td[4]/text()'))  # DE

        participant_stat_row = response.xpath('body/div/center/table[2]/tr[3]')
        dr['participant_stats']['locals'] = get_and_norm(participant_stat_row.xpath('td[1]/text()'))  # FE
        dr['participant_stats']['received_envelopes'] = get_and_norm(participant_stat_row.xpath('td[2]/text()'))  # IE
        dr['participant_stats']['total'] = get_and_norm(participant_stat_row.xpath('td[3]/text()'))  # JE

        result_stat_row = response.xpath('body/div/center/table[3]/tr[3]')
        dr['result_stats']['pages_in_urn_and_envelopes'] = get_and_norm(result_stat_row.xpath('td[1]/text()'))  # KE
        dr['result_stats']['invalid_pages'] = get_and_norm(result_stat_row.xpath('td[2]/text()'))  # ME
        dr['result_stats']['valid_pages'] = get_and_norm(result_stat_row.xpath('td[3]/text()'))  # NE

        dr['candidate_results'] = []

        candidate_rows = response.xpath('body/div/center/table[4]/tr')

        for index, row in enumerate(candidate_rows):

            # first row has only headers
            if index > 0:
                dr['candidate_results'].append(
                    CandidateResult(
                        id=row.xpath('td[1]/text()').extract_first().strip(),
                        candidate_name=row.xpath('td[2]/text()').extract_first().strip(),
                        candidate_party=row.xpath('td[3]/text()').extract_first().strip(),
                        num_of_valid_votes=get_and_norm(row.xpath('td[4]/text()')),
                        rate_of_valid_votes=row.xpath('td[5]/text()').extract_first().strip(),
                    )
                )

        yield dr
