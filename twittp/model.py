from datetime import datetime, timedelta, timezone
import math
import numpy as np
import random
import simplejson as json
from scipy.sparse import csr_matrix
from .twitter import BagOfWords, Stopwords, TwitterTrend


TREND_PREEMT = 0  # Number of windows to preempt trends by
MINIMUM_TREND_SIZE = 15  # Shortest positive trend to allow


def dtw_distance(a, b):
    """ Function to compute the Dynamic-Time Warp Distance between arrays.

    This takes two numpy arrays and computes the DTW distance according to
    http://en.wikipedia.org/wiki/Dynamic_time_warping
    """
    n = a.size // 3
    m = b.size // 3  # Each point in time takes three columns

    dtw = np.zeros((n, m), dtype=np.object)
    dtw[0][0] = 0

    for i in range(n):
        if i == 0:
            continue
        j = 0
        cost = TrendCell.count_weight * math.fabs(a[3 * i] - b[3 * j])
        cost += TrendCell.delta_weight * math.fabs(a[3 * i + 1] - b[3 * j + 1])
        cost += TrendCell.delta_delta_weight * math.fabs(a[3 * i + 2] - b[3 * j + 2])
        dtw[i][j] = cost + dtw[i - 1][j]

    for j in range(n):
        if j == 0:
            continue
        i = 0
        cost = TrendCell.count_weight * math.fabs(a[3 * i] - b[3 * j])
        cost += TrendCell.delta_weight * math.fabs(a[3 * i + 1] - b[3 * j + 1])
        cost += TrendCell.delta_delta_weight * math.fabs(a[3 * i + 2] - b[3 * j + 2])
        dtw[i][j] = cost + dtw[i][j - 1]

    for i in range(n):
        for j in range(m):
            cost = TrendCell.count_weight * ((a[3 * i] - b[3 * j]) ** 2)
            cost += TrendCell.delta_weight * ((a[3 * i + 1] - b[3 * j + 1]) ** 2)
            cost += TrendCell.delta_delta_weight * ((a[3 * i + 2] - b[3 * j + 2]) ** 2)

            dtw[i][j] = cost + min(dtw[i - 1][j], dtw[i][j - 1], dtw[i - 1][j - 1])
    return dtw[n - 1][m - 1]


def array_trend_distance(a, b):
    """ Distance metric between two time-series by minimum alignment.

    This takes two numpy arrays of features like c_t1, d_t1, dd_t1, ..., c_tn,
    d_tn, dd_tn, which should be very sparse, and finds the alignment that
    minimizes euclidean distance and returns the distance of that alignment.
    """
    if len(a) > len(b):
        return array_trend_distance(b, a)

    # Since a and b are likely sparse, let's just get the non-zeroes
    start_a = None
    end_a = 0
    start_b = None
    end_b = 0
    for x in range(len(a)):
        if a[x] != 0:
            end_a = x
            if start_a is None:
                start_a = x
        if b[x] != 0:
            end_b = x
            if start_b is None:
                start_b = x
    len_a = end_a - start_a + 1
    len_b = end_b - start_b + 1

    if start_a is None or start_b is None:
        return 0

    min_distance = None

    for offset in range(len_b - len_a + 1):
        total = 0
        for i in range(len(a)):
            total += math.sqrt(a[start_a + i] - b[start_b + offset + i])

        if min_distance is None:
            min_distance = total
        elif min_distance > total:
            min_distance = total

    return min_distance


