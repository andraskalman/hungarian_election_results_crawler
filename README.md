Hungarian election results crawler
=======================================

Scrapy crawler for Hungarian election results from valasztas.hu


Running the application
------------------------

1. Setup the environment
    1.1. With Conda
    Create the conda env from the environments.yml

        conda env create -f ./enviroment.yml

    Activate the environment

        source activate hungarian_election_results_crawler

    1.2. With pip (and virtualenv)

        virtualenv env
        source env/bin/activate
        pip install -r requirements.txt

2. The project contains several spiders:
   - 2018 electoral districts: `districts_2018`
   - 2018 electoral wards: `wards_2018`
   - 2014 electoral districts: `districts_2014`
   - 2014 electoral wards: `wards_2014`

2. Running the crawlers

   - Crawling district results (OEVK)

         scrapy crawl districts_2018

     crawing can be restricted only to one district (district id in paramterer is concatenated from location and number of the district)

         scrapy crawl districts_2018 -a district_id=BARANYA-01

     or at 2014 district crawler

         scrapy crawl districts_2014 -a county_filter=somogy -a district_num_filter=03

   - ward results:

         scrapy crawl wards_2018

    crawing can be restricted only to one location:

         scrapy crawl wards_2018 -a location_filter=Oroszlány

    or only one ward:

         scrapy crawl wards_2018 -a location_filter=Oroszlány -a ward_filter=004


  The results will be exported to json files named by the crawler and crawling timestamp.
