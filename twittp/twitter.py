from bisect import bisect
import calendar
from collections import Counter
import datetime as dt
import random
import re
import simplejson as json


class TwitterTrend:
    """ Represents a trend from the Twitter API.

    Note that this is different from a TrendLine. This simply represents a
    trend's name and when Twitter said is was in the top trending. A TrendLine
    on the other hand is intended to communicate change in a Trend over time
    based on some properties of the Tweets as they were in a time window. Use
    this to model the output from the Twitter API's trending endpoint.
    """

    def __init__(self, name, timestamps=None, window_size=120):
        """ Constructor for TwitterTrend with or without timestamps.

        If no timestamps are provided, it is assumed that they will be filled
        in at a later time and timestamps is initialized to an empty list. Name
        should be the name of the trend as in the JSON file retrieved from the
        Twitter API. The window_size should almost never be changed, but it is
        the number of seconds between trend windows, aka, it represents how
        granular our trends are.
        """
        self.name = name
        self.timestamps = [] if timestamps is None else timestamps
        self.window_size = window_size

    @staticmethod
    def from_file(json_file):
        """ Read a trends from a file using the from_twitter_json method. """
        lines = []
        with open(json_file) as f:
            for line in f:
                lines.append(line)
        return TwitterTrend.from_json_strings(lines)

    @staticmethod
    def from_json_strings(json_strings):
        """ Constructs a list of TwitterTrends from a list of json strings.

        This json_strings argument is expected to be a list of JSON strings,
        each of which is the return value from the Twitter API's trends
        endpoint at a particular time.
        """
        trends_timestamps = {}
        last_ts = 0
        for json_s in json_strings:
            json_obj = json.loads(json_s)
            jdt = dt.datetime.strptime(json_obj['as_of'], '%Y-%m-%dT%H:%M:%SZ')

            # Reduce jdt to the nearest 2-minute window, rounded down
            minutes = jdt.minute
            minutes = minutes - (minutes % 2)  # If odd, reduce to even
            jdt.replace(minute = minutes, second = 0, microsecond = 0)

            ts = calendar.timegm(jdt.utctimetuple())

            while ts > last_ts:
                for topic in json_obj['trends']:
                    if trends_timestamps.get(topic['name']) is None:
                        trends_timestamps[topic['name']] = [last_ts]
                    else:
                        trends_timestamps[topic['name']].append(last_ts)

                if last_ts == 0:
                    last_ts = ts
                else:
                    tempdt = dt.datetime.utcfromtimestamp(last_ts) + \
                             dt.timedelta(minutes=2)
                    last_ts = calendar.timegm(tempdt.utctimetuple())

        trends = []
        for trend, timestamps in trends_timestamps:
            twitter_trend = TwitterTrend(trend, timestamps=timestamps)
            trends.append(twitter_trend)

        return trends


class BagOfWords(Counter):
    """ Represents a bag-of-words model of Tweets.

    This is used to construct "non-trends", i.e., strings that are sampled from
    the distribution of words in Tweets that could be trends, but are not. It
    follows what you would expect for a bag-of-words model of tweets to do. One
    important thing to understand is how words are read from a Tweet. A word is
    something that matches the word_re regex and is flanked by whitespace.
    """
    word_re = re.compile("#?\w\w\Z")

    def random_trend_names(self, positive_trends, n=1):
        """ Creates n unique topics that don't match any positive topics. """
        total = 0
        words = []
        weights = []
        for word, weight in self:
            total += weight
            weights.append(total)

        positive_names = set([trend.name for trend in positive_trends])
        negative_names = []

        for x in range(n):
            name_words = []

            while ' '.join(name_words) not in positive_names or negative_names:
                name_words = []
                for j in range(random.randint(1, 3)):
                    i = random.randrange(total)
                    x = bisect(weights, i)
                    name_words.append(words[x])

            negative_names.append(' '.join(name_words))
        return negative_names

    @staticmethod
    def from_file(json_file, stopwords=set()):
        """ Takes a file of Tweets and a stopwords set and create a word model.

        The json_file should be a string path to the file containing one tweet
        per line encoded in JSON as the Twitter API does. Technically, all that
        is required for model creation is just the 'text' field of the objects,
        so other fields can be dropped for bag of words model creation. The
        stopwords argument is a set containing the words to ignore when
        constructing the model.
        """
        bag_of_words = BagOfWords()
        with open(json_file) as f:
            for line in f:
                tweet = json.loads(line)
                words = tweet['text'].split()
                for word in words:
                    if word in stopwords:
                        continue
                    elif BagOfWords.word_re.match(word) is None:
                        continue
                    else:
                        bag_of_words = bag_of_words + {word: 1}
        return bag_of_words