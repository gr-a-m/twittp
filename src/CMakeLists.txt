# This is the CMake build file for the src directory
set(CMAKE_CXX_FLAGS -std=c++11)
set(TWITTP_SOURCE_FILES main.cpp data_loader.hpp data_loader.cpp data_point.hpp data_point.cpp trend_line.hpp trend_line.cpp)

add_executable(twittp ${TWITTP_SOURCE_FILES})

