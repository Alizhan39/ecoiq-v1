#pragma once

// Offline candidate spatial calculations for the existing digital_twin app.
// No graphics backend, Python bridge, mesh upload, file I/O, AI or live site data.
#include <array>
#include <cstddef>

namespace ecoiq::twin {

struct Point3 {
  double x;
  double y;
  double z;
};

struct Bounds3 {
  Point3 minimum;
  Point3 maximum;
};

struct TwinPose {
  Point3 translation;
  // metres per local model unit, must be strictly positive and finite.
  double metres_per_unit;
};

[[nodiscard]] Point3 transform_point(Point3 local, TwinPose pose);
[[nodiscard]] Bounds3 transform_bounds(Bounds3 local, TwinPose pose);
[[nodiscard]] double volume_m3(Bounds3 world_bounds);

} // namespace ecoiq::twin
