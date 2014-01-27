#include "trend_line.hpp"

#include <memory>

twittp::trend_line::trend_line(std::shared_ptr<std::map<long, data_point>> data_series) {
    this->data_series = std::shared_ptr<std::map<long, data_point>>(data_series);
}

twittp::trend_line_difference twittp::trend_line::distance(const twittp::trend_line& other_trend_line) {
    return twittp::trend_line_difference { 0, 0 };
}
