// Synthetic-only geometry preview wrapper for existing C++ library.
// No site model ingestion, no licence claims, no renderer, no network.
#include "ecoiq/twin_geometry.hpp"

#include <cmath>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {
double bounded(const char* text) {
  const std::string token(text);
  if (token.empty() || token.size() > 32) {
    throw std::invalid_argument("invalid dimension");
  }
  std::size_t parsed = 0;
  const double value = std::stod(token, &parsed);
  if (parsed != token.size() || !std::isfinite(value) || value < 0.0 ||
      value > 1'000'000.0) {
    throw std::invalid_argument("invalid dimension");
  }
  return value;
}
} // namespace

int main(int argc, char** argv) {
  if (argc != 5) {
    std::cerr << "usage: ecoiq-twin-preview X Y Z METRES_PER_UNIT\n";
    return 2;
  }
  try {
    const double x = bounded(argv[1]);
    const double y = bounded(argv[2]);
    const double z = bounded(argv[3]);
    const double scale = bounded(argv[4]);
    if (scale <= 0.0) {
      throw std::invalid_argument("scale must be positive");
    }
    const auto bounds = ecoiq::twin::transform_bounds(
        {{0.0, 0.0, 0.0}, {x, y, z}},
        {{0.0, 0.0, 0.0}, scale});
    const double volume = ecoiq::twin::volume_m3(bounds);
    std::cout << std::setprecision(15)
              << "{\"synthetic_geometry_volume_m3\":" << volume
              << ",\"engineering_calibrated\":false"
              << ",\"approved_for_real_assets\":false}\n";
    return 0;
  } catch (const std::exception&) {
    std::cerr << "invalid synthetic geometry\n";
    return 1;
  }
}
