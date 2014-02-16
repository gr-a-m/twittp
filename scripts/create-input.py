import random
import sys


# Function to print help topics
def print_help():
    print('Usage: python create-input.py <cleaned tweets> <cleaned topics>')


# This function reads from the two provided files and prints out input for the
# main twittp program. It essentially outputs a TSV matrix of twitter topics
# over time.
def merge_files(tweets, topics):
    timestamps = []
    topics_time = {}
    print tweets
    print topics

    # We will first extract relevent information from the topics file
    with open(topics) as f:
        for line in f:
            # The file should be <timestamp>\t<topic_name>
            (ts, topic) = line.split('\t')

            # If we haven't seen this timestamp, add it to the list
            if timestamps[-1] != ts:
                timestamps.append(ts)

            # If we haven't seen this topic, create a set for it
            if topics_time.get(topic) is None:
                topics_time[topic] = set()
            topics_time[topic].add(ts)

    # We want to get an equal number of non-topics
    non_topics = sample_texts(tweets, topics_time.keys(), len(topics))


def group_tweets(tweets, topics, non_topics):
    ts_dict = {}

    with open(tweets) as f:
        for line in f:
            line_array = line.split('\t')
            text = line_array[0]


# This method takes a tweet file and generates n random topics from the tweets
# contained within it.
def sample_texts(tweets, topics, n):
    bag_of_words = set()
    with open(tweets) as f:
        for line in f:
            # Add any unique words to bag_of_words
            line_array = line.split('\t')
            words = line_array[0].split()
            bag_of_words.add(words)
    sample = []

    # We will get n arbitrary elements from bag_of_words
    for i in range(0, n):
        topic_list = []
        # Let's get between 1 and 3 words for our fake topic
        for j in range(0, random.randint(1, 3)):
            topic_list.append(bag_of_words.pop())
        # While we're getting fake topics that acutally trended, we need to
        # make a new one because we explicitly want non-topics
        while (' '.join(topic_list)) in topics:
            topic_list = []
            for j in range(0, random.random(1, 3)):
                topic_list.append(bag_of_words.pop())
    return sample


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
