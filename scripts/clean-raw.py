import fileinput
import simplejson as json


# Function to process a single JSON string from the raw data file
def process(json_string):
    # Load our JSON string into an object
    json_obj = json.loads(json_string)

    # Create a new object and populate only the fields of interest
    clean_obj = {}
    clean_obj['text'] = json_obj['text']
    clean_obj['created_at'] = json_obj['created_at']
    clean_obj['id'] = json_obj['id']
    clean_obj['user_id'] = json_obj['user']['id']
    clean_obj['user_followers'] = json_obj['user']['followers_count']

    # Print out the clean JSON object
    print json.dumps(clean_obj, ensure_ascii=False).encode("UTF-8", "ignore")

# Function to be called upon starting
def main():
    # Iterate through the lines in stdin, with line being the current line
    for line in fileinput.input():
        process(line)

# If the script is executed, run main
if __name__ == "__main__":
    main()
