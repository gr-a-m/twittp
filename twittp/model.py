from bisect import bisect
from collections import Counter
from datetime import datetime, timedelta
import math
import random
import re
import simplejson as json
from twitter import TwitterTrend


TREND_PREEMT = 90  # Number of windows to preempt trends by
MINIMUM_TREND_SIZE = 30  # Shortest positive trend to allow


class TrendLine:
    """ Represents a single trend line

    A "trend line" is considered some list of data over consecutive time
    quanta. By default, we assume each window is two minutes, but this can be
    overridden. Also, for now that data is a list of TrendCell, but we could
    generalize more (and I probably will when experimenting with other
    properties to use for trend detection).
    """

    def __init__(self, name, start_ts, data=None, window_size=120):
        """ Constructor for TrendLine 

        The name of the TrendLine is what we imagine the trend would be called
        on Twitter. An example would be "#OWS" or something of the like. Data
        is a list of data points. In general, this means list of TrendCell. The
        start_ts is the UTC timestamp of when the trend began/is beginning.
        The window_size should almost never be changed, but it is the number
        of seconds from one data point to another.
        """
        self.name = name
        self.start_ts = start_ts
        self.data = [] if data is None else data
        self.window_size = window_size

    def match_text(self, text):
        """ Determines whether a piece of text matches the trend. """
        for word in self.name.split():
            if word not in text:
                return False
        return True

    @staticmethod
    def random_trend(name, start, end, lengths):
        """ Creates an empty TrendLine of length sampled from lengths. """
        length = lengths[random.randrange(0, len(lengths))]
        start_trend = random.randint(start / 120, (end / 120) - length)
        data = [TrendCell(trending=False) for x in range(length)]
        return TrendLine(name, start_ts=start_trend, data=data)

    @staticmethod
    def construct_negative_trends(trends, bag_of_words):
        """ Construct negative trends like the provided positive trends.

        The negative trends have names generated from the TrendBagOfWords model
        provided. The start, end, and lengths of the negative trends are based
        on those of the provided positive trends. This ensures that the trends
        produced by this method are like the positive trends provided.
        """
        start = min([trend.start_ts for trend in trends])
        end = max([trend.window_size * (len(trend.data) - 1) + trend.start_ts
                   for trend in trends])
        lengths = [len(trend.data) - 1 for trend in trends]
        names = bag_of_words.random_trend_names(trends, len(trends))

        return [TrendLine.random_trend(name, start, end, lengths) for name in
                names]

    @staticmethod
    def populate_from_file(trends, tweet_file):
        """ Fills data of a list of TrendLines from JSON file of tweet objects.

        This works in two passes -- first the counts are filled in by reading
        each tweet from the JSON file (one tweet per line), and incrementing
        the count if there is a match between the text and the trend and the
        Tweet falls in the range of the trend.

        The second pass consists of going through each trend that was passed to
        the method and filling in the delta and delta_delta of the data from
        the counts that were just loaded in.
        """
        with open(tweet_file) as f:
            for line in f:
                tweet = json.loads(line)
                dt = datetime.strptime(tweet['created_at'], "%a %b %d %H:%M:%S %z %Y")
                ts = (dt - datetime(1970, 1, 1)) // timedelta(seconds=1)
                for trend in trends:
                    end_ts = trend.start_ts + trend.window_size * \
                        (len(trend.data) - 1)
                    if trend.start_ts <= ts <= end_ts and \
                            trend.match_text(tweet['text']):
                        offset = (ts - trend.start_ts) % trend.window_size
                        trend.data[offset].count += 1

        # Second pass
        for trend in trends:
            first = True
            second = False
            for index in len(trend.data):
                datum = trend.data[index]
                if first:
                    datum.delta = 0
                    datum.delta_delta = 0
                    first = False
                    second = True
                elif second:
                    datum.delta = trend.data[index - 1].count - datum.count
                    datum.delta_delta = 0
                    second = False
                else:
                    datum.delta = trend.data[index - 1].count - datum.count
                    datum.delta_delta = trend.data[index - 1].delta - datum.delta

    @staticmethod
    def from_twitter_trend(twitter_trend, window_size=120):
        """"""
        longest_consecutive = 0
        start_longest = None

        start_consecutive = None
        current_consecutive = 0
        last_timestamp = None

        for ts in twitter_trend.timestamps:
            if start_consecutive is None:
                start_consecutive = ts
                current_consecutive = 1
            elif ts == last_timestamp + window_size:
                current_consecutive += 1
            else:
                if start_longest is None:
                    start_longest = start_consecutive
                    longest_consecutive = current_consecutive
                elif longest_consecutive < current_consecutive:
                    start_longest = start_consecutive
                    longest_consecutive = current_consecutive
                else:
                    start_consecutive = None
                    current_consecutive = 0

            last_timestamp = ts

        data = [TrendCell(trending=True) for i in range(longest_consecutive)]

        return TrendLine(twitter_trend.name, start_longest, data, window_size)

    @staticmethod
    def model_from_files(trend_file, tweet_file):
        # Load the positive trends from the file
        twitter_trends = TwitterTrend.from_file(trend_file)
        positive_trends = [TrendLine.from_twitter_trend(trend) for trend in
                           twitter_trends]

        # Remove any short trends
        positive_trends = [trend for trend in positive_trends if
                           len(trend.data) >= MINIMUM_TREND_SIZE]

        # Create negative trends using a bag of words model
        bag_of_words = TrendBagOfWords.from_file(tweet_file)
        negative_trends = TrendLine.construct_negative_trends(positive_trends,
                                                              bag_of_words)

        # Merge the trends and populate them using tweet data
        all_trends = positive_trends
        all_trends.extend(negative_trends)
        TrendLine.populate_from_file(all_trends, tweet_file)
        return all_trends


class TrendCell:
    """ Represents a single data point in a TrendLine

    In particular, this is one where the only variables of concern are the
    number of matching Tweets at this time, the change since the last time, and
    the change in the change since the last time.
    """
    count_weight = 1.0
    delta_weight = 1.0
    delta_delta_weight = 1.0

    def __init__(self, trending, count=0, delta=0, delta_delta=0):
        """ Constructor for TrendCell 

        The only information that is required when constructing a topic cell
        is whether the TrendLine is trending at this time or not. By "trending",
        we mean whatever Twitter uses to determine if a topic is trending.
        """
        self.trending = trending
        self.count = count
        self.delta = delta
        self.delta_delta = delta_delta

    def distance(self, other):
        """ Find the distance between two TrendCells.

        This is highly dependent of the weights we give the count, delta, and
        delta_delta of the TrendCells in distance computation. Optimal weights
        need to be determined experimentally, but for now 1.0 placeholders are
        present. """
        count_distance = math.fabs(self.count - other.count)
        delta_distance = math.fabs(self.delta - other.delta)
        dd_distance = math.fabs(self.delta_delta - other.delta_delta)
        return (TrendCell.count_weight * count_distance) + \
               (TrendCell.delta_weight * delta_distance) + \
               (TrendCell.delta_delta_weight * dd_distance)


class TrendBagOfWords(Counter):
    """ Represents a model of Twitter data to construct false trends from. """
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
        bag_of_words = TrendBagOfWords()
        with open(json_file) as f:
            for line in f:
                tweet = json.loads(line)
                words = tweet['text'].split()
                for word in words:
                    if word in stopwords:
                        continue
                    elif TrendBagOfWords.word_re.match(word) is None:
                        continue
                    else:
                        bag_of_words = bag_of_words + {word: 1}
        return bag_of_words
