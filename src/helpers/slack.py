import requests
import json

SLACK_URL = "https://hooks.slack.com/services/"

def get_field_markdown(team_name, score, number):
	return [ 	
				{
					"type": "mrkdwn",
					"text": f"{number}. " + team_name
				},
				{
					"type": "mrkdwn",
					"text": f"{score:.2f}"
				}
			]

def get_fields_markdown(names, scores):
	return_markdown = [
				{
					"type": "mrkdwn",
					"text": "_Team Name_"
				},
				{
					"type": "mrkdwn",
					"text": "_Score_"
				}]
	for index, (name, score) in enumerate(zip(names, scores)):
		return_markdown += get_field_markdown(name, score, index+1)
	return return_markdown


MESSEGE_STRUCT = lambda names, scores: {
	"blocks": [
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": f"A new submission has landed in the leader board. \n\n Latest ranking is:"
			},
			"fields": get_fields_markdown(names, scores)
		},
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": "Keep going - still time to get to first place :100: :muscle:"
			}
		}
	]
}

def post_leaders(channel_api:str, leaders:dict, no_leaders = None):
	'''
	If no_leaders isn't specified, posts the full leaderboard. Otherwise posts the top <no_leaders> submissions
	'''

	if not no_leaders:
		no_leaders = 4
	assert 0 < no_leaders < 5, f"Please provide a valid range for the leaderboard" 
	names = list(leaders.keys())[:no_leaders]
	scores = list(leaders.values())[:no_leaders]
	
	response = requests.post(
        url=SLACK_URL+channel_api, 
        data=json.dumps(
            MESSEGE_STRUCT(
                names=names, 
                scores=scores
                )
            )
        )
	print(json.dumps(
            MESSEGE_STRUCT(
                names=names, 
                scores=scores
                )
            )
 	)
	print(response.status_code)

if __name__=="__main__":
#    https://hooks.slack.com/services/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
    channel_api = "TV19HHM24/B044ZGKDNP6/5iikIvB7AP85eJZ7y4UgwQFs"
    leaders = {
        "Steve": 97.1,
        "Bob": 84.3,
        "Alice": 79.6, 
		"Jim": 92, 
		"John": 15
    }

    post_leaders(channel_api, leaders)


