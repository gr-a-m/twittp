TwitTP -- Twitter Trend Prediction
==================================

This project will include the code created during the duration of my [FURI][1]
project during the Spring of 2014 at Arizona State University. Over time, I
will update this README to cover the scope of the project/repository as it
evolves.

As of this writing (January 22, 2014), I have not completed any of the
intended functionality, but if you check back here often, you may very well
find changes, even over just a couple of days.

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

Build
-----

Currently, to build TwitTP, you need [CMake][5] to generate the build files and
one of the supported [CMake generators][6]. Once you have this, you can build
the project as follows:

    cd /path/to/twittp/directory
    mkdir build
    cd build
    cmake ..

This will generate the build files in your new build directory. From there, you
build the project with the generated Makefile/Visual Studio sln/Whatever and
the resulting twittp binary should appear in the build/bin directory. An example
using makefiles is to do the previous steps, then type `make`. This is
sufficient to generate the binary on a platform that uses makefiles for its
generator.

Usage
-----

(In Progress)

Contact
-------

To contact me, send an email to my [ASU Email][2] or my [personal email][3]. To
learn more about me or what else I do, visit [my website][4].

[1]: http://more.engineering.asu.edu/furi/ "FURI Home Page"
[2]: mailto:grant.a.marshall@asu.edu "ASU Email"
[3]: mailto:gam@mthcmp.com "Personal Email"
[4]: http://www.mthcmp.com "Personal Website"
[5]: http://www.cmake.org "CMake"
[6]: http://www.cmake.org/cmake/help/v2.8.12/cmake.html#section_Generators "CMake Generators"

