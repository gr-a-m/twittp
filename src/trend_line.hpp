#ifndef TWITTP_TREND_LINE_HPP
#define TWITTP_TREND_LINE_HPP

#include <map>
#include <memory>

#include "data_point.hpp"

namespace twittp {
    struct trend_line_difference {
        long timestamp;
        int distance;
    };

    class trend_line {
        public:
            // Data
            std::shared_ptr<std::map<long, twittp::data_point>> data_series;

            // Functions
            trend_line(std::shared_ptr<std::map<long, twittp::data_point>> data_series);
            twittp::trend_line_difference distance(const trend_line& other_trend_line);
    };
}

#endif
