#ifndef TWITTP_DATA_LOADER_HPP
#define TWITTP_DATA_LOADER_HPP

#include <memory>
#include <vector>

#include "trend_line.hpp"

namespace twittp {
    enum class file_type {
        TSV
    };

    class data_loader {
        public:
            std::vector<std::shared_ptr<twittp::trend_line>> static load_data(std::string file_name, twittp::file_type type);
    };
}

#endif
