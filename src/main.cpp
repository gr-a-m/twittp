/*! \brief File that simply contains the main procedure of the program.
 *  \file main.cpp
 *
 *  This file contains functions that set up and execute the functionality of
 *  the twittp executable.
 *
 *  \author Grant Marshall <grant.a.marshall@asu.edu>
 */
#include <iostream>

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
    if (argc < 2)
        std::cout << "Please provide a file name" << std::endl;
    else
        std::cout << "Reading data from file " << argv[1] << std::endl;

    return 0;
}
