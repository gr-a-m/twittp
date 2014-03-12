from datetime import datetime, timedelta, timezone
import math
import random
import simplejson as json
from .twitter import BagOfWords, Stopwords, TwitterTrend


TREND_PREEMT = 90  # Number of windows to preempt trends by
MINIMUM_TREND_SIZE = 30  # Shortest positive trend to allow


class TrendModel:
    """ Represents all of the Trends that compose a "model" in twittp. """

    def __init__(self, trends=None):
        self.trends = [] if trends is None else trends

    def leave_one_out(self):
        """ Computes the leave-one-out accuracy of the model.

        In the future, this may tune TopicCell weights until this is optimum.
        For now, it just computes it.
        """
        total = 0
        matches = 0

        for trend_a in self.trends:
            other_trends = list(self.trends)
            other_trends.remove(trend_a)
            match = None
            min_distance = None

            for trend_b in other_trends:
                dist = trend_a.distance(trend_b)
                if match is None:
                    match = trend_b
                    min_distance = dist
                else:
                    if trend_a.distance(trend_b) < min_distance:
                        match = trend_b
                        min_distance = dist
            if trend_a.trending() and trend_b.trending() or not \
                    trend_a.trending() and not trend_b.trending():
                matches += 1
            total += 1

        return matches / total


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

    def distance(self, other):
        """ Returns the distance and align between this TrendLine and another.

        This is measured by finding the alignment of the shorter TrendLine
        against that longer one than minimizes the sum of the distances between
        corresponding data members.
        """
        # Distance is symmetric, so just define it for self < other
        if len(self.data) > len(other.data):
            return other.distance(self)

        # Somewhat complex at first glance, but very clean
        return min(
            [sum(
                [self.data[offset + i].distance(other.data) for i in range(len(self.data))]
            ) for offset in range(len(other.data) - len(self.data))]
        )

    def trending(self):
        """ Indicates if this TrendLine ever trends on Twitter. """
        for datum in self.data:
            if datum.trending:
                return True
        return False

    @staticmethod
    def random_trend(name, start, end, lengths):
        """ Creates an empty TrendLine of length sampled from lengths. """
        length = lengths[random.randrange(0, len(lengths))]
        start_trend = random.randint(start // 120, (end // 120) - length)
        data = [TrendCell(trending=False) for _ in range(length)]
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
        end = max([trend.window_size * (len(trend.data)) + trend.start_ts
                   for trend in trends])
        lengths = [len(trend.data) for trend in trends]
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
            # Memoize the ending timestamps for our trends to speed things up
            end_ts = {}
            for trend in trends:
                end_ts[trend.name] = trend.start_ts + trend.window_size * \
                    (len(trend.data))

            for line in f:
                tweet = json.loads(line)
                words = tweet['text'].split()
                dt = datetime.strptime(tweet['created_at'],
                                       "%a %b %d %H:%M:%S %z %Y")
                ts = (dt - datetime(1970, 1, 1, tzinfo=timezone(timedelta(0)))) // timedelta(seconds=1)
                for trend in trends:
                    if trend.start_ts <= ts <= end_ts[trend.name] and \
                            trend.match_text(words):
                        offset = (ts - trend.start_ts) % trend.window_size
                        trend.data[offset].count += 1

        # Second pass
        for trend in trends:
            first = True
            second = False
            for index in range(len(trend.data)):
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
        """ Converts a TwitterTrend into a TrendLine.

        The TrendLine represents the longest consecutive time windows where this
        trend is "trending" according to Twitter.
        """
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

        data = [TrendCell(True) for _ in range(longest_consecutive)]

        return TrendLine(twitter_trend.name, start_longest, data=data,
                         window_size=window_size)

    @staticmethod
    def model_from_files(trend_file, tweet_file, stopwords_file):
        """ Constructs a "model" (List[TrendLine]) from tweets and trends.

        This high-level method uses a number of other static methods to build
        the various components that go into the model. It starts by reading
        the trends from the trends file, creating "positive" trends from that,
        building a bag-of-words model of the tweets, creating "negative" trends
        from the positive trends and bag-of-words, then populating all of these
        trends with data from the tweets.
        """
        # Load the positive trends from the file
        twitter_trends = TwitterTrend.from_file(trend_file)
        positive_trends = [TrendLine.from_twitter_trend(trend) for trend in
                           twitter_trends]

        # Remove any short trends
        positive_trends = [trend for trend in positive_trends if
                           len(trend.data) >= MINIMUM_TREND_SIZE]

        # Prepend each trend with the TREND_PREEMPT value of TrendCells
        for trend in positive_trends:
            preempt_cells = [TrendCell(False) for _ in range(TREND_PREEMT)]
            preempt_cells.extend(trend.data)
            trend.data = preempt_cells
            trend.start_ts = trend.start_ts - (trend.window_size * TREND_PREEMT)

        # Create negative trends using a bag of words model
        stopwords = Stopwords.from_csv(stopwords_file)
        bag_of_words = BagOfWords.from_file(tweet_file, stopwords=stopwords)
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
        present.
        """
        count_distance = math.fabs(self.count - other.count)
        delta_distance = math.fabs(self.delta - other.delta)
        dd_distance = math.fabs(self.delta_delta - other.delta_delta)
        return (TrendCell.count_weight * count_distance) + \
               (TrendCell.delta_weight * delta_distance) + \
               (TrendCell.delta_delta_weight * dd_distance)