class TrendModel:
    """ Represents all of the Trends that compose a "model" in twittp. """

    def __init__(self, trends=None):
        """ Constructor for TrendModel.

        A TrendModel can be loosely reasoned about as a list of different
        TrendLines, some positive, some negative. The constructor reflects
        this.
        """
        self.trends = [] if trends is None else trends

    def leave_one_out(self):
        """ Computes the leave-one-out accuracy of the model.

        In the future, this may tune TopicCell weights until this is optimum.
        For now, it just computes it.
        """
        total = 0
        matches = 0

        for trend_a in self.trends:
            match = None
            min_distance = None

            for trend_b in self.trends:
                if trend_a == trend_b:
                    continue
                dist = trend_a.distance(trend_b)
                if match is None:
                    match = trend_b
                    min_distance = dist
                else:
                    if dist < min_distance:
                        match = trend_b
                        min_distance = dist

            a_trend = trend_a.trending()
            match_trend = match.trending()
            if a_trend and match_trend or not a_trend and not match_trend:
                matches += 1
            total += 1

        return matches / total

    def serialize(self):
        """ Return a string encoding of the model. """
        return json.dumps(self, cls=TwitTPEncoder, ensure_ascii=False)

    def sparse_matrix(self):
        start_t = min([trend.start_ts for trend in self.trends])
        end_t = max([trend.start_ts + trend.window_size * len(trend.data) for trend in self.trends])
        width = ((end_t - start_t) // self.trends[0].window_size) * 3
        y = []
        m = csr_matrix((len(self.trends), width))
        for i, trend in enumerate(self.trends):
            if trend.trending():
                y.append(1)
            else:
                y.append(0)
            offset = ((trend.start_ts - start_t) // trend.window_size) * 3
            for j, datum in enumerate(trend.data):
                m[i, offset + j * 3:offset + (j + 1) * 3] = datum.count, datum.delta, datum.delta_delta
        return m, y

    @staticmethod
    def from_obj(obj):
        if obj.get('trends') is None:
            return None
        trends = [TrendLine.from_obj(trend) for trend in obj['trends']]
        return TrendModel(trends=trends)

    @staticmethod
    def model_from_files(trend_file, tweet_file, stopwords_file):
        """ Constructs a TrendModel from tweets and trends.

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
        return TrendModel(trends=all_trends)


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
            if word in text:
                return True
        return False

    def distance(self, other):
        """ Returns the distance between this TrendLine and another.

        This is measured by finding the alignment of the shorter TrendLine
        against that longer one than minimizes the sum of the distances between
        corresponding data members.
        """
        # Distance is symmetric, so just define it for self < other
        if len(self.data) > len(other.data):
            return other.distance(self)

        min_distance = None
        for offset in range(len(other.data) - len(self.data) + 1):
            total = 0
            for i in range(len(self.data)):
                total += self.data[i].distance(other.data[offset + i])
            if min_distance is None:
                min_distance = total
            elif min_distance > total:
                min_distance = total
        return min_distance

    def trending(self):
        """ Indicates if this TrendLine ever trends on Twitter. """
        for datum in self.data:
            if datum.trending:
                return True
        return False

    @staticmethod
    def from_obj(obj):
        if obj.get('name') is None or obj.get('window_size') is None or \
                obj.get('data') is None or obj.get('start_ts') is None:
            return None
        name = obj['name']
        window_size = obj['window_size']
        start_ts = obj['start_ts']
        data = [TrendCell.from_obj(cell) for cell in obj['data']]
        return TrendLine(name, start_ts, data, window_size)

    @staticmethod
    def random_trend(name, start, end, lengths):
        """ Creates an empty TrendLine of length sampled from lengths. """
        length = lengths[random.randrange(0, len(lengths))]
        start_trend = random.randint(start // 120, (end // 120) - length)
        data = [TrendCell(trending=False) for _ in range(length)]
        return TrendLine(name, start_ts=start_trend*120, data=data)

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
                ts = (dt - datetime(1970, 1, 1, tzinfo=timezone(timedelta(0))))\
                    // timedelta(seconds=1)
                for trend in trends:
                    if trend.start_ts <= ts < end_ts[trend.name] and \
                            trend.match_text(words):
                        offset = (ts - trend.start_ts) // trend.window_size
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
                    datum.delta = datum.count - trend.data[index - 1].count
                    datum.delta_delta = 0
                    second = False
                else:
                    datum.delta = datum.count - trend.data[index - 1].count
                    datum.delta_delta = datum.delta - trend.data[index - 1].delta

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

    @staticmethod
    def from_obj(obj):
        if obj.get('trending') is None or obj.get('count') is None or \
                obj.get('delta') is None or obj.get('delta_delta') is None:
            return None
        return TrendCell(obj['trending'], obj['count'], obj['delta'],
                         obj['delta_delta'])


class TwitTPEncoder(json.JSONEncoder):
    """ This encoder lets us serialize TwitTP models. """
    def default(self, o):
        """ This overridden default() handles TwitTP objects properly. """
        if isinstance(o, TrendModel) or isinstance(o, TrendLine) or \
                isinstance(o, TrendCell):
            return o.__dict__
        return super(TwitTPEncoder, self).default(o)
