# SwampHacks-XII


AI MODEL: 
Pull from 50 real locations Planet conditions ( hazard index )
 - weather
 - extreme heat
 - lightning ( strike within 10 miles causes 30 minute no work)
 - flooding (sites near rivers flood-risk after heavy rain)
 - soil saturation
 - wildlife sightins


Front end: 
Prediction at 6PM releases next day
Crew reports crash/debris
 - photo
 - pin loc on map
 - share to DB for local loc for future project owners

Admin account
- ranks sites by riskiness
- show where to focus attention/resources

Backend:
 - database to store admin/worker
 - pull from weather APIs
 - pull from model
 - database to store incident info
 - Flask RestFUL