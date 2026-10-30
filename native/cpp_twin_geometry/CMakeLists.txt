cmake_minimum_required(VERSION 3.16)
project(ecoiq_cpp_twin_geometry LANGUAGES CXX)

add_library(ecoiq_twin_geometry STATIC src/twin_geometry.cpp)
target_compile_features(ecoiq_twin_geometry PUBLIC cxx_std_20)
target_include_directories(ecoiq_twin_geometry PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_compile_options(ecoiq_twin_geometry PRIVATE
  $<$<CXX_COMPILER_ID:GNU,Clang>:-Wall -Wextra -Wpedantic -Werror>)

add_executable(ecoiq_twin_geometry_tests tests/test_twin_geometry.cpp)
target_link_libraries(ecoiq_twin_geometry_tests PRIVATE ecoiq_twin_geometry)
enable_testing()
add_test(NAME safe_geometry_math COMMAND ecoiq_twin_geometry_tests)

# Offline synthetic-only preview, not linked into Django.
add_executable(ecoiq-twin-preview src/demo_cli.cpp)
target_link_libraries(ecoiq-twin-preview PRIVATE ecoiq_twin_geometry)
