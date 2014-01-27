/*! \brief File that simply contains the main procedure of the program.
 *  \file main.cpp
 *
 *  This file contains functions that set up and execute the functionality of
 *  the twittp executable.
 *
 *  \author Grant Marshall <grant.a.marshall@asu.edu>
 */
#include <iostream>
#include <memory>

#include "easylogging++.h"

#include "data_loader.hpp"
#include "data_point.hpp"
#include "trend_line.hpp"

// Logging library requires initialization
_INITIALIZE_EASYLOGGINGPP

/*! \brief Entry point for the program.
 *
 *  \fn main
 *  \param argc The number of arguments provided
 *  \param argv An array of cstyle strings containing the arguments
 *  \return An integer code representing the success of the program
 *
 *  Not very much is done in the main method. Most work is done is separate
 *  objects to better organize the code.
 */
int main(int argc, char* argv[]) {
    el::Helpers::setArgs(argc, argv);

    if (argc < 2)
        LOG(INFO) << "Please provide a file to read data from.";
    else
        LOG(INFO) << "Reading data from " << argv[1];

    std::string file(argv[1]);

    std::vector<std::shared_ptr<twittp::trend_line>> trend_lines =
        twittp::data_loader::load_data(file, twittp::file_type::TSV);

    return 0;
}
