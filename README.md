Hungarian election 2018 results crawler
=======================================

Scrapy crawler for the 2018 Hungarian election results from valasztas.hu


Running the application
------------------------

1. Setup the environment
    1.1. With Conda
    Create the conda env from the environments.yml

        conda env create -f ./enviroment.yml

    Activate the environment

        source activate hungarian_election_results_2018_crawler

    1.2. With pip (and virtualenv)

        virtualenv env
        source env/bin/activate
        pip install -r requirements.txt

2. Running the crawlers

   - Crawling OEVK results

         scrapy crawl oevk

     crawing can be restricted only to one OEVK

         scrapy crawl oevk -a oevk_id=BARANYA-01

   - voting district results:

         scrapy crawl voting_district

    crawing can be restricted only to one location:

         scrapy crawl voting_district -a location=Oroszlány

    or only one district:

         scrapy crawl voting_district -a location=Oroszlány -a dictrict_id=004


  The results will be exported to json files named by the crawler and crawling timestamp.
