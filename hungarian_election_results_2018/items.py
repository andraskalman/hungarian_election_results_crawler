# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class OEVKResult(scrapy.Item):

    county = scrapy.Field()
    oevk_num = scrapy.Field()
    oevk_url = scrapy.Field()
    oevk_id = scrapy.Field() # {county}-{oevk}
    location = scrapy.Field()
    voted_candidate = scrapy.Field()
    voted_candidate_party = scrapy.Field()
    progress_of_processing = scrapy.Field()
    page_generated_at = scrapy.Field()

# column titles are not similar to ElectionReport

    locals_registered = scrapy.Field()              # AE
    non_locals_registered = scrapy.Field()          # BE
    registered_at_consulates = scrapy.Field()       # CE
    total_num_of_registered = scrapy.Field()        # EE

    locals_voted = scrapy.Field()                   # FE
    non_local_envelopes = scrapy.Field()            # IE
    total_num_of_voters = scrapy.Field()            # JE
    total_vote_rate = scrapy.Field()                # JE

    pages_in_urn_and_envelopes = scrapy.Field()     # KE
    invalid_pages = scrapy.Field()                  # ME
    invalid_page_rate = scrapy.Field()              # ME
    valid_pages = scrapy.Field()                    # NE
    valid_page_rate = scrapy.Field()                # NE

    candidate_results = scrapy.Field()
    voting_area_results = scrapy.Field()


class CandidateResult(scrapy.Item):
    num = scrapy.Field()
    candidate_name = scrapy.Field()
    candidate_party = scrapy.Field()
    num_of_valid_votes = scrapy.Field()
    rate_of_valid_votes = scrapy.Field()


class VotingDistrictResult(scrapy.Item):

    #id = scrapy.Field() # {oevk}-{num}
    oevk = scrapy.Field()
    num = scrapy.Field()

    location = scrapy.Field()
    address = scrapy.Field()

    non_local_votes = scrapy.Field()
    non_local_and_consulate_votes = scrapy.Field()

    url = scrapy.Field()

    page_generated_at = scrapy.Field()

    individual_results = scrapy.Field()         # IndividualResult
    general_list_results = scrapy.Field()       # GeneralListResult


class ElectionReport(scrapy.Item):
    locals_registered = scrapy.Field()          # AE
    locals_voted = scrapy.Field()               # FE
    locals_vote_rate = scrapy.Field()           # FE

    registered = scrapy.Field()                 # AL

    non_locals_registered = scrapy.Field()      # BE / BOE / BOL
    non_locals_voted = scrapy.Field()           # GE / GL
    non_locals_vote_rate = scrapy.Field()       # GE_rate

    registered_at_consulates = scrapy.Field()  # CE
    total_num_of_registered = scrapy.Field()   # EE
    non_local_and_consulate_envelope_votes = scrapy.Field()            # IE
    total_num_of_voters = scrapy.Field()            # JE
    total_vote_rate = scrapy.Field()                # JE

    non_local_envelopes_in_urn = scrapy.Field() # IE
    unstamped_pages_in_urn = scrapy.Field()     # OE
    stamped_pages_in_urn = scrapy.Field()       # KE
    diff_compared_to_voters = scrapy.Field()    # LE
    invalid_pages = scrapy.Field()              # ME
    valid_pages = scrapy.Field()                # NE



class IndividualResult(ElectionReport):

    scanned_report_url = scrapy.Field()
    candidate_results = scrapy.Field()      # list of CandidateResult


class GeneralListResult(ElectionReport):
    scanned_report_url = scrapy.Field()

    total_summary = scrapy.Field()          # election report
    party_list_summary = scrapy.Field()     # election report
    minority_list_summary = scrapy.Field()  # election report

    party_results = scrapy.Field()          # list of PartyResult

    total_votes_on_party_lists = scrapy.Field()

    minority_results = scrapy.Field()       # dict of minority_name and election reports


class PartyResult(scrapy.Item):
    id = scrapy.Field()
    party_name = scrapy.Field()
    num_of_votes = scrapy.Field()
