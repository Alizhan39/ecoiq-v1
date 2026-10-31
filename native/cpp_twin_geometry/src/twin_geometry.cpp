#include "ecoiq/twin_geometry.hpp"

#include <cmath>
#include <stdexcept>

namespace ecoiq::twin {

namespace {
void require_finite(double value) {
  if (!std::isfinite(value)) {
    throw std::invalid_argument("Non-finite geometry is not permitted");
  }
}

void validate_point(Point3 value) {
  require_finite(value.x);
  require_finite(value.y);
  require_finite(value.z);
}

void validate_bounds(Bounds3 bounds) {
  validate_point(bounds.minimum);
  validate_point(bounds.maximum);
  if (bounds.minimum.x > bounds.maximum.x ||
      bounds.minimum.y > bounds.maximum.y ||
      bounds.minimum.z > bounds.maximum.z) {
    throw std::invalid_argument("Bounds have negative dimensions");
  }
}

} // namespace

Point3 transform_point(Point3 local, TwinPose pose) {
  validate_point(local);
  validate_point(pose.translation);
  require_finite(pose.metres_per_unit);
  if (pose.metres_per_unit <= 0.0) {
    throw std::invalid_argument("Scale must be greater than zero");
  }
  Point3 result{
      pose.translation.x + local.x * pose.metres_per_unit,
      pose.translation.y + local.y * pose.metres_per_unit,
      pose.translation.z + local.z * pose.metres_per_unit};
  validate_point(result);
  return result;
}

Bounds3 transform_bounds(Bounds3 local, TwinPose pose) {
  validate_bounds(local);
  return Bounds3{
      transform_point(local.minimum, pose),
      transform_point(local.maximum, pose)};
}

double volume_m3(Bounds3 world_bounds) {
  validate_bounds(world_bounds);
  const auto dx = world_bounds.maximum.x - world_bounds.minimum.x;
  const auto dy = world_bounds.maximum.y - world_bounds.minimum.y;
  const auto dz = world_bounds.maximum.z - world_bounds.minimum.z;
  const double volume = dx * dy * dz;
  require_finite(volume);
  return volume;
}

} // namespace ecoiq::twin
