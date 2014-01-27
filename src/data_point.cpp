#include "data_point.hpp"

// This is the implementation of the primary constructor
twittp::data_point::data_point(long timestamp, long count, long delta_count, long delta_delta_count, bool trending) {
    this->timestamp = timestamp;
    this->count = count;
    this->delta_count = delta_count;
    this->delta_delta_count = delta_delta_count;
    this->trending = trending;
}
