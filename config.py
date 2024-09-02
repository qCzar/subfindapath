from boto.s3.connection import S3Connection
# this is what Heroku says to do but I suspect there's more to it because I don't use S3 for this bot?
s3 = S3Connection(os.environ['S3_KEY'], os.environ['S3_SECRET'])

keywords = ["!helped", "helped!", "thank you!", "that helps", "that helped", "helpful!", "thank you very much"]
flairs = {
	1: {
		"title": "Apprentice Pathfinder",
		"template": "7afde4b8-3c71-11ef-be3b-7675771075c0"
	},
	10: {
		"title": "Rookie Pathfinder",
		"template": "880de1c6-3c71-11ef-8c74-c20061f8fb5b"
	},
	20: {
		"title": "Quality Pathfinder",
		"template": "8df8e13a-3c71-11ef-8e6f-a2eb48b72db4"
	},
	40: {
		"title": "Experienced Pathfinder",
		"template": "32a76702-3c76-11ef-bdd5-7a905cb23141"
	},
	70: {
		"title": "Adept Pathfinder", 
		"template": "97786370-3c71-11ef-9914-3aba3435f0e2"
	},
	100: {
		"title": "Expert Pathfinder",
		"template": "39e82da8-3c76-11ef-afb1-e29602640e0e"
	},
	150: {
		"title": "Master Pathfinder",
		"template": "3f98101a-3c76-11ef-9659-eaf1a9f40995"
	},
	200: {
		"title": "Doctorate Pathfinder", 
		"template": "70d5c706-4ebb-11ef-9b93-0a22e7153e33"
	}
}
