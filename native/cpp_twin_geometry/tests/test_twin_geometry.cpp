#include "ecoiq/twin_geometry.hpp"

#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

using ecoiq::twin::Bounds3;
using ecoiq::twin::Point3;
using ecoiq::twin::TwinPose;
using ecoiq::twin::transform_bounds;
using ecoiq::twin::transform_point;
using ecoiq::twin::volume_m3;

void require(bool valid, const char* message) {
  if (!valid) {
    throw std::runtime_error(message);
  }
}

template <typename F>
void require_rejected(F&& operation, const char* message) {
  try {
    operation();
  } catch (const std::invalid_argument&) {
    return;
  }
  throw std::runtime_error(message);
}

int main() {
  try {
    const TwinPose pose{Point3{10.0, 20.0, -5.0}, 2.0};
    const Point3 mapped = transform_point(Point3{1.0, 2.0, 3.0}, pose);
    require(mapped.x == 12.0 && mapped.y == 24.0 && mapped.z == 1.0,
            "Point translation/scaling failed");

    const Bounds3 box = transform_bounds(
        Bounds3{Point3{0, 0, 0}, Point3{2, 3, 4}}, pose);
    require(box.minimum.x == 10.0 && box.maximum.z == 3.0,
            "Bounds transform incorrect");
    require(volume_m3(box) == 192.0, "Volume must use cubic metres");

    require(volume_m3(Bounds3{Point3{0, 0, 0}, Point3{0, 5, 5}}) == 0.0,
            "Measured zero volume must not be treated as missing");

    require_rejected([&] {
      transform_point(Point3{0, 0, 0}, TwinPose{Point3{0, 0, 0}, 0});
    }, "Zero scale should be rejected");
    require_rejected([&] {
      transform_point(Point3{0, 0, 0}, TwinPose{Point3{0, 0, 0}, -1});
    }, "Negative scale should be rejected");
    require_rejected([&] {
      transform_bounds(Bounds3{Point3{4, 0, 0}, Point3{1, 3, 4}}, pose);
    }, "Reversed bounds should be rejected");
    require_rejected([&] {
      transform_point(Point3{std::numeric_limits<double>::quiet_NaN(), 0, 0}, pose);
    }, "NaN should be rejected");
    require_rejected([&] {
      transform_point(Point3{std::numeric_limits<double>::max(), 0, 0},
                      TwinPose{Point3{0, 0, 0}, 2.0});
    }, "Overflow should be rejected");
    require_rejected([&] {
      volume_m3(Bounds3{Point3{0, 0, 0},
                        Point3{std::numeric_limits<double>::max(), 1e200, 2}});
    }, "Volume overflow should be rejected");

    std::cout << "EcoIQ C++ candidate geometry: all safety checks passed\n";
    return 0;
  } catch (const std::exception& exc) {
    std::cerr << "EcoIQ C++ candidate geometry failed: " << exc.what() << '\n';
    return 1;
  }
}
