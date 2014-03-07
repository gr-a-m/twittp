from bisect import bisect
from collections import deque
from datetime import datetime, timedelta
import pprint
import random
import re
import simplejson as json
import sys


# The number of seconds to add before a positive trend for matching
TREND_PREEMPT = 7200  # 2 Hours
MIN_TREND_WINDOWS = 30  # 1 Hour trend minimum
stopwords = set()


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
    print('Usage: python create-input.py <cleaned tweets> <cleaned topics> <stopwords>')


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
    # for k, v in topics_time.items():
    #     print("{}\t{}".format(k, len(v)))
    topics_time, longest = prune_trends(topics_time)
    print("{} unique topics".format(len(topics_time.keys())))

    # We want to get an equal number of non-topics
    non_topics = bag_sample_texts(tweets, topics_time,
                                  len(topics_time.keys()), first_ts, last_ts,
                                  longest)

    # Create corresponding TrendLine lists
    positive_trends = create_trendlines(topics_time, trending=True)
    negative_trends = create_trendlines(non_topics)
    all_trends = positive_trends
    all_trends.extend(negative_trends)  # This object contains all trends
    pp = pprint.PrettyPrinter(indent=4)
    for tr in all_trends:
        pp.pprint(tr.name)
        pp.pprint(tr.start_ts)
        pp.pprint(len(tr.data))


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
        tl = TrendLine(k, v[0] - TREND_PREEMPT)

        # If we're trending, prepend some non-trending timestamps
        for x in range(TREND_PREEMPT // 120):
            tc = TopicCell()
            tl.data.append(tc)

        # Go through and add a TopicCell for each timestamp
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
def bag_sample_texts(tweets, topics_time, n, start, end, longest):
    global stopwords
    topics = topics_time.keys()
    bag_of_words = {}
    word_re = re.compile("\w\w+\Z")  # make a word regex

    true_topics_lengths = [len(topics_time[k]) for k in topics_time.keys()]

    # Open up the tweet file and add each tweet's text to the bag of words.
    with open(tweets) as f:
        for line in f:
            # Add any unique words to bag_of_words
            tweet = json.loads(line)
            words = tweet['text'].split()
            for word in words:
                word = word.lower()
                # Ignore URLs
                if (word_re.match(word) is None) or word in stopwords:
                    continue
                if bag_of_words.get(word) is None:
                    bag_of_words[word] = 1
                else:
                    bag_of_words[word] += 1

    sample = {}

    # Set up the machinery to randomly sample from the words according to
    # their frequency.
    values, weights = zip(*bag_of_words.items())
    total = 0
    cumulative_weights = []
    for w in weights:
        total += w
        cumulative_weights.append(total)

    # We will get n arbitrary elements from bag_of_words
    for i in range(n):
        topic_list = []
        # Let's get between 1 and 3 words for our fake topic
        for j in range(random.randint(1, 3)):
            x = random.randrange(0, total)
            i = bisect(cumulative_weights, x)
            topic_list.append(values[i])
        # While we're getting fake topics that acutally trended, we need to
        # make a new one because we explicitly want non-topics
        while (' '.join(topic_list)) in topics:
            topic_list = []
            for j in range(random.randint(1, 3)):
                x = random.randrange(0, total)
                i = bisect(cumulative_weights, x)
                topic_list.append(values[i])
        sample[" ".join(topic_list)] = random_trendline(start, end, longest,
                                                        true_topics_lengths)

    return sample


def populate_trendlines(tweets, trends):
    # Create a list of deques that contain each trend's timestamps
    tss = []
    for t in trends:
        t_ts = deque()
        for n in range(len(t.data)):
            t_ts.append(t.start_ts + 120 * n)
        tss.append(t_ts)

    with open(tweets) as f:
        for line in f:
            tweet = json.loads(line)
            words = tweet.split()
            dt = datetime.strptime(tweet['created_at'],
                                   "%a %b %d %H:%M:%S %z %Y")
            ts = (dt - datetime(1970, 1, 1)) // timedelta(seconds=1)

            # Only check for a match if in the ts
            for i in range(len(tss)):
                t_ts = tss[i]
                first_ts = t_ts[0]

                # Our tweets have passed this times window
                if ts >= first_ts + 120:
                    t_ts.popleft()
                    first_ts = t_ts[0]

                # We are in the window
                if ts >= first_ts:
                    if match_topic(trends[i].name, words):
                        offset = (trends[i].start_ts - first_ts) // 120
                        trends[i].data[offset].count += 1


def match_topic(topic, words):
    for t in topic.split():
        if t in words:
            return True
    return False


# This function creates a random array of timestamps in a given range with a
# provided maximum length
def random_trendline(start, end, max_length, lengths):
    start_trend = random.randint(start / 120, (end / 120) - max_length)
    length_index = random.randrange(0, len(lengths))
    trend_length = lengths[length_index]

    return [120 * (start_trend + x) for x in range(trend_length)]


# Entry point for the program
def main():
    global stopwords
    if len(sys.argv) < 4:
        print_help()
    else:
        # Arg 1 is the name of the file to load tweets from
        tweet_file_name = sys.argv[1]
        # Arg 2 is the name of the file to load topics from
        topic_file_name = sys.argv[2]
        # Arg 3 is a file containing our stopwords to ignore
        stopwords_file_name = sys.argv[3]
        with open(stopwords_file_name) as f:
            for line in f:
                stopwords.update(line.split())

        # Finally, kick off execution
        merge_files(tweet_file_name, topic_file_name)

# If this script is called as a program, run main()
if __name__ == "__main__":
    main()
