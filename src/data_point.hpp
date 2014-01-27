/*! This file contains the interface for the data_point class.
 *  \file data_point.hpp
 *  \author Grant Marshall <grant.a.marshall@asu.edu>
 */
#ifndef TWITTP_DATA_POINT_HPP
#define TWITTP_DATA_POINT_HPP

namespace twittp {
    /*! \brief This class represents information about a trend for a given
     *  window in time.
     *  \class data_point
     *
     *  This class has public access to its members because it is primarily a
     *  data class.
     */
    class data_point {
        public:
            // Data
            //! The timestamp for this point in the time series
            long timestamp;
            //! The number of tweets for the topic in this window in the time series
            long count;
            //! The change in count since the last data point
            long delta_count;
            //! The change in the change in count since the last data point
            long delta_delta_count;
            //! Whether the topic is trending at this point or not
            bool trending;

            // Functions
            /*! The main constructor for the class -- it requires all of the
             *  data be known.
             */
            data_point(long timestamp, long count, long delta_count,
                    long delta_delta_count, bool trending);
    };
}

#endif
