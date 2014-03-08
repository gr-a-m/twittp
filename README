TwitTP -- Twitter Trend Prediction
==================================

This project will include the code created during the duration of my [FURI][1]
project during the Spring of 2014 at Arizona State University. Over time, I
will update this README to cover the scope of the project/repository as it
evolves.

Intent
------

This repository will include code from my research into predicting trends on
Twitter. If successful, I will include code implementing algorithms to take
Twitter data (likely in the form of JSON data, but I may add some restrictions
to the data format for simplicity's sake) and a desired topic, and attempt to
predict whether that topic will appear in the "top trending" categories at
some point in the near future.

As time goes on, I will refine this vision to a more specific set of feature(s)
and capabilities.

Usage
-----

There are two utilities provided in the `scripts/` subdirectory that are for
processing raw tweets/topics from the Twitter API for the purpose of use in
twittp. 

-	`clean-topics.py` processes a JSON file that has the results of one
call to the trending endpoint of the Twitter API on every line and it
outputs those topics in a format that is more friendly for twittp to handle.
-	`clean-tweets.py` processes a JSON file with one Tweet from the Twitter
API per line and outputs a much simpler TSV file with most of the
extraneous fields left out. This makes it easier to store tweets for the
express purpose of running them through twittp and makes it faster for
twittp to run because it wont have to parse a huge JSON file every time it
touches the input.

The actual script to run twittp as intended is not in the repo at the moment.
I'm going through some restructuring, but I expect to have a basic model
construction and leave-one-out testing script soon.

Contact
-------

To contact me, send an email to my [ASU Email][2] or my [personal email][3]. To
learn more about me or what else I do, visit [my website][4].

[1]: http://more.engineering.asu.edu/furi/ "FURI Home Page"
[2]: mailto:grant.a.marshall@asu.edu "ASU Email"
[3]: mailto:gam@grantamarshall.com "Personal Email"
[4]: http://www.mthcmp.com "Personal Website"

