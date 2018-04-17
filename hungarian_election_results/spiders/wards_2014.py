# -*- coding: utf-8 -*-
import scrapy
from string import ascii_lowercase
import unicodedata
import unidecode
from urllib.parse import urljoin
from ..items import *
import copy
from . import get_and_norm


class Ward2014Spider(scrapy.Spider):
    name = 'wards_2014'
    allowed_domains = ['valasztas.hu']

    start_url_pattern = "http://valtor.valasztas.hu/valtort/jsp/telkiv.jsp?EA=33&TIP=0&URLTIP=1&URL=szavkorval&URLPAR=URL%%3D2%%26URLPAR%%3D2&CH=%s"

    def __init__(self, location_filter=None, ward_filter=None, *args, **kwargs):
        super(Ward2014Spider, self).__init__(*args, **kwargs)
        self.location_filter = location_filter
        if location_filter is not None:
            self.start_urls = [self.start_url_pattern % unidecode.unidecode(location_filter[0]).lower()]
        else:
            self.start_urls = [self.start_url_pattern % x for x in ascii_lowercase]
        self.ward_filter = ward_filter

    def parse(self, response):
        links = response.xpath('body/div/center/table[2]//a')
        for link in links:
            wr = WardResult(
                location=link.xpath('text()').extract_first().strip(),
            )
            if self.location_filter is None or self.location_filter.lower() == wr['location'].lower():
                request = scrapy.Request(urljoin(response.url,
                                 unicodedata.normalize('NFKD', link.xpath('@href').extract_first())),
                                 callback=self.parse_location_page)
                request.meta['ward_result'] = wr
                yield request
            else:
                continue

    def parse_location_page(self, response):
        self.logger.debug("processing location result page: %s" % response.url)

        rows = response.xpath('body/div/center/table[1]/tr')
        for index, row in enumerate(rows):

            # first row has only headers
            if index > 0:
                wr = copy.deepcopy(response.meta['ward_result'])
                wr['num'] = row.xpath('td[1]//a/text()').extract_first().strip()
                wr['url'] = urljoin(response.url,
                                    unicodedata.normalize('NFKD', row.xpath('td[1]//a/@href').extract_first()))
                wr['address'] = row.xpath('td[2]//text()').extract_first().strip()
                spec = row.xpath('td[3]//text()').extract_first()
                wr['non_local_votes'] = spec == 'Településszintű lakosok + átjelentkezettek szavazására kijelölt'
                wr['counting_cross_registered_and_consulate_votes'] = spec == 'Átjelentkezettek + külképviseleten szavazók szavazat számlálásra kijelölt'

                if self.ward_filter is None or self.ward_filter == wr['num']:
                    request = scrapy.Request(wr['url'], callback=self.parse_ward_page)
                    request.meta['ward_result'] = wr
                    yield request
                else:
                    continue

    def parse_ward_page(self, response):
        self.logger.debug("processing ward page: %s" % response.url)
        wr = response.meta['ward_result']
        wr['district'] = response.xpath('body/div/center/p[1]//text()').extract_first().strip()
        link_list = response.xpath('body/div/center/table[1]/tr//ul')
        individual_subpage_url = urljoin(response.url,
                                 unicodedata.normalize('NFKD', link_list.xpath('li[1]/a/@href').extract_first()))
        list_subpage_url = urljoin(response.url,
                                 unicodedata.normalize('NFKD', link_list.xpath('li[2]/a/@href').extract_first()))

        request = scrapy.Request(individual_subpage_url, callback=self.parse_individual_page)
        request.meta['ward_result'] = wr
        request.meta['list_page_url'] = list_subpage_url
        yield request

    def parse_individual_page(self, response):
        self.logger.debug("processing individual page: %s" % response.url)
        wr = response.meta['ward_result']

        wr['district'] = "%s %s" % (wr['district'], response.xpath('body/div/center/p[contains(.,"számú egyéni választókerület")]//text()').extract_first().strip())

        ir = IndividualResult()

        offset = 0

        ir['register_stats'] = RegisterStats()
        ir['participant_stats'] = ParticipantStats()
        ir['result_stats'] = ResultStats()

        summary_row = response.xpath('body/div/center/table[1]/tr[3]')
        ir['register_stats']['local_voters'] = get_and_norm(summary_row.xpath('td[1]/text()'))  # AE

        if wr['counting_cross_registered_and_consulate_votes']:
            ir['register_stats']['cross_registered_voters'] = get_and_norm(summary_row.xpath('td[2]/text()'))  # BE
            ir['register_stats']['consulate_voters'] = get_and_norm(summary_row.xpath('td[3]/text()'))  # C
            ir['register_stats']['total'] = get_and_norm(summary_row.xpath('td[4]/text()'))  # EE
        else:
            ir['participant_stats']['locals'] = get_and_norm(summary_row.xpath('td[2]/text()'))  # FE

        if wr['non_local_votes']:
            offset = 1
            t4_row = response.xpath('body/div/center/table[2]/tr[3]')
            ir['register_stats']['non_local_voters'] = get_and_norm(t4_row.xpath('td[1]/text()'))  # BOE
            ir['participant_stats']['non_locals'] = get_and_norm(t4_row.xpath('td[2]/text()'))  # GE

        if wr['counting_cross_registered_and_consulate_votes']:
            offset = 1
            t4_row = response.xpath('body/div/center/table[2]/tr[3]')
            ir['participant_stats']['locals'] = get_and_norm(t4_row.xpath('td[1]/text()'))  # FE
            ir['participant_stats']['received_envelopes'] = get_and_norm(t4_row.xpath('td[2]/text()'))  # IE
            ir['participant_stats']['total'] = get_and_norm(t4_row.xpath('td[3]/text()'))  # JE

        stat_table_row = response.xpath("body/div/center/table[%s]/tr[3]" % str(2 + offset))
        ir['result_stats']['stamped_pages_in_urn'] = get_and_norm(stat_table_row.xpath("td[1]/text()"))  # KE
        ir['result_stats']['diff_compared_to_voters'] = get_and_norm(stat_table_row.xpath("td[2]/text()"))  # LE
        ir['result_stats']['invalid_pages'] = get_and_norm(stat_table_row.xpath("td[3]/text()"))  # ME
        ir['result_stats']['valid_pages'] = get_and_norm(stat_table_row.xpath("td[4]/text()"))  # NE

        candidate_result_rows = response.xpath("body/div/center/table[%s]/tr" % str(3 + offset))
        ir['candidate_results'] = []

        for index, row in enumerate(candidate_result_rows):

            # first row has only headers
            if index > 0:
                ir['candidate_results'].append(
                    CandidateResult(
                        id=row.xpath('td[1]/text()').extract_first().strip(),
                        candidate_name=row.xpath('td[2]/text()').extract_first().strip(),
                        candidate_party=row.xpath('td[3]/text()').extract_first().strip(),
                        num_of_valid_votes=get_and_norm(row.xpath('td[4]/text()')),
                    )
                )

        wr['individual_results'] = ir
        request = scrapy.Request(response.meta['list_page_url'], callback=self.parse_list_page)
        request.meta['ward_result'] = wr
        yield request

    def parse_list_page(self, response):
        self.logger.debug("processing list page: %s" % response.url)
        wr = response.meta['ward_result']

        gr = GeneralListResult()

        general_list_table = response.xpath("body/div/center/table[1]")
        if wr['counting_cross_registered_and_consulate_votes']:

            gr['total_summary'] = ListResultStats(
                total_registered=get_and_norm(general_list_table.xpath('tr[2]/td[2]/text()')),
                locals_voted=get_and_norm(general_list_table.xpath('tr[2]/td[3]/text()')),
                received_envelopes=get_and_norm(general_list_table.xpath('tr[2]/td[4]/text()')),
                total_voted=get_and_norm(general_list_table.xpath('tr[2]/td[5]/text()')),
                stamped_pages_in_urn_and_envelopes=get_and_norm(general_list_table.xpath('tr[2]/td[6]/text()')),
                invalid_pages=get_and_norm(general_list_table.xpath('tr[2]/td[7]/text()')),
                valid_pages=get_and_norm(general_list_table.xpath('tr[2]/td[8]/text()'))
            )

            gr['party_list_summary'] = ListResultStats(
                total_registered=get_and_norm(general_list_table.xpath('tr[3]/td[2]/text()')),
                locals_voted=get_and_norm(general_list_table.xpath('tr[3]/td[3]/text()')),
                received_envelopes=get_and_norm(general_list_table.xpath('tr[3]/td[4]/text()')),
                total_voted=get_and_norm(general_list_table.xpath('tr[3]/td[5]/text()')),
                stamped_pages_in_urn_and_envelopes=get_and_norm(general_list_table.xpath('tr[3]/td[6]/text()')),
                invalid_pages=get_and_norm(general_list_table.xpath('tr[3]/td[7]/text()')),
                valid_pages=get_and_norm(general_list_table.xpath('tr[3]/td[8]/text()'))
            )

            gr['minority_list_summary'] = ListResultStats(
                total_registered=get_and_norm(general_list_table.xpath('tr[4]/td[2]/text()')),
                locals_voted=get_and_norm(general_list_table.xpath('tr[4]/td[3]/text()')),
                received_envelopes=get_and_norm(general_list_table.xpath('tr[4]/td[4]/text()')),
                total_voted=get_and_norm(general_list_table.xpath('tr[2]/td[5]/text()')),
                stamped_pages_in_urn_and_envelopes=get_and_norm(general_list_table.xpath('tr[4]/td[6]/text()')),
                invalid_pages=get_and_norm(general_list_table.xpath('tr[4]/td[7]/text()')),
                valid_pages=get_and_norm(general_list_table.xpath('tr[4]/td[8]/text()'))
            )
        else:
            gr['total_summary'] = ListResultStats(
                locals_registered=get_and_norm(general_list_table.xpath('tr[2]/td[2]/text()')),
                locals_voted=get_and_norm(general_list_table.xpath('tr[2]/td[3]/text()')),
                stamped_pages_in_urn=get_and_norm(general_list_table.xpath('tr[2]/td[4]/text()')),
                diff_compared_to_voters=get_and_norm(general_list_table.xpath('tr[2]/td[5]/text()')),
                invalid_pages=get_and_norm(general_list_table.xpath('tr[2]/td[6]/text()')),
                valid_pages=get_and_norm(general_list_table.xpath('tr[2]/td[7]/text()'))
            )

            gr['party_list_summary'] = ListResultStats(
                locals_registered=get_and_norm(general_list_table.xpath('tr[3]/td[2]/text()')),
                locals_voted=get_and_norm(general_list_table.xpath('tr[3]/td[3]/text()')),
                stamped_pages_in_urn=get_and_norm(general_list_table.xpath('tr[3]/td[4]/text()')),
                diff_compared_to_voters=get_and_norm(general_list_table.xpath('tr[3]/td[5]/text()')),
                invalid_pages=get_and_norm(general_list_table.xpath('tr[3]/td[6]/text()')),
                valid_pages=get_and_norm(general_list_table.xpath('tr[3]/td[7]/text()'))
            )

            gr['minority_list_summary'] = ListResultStats(
                locals_registered=get_and_norm(general_list_table.xpath('tr[4]/td[2]/text()')),
                locals_voted=get_and_norm(general_list_table.xpath('tr[4]/td[3]/text()')),
                stamped_pages_in_urn=get_and_norm(general_list_table.xpath('tr[4]/td[4]/text()')),
                diff_compared_to_voters=get_and_norm(general_list_table.xpath('tr[4]/td[5]/text()')),
                invalid_pages=get_and_norm(general_list_table.xpath('tr[4]/td[6]/text()')),
                valid_pages=get_and_norm(general_list_table.xpath('tr[4]/td[7]/text()'))
            )

        has_minority_results = ('locals_registered' in gr['minority_list_summary']
                                and int(gr['minority_list_summary']['locals_registered']) > 0) \
                               or \
                               ('total_registered' in gr['minority_list_summary']
                                and int(gr['minority_list_summary']['total_registered']) > 0)

        # if not has_minority_results:
        #    del gr['minority_list_summary']

        offset = 0
        if wr['non_local_votes']:
            gr['register_stats'] = RegisterStats()
            gr['participant_stats'] = ParticipantStats()
            general_list_table_non_local = response.xpath("body/div/center/table[2]")
            gr['register_stats']['non_local_voters'] = get_and_norm(general_list_table_non_local.xpath('tr[3]/td[1]/text()'))  # BOL
            gr['participant_stats']['non_locals'] = get_and_norm(general_list_table_non_local.xpath('tr[3]/td[2]/text()'))  # GL
            offset = 1

        party_list_result_rows = response.xpath("body/div/center/table[%s]/tr" % str(2 + offset))
        gr['party_results'] = []

        for index, row in enumerate(party_list_result_rows):

            if index > 0:
                # first row has only headers
                gr['party_results'].append(
                    PartyResult(
                        id=row.xpath('td[1]/text()').extract_first().strip(),
                        party_name=row.xpath('td[2]/text()').extract_first().strip(),
                        num_of_votes=get_and_norm(row.xpath('td[3]/text()')),
                    )
                )
        wr['general_list_results'] = gr

        if has_minority_results:
            gr['minority_results'] = {}
            minority_list_rows = response.xpath("body/div/center/table[%s]/tr" % str(3 + offset))
            for index, row in enumerate(minority_list_rows):
                if index > 0:
                    if wr['counting_cross_registered_and_consulate_votes']:
                        stats = ListResultStats(
                            total_registered=get_and_norm(row.xpath('td[2]/text()')),
                            locals_voted=get_and_norm(row.xpath('td[3]/text()')),
                            stamped_pages_in_urn_and_envelopes=get_and_norm(row.xpath('td[4]/text()')),
                            invalid_pages=get_and_norm(row.xpath('td[5]/text()')),
                            valid_pages=get_and_norm(row.xpath('td[6]/text()'))
                        )
                        if int(stats['total_registered']) > 0:
                            gr['minority_results'][row.xpath('td[1]/text()').extract_first().strip()] = stats
                    else:
                        stats = ListResultStats(
                            locals_registered=get_and_norm(row.xpath('td[2]/text()')),
                            locals_voted=get_and_norm(row.xpath('td[3]/text()')),
                            stamped_pages_in_urn=get_and_norm(row.xpath('td[4]/text()')),
                            diff_compared_to_voters=get_and_norm(row.xpath('td[5]/text()')),
                            invalid_pages=get_and_norm(row.xpath('td[6]/text()')),
                            valid_pages=get_and_norm(row.xpath('td[7]/text()'))
                        )
                        if int(stats['locals_registered']) > 0:
                            gr['minority_results'][row.xpath('td[1]/text()').extract_first().strip()] = stats

        yield wr
