# -*- coding: utf-8 -*-
import scrapy
import unicodedata
from urllib.parse import urljoin
from ..items import *
from . import get_and_norm


class OevkSpider(scrapy.Spider):
    name = 'oevk'
    allowed_domains = ['valasztas.hu']
    start_urls = ['http://valasztas.hu/dyn/pv18/szavossz/hu/oevker.html']

    def __init__(self, oevk_id=None, *args, **kwargs):
        super(OevkSpider, self).__init__(*args, **kwargs)
        self.oevk_id = oevk_id

    def parse(self, response):
        rows = response.xpath('body/div/center/table[2]/tr')
        for index, row in enumerate(rows):

            # first row has only headers
            if index > 0:
                oevk_result = OEVKResult(
                    county=row.xpath('td[1]/text()').extract_first().strip(),
                    oevk_num=row.xpath('td[2]/a/text()').extract_first().strip(),
                    oevk_url=urljoin(response.url,
                                    unicodedata.normalize('NFKD', row.xpath('td[2]/a/@href').extract_first())),
                    location=row.xpath('td[3]/text()').extract_first().strip(),
                    voted_candidate=row.xpath('td[4]/a/text()').extract_first().strip(),
                    voted_candidate_party=row.xpath('td[5]/text()').extract_first().strip(),
                    progress_of_processing=row.xpath('td[6]/text()').extract_first().strip(),
                )

                oevk_result['oevk_id'] =  "%s-%s" % (oevk_result['county'], oevk_result['oevk_num'])
                if self.oevk_id is None or self.oevk_id == oevk_result['oevk_id']:
                    request = scrapy.Request(oevk_result['oevk_url'], callback=self.parse_oevk_result_page)
                    request.meta['oevk_result'] = oevk_result
                    yield request
                else:
                    continue

    def parse_oevk_result_page(self, response):
        self.logger.debug("processing oevk result page: %s" % response.url)

        oevk_result = response.meta['oevk_result']

        oevk_result['register_stats'] = RegisterStats()
        oevk_result['participant_stats'] = ParticipantStats()
        oevk_result['result_stats'] = ResultStats()

        t1_row = response.xpath('body/div/center/table[1]/tr[1]')
        oevk_result['page_generated_at'] = t1_row.xpath('td[1]/text()').extract_first().strip()

        t2_row = response.xpath('body/div/center/table[2]/tr[3]')
        oevk_result['register_stats']['local_voters'] = get_and_norm(t2_row.xpath('td[1]/text()'))  # AE
        oevk_result['register_stats']['cross_registered_voters'] = get_and_norm(t2_row.xpath('td[2]/text()'))  # BE
        oevk_result['register_stats']['consulate_voters'] = get_and_norm(t2_row.xpath('td[3]/text()'))  # CE
        oevk_result['register_stats']['total'] = get_and_norm(t2_row.xpath('td[4]/text()'))  # EE

        t3_row = response.xpath('body/div/center/table[3]/tr[3]')
        oevk_result['participant_stats']['locals'] = get_and_norm(t3_row.xpath('td[1]/text()'))  # FE
        oevk_result['participant_stats']['received_envelopes'] = get_and_norm(t3_row.xpath('td[2]/text()'))  # IE
        oevk_result['participant_stats']['total'] = get_and_norm(t3_row.xpath('td[3]/br/preceding-sibling::text()'))  # JE
        oevk_result['participant_stats']['total_rate'] = t3_row.xpath('td[3]/br/following-sibling::text()').extract_first().strip()  # JE

        t4_rows = response.xpath('body/div/center/table[4]/tr')
        oevk_result['result_stats']['pages_in_urn_and_envelopes'] = get_and_norm(t4_rows[2].xpath('td[1]/text()'))  # KE
        oevk_result['result_stats']['invalid_pages'] = get_and_norm(t4_rows[2].xpath('td[2]/text()'))  # ME
        oevk_result['result_stats']['valid_pages'] = get_and_norm(t4_rows[2].xpath('td[3]/text()'))  # NE

        oevk_result['result_stats']['invalid_page_rate'] = t4_rows[3].xpath('td[1]/text()').extract_first().strip()  # ME
        oevk_result['result_stats']['valid_page_rate'] = t4_rows[3].xpath('td[2]/text()').extract_first().strip()  # NE

        oevk_result['candidate_results'] = []

        t5_rows = response.xpath('body/div/center/table[5]/tr')

        for index, row in enumerate(t5_rows):

            # first row has only headers
            if index > 0:
                oevk_result['candidate_results'].append(
                    CandidateResult(
                        id=row.xpath('td[1]/text()').extract_first().strip(),
                        candidate_name=row.xpath('td[2]/a/text()').extract_first().strip(),
                        candidate_party=row.xpath('td[3]/text()').extract_first().strip(),
                        num_of_valid_votes=get_and_norm(row.xpath('td[4]/text()')),
                        rate_of_valid_votes=row.xpath('td[5]/text()').extract_first().strip(),
                    )
                )

        yield oevk_result
