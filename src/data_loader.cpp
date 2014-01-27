#include "data_loader.hpp"

#include <fstream>
#include <sstream>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

#include "easylogging++.h"

std::vector<std::shared_ptr<twittp::trend_line>> twittp::data_loader::load_data(
        std::string file_name, twittp::file_type type) {
    // Open a file stream
    LOG(INFO) << "Opening file stream";
    std::ifstream file(file_name);

    // Create a vector to hold pointers to trend lines
    std::vector<std::shared_ptr<twittp::trend_line>> trend_lines;

    // Currently, don't bother with file type -- only TSV
    if (type != twittp::file_type::TSV) {
        ;
    }

    // Keep track of the previous count and delta to compute delta and delta delta
    long last_count = 0;
    long last_delta = 0;
    std::string last_topic = "";

    std::unordered_map<std::string, std::shared_ptr<std::map<long, twittp::data_point>>> topics_base_map;

    LOG(INFO) << "Reading lines from " << file_name;
    // Extract lines from the file until we hit eof
    while (!file.eof()) {
        // Read a line and put it into a stringstream
        std::string line;
        std::getline(file, line);
        std::stringstream ss(line);

        // Extract the topic_name first
        std::string topic_name;
        std::getline(ss, topic_name, '\t');

        // If we've reached a new topic, reset the last variables
        if (last_topic != topic_name) {
            last_count = 0;
            last_delta = 0;
            last_topic = topic_name;
        }

        // Extract the timestamp of the data point
        long timestamp;
        ss >> timestamp;

        // Extract the counts
        long count;
        ss >> count;

        // Compute delta and delta_delta if possible
        long delta = 0;
        if (last_count != 0) {
            delta = count - last_count;
        }

        long delta_delta = 0;
        if (last_delta != 0) {
            delta_delta = delta - last_delta;
        }

        // Extract whether we are trending or not
        bool trending;
        ss >> trending;

        // Add the data point to the base map
        twittp::data_point dp(timestamp, count, delta, delta_delta, trending);
        if (topics_base_map.find(topic_name) == topics_base_map.end()) {
            topics_base_map[topic_name] = std::make_shared<std::map<long, twittp::data_point>>();
        }
        topics_base_map[topic_name]->insert(std::make_pair(timestamp, dp));
    }
    LOG(INFO) << "Finished reading from " << file_name;

    for(auto it = topics_base_map.begin(); it != topics_base_map.end(); ++it) {
        std::shared_ptr<std::map<long, twittp::data_point>> temp_map = (*it).second;
        std::shared_ptr<twittp::trend_line> tl = std::make_shared<twittp::trend_line>(temp_map);
        trend_lines.push_back(tl);
    }
    LOG(INFO) << "Data converted into trend lines";

    return trend_lines;
}
