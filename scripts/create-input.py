import bintrees
import pprint
import random
import simplejson as json
import sys


# The number of seconds to add before a positive trend for matching
TREND_PREEMPT = 7200  # 2 Hours
MIN_TREND_WINDOWS = 30 # 1 Hour trend minimum


class TrendLine:
    def __init__(self, name, start_ts):
        self.name = name
        self.start_ts = start_ts
        self.data = []


class TopicCell:
    def __init__(self):
        self.trending = False
        self.count = 0
        self.delta = 0
        self.delta_delta = 0


# Function to print help topics
def print_help():
    print('Usage: python create-input.py <cleaned tweets> <cleaned topics>')


# This function reads from the two provided files and prints out input for the
# main twittp program. It essentially outputs a TSV matrix of twitter topics
# over time.
def merge_files(tweets, topics):
    timestamps = []
    topics_time = dict()

    first_ts = 0
    last_ts = 0

    # We will first extract relevant information from the topics file
    with open(topics) as f:
        for line in f:
            line_columns = line.split('\t')
            ts = int(line_columns[0])

            if first_ts == 0:
                first_ts = ts
            last_ts = ts

            # If we haven't seen this timestamp, add it to the list
            if len(timestamps) == 0 or timestamps[-1] != ts:
                timestamps.append(ts)

            # For each topic, if we haven't seen this topic, create a set
            for topic in line_columns[1:]:
                topic = topic.strip()  # Strip any trailing whitespace
                if topics_time.get(topic) is None:
                    topics_time[topic] = set()
                topics_time[topic].add(ts)

    # Remove any short topics
    topics_time, longest = prune_trends(topics_time)
    print("{} unique topics".format(len(topics_time.keys())))

    # We want to get an equal number of non-topics
    non_topics = bag_sample_texts(tweets, topics_time.keys(),
                                  len(topics_time.keys()), first_ts, last_ts,
                                  longest)

    # Create corresponding TrendLine lists
    positive_trends = create_trendlines(topics_time, trending=True)
    negative_trends = create_trendlines(non_topics)
    all_trends = positive_trends
    all_trends.extend(negative_trends)  # This object contains all trends


# This function removes any unusually short trends from the provided object
# and returns smaller connected trends. It also returns the length of the
# longest trend
def prune_trends(topics):
    longest = 0
    positive_topics = {}
    for k, v in topics.items():
        length = len(v)
        # Ignore any trends lasting less than the window
        if length < MIN_TREND_WINDOWS:
            continue
        if length > longest:
            longest = length

        # Sort our timestamps
        values = list(v)
        values.sort()

        # Add the timestamps to the topic
        positive_topics[k] = values
    return positive_topics, longest


# Create TrendLine objects out of the topics provided (not populated with data
# from tweets)
def create_trendlines(topics, trending=False):
    trendlines = []

    # Create an empty trend line for each topic
    for k, v in topics.items():
        tl = TrendLine(k, v[0])
        for x in range((v[-1] - v[0]) // 120):
            tc = TopicCell()
            if trending and x in v:
                tc.trending = True
            tl.data.append(tc)
        trendlines.append(tl)

    return trendlines


# This method takes a tweet file and generates n random topics from the tweets
# contained within it. Named "bag" because it treats all of the tweets like a
# bag of words.
def bag_sample_texts(tweets, topics, n, start, end, longest):
    bag_of_words = set()

    # Open up the tweet file and add each tweet's text to the bag of words.
    with open(tweets) as f:
        for line in f:
            # Add any unique words to bag_of_words
            tweet = json.loads(line)
            words = tweet['text'].split()
            for word in words:
                # Ignore URLs
                if word[0:4] == 'http':
                    continue
                word = word.rstrip('.?\'\",;:@!').lstrip('.?\'\",;:@!')
                bag_of_words.add(word)

    sample = {}

    # We will get n arbitrary elements from bag_of_words
    for i in range(n):
        topic_list = []
        # Let's get between 1 and 3 words for our fake topic
        for j in range(random.randint(1, 3)):
            topic_list.append(bag_of_words.pop())
        # While we're getting fake topics that acutally trended, we need to
        # make a new one because we explicitly want non-topics
        while (' '.join(topic_list)) in topics:
            topic_list = []
            for j in range(random.randint(1, 3)):
                topic_list.append(bag_of_words.pop())
        sample[" ".join(topic_list)] = random_trendline(start, end, longest)

    return sample


# This function creates a random array of timestamps in a given range with a
# provided maximum length
def random_trendline(start, end, max_length):
    start_trend = random.randint(start / 120, (end / 120) - max_length)
    trend_length = random.randint(0, max_length)
    return [120 * (start_trend + x) for x in range(trend_length)]


# Entry point for the program
def main():
    if len(sys.argv) < 3:
        print_help()
    else:
        # Arg 1 is the name of the file to load tweets from
        tweet_file_name = sys.argv[1]
        # Arg 2 is the name of the file to load topics from
        topic_file_name = sys.argv[2]
        merge_files(tweet_file_name, topic_file_name)

# If this script is called as a program, run main()
if __name__ == "__main__":
    main()
