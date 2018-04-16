# -*- coding: utf-8 -*-
import scrapy
from string import ascii_lowercase
import unicodedata
import unidecode
from urllib.parse import urljoin
from ..items import *
import copy


class VotingDistrictSpider(scrapy.Spider):
    name = 'voting_district'
    allowed_domains = ['valasztas.hu']

    start_url_pattern = "http://valasztas.hu/dyn/pv18/szavossz/hu/TK/szkkivtk%s.html"

    def __init__(self, location=None, district_id=None, *args, **kwargs):
        super(VotingDistrictSpider, self).__init__(*args, **kwargs)
        self.location = location
        if location is not None:
            self.start_urls = [ self.start_url_pattern % unidecode.unidecode(location[0]).lower() ]
        else:
            self.start_urls = [self.start_url_pattern % x for x in ascii_lowercase]
        self.district_id = district_id

    def parse(self, response):
        links = response.xpath('body/div/center/table[2]//a')
        for link in links:
            vdr = VotingDistrictResult(
                location = link.xpath('text()').extract_first().strip(),
            )
            if self.location is None or self.location.lower() == vdr['location'].lower():
                request = scrapy.Request(urljoin(response.url,
                                 unicodedata.normalize('NFKD', link.xpath('@href').extract_first())),
                                 callback=self.parse_location_page
                )
                request.meta['voting_district_result'] = vdr
                yield request
            else:
                continue

    def parse_location_page(self, response):
        self.logger.debug("processing location result page: %s" % response.url)

        rows = response.xpath('body/div/center/table[2]/tr')
        for index, row in enumerate(rows):

            # first row has only headers
            if index > 0:
                vdr = copy.deepcopy(response.meta['voting_district_result'])
                vdr['num'] = row.xpath('td[1]/a/text()').extract_first().strip()
                vdr['url'] = urljoin(response.url,
                                    unicodedata.normalize('NFKD', row.xpath('td[1]/a/@href').extract_first()))
                vdr['address'] = row.xpath('td[2]/text()').extract_first().strip()
                vdr['non_locals_allowed'] = len(row.xpath('td[3]/img')) > 0

                if self.district_id is None or self.district_id == vdr['num']:
                    request = scrapy.Request(vdr['url'], callback=self.parse_voting_district_page)
                    request.meta['voting_district_result'] = vdr
                    yield request
                else:
                    continue

    def parse_voting_district_page(self, response):
        self.logger.debug("processing voting district page: %s" % response.url)

        vdr = response.meta['voting_district_result']

        t1_row = response.xpath('body/div/center/table[1]/tr[1]')
        vdr['page_generated_at'] = t1_row.xpath('td[1]/text()').extract_first().strip();
        vdr['page_generated_at'] = t1_row.xpath('td[1]/text()').extract_first().strip()

        vdr['oevk'] = response.xpath('body/div/center/h2[2]/text()').extract_first().strip()

        ir = IndividualResult(
            scanned_report_url = urljoin(response.url,
                                    unicodedata.normalize('NFKD', response.xpath('body/div/center/table[2]/tr[1]/td[3]/a/@href').extract_first()))
        )

        t3_row = response.xpath('body/div/center/table[3]/tr[3]')
        ir['locals_registered'] = t3_row.xpath('td[1]/text()').extract_first().strip().replace(u'\xa0', u'')
        ir['locals_voted'] = t3_row.xpath('td[2]/br/preceding-sibling::text()').extract_first().strip().replace(u'\xa0', u'')
        ir['locals_vote_rate'] = t3_row.xpath('td[2]/br/following-sibling::text()').extract_first().strip()

        if vdr['non_locals_allowed']:
            offset = 1
            t4_row = response.xpath('body/div/center/table[4]/tr[3]')
            ir['non_locals_registered'] = t4_row.xpath('td[1]/text()').extract_first().strip().replace(u'\xa0', u'')
            ir['non_locals_voted'] = t4_row.xpath('td[2]/br/preceding-sibling::text()').extract_first().strip().replace(u'\xa0', u'')
            ir['non_locals_vote_rate'] = t4_row.xpath('td[2]/br/following-sibling::text()').extract_first().strip()

            t5_row = response.xpath('body/div/center/table[5]/tr[3]')
            ir['non_local_envelopes_in_urn'] = t5_row.xpath('td[1]/text()').extract_first().strip().replace(u'\xa0', u'')
            ir['unstamped_pages_in_urn'] = t5_row.xpath('td[2]/text()').extract_first().strip().replace(u'\xa0', u'')
            ir['stamped_pages_in_urn'] = t5_row.xpath('td[3]/text()').extract_first().strip().replace(u'\xa0', u'')
            ir['diff_compared_to_voters'] = t5_row.xpath('td[4]/text()').extract_first().strip().replace(u'\xa0', u'')
            ir['invalid_pages'] = t5_row.xpath('td[5]/text()').extract_first().strip().replace(u'\xa0', u'')
            ir['valid_pages'] = t5_row.xpath('td[6]/text()').extract_first().strip().replace(u'\xa0', u'')

        else:
            offset = 0
            t4_row = response.xpath('body/div/center/table[4]/tr[3]')
            ir['unstamped_pages_in_urn'] = t4_row.xpath('td[1]/text()').extract_first().strip().replace(u'\xa0', u'')
            ir['stamped_pages_in_urn'] = t4_row.xpath('td[2]/text()').extract_first().strip().replace(u'\xa0', u'')
            ir['diff_compared_to_voters'] = t4_row.xpath('td[3]/text()').extract_first().strip().replace(u'\xa0', u'')
            ir['invalid_pages'] = t4_row.xpath('td[4]/text()').extract_first().strip().replace(u'\xa0', u'')
            ir['valid_pages'] = t4_row.xpath('td[5]/text()').extract_first().strip().replace(u'\xa0', u'')

        candidate_result_rows = response.xpath("body/div/center/table[%s]/tr" % str(5 + offset))
        ir['candidate_results'] = []

        for index, row in enumerate(candidate_result_rows):

            # first row has only headers
            if index > 0:
                ir['candidate_results'].append(
                    CandidateResult(
                        num=row.xpath('td[1]/text()').extract_first().strip(),
                        candidate_name = row.xpath('td[2]/text()').extract_first().strip(),
                        candidate_party = row.xpath('td[3]/text()').extract_first().strip(),
                        num_of_valid_votes = row.xpath('td[4]/text()').extract_first().strip().replace(u'\xa0', u''),
                    )
                )

        vdr['individual_results'] = ir

        gr = GeneralListResult(
            scanned_report_url=urljoin(response.url,
                                       unicodedata.normalize('NFKD', response.xpath(
                                           "body/div/center/table[%s]/tr[1]/td[3]/a/@href" % str(6 + offset)).extract_first()))
        )

        general_list_table = response.xpath("body/div/center/table[%s]" % str(7 + offset))
        gr['total_summary'] = ElectionReport(
            locals_registered=general_list_table.xpath('tr[2]/td[2]/text()').extract_first().strip().replace(u'\xa0', u''),
            locals_voted=general_list_table.xpath('tr[2]/td[3]/text()').extract_first().strip().replace(u'\xa0', u''),
            unstamped_pages_in_urn=general_list_table.xpath('tr[2]/td[4]/text()').extract_first().strip().replace(u'\xa0', u''),
            stamped_pages_in_urn=general_list_table.xpath('tr[2]/td[5]/text()').extract_first().strip().replace(u'\xa0', u''),
            diff_compared_to_voters=general_list_table.xpath('tr[2]/td[6]/text()').extract_first().strip().replace(u'\xa0', u''),
            invalid_pages=general_list_table.xpath('tr[2]/td[7]/text()').extract_first().strip().replace(u'\xa0', u''),
            valid_pages=general_list_table.xpath('tr[2]/td[8]/text()').extract_first().strip().replace(u'\xa0', u'')
        )

        gr['party_list_summary'] = ElectionReport(
            locals_registered=general_list_table.xpath('tr[3]/td[2]/text()').extract_first().strip().replace(u'\xa0', u''),
            locals_voted=general_list_table.xpath('tr[3]/td[3]/text()').extract_first().strip().replace(u'\xa0', u''),
            unstamped_pages_in_urn=general_list_table.xpath('tr[3]/td[4]/text()').extract_first().strip().replace(u'\xa0', u''),
            stamped_pages_in_urn=general_list_table.xpath('tr[3]/td[5]/text()').extract_first().strip().replace(u'\xa0', u''),
            diff_compared_to_voters=general_list_table.xpath('tr[3]/td[6]/text()').extract_first().strip().replace(u'\xa0', u''),
            invalid_pages=general_list_table.xpath('tr[3]/td[7]/text()').extract_first().strip().replace(u'\xa0', u''),
            valid_pages=general_list_table.xpath('tr[3]/td[8]/text()').extract_first().strip().replace(u'\xa0', u'')
        )

        has_minority_results = len(general_list_table.xpath('tr')) > 3
        if has_minority_results:
            gr['minority_list_summary'] = ElectionReport(
                locals_registered=general_list_table.xpath('tr[4]/td[2]/text()').extract_first().strip().replace(u'\xa0', u''),
                locals_voted=general_list_table.xpath('tr[4]/td[3]/text()').extract_first().strip().replace(u'\xa0', u''),
                unstamped_pages_in_urn=general_list_table.xpath('tr[4]/td[4]/text()').extract_first().strip().replace(u'\xa0', u''),
                stamped_pages_in_urn=general_list_table.xpath('tr[4]/td[5]/text()').extract_first().strip().replace(u'\xa0', u''),
                diff_compared_to_voters=general_list_table.xpath('tr[4]/td[6]/text()').extract_first().strip().replace(u'\xa0', u''),
                invalid_pages=general_list_table.xpath('tr[4]/td[7]/text()').extract_first().strip().replace(u'\xa0', u''),
                valid_pages=general_list_table.xpath('tr[4]/td[8]/text()').extract_first().strip().replace(u'\xa0', u'')
            )


        if vdr['non_locals_allowed']:
            general_list_table_non_local = response.xpath("body/div/center/table[%s]" % str(8 + offset))
            gr['total_summary']['non_locals_registered'] = general_list_table_non_local.xpath('tr[3]/td[1]/text()').extract_first().strip().replace(u'\xa0', u'')
            gr['total_summary']['non_locals_voted'] = general_list_table_non_local.xpath('tr[3]/td[2]/text()').extract_first().strip().replace(u'\xa0', u'')
            offset = 2

        party_list_result_rows = response.xpath("body/div/center/table[%s]/tr" % str(8 + offset))
        gr['party_results'] = []

        for index, row in enumerate(party_list_result_rows):

            if index == len(party_list_result_rows) - 1:
                # summary row
                gr['total_votes_on_party_lists'] = row.xpath('td[3]/text()').extract_first().strip().replace(u'\xa0', u'')
            elif index > 0:
                # first row has only headers
                gr['party_results'].append(
                    PartyResult(
                        id=row.xpath('td[1]/text()').extract_first().strip(),
                        party_name=row.xpath('td[2]/text()').extract_first().strip(),
                        num_of_votes=row.xpath('td[3]/text()').extract_first().strip().replace(u'\xa0', u''),
                    )
                )
        vdr['general_list_results'] = gr

        if has_minority_results:
            gr['minority_results'] = {}
            minority_list_rows = response.xpath("body/div/center/table[%s]/tr" % str(9 + offset))
            for index, row in enumerate(minority_list_rows):
                if index > 0:
                    gr['minority_results'][row.xpath('td[1]/text()').extract_first().strip()] = ElectionReport(
                        locals_registered=row.xpath('td[2]/text()').extract_first().strip().replace(u'\xa0', u''),
                        locals_voted=row.xpath('td[3]/text()').extract_first().strip().replace(u'\xa0', u''),
                        unstamped_pages_in_urn=row.xpath('td[4]/text()').extract_first().strip().replace(u'\xa0', u''),
                        stamped_pages_in_urn=row.xpath('td[5]/text()').extract_first().strip().replace(u'\xa0', u''),
                        diff_compared_to_voters=row.xpath('td[6]/text()').extract_first().strip().replace(u'\xa0', u''),
                        invalid_pages=row.xpath('td[7]/text()').extract_first().strip().replace(u'\xa0', u''),
                        valid_pages=row.xpath('td[8]/text()').extract_first().strip().replace(u'\xa0', u'')
             )

        yield vdr