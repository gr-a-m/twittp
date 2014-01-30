import calendar
import datetime as dt
import fileinput
import simplejson as json

last_ts = 0

def print_topics(ts, topics):
    line = "%d" % ts
    for topic in topics:
        line += "\t%s" % topic
    print line.encode("UTF-8", "ignore")

# Function to process a single JSON string from the raw data file
def process(json_string):
    global last_ts
    ts = 0

    # Load our JSON string into an object
    json_obj = json.loads(json_string)

    # Create a new object and populate only the fields of interest
    jdt = dt.datetime.strptime(json_obj['as_of'], '%Y-%m-%dT%H:%M:%SZ')
    minutes = jdt.minute
    if minutes % 2 == 1:
        minutes = minutes - 1
   	jdt = jdt.replace(second=0, minute=minutes)

    # If this is the first timestamp, print set the timestamp and print
    if last_ts == 0:
    	last_ts = calendar.timegm(jdt.utctimetuple())
        topics = []
        for topic in json_obj['trends']:
            topics.append(topic['name'])
        print_topics(last_ts, topics)
        return

    ts = calendar.timegm(jdt.utctimetuple())
    # If this new set of trends happened in at least the next time step, print
    if ts > last_ts:
        topics = []
        for topic in json_obj['trends']:
            topics.append(topic['name'])
        while last_ts < ts:
            print_topics(last_ts, topics)
            tempdt = dt.datetime.utcfromtimestamp(last_ts) + dt.timedelta(minutes=2)
            last_ts = calendar.timegm(tempdt.utctimetuple())
        last_ts = ts

# Function to be called upon starting
def main():
    # Iterate through the lines in stdin, with line being the current line
    for line in fileinput.input():
        process(line)

# If the script is executed, run main
if __name__ == "__main__":
    main()
