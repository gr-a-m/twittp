import argparse


def main():
    """Parses arguments using argparse and executes corresponding code"""
    command_parser = argparse.ArgumentParser(description='twittp -- Twitter Trend Prediction')
    subparsers = command_parser.add_subparsers(title="commands")

    build_model_parser = subparsers.add_parser('build-model', help='Build a '
        'model for other actions in twittp')

    build_model_parser.description = 'Build a model for other actions in twittp'

    build_model_parser.add_argument('tweets', help='The JSON file containing '
                                    'tweets from the Twitter API')
    build_model_parser.add_argument('trends', help='The JSON file containing '
                                    'trends from the Twitter API')
    build_model_parser.add_argument('--stopword', help='An optional CSV file '
                                    'containing words to ignore when constructing the model')

    loo_test_parser = subparsers.add_parser('loo-test', help='Test the '
        'performance of a model using leave-one-out testing')
    loo_test_parser.description = 'Test the performance of a model using ' \
        'leave-one-out testing'
    loo_test_parser.add_argument('model', help='The JSON file containing the '
        'model created by build-model')

    args = command_parser.parse_args()


if __name__ == '__main__':
    main()
