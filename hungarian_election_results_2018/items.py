# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class CandidateResult(scrapy.Item):
    id = scrapy.Field()
    candidate_name = scrapy.Field()
    candidate_party = scrapy.Field()
    num_of_valid_votes = scrapy.Field()
    rate_of_valid_votes = scrapy.Field()


class VotingDistrictResult(scrapy.Item):
    # id = scrapy.Field() # {oevk}-{num}
    oevk = scrapy.Field()
    num = scrapy.Field()

    location = scrapy.Field()
    address = scrapy.Field()

    non_local_votes = scrapy.Field()
    counting_cross_registered_and_consulate_votes = scrapy.Field()

    url = scrapy.Field()

    page_generated_at = scrapy.Field()

    individual_results = scrapy.Field()  # IndividualResult
    general_list_results = scrapy.Field()  # GeneralListResult


class ElectionReport(scrapy.Item):
    register_stats = scrapy.Field()  # RegisterStats
    participant_stats = scrapy.Field()  # ParticipantStats
    result_stats = scrapy.Field()  # ResultStats

class OEVKResult(ElectionReport):
    county = scrapy.Field()
    oevk_num = scrapy.Field()
    oevk_url = scrapy.Field()
    oevk_id = scrapy.Field()  # {county}-{oevk}
    location = scrapy.Field()
    voted_candidate = scrapy.Field()
    voted_candidate_party = scrapy.Field()
    progress_of_processing = scrapy.Field()
    page_generated_at = scrapy.Field()

    candidate_results = scrapy.Field()
    voting_area_results = scrapy.Field()


class IndividualResult(ElectionReport):
    scanned_report_url = scrapy.Field()
    candidate_results = scrapy.Field()  # list of CandidateResult


class GeneralListResult(ElectionReport):
    scanned_report_url = scrapy.Field()

    total_summary = scrapy.Field()  # ListResultStats
    party_list_summary = scrapy.Field()  # ListResultStats
    minority_list_summary = scrapy.Field()  # ListResultStats

    party_results = scrapy.Field()  # list of PartyResult

    total_votes_on_party_lists = scrapy.Field()

    minority_results = scrapy.Field()  # dict with key: minority_name and value: ListResultStats


class PartyResult(scrapy.Item):
    id = scrapy.Field()
    party_name = scrapy.Field()
    num_of_votes = scrapy.Field()


class RegisterStats(scrapy.Item):
    local_voters = scrapy.Field()  # AE, AL
    cross_registered_voters = scrapy.Field()  # BE, BL
    non_local_voters = scrapy.Field()  # BOE, BOL
    consulate_voters = scrapy.Field()  # C
    total = scrapy.Field()  # EE


class ParticipantStats(scrapy.Item):
    locals = scrapy.Field()  # FE, FL
    locals_vote_rate = scrapy.Field()  # FE, FL

    non_locals = scrapy.Field()  # GE, GL
    non_locals_vote_rate = scrapy.Field()  # GE

    received_envelopes = scrapy.Field()  # IE, IL

    total = scrapy.Field()  # JE, JL
    total_rate = scrapy.Field()  # JE, JL


class ResultStats(scrapy.Item):
    non_local_envelopes_in_urn = scrapy.Field()  # IE
    unstamped_pages_in_urn = scrapy.Field()  # OE
    stamped_pages_in_urn = scrapy.Field()  # KE
    diff_compared_to_voters = scrapy.Field()  # LE
    invalid_pages = scrapy.Field()  # ME
    valid_pages = scrapy.Field()  # NE
    pages_in_urn_and_envelopes = scrapy.Field()  # KE/OEVK
    invalid_page_rate = scrapy.Field()  # ME / OEVK
    valid_page_rate = scrapy.Field()  # NE / OEVK


class ListResultStats(ResultStats):
    locals_registered = scrapy.Field()
    total_registered = scrapy.Field()
    locals_voted = scrapy.Field()
