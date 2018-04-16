# -*- coding: utf-8 -*-
import scrapy
from string import ascii_lowercase
import unicodedata
import unidecode
from urllib.parse import urljoin
from ..items import *
import copy
from . import get_and_norm


class WardSpider(scrapy.Spider):
    name = 'wards_2018'
    allowed_domains = ['valasztas.hu']

    start_url_pattern = "http://valasztas.hu/dyn/pv18/szavossz/hu/TK/szkkivtk%s.html"

    def __init__(self, location=None, ward=None, *args, **kwargs):
        super(WardSpider, self).__init__(*args, **kwargs)
        self.location = location
        if location is not None:
            self.start_urls = [self.start_url_pattern % unidecode.unidecode(location[0]).lower()]
        else:
            self.start_urls = [self.start_url_pattern % x for x in ascii_lowercase]
        self.ward = ward

    def parse(self, response):
        links = response.xpath('body/div/center/table[2]//a')
        for link in links:
            wr = WardResult(
                location=link.xpath('text()').extract_first().strip(),
            )
            if self.location is None or self.location.lower() == wr['location'].lower():
                request = scrapy.Request(urljoin(response.url,
                                 unicodedata.normalize('NFKD', link.xpath('@href').extract_first())),
                                 callback=self.parse_location_page)
                request.meta['ward_result'] = wr
                yield request
            else:
                continue

    def parse_location_page(self, response):
        self.logger.debug("processing location result page: %s" % response.url)

        rows = response.xpath('body/div/center/table[2]/tr')
        for index, row in enumerate(rows):

            # first row has only headers
            if index > 0:
                wr = copy.deepcopy(response.meta['ward_result'])
                wr['num'] = row.xpath('td[1]/a/text()').extract_first().strip()
                wr['url'] = urljoin(response.url,
                                    unicodedata.normalize('NFKD', row.xpath('td[1]/a/@href').extract_first()))
                wr['address'] = row.xpath('td[2]/text()').extract_first().strip()
                wr['non_local_votes'] = len(row.xpath('td[3]/img')) > 0
                wr['counting_cross_registered_and_consulate_votes'] = len(row.xpath('td[4]/img')) > 0

                if self.ward is None or self.ward == wr['num']:
                    request = scrapy.Request(wr['url'], callback=self.parse_voting_district_page)
                    request.meta['ward_result'] = wr
                    yield request
                else:
                    continue

    def parse_voting_district_page(self, response):
        self.logger.debug("processing ward result page: %s" % response.url)

        wr = response.meta['ward_result']

        t1_row = response.xpath('body/div/center/table[1]/tr[1]')
        wr['page_generated_at'] = t1_row.xpath('td[1]/text()').extract_first().strip()

        wr['district'] = response.xpath('body/div/center/h2[2]/text()').extract_first().strip()

        ir = IndividualResult(
            scanned_report_url=urljoin(response.url,
                                    unicodedata.normalize('NFKD', response.xpath('body/div/center/table[2]/tr[1]/td[3]/a/@href').extract_first()))
        )

        offset = 0  # There are 3 types of voting districts:
                    # - only locals
                    # - locals + non-locals
                    # - locals + non-locals + votes from consulates.
                    # Each type has extra tables in the pages. The offset variable will represent the table sequence number offsets

        ir['register_stats'] = RegisterStats()
        ir['participant_stats'] = ParticipantStats()
        ir['result_stats'] = ResultStats()

        summary_row = response.xpath('body/div/center/table[3]/tr[3]')
        ir['register_stats']['local_voters'] = get_and_norm(summary_row.xpath('td[1]/text()'))  # AE

        if wr['counting_cross_registered_and_consulate_votes']:
            ir['register_stats']['cross_registered_voters'] = get_and_norm(summary_row.xpath('td[2]/text()'))  # BE
            ir['register_stats']['consulate_voters'] = get_and_norm(summary_row.xpath('td[3]/text()'))  # C
            ir['register_stats']['total'] = get_and_norm(summary_row.xpath('td[4]/text()'))  # EE
        else:
            ir['participant_stats']['locals'] = get_and_norm(summary_row.xpath('td[2]/br/preceding-sibling::text()'))  # FE
            ir['participant_stats']['locals_vote_rate'] = summary_row.xpath('td[2]/br/following-sibling::text()').extract_first().strip()  # FE

        if wr['non_local_votes']:
            offset = 1
            t4_row = response.xpath('body/div/center/table[4]/tr[3]')
            ir['register_stats']['non_local_voters'] = get_and_norm(t4_row.xpath('td[1]/text()'))  # BOE
            ir['participant_stats']['non_locals'] = get_and_norm(t4_row.xpath('td[2]/br/preceding-sibling::text()'))  # GE
            ir['participant_stats']['non_locals_vote_rate'] = t4_row.xpath('td[2]/br/following-sibling::text()').extract_first().strip()  # GE

        if wr['counting_cross_registered_and_consulate_votes']:
            offset = 1
            t4_row = response.xpath('body/div/center/table[4]/tr[3]')
            ir['participant_stats']['locals'] = get_and_norm(t4_row.xpath('td[1]/text()'))  # FE
            ir['participant_stats']['received_envelopes'] = get_and_norm(t4_row.xpath('td[2]/text()'))  # IE
            ir['participant_stats']['total'] = get_and_norm(t4_row.xpath('td[3]/br/preceding-sibling::text()'))  # JE
            ir['participant_stats']['total_rate'] = t4_row.xpath('td[3]/br/following-sibling::text()').extract_first().strip()  # JE

        stat_table_row = response.xpath("body/div/center/table[%s]/tr[3]" % str(4 + offset))
        col_offset = 0
        if wr['non_local_votes']:
            col_offset = 1
            ir['result_stats']['non_local_envelopes_in_urn'] = get_and_norm(stat_table_row.xpath("td[1]/text()"))  # IE
        ir['result_stats']['unstamped_pages_in_urn'] = get_and_norm(stat_table_row.xpath("td[%s]/text()" % str(1 + col_offset)))  # OE
        ir['result_stats']['stamped_pages_in_urn'] = get_and_norm(stat_table_row.xpath("td[%s]/text()" % str(2 + col_offset)))  # KE
        ir['result_stats']['diff_compared_to_voters'] = get_and_norm(stat_table_row.xpath("td[%s]/text()" % str(3 + col_offset)))  # LE
        ir['result_stats']['invalid_pages'] = get_and_norm(stat_table_row.xpath("td[%s]/text()" % str(4 + col_offset)))  # ME
        ir['result_stats']['valid_pages'] = get_and_norm(stat_table_row.xpath("td[%s]/text()" % str(5 + col_offset)))  # NE

        candidate_result_rows = response.xpath("body/div/center/table[%s]/tr" % str(5 + offset))
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

        gr = GeneralListResult(
            scanned_report_url=urljoin(response.url,
                                       unicodedata.normalize('NFKD', response.xpath(
                                           "body/div/center/table[%s]/tr[1]/td[3]/a/@href" % str(6 + offset)).extract_first()))
        )

        if wr['counting_cross_registered_and_consulate_votes']:
            gr['register_stats'] = RegisterStats()
            gr['participant_stats'] = ParticipantStats()

            summary_row = response.xpath("body/div/center/table[%s]/tr[3]" % str(7 + offset))

            gr['register_stats']['local_voters'] = get_and_norm(summary_row.xpath('td[1]/text()'))  # AL
            gr['register_stats']['cross_registered_voters'] = get_and_norm(summary_row.xpath('td[2]/text()'))  # BL
            gr['register_stats']['consulate_voters'] = get_and_norm(summary_row.xpath('td[3]/text()'))  # C
            gr['register_stats']['total'] = get_and_norm(summary_row.xpath('td[4]/text()'))  # EL

            summary_row_2 = response.xpath("body/div/center/table[%s]/tr[3]" % str(8 + offset))
            gr['participant_stats']['locals'] = get_and_norm(summary_row_2.xpath('td[1]/text()'))  # FL
            gr['participant_stats']['received_envelopes'] = get_and_norm(summary_row_2.xpath('td[2]/text()'))  # IL
            gr['participant_stats']['total'] = get_and_norm(summary_row_2.xpath('td[3]/br/preceding-sibling::text()'))  # JL
            gr['participant_stats']['total_rate'] = summary_row_2.xpath('td[3]/br/following-sibling::text()').extract_first().strip()  # JL

            offset += 2

            general_list_table = response.xpath("body/div/center/table[%s]" % str(7 + offset))
            gr['total_summary'] = ListResultStats(
                total_registered=get_and_norm(general_list_table.xpath('tr[2]/td[2]/text()')),
                unstamped_pages_in_urn=get_and_norm(general_list_table.xpath('tr[2]/td[3]/text()')),
                stamped_pages_in_urn=get_and_norm(general_list_table.xpath('tr[2]/td[4]/text()')),
                diff_compared_to_voters=get_and_norm(general_list_table.xpath('tr[2]/td[5]/text()')),
                invalid_pages=get_and_norm(general_list_table.xpath('tr[2]/td[6]/text()')),
                valid_pages=get_and_norm(general_list_table.xpath('tr[2]/td[7]/text()'))
            )

            gr['party_list_summary'] = ListResultStats(
                total_registered=get_and_norm(general_list_table.xpath('tr[3]/td[2]/text()')),
                unstamped_pages_in_urn=get_and_norm(general_list_table.xpath('tr[3]/td[3]/text()')),
                stamped_pages_in_urn=get_and_norm(general_list_table.xpath('tr[3]/td[4]/text()')),
                diff_compared_to_voters=get_and_norm(general_list_table.xpath('tr[3]/td[5]/text()')),
                invalid_pages=get_and_norm(general_list_table.xpath('tr[3]/td[6]/text()')),
                valid_pages=get_and_norm(general_list_table.xpath('tr[3]/td[7]/text()'))
            )

            has_minority_results = len(general_list_table.xpath('tr')) > 3
            if has_minority_results:
                gr['minority_list_summary'] = ListResultStats(
                    total_registered=get_and_norm(general_list_table.xpath('tr[4]/td[2]/text()')),
                    unstamped_pages_in_urn=get_and_norm(general_list_table.xpath('tr[4]/td[3]/text()')),
                    stamped_pages_in_urn=get_and_norm(general_list_table.xpath('tr[4]/td[4]/text()')),
                    diff_compared_to_voters=get_and_norm(general_list_table.xpath('tr[4]/td[5]/text()')),
                    invalid_pages=get_and_norm(general_list_table.xpath('tr[4]/td[6]/text()')),
                    valid_pages=get_and_norm(general_list_table.xpath('tr[4]/td[7]/text()'))
                )
        else:
            general_list_table = response.xpath("body/div/center/table[%s]" % str(7 + offset))
            gr['total_summary'] = ListResultStats(
                locals_registered=get_and_norm(general_list_table.xpath('tr[2]/td[2]/text()')),
                locals_voted=get_and_norm(general_list_table.xpath('tr[2]/td[3]/text()')),
                unstamped_pages_in_urn=get_and_norm(general_list_table.xpath('tr[2]/td[4]/text()')),
                stamped_pages_in_urn=get_and_norm(general_list_table.xpath('tr[2]/td[5]/text()')),
                diff_compared_to_voters=get_and_norm(general_list_table.xpath('tr[2]/td[6]/text()')),
                invalid_pages=get_and_norm(general_list_table.xpath('tr[2]/td[7]/text()')),
                valid_pages=get_and_norm(general_list_table.xpath('tr[2]/td[8]/text()'))
            )

            gr['party_list_summary'] = ListResultStats(
                locals_registered=get_and_norm(general_list_table.xpath('tr[3]/td[2]/text()')),
                locals_voted=get_and_norm(general_list_table.xpath('tr[3]/td[3]/text()')),
                unstamped_pages_in_urn=get_and_norm(general_list_table.xpath('tr[3]/td[4]/text()')),
                stamped_pages_in_urn=get_and_norm(general_list_table.xpath('tr[3]/td[5]/text()')),
                diff_compared_to_voters=get_and_norm(general_list_table.xpath('tr[3]/td[6]/text()')),
                invalid_pages=get_and_norm(general_list_table.xpath('tr[3]/td[7]/text()')),
                valid_pages=get_and_norm(general_list_table.xpath('tr[3]/td[8]/text()'))
            )

            has_minority_results = len(general_list_table.xpath('tr')) > 3
            if has_minority_results:
                gr['minority_list_summary'] = ListResultStats(
                    locals_registered=get_and_norm(general_list_table.xpath('tr[4]/td[2]/text()')),
                    locals_voted=get_and_norm(general_list_table.xpath('tr[4]/td[3]/text()')),
                    unstamped_pages_in_urn=get_and_norm(general_list_table.xpath('tr[4]/td[4]/text()')),
                    stamped_pages_in_urn=get_and_norm(general_list_table.xpath('tr[4]/td[5]/text()')),
                    diff_compared_to_voters=get_and_norm(general_list_table.xpath('tr[4]/td[6]/text()')),
                    invalid_pages=get_and_norm(general_list_table.xpath('tr[4]/td[7]/text()')),
                    valid_pages=get_and_norm(general_list_table.xpath('tr[4]/td[8]/text()'))
                )

        if wr['non_local_votes']:
            gr['register_stats'] = RegisterStats()
            gr['participant_stats'] = ParticipantStats()
            general_list_table_non_local = response.xpath("body/div/center/table[%s]" % str(8 + offset))
            gr['register_stats']['non_local_voters'] = get_and_norm(general_list_table_non_local.xpath('tr[3]/td[1]/text()'))  # BOL
            gr['participant_stats']['non_locals'] = get_and_norm(general_list_table_non_local.xpath('tr[3]/td[2]/text()'))  # GL
            offset += 1

        party_list_result_rows = response.xpath("body/div/center/table[%s]/tr" % str(8 + offset))
        gr['party_results'] = []

        for index, row in enumerate(party_list_result_rows):

            if index == len(party_list_result_rows) - 1:
                # summary row
                gr['total_votes_on_party_lists'] = get_and_norm(row.xpath('td[3]/text()'))
            elif index > 0:
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
            minority_list_rows = response.xpath("body/div/center/table[%s]/tr" % str(9 + offset))
            for index, row in enumerate(minority_list_rows):
                if index > 0:
                    if wr['counting_cross_registered_and_consulate_votes']:
                        gr['minority_results'][row.xpath('td[1]/text()').extract_first().strip()] = ListResultStats(
                            total_registered=get_and_norm(row.xpath('td[2]/text()')),
                            unstamped_pages_in_urn=get_and_norm(row.xpath('td[3]/text()')),
                            stamped_pages_in_urn=get_and_norm(row.xpath('td[4]/text()')),
                            diff_compared_to_voters=get_and_norm(row.xpath('td[5]/text()')),
                            invalid_pages=get_and_norm(row.xpath('td[6]/text()')),
                            valid_pages=get_and_norm(row.xpath('td[7]/text()'))
                        )
                    else:
                        gr['minority_results'][row.xpath('td[1]/text()').extract_first().strip()] = ListResultStats(
                            locals_registered=get_and_norm(row.xpath('td[2]/text()')),
                            locals_voted=get_and_norm(row.xpath('td[3]/text()')),
                            unstamped_pages_in_urn=get_and_norm(row.xpath('td[4]/text()')),
                            stamped_pages_in_urn=get_and_norm(row.xpath('td[5]/text()')),
                            diff_compared_to_voters=get_and_norm(row.xpath('td[6]/text()')),
                            invalid_pages=get_and_norm(row.xpath('td[7]/text()')),
                            valid_pages=get_and_norm(row.xpath('td[8]/text()'))
                        )

        yield wr
